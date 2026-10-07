#!/usr/bin/env python3
"""Lance les evals de la skill legistique-fr et note chaque attente avec un juge.

Deux campagnes :

- **evals de qualité** (legistique-fr/evals/evals.json) : chaque prompt est exécuté par Claude Code en
  mode non interactif (``claude -p``) dans un projet temporaire où la skill est installée, puis un juge
  (API Anthropic, sortie JSON structurée) dit pour chaque attente si la réponse la respecte ;
- **déclenchement** (legistique-fr/evals/declenchement.json, option ``--declenchement``) : chaque requête
  est soumise à Claude Code et l'on regarde seulement si la skill a été chargée.

Usage (depuis la racine du dépôt) :

    python3 scripts/run_evals.py --simulation              # vérifie la mécanique, aucun appel payant
    python3 scripts/run_evals.py                           # toutes les evals, confirmation demandée
    python3 scripts/run_evals.py --ids 2,10 --oui          # quelques evals, sans confirmation
    python3 scripts/run_evals.py --sans-skill              # référence : même prompts, skill absente
    python3 scripts/run_evals.py --declenchement           # précision et rappel du déclenchement
    python3 scripts/run_evals.py --reference legistique-fr-workspace/evals/20261007-1012
                                                           # compare au résultat d'une campagne antérieure

Chaque campagne écrit dans ``legistique-fr-workspace/evals/<horodatage>/`` (dossier ignoré par git) :
les réponses (``<nom>.md``), le journal brut de Claude Code (``<nom>.jsonl``), les verdicts
(``resultats.json``) et un rapport lisible (``rapport.md``).

Coût : chaque eval lance une session Claude Code complète, puis un appel au juge. Le script affiche le
nombre d'appels et demande confirmation avant de dépenser quoi que ce soit (``--oui`` pour s'en passer).

Prérequis : la CLI ``claude`` authentifiée ; pour le juge, le paquet ``anthropic`` (``pip install
anthropic``) et des identifiants (``ANTHROPIC_API_KEY`` ou un profil ``ant auth login``).
"""
import argparse
import concurrent.futures
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "legistique-fr"
EVALS = SKILL / "evals" / "evals.json"
DECLENCHEMENT = SKILL / "evals" / "declenchement.json"
WORKSPACE = ROOT / "legistique-fr-workspace" / "evals"

JUGE = "claude-opus-5-5"
OUTILS = ["Read", "Glob", "Grep", "Write", "Edit", "Skill", "Bash(python3:*)", "Bash(ls:*)", "Bash(mkdir:*)"]
OUTILS_WEB = ["WebFetch", "WebSearch"]

SCHEMA_VERDICTS = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "numero": {"type": "integer"},
                    "respecte": {"type": "boolean"},
                    "justification": {"type": "string"},
                },
                "required": ["numero", "respecte", "justification"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}

CONSIGNE_JUGE = """Tu évalues la réponse d'un assistant de légistique française (rédaction et correction de \
textes normatifs selon le Guide de légistique du Conseil d'Etat et du SGG).

Pour chaque attente numérotée, dis si la réponse la respecte. Sois exigeant et littéral : une attente \
n'est respectée que si la réponse y satisfait réellement, pas si elle s'en approche. Une attente qui \
interdit quelque chose (« aucun numéro inventé ») est respectée si la réponse ne le fait nulle part. \
Quand une attente porte sur le projet de texte, regarde le projet lui-même, pas les commentaires qui \
l'accompagnent. La justification tient en une ou deux phrases et cite le passage décisif.

Réponds avec un verdict par attente, dans l'ordre, numérotés à partir de 1."""


# --- Exécution d'un prompt par Claude Code -------------------------------------------------------


def preparer_projet(dossier, avec_skill):
    """Projet temporaire : la skill dans .claude/skills (sans ses evals), rien d'autre."""
    dossier.mkdir(parents=True, exist_ok=True)
    if avec_skill:
        cible = dossier / ".claude" / "skills" / "legistique-fr"
        shutil.copytree(SKILL, cible, ignore=shutil.ignore_patterns("evals", "__pycache__"))
    return dossier


