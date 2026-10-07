"""Tests du fichier Word avec marques de révision (legistique-fr/scripts/redline_docx.py).

Propriété vérifiée : dans le document produit, « Refuser toutes les modifications » redonne le texte
d'origine et « Accepter toutes les modifications » le texte corrigé, paragraphe par paragraphe.
"""
import random
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "legistique-fr" / "scripts" / "redline_docx.py"
sys.path.insert(0, str(SCRIPT.parent))

import redline_docx as R  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def resolve(document_xml, accept):
    """Texte des paragraphes après acceptation (accept=True) ou refus de toutes les révisions."""
    root = ET.fromstring(document_xml)
    paragraphs = []
    for p in root.iter(W + "p"):
        mark = p.find(f"{W}pPr/{W}rPr")
        if mark is not None:
            if accept and mark.find(W + "del") is not None:
                continue
            if not accept and mark.find(W + "ins") is not None:
                continue
        parts = []
        for child in p:
            tag = child.tag
            if tag == W + "r":
                parts.extend(t.text or "" for t in child.iter(W + "t"))
            elif tag == W + "ins" and accept:
                parts.extend(t.text or "" for t in child.iter(W + "t"))
            elif tag == W + "del" and not accept:
                parts.extend(t.text or "" for t in child.iter(W + "delText"))
        paragraphs.append("".join(parts))
    return paragraphs


