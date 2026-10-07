"""Cohérence du paquet de la skill : en-tête de SKILL.md, fichiers référencés, fiches citées, evals."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "legistique-fr"
GUIDE = SKILL / "references" / "guide"
sys.path.insert(0, str(SKILL / "scripts"))

import lint_legistique as L  # noqa: E402


def frontmatter():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "en-tête YAML absent"
    head = m.group(1)
    name = re.search(r"^name: (.+)$", head, re.M).group(1).strip()
    desc = re.search(r"^description: >-\n((?:  .*\n?)+)", head, re.M).group(1)
    return name, " ".join(desc.split()), head


def fiches_du_guide():
    ids = set()
    for p in GUIDE.glob("*.md"):
        m = re.match(r"^(\d+(?:\.\d+)+)-", p.name)
        if m:
            ids.add(m.group(1))
    return ids


class EnTete(unittest.TestCase):

    def test_nom(self):
        name, _, _ = frontmatter()
        self.assertEqual(name, SKILL.name)
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)

    def test_description(self):
        _, desc, _ = frontmatter()
        self.assertLessEqual(len(desc), 1024, "la description dépasse 1 024 caractères")
        for mot in ["rédige", "corrige", "amendement", "exposé des motifs"]:
            self.assertIn(mot, desc)

    def test_version(self):
        _, _, head = frontmatter()
        self.assertRegex(head, r'version: "\d+\.\d+\.\d+"')


class Fichiers(unittest.TestCase):

    def test_chemins_cites_dans_skill_md(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        chemins = set(re.findall(r"`((?:references|scripts|evals)/[^`\s]+)`", text))
        self.assertTrue(chemins)
        for c in chemins:
            with self.subTest(chemin=c):
                self.assertTrue((SKILL / c.rstrip("/")).exists(), c)

    def test_fiches_de_synthese_listees(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for p in (SKILL / "references").glob("*.md"):
            with self.subTest(fichier=p.name):
                self.assertIn(f"references/{p.name}", text, "fiche de synthèse absente du tableau des références")

    def test_fiches_citees_existent(self):
        ids = fiches_du_guide()
        sources = [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md")]
        for src in sources:
            text = src.read_text(encoding="utf-8")
            for groupe in re.findall(r"\bfiches? ((?:\d+(?:\.\d+)+(?:,| et| à|\s)*)+)", text):
                for fiche in re.findall(r"\d+(?:\.\d+)+", groupe):
                    with self.subTest(source=src.name, fiche=fiche):
                        self.assertIn(fiche, ids)

    def test_fiches_des_regles_du_controle(self):
        ids = fiches_du_guide() | {"annexe typo"}
        for rid, _, _, fiche, grav, _ in L.RULES:
            with self.subTest(regle=rid):
                self.assertIn(fiche, ids)
                self.assertIn(grav, {"B", "R", "S"})


class Evals(unittest.TestCase):

    def test_evals(self):
        data = json.loads((SKILL / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(data["skill_name"], SKILL.name)
        ids = [e["id"] for e in data["evals"]]
        self.assertEqual(ids, list(range(1, len(ids) + 1)))
        noms = [e["name"] for e in data["evals"]]
        self.assertEqual(len(noms), len(set(noms)))
        for e in data["evals"]:
            with self.subTest(eval=e["name"]):
                self.assertTrue(e["prompt"].strip())
                self.assertTrue(e["expectations"])
                for f in e.get("files", []):
                    self.assertTrue((SKILL / "evals" / f).exists(), f)

    def test_declenchement(self):
        data = json.loads((SKILL / "evals" / "declenchement.json").read_text(encoding="utf-8"))
        self.assertTrue(any(c["doit_declencher"] for c in data))
        self.assertTrue(any(not c["doit_declencher"] for c in data))
        for c in data:
            self.assertEqual(set(c), {"requete", "doit_declencher"})


if __name__ == "__main__":
    unittest.main()
