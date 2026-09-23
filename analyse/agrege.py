"""Rassemble les JSON d'extraction en deux tables exploitables.

    python3 analyse/agrege.py [dossier_json] [-o dossier_sortie]

Produit :
  candidats.csv  une ligne par candidat, une colonne par champ scalaire de
                 donnees_normalisees (prefixe par son bloc : academique_bac_mention).
  codes.csv      format long (id_candidat, champ, code) pour les champs qui
                 sont des listes. Un value_counts() sur ce fichier compte
                 directement les occurrences, ce qu'une colonne de listes
                 dans candidats.csv ne permet pas.

Le verbatim n'est pas aplati : il n'est pas comparable d'un CV a l'autre,
c'est precisement la raison d'etre de donnees_normalisees.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from vocabulaire import CHAMPS_LISTES


def charge(chemin: Path) -> dict:
    with chemin.open(encoding="utf-8") as f:
        return json.load(f)


def aplatit(cv: dict, chemin: Path) -> tuple[dict, list[dict]]:
    """Retourne (ligne scalaire, lignes longues pour les champs listes)."""
    meta = cv.get("meta") or {}
    # Sans meta.id_candidat, le nom du fichier fait office d'identifiant.
    id_candidat = meta.get("id_candidat") or chemin.stem

    ligne = {
        "id_candidat": id_candidat,
        "fichier_source": meta.get("fichier_source"),
    }
    codes = []

    normalisees = cv.get("donnees_normalisees") or {}
    for bloc, contenu in normalisees.items():
        if not isinstance(contenu, dict):
            continue
        for champ, valeur in contenu.items():
            if isinstance(valeur, list):
                for code in valeur:
                    codes.append(
                        {
                            "id_candidat": id_candidat,
                            "champ": f"{bloc}.{champ}",
                            "code": code,
                        }
                    )
            else:
                ligne[f"{bloc}_{champ}"] = valeur

    # La qualite OCR conditionne la lecture de tout le reste : elle voyage
    # avec les donnees plutot que dans un fichier a part.
    qualite = cv.get("qualite_extraction") or {}
    ligne["ocr_qualite"] = qualite.get("qualite_ocr_globale")
    ligne["ocr_cv_tronque"] = qualite.get("cv_tronque")
    ligne["ocr_langue_cv"] = qualite.get("langue_du_cv")
    ligne["ocr_nb_sections_illisibles"] = len(qualite.get("sections_illisibles") or [])

    return ligne, codes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", default="sorties", type=Path)
    parser.add_argument("-o", "--sortie", default=Path("analyse"), type=Path)
    args = parser.parse_args()

    fichiers = sorted(args.dossier.glob("*.json"))
    if not fichiers:
        print(f"Aucun JSON dans {args.dossier}/", file=sys.stderr)
        return 1

    lignes, codes = [], []
    illisibles = []
    for chemin in fichiers:
        try:
            cv = charge(chemin)
        except json.JSONDecodeError as e:
            # Un JSON casse est le mode d'echec le plus courant quand le LLM
            # entoure sa reponse de texte. On le signale sans tout arreter.
            illisibles.append((chemin.name, str(e)))
            continue
        ligne, codes_cv = aplatit(cv, chemin)
        lignes.append(ligne)
        codes.extend(codes_cv)

    df = pd.DataFrame(lignes).set_index("id_candidat").sort_index()
    df_codes = pd.DataFrame(codes, columns=["id_candidat", "champ", "code"])

    args.sortie.mkdir(parents=True, exist_ok=True)
    chemin_candidats = args.sortie / "candidats.csv"
    chemin_codes = args.sortie / "codes.csv"
    df.to_csv(chemin_candidats)
    df_codes.to_csv(chemin_codes, index=False)

    print(f"{len(df)} candidats, {len(df.columns)} colonnes -> {chemin_candidats}")
    print(f"{len(df_codes)} codes -> {chemin_codes}")

    champs_vus = set(df_codes["champ"].unique())
    manquants = sorted(set(CHAMPS_LISTES) - champs_vus)
    if manquants:
        # Pas une erreur : un champ liste vide chez tout le monde est possible.
        # Mais c'est le symptome d'un prompt qui ne remplit jamais ce champ.
        print(f"Champs listes jamais remplis : {', '.join(manquants)}")

    for nom, erreur in illisibles:
        print(f"JSON illisible, ignore : {nom} ({erreur})", file=sys.stderr)

    return 1 if illisibles else 0


if __name__ == "__main__":
    sys.exit(main())
