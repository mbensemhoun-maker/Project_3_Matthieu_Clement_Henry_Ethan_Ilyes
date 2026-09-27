"""Lecture et validation du JSON court. Aucun indicateur n'est demande au LLM."""

import json
import math
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
TEXTE = (str, type(None))
NOMBRE = (int, float, type(None))
RUBRIQUES = {"formation", "competences", "langues", "experiences", "engagements", "international"}
TYPES_EXPERIENCE = {"stage", "alternance", "job_etudiant", "emploi", "benevolat", "autre", None}

# Une liste dans ce schema indique le type de ses elements, pas un element a recopier.
SCHEMA = {
    "meta": {"id_candidat": str, "fichier_source": str},
    "formation": {
        "filiere_bac": TEXTE, "mention_bac": TEXTE, "etablissement": TEXTE,
        "specialites": [str], "options": [str], "prepa": TEXTE,
        "etudes_superieures": [str], "anomalies_parcours": TEXTE,
        "concours": [str],
        "resultats": [{"intitule": str, "note_sur_20": NOMBRE}],
    },
    "competences": {"langages": [str], "outils": [str], "projets": [str], "certifications": [str]},
    "langues": [{"langue": str, "niveau": TEXTE, "certification": TEXTE, "score": TEXTE}],
    "experiences": [{"type": TEXTE, "poste": str, "organisation": TEXTE, "duree": TEXTE, "missions": TEXTE}],
    "engagements": [{"role": str, "organisation": TEXTE, "description": TEXTE}],
    "international": [{"pays": TEXTE, "motif": str, "duree": TEXTE}],
    "rubriques_illisibles": [str],
}


def normalise_texte(texte):
    """Uniformise casse, accents et espaces, sans inventer de categorie."""
    texte = unicodedata.normalize("NFKD", texte.casefold())
    return " ".join("".join(c for c in texte if not unicodedata.combining(c)).split())


def valeurs_uniques(valeurs):
    resultat = []
    for valeur in valeurs:
        code = normalise_texte(valeur)
        if code not in resultat:
            resultat.append(code)
    return resultat


def mention_standard(mention):
    if mention is None:
        return None
    code = normalise_texte(mention)
    correspondances = {"tb": "tres bien", "b": "bien", "ab": "assez bien", "passable": "sans mention"}
    return correspondances.get(code, code)


def valide_cv(cv):
    """Retourne les erreurs de structure ; ne garantit pas la fidelite au TXT."""
    erreurs = []
    if isinstance(cv, dict) and "donnees_normalisees" in cv:
        return ["Ancien format JSON : regenerer avec prompt.md et --force, ou adapter ce fichier."]

    def verifie(valeur, schema, chemin):
        if isinstance(schema, dict):
            if not isinstance(valeur, dict):
                erreurs.append(f"{chemin} : objet attendu")
                return
            for cle in schema:
                if cle not in valeur:
                    erreurs.append(f"{chemin}.{cle} : champ manquant")
                else:
                    verifie(valeur[cle], schema[cle], f"{chemin}.{cle}")
            for cle in valeur.keys() - schema.keys():
                erreurs.append(f"{chemin}.{cle} : champ inattendu")
        elif isinstance(schema, list):
            if not isinstance(valeur, list):
                erreurs.append(f"{chemin} : liste attendue")
                return
            for numero, element in enumerate(valeur):
                verifie(element, schema[0], f"{chemin}[{numero}]")
        else:
            types = schema if isinstance(schema, tuple) else (schema,)
            if type(valeur) not in types:
                erreurs.append(f"{chemin} : type incorrect")
            elif isinstance(valeur, str) and not valeur.strip():
                erreurs.append(f"{chemin} : utiliser null ou [] au lieu d'une chaine vide")
            elif isinstance(valeur, (int, float)) and (not math.isfinite(valeur) or not 0 <= valeur <= 20):
                erreurs.append(f"{chemin} : note attendue entre 0 et 20")

    verifie(cv, SCHEMA, "cv")
    if erreurs:
        return erreurs
    if not cv["meta"]["fichier_source"].endswith(".pdf"):
        erreurs.append("meta.fichier_source : nom du PDF d'origine attendu")
    for rubrique in cv["rubriques_illisibles"]:
        if rubrique not in RUBRIQUES:
            erreurs.append(f"Rubrique illisible inconnue : {rubrique}")
    for experience in cv["experiences"]:
        if experience["type"] not in TYPES_EXPERIENCE:
            erreurs.append(f"Type d'experience inconnu : {experience['type']}")
    return erreurs


def charge_dossier(dossier):
    """Refuse un lot vide, invalide ou contenant des candidats en double."""
    fichiers = sorted(Path(dossier).glob("*.json"))
    if not fichiers:
        raise ValueError(f"Aucun JSON dans {dossier}")
    candidats, ids, sources, erreurs = [], set(), set(), []
    for fichier in fichiers:
        try:
            cv = json.loads(fichier.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as erreur:
            erreurs.append(f"{fichier.name} : {erreur}")
            continue
        problemes = valide_cv(cv)
        if problemes:
            erreurs.extend(f"{fichier.name} : {message}" for message in problemes)
            continue
        identifiant, source = cv["meta"]["id_candidat"], cv["meta"]["fichier_source"]
        if identifiant in ids or source in sources:
            erreurs.append(f"{fichier.name} : candidat ou fichier source en double")
        ids.add(identifiant)
        sources.add(source)
        candidats.append(cv)
    if erreurs:
        raise ValueError("\n".join(erreurs))
    return candidats