def produce(original, revise):
    """Lance le script comme un utilisateur et renvoie le contenu du .docx."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        args = [sys.executable, str(SCRIPT), "--revise", str(tmp / "revise.txt"), "--sortie", str(tmp / "out.docx")]
        (tmp / "revise.txt").write_text("\n".join(revise) + "\n", encoding="utf-8")
        if original is not None:
            (tmp / "original.txt").write_text("\n".join(original) + "\n", encoding="utf-8")
            args += ["--original", str(tmp / "original.txt")]
        subprocess.run(args, check=True, capture_output=True)
        with zipfile.ZipFile(tmp / "out.docx") as z:
            return {name: z.read(name).decode("utf-8") for name in z.namelist()}


ORIGINAL = [
    "Décret n° … du … modifiant le décret n° 2015-1689 du 17 décembre 2015",
    "Le Premier ministre,",
    "Vu le décret n° 2015-1689 du 17 décembre 2015 ;",
    "Vu la Constitution ;",
    "Décrète :",
    "Article 1",
    "La commission devra se réunir au moins 2 fois par an.",
    "Ledit président pourra inviter toute personne concernée.",
    "Article 2",
    "Toutes dispositions contraires au présent décret sont abrogées.",
    "Article 3",
    "Le ministre en charge de l'économie est chargé de l'exécution du présent décret.",
]
REVISE = [
    "Décret n° … du … relatif à la commission consultative des usagers",
    "Le Premier ministre,",
    "Vu la Constitution ;",
    "Vu le décret n° 2015-1689 du 17 décembre 2015 ;",
    "Décrète :",
    "Article 1er",
    "La commission se réunit au moins deux fois par an.",
    "Le président peut inviter toute personne dont l'audition lui paraît utile.",
    "Article 2",
    "Le ministre chargé de l'économie est chargé de l'exécution du présent décret.",
]


class RoundTrip(unittest.TestCase):

    def check(self, original, revise):
        files = produce(original, revise)
        doc = files["word/document.xml"]
        self.assertEqual(resolve(doc, accept=True), revise)
        self.assertEqual(resolve(doc, accept=False), original)
        return files

    def test_correction_complete(self):
        self.check(ORIGINAL, REVISE)

    def test_identique(self):
        files = self.check(ORIGINAL, ORIGINAL)
        self.assertNotIn("<w:ins ", files["word/document.xml"])
        self.assertNotIn("<w:del ", files["word/document.xml"])

    def test_insertion_en_tete_et_suppression_en_fin(self):
        self.check(["B", "C", "D"], ["A", "B", "C"])

    def test_tout_remplace(self):
        self.check(["Un texte ancien.", "Un autre."], ["Rien de commun ici", "Ni là", "Ni encore là"])

    def test_paragraphes_deplaces(self):
        self.check(["Article 1", "Texte A.", "Article 2", "Texte B."], ["Article 2", "Texte B.", "Article 1", "Texte A."])

    def test_caracteres_speciaux(self):
        self.check(['Le taux < 5 % & "au moins" > 2.'], ["Le taux < 6 % & « au moins » > 2 ; l'autre."])

    def test_ponctuation_seule(self):
        self.check(["Le ministre, chargé de l'exécution."], ["Le ministre chargé de l'exécution."])

    def test_aleatoire(self):
        """Suppressions, insertions, réécritures et déplacements tirés au hasard (graine fixe)."""
        rng = random.Random(1789)
        mots = ["le", "ministre", "chargé", "de", "la", "santé", "fixe", "liste", "des", "pièces", "annuel",
                "Article", "1er", "2", "décret", "«", "»", ";", ",", "."]
        for _ in range(300):
            original = [" ".join(rng.choices(mots, k=rng.randint(1, 8))) for _ in range(rng.randint(0, 7))]
            revise = list(original)
            for _ in range(rng.randint(0, 4)):
                op = rng.choice("dimr")
                if op == "d" and revise:
                    revise.pop(rng.randrange(len(revise)))
                elif op == "i":
                    revise.insert(rng.randint(0, len(revise)), " ".join(rng.choices(mots, k=rng.randint(1, 8))))
                elif op == "m" and revise:
                    k = rng.randrange(len(revise))
                    w = revise[k].split(" ")
                    w[rng.randrange(len(w))] = rng.choice(mots)
                    revise[k] = " ".join(w)
                elif op == "r" and len(revise) > 1:
                    revise.append(revise.pop(rng.randrange(len(revise))))
            if not revise:
                continue
            doc = R.Doc("Test")
            R.build(doc, original, revise)
            xml = doc.document_xml()
            with self.subTest(original=original, revise=revise):
                self.assertEqual(resolve(xml, accept=True), revise)
                self.assertEqual(resolve(xml, accept=False), original)

    def test_document_propre(self):
        files = produce(None, REVISE)
        self.assertNotIn("<w:ins ", files["word/document.xml"])
        self.assertNotIn("trackRevisions", files["word/settings.xml"])
        self.assertEqual(resolve(files["word/document.xml"], accept=True), REVISE)


class Paquet(unittest.TestCase):

    def test_parties_et_xml_valide(self):
        files = produce(ORIGINAL, REVISE)
        for part in ["[Content_Types].xml", "_rels/.rels", "word/_rels/document.xml.rels", "word/document.xml",
                     "word/styles.xml", "word/settings.xml"]:
            with self.subTest(part=part):
                self.assertIn(part, files)
                ET.fromstring(files[part])  # lève une exception si le XML est mal formé
        self.assertIn("<w:trackRevisions/>", files["word/settings.xml"])

    def test_identifiants_de_revision_uniques(self):
        doc = produce(ORIGINAL, REVISE)["word/document.xml"]
        root = ET.fromstring(doc)
        ids = [el.get(W + "id") for el in root.iter() if el.tag in {W + "ins", W + "del"}]
        self.assertTrue(ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_tetes_d_article_centrees(self):
        doc = produce(None, ["Article 1er", "Le texte."])["word/document.xml"]
        root = ET.fromstring(doc)
        jcs = [p.find(f"{W}pPr/{W}jc").get(W + "val") for p in root.iter(W + "p")]
        self.assertEqual(jcs, ["center", "both"])


class Lecture(unittest.TestCase):

    def test_markdown_retire(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("> **Article 1er**\n\n>   Le texte.  \n\n")
        try:
            self.assertEqual(R.read_lines(f.name), ["Article 1er", "Le texte."])
        finally:
            Path(f.name).unlink()


if __name__ == "__main__":
    unittest.main()
