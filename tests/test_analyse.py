"""Verification des comptages, des donnees inconnues et du pipeline sans API."""

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from analyse.agrege import construit_tables
from analyse.donnees import RACINE, charge_dossier, valide_cv
from extraction import pipeline

EXEMPLES = RACINE / "analyse" / "exemples"


class AnalyseTests(unittest.TestCase):
    def setUp(self):
        self.candidats = charge_dossier(EXEMPLES)
        self.lea = copy.deepcopy(self.candidats[0])

    def test_comptages_des_trois_exemples(self):
        tableau, codes = construit_tables(self.candidats)
        tableau = tableau.set_index("id_candidat")
        attentes = {
            "01_lea_vasseur": [2, 1, 1, 0, 2, 1],
            "04_hugo_lefebvre": [0, 0, 1, 1, 2, 0],
            "10_kevin_dubreuil": [0, 0, 0, 0, 0, 0],
        }
        colonnes = ["nb_langages", "nb_projets", "nb_stages", "nb_jobs_etudiants", "nb_engagements", "nb_sejours"]
        for identifiant, attendu in attentes.items():
            with self.subTest(candidat=identifiant):
                self.assertEqual(tableau.loc[identifiant, colonnes].tolist(), attendu)
        self.assertEqual(tableau.loc["01_lea_vasseur", "mention_bac"], "tres bien")
        self.assertEqual(codes[codes["champ"] == "langages"]["code"].tolist(), ["python", "sql"])

    def test_competences_repetees_comptees_une_seule_fois(self):
        self.lea["competences"]["langages"] += [" PYTHON ", "Sql"]
        self.lea["formation"]["specialites"] += ["mathematiques"]
        tableau, codes = construit_tables([self.lea])
        self.assertEqual(tableau.loc[0, "nb_langages"], 2)
        self.assertEqual(tableau.loc[0, "nb_specialites"], 3)
        self.assertEqual(len(codes[codes["champ"] == "langages"]), 2)

    def test_rubriques_illisibles_exclues_des_indicateurs(self):
        self.lea["rubriques_illisibles"] = ["formation", "competences", "experiences", "langues", "engagements", "international"]
        tableau, codes = construit_tables([self.lea, self.candidats[-1]])
        for colonne in tableau.columns:
            if colonne.startswith("nb_") or colonne == "mention_bac":
                self.assertTrue(pd.isna(tableau.loc[0, colonne]), colonne)
        self.assertFalse((codes["id_candidat"] == "01_lea_vasseur").any())
        # Le CV lisible sans experience garde zero et reste dans la moyenne.
        self.assertEqual(tableau["nb_stages"].dropna().tolist(), [0])

    def test_type_experience_inconnu_ne_devient_pas_zero(self):
        self.lea["experiences"][0]["type"] = None
        tableau, _ = construit_tables([self.lea])
        self.assertEqual(tableau.loc[0, "nb_experiences"], 1)
        self.assertTrue(pd.isna(tableau.loc[0, "nb_stages"]))
        self.assertTrue(pd.isna(tableau.loc[0, "nb_jobs_etudiants"]))

    def test_notes_invalides_refusees(self):
        for note in [-1, 21, True, "17.4", float("nan"), float("inf")]:
            with self.subTest(note=note):
                self.lea["formation"]["resultats"][0]["note_sur_20"] = note
                self.assertTrue(valide_cv(self.lea))

    def test_champs_manquants_et_lignes_vides_refuses(self):
        del self.lea["formation"]
        self.assertTrue(valide_cv(self.lea))
        cv = copy.deepcopy(self.candidats[0])
        cv["experiences"] = [{cle: None for cle in cv["experiences"][0]}]
        self.assertTrue(valide_cv(cv))
        self.assertIn("Ancien format", valide_cv({"donnees_normalisees": {}})[0])

    def test_doublons_de_candidat_ou_de_source_refuses(self):
        for cle in ["id_candidat", "fichier_source"]:
            with self.subTest(cle=cle), tempfile.TemporaryDirectory() as temporaire:
                dossier = Path(temporaire)
                copie = copy.deepcopy(self.lea)
                copie["meta"][cle] = "autre.pdf" if cle == "fichier_source" else "autre"
                for nom, cv in [("a", self.lea), ("b", copie)]:
                    (dossier / f"{nom}.json").write_text(json.dumps(cv), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "en double"):
                    charge_dossier(dossier)

    def test_aucun_fichier_invalide_ignore(self):
        with tempfile.TemporaryDirectory() as temporaire:
            dossier = Path(temporaire)
            with self.assertRaisesRegex(ValueError, "Aucun JSON"):
                charge_dossier(dossier)
            (dossier / "valide.json").write_text(json.dumps(self.lea), encoding="utf-8")
            (dossier / "invalide.json").write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalide.json"):
                charge_dossier(dossier)

    def test_gabarit_du_prompt_valide_et_listes_vides(self):
        prompt = pipeline.prompt_depuis_markdown(RACINE / "prompt.md")
        message = pipeline.construit_message({"prompt": prompt, "donnees_extraites": "Texte CV", "id_candidat": "test", "fichier_source": "test.pdf"})
        cv, _ = json.JSONDecoder().raw_decode(message[message.index("{"):])
        self.assertEqual(valide_cv(cv), [])
        tableau, codes = construit_tables([cv])
        self.assertEqual(tableau.loc[0, "nb_stages"], 0)
        self.assertTrue(pd.isna(tableau.loc[0, "mention_bac"]))
        self.assertTrue(codes.empty)

    def test_accolades_du_cv_ne_sont_pas_des_variables(self):
        message = pipeline.construit_message({"prompt": "{donnees_extraites} / {id_candidat}", "donnees_extraites": "Un projet {id_candidat}", "id_candidat": "test"})
        self.assertEqual(message, "Un projet {id_candidat} / test")

    def test_pipeline_valide_avant_enregistrement(self):
        for reponse_valide in [True, False]:
            with self.subTest(valide=reponse_valide), tempfile.TemporaryDirectory() as temporaire:
                dossier = Path(temporaire)
                sorties = dossier / "sorties"
                (dossier / "source.txt").write_text("CV de test", encoding="utf-8")
                chaine = Mock()
                chaine.batch.return_value = [json.dumps(self.lea if reponse_valide else {"experiences": []})]
                argv = ["pipeline.py", str(dossier), "-o", str(sorties)]
                with patch.object(sys, "argv", argv), patch.object(pipeline, "construit_chaine", return_value=chaine), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    resultat = pipeline.main()
                self.assertEqual(resultat, 0 if reponse_valide else 1)
                self.assertEqual((sorties / "source.json").exists(), reponse_valide)
                if reponse_valide:
                    cv = charge_dossier(sorties)[0]
                    self.assertEqual(cv["meta"], {"id_candidat": "source", "fichier_source": "source.pdf"})
                else:
                    self.assertTrue((sorties / "source.brut.txt").exists())

    def test_reponse_liste_refusee_meme_avec_un_seul_cv(self):
        reponse = "```json\n" + json.dumps([self.lea]) + "\n```"
        self.assertTrue(valide_cv(json.loads(pipeline.nettoie_json(reponse))))

    def test_ancien_json_signale_avant_tout_appel_api(self):
        with tempfile.TemporaryDirectory() as temporaire:
            dossier = Path(temporaire)
            (dossier / "cv.txt").write_text("CV test", encoding="utf-8")
            (dossier / "cv.json").write_text('{"donnees_normalisees": {}}', encoding="utf-8")
            argv = ["pipeline.py", str(dossier), "-o", str(dossier)]
            with patch.object(sys, "argv", argv), patch.object(pipeline, "construit_chaine") as chaine, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(pipeline.main(), 1)
            chaine.assert_not_called()

    def test_commandes_completes_sur_les_exemples(self):
        with tempfile.TemporaryDirectory() as temporaire:
            commandes = [
                ["analyse/controle_coherence.py", str(EXEMPLES)],
                ["analyse/agrege.py", str(EXEMPLES), "-o", temporaire],
                ["analyse/stats.py", "-d", temporaire],
            ]
            for commande in commandes:
                resultat = subprocess.run([sys.executable, *commande], cwd=RACINE, capture_output=True, text=True)
                self.assertEqual(resultat.returncode, 0, resultat.stdout + resultat.stderr)
            self.assertIn("3/3 CV", resultat.stdout)
            tableau = pd.read_csv(Path(temporaire) / "candidats.csv")
            self.assertEqual(len(tableau), 3)
            self.assertEqual(tableau["nb_stages"].sum(), 2)


if __name__ == "__main__":
    unittest.main()
