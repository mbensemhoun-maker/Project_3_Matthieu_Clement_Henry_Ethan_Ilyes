"""Statistiques descriptives sur la promo de candidats.

    python3 analyse/agrege.py sorties/      # d'abord
    python3 analyse/stats.py                # ensuite

Regle appliquee partout : une rubrique illisible n'entre pas dans la base de
calcul. Sans ca, "40% des candidats n'ont pas fait de stage" melange les
candidats qui n'en ont pas fait et ceux dont la rubrique n'a pas ete lue. Chaque
pourcentage est donc affiche avec sa base et le nombre de CV ecartes.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def base(df: pd.DataFrame, rubrique: str) -> tuple[pd.DataFrame, int]:
    """Restreint aux CV dont la rubrique a ete lue. Retourne (base, ecartes)."""
    colonne = f"completude_{rubrique}"
    if colonne not in df.columns:
        return df, 0
    lisible = df[df[colonne] != "illisible"]
    return lisible, len(df) - len(lisible)


def part(df: pd.DataFrame, rubrique: str, masque_nom: str, masque) -> str:
    b, ecartes = base(df, rubrique)
    if b.empty:
        return f"{masque_nom} : aucune base de calcul"
    n = int(masque(b).sum())
    txt = f"{masque_nom} : {n}/{len(b)} ({n / len(b):.0%})"
    if ecartes:
        txt += f"  [{ecartes} CV ecarte(s), rubrique illisible]"
    return txt


def distribution(df: pd.DataFrame, colonne: str, rubrique: str, titre: str) -> None:
    b, ecartes = base(df, rubrique)
    serie = b[colonne].dropna()
    print(f"\n{titre}  (base {len(serie)}/{len(df)}" + (f", {ecartes} illisible(s)" if ecartes else "") + ")")
    if serie.empty:
        print("  aucune valeur")
        return
    for valeur, n in serie.value_counts().items():
        print(f"  {valeur:28} {n:3}  {n / len(serie):>5.0%}")


def top_codes(codes: pd.DataFrame, champ: str, titre: str, effectif: int) -> None:
    sous = codes[codes["champ"] == champ]
    print(f"\n{titre}  ({sous['id_candidat'].nunique()}/{effectif} candidats concernes)")
    if sous.empty:
        print("  aucun code")
        return
    for code, n in sous["code"].value_counts().items():
        print(f"  {code:28} {n:3}  {n / effectif:>5.0%} de la promo")


def croise_avec_notes(df: pd.DataFrame, chemin_notes: Path) -> None:
    """Confronte les indicateurs extraits aux notes de reference, si elles existent.

    Utile pour reperer un indicateur qui ne discrimine rien : si la note moyenne
    est la meme avec et sans prepa, soit l'extraction rate quelque chose, soit le
    critere ne pese pas autant que la grille le pretend.
    """
    if not chemin_notes.exists():
        print(f"\n(pas de notes de reference dans {chemin_notes}, croisement saute)")
        return
    notes = pd.read_csv(chemin_notes, sep=";")
    fusion = df.merge(notes, left_on="fichier_source", right_on="fichier", how="inner")
    if fusion.empty:
        print(
            "\nCroisement impossible : aucun fichier_source ne correspond a la colonne "
            "'fichier' des notes de reference."
        )
        return

    print(f"\n{'=' * 60}\nCROISEMENT AVEC LES NOTES DE REFERENCE ({len(fusion)} CV apparies)")
    print(f"\nNote moyenne : {fusion['total_sur20'].mean():.1f}/20  "
          f"(min {fusion['total_sur20'].min()}, max {fusion['total_sur20'].max()})")

    for colonne, libelle in (
        ("academique_a_fait_prepa", "prepa"),
        ("experience_a_experience_data", "experience data"),
        ("international_a_experience_internationale", "sejour international"),
        ("engagement_a_role_responsabilite", "role de responsabilite"),
    ):
        if colonne not in fusion.columns:
            continue
        groupes = fusion.groupby(fusion[colonne].fillna(False).astype(bool))["total_sur20"]
        if len(groupes) < 2:
            continue
        avec, sans = groupes.get_group(True), groupes.get_group(False)
        print(
            f"  avec {libelle:24} {avec.mean():5.1f}/20 (n={len(avec)})   "
            f"sans : {sans.mean():5.1f}/20 (n={len(sans)})   "
            f"ecart {avec.mean() - sans.mean():+.1f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", "--donnees", default=Path("analyse"), type=Path)
    parser.add_argument("-n", "--notes", default=Path("cv-test/notes-reference.csv"), type=Path)
    args = parser.parse_args()

    chemin_candidats = args.donnees / "candidats.csv"
    if not chemin_candidats.exists():
        print(f"{chemin_candidats} absent. Lancer d'abord : python3 analyse/agrege.py sorties/", file=sys.stderr)
        return 1

    df = pd.read_csv(chemin_candidats)
    codes = pd.read_csv(args.donnees / "codes.csv")
    n = len(df)

    print(f"{'=' * 60}\nPROMO : {n} candidats")

    print("\nQualite OCR")
    for valeur, k in df["ocr_qualite"].value_counts(dropna=False).items():
        print(f"  {str(valeur):28} {k:3}  {k / n:>5.0%}")
    tronques = int(df["ocr_cv_tronque"].fillna(False).astype(bool).sum())
    print(f"  {'CV tronques':28} {tronques:3}  {tronques / n:>5.0%}")

    print("\nRubriques illisibles (elles reduisent la base de calcul plus bas)")
    rubriques = [c[len("completude_"):] for c in df.columns if c.startswith("completude_")]
    for rubrique in rubriques:
        k = int((df[f"completude_{rubrique}"] == "illisible").sum())
        if k:
            print(f"  {rubrique:28} {k:3}  {k / n:>5.0%}")
    if not any((df[f"completude_{r}"] == "illisible").any() for r in rubriques):
        print("  aucune")

    print(f"\n{'=' * 60}\nPROFIL ACADEMIQUE")
    distribution(df, "academique_bac_mention", "formation", "Mention au bac")
    distribution(df, "academique_bac_filiere", "formation", "Filiere du bac")
    distribution(df, "academique_prepa_filiere", "formation", "Filiere de prepa")
    b, _ = base(df, "formation")
    if "academique_bac_moyenne_sur_20" in df.columns:
        moyennes = b["academique_bac_moyenne_sur_20"].dropna()
        if not moyennes.empty:
            print(
                f"\nMoyenne au bac : {moyennes.mean():.1f}/20 (mediane {moyennes.median():.1f}, "
                f"renseignee pour {len(moyennes)}/{len(b)} CV)"
            )
    print("\n" + part(df, "formation", "Ont fait une prepa",
                      lambda d: d["academique_a_fait_prepa"].fillna(False).astype(bool)))

    print(f"\n{'=' * 60}\nQUANTITATIF ET TECH")
    top_codes(codes, "quantitatif.specialites_codes", "Specialites de terminale", n)
    top_codes(codes, "tech.langages_codes", "Langages", n)
    top_codes(codes, "tech.outils_codes", "Outils", n)
    print("\n" + part(df, "competences_tech", "Au moins un projet data",
                      lambda d: d["tech_nb_projets_data"].fillna(0) > 0))
    print(part(df, "competences_tech", "Au moins une certification",
               lambda d: d["tech_nb_certifications"].fillna(0) > 0))

    print(f"\n{'=' * 60}\nLANGUES")
    distribution(df, "langues_anglais_niveau_cecrl", "langues", "Niveau d'anglais (CECRL declare)")
    distribution(df, "langues_anglais_test", "langues", "Test d'anglais passe")
    top_codes(codes, "langues.autres_langues_codes", "Autres langues", n)

    print(f"\n{'=' * 60}\nEXPERIENCE")
    print(part(df, "experiences", "Au moins un stage", lambda d: d["experience_nb_stages"].fillna(0) > 0))
    print(part(df, "experiences", "Au moins un job etudiant", lambda d: d["experience_nb_jobs_etudiants"].fillna(0) > 0))
    print(part(df, "experiences", "Experience data", lambda d: d["experience_a_experience_data"].fillna(False).astype(bool)))
    b, _ = base(df, "experiences")
    durees = b["experience_duree_totale_mois"].dropna()
    if not durees.empty:
        print(
            f"Duree cumulee d'experience : mediane {durees.median():.1f} mois, "
            f"moyenne {durees.mean():.1f} mois (calculable pour {len(durees)}/{len(b)} CV)"
        )
    else:
        print("Duree cumulee d'experience : non calculable (dates absentes ou experiences en cours)")

    print(f"\n{'=' * 60}\nENGAGEMENT ET INTERNATIONAL")
    top_codes(codes, "engagement.types_codes", "Types d'engagement", n)
    print("\n" + part(df, "engagement", "Role de responsabilite",
                      lambda d: d["engagement_a_role_responsabilite"].fillna(False).astype(bool)))
    print(part(df, "international", "Experience internationale",
               lambda d: d["international_a_experience_internationale"].fillna(False).astype(bool)))
    top_codes(codes, "international.pays_codes", "Pays", n)

    croise_avec_notes(df, args.notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
