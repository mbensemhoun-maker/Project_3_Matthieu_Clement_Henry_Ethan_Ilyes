"""Calcule en Python les indicateurs du JSON court et exporte deux CSV.

Le notebook analyse_cv.ipynb montre ces memes boucles avec des explications.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__:
    from .donnees import RACINE, charge_dossier, mention_standard, valeurs_uniques
else:
    from donnees import RACINE, charge_dossier, mention_standard, valeurs_uniques


def construit_tables(candidats):
    lignes, codes = [], []
    for cv in candidats:
        illisibles = cv["rubriques_illisibles"]
        ligne = {"id_candidat": cv["meta"]["id_candidat"], "fichier_source": cv["meta"]["fichier_source"]}
        ligne["mention_bac"] = None if "formation" in illisibles else mention_standard(cv["formation"]["mention_bac"])
        ligne["nb_specialites"] = None if "formation" in illisibles else len(valeurs_uniques(cv["formation"]["specialites"]))
        for champ in ["langages", "outils", "projets", "certifications"]:
            valeurs = valeurs_uniques(cv["competences"][champ])
            ligne[f"nb_{champ}"] = None if "competences" in illisibles else len(valeurs)
            if champ in ["langages", "outils"] and "competences" not in illisibles:
                for valeur in valeurs:
                    codes.append({"id_candidat": ligne["id_candidat"], "champ": champ, "code": valeur})
        ligne["nb_experiences"] = None if "experiences" in illisibles else len(cv["experiences"])
        nb_stages, nb_jobs = 0, 0
        types_connus = True
        for experience in cv["experiences"]:
            if experience["type"] is None:
                types_connus = False
            if experience["type"] == "stage":
                nb_stages += 1
            if experience["type"] == "job_etudiant":
                nb_jobs += 1
        ligne["nb_stages"] = nb_stages if types_connus and "experiences" not in illisibles else None
        ligne["nb_jobs_etudiants"] = nb_jobs if types_connus and "experiences" not in illisibles else None
        ligne["nb_langues"] = None if "langues" in illisibles else len(valeurs_uniques([x["langue"] for x in cv["langues"]]))
        ligne["nb_engagements"] = None if "engagements" in illisibles else len(cv["engagements"])
        ligne["nb_sejours"] = None if "international" in illisibles else len(cv["international"])
        ligne["rubriques_illisibles"] = ", ".join(illisibles)
        lignes.append(ligne)
    return pd.DataFrame(lignes), pd.DataFrame(codes, columns=["id_candidat", "champ", "code"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", type=Path, default=RACINE / "sorties")
    parser.add_argument("-o", "--sortie", type=Path, default=RACINE / "analyse")
    args = parser.parse_args()
    try:
        candidats = charge_dossier(args.dossier)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 1
    tableau, codes = construit_tables(candidats)
    args.sortie.mkdir(parents=True, exist_ok=True)
    tableau.to_csv(args.sortie / "candidats.csv", index=False)
    codes.to_csv(args.sortie / "codes.csv", index=False)
    print(f"{len(tableau)} candidats -> {args.sortie}/candidats.csv et codes.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
