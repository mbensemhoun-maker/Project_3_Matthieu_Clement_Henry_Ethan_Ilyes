"""Bareme pedagogique deterministe. Chaque point est accompagne d'une regle.

Les notes de reference ne sont jamais lues ici. Les points a verifier ne sont
ni offerts ni convertis en penalites : ils forment une marge explicite.
"""

import re

from .donnees import mention_standard, normalise_texte, nom_competence

CRITERES = {
    "academique": ("Excellence académique", 6),
    "quantitatif": ("Aptitude quantitative", 4),
    "tech": ("Compétences data / tech", 2),
    "langues": ("Anglais et langues", 2),
    "experience": ("Expérience professionnelle", 3),
    "engagement": ("Engagement et responsabilités", 2),
    "international": ("Ouverture internationale", 0.5),
    "coherence": ("Liens factuels avec Business & Data", 0.5),
}


def contient(texte, motif):
    return bool(re.search(motif, normalise_texte(texte)))


def decrit(elements):
    """Descriptions courtes issues du JSON, sans evaluation qualitative du LLM."""
    lignes = []
    for element in elements:
        if isinstance(element, dict):
            valeurs = [str(v) for v in element.values() if v is not None]
            lignes.append(" — ".join(valeurs))
        else:
            lignes.append(str(element))
    return "; ".join(lignes) or "Aucun élément mentionné."


def note_maths(resultats):
    """Une moyenne explicite ; sinon le trimestre le plus recent identifie.

    On ne choisit jamais la meilleure des notes et on ne melange pas les types
    d'epreuves. Plusieurs notes sans ordre clair imposent une verification.
    """
    notes = [r for r in resultats if contient(r["intitule"], r"\bmath(?:s|ematiques)?\b") and r["note_sur_20"] is not None]
    if len(notes) == 1:
        return notes[0]["note_sur_20"], notes[0]["intitule"]
    trimestres = []
    for resultat in notes:
        libelle = normalise_texte(resultat["intitule"])
        trimestre = None
        for numero, motif in [(1, r"premier|1er|trimestre\s*1|\bt1\b"),
                              (2, r"deuxieme|2e|second|trimestre\s*2|\bt2\b"),
                              (3, r"troisieme|3e|dernier trimestre|trimestre\s*3|\bt3\b")]:
            if re.search(motif, libelle):
                trimestre = numero
        if trimestre:
            trimestres.append((trimestre, resultat))
    if len(trimestres) == len(notes) and trimestres:
        dernier = max(t for t, _ in trimestres)
        selection = [r for t, r in trimestres if t == dernier]
        if len(selection) == 1:
            return selection[0]["note_sur_20"], selection[0]["intitule"]
    return None, "Note de mathématiques absente ou plusieurs résultats sans ordre univoque."


def points_anglais(langues):
    anglais = [l for l in langues if normalise_texte(l["langue"]) in {"anglais", "english"}]
    if len(anglais) != 1:
        return 0, 1.5, "Anglais absent ou décrit plusieurs fois : niveau à vérifier."
    langue = anglais[0]
    niveau = " ".join(v for v in [langue["niveau"], langue["certification"]] if v)
    for motif, points in [(r"\bc[12]\b", 1.5), (r"\bb2\b", 1), (r"\bb1\b", 0.75),
                           (r"\ba[12]\b|scolaire|notions|debutant", 0.5)]:
        if contient(niveau, motif):
            return points, 0, f"Niveau explicitement annoncé : {niveau} (déclaratif sauf certificat vérifié)."
    test = normalise_texte(langue["certification"] or "")
    score = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*", langue["score"] or "")
    if score:
        valeur, maximum = [float(x.replace(",", ".")) for x in score.groups()]
        baremes = [("toefl", 120, [100, 80, 60]), ("toeic", 990, [900, 750, 550]), ("ielts", 9, [7, 6, 5])]
        for nom, echelle, seuils in baremes:
            if nom in test and maximum == echelle and 0 <= valeur <= maximum:
                points = 0.5
                for seuil, credit in zip(seuils, [1.5, 1, 0.75]):
                    if valeur >= seuil:
                        points = credit
                        break
                return points, 0, f"Barème du projet pour {langue['certification']} {langue['score']} ; aucune conversion CECRL."
    return 0, 1.5, "Niveau ou échelle du test d'anglais non exploitable : à vérifier."


