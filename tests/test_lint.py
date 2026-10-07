"""Tests du contrôle automatique (legistique-fr/scripts/lint_legistique.py).

Lancer depuis la racine du dépôt : python3 -m unittest discover tests
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "legistique-fr" / "scripts" / "lint_legistique.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPT.parent))

import lint_legistique as L  # noqa: E402


def run(*args, stdin=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", check=True).stdout


def regles(text, structure=True):
    found = L.lint(text) + (L.structure(text) if structure else [])
    return [f["regle"] for f in found]


class Fixtures(unittest.TestCase):
    """Chaque fixture produit exactement les constats relus et consignés dans attendu.json."""

    def test_fixtures(self):
        attendu = json.loads((FIXTURES / "attendu.json").read_text(encoding="utf-8"))
        self.assertTrue(attendu)
        for name, expected in attendu.items():
            with self.subTest(fixture=name):
                found = json.loads(run(str(FIXTURES / name), "--json"))
                self.assertEqual(sorted(f"{f['ligne']}:{f['regle']}" for f in found), expected)

    def test_toutes_les_fixtures_ont_un_attendu(self):
        attendu = json.loads((FIXTURES / "attendu.json").read_text(encoding="utf-8"))
        fichiers = {p.name for p in FIXTURES.iterdir() if p.suffix in {".txt", ".md"}}
        self.assertEqual(fichiers, set(attendu))


class FauxPositifs(unittest.TestCase):
    """Ce qui est d'usage dans un texte normatif ne doit pas être signalé."""

    def assertClean(self, text):
        self.assertEqual(L.lint(text) + L.structure(text), [], text)

    def test_mots_cites_du_texte_en_vigueur(self):
        self.assertClean("Au premier alinéa, les mots : « devra transmettre » sont remplacés par les mots : "
                         "« transmet ».")

    def test_formule_de_publication(self):
        self.assertClean("Le ministre de l'intérieur est chargé de l'exécution du présent décret, qui sera "
                         "publié au Journal officiel de la République française.")

    def test_vise_et_notamment_dans_les_visas(self):
        self.assertClean("Vu le code de l'environnement, notamment le texte visé à son article L. 120-1 ;")

    def test_articles_de_code_et_chiffres_romains(self):
        self.assertClean("Le I de l'article L. 731-1-1 et l'article LO 111-7-1 sont applicables.")

    def test_titre_en_capitales(self):
        self.assertClean("TITRE II\nDISPOSITIONS TRANSITOIRES ET FINALES")

    def test_nombres_de_cent_et_plus(self):
        self.assertClean("Le seuil est fixé à 250 salariés et le délai à cent vingt jours.")

    def test_heure_et_url(self):
        self.assertClean("Le texte peut être consulté sur le site https://www.legifrance.gouv.fr à 10:30.")

    def test_article_1er(self):
        self.assertClean("Article 1er\n\nL'article 1er du décret du 5 janvier 2010 susvisé est abrogé.")


class Detections(unittest.TestCase):
    """Une règle par cas : le constat attendu est produit."""

    cas = {
        "futur": "Les entreprises transmettront le bilan.",
        "doit": "Les entreprises doivent transmettre le bilan.",
        "et-ou": "Le bilan est transmis et/ou publié.",
        "le-ou-les": "Le ou les représentants sont désignés.",
        "ledit": "Ledit bilan est publié.",
        "vise": "Les entreprises visées à l'article 2 publient leur bilan.",
        "en-charge": "Le ministre en charge de la santé fixe la liste.",
        "anglicisme": "Les mesures impactent les entreprises.",
        "latin": "Le bilan est publié in fine sur le site.",
        "dispositions-contraires": "Toutes dispositions contraires sont abrogées.",
        "renvoi-modalites": "Un arrêté fixe les modalités d'application du présent décret.",
        "date-par-arrete": "Le présent décret entre en vigueur à une date fixée par arrêté.",
        "alinea-chiffre": "A l'alinéa 2 de l'article 3, le mot : « annuel » est supprimé.",
        "duree-chiffres": "Les membres sont nommés pour 3 ans.",
        "guillemets-droits": 'Le mot "annuel" est supprimé.',
        "sigle": "Le bilan est transmis à l'ADEME.",
        "jorf": "Il est publié au JORF.",
        "renvoi-relatif": "Les dispositions de l'alinéa précédent sont applicables.",
        "article-1": "Article 1\n\nLe bilan est publié.",
    }

    def test_detections(self):
        for regle, text in self.cas.items():
            with self.subTest(regle=regle):
                self.assertIn(regle, regles(text, structure=False))

    def test_notamment_bloquant_pres_d_une_sanction(self):
        found = [f for f in L.lint("Est puni de l'amende le fait notamment de ne pas publier le bilan.")
                 if f["regle"] == "notamment"]
        self.assertEqual([f["gravite"] for f in found], ["B"])

    def test_notamment_style_ailleurs(self):
        found = [f for f in L.lint("Le bilan comporte notamment le kilométrage.") if f["regle"] == "notamment"]
        self.assertEqual([f["gravite"] for f in found], ["S"])

    def test_alinea_en_chiffres_dans_le_chapeau_d_un_amendement(self):
        text = ("AMENDEMENT n° …\n\nARTICLE 3\n\nAprès l'alinéa 4, insérer l'alinéa suivant :\n« … ».\n\n"
                "Alinéa 7\nRédiger ainsi cet alinéa :\n« Au deuxième alinéa de l'article L. 1, le mot : « a » est "
                "supprimé. »\n\nEXPOSÉ SOMMAIRE\nCet amendement précise l'alinéa 2 de l'article.")
        found = [(f["ligne"], f["regle"]) for f in L.lint(text) if f["regle"] == "alinea-chiffre"]
        self.assertEqual(found, [(13, "alinea-chiffre")])

    def test_date_bornee_acceptee(self):
        self.assertNotIn("date-par-arrete", regles(
            "La présente loi entre en vigueur à une date fixée par décret, et au plus tard le 1er janvier 2028."))


