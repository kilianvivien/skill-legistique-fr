"""Tests du lanceur d'evals (scripts/run_evals.py), sans aucun appel payant."""
import io
import json
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_evals as RE  # noqa: E402

try:
    import anthropic  # noqa: F401
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


def ev_type(**kw):
    base = {"id": 1, "name": "essai", "prompt": "Rédige un décret.", "expected_output": "Un décret.",
            "files": [], "expectations": ["Le projet est au présent", "Aucun NOR inventé"]}
    base.update(kw)
    return base


class Journal(unittest.TestCase):

    def lignes(self, *evs):
        return [json.dumps(e, ensure_ascii=False) for e in evs]

    def test_reponse_cout_et_skill(self):
        journal = self.lignes(
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Skill", "input": {"skill": "legistique-fr"}}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/x/references/typographie.md"}},
                {"type": "text", "text": "…"}]}},
            {"type": "result", "subtype": "success", "result": "## Projet de texte", "total_cost_usd": 0.42},
        )
        res = RE.analyser_journal(journal + ["", "pas du json"])
        self.assertEqual(res["reponse"], "## Projet de texte")
        self.assertEqual(res["cout_usd"], 0.42)
        self.assertTrue(res["skill_chargee"])
        self.assertEqual(res["outils"], ["Skill", "Read"])
        self.assertIsNone(res["erreur"])

    def test_lecture_directe_du_skill_md(self):
        journal = self.lignes({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/p/.claude/skills/legistique-fr/SKILL.md"}}]}})
        self.assertTrue(RE.analyser_journal(journal)["skill_chargee"])

    def test_autre_skill(self):
        journal = self.lignes({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "docx"}}]}})
        self.assertFalse(RE.analyser_journal(journal)["skill_chargee"])

    def test_erreur_de_session(self):
        journal = self.lignes({"type": "result", "subtype": "error_max_budget_usd", "is_error": True, "result": ""})
        self.assertEqual(RE.analyser_journal(journal)["erreur"], "error_max_budget_usd")