def commande_claude(prompt, modele, web, budget):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--setting-sources", "project", "--strict-mcp-config", "--no-session-persistence",
           "--allowedTools", *(OUTILS + (OUTILS_WEB if web else []))]
    if modele:
        cmd += ["--model", modele]
    if budget:
        cmd += ["--max-budget-usd", str(budget)]
    return cmd


def analyser_journal(lignes):
    """Extrait du flux stream-json : texte final, outils appelés, skill chargée, coût."""
    res = {"reponse": "", "outils": [], "skill_chargee": False, "cout_usd": None, "erreur": None}
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            ev = json.loads(ligne)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for bloc in ev.get("message", {}).get("content", []):
                if bloc.get("type") != "tool_use":
                    continue
                nom, entree = bloc.get("name"), bloc.get("input") or {}
                res["outils"].append(nom)
                if nom == "Skill" and "legistique-fr" in json.dumps(entree, ensure_ascii=False):
                    res["skill_chargee"] = True
                if nom == "Read" and str(entree.get("file_path", "")).endswith("legistique-fr/SKILL.md"):
                    res["skill_chargee"] = True
        elif ev.get("type") == "result":
            res["reponse"] = ev.get("result") or ""
            res["cout_usd"] = ev.get("total_cost_usd")
            if ev.get("is_error") or ev.get("subtype") not in (None, "success"):
                res["erreur"] = ev.get("subtype") or "erreur"
    return res


def fichiers_produits(dossier):
    """Fichiers créés par la session (hors skill), avec le décompte des révisions des .docx."""
    out = []
    for p in sorted(dossier.rglob("*")):
        if not p.is_file() or ".claude" in p.relative_to(dossier).parts:
            continue
        info = {"chemin": str(p.relative_to(dossier)), "octets": p.stat().st_size}
        if p.suffix == ".docx":
            try:
                with zipfile.ZipFile(p) as z:
                    xml = z.read("word/document.xml").decode("utf-8")
                    reglages = z.read("word/settings.xml").decode("utf-8") if "word/settings.xml" in z.namelist() else ""
                info["insertions"] = len(re.findall(r"<w:ins ", xml))
                info["suppressions"] = len(re.findall(r"<w:del ", xml))
                info["suivi_active"] = "trackRevisions" in reglages
            except (KeyError, zipfile.BadZipFile) as e:
                info["illisible"] = str(e)
        out.append(info)
    return out


def executer(prompt, dossier, args, budget=None):
    if args.simulation:
        return {"reponse": "(simulation : aucune réponse produite)", "outils": [], "skill_chargee": False,
                "cout_usd": 0.0, "erreur": None, "journal": [], "fichiers": []}
    t0 = time.time()
    try:
        proc = subprocess.run(commande_claude(prompt, args.modele, args.web, budget or args.budget), cwd=dossier,
                              capture_output=True, text=True, encoding="utf-8", timeout=args.delai)
        lignes = proc.stdout.splitlines()
        res = analyser_journal(lignes)
        if proc.returncode and not res["erreur"]:
            res["erreur"] = f"code {proc.returncode} : {proc.stderr.strip()[:300]}"
    except subprocess.TimeoutExpired:
        lignes, res = [], {"reponse": "", "outils": [], "skill_chargee": False, "cout_usd": None,
                           "erreur": f"délai de {args.delai} s dépassé"}
    res["journal"] = lignes
    res["fichiers"] = fichiers_produits(dossier)
    res["duree_s"] = round(time.time() - t0, 1)
    return res


# --- Juge ----------------------------------------------------------------------------------------