def evalue_cv(cv):
    """Huit lignes expliquent le score et les points restant a verifier."""
    formation, competences = cv["formation"], cv["competences"]
    illisibles = set(cv["rubriques_illisibles"])
    lignes = []

    def ajoute(cle, points, reserve, faits, regle, verifier="", rubriques=()):
        label, poids = CRITERES[cle]
        if illisibles.intersection(rubriques):
            points, reserve = 0, poids
            verifier = "Rubrique illisible : vérifier le PDF avant de noter."
        if not 0 <= points <= poids or not 0 <= reserve <= poids - points:
            raise ValueError(f"Barème incohérent pour {cle}")
        lignes.append({"id_candidat": cv["meta"]["id_candidat"], "critere": cle, "libelle": label,
                       "poids": poids, "points": points, "points_a_verifier": reserve,
                       "faits": faits, "regle": regle, "a_verifier": verifier,
                       "source": "datas_extract/" + cv["meta"]["fichier_source"].removesuffix(".pdf") + ".txt"})

    mention = mention_standard(formation["mention_bac"])
    points = {"tres bien": 6, "bien": 4.5, "assez bien": 3.5, "sans mention": 2}.get(mention)
    ajoute("academique", points or 0, 6 if points is None else 0,
           decrit([formation[k] for k in ["filiere_bac", "mention_bac", "etablissement", "anomalies_parcours"] if formation[k]]),
           "Mention explicite : TB 6 ; B 4,5 ; AB 3,5 ; sans mention 2. Aucun point lié à la réputation du lycée ou au redoublement.",
           "Mention du bac à renseigner ou préciser." if points is None else "Vérifier la mention sur le justificatif académique.", ("formation",))

    specialites = " ; ".join(formation["specialites"])
    maths = contient(specialites, r"\bmath(?:s|ematiques)?\b")
    scientifique = contient(specialites, r"\bnsi\b|numerique.*informatique|physique|sciences de l.ingenieur")
    concours = any(contient(c, r"math|physique|scientifique|informatique|\bscience") for c in formation["concours"])
    note, contexte = note_maths(formation["resultats"])
    bonus_note = 0 if note is None or note < 10 else 0.5 if note < 12 else 0.75 if note < 14 else 1 if note < 16 else 1.5
    points = 1.5 * maths + 0.5 * scientifique + 0.5 * concours + bonus_note
    ajoute("quantitatif", points, 1.5 if note is None else 0,
           decrit(formation["specialites"] + formation["concours"] + formation["resultats"]),
           "Maths en spécialité +1,5 ; autre spécialité scientifique +0,5 ; concours scientifique +0,5 ; note de maths jusqu'à +1,5.",
           contexte + (f" : {note}/20 retenu." if note is not None else " Aucun remplacement par la moyenne générale."), ("formation",))

    langages = {nom_competence(x) for x in competences["langages"]}
    langage = bool(langages.intersection({"python", "sql", "r", "javascript", "java", "c", "c++", "html", "css", "typescript", "matlab", "julia"}))
    outil = any(contient(o, r"power\s*bi|tableau|pandas|numpy|matplotlib|excel.*(?:avance|tcd|crois|recherchev)") for o in competences["outils"])
    projets = [p for p in competences["projets"] if contient(p, r"data|donnee|python|sql|code|web|html|css|excel|kaggle|modele|scrap")]
    projet = max([0.25 if contient(p, r"non finalise|non acheve|en cours|pas de mise en ligne|commence") else 0.5 for p in projets], default=0)
    certification = any(contient(c, r"data|python|sql|machine learning|analyse") and not contient(c, r"en cours|non obtenu|prepare") for c in competences["certifications"])
    ajoute("tech", 0.5 + 0.5 * langage + 0.25 * outil + projet + 0.25 * certification, 0,
           decrit(sum(competences.values(), [])),
           "Socle 0,5 ; langage +0,5 ; outil data/Excel avancé +0,25 ; projet +0,5 (+0,25 si inachevé) ; certification data obtenue +0,25.",
           "Les niveaux sont déclarés. Contrôler les projets et certificats ; une technologie hors liste demande une revue.", ("competences",))

    anglais, reserve, commentaire = points_anglais(cv["langues"])
    autre = any(normalise_texte(l["langue"]) not in {"anglais", "english", "francais", "french"} for l in cv["langues"])
    ajoute("langues", anglais + 0.5 * autre, reserve, decrit(cv["langues"]),
           "Anglais jusqu'à 1,5 selon le niveau ou le score explicite ; autre langue mentionnée +0,5.", commentaire, ("langues",))

    experiences = [e for e in cv["experiences"] if e["type"] in {"stage", "alternance", "job_etudiant", "emploi"}]
    inconnu = any(e["type"] is None for e in cv["experiences"])
    missions = any(e["missions"] and not contient(e["missions"], r"^(?:observation|decouverte)(?: seule(?:ment)?)?[.!]?$" ) for e in experiences)
    regulier = any(contient(e["duree"] or "", r"regulier|samed|dimanch|week.end|deux etes|deux annees|(?:[4-9]|\d{2,}) semaines?|(?:un|une|[1-9]\d*) mois|par semaine") for e in experiences)
    points = 0.5 + 0.75 * bool(experiences) + 0.75 * (len(experiences) >= 2) + 0.5 * missions + 0.5 * regulier
    reserve = 3 - points if inconnu else (0.5 if experiences and not regulier and any(not e["duree"] for e in experiences) else 0)
    ajoute("experience", points, reserve, decrit(cv["experiences"]),
           "Socle 0,5 ; première expérience +0,75 ; deuxième +0,75 ; missions décrites +0,5 ; régularité ou durée explicite suffisante +0,5.",
           "Type ou durée à préciser." if reserve else "Durées conservées telles qu'écrites ; pas de conversion approximative des dates.", ("experiences",))

    responsables = [e for e in cv["engagements"] if contient(e["role"], r"president|tresori|capitaine|fondateur|secretaire|responsable|coordinateur") and not contient(e["role"], r"sans|aucun|pas de")]
    action = any(e["description"] and contient(e["description"], r"organis|gestion|animation|budget|equipe|accompagn|creation|encadre|financ") for e in responsables)
    ajoute("engagement", 0.5 * bool(cv["engagements"]) + 0.75 * bool(responsables) + 0.75 * action, 0,
           decrit(cv["engagements"]), "Activité collective +0,5 ; responsabilité explicite +0,75 ; action associée décrite +0,75.",
           "Les loisirs individuels seuls ne constituent pas un engagement collectif.", ("engagements",))

    etudes = any(contient(i["motif"], r"echange|scolaire|etude|linguistique|immersion|universit") for i in cv["international"])
    ajoute("international", 0.25 + 0.25 * etudes, 0, decrit(cv["international"]),
           "Socle 0,25 même sans séjour ; séjour d'études/échange/immersion explicite +0,25. Aucun point pour la nationalité.",
           "Motif du séjour à vérifier s'il est ambigu.", ("international",))

    domaines = {
        "formation": contient(specialites, r"math|\bnsi\b|\bses\b|gestion|finance|informatique"),
        "competences": langage or outil or bool(projets),
        "experiences": any(contient(e["missions"] or "", r"donnee|data|python|sql|comptab|commercial|vente|client|gestion|marche") for e in experiences),
    }
    liens = [k for k, valeur in domaines.items() if valeur and k not in illisibles]
    points = min(0.5, 0.25 * len(liens))
    reserve = 0.5 - points if illisibles.intersection(domaines) else 0
    ajoute("coherence", points, reserve, "Rubriques avec un lien explicite : " + (", ".join(liens) or "aucune"),
           "+0,25 par rubrique reliée à Business & Data, plafond 0,5. Indicateur de liens factuels, sans jugement sur la motivation.",
           "La cohérence du projet personnel reste à discuter avec le candidat.")
    return lignes


