#!/usr/bin/env python3
"""Evals par agents : exécution par des sous-agents Claude Code, notation par Codex.

Variante de ``run_evals.py`` qui ne dépend ni de ``claude -p`` ni de l'API Anthropic. Elle compare
plusieurs versions de la skill sur les mêmes cas, en trois temps :

1. ``preparer`` crée un dossier de campagne : une copie de chaque version de la skill (sans ses
   evals, pour que l'agent ne voie pas les attentes), un fichier par énoncé, et ``consignes.json``,
   la liste des tâches à confier aux sous-agents (une par version et par cas) ;
2. Claude Code lance un sous-agent par tâche (modèle Sonnet par défaut), qui lit la skill copiée,
   répond à l'énoncé et écrit sa réponse au chemin indiqué. La procédure est décrite dans la skill
   de projet ``.claude/skills/evals-par-agents/SKILL.md`` ;
3. ``noter`` fait noter chaque réponse par un modèle indépendant via la CLI Codex (``codex exec``),
   avec la consigne et le schéma de ``run_evals.py``, puis écrit ``resultats.json`` et ``rapport.md``.

Usage (depuis la racine du dépôt) :

    python3 scripts/evals_agents.py preparer --ids 1,2,11 --versions v0.5.3,courante
    python3 scripts/evals_agents.py noter legistique-fr-workspace/evals-agents/<horodatage>
    python3 scripts/evals_agents.py noter <dossier> --modele gpt-6.1-sol --parallele 8

Une version est ``courante`` (l'arbre de travail, modifications non commitées comprises) ou toute
référence git (étiquette ``v0.5.3``, branche, commit). Les campagnes sont écrites dans
``legistique-fr-workspace/evals-agents/<horodatage>/`` (dossier ignoré par git).
"""
import argparse
import concurrent.futures
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_evals as R  # noqa: E402

WORKSPACE = ROOT / "legistique-fr-workspace" / "evals-agents"
JUGE_CODEX = "gpt-6.1-sol"
MODELE_AGENT = "sonnet"

CONSIGNE_AGENT = """You are acting as a user-facing assistant equipped with a skill. The skill lives in \
this folder (and ONLY this folder): {skill}

1. Read SKILL.md in that folder in full and follow its instructions, reading the reference files it \
points to when relevant (only inside that folder). You may run its python scripts (lint) if useful. \
Do not read any other folder on disk (no other skill versions, no evals, no repository, no other \
answers), and do not use the web.
2. Then answer, in French, the user request contained in this file: {enonce}
3. Write your complete final answer (exactly what you would show the user, in Markdown) to: {reponse}
Then reply with just "done"."""


# --- Préparation --------------------------------------------------------------------------------


def nom_dossier(version):
    return version.replace("/", "-")


def copier_version(version, cible):
    """Copie le dossier legistique-fr de la version demandée dans cible, sans les evals."""
    dest = cible / "legistique-fr"
    if version == "courante":
        shutil.copytree(R.SKILL, dest, ignore=shutil.ignore_patterns("evals", "__pycache__", "*.pyc"))
        return
    archive = subprocess.run(["git", "archive", version, "legistique-fr"], cwd=ROOT,
                             capture_output=True, check=False)
    if archive.returncode:
        sys.exit(f"version introuvable dans git : {version} ({archive.stderr.decode().strip()})")
    cible.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-x", "-C", str(cible)], input=archive.stdout, check=True)
    shutil.rmtree(dest / "evals", ignore_errors=True)