class Projet(unittest.TestCase):

    def test_skill_installee_sans_ses_evals(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = RE.preparer_projet(Path(tmp) / "p", True)
            skill = d / ".claude" / "skills" / "legistique-fr"
            self.assertTrue((skill / "SKILL.md").exists())
            self.assertTrue((skill / "scripts" / "lint_legistique.py").exists())
            self.assertFalse((skill / "evals").exists())

    def test_sans_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = RE.preparer_projet(Path(tmp) / "p", False)
            self.assertEqual(list(d.iterdir()), [])

    def test_commande_isolee(self):
        cmd = RE.commande_claude("Bonjour", "claude-opus-5-5", web=False, budget=2.5)
        for attendu in ["-p", "stream-json", "--verbose", "--setting-sources", "project", "--strict-mcp-config",
                        "--no-session-persistence", "--model", "claude-opus-5-5", "--max-budget-usd", "2.5"]:
            self.assertIn(attendu, cmd)
        self.assertNotIn("WebFetch", cmd)
        self.assertIn("WebFetch", RE.commande_claude("Bonjour", None, web=True, budget=None))

    def test_fichiers_produits_et_revisions_word(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = RE.preparer_projet(Path(tmp) / "p", True)
            with zipfile.ZipFile(d / "corrige.docx", "w") as z:
                z.writestr("word/document.xml", '<w:document><w:ins w:id="1"/><w:del w:id="2"/><w:ins w:id="3"/></w:document>')
                z.writestr("word/settings.xml", "<w:settings><w:trackRevisions/></w:settings>")
            (d / "notes.txt").write_text("x", encoding="utf-8")
            fichiers = RE.fichiers_produits(d)
        self.assertEqual([f["chemin"] for f in fichiers], ["corrige.docx", "notes.txt"])
        self.assertEqual((fichiers[0]["insertions"], fichiers[0]["suppressions"], fichiers[0]["suivi_active"]),
                         (2, 1, True))


class FakeClient:
    def __init__(self, message):
        self.message, self.appels = message, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.appels.append(kw)
        return self.message


def message(stop_reason="end_turn", texte=None, stop_details=None):
    contenu = [SimpleNamespace(type="thinking", thinking="")]
    if texte is not None:
        contenu.append(SimpleNamespace(type="text", text=texte))
    return SimpleNamespace(stop_reason=stop_reason, stop_details=stop_details, content=contenu,
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


@unittest.skipUnless(HAS_SDK, "paquet anthropic absent")
class Juge(unittest.TestCase):

    def test_verdicts(self):
        verdicts = {"verdicts": [{"numero": 1, "respecte": True, "justification": "présent"},
                                 {"numero": 2, "respecte": False, "justification": "NOR inventé"}]}
        client = FakeClient(message(texte=json.dumps(verdicts)))
        res, err = RE.juger(client, ev_type(), "réponse", [], "claude-opus-5-5")
        self.assertIsNone(err)
        self.assertEqual([v["respecte"] for v in res["verdicts"]], [True, False])
        appel = client.appels[0]
        self.assertEqual(appel["model"], "claude-opus-5-5")
        self.assertEqual(appel["fallbacks"], "default")
        self.assertIn("server-side-fallback-2026-07-01", appel["betas"])
        self.assertEqual(appel["output_config"]["format"]["schema"], RE.SCHEMA_VERDICTS)
        self.assertNotIn("thinking", appel)
        contenu = appel["messages"][0]["content"]
        self.assertIn("1. Le projet est au présent", contenu)
        self.assertIn("<reponse_de_l_assistant>\nréponse\n</reponse_de_l_assistant>", contenu)

    def test_refus(self):
        client = FakeClient(message(stop_reason="refusal", stop_details=SimpleNamespace(category="cyber")))
        res, err = RE.juger(client, ev_type(), "réponse", [], "claude-opus-5-5")
        self.assertIsNone(res)
        self.assertIn("refus", err)

    def test_nombre_de_verdicts_incoherent(self):
        client = FakeClient(message(texte=json.dumps({"verdicts": [
            {"numero": 1, "respecte": True, "justification": "ok"}]})))
        res, err = RE.juger(client, ev_type(), "réponse", [], "claude-opus-5-5")
        self.assertIsNone(res)
        self.assertIn("1 verdicts pour 2 attentes", err)


class Campagnes(unittest.TestCase):

    def test_simulation_qualite(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            sortie = RE.main(["--simulation", "--ids", "1,14", "--sortie", tmp])
            resultats = json.loads((sortie / "resultats.json").read_text(encoding="utf-8"))
            rapport = (sortie / "rapport.md").read_text(encoding="utf-8")
            self.assertTrue((sortie / "01-prose-vers-decret.md").exists())
        self.assertEqual([e["id"] for e in resultats["evals"]], [1, 14])
        self.assertTrue(resultats["simulation"])
        self.assertIn("simulation", rapport)
        self.assertIn("| 14. question-ponctuelle-abrogation |", rapport)

    def test_simulation_declenchement(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()):
            sortie = RE.main(["--simulation", "--declenchement", "--sortie", tmp])
            resultats = json.loads((sortie / "resultats.json").read_text(encoding="utf-8"))
        self.assertEqual(len(resultats["requetes"]), len(json.loads(RE.DECLENCHEMENT.read_text(encoding="utf-8"))))

    def test_comparaison_avec_une_reference(self):
        args = SimpleNamespace(sans_skill=False, modele=None, juge="j", simulation=False)
        ligne = {"id": 1, "nom": "essai", "skill_chargee": True, "cout_usd": 1.0, "erreur": None, "reussies": 2,
                 "total": 2, "attentes": ["a", "b"], "verdicts": [{"numero": 1, "respecte": True, "justification": ""},
                                                                  {"numero": 2, "respecte": True, "justification": ""}]}
        ref = dict(ligne, reussies=1)
        rapport = RE.rapport_qualite([ligne], args, [ref])
        self.assertIn("| 1. essai | 2/2 | 1/2 | oui | 1.00 |  |", rapport)
        self.assertIn("**Total : 2/2 attentes respectées (100 %)**", rapport)

    def test_mesures_de_declenchement(self):
        args = SimpleNamespace(simulation=False)
        lignes = [{"requete": "a", "attendu": True, "observe": True},
                  {"requete": "b", "attendu": True, "observe": False},
                  {"requete": "c", "attendu": False, "observe": True},
                  {"requete": "d", "attendu": False, "observe": False}]
        _, mesures = RE.rapport_declenchement(lignes, args)
        self.assertEqual(mesures, {"precision": 0.5, "rappel": 0.5})

    def test_identifiant_inconnu(self):
        with self.assertRaises(SystemExit):
            RE.choisir([ev_type()], "1,99")


if __name__ == "__main__":
    unittest.main()
