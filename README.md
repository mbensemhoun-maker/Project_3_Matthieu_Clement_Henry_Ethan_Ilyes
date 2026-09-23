# Notation automatique de CV — Albert School x Mines Paris PSL

Projet 3 — Matthieu, Clément, Henry, Ethan, Ilyes

Chaîne qui part d'un CV de candidat en PDF et produit deux choses : les
informations nécessaires pour le noter, et des données comparables d'un
candidat à l'autre pour faire des statistiques sur la promo.

## Le flux

```
  cv-test/*.pdf
        │
        │  OCR                                    ← à brancher
        ▼
   texte brut
        │
        │  prompt.md                              ← à brancher (appel LLM)
        ▼
  sorties/*.json          un fichier par CV, deux blocs :
        │                   · verbatim        → sert à noter
        │                   · normalisé       → sert à compter
        │
        ├──────────────► analyse/controle_coherence.py
        │                  les deux blocs se contredisent-ils ?
        │
        ▼
  analyse/agrege.py
        │
        ├─► analyse/candidats.csv    une ligne par candidat
        └─► analyse/codes.csv        format long pour les champs listes
                │
                ▼
         analyse/stats.py
           statistiques de promo + croisement avec les notes de référence
```

Deux étapes restent à brancher : l'OCR et l'appel LLM. Tout ce qui est en aval
existe et tourne, sur des CV fabriqués à la main en attendant les vrais.

## Pourquoi deux blocs dans le JSON

Le JSON produit sert à deux usages qui s'opposent.

**Noter un candidat** demande du verbatim. Le correcteur a besoin du CV tel
qu'il est écrit, sans reformulation qui pourrait déformer un fait. D'où la règle
centrale du prompt : ne déduis pas, n'interprète pas, recopie.

**Faire des statistiques** demande l'inverse. « TB », « Très bien » et
« mention très bien » sont la même information, mais trois chaînes différentes,
donc trois lignes dans un `value_counts()`. Inagrégeable sur une promo.

D'où la structure : les blocs verbatim restent intacts, et `donnees_normalisees`
rejoue les mêmes informations dans un vocabulaire fermé — enums, compteurs,
codes ISO. On ne remplace rien, on duplique. Si le recodage se trompe,
l'original est encore là pour rattraper.

## Absence n'est pas illisible

Un candidat qui n'a pas fait de stage et un CV dont la rubrique expérience n'a
pas été lue par l'OCR produisent tous les deux un champ vide. Ils ne doivent pas
être traités pareil :

- pour **la notation**, la grille dit qu'une expérience rare absente ne se note
  pas 0 d'office — mais une rubrique illisible ne devrait rien coûter du tout ;
- pour **les statistiques**, « 40 % des candidats n'ont pas fait de stage » est
  faux si 15 % des CV avaient la rubrique illisible. Deux populations sans
  rapport, additionnées.

Le JSON les distingue à deux endroits : `qualite_extraction.sections_illisibles`
liste les rubriques vues mais inexploitables, et `donnees_normalisees.completude`
donne par rubrique `renseigne` / `absent_confirme` / `illisible`. Les scripts de
stats excluent les rubriques illisibles de chaque base de calcul et affichent
combien de CV ont été écartés.

## Fichiers

| Fichier | Rôle |
|---|---|
| [prompt.md](prompt.md) | le prompt d'extraction, avec son format de sortie et ses règles |
| [grille-notation-cv.md](grille-notation-cv.md) | la grille de notation sur 20, 8 critères pondérés |
| [cv-test/](cv-test/) | 11 CV de test + `notes-reference.csv`, les notes attendues |
| [sorties/](sorties/) | les JSON d'extraction, un par CV — vide pour l'instant |
| [analyse/](analyse/) | contrôle de cohérence, agrégation, statistiques |

## Lancer la chaîne

Une fois les JSON dans `sorties/` :

```bash
python3 analyse/controle_coherence.py sorties/   # les JSON sont-ils fiables ?
python3 analyse/agrege.py sorties/               # → candidats.csv + codes.csv
python3 analyse/stats.py                         # → le rapport de promo
```

Sans JSON, les scripts tournent sur les fixtures :

```bash
python3 analyse/controle_coherence.py analyse/fixtures
python3 analyse/agrege.py analyse/fixtures && python3 analyse/stats.py
```

Dépendance : `pandas`.

## Contrôler avant de compter

`controle_coherence.py` vérifie que le bloc normalisé ne contredit pas le
verbatim **du même JSON**. Le bloc normalisé ne fait que recoder ce qui a déjà
été extrait : toute valeur normalisée sans appui dans le verbatim est une
invention, et ça se détecte mécaniquement, sans relire le CV ni avoir de vérité
terrain.

Ce qu'il ne fait pas : dire si l'extraction est *juste*. Un CV dont la mention a
été mal lue passera le contrôle sans broncher, tant que le bloc normalisé
recopie fidèlement cette erreur. La justesse se vérifie en comparant au PDF, et
`cv-test/notes-reference.csv` est là pour ça.

Il retourne 1 s'il reste une erreur, donc il peut servir de garde avant de
publier des statistiques.

## État d'avancement

Fait :

- [x] grille de notation v2, avec repondération des critères
- [x] prompt d'extraction v4, verbatim + bloc normalisé + qualité d'extraction
- [x] contrôle de cohérence, testé sur 3 CV fabriqués
- [x] agrégation en CSV et statistiques descriptives

À faire :

- [ ] OCR des PDF vers du texte brut
- [ ] appel LLM qui applique `prompt.md` et écrit dans `sorties/`
- [ ] faire tourner la chaîne sur les 11 CV de `cv-test/`
- [ ] comparer les notes obtenues à `notes-reference.csv`
- [ ] l'étape de notation elle-même : rien ne note encore, le prompt extrait
      seulement

## Points ouverts

- **Notation en un ou deux temps ?** Aujourd'hui le prompt extrait sans noter.
  Reste à décider si la notation est un second appel LLM sur le JSON, des règles
  déterministes sur les champs normalisés, ou un mélange : la grille signale
  elle-même que les critères 1, 2 et 4 sont factuels et que les critères 3, 5, 6
  et 8 demandent du jugement.
- **Le bloc normalisé dans le même appel ?** Un second appel qui prendrait le
  JSON verbatim en entrée, sans accès au CV, ne pourrait rien inventer de neuf.
  Coût : un appel de plus.
- **`analyse/vocabulaire.py` duplique les listes de valeurs de `prompt.md`.**
  Si quelqu'un en élargit une sans l'autre, le contrôle rejettera des valeurs
  pourtant valides.
- **Le vocabulaire fermé va manquer de valeurs** (outils, pays, spécialités
  étrangères). Compter la fréquence de `"autre"` par champ sur un vrai lot dira
  s'il faut élargir les listes.
