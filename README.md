# Analyse des CV — Albert School x Mines Paris PSL

Projet 3 — Matthieu, Clément, Henry, Ethan, Ilyes

Le modèle met les informations des CV en **JSON court**. Les indicateurs sont
calculés en Python dans [analyse_cv.ipynb](analyse_cv.ipynb), avec des boucles
`for`, des tableaux pandas et des graphiques commentés.

## Ouvrir le notebook

Depuis la racine du projet :

```bash
python3 -m pip install -r extraction/requirements.txt
```

Ouvrir **`analyse_cv.ipynb`** dans VS Code, sélectionner l'interpréteur Python
utilisé pour l'installation, puis **Exécuter tout**.

- Si `sorties/` contient des JSON, le notebook les analyse.
- Sinon, il utilise **trois exemples saisis à la main** dans `analyse/exemples/`,
  issus des CV fictifs de test. Ce mode est signalé dans le notebook et les
  graphiques. Aucun appel API n'est effectué par le notebook.
- Un fichier invalide ou un candidat en double arrête l'analyse avec une erreur.
- Les exports des exemples vont dans `analyse/demo/` ; ceux des réponses du
  modèle vont dans `analyse/`.

## Le flux

```text
cv-test/*.pdf
    → extraction/extrait_texte.py
    → datas_extract/*.txt
    → extraction/pipeline.py + prompt.md
    → sorties/*.json
    → analyse_cv.ipynb : boucles, tableau, graphiques, comparaison aux références
```

Chaque fait apparaît une seule fois dans le JSON. Le bloc
`donnees_normalisees` et les compteurs produits par le modèle sont supprimés.
Le notebook calcule les nombres de langages, de stages, de projets, etc.
Les textes source restent dans `datas_extract/` pour contrôler les informations.

Une liste vide dans une rubrique lisible donne zéro élément **mentionné**.
Une rubrique illisible donne une valeur inconnue, exclue du calcul concerné.
Les graphiques et pourcentages précisent leur effectif exploitable.
Les résultats scolaires conservent leur intitulé : une moyenne de terminale
n'est pas confondue avec une note au bac.

## Produire des réponses avec le modèle

L'extraction des PDF avec couche texte est gratuite. Les scans demandent un
OCR séparé. L'appel au modèle nécessite une clé API et est facturé.

```bash
python3 extraction/extrait_texte.py
python3 extraction/pipeline.py --texte-seul  # vérifie les entrées sans appel
export OPENAI_API_KEY="votre-cle-api"
python3 extraction/pipeline.py --limite 2    # génère les JSON de 2 CV
python3 extraction/pipeline.py              # traite les CV restants
```

Le modèle par défaut est `gpt-4o-mini` (`--modele` pour le modifier).
Les JSON sont validés avant enregistrement. Une réponse incorrecte est gardée
à part dans un fichier `.brut.txt` et le programme renvoie une erreur.

**Anciennes sorties :** les JSON contenant `donnees_normalisees` ne sont plus
compatibles. Le programme les signale ; `--force` permet de les régénérer avec
le nouveau prompt. Sauvegarder les anciennes réponses si elles doivent être
conservées. Les CSV dérivés se régénèrent avec les nouveaux JSON.

Aucun appel au modèle n'a été effectué lors de cette refonte. Les trois exemples
servent à vérifier le code, pas à mesurer la qualité d'extraction du modèle.

## Version en scripts

Le notebook montre les calculs étape par étape. Les mêmes étapes restent
accessibles en ligne de commande :

```bash
python3 analyse/controle_coherence.py sorties/
python3 analyse/agrege.py sorties/
python3 analyse/stats.py
```

Pour tester sans API sur les exemples :

```bash
python3 analyse/controle_coherence.py analyse/exemples/
python3 analyse/agrege.py analyse/exemples/ -o analyse/demo/
python3 analyse/stats.py -d analyse/demo/
python3 -m unittest discover -s tests -v
```

`run.py` conserve les étapes `txt`, `llm`, `controle`, `agrege`, `stats`.
`python3 run.py --jusqua txt` n'effectue que l'extraction texte.
`python3 run.py --limite 2` inclut des appels au modèle.

## Fichiers

| Fichier ou dossier | Rôle |
|---|---|
| [analyse_cv.ipynb](analyse_cv.ipynb) | analyse expliquée avec boucles `for` |
| [prompt.md](prompt.md) | format JSON court et consignes au modèle |
| [datas_extract/](datas_extract/) | 11 textes extraits des CV de test |
| [sorties/](sorties/) | réponses JSON du modèle |
| [analyse/exemples/](analyse/exemples/) | 3 exemples manuels pour la démonstration |
| [analyse/donnees.py](analyse/donnees.py) | schéma, validation et nettoyage simple |
| [analyse/](analyse/) | validation, agrégation et statistiques en scripts |
| [grille-notation-cv.md](grille-notation-cv.md) | grille de notation de référence |

Les notes dans `cv-test/notes-reference.csv` sont utilisées **après** le
traitement pour une comparaison descriptive. Elles ne sont pas envoyées au
modèle. Ce notebook n'attribue pas automatiquement de note d'admission.
