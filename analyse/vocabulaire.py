"""Vocabulaire ferme du bloc donnees_normalisees.

Source unique de verite pour les scripts d'analyse. Doit rester synchronise
avec la section "BLOC donnees_normalisees" de prompt.md : si on ajoute une
valeur d'un cote, il faut l'ajouter de l'autre, sinon le controle de coherence
signalera comme invalides des valeurs que le prompt autorise.
"""

BAC_FILIERE = {"generale", "technologique", "professionnelle", "etranger", "autre"}
BAC_MENTION = {
    "sans_mention",
    "assez_bien",
    "bien",
    "tres_bien",
    "tres_bien_felicitations",
    "autre",
}
PREPA_FILIERE = {"MPSI", "PCSI", "PTSI", "MP2I", "BCPST", "ECG", "BL", "autre"}
NIVEAU_ETUDES = {
    "terminale",
    "bac",
    "bac+1",
    "bac+2",
    "bac+3",
    "bac+4",
    "bac+5",
    "autre",
}
SPECIALITES = {
    "maths",
    "nsi",
    "physique_chimie",
    "svt",
    "ses",
    "hggsp",
    "llce",
    "hlp",
    "arts",
    "si",
    "autre",
}
SPECIALITES_SCIENTIFIQUES = {"maths", "nsi", "physique_chimie", "svt", "si"}
LANGAGES = {
    "python",
    "sql",
    "r",
    "java",
    "javascript",
    "c",
    "cpp",
    "matlab",
    "sas",
    "vba",
    "autre",
}
OUTILS = {
    "excel",
    "power_bi",
    "tableau",
    "git",
    "pandas",
    "sklearn",
    "tensorflow",
    "pytorch",
    "spark",
    "figma",
    "autre",
}
CECRL = {"A1", "A2", "B1", "B2", "C1", "C2", "natif"}
TESTS_ANGLAIS = {"toefl_ibt", "toeic", "ielts", "cambridge", "autre"}
ENGAGEMENT_TYPES = {
    "bde",
    "junior_entreprise",
    "association",
    "sport",
    "entrepreneuriat",
    "mandat_electif",
    "humanitaire",
    "autre",
}
COMPLETUDE = {"renseigne", "absent_confirme", "illisible"}

# Les rubriques qui ont un statut de completude, dans l'ordre du prompt.
RUBRIQUES = [
    "formation",
    "quantitatif",
    "competences_tech",
    "langues",
    "experiences",
    "engagement",
    "international",
]

# Les champs de type liste, et le vocabulaire qui s'y applique.
CHAMPS_LISTES = {
    "quantitatif.specialites_codes": SPECIALITES,
    "tech.langages_codes": LANGAGES,
    "tech.outils_codes": OUTILS,
    "engagement.types_codes": ENGAGEMENT_TYPES,
    "langues.autres_langues_codes": None,  # codes ISO 639-1, liste ouverte
    "international.pays_codes": None,  # codes ISO 3166-1, liste ouverte
}
