"""Tests de scripts/evals_agents.py (préparation et rapport), sans appel à un modèle."""
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import evals_agents as EA  # noqa: E402


class Preparer(unittest.TestCase):

    def test_campagne_version_courante(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(ids="1,2", versions="courante", modele_agent="sonnet", sortie=tmp)
            with redirect_stdout(StringIO()):
                dossier = EA.preparer(args)
            skill = dossier / "skills" / "courante" / "legistique-fr"
            self.assertTrue((skill / "SKILL.md").exists())
            self.assertFalse((skill / "evals").exists(), "les attentes ne doivent pas être visibles de l'agent")
            campagne = json.loads((dossier / "consignes.json").read_text(encoding="utf-8"))
            self.assertEqual([t["id"] for t in campagne["taches"]], [1, 2])
            for t in campagne["taches"]:
                self.assertTrue(Path(t["reponse"]).is_absolute())
                self.assertIn(str(skill), t["consigne"])
                self.assertIn(t["reponse"], t["consigne"])
                self.assertTrue((dossier / "enonces" / f"{t['id']:02d}.txt").exists())


class Rapport(unittest.TestCase):

    def test_tableau_et_attentes_manquees(self):
        campagne = {"versions": ["v0", "courante"], "ids": [1], "modele_agent": "sonnet"}
        lignes = [
            {"version": "v0", "id": 1, "nom": "essai", "total": 2, "attentes": ["A", "B"], "reussies": 1,
             "verdicts": [{"numero": 1, "respecte": True, "justification": "ok"},
                          {"numero": 2, "respecte": False, "justification": "manque B"}]},
            {"version": "courante", "id": 1, "nom": "essai", "total": 2, "attentes": ["A", "B"],
             "erreur": "réponse absente"},
        ]
        texte = EA.rapport(campagne, lignes, "juge")
        self.assertIn("| 1. essai | 1/2 | réponse absente |", texte)
        self.assertIn("manque B", texte)
        self.assertIn("**1/2** (50 %)", texte)


if __name__ == "__main__":
    unittest.main()
