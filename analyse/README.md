# Analyse des JSON courts

Ouvrir [analyse_cv.ipynb](../analyse_cv.ipynb) pour suivre les boucles de lecture,
les comptages, les tableaux, les graphiques et la comparaison aux références.

Les scripts utilisent exactement le même format :

```bash
python3 analyse/controle_coherence.py sorties/
python3 analyse/agrege.py sorties/
python3 analyse/stats.py
```

- `donnees.py` valide les types, les champs, les notes sur 20 et les doublons.
  Il signale les anciennes sorties contenant `donnees_normalisees`.
- `controle_coherence.py` applique cette validation à tout le dossier. Il ne
  vérifie pas la fidélité du JSON au texte ; cette comparaison reste à faire.
- `agrege.py` calcule les indicateurs en Python, puis exporte `candidats.csv`
  (une ligne par candidat) et `codes.csv` (langages et outils par candidat).
- `stats.py` affiche un résumé des CSV, avec les effectifs exploitables.
- `exemples/` contient trois JSON saisis à la main à partir des CV fictifs du
  projet. Ils permettent de tester sans modèle et ne sont pas ses réponses.

Une rubrique illisible produit des indicateurs inconnus, pas des zéros. Une
expérience de type inconnu empêche un comptage complet des stages ou jobs,
mais elle compte dans le nombre total d'expériences mentionnées.

Les graphiques comptent les compétences une seule fois par candidat après
uniformisation de la casse, des accents et des espaces. Les durées restent
textuelles : aucune conversion approximative en mois n'est appliquée.

Les exemples s'exportent avec `-o analyse/demo/`, puis s'analysent avec
`python3 analyse/stats.py -d analyse/demo/`. Les CSV de production et de
démonstration sont ignorés par Git.