def message_juge(ev, reponse, fichiers):
    attentes = "\n".join(f"{i}. {a}" for i, a in enumerate(ev["expectations"], 1))
    fichiers_txt = json.dumps(fichiers, ensure_ascii=False, indent=1) if fichiers else "aucun"
    return (f"{CONSIGNE_JUGE}\n\n<demande>\n{ev['prompt']}\n</demande>\n\n"
            f"<reponse_attendue_en_resume>\n{ev.get('expected_output', '')}\n</reponse_attendue_en_resume>\n\n"
            f"<reponse_de_l_assistant>\n{reponse}\n</reponse_de_l_assistant>\n\n"
            f"<fichiers_produits>\n{fichiers_txt}\n</fichiers_produits>\n\n<attentes>\n{attentes}\n</attentes>")


def juger(client, ev, reponse, fichiers, modele):
    import anthropic

    try:
        msg = client.beta.messages.create(
            model=modele,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA_VERDICTS}},
            messages=[{"role": "user", "content": message_juge(ev, reponse, fichiers)}],
        )
    except anthropic.RateLimitError as e:
        return None, f"limite de débit atteinte : {e.message}"
    except anthropic.APIStatusError as e:
        return None, f"erreur API {e.status_code} : {e.message}"
    except anthropic.APIConnectionError:
        return None, "connexion à l'API impossible"
    if msg.stop_reason == "refusal":
        cat = msg.stop_details.category if msg.stop_details else None
        return None, f"refus du juge (catégorie : {cat})"
    if msg.stop_reason == "max_tokens":
        return None, "réponse du juge tronquée (max_tokens)"
    texte = next((b.text for b in msg.content if b.type == "text"), None)
    if texte is None:
        return None, "réponse du juge sans texte"
    verdicts = json.loads(texte)["verdicts"]
    if [v["numero"] for v in verdicts] != list(range(1, len(ev["expectations"]) + 1)):
        return None, f"le juge a rendu {len(verdicts)} verdicts pour {len(ev['expectations'])} attentes"
    usage = {"entree": msg.usage.input_tokens, "sortie": msg.usage.output_tokens}
    return {"verdicts": verdicts, "usage_juge": usage}, None


# --- Campagnes ----------------------------------------------------------------------------------


def campagne_qualite(evals, args, sortie, client):
    def une(ev):
        with tempfile.TemporaryDirectory(prefix=f"eval-{ev['name']}-") as tmp:
            dossier = preparer_projet(Path(tmp), not args.sans_skill)
            ex = executer(ev["prompt"], dossier, args)
        (sortie / f"{ev['id']:02d}-{ev['name']}.md").write_text(ex["reponse"], encoding="utf-8")
        (sortie / f"{ev['id']:02d}-{ev['name']}.jsonl").write_text("\n".join(ex["journal"]), encoding="utf-8")
        ligne = {"id": ev["id"], "nom": ev["name"], "skill_chargee": ex["skill_chargee"], "cout_usd": ex["cout_usd"],
                 "duree_s": ex.get("duree_s"), "fichiers": ex["fichiers"], "erreur": ex["erreur"]}
        if ex["erreur"] and not ex["reponse"]:
            return ligne
        if args.simulation:
            ligne["verdicts"] = [{"numero": i, "respecte": False, "justification": "simulation"}
                                 for i in range(1, len(ev["expectations"]) + 1)]
        else:
            jugement, erreur = juger(client, ev, ex["reponse"], ex["fichiers"], args.juge)
            if erreur:
                ligne["erreur"] = erreur
                return ligne
            ligne.update(jugement)
        ligne["reussies"] = sum(v["respecte"] for v in ligne["verdicts"])
        ligne["total"] = len(ev["expectations"])
        ligne["attentes"] = ev["expectations"]
        print(f"  {ev['id']:2d} {ev['name']:<40} {ligne['reussies']}/{ligne['total']}", flush=True)
        return ligne

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallele) as pool:
        lignes = list(pool.map(une, evals))
    return sorted(lignes, key=lambda l: l["id"])


def campagne_declenchement(requetes, args):
    def une(c):
        with tempfile.TemporaryDirectory(prefix="declenchement-") as tmp:
            dossier = preparer_projet(Path(tmp), True)
            ex = executer(c["requete"], dossier, args, budget=args.budget_declenchement)
        return {"requete": c["requete"], "attendu": c["doit_declencher"], "observe": ex["skill_chargee"],
                "cout_usd": ex["cout_usd"], "erreur": ex["erreur"] if not ex["outils"] else None}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallele) as pool:
        return list(pool.map(une, requetes))


