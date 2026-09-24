"""Verifie que donnees_normalisees ne contredit pas le verbatim du meme JSON.

    python3 analyse/controle_coherence.py [dossier_json]

Ce script ne dit pas si l'extraction est JUSTE : pour ca il faut relire le CV.
Il dit si le bloc normalise est coherent avec ce qui a ete extrait au-dessus.
Le bloc n'est cense contenir aucune information neuve : il recode. Donc toute
valeur normalisee sans appui dans le verbatim est une invention, et ca se
verifie mecaniquement, sans verite terrain.

Deux severites :
  ERREUR  contradiction ou invention -- le chiffre est faux.
  ALERTE  suspect mais explicable -- a regarder avant de publier des stats.

Code de retour 1 s'il reste au moins une ERREUR.
"""

import argparse
import json
import sys
from pathlib import Path

import vocabulaire as v

MENTIONS_ATTENDUES = {
    "tb": "tres_bien",
    "b": "bien",
    "ab": "assez_bien",
    "tres bien": "tres_bien",
    "très bien": "tres_bien",
    "bien": "bien",
    "assez bien": "assez_bien",
    "passable": "sans_mention",
    "sans mention": "sans_mention",
}


def vide(valeur) -> bool:
    """Un champ sans information : null, liste vide, chaine blanche."""
    if valeur is None:
        return True
    if isinstance(valeur, (list, dict, str)):
        return len(valeur) == 0 or (isinstance(valeur, str) and not valeur.strip())
    return False


def entrees_reelles(liste) -> list:
    """Filtre les entrees entierement nulles.

    Le gabarit de prompt.md montre chaque liste avec un element type dont tous
    les champs valent null. Un modele qui recopie le gabarit sans le remplir
    produit une liste de longueur 1 qui ne contient rien. Sans ce filtre, tous
    les comptages sont fausses d'une unite.
    """
    if not isinstance(liste, list):
        return []
    return [e for e in liste if isinstance(e, dict) and any(not vide(x) for x in e.values())]


class Controle:
    def __init__(self, id_candidat: str):
        self.id = id_candidat
        self.problemes: list[tuple[str, str, str]] = []

    def erreur(self, regle: str, message: str) -> None:
        self.problemes.append(("ERREUR", regle, message))

    def alerte(self, regle: str, message: str) -> None:
        self.problemes.append(("ALERTE", regle, message))

    def sans_appui(self, regle: str, valeur, source, nom_valeur: str, nom_source: str) -> None:
        """Le normalise affirme quelque chose que le verbatim ne dit pas."""
        if not vide(valeur) and vide(source):
            self.erreur(regle, f"{nom_valeur}={valeur!r} mais {nom_source} est vide")

    def enum(self, regle: str, valeur, autorisees: set, nom: str) -> None:
        if not vide(valeur) and valeur not in autorisees:
            self.erreur(regle, f"{nom}={valeur!r} hors vocabulaire")

    def compteur(self, regle: str, valeur, nom: str) -> None:
        if valeur is None:
            self.erreur(regle, f"{nom} est null, un compteur vaut 0 quand il n'y a rien")