class Structure(unittest.TestCase):

    DECRET = ("Le Premier ministre,\n{visas}\nDécrète :\n\n{articles}")
    EXEC = "Le ministre de l'intérieur est chargé de l'exécution du présent décret."

    def decret(self, articles, visas="Vu la Constitution ;"):
        body = "\n\n".join(f"Article {'1er' if i == 1 else i}\n\n{a}" for i, a in enumerate(articles, 1))
        return self.DECRET.format(visas=visas, articles=body)

    def test_decret_minimal_propre(self):
        self.assertEqual(L.structure(self.decret(["Le bilan est publié.", self.EXEC])), [])

    def test_execution_absente(self):
        self.assertIn("structure-execution-absente", regles(self.decret(["Le bilan est publié."])))

    def test_execution_sur_plusieurs_lignes(self):
        text = self.decret(["Le bilan est publié.", "Le ministre de l'intérieur et la ministre de la santé "
                            "sont chargés, chacun en ce qui le\nconcerne, de l'exécution du présent décret."])
        self.assertEqual(L.structure(text), [])

    def test_entree_en_vigueur_apres_execution(self):
        text = self.decret(["Le bilan est publié.", self.EXEC, "Le présent décret entre en vigueur le 1er janvier 2027."])
        self.assertIn("structure-vigueur-apres-execution", regles(text))
        self.assertIn("structure-execution-place", regles(text))

    def test_disposition_inseree_sur_l_entree_en_vigueur_ignoree(self):
        text = self.decret(["Après l'article 3 du décret du 5 janvier 2010 susvisé, il est inséré un article 3-1 "
                            "ainsi rédigé :\n« Art. 3-1. – Le présent article entre en vigueur le 1er mars. »",
                            self.EXEC], visas="Vu le décret n° 2010-12 du 5 janvier 2010 relatif aux pilotes ;")
        self.assertEqual(L.structure(text), [])

    def test_numerotation(self):
        text = "Le Premier ministre,\nDécrète :\n\nArticle 1er\n\nA.\n\nArticle 3\n\n" + self.EXEC
        self.assertIn("structure-numerotation", regles(text))

    def test_article_unique_et_autres(self):
        text = "Le Premier ministre,\nDécrète :\n\nArticle unique\n\nA.\n\nArticle 2\n\n" + self.EXEC
        self.assertIn("structure-article-unique", regles(text))

    def test_ordre_des_visas(self):
        visas = "Vu le décret n° 2010-12 du 5 janvier 2010 relatif aux pilotes ;\nVu le code des transports ;"
        self.assertIn("structure-ordre-visas", regles(self.decret([self.EXEC], visas)))

    def test_codes_par_ordre_alphabetique_du_nom(self):
        visas = "Vu le code de l'environnement ;\nVu le code pénal ;\nVu le code de la sécurité sociale ;"
        self.assertEqual(L.structure(self.decret([self.EXEC], visas)), [])

    def test_consultations_apres_les_textes_puis_conseil_d_etat(self):
        visas = ("Vu la Constitution ;\nVu le code des transports ;\nVu l'avis du conseil en date du 3 mars 2026 ;\n"
                 "Le Conseil d'Etat (section des travaux publics) entendu,")
        self.assertEqual(L.structure(self.decret([self.EXEC], visas)), [])

    def test_susvise_absent_des_visas(self):
        text = self.decret(["L'article 2 du décret du 12 mars 2018 susvisé est abrogé.", self.EXEC])
        self.assertIn("structure-susvise-absent", regles(text))

    def test_susvise_present_dans_les_visas(self):
        text = self.decret(["L'article 2 du décret du 5 janvier 2010 susvisé est abrogé.", self.EXEC],
                           visas="Vu le décret n° 2010-12 du 5 janvier 2010 relatif aux pilotes ;")
        self.assertEqual(L.structure(text), [])

    def test_susvise_code(self):
        text = self.decret(["L'article R. 1 du code des transports susvisé est abrogé.", self.EXEC])
        self.assertIn("structure-susvise-code", regles(text))

    def test_susvise_ambigu(self):
        visas = ("Vu le décret n° 2010-12 du 5 janvier 2010 relatif aux pilotes ;\n"
                 "Vu le décret n° 2019-1250 du 28 novembre 2019 relatif aux ports ;")
        text = self.decret(["L'article 2 du décret susvisé est abrogé.", self.EXEC], visas)
        self.assertIn("structure-susvise-ambigu", regles(text))

    def test_double_modification_entre_articles(self):
        text = self.decret(["A l'article R. 1 du code des transports, le mot : « a » est supprimé.",
                            "L'article R. 1 du code des transports est complété par les mots : « b ».", self.EXEC])
        self.assertIn("structure-double-modification", regles(text))

    def test_insertion_apres_un_article_modifie_n_est_pas_une_double_modification(self):
        text = self.decret(["A l'article R. 1 du code des transports, le mot : « a » est supprimé.",
                            "Après l'article R. 1 du code des transports, il est inséré un article R. 1-1 ainsi "
                            "rédigé :\n« Art. R. 1-1. – Texte. »", self.EXEC])
        self.assertEqual(L.structure(text), [])

    def test_meme_numero_dans_deux_codes(self):
        text = self.decret(["A l'article R. 1 du code des transports, le mot : « a » est supprimé.",
                            "A l'article R. 1 du code de l'environnement, le mot : « a » est supprimé.", self.EXEC])
        self.assertEqual(L.structure(text), [])

    def test_loi(self):
        text = ("Projet de loi relatif à l'insertion\n\nVu la Constitution ;\n\nArticle 1er\n\nLa présente loi "
                "entre en vigueur le 1er janvier 2027.\n\nArticle 2\n\nLe ministre est chargé de l'exécution "
                "de la présente loi.")
        self.assertEqual(sorted(regles(text)), ["structure-loi-execution", "structure-loi-visas"])


