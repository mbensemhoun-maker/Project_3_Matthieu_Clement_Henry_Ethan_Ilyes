"""PDF -> TXT -> JSON Ollama, avec provenance et reutilisation verifiee."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

from .donnees import SCHEMA, schema_json, valide_cv, normalise_texte

GROUPES = ["formation", "competences", "langues", "experiences", "engagements", "international"]
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 768}


def empreinte(contenu):
    if isinstance(contenu, str):
        contenu = contenu.encode("utf-8")
    return hashlib.sha256(contenu).hexdigest()


def ecrit_json(chemin, contenu):
    """Remplacement atomique : une interruption ne laisse pas un demi-JSON."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
    temporaire.write_text(json.dumps(contenu, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporaire.replace(chemin)


def extrait_pdf(pdf, dossier_texte):
    pdf = Path(pdf)
    pages = []
    for numero, page in enumerate(PdfReader(pdf).pages, 1):
        texte = (page.extract_text() or "").strip()
        if not texte:
            raise ValueError(f"{pdf.name}, page {numero} : aucun texte lisible. OCR ou verification necessaire.")
        pages.append(texte.replace("\x7f", "•"))
    texte = "\n\n".join(pages)
    if not texte.strip():
        raise ValueError(f"{pdf.name} : document vide")
    destination = Path(dossier_texte) / (pdf.stem + ".txt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(texte + "\n", encoding="utf-8")
    return {"pdf": pdf, "texte": texte, "txt": destination,
            "pdf_sha256": empreinte(pdf.read_bytes()), "texte_sha256": empreinte(texte)}


def lit_prompt(chemin):
    texte = Path(chemin).read_text(encoding="utf-8")
    bloc = re.search(r"^```text\n(.*?)^```", texte, re.M | re.S)
    if not bloc:
        raise ValueError("Le prompt doit etre dans un bloc ```text de prompt.md.")
    return texte


def gabarit(schema):
    if isinstance(schema, dict):
        return {cle: gabarit(valeur) for cle, valeur in schema.items()}
    if isinstance(schema, list):
        return []
    return None


def message_cv(prompt, texte, identifiant, rubrique):
    commun = re.search(r"^```text\n(.*?)^```", prompt, re.M | re.S)[1].strip()
    consignes = re.search(r"^### " + rubrique + r"\n```text\n(.*?)^```", prompt, re.M | re.S)
    if not consignes:
        raise ValueError(f"Consignes absentes pour {rubrique} dans prompt.md")
    # Des listes vides evitent d'inciter le modele a remplir un faux element.
    schema = SCHEMA[rubrique]
    forme = gabarit(schema)
    valeurs = {"donnees_extraites": texte, "id_candidat": identifiant,
               "rubrique": rubrique, "consignes": consignes[1].strip(),
               "format_attendu": json.dumps({rubrique: forme}, ensure_ascii=False)}
    return re.sub(r"\{(donnees_extraites|id_candidat|rubrique|consignes|format_attendu)\}", lambda m: valeurs[m[1]], commun)


def appelle_ollama(message, modele, adresse="http://127.0.0.1:11434", schema=None):
    corps = {"model": modele, "stream": True, "format": schema or schema_json(),
             "messages": [{"role": "user", "content": message}],
             "options": OPTIONS}
    try:
        debut = time.perf_counter()
        with requests.post(adresse.rstrip("/") + "/api/chat", json=corps, timeout=(10, 240), stream=True) as reponse:
            reponse.raise_for_status()
            contenu = ""
            for ligne in reponse.iter_lines():
                if time.perf_counter() - debut > 240:
                    raise ValueError("Delai maximal de generation depasse")
                if not ligne:
                    continue
                fragment = json.loads(ligne)
                if fragment.get("error"):
                    raise ValueError(fragment["error"])
                contenu += fragment.get("message", {}).get("content", "")
                try:
                    objet = json.loads(contenu)
                except ValueError:
                    objet = None
                if isinstance(objet, dict):
                    # Certains petits modeles continuent a emettre des espaces apres
                    # leur JSON. Fermer le flux des que l'objet est complet suffit.
                    return {"message": {"content": contenu}, "done": True, "arret": "objet_json_complet",
                            "total_duration": int((time.perf_counter() - debut) * 1e9)}
                if fragment.get("done"):
                    break
            raise ValueError("Le flux ne contient aucun objet JSON complet")
    except (requests.RequestException, ValueError) as erreur:
        raise RuntimeError(f"Ollama indisponible ou reponse incorrecte. Lancer Ollama et verifier le modele {modele}. {erreur}") from erreur


def normalise_types(section):
    """Traduction lexicale des libelles de type ; aucune inference sur le poste."""
    changements = []
    if not isinstance(section.get("experiences"), list):
        return changements
    aliases = {"emploi_etudiant": "job_etudiant", "job_etudiant": "job_etudiant", "stage": "stage",
               "alternance": "alternance", "emploi": "emploi", "benevolat": "benevolat", "autre": "autre"}
    for numero, experience in enumerate(section["experiences"]):
        if isinstance(experience, dict) and isinstance(experience.get("type"), str):
            avant = experience["type"]
            code = normalise_texte(avant).replace(" ", "_")
            apres = aliases.get(code, avant)
            if avant != apres:
                experience["type"] = apres
                changements.append({"index": numero, "avant": avant, "apres": apres})
    return changements


def structure_cv(entree, dossier_sorties, prompt, modele="llama3.2:3b", autoriser_generation=True,
                 adresse="http://127.0.0.1:11434", appel=appelle_ollama):
    """Reutilise seulement un resultat dont les empreintes et le format correspondent."""
    dossier = Path(dossier_sorties)
    identifiant = entree["pdf"].stem
    destination = dossier / "json" / f"{identifiant}.json"
    chemin_provenance = dossier / "provenance.json"
    provenance = json.loads(chemin_provenance.read_text(encoding="utf-8")) if chemin_provenance.exists() else {}
    attendu = {"pdf_sha256": entree["pdf_sha256"], "texte_sha256": entree["texte_sha256"],
               "prompt_sha256": empreinte(prompt), "schema_sha256": empreinte(json.dumps(schema_json(), sort_keys=True)),
               "modele": modele, "moteur": "ollama", "strategie": "six_rubriques"}
    precedent = provenance.get(identifiant, {})
    if destination.exists() and all(precedent.get(k) == v for k, v in attendu.items()):
        cv = json.loads(destination.read_text(encoding="utf-8"))
        if not valide_cv(cv) and precedent.get("json_sha256") == empreinte(destination.read_bytes()):
            if cv["meta"] == {"id_candidat": identifiant, "fichier_source": entree["pdf"].name}:
                return cv, "cache modele verifie"
    if not autoriser_generation:
        raise ValueError(f"{identifiant} : cache absent, modifie ou perime. Activer AUTORISER_GENERATION et lancer Ollama.")
    if re.search(r"illisible|\[OCR", entree["texte"], re.I):
        raise ValueError(f"{identifiant} : texte signale comme illisible, verifier le PDF.")
    cv = gabarit(SCHEMA)
    cv["meta"] = {"id_candidat": identifiant, "fichier_source": entree["pdf"].name}
    journal = []
    for rubrique in GROUPES:
        intermediaire = dossier / ".travail" / f"{identifiant}.{rubrique}.json"
        if intermediaire.exists():
            sauvegarde = json.loads(intermediaire.read_text(encoding="utf-8"))
            candidat = {**cv, rubrique: sauvegarde.get("contenu")}
            if sauvegarde.get("sources") == attendu and not valide_cv(candidat):
                cv = candidat
                journal.append(sauvegarde["appel"])
                continue
        message = message_cv(prompt, entree["texte"], identifiant, rubrique)
        if rubrique in {"international", "engagements", "experiences"}:
            message += ("\nVérification finale : ne crée aucun élément pour remplir la liste. "
                        "Si aucun fait du CV ne correspond à cette rubrique, retourne exactement "
                        + json.dumps({rubrique: []}) + ". N'utilise aucun exemple des consignes comme fait du CV.")
        for tentative in range(2):
            try:
                resultat = appel(message, modele, adresse, schema_json({rubrique: SCHEMA[rubrique]}))
            except RuntimeError as erreur:
                if tentative == 0 and "aucun objet JSON complet" in str(erreur):
                    message += "\nLa réponse précédente était trop longue ou incomplète. Sois très bref, sans répétition, et ferme l'objet JSON."
                    continue
                raise
            brut = resultat.get("message", {}).get("content", "")
            try:
                section = json.loads(brut)
                if not isinstance(section, dict) or set(section) != {rubrique}:
                    raise ValueError(f"Un objet avec la seule cle {rubrique} est attendu")
                normalisations = normalise_types(section)
                candidat = {**cv, **section}
                erreurs = valide_cv(candidat)
                if erreurs:
                    raise ValueError("; ".join(erreurs))
            except (ValueError, TypeError) as erreur:
                dossier.mkdir(parents=True, exist_ok=True)
                (dossier / f"{identifiant}.{rubrique}.brut.txt").write_text(brut, encoding="utf-8")
                if tentative == 1:
                    raise ValueError(f"{identifiant}/{rubrique} : format refuse : {erreur}") from erreur
                message += "\nCorrige ces erreurs de format : " + str(erreur)
                continue
            cv = candidat
            details = {"rubrique": rubrique, "reponse_sha256": empreinte(brut), "tentatives": tentative + 1,
                            "normalisations_types": normalisations,
                            "tokens_entree": resultat.get("prompt_eval_count"), "tokens_sortie": resultat.get("eval_count"),
                            "options": OPTIONS, "message_sha256": empreinte(message),
                            "arret": resultat.get("arret", "fin_modele"),
                            "duree_secondes": round(resultat.get("total_duration", 0) / 1e9, 2)}
            journal.append(details)
            ecrit_json(intermediaire, {"sources": attendu, "contenu": cv[rubrique], "appel": details})
            break
    ecrit_json(destination, cv)
    provenance[identifiant] = {**attendu, "origine": "reponses_modele_assemblees", "fichier_source": entree["pdf"].name,
        "date_utc": datetime.now(timezone.utc).isoformat(), "json_sha256": empreinte(destination.read_bytes()), "appels": journal}
    ecrit_json(chemin_provenance, provenance)
    return cv, "genere par Ollama (6 rubriques)"