def controle_cv(cv: dict, id_candidat: str) -> Controle:
    c = Controle(id_candidat)
    n = cv.get("donnees_normalisees")
    if not isinstance(n, dict):
        c.erreur("structure", "bloc donnees_normalisees absent")
        return c

    formation = cv.get("formation") or {}
    bac = formation.get("bac") or {}
    quantitatif = cv.get("quantitatif") or {}
    tech = cv.get("competences_tech") or {}
    experiences = entrees_reelles(cv.get("experiences"))
    engagements = entrees_reelles(cv.get("engagement"))
    internationaux = entrees_reelles(cv.get("international"))
    langues = entrees_reelles(cv.get("langues"))
    qualite = cv.get("qualite_extraction") or {}

    # Gabarit recopie tel quel : detecte avant les comptages, qui en dependent.
    for nom, brut in (
        ("experiences", cv.get("experiences")),
        ("engagement", cv.get("engagement")),
        ("international", cv.get("international")),
        ("langues", cv.get("langues")),
    ):
        brut = brut if isinstance(brut, list) else []
        fantomes = len(brut) - len(entrees_reelles(brut))
        if fantomes:
            c.alerte(
                "gabarit",
                f"{nom} contient {fantomes} entree(s) entierement nulle(s), "
                "le gabarit a ete recopie sans etre rempli",
            )

    aca = n.get("academique") or {}
    quant = n.get("quantitatif") or {}
    t = n.get("tech") or {}
    lang = n.get("langues") or {}
    exp = n.get("experience") or {}
    eng = n.get("engagement") or {}
    inter = n.get("international") or {}
    comp = n.get("completude") or {}

    # --- Inventions : le normalise affirme ce que le verbatim ne dit pas ---
    c.sans_appui("invention", aca.get("bac_mention"), bac.get("mention"), "bac_mention", "formation.bac.mention")
    c.sans_appui("invention", aca.get("bac_annee"), bac.get("annee"), "bac_annee", "formation.bac.annee")
    c.sans_appui("invention", aca.get("bac_moyenne_sur_20"), bac.get("moyenne"), "bac_moyenne_sur_20", "formation.bac.moyenne")
    c.sans_appui("invention", aca.get("bac_filiere"), bac.get("filiere"), "bac_filiere", "formation.bac.filiere")

    prepa = formation.get("prepa") or {}
    a_prepa_verbatim = not vide(prepa.get("filiere")) or not vide((prepa.get("etablissement") or {}).get("nom"))
    if aca.get("a_fait_prepa") and not a_prepa_verbatim:
        c.erreur("invention", "a_fait_prepa=true mais formation.prepa est vide")
    if a_prepa_verbatim and aca.get("a_fait_prepa") is False:
        c.erreur("contradiction", "formation.prepa est remplie mais a_fait_prepa=false")
    c.sans_appui("invention", aca.get("prepa_filiere"), prepa.get("filiere"), "prepa_filiere", "formation.prepa.filiere")

    a_anomalie = not vide(formation.get("anomalies_parcours"))
    if bool(aca.get("a_anomalie_parcours")) != a_anomalie:
        c.erreur(
            "contradiction",
            f"a_anomalie_parcours={aca.get('a_anomalie_parcours')} mais "
            f"formation.anomalies_parcours {'est rempli' if a_anomalie else 'est vide'}",
        )

    if exp.get("a_encadrement") and not any(not vide(e.get("encadrement")) for e in experiences):
        c.erreur("invention", "a_encadrement=true mais aucune experience n'a d'encadrement")

    if not vide(lang.get("anglais_score")) and vide(lang.get("anglais_test")):
        c.erreur("invention", "anglais_score renseigne sans anglais_test : score illisible")

    # --- Recodage : la valeur normalisee correspond-elle au verbatim ? ---
    mention_verbatim = (bac.get("mention") or "").strip().lower()
    attendue = MENTIONS_ATTENDUES.get(mention_verbatim.replace("mention ", ""))
    if attendue and aca.get("bac_mention") not in (None, attendue):
        c.erreur(
            "recodage",
            f"mention verbatim {bac.get('mention')!r} devrait donner {attendue!r}, "
            f"pas {aca.get('bac_mention')!r}",
        )

    # --- Vocabulaire ferme ---
    c.enum("vocabulaire", aca.get("bac_filiere"), v.BAC_FILIERE, "bac_filiere")
    c.enum("vocabulaire", aca.get("bac_mention"), v.BAC_MENTION, "bac_mention")
    c.enum("vocabulaire", aca.get("prepa_filiere"), v.PREPA_FILIERE, "prepa_filiere")
    c.enum("vocabulaire", aca.get("niveau_etudes_max"), v.NIVEAU_ETUDES, "niveau_etudes_max")
    c.enum("vocabulaire", lang.get("anglais_niveau_cecrl"), v.CECRL, "anglais_niveau_cecrl")
    c.enum("vocabulaire", lang.get("anglais_test"), v.TESTS_ANGLAIS, "anglais_test")
    for champ, autorisees in v.CHAMPS_LISTES.items():
        if autorisees is None:
            continue
        bloc, cle = champ.split(".")
        for code in (n.get(bloc) or {}).get(cle) or []:
            c.enum("vocabulaire", code, autorisees, f"{champ}[]")

    # --- Compteurs ---
    for bloc, cle in (
        ("quantitatif", "nb_specialites_scientifiques"),
        ("quantitatif", "nb_concours_scientifiques"),
        ("tech", "nb_langages"),
        ("tech", "nb_projets_data"),
        ("tech", "nb_certifications"),
        ("langues", "nb_langues_hors_maternelle"),
        ("experience", "nb_stages"),
        ("experience", "nb_alternances"),
        ("experience", "nb_jobs_etudiants"),
        ("engagement", "nb_engagements"),
        ("international", "nb_sejours"),
    ):
        c.compteur("compteur", (n.get(bloc) or {}).get(cle), f"{bloc}.{cle}")

    codes_langages = t.get("langages_codes") or []
    if t.get("nb_langages") is not None and t["nb_langages"] != len(set(codes_langages)):
        c.erreur(
            "compteur",
            f"nb_langages={t['nb_langages']} mais langages_codes en contient "
            f"{len(set(codes_langages))} (dedoublonnes)",
        )

    specialites = quant.get("specialites_codes") or []
    attendu_sci = len([s for s in specialites if s in v.SPECIALITES_SCIENTIFIQUES])
    if quant.get("nb_specialites_scientifiques") not in (None, attendu_sci):
        c.erreur(
            "compteur",
            f"nb_specialites_scientifiques={quant['nb_specialites_scientifiques']} "
            f"mais specialites_codes en contient {attendu_sci}",
        )

    somme_exp = sum(exp.get(k) or 0 for k in ("nb_stages", "nb_alternances", "nb_jobs_etudiants"))
    if somme_exp > len(experiences):
        c.erreur(
            "compteur",
            f"les compteurs totalisent {somme_exp} experiences mais le bloc verbatim "
            f"en contient {len(experiences)}",
        )

    for nom, compteur, verbatim in (
        ("nb_engagements", eng.get("nb_engagements"), engagements),
        ("nb_sejours", inter.get("nb_sejours"), internationaux),
        ("nb_projets_data", t.get("nb_projets_data"), entrees_reelles(tech.get("projets_data"))),
        ("nb_certifications", t.get("nb_certifications"), entrees_reelles(tech.get("certifications"))),
        ("nb_concours_scientifiques", quant.get("nb_concours_scientifiques"), entrees_reelles(quantitatif.get("concours_scientifiques"))),
    ):
        if compteur is not None and compteur > len(verbatim):
            c.erreur("compteur", f"{nom}={compteur} mais le verbatim en contient {len(verbatim)}")

    if inter.get("a_experience_internationale") and not internationaux:
        c.erreur("invention", "a_experience_internationale=true mais le bloc international est vide")

    if lang.get("nb_langues_hors_maternelle") is not None and langues:
        if lang["nb_langues_hors_maternelle"] > len(langues):
            c.erreur(
                "compteur",
                f"nb_langues_hors_maternelle={lang['nb_langues_hors_maternelle']} "
                f"mais seulement {len(langues)} langues extraites",
            )

    # --- Durees ---
    for bloc, nom in (("experience", "duree_totale_mois"), ("international", "duree_totale_mois")):
        duree = (n.get(bloc) or {}).get(nom)
        if duree == 0:
            c.alerte(
                "duree",
                f"{bloc}.{nom}=0 : null est attendu quand rien n'est calculable, "
                "0 se confond avec une absence reelle",
            )
        if duree is not None and duree < 0:
            c.erreur("duree", f"{bloc}.{nom}={duree} est negatif")
    if exp.get("duree_totale_mois") is not None and exp.get("duree_plus_longue_mois") is not None:
        if exp["duree_plus_longue_mois"] > exp["duree_totale_mois"]:
            c.erreur(
                "duree",
                f"duree_plus_longue_mois={exp['duree_plus_longue_mois']} depasse "
                f"duree_totale_mois={exp['duree_totale_mois']}",
            )

    # --- Completude vs sections_illisibles ---
    illisibles_declarees = set(qualite.get("sections_illisibles") or [])
    contenu_verbatim = {
        "formation": formation,
        "quantitatif": quantitatif,
        "competences_tech": tech,
        "langues": langues,
        "experiences": experiences,
        "engagement": engagements,
        "international": internationaux,
    }
    for rubrique in v.RUBRIQUES:
        statut = comp.get(rubrique)
        if vide(statut):
            c.erreur("completude", f"completude.{rubrique} est null, un statut est obligatoire")
            continue
        c.enum("completude", statut, v.COMPLETUDE, f"completude.{rubrique}")
        if (statut == "illisible") != (rubrique in illisibles_declarees):
            c.erreur(
                "completude",
                f"completude.{rubrique}={statut!r} mais la rubrique est "
                f"{'presente' if rubrique in illisibles_declarees else 'absente'} "
                "de qualite_extraction.sections_illisibles",
            )
        rempli = any(not vide(x) for x in (contenu_verbatim[rubrique] or {}).values()) if isinstance(
            contenu_verbatim[rubrique], dict
        ) else bool(contenu_verbatim[rubrique])
        if statut == "renseigne" and not rempli:
            c.erreur("completude", f"completude.{rubrique}='renseigne' mais la rubrique est vide")
        if statut == "absent_confirme" and rempli:
            c.erreur("completude", f"completude.{rubrique}='absent_confirme' mais la rubrique contient des donnees")

    return c


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", default="sorties", type=Path)
    parser.add_argument("-q", "--quiet", action="store_true", help="n'affiche que les ERREUR")
    args = parser.parse_args()

    fichiers = sorted(args.dossier.glob("*.json"))
    if not fichiers:
        print(f"Aucun JSON dans {args.dossier}/", file=sys.stderr)
        return 1

    total_erreurs = total_alertes = 0
    cv_propres = 0
    par_regle: dict[str, int] = {}

    for chemin in fichiers:
        try:
            cv = json.loads(chemin.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"\n{chemin.name}\n  ERREUR  json  {e}")
            total_erreurs += 1
            continue

        id_candidat = ((cv.get("meta") or {}).get("id_candidat")) or chemin.stem
        c = controle_cv(cv, id_candidat)
        erreurs = [p for p in c.problemes if p[0] == "ERREUR"]
        alertes = [p for p in c.problemes if p[0] == "ALERTE"]
        total_erreurs += len(erreurs)
        total_alertes += len(alertes)
        for severite, regle, _ in c.problemes:
            par_regle[regle] = par_regle.get(regle, 0) + 1

        if not c.problemes:
            cv_propres += 1
            continue
        a_montrer = erreurs if args.quiet else c.problemes
        if a_montrer:
            print(f"\n{id_candidat}  ({chemin.name})")
            for severite, regle, message in a_montrer:
                print(f"  {severite:7} {regle:12} {message}")

    print(f"\n{'-' * 60}")
    print(f"{len(fichiers)} CV controles, {cv_propres} sans probleme")
    print(f"{total_erreurs} erreur(s), {total_alertes} alerte(s)")
    if par_regle:
        detail = ", ".join(f"{r}={n}" for r, n in sorted(par_regle.items(), key=lambda x: -x[1]))
        print(f"Par regle : {detail}")

    return 1 if total_erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