# --- Rapports -----------------------------------------------------------------------------------


def taux(lignes):
    notees = [l for l in lignes if "total" in l]
    reussies, total = sum(l["reussies"] for l in notees), sum(l["total"] for l in notees)
    return reussies, total


def rapport_qualite(lignes, args, reference=None):
    reussies, total = taux(lignes)
    ref = {l["nom"]: l for l in (reference or [])}
    out = [f"# Evals de qualité ({'sans' if args.sans_skill else 'avec'} la skill)", "",
           f"Exécution : {args.modele or 'modèle par défaut de Claude Code'} ; juge : {args.juge}"
           + (" ; **simulation**" if args.simulation else ""), "",
           f"**Total : {reussies}/{total} attentes respectées"
           + (f" ({100 * reussies / total:.0f} %)" if total else "") + "**", "",
           "| Eval | Score | " + ("Référence | " if reference else "") + "Skill chargée | Coût ($) | Remarque |",
           "|---|---|---|---|---|" + ("---|" if reference else "")]
    for l in lignes:
        score = f"{l['reussies']}/{l['total']}" if "total" in l else "—"
        cols = [f"{l['id']}. {l['nom']}", score]
        if reference:
            r = ref.get(l["nom"])
            cols.append(f"{r['reussies']}/{r['total']}" if r and "total" in r else "—")
        cout = f"{l['cout_usd']:.2f}" if isinstance(l.get("cout_usd"), (int, float)) else "—"
        cols += ["oui" if l["skill_chargee"] else "non", cout, l.get("erreur") or ""]
        out.append("| " + " | ".join(cols) + " |")
    out += ["", "## Attentes non respectées", ""]
    for l in lignes:
        for v in l.get("verdicts", []):
            if not v["respecte"]:
                out.append(f"- **{l['nom']}**, attente {v['numero']} : {l['attentes'][v['numero'] - 1]}  \n"
                           f"  {v['justification']}")
    return "\n".join(out) + "\n"


def rapport_declenchement(lignes, args):
    vp = sum(l["attendu"] and l["observe"] for l in lignes)
    fp = sum(not l["attendu"] and l["observe"] for l in lignes)
    fn = sum(l["attendu"] and not l["observe"] for l in lignes)
    precision = vp / (vp + fp) if vp + fp else 0.0
    rappel = vp / (vp + fn) if vp + fn else 0.0
    out = ["# Déclenchement de la skill" + (" (simulation)" if args.simulation else ""), "",
           f"Précision : {precision:.0%} ; rappel : {rappel:.0%} ({vp} vrais positifs, {fp} faux positifs, "
           f"{fn} faux négatifs sur {len(lignes)} requêtes)", "",
           "| Requête | Attendu | Observé | |", "|---|---|---|---|"]
    for l in lignes:
        ok = "✓" if l["attendu"] == l["observe"] else "✗"
        out.append(f"| {l['requete'][:90]} | {'oui' if l['attendu'] else 'non'} | "
                   f"{'oui' if l['observe'] else 'non'} | {ok} {l.get('erreur') or ''} |")
    return "\n".join(out) + "\n", {"precision": precision, "rappel": rappel}


# --- Programme principal ------------------------------------------------------------------------


def choisir(evals, ids):
    if not ids:
        return evals
    voulus = {int(x) for x in ids.split(",")}
    choisies = [e for e in evals if e["id"] in voulus]
    inconnus = voulus - {e["id"] for e in choisies}
    if inconnus:
        sys.exit(f"identifiants d'eval inconnus : {sorted(inconnus)}")
    return choisies


