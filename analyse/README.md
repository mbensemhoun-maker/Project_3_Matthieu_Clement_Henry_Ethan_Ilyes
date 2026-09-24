# Analyse — des JSON d'extraction aux statistiques

Chaîne en trois étapes. Elle part d'un dossier de JSON produits par
[prompt.md](../prompt.md), un fichier par CV.

```
sorties/*.json  →  controle_coherence.py  →  agrege.py  →  stats.py
                   (valide)                  (aplatit)     (compte)
```

## Étape manquante

Rien ne produit encore les JSON. Il faut brancher le pipeline OCR + appel LLM
qui lit `cv-test/*.pdf`, applique le prompt et écrit un JSON par CV dans
`sorties/`. En attendant, les scripts tournent sur `analyse/fixtures/`, trois
CV fabriqués à la main.

Convention de nommage attendue : un JSON par CV, `meta.fichier_source` rempli
avec le nom du PDF (`01_lea_vasseur.pdf`). C'est cette valeur qui permet le
croisement avec `cv-test/notes-reference.csv`.

## 1. Contrôler

```
python3 analyse/controle_coherence.py sorties/
```

Vérifie que `donnees_normalisees` ne contredit pas le verbatim **du même
JSON**. Le bloc normalisé est censé recoder ce qui a déjà été extrait, sans
rien ajouter : toute valeur normalisée sans appui dans le verbatim est une
invention, et ça se vérifie sans relire le CV.

Ce que le script ne fait pas : dire si l'extraction est *juste*. Un CV dont la
mention a été mal lue par l'OCR passera le contrôle sans broncher, tant que le
bloc normalisé recopie fidèlement cette erreur. Pour la justesse, il faut
comparer au PDF.

Deux sévérités : `ERREUR` (contradiction ou invention — le chiffre est faux) et
`ALERTE` (suspect mais explicable). Code de retour 1 s'il reste une erreur, donc
utilisable comme garde avant de publier des stats.

Test sur les fixtures :

```
python3 analyse/controle_coherence.py analyse/fixtures
```

`demo_01` est cohérent et doit passer. `demo_02` cumule 20 erreurs (mention mal
recodée, prépa inventée, compteurs faux, completude contradictoire). `demo_03`
a le gabarit du prompt recopié tel quel — des listes de longueur 1 dont tous les
champs sont `null`, qui fausseraient tous les comptages d'une unité si on ne les
filtrait pas.

## 2. Agréger

```
python3 analyse/agrege.py sorties/
```

Écrit deux fichiers dans `analyse/` :

- **`candidats.csv`** — une ligne par candidat, une colonne par champ scalaire
  de `donnees_normalisees`, préfixée par son bloc (`academique_bac_mention`).
- **`codes.csv`** — format long `(id_candidat, champ, code)` pour les champs qui
  sont des listes. Une colonne de listes dans un CSV ne se compte pas ;
  en format long, `value_counts()` suffit.

Le verbatim n'est pas aplati : il n'est pas comparable d'un CV à l'autre, c'est
toute la raison d'être de `donnees_normalisees`.

## 3. Compter

```
python3 analyse/stats.py
```

Profil académique, tech, langues, expérience, engagement, et croisement avec
`cv-test/notes-reference.csv` quand les fichiers s'apparient.

**Chaque pourcentage exclut les CV dont la rubrique est illisible**, et affiche
combien ont été écartés. Sans ce filtre, « 40 % des candidats n'ont pas fait de
stage » additionne ceux qui n'en ont pas fait et ceux dont la rubrique
expérience n'a pas été lue — deux populations qui n'ont rien à voir. C'est la
raison d'être du bloc `completude`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `vocabulaire.py` | les valeurs autorisées, **à garder synchronisées avec `prompt.md`** |
| `controle_coherence.py` | validation normalisé ↔ verbatim |
| `agrege.py` | JSON → `candidats.csv` + `codes.csv` |
| `stats.py` | statistiques descriptives |
| `fixtures/` | 3 CV fabriqués pour tester les scripts sans pipeline |

`candidats.csv` et `codes.csv` sont des fichiers dérivés, régénérables, et
git-ignorés.

## Point de vigilance

`vocabulaire.py` duplique les listes de valeurs qui sont dans `prompt.md`. Si
quelqu'un élargit une liste d'un côté sans l'autre, le contrôle signalera comme
invalides des valeurs que le prompt autorise. À terme, mieux vaudrait générer la
section du prompt depuis `vocabulaire.py` que maintenir les deux à la main.
