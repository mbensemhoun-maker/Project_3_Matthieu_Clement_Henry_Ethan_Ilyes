# CV d’admission — Albert School

**Ouvrir [analyse_cv.ipynb](analyse_cv.ipynb) et exécuter toutes les cellules.**
Le notebook lit les PDF, conserve les textes, utilise Ollama pour les JSON,
calcule les indicateurs et une **note pédagogique expliquée sur 20**, puis
exporte une synthèse factuelle par candidat.

## Lancer le projet

Depuis le dossier du projet :

```bash
python3 -m pip install -r requirements.txt
```

Dans VS Code/Jupyter, choisir cet environnement Python comme noyau puis
**Exécuter tout** dans `analyse_cv.ipynb`.

- Les JSON déjà produits sur les 11 CV fictifs sont fournis avec leur provenance.
  Leur relecture fonctionne sans Ollama si leurs empreintes correspondent.
- Pour traiter un nouveau CV, le placer dans `cv-test/`, lancer Ollama avec
  `llama3.2:3b`, passer `AUTORISER_GENERATION = True` dans le notebook, puis
  le relancer. Six appels locaux sont faits par CV,
  un par rubrique. Aucun abonnement ni clé API n’est utilisé par le code.
- `AUTORISER_GENERATION = False` dans le notebook interdit tout nouvel appel.
- Un PDF scanné sans texte exige un OCR séparé : le notebook le signale et s’arrête.

## Où sont les fichiers ?

| Élément | Rôle |
|---|---|
| `analyse_cv.ipynb` | seul point d’entrée, étapes expliquées et graphiques |
| `prompt.md` | consignes au modèle, rubrique par rubrique |
| `grille-notation-cv.md` | huit critères, règles, gestion des informations manquantes |
| `src/` | trois modules : données, lecture/modèle, notation/synthèse |
| `cv-test/` | 11 PDF fictifs et notes de référence pour comparaison finale |
| `datas_extract/` | textes lus dans les PDF, conservés pour contrôler les faits |
| `sorties/json/` | réponses du modèle assemblées en un JSON par CV |
| `sorties/` | provenance, tableaux, synthèses et rapport de vérification |
| `tests/` | contrôles et exemples manuels, jamais utilisés à la place du modèle |

## Lire le résultat

`sorties/candidats.csv` : une ligne par candidat, note sur 20 et points à vérifier.
`sorties/criteres.csv` : huit sous-notes par candidat, règles, faits et sources.
`sorties/syntheses.md` : synthèses individuelles lisibles.
`sorties/relectures.json` : corrections documentées, avec extraits et empreintes des sources.
`sorties/validation.md` : contrôles réellement effectués et limites constatées.

Le petit modèle installé fait des erreurs. Sur le lot livré, une relecture par
l’assistant corrige les faits avant notation, avec chaque correction conservée
séparément. Les réponses originales restent intactes. Un nouveau CV porte le
statut « non relu » ; une nouvelle génération rend les anciennes corrections
périmées. La validation humaine de l’équipe reste nécessaire.

Le barème détaillé est une **proposition pédagogique à valider**. Les références
sont comparées après calcul et ne sont pas envoyées au modèle. Les points à vérifier
ne sont pas ajoutés à la note. Une note ne constitue pas une décision d’admission.

## Vérifier le code

```bash
python3 -m unittest discover -s tests -v
```

Les sorties de démonstration concernent uniquement les CV fictifs du dépôt.
Documentation de l’API locale : [sorties structurées Ollama](https://docs.ollama.com/capabilities/structured-outputs).