def preparer(args):
    evals = R.choisir(json.loads(R.EVALS.read_text(encoding="utf-8"))["evals"], args.ids)
    versions = [v.strip() for v in args.versions.split(",") if v.strip()]
    horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dossier = (Path(args.sortie) if args.sortie else WORKSPACE / horodatage).resolve()
    (dossier / "enonces").mkdir(parents=True, exist_ok=True)
    for ev in evals:
        (dossier / "enonces" / f"{ev['id']:02d}.txt").write_text(ev["prompt"], encoding="utf-8")
    taches = []
    for version in versions:
        vdir = dossier / "skills" / nom_dossier(version)
        copier_version(version, vdir)
        (dossier / "reponses" / nom_dossier(version)).mkdir(parents=True, exist_ok=True)
        for ev in evals:
            skill = vdir / "legistique-fr"
            enonce = dossier / "enonces" / f"{ev['id']:02d}.txt"
            reponse = dossier / "reponses" / nom_dossier(version) / f"{ev['id']:02d}.md"
            taches.append({
                "version": version, "id": ev["id"], "nom": ev["name"],
                "description": f"Eval {ev['id']} {version}",
                "modele": args.modele_agent,
                "reponse": str(reponse),
                "consigne": CONSIGNE_AGENT.format(skill=skill, enonce=enonce, reponse=reponse),
            })
    campagne = {"date": horodatage, "versions": versions, "ids": [e["id"] for e in evals],
                "modele_agent": args.modele_agent, "taches": taches}
    (dossier / "consignes.json").write_text(json.dumps(campagne, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Campagne préparée : {dossier}")
    print(f"{len(taches)} tâche(s) à confier à des sous-agents ({args.modele_agent}) : voir consignes.json")
    return dossier


# --- Notation -----------------------------------------------------------------------------------


def noter_une(tache, ev, modele, dossier):
    reponse = Path(tache["reponse"])
    ligne = {"version": tache["version"], "id": ev["id"], "nom": ev["name"], "total": len(ev["expectations"]),
             "attentes": ev["expectations"]}
    if not reponse.exists() or not reponse.read_text(encoding="utf-8").strip():
        ligne["erreur"] = "réponse absente"
        return ligne
    schema = dossier / "schema-verdicts.json"
    sortie = dossier / "verdicts" / f"{nom_dossier(tache['version'])}-{ev['id']:02d}.json"
    sortie.parent.mkdir(exist_ok=True)
    msg = R.message_juge(ev, reponse.read_text(encoding="utf-8"), [])
    proc = subprocess.run(["codex", "exec", "-m", modele, "--skip-git-repo-check", "-s", "read-only",
                           "--output-schema", str(schema), "-o", str(sortie), msg],
                          cwd=dossier, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1200)
    try:
        verdicts = json.loads(sortie.read_text(encoding="utf-8"))["verdicts"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        ligne["erreur"] = f"notation impossible : {proc.stderr.strip()[-300:]}"
        return ligne
    if [v["numero"] for v in verdicts] != list(range(1, ligne["total"] + 1)):
        ligne["erreur"] = f"{len(verdicts)} verdicts pour {ligne['total']} attentes"
        return ligne
    ligne["verdicts"] = verdicts
    ligne["reussies"] = sum(v["respecte"] for v in verdicts)
    return ligne


def rapport(campagne, lignes, modele):
    versions = campagne["versions"]
    par = {(l["version"], l["id"]): l for l in lignes}
    out = ["# Evals par agents", "",
           f"Exécution : sous-agents Claude Code ({campagne['modele_agent']}) ; notation : {modele} (Codex)", "",
           "| Eval | " + " | ".join(versions) + " |", "|---|" + "---|" * len(versions)]
    for i in campagne["ids"]:
        nom = next(l["nom"] for l in lignes if l["id"] == i)
        cases = []
        for v in versions:
            l = par.get((v, i), {})
            cases.append(f"{l['reussies']}/{l['total']}" if "reussies" in l else (l.get("erreur") or "—"))
        out.append(f"| {i}. {nom} | " + " | ".join(cases) + " |")
    totaux = []
    for v in versions:
        notees = [l for l in lignes if l["version"] == v and "reussies" in l]
        r, t = sum(l["reussies"] for l in notees), sum(l["total"] for l in notees)
        totaux.append(f"**{r}/{t}**" + (f" ({100 * r / t:.0f} %)" if t else ""))
    out += ["| **Total** | " + " | ".join(totaux) + " |", "", "## Attentes non respectées", ""]
    for l in sorted(lignes, key=lambda l: (l["version"], l["id"])):
        for v in l.get("verdicts", []):
            if not v["respecte"]:
                out.append(f"- **{l['version']}**, eval {l['id']} ({l['nom']}), attente {v['numero']} : "
                           f"{l['attentes'][v['numero'] - 1]}  \n  {v['justification']}")
    return "\n".join(out) + "\n"


def noter(args):
    if not shutil.which("codex"):
        sys.exit("CLI « codex » introuvable : installer Codex pour la notation.")
    dossier = Path(args.dossier).resolve()
    campagne = json.loads((dossier / "consignes.json").read_text(encoding="utf-8"))
    evals = {e["id"]: e for e in json.loads(R.EVALS.read_text(encoding="utf-8"))["evals"]}
    (dossier / "schema-verdicts.json").write_text(json.dumps(R.SCHEMA_VERDICTS), encoding="utf-8")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallele) as pool:
        lignes = list(pool.map(lambda t: noter_une(t, evals[t["id"]], args.modele, dossier), campagne["taches"]))
    for l in lignes:
        etat = f"{l['reussies']}/{l['total']}" if "reussies" in l else l.get("erreur")
        print(f"  {l['version']:<12} {l['id']:2d} {l['nom']:<40} {etat}")
    (dossier / "resultats.json").write_text(json.dumps({"juge": args.modele, "lignes": lignes},
                                                       ensure_ascii=False, indent=2), encoding="utf-8")
    (dossier / "rapport.md").write_text(rapport(campagne, lignes, args.modele), encoding="utf-8")
    print(f"\nRapport : {dossier / 'rapport.md'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = ap.add_subparsers(dest="commande", required=True)
    p = sous.add_parser("preparer", help="crée le dossier de campagne et la liste des tâches")
    p.add_argument("--ids", help="evals à lancer (ex. « 1,2,11 ») ; toutes par défaut")
    p.add_argument("--versions", default="courante",
                   help="versions comparées, séparées par des virgules : « courante » ou une référence git")
    p.add_argument("--modele-agent", default=MODELE_AGENT, help=f"modèle des sous-agents (défaut : {MODELE_AGENT})")
    p.add_argument("--sortie", help="dossier de campagne (défaut : legistique-fr-workspace/evals-agents/<horodatage>)")
    n = sous.add_parser("noter", help="fait noter les réponses par Codex et écrit le rapport")
    n.add_argument("dossier", help="dossier de campagne créé par « preparer »")
    n.add_argument("--modele", default=JUGE_CODEX, help=f"modèle du juge Codex (défaut : {JUGE_CODEX})")
    n.add_argument("--parallele", type=int, default=8, help="notations simultanées (défaut : 8)")
    args = ap.parse_args(argv)
    return preparer(args) if args.commande == "preparer" else noter(args)


if __name__ == "__main__":
    main()