class Markdown(unittest.TestCase):

    def test_blocs_de_code(self):
        found = json.loads(run(str(FIXTURES / "reponse.md"), "--json"))
        self.assertTrue(all(f["ligne"] == 19 for f in found))

    def test_lignes_citees(self):
        text = "Commentaire : le texte devra changer.\n\n> Article 1er\n>\n> Les entreprises transmettront."
        found = L.lint(L.markdown_lintable(text))
        self.assertEqual([(f["ligne"], f["regle"]) for f in found], [(5, "futur")])

    def test_sans_bloc_ni_citation(self):
        text = "# Titre\n\n| a | b |\n|---|---|\n\nLes entreprises transmettront."
        found = L.lint(L.markdown_lintable(text))
        self.assertEqual([(f["ligne"], f["regle"]) for f in found], [(6, "futur")])

    def test_option_explicite_sur_entree_standard(self):
        found = json.loads(run("-", "--json", "--markdown", stdin="# Doit\n\n```\nIl sera fait.\n```\n"))
        self.assertEqual([f["regle"] for f in found], ["futur"])


class References(unittest.TestCase):

    def test_extraction(self):
        text = ("Vu le code pénal, notamment son article R. 610-1 ;\nVu le décret n° 2015-1689 du 17 décembre 2015 ;\n"
                "Vu le règlement (UE) 2016/679 ;\nCE, Ass., 9 février 1990, Elections municipales de Lifou.")
        refs = [r["reference"] for r in L.references(text)]
        self.assertIn("R. 610-1", refs)
        self.assertIn("décret n° 2015-1689 du 17 décembre 2015", refs)
        self.assertIn("règlement (UE) 2016/679", refs)
        self.assertTrue(any(r.startswith("CE") and "1990" in r for r in refs))

    def test_origine(self):
        projet = FIXTURES / "decret-propre.txt"
        demande = ROOT / "tests" / "fixtures" / "attendu.json"  # ne contient aucune référence
        found = json.loads(run(str(projet), "--refs", "--json", "--source", str(demande)))
        self.assertTrue(found)
        self.assertTrue(all(r["origine"] == "ajoutée" for r in found))
        found = json.loads(run(str(projet), "--refs", "--json", "--source", str(projet)))
        self.assertTrue(all(r["origine"] == "fournie" for r in found))


if __name__ == "__main__":
    unittest.main()