def totalise(criteres):
    """La somme reste sur 20 ; aucune renormalisation des informations manquantes."""
    points, reserve = 0, 0
    for critere in criteres:
        points += critere["points"]
        reserve += critere["points_a_verifier"]
    return round(points, 2), round(reserve, 2)


def synthese_markdown(cv, criteres, origine):
    points, reserve = totalise(criteres)
    identifiant = cv["meta"]["id_candidat"]
    lignes = [f"## {identifiant}", "", f"**Note pédagogique provisoire : {points:g}/20. Points restant à vérifier : {reserve:g}.**",
              f"Origine des données : {origine}. Source : `datas_extract/{identifiant}.txt`.", "",
              "Les points à vérifier ne sont pas ajoutés à la note ; ils indiquent son incertitude liée aux données.", ""]
    for critere in criteres:
        lignes.extend([f"### {critere['libelle']} — {critere['points']:g}/{critere['poids']:g}", "",
                       critere["faits"], "", "Règle : " + critere["regle"],
                       "À vérifier : " + critere["a_verifier"], ""])
    manquants = []
    for rubrique in ["experiences", "engagements", "international"]:
        if not cv[rubrique]:
            manquants.append(rubrique + " : aucun élément mentionné")
    for critere in criteres:
        if critere["points_a_verifier"]:
            manquants.append(critere["libelle"] + " : " + critere["a_verifier"])
    lignes.extend(["### Informations manquantes", "", *(["- " + x for x in manquants] or ["- Aucune information bloquante identifiée par les règles."]), "",
                   "Note indicative à relire avec les pièces du dossier ; aucune décision d'admission automatique.", ""])
    return "\n".join(lignes)
