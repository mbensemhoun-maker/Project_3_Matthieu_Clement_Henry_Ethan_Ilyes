"""Resume les indicateurs calcules par agrege.py ; analyse detaillee dans le notebook."""

import argparse
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--donnees", type=Path, default=RACINE / "analyse")
    parser.add_argument("-n", "--notes", type=Path, default=RACINE / "cv-test" / "notes-reference.csv")
    args = parser.parse_args()
    chemin = args.donnees / "candidats.csv"
    if not chemin.exists():
        print("Lancer d'abord analyse/agrege.py ou le notebook.", file=sys.stderr)
        return 1
    df = pd.read_csv(chemin)
    if "nb_stages" not in df:
        print("Ancien CSV : regenerer avec analyse/agrege.py.", file=sys.stderr)
        return 1
    print(f"{len(df)} candidats")
    print("\nMentions au bac (valeurs renseignees) :")
    print(df["mention_bac"].value_counts().to_string())
    for colonne in ["nb_langages", "nb_projets", "nb_stages", "nb_engagements", "nb_sejours"]:
        valeurs = df[colonne].dropna()
        if valeurs.empty:
            print(f"{colonne} : aucune valeur exploitable")
            continue
        print(f"{colonne} : moyenne {valeurs.mean():.2f} ; base {len(valeurs)}/{len(df)} CV")
    codes = pd.read_csv(args.donnees / "codes.csv")
    print("\nLangages mentionnes (nombre de candidats) :")
    print(codes.loc[codes["champ"] == "langages", "code"].value_counts().to_string())
    if args.notes.exists():
        notes = pd.read_csv(args.notes, sep=";")
        comparaison = df.merge(notes[["fichier", "total_sur20"]], left_on="fichier_source", right_on="fichier", how="inner", validate="one_to_one")
        print(f"\n{len(comparaison)}/{len(df)} CV avec une note de reference (pas une prediction).")
        if not comparaison.empty:
            print(comparaison[["id_candidat", "nb_stages", "nb_langages", "total_sur20"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
