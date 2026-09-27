"""Tests sans appel reseau : calculs, provenance et lot relu des 11 CV."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.donnees import RACINE, valide_cv, charge_dossier, mention_standard, nom_competence, applique_relecture
from src.evaluation import CRITERES, evalue_cv, totalise, note_maths, points_anglais, contient
from src.pipeline import extrait_pdf, structure_cv, lit_prompt, message_cv, empreinte, ecrit_json, appelle_ollama, normalise_types

EXEMPLES = RACINE / "tests" / "exemples_manuels"


class UnitaireTests(unittest.TestCase):
    def setUp(self):
        self.candidats = charge_dossier(EXEMPLES)
        self.lea = copy.deepcopy(self.candidats[0])

    def test_bornes_et_explications(self):
        self.assertEqual(sum(p for _, p in CRITERES.values()), 20)
        for cv in self.candidats:
            details = evalue_cv(cv)
            self.assertEqual(len(details), 8)
            score, reserve = totalise(details)
            self.assertTrue(0 <= score <= score + reserve <= 20)
            for d in details:
                self.assertTrue(d["faits"] and d["regle"] and d["source"])

    def test_informations_illisibles_non_remplacees_par_zero_certain(self):
        self.lea["rubriques_illisibles"] = ["formation", "competences", "langues", "experiences", "engagements", "international"]
        self.assertEqual(totalise(evalue_cv(self.lea)), (0, 20))

    def test_mention_absente_ne_se_deduit_pas_de_la_moyenne(self):
        self.lea["formation"]["mention_bac"] = None
        detail = evalue_cv(self.lea)[0]
        self.assertEqual((detail["points"], detail["points_a_verifier"]), (0, 6))

    def test_derniere_note_de_maths_meme_si_elle_baisse(self):
        resultats = [{"intitule": "Mathématiques premier trimestre", "note_sur_20": 18},
                     {"intitule": "Mathématiques troisième trimestre", "note_sur_20": 12}]
        self.assertEqual(note_maths(resultats)[0], 12)
        self.assertIsNone(note_maths([{"intitule": "Moyenne générale", "note_sur_20": 19}])[0])

    def test_notes_ambigues_imposent_verification(self):
        self.assertIsNone(note_maths([{"intitule": "Maths", "note_sur_20": 12},
                                     {"intitule": "Maths", "note_sur_20": 18}])[0])

    def test_score_anglais_exige_une_echelle(self):
        anglais = {"langue": "Anglais", "niveau": None, "certification": "TOEFL iBT", "score": "112/120"}
        self.assertEqual(points_anglais([anglais])[:2], (1.5, 0))
        anglais["score"] = "112"
        self.assertEqual(points_anglais([anglais])[:2], (0, 1.5))

    def test_projet_inacheve_et_certification_en_cours(self):
        self.lea["competences"]["projets"] = ["Site web HTML non finalisé"]
        self.lea["competences"]["certifications"] = ["Certification DataCamp SQL en cours"]
        points1 = evalue_cv(self.lea)[2]["points"]
        self.lea["competences"]["projets"] = ["Site web HTML publié"]
        self.lea["competences"]["certifications"] = ["Certification DataCamp SQL obtenue"]
        self.assertEqual(evalue_cv(self.lea)[2]["points"] - points1, 0.5)

    def test_identite_et_nom_lycee_sans_effet_sur_la_note(self):
        avant = totalise(evalue_cv(self.lea))
        self.lea["meta"] = {"id_candidat": "anonyme", "fichier_source": "anonyme.pdf"}
        self.lea["formation"]["etablissement"] = "Autre lycée"
        self.lea["formation"]["anomalies_parcours"] = "Redoublement"
        self.assertEqual(totalise(evalue_cv(self.lea)), avant)

    def test_normalisation_conserve_le_niveau_dans_la_source(self):
        self.assertEqual(nom_competence("Python — bases"), "python")
        self.assertEqual(nom_competence("Python (pandas)"), "python")
        self.assertEqual(mention_standard("Mention Très Bien"), "tres bien")

    def test_types_et_notes_invalides_refuses(self):
        for note in [-1, 21, True, "17.4", float("nan"), float("inf")]:
            with self.subTest(note=note):
                self.lea["formation"]["resultats"][0]["note_sur_20"] = note
                self.assertTrue(valide_cv(self.lea))
        self.assertTrue(valide_cv({"donnees_normalisees": {}}))

    def test_types_equivalents_normalises_sans_inventer(self):
        section = {"experiences": [{"type": "emploi étudiant"}, {"type": "job étudiant"}, {"type": None}]}
        corrections = normalise_types(section)
        self.assertEqual([e["type"] for e in section["experiences"]], ["job_etudiant", "job_etudiant", None])
        self.assertEqual(len(corrections), 2)

    def test_pdf_sans_texte_ne_devient_pas_un_cv_vide(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as temporaire:
            p = Path(temporaire)
            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            writer.write(p / "scan.pdf")
            with self.assertRaisesRegex(ValueError, "OCR"):
                extrait_pdf(p / "scan.pdf", p / "txt")
            self.assertFalse((p / "txt" / "scan.txt").exists())

    def test_doublons_et_lot_vide_refuses(self):
        with tempfile.TemporaryDirectory() as temporaire:
            p = Path(temporaire)
            with self.assertRaises(ValueError):
                charge_dossier(p)
            ecrit_json(p / "a.json", self.lea)
            ecrit_json(p / "b.json", self.lea)
            with self.assertRaisesRegex(ValueError, "en double"):
                charge_dossier(p)

    def test_prompt_ninjecte_ni_bareme_ni_references(self):
        prompt = lit_prompt(RACINE / "prompt.md")
        message = message_cv(prompt, "CV contenant {id_candidat}", "test", "langues")
        self.assertIn("CV contenant {id_candidat}", message)
        self.assertNotIn("notes-reference", message)
        self.assertNotIn("total_sur20", message)

    def test_cache_modele_et_invalidations(self):
        with tempfile.TemporaryDirectory() as temporaire:
            p = Path(temporaire)
            entree = {"pdf": Path("01_lea_vasseur.pdf"), "texte": "texte", "texte_sha256": empreinte("texte"), "pdf_sha256": "pdf"}
            def reponse(message, modele, adresse, schema):
                cle = next(iter(schema["properties"]))
                return {"message": {"content": json.dumps({cle: self.lea[cle]})}}
            appel = Mock(side_effect=reponse)
            prompt = lit_prompt(RACINE / "prompt.md")
            cv, _ = structure_cv(entree, p, prompt, appel=appel)
            self.assertEqual(appel.call_count, 6)
            self.assertEqual(cv, self.lea)
            structure_cv(entree, p, prompt, autoriser_generation=False, appel=appel)
            self.assertEqual(appel.call_count, 6)
            with self.assertRaisesRegex(ValueError, "cache absent"):
                structure_cv(entree, p, prompt + "\n", autoriser_generation=False)
            cv["formation"]["mention_bac"] = "Bien"
            ecrit_json(p / "json" / "01_lea_vasseur.json", cv)
            with self.assertRaisesRegex(ValueError, "cache absent"):
                structure_cv(entree, p, prompt, autoriser_generation=False)

    def test_json_invalide_ne_devient_pas_un_resultat(self):
        with tempfile.TemporaryDirectory() as temporaire:
            p = Path(temporaire)
            entree = {"pdf": Path("test.pdf"), "texte": "texte", "texte_sha256": "txt", "pdf_sha256": "pdf"}
            appel = Mock(return_value={"message": {"content": "{invalide"}})
            with self.assertRaisesRegex(ValueError, "format refuse"):
                structure_cv(entree, p, lit_prompt(RACINE / "prompt.md"), appel=appel)
            self.assertFalse((p / "json" / "test.json").exists())
            self.assertEqual(appel.call_count, 2)

    def test_reprise_apres_une_reponse_incomplete(self):
        with tempfile.TemporaryDirectory() as temporaire:
            entree = {"pdf": Path("01_lea_vasseur.pdf"), "texte": "Texte de test", "texte_sha256": "txt", "pdf_sha256": "pdf"}
            appels = []
            def reponse(message, modele, adresse, schema):
                cle = next(iter(schema["properties"]))
                appels.append(cle)
                if len(appels) == 1:
                    raise RuntimeError("Le flux ne contient aucun objet JSON complet")
                return {"message": {"content": json.dumps({cle: self.lea[cle]})}}
            cv, _ = structure_cv(entree, temporaire, lit_prompt(RACINE / "prompt.md"), appel=reponse)
            self.assertEqual(cv, self.lea)
            self.assertEqual(appels.count("formation"), 2)

    def test_flux_ollama_arrete_des_que_le_json_est_complet(self):
        reponse = Mock()
        reponse.__enter__ = Mock(return_value=reponse)
        reponse.__exit__ = Mock(return_value=False)
        def lignes():
            yield json.dumps({"message": {"content": '{"international":'}}).encode()
            yield json.dumps({"message": {"content": '[]}'}}).encode()
            raise AssertionError("Le code ne doit pas attendre les espaces emis apres le JSON.")
        reponse.iter_lines.side_effect = lignes
        with patch("src.pipeline.requests.post", return_value=reponse):
            resultat = appelle_ollama("Texte test", "modele-test")
        self.assertEqual(json.loads(resultat["message"]["content"]), {"international": []})
        self.assertEqual(resultat["arret"], "objet_json_complet")

    def test_flux_tronque_refuse(self):
        reponse = Mock()
        reponse.__enter__ = Mock(return_value=reponse)
        reponse.__exit__ = Mock(return_value=False)
        reponse.iter_lines.return_value = [json.dumps({"message": {"content": '{"formation":'}, "done": True}).encode()]
        with patch("src.pipeline.requests.post", return_value=reponse):
            with self.assertRaisesRegex(RuntimeError, "aucun objet JSON complet"):
                appelle_ollama("Texte test", "modele-test")

    def test_corrections_tracees_et_relecture_perimee(self):
        with tempfile.TemporaryDirectory() as temporaire:
            p = Path(temporaire)
            brut = p / "json" / "01_lea_vasseur.json"
            ecrit_json(brut, self.lea)
            revue = {"json_sha256": empreinte(brut.read_bytes()), "texte_sha256": empreinte("Texte : Mention Bien"),
                     "corrections": [{"chemin": ["formation", "mention_bac"], "avant": "Très Bien", "apres": "Bien",
                                      "raison": "Copie de la mention", "extraits_source": ["Mention Bien"]}]}
            ecrit_json(p / "relectures.json", {"01_lea_vasseur": revue})
            cv, statut, _ = applique_relecture(self.lea, "Texte : Mention Bien", p)
            self.assertEqual(cv["formation"]["mention_bac"], "Bien")
            self.assertEqual(self.lea["formation"]["mention_bac"], "Très Bien")
            self.assertEqual(statut, "relu avec corrections")
            with self.assertRaisesRegex(ValueError, "perimee"):
                applique_relecture(self.lea, "Texte modifié", p)
            revue["corrections"][0]["extraits_source"] = ["Citation inventée"]
            ecrit_json(p / "relectures.json", {"01_lea_vasseur": revue})
            with self.assertRaisesRegex(ValueError, "citation"):
                applique_relecture(self.lea, "Texte : Mention Bien", p)


class LotReelTests(unittest.TestCase):
    def test_onze_pdf_et_json_reels_relus(self):
        attendus = json.loads((RACINE / "tests" / "attendus_cv.json").read_text())
        self.assertEqual(len(attendus), 11)
        provenance = json.loads((RACINE / "sorties" / "provenance.json").read_text())
        with tempfile.TemporaryDirectory() as temporaire:
            for identifiant, attendu in attendus.items():
                with self.subTest(candidat=identifiant):
                    pdf = RACINE / "cv-test" / f"{identifiant}.pdf"
                    entree = extrait_pdf(pdf, temporaire)
                    brut, statut = structure_cv(entree, RACINE / "sorties", lit_prompt(RACINE / "prompt.md"), autoriser_generation=False)
                    self.assertEqual(statut, "cache modele verifie")
                    self.assertEqual(len(provenance[identifiant]["appels"]), 6)
                    cv, relecture, _ = applique_relecture(brut, entree["texte"], RACINE / "sorties")
                    self.assertNotEqual(relecture, "non relu")
                    self.assertEqual(mention_standard(cv["formation"]["mention_bac"]), attendu["mention"])
                    self.assertEqual(sorted({nom_competence(x) for x in cv["competences"]["langages"]}), sorted(attendu["langages"]))
                    self.assertEqual(sum(e["type"] == "stage" for e in cv["experiences"]), attendu["stages"])
                    maths = sorted(r["note_sur_20"] for r in cv["formation"]["resultats"] if contient(r["intitule"], r"\bmath(?:s|ematiques)?\b") and r["note_sur_20"] is not None)
                    self.assertEqual(maths, sorted(attendu["notes_maths"]))
                    score, reserve = totalise(evalue_cv(cv))
                    self.assertTrue(0 <= score <= score + reserve <= 20)


if __name__ == "__main__":
    unittest.main()