def confirmer(n_sessions, n_juge, args):
    if args.simulation or args.oui:
        return
    print(f"Cette campagne lance {n_sessions} session(s) Claude Code"
          + (f" et {n_juge} appel(s) au juge ({args.juge})" if n_juge else "")
          + (f", plafonnées à {args.budget} $ par session" if args.budget else "") + ".")
    if input("Continuer ? [o/N] ").strip().lower() not in {"o", "oui", "y", "yes"}:
        sys.exit("Campagne annulée.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="evals à lancer, par identifiant (ex. « 1,2,10 ») ; toutes par défaut")
    ap.add_argument("--declenchement", action="store_true", help="campagne de déclenchement au lieu des evals")
    ap.add_argument("--sans-skill", action="store_true", help="exécuter les prompts sans la skill (référence)")
    ap.add_argument("--modele", help="modèle de Claude Code pour l'exécution (défaut : celui de la CLI)")
    ap.add_argument("--juge", default=JUGE, help=f"modèle du juge (défaut : {JUGE})")
    ap.add_argument("--web", action="store_true", help="autoriser WebFetch et WebSearch (vérification Légifrance)")
    ap.add_argument("--budget", type=float, help="plafond de dépense par session Claude Code, en dollars")
    ap.add_argument("--delai", type=int, default=1800, help="délai maximal d'une session, en secondes")
    ap.add_argument("--budget-declenchement", type=float, default=0.5,
                    help="plafond par requête de déclenchement, en dollars (défaut : 0,50) : seul compte le "
                         "chargement de la skill, pas la réponse complète")
    ap.add_argument("--parallele", type=int, default=1, help="sessions simultanées (défaut : 1)")
    ap.add_argument("--reference", help="dossier d'une campagne antérieure à comparer")
    ap.add_argument("--sortie", help="dossier de sortie (défaut : legistique-fr-workspace/evals/<horodatage>)")
    ap.add_argument("--simulation", action="store_true",
                    help="ne rien appeler : vérifie la préparation, l'analyse et les rapports")
    ap.add_argument("--oui", action="store_true", help="ne pas demander de confirmation avant de dépenser")
    args = ap.parse_args(argv)

    if not args.simulation and not shutil.which("claude"):
        sys.exit("CLI « claude » introuvable : installer Claude Code ou lancer avec --simulation.")

    horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    suffixe = "-declenchement" if args.declenchement else ("-sans-skill" if args.sans_skill else "")
    sortie = Path(args.sortie) if args.sortie else WORKSPACE / (horodatage + suffixe)
    sortie.mkdir(parents=True, exist_ok=True)

    if args.declenchement:
        requetes = json.loads(DECLENCHEMENT.read_text(encoding="utf-8"))
        args.budget = args.budget_declenchement
        confirmer(len(requetes), 0, args)
        lignes = campagne_declenchement(requetes, args)
        texte, mesures = rapport_declenchement(lignes, args)
        (sortie / "resultats.json").write_text(json.dumps({"mesures": mesures, "requetes": lignes},
                                                          ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        evals = choisir(json.loads(EVALS.read_text(encoding="utf-8"))["evals"], args.ids)
        confirmer(len(evals), len(evals), args)
        client = None
        if not args.simulation:
            try:
                import anthropic
            except ImportError:
                sys.exit("Le juge a besoin du paquet « anthropic » : pip install anthropic")
            client = anthropic.Anthropic()
        print(f"{len(evals)} eval(s) → {sortie}")
        lignes = campagne_qualite(evals, args, sortie, client)
        reference = None
        if args.reference:
            reference = json.loads((Path(args.reference) / "resultats.json").read_text(encoding="utf-8"))["evals"]
        texte = rapport_qualite(lignes, args, reference)
        reussies, total = taux(lignes)
        resultats = {"date": horodatage, "avec_skill": not args.sans_skill, "modele": args.modele,
                     "juge": args.juge, "simulation": args.simulation, "reussies": reussies, "total": total,
                     "evals": lignes}
        (sortie / "resultats.json").write_text(json.dumps(resultats, ensure_ascii=False, indent=2), encoding="utf-8")

    (sortie / "rapport.md").write_text(texte, encoding="utf-8")
    print(f"\nRapport : {sortie / 'rapport.md'}")
    return sortie


if __name__ == "__main__":
    main()
