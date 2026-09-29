# Documentation pour la présentation orale

## 1. Le projet en une phrase

Ce projet construit une chaîne reproductible qui lit des CV au format PDF,
utilise un modèle de langage local pour en extraire des faits structurés, applique
une relecture traçable, puis calcule avec du code Python une note pédagogique
expliquée sur 20.

La séparation essentielle à présenter est la suivante :

> **Ollama extrait et organise les faits ; Python contrôle les données et calcule
> la note. Le modèle de langage ne décide jamais de la note.**

Le projet traite 11 CV fictifs. Il ne prend aucune décision automatique
d'admission : le résultat est une aide à l'analyse qui doit être relue.

## 2. Problème traité et objectifs

Le traitement manuel d'un ensemble de CV est long et peut produire des décisions
difficiles à expliquer. Le projet cherche donc à :

- extraire les informations utiles de plusieurs mises en page de CV ;
- représenter tous les candidats avec le même schéma JSON ;
- appliquer les mêmes règles à tous les dossiers ;
- rendre chaque point de la note explicable ;
- signaler les informations absentes ou ambiguës ;
- conserver les sources, les corrections et la provenance des résultats ;
- pouvoir relancer l'analyse sans appeler inutilement le modèle.

Le système n'a pas pour objectif de remplacer un jury. Il automatise une partie
factuelle et répétitive, mais conserve une étape de relecture humaine.

## 3. Architecture générale

```text
cv-test/*.pdf
      |
      v
extrait_pdf() ----------------------> datas_extract/*.txt
      |
      v
structure_cv() + prompt.md + Ollama
      |
      +-----------------------------> sorties/json/*.json
      +-----------------------------> sorties/provenance.json
      |
      v
applique_relecture() <-------------- sorties/relectures.json
      |
      v
evalue_cv() puis totalise()
      |
      +-----------------------------> sorties/candidats.csv
      +-----------------------------> sorties/criteres.csv
      +-----------------------------> sorties/syntheses.md
      +-----------------------------> graphiques du notebook
```

Le notebook `analyse_cv.ipynb` est le point d'entrée. Les traitements importants
sont placés dans trois modules afin de séparer les responsabilités et de pouvoir
les tester indépendamment :

| Fichier | Responsabilité |
|---|---|
| `src/pipeline.py` | Lecture des PDF, appels à Ollama, cache et provenance |
| `src/donnees.py` | Schéma commun, validation, normalisation et relecture |
| `src/evaluation.py` | Barème déterministe, total et synthèses |
| `prompt.md` | Instructions d'extraction envoyées au modèle |
| `grille-notation-cv.md` | Règles fonctionnelles du barème |
| `tests/test_projet.py` | Tests unitaires et test du lot complet |

## 4. Déroulement complet du traitement

### Étape 1 — Lecture des PDF

La fonction `extrait_pdf(pdf, dossier_texte)` utilise `pypdf` pour lire toutes
les pages du fichier. Elle assemble leur couche texte et l'enregistre dans
`datas_extract/`.

Elle retourne notamment :

```python
{
    "pdf": chemin_pdf,
    "texte": texte_extrait,
    "txt": chemin_du_txt,
    "pdf_sha256": empreinte_du_pdf,
    "texte_sha256": empreinte_du_texte,
}
```

Une page sans texte arrête le traitement. Le programme évite ainsi de transformer
un PDF scanné non reconnu en faux CV vide. Dans ce cas, un OCR séparé est
nécessaire.

### Étape 2 — Construction du prompt

`lit_prompt()` lit `prompt.md`, puis `message_cv()` construit une consigne pour
une seule rubrique. Le modèle reçoit :

- le texte du CV ;
- le nom de la rubrique demandée ;
- les règles spécifiques à cette rubrique ;
- la forme JSON exacte attendue.

Le modèle ne reçoit ni le barème, ni les notes de référence. Cette séparation
évite de lui faire adapter l'extraction au résultat attendu.

### Étape 3 — Structuration par Ollama

`structure_cv()` traite séparément les six rubriques suivantes :

```python
formation
competences
langues
experiences
engagements
international
```

Il y a donc au maximum six appels principaux par CV, plutôt qu'une grande
réponse unique. Cette stratégie :

- réduit la taille et la complexité de chaque réponse ;
- permet d'utiliser un schéma différent pour chaque rubrique ;
- facilite la reprise après une interruption ;
- localise plus précisément les erreurs.

Chaque réponse doit être un objet JSON contenant uniquement la rubrique demandée.
Le format est vérifié avec le schéma défini dans `src/donnees.py`. Une réponse
incorrecte est refusée et peut déclencher une seconde tentative accompagnée du
message d'erreur.

Pour `experiences`, `engagements` et `international`, le prompt rappelle au modèle
de renvoyer une liste vide lorsqu'aucun fait n'est présent. Cela limite la création
d'éléments fictifs uniquement destinés à remplir le tableau.

### Étape 4 — Cache et reprise

Avant d'appeler Ollama, `structure_cv()` cherche un résultat existant. Le cache
n'est accepté que si tous les éléments suivants correspondent :

- empreinte du PDF ;
- empreinte du texte extrait ;
- empreinte du prompt ;
- empreinte du schéma ;
- nom du modèle ;
- stratégie d'extraction ;
- empreinte du JSON final ;
- identité attendue du candidat.

Des résultats intermédiaires sont également conservés dans `sorties/.travail/`.
Si quatre rubriques ont déjà été produites avant une interruption, le traitement
peut reprendre sans les recalculer.

Dans le notebook, `AUTORISER_GENERATION = False` impose actuellement le mode
cache. Aucun appel involontaire à Ollama n'est alors possible. Pour traiter un
nouveau CV, il faut démarrer Ollama et passer explicitement ce réglage à `True`.

### Étape 5 — Validation du JSON

Le dictionnaire `SCHEMA` décrit tous les champs autorisés et leurs types. Par
exemple, une expérience contient un type, un poste, une organisation, une durée
et des missions.

`schema_json()` convertit ce schéma Python en JSON Schema pour Ollama.
`valide_cv()` réalise ensuite un contrôle côté Python :

- présence de tous les champs ;
- absence de champs inattendus ;
- types corrects ;
- chaînes non vides ;
- notes comprises entre 0 et 20 ;
- types d'expériences autorisés ;
- cohérence du nom du PDF.

Cette validation garantit la forme des données, mais pas leur fidélité au CV.
Un JSON parfaitement valide peut encore contenir une information inventée ou
mal classée. C'est la raison de l'étape suivante.

### Étape 6 — Relecture traçable

`applique_relecture()` charge les corrections de `sorties/relectures.json`.
Chaque correction indique :

```json
{
  "chemin": ["formation", "mention_bac"],
  "avant": "Très Bien",
  "apres": "Bien",
  "raison": "Copie de la mention",
  "extraits_source": ["Mention Bien"]
}
```

Avant l'application, la fonction vérifie :

- que les empreintes du texte et du JSON sont toujours les mêmes ;
- qu'une justification est fournie ;
- que les citations existent réellement dans le texte extrait ;
- que la valeur `avant` correspond encore au JSON courant.

Le CV est copié avec `deepcopy`, donc le JSON original du modèle reste intact.
Une nouvelle génération rend automatiquement l'ancienne relecture périmée.

Les trois statuts possibles sont :

- `non relu` ;
- `relu sans correction` ;
- `relu avec corrections`.

### Étape 7 — Calcul déterministe de la note

`evalue_cv()` applique huit critères dont les poids totalisent 20 :

| Critère | Poids maximal |
|---|---:|
| Excellence académique | 6 |
| Aptitude quantitative | 4 |
| Compétences data / tech | 2 |
| Anglais et langues | 2 |
| Expérience professionnelle | 3 |
| Engagement et responsabilités | 2 |
| Ouverture internationale | 0,5 |
| Liens factuels avec Business & Data | 0,5 |

Pour chaque critère, la fonction produit :

- les points attribués ;
- le maximum du critère ;
- les faits utilisés ;
- la règle appliquée ;
- les éventuels points restant à vérifier ;
- le chemin du texte source.

Les calculs reposent sur des règles Python explicites et non sur une appréciation
du modèle. Quelques exemples :

- mention très bien : 6 points académiques ;
- spécialité mathématiques : 1,5 point quantitatif ;
- présence d'un langage reconnu : bonus technique ;
- niveau d'anglais B2 : 1 point sur la partie anglais ;
- missions professionnelles décrites : bonus d'expérience.

`note_maths()` évite de choisir automatiquement la meilleure note. S'il existe
plusieurs trimestres clairement identifiés, le dernier est retenu, même si sa
note est plus basse. Si l'ordre est ambigu, la fonction réserve les points pour
une vérification.

`points_anglais()` accepte un niveau CECRL explicite ou certains scores accompagnés
de leur échelle. Un nombre seul n'est pas interprété.

Enfin, `totalise()` additionne les points sans renormaliser artificiellement le
résultat sur 20.

### Étape 8 — Gestion de l'incertitude

Le projet distingue deux valeurs :

- `note_sur20` : points réellement attribués par les règles ;
- `points_a_verifier` : points éventuellement accessibles après vérification.

Par exemple :

```text
Note : 11,75/20
Points à vérifier : 1,5
Plafond après vérification : 13,25/20
```

Les 1,5 points ne sont pas ajoutés à la note. Ils rendent visible une information
manquante ou ambiguë. Une liste vide signifie « aucun élément mentionné dans le
CV », pas « le candidat n'a jamais réalisé cet élément ».

### Étape 9 — Analyse et export

Le notebook utilise `pandas` pour produire une ligne par candidat et une ligne
par sous-note. Il calcule également des statistiques descriptives : langages
mentionnés, mentions au bac, stages et distribution des notes.

Les principaux résultats sont :

| Sortie | Contenu |
|---|---|
| `sorties/candidats.csv` | Résumé et total de chaque candidat |
| `sorties/criteres.csv` | Détail des huit critères par candidat |
| `sorties/syntheses.md` | Synthèses lisibles avec règles et faits |
| `sorties/comparaison.csv` | Comparaison descriptive aux références |
| `sorties/provenance.json` | Empreintes, modèle, options et journal des appels |
| `sorties/validation.md` | Contrôles effectués, résultats et limites |

Les notes de référence sont chargées seulement à la fin. Elles servent à une
comparaison descriptive et ne participent ni à l'extraction ni au calcul.

## 5. Fonctions importantes à connaître à l'oral

### `src/pipeline.py`

| Fonction | Rôle |
|---|---|
| `empreinte` | Calcule une empreinte SHA-256 |
| `ecrit_json` | Écrit un JSON de façon atomique via un fichier temporaire |
| `extrait_pdf` | Lit le PDF et conserve son texte |
| `lit_prompt` | Charge et vérifie le fichier de prompt |
| `gabarit` | Construit une structure vide conforme au schéma |
| `message_cv` | Prépare le message d'une rubrique |
| `appelle_ollama` | Appelle l'API locale et lit sa réponse en flux |
| `normalise_types` | Harmonise certains libellés sans inventer de fait |
| `structure_cv` | Orchestre le cache, les six appels, la validation et la provenance |

`appelle_ollama()` utilise une température de 0 et une graine fixe pour limiter
la variabilité. Il arrête la lecture du flux dès qu'un objet JSON complet est
disponible. Cela évite d'attendre des espaces ou du texte supplémentaire.

### `src/donnees.py`

| Fonction | Rôle |
|---|---|
| `normalise_texte` | Uniformise casse, accents et espaces pour les comparaisons |
| `valeurs_uniques` | Supprime les doublons normalisés |
| `mention_standard` | Harmonise les écritures des mentions du bac |
| `nom_competence` | Isole le nom d'une compétence de son niveau |
| `schema_json` | Produit le JSON Schema envoyé à Ollama |
| `valide_cv` | Contrôle la structure complète d'un CV |
| `charge_dossier` | Charge un lot JSON et refuse doublons ou erreurs |
| `applique_relecture` | Applique les corrections justifiées et compatibles |

### `src/evaluation.py`

| Fonction | Rôle |
|---|---|
| `contient` | Recherche un motif dans un texte normalisé |
| `decrit` | Construit une description courte des faits |
| `note_maths` | Sélectionne une note de mathématiques sans choisir la meilleure |
| `points_anglais` | Applique les règles de niveau ou de score d'anglais |
| `evalue_cv` | Calcule et explique les huit sous-notes |
| `totalise` | Additionne points acquis et points à vérifier |
| `synthese_markdown` | Produit une fiche lisible par candidat |

## 6. Zoom sur `structure_cv()`

### Signature et responsabilité

```python
def structure_cv(entree, dossier_sorties, prompt,
                 modele="llama3.2:3b",
                 autoriser_generation=True,
                 adresse="http://127.0.0.1:11434",
                 appel=appelle_ollama):
```

Cette fonction est l'orchestrateur de l'extraction structurée. Elle ne lit pas
directement le PDF : elle reçoit la sortie de `extrait_pdf()`, décide si un JSON
existant est réutilisable et, si nécessaire, interroge Ollama pour construire le
CV rubrique par rubrique.

Ses paramètres sont :

- `entree` : dictionnaire contenant le PDF, son texte et leurs empreintes ;
- `dossier_sorties` : emplacement du JSON, de la provenance et des sauvegardes ;
- `prompt` : contenu de `prompt.md` ;
- `modele` : modèle Ollama demandé ;
- `autoriser_generation` : autorisation explicite de produire une nouvelle réponse ;
- `adresse` : adresse de l'API locale Ollama ;
- `appel` : fonction d'appel au modèle, injectable pour faciliter les tests.

Elle renvoie un tuple :

```python
(cv, statut)
```

Le statut vaut soit `cache modele verifie`, soit
`genere par Ollama (6 rubriques)`.

### Déroulement ligne par ligne

1. Elle déduit l'identifiant à partir du nom du PDF :

   ```python
   identifiant = entree["pdf"].stem
   ```

2. Elle détermine le chemin du JSON final et charge `provenance.json`.

3. Elle construit `attendu`, la signature complète de la génération : empreintes
   du PDF, du texte, du prompt et du schéma, modèle, moteur et stratégie.

4. Elle recherche un cache. Le JSON n'est renvoyé que si toutes les signatures
   correspondent, si `valide_cv()` ne trouve aucune erreur, si son empreinte est
   intacte et si ses métadonnées correspondent au fichier courant.

5. Sans cache valide, elle contrôle `autoriser_generation`. Si la valeur est
   `False`, elle s'arrête au lieu de contacter implicitement Ollama.

6. Elle refuse un texte signalé comme illisible ou OCR avant de construire un
   candidat artificiellement vide.

7. Elle initialise un CV complet mais vide avec `gabarit(SCHEMA)`, puis remplit
   elle-même `meta`. Le modèle ne choisit donc ni l'identifiant ni le fichier source.

8. Elle parcourt `GROUPES`. Pour chaque rubrique, elle cherche d'abord une
   sauvegarde intermédiaire compatible dans `sorties/.travail/`.

9. Si aucune sauvegarde n'est réutilisable, `message_cv()` construit le prompt et
   `appel()` interroge Ollama avec le sous-schéma de la rubrique.

10. Elle décode la réponse avec `json.loads()`, impose une seule clé, normalise
    quelques libellés d'expérience, assemble la rubrique et valide le CV obtenu.

11. En cas de problème de format, elle conserve la réponse brute, ajoute l'erreur
    aux consignes et effectue une seconde tentative. Une réponse en flux incomplète
    reçoit également une nouvelle consigne de brièveté.

12. Après une rubrique valide, elle journalise l'empreinte de la réponse, le
    nombre de tentatives, les normalisations, les compteurs de jetons lorsqu'ils
    sont disponibles, la durée et la cause d'arrêt.

13. Une fois les six rubriques terminées, elle écrit le JSON final, met à jour
    `provenance.json` et renvoie le CV.

### Pseudo-code simplifié

```text
calculer la signature attendue
si le cache complet est valide :
    renvoyer le cache
si la génération est interdite :
    lever une erreur

initialiser un CV vide
pour chaque rubrique :
    si une sauvegarde compatible existe :
        la réutiliser
    sinon :
        construire le message
        appeler Ollama, au maximum deux tentatives
        décoder et valider la rubrique
        sauvegarder le résultat intermédiaire

écrire le JSON et la provenance
renvoyer le CV assemblé
```

### Pourquoi le paramètre `appel` est utile

La valeur par défaut est `appelle_ollama`, mais les tests peuvent fournir une
fonction simulée. Ils vérifient ainsi le comportement de l'orchestrateur sans
dépendre d'un serveur, d'un modèle installé ou d'une réponse aléatoire. C'est un
exemple d'injection de dépendance.

### Formulation simple pour l'oral

> « `structure_cv` pilote toute la phase IA. Elle commence par vérifier si un
> résultat existant est encore valable. Sinon, et seulement si on l'autorise,
> elle demande séparément six rubriques à Ollama, valide chaque réponse, permet
> une reprise et enregistre toute la provenance. »

## 7. Zoom sur `applique_relecture()`

### Signature et responsabilité

```python
def applique_relecture(cv, texte, dossier_sorties):
```

Cette fonction applique les corrections explicites enregistrées après la
comparaison du JSON au texte source. Elle protège le résultat brut du modèle et
empêche de réutiliser une correction sur une nouvelle version du document.

Ses paramètres sont :

- `cv` : dictionnaire brut produit ou chargé par `structure_cv()` ;
- `texte` : texte extrait du PDF ;
- `dossier_sorties` : dossier contenant `relectures.json` et le JSON brut.

Elle renvoie :

```python
(resultat, statut_relecture, corrections)
```

### Déroulement détaillé

1. Elle charge `relectures.json`, ou utilise un dictionnaire vide s'il n'existe pas.

2. Elle récupère l'identifiant dans `cv["meta"]["id_candidat"]` et cherche la
   relecture correspondante.

3. Si aucune relecture n'existe, elle renvoie immédiatement le CV avec le statut
   `non relu` et une liste de corrections vide.

4. Si une relecture existe, elle recalcule les empreintes du JSON brut et du texte.
   Une différence signifie que la correction a été écrite pour une autre version :
   la fonction lève alors une erreur de relecture périmée.

5. Elle crée `resultat = copy.deepcopy(cv)`. Les modifications portent donc sur
   une copie indépendante ; le dictionnaire reçu et le fichier brut restent intacts.

6. Pour chaque correction, elle exige une raison non vide et au moins une citation.
   Chaque extrait est normalisé puis recherché dans le texte source. Une citation
   inventée ou absente provoque une erreur.

7. Le tableau `chemin` permet de naviguer jusqu'au champ visé. Ainsi :

   ```python
   ["formation", "mention_bac"]
   ```

   désigne `resultat["formation"]["mention_bac"]`.

8. Avant d'écrire `apres`, la fonction vérifie que la valeur courante correspond
   exactement à `avant`. Cela empêche une correction de s'appliquer au mauvais état.

9. Une fois toutes les corrections jouées, `valide_cv(resultat)` vérifie que le
   document final respecte toujours le schéma.

10. Le statut final distingue une relecture sans modification d'une relecture
    ayant réellement corrigé des champs.

### Exemple concret

```json
{
  "chemin": ["formation", "options"],
  "avant": [],
  "apres": ["Maths Expertes"],
  "raison": "Option explicitement citée.",
  "extraits_source": ["NSI (+ Maths Expertes)"]
}
```

La correction n'est appliquée que si la liste `options` est encore vide, si
l'extrait existe dans le texte et si les empreintes sont celles des sources
relues. Elle ne repose donc pas uniquement sur une modification libre du JSON.

### Différence entre validation et relecture

`valide_cv()` répond à la question « la donnée a-t-elle la bonne forme ? ».
`applique_relecture()` aide à répondre à la question « la donnée correspond-elle
encore à une correction justifiée par cette version du texte ? ».

Par exemple, la valeur `"B1"` placée dans la mauvaise langue peut respecter le
schéma JSON tout en étant factuellement incorrecte. La validation seule ne peut
pas détecter cette erreur.

### Formulation simple pour l'oral

> « `applique_relecture` rejoue des corrections documentées sans écraser la
> réponse du modèle. Les empreintes relient chaque correction à une version
> précise du texte et du JSON, tandis que les citations et la valeur `avant`
> empêchent une application aveugle. »

## 8. Fiabilité et résultats observés

La suite actuelle contient 21 tests automatisés. Elle vérifie notamment :

- les bornes et l'explication des notes ;
- l'invalidation du cache après une modification ;
- le refus des JSON invalides ;
- la reprise après une réponse incomplète ;
- le traitement des notes de maths ambiguës ;
- le refus d'un PDF sans texte ;
- la relecture traçable et son invalidation ;
- l'absence d'effet du nom ou du lycée sur la note ;
- le traitement complet des 11 CV.

Commande de vérification :

```bash
python3 -m unittest discover -s tests -v
```

Sur les quatre faits ciblés par candidat dans le rapport de validation — mention,
langages, nombre de stages et notes de mathématiques — le modèle brut obtient
31 contrôles conformes sur 44. Après la relecture documentée, les 44 contrôles
sont conformes.

Ce résultat ne prouve pas que tous les champs sont parfaits. Il montre surtout
pourquoi la relecture est nécessaire avec le petit modèle local utilisé.

## 9. Choix techniques à défendre

### Pourquoi un modèle local ?

- pas de clé API ni d'abonnement ;
- les CV ne sont pas envoyés à un service distant par le code ;
- environnement maîtrisé pour la démonstration.

La contrepartie est une qualité d'extraction limitée avec `llama3.2:3b`, ce qui
explique les contrôles stricts et la relecture.

### Pourquoi du JSON structuré ?

Le JSON donne une interface stable entre l'extraction par IA et le calcul Python.
Le modèle gère le langage naturel ; le reste du programme travaille sur des
champs connus et vérifiables.

### Pourquoi calculer la note en Python ?

Une règle Python est déterministe, testable et explicable. Demander directement
une note au modèle rendrait le résultat moins reproductible et plus difficile à
auditer.

### Pourquoi des empreintes SHA-256 ?

Elles permettent de détecter toute modification d'une source, d'un prompt, d'un
schéma ou d'un résultat. Le programme évite ainsi de réutiliser silencieusement
un cache ou une correction devenu obsolète.

### Pourquoi conserver le brut et les corrections séparément ?

Cette séparation permet de distinguer ce qu'a produit le modèle de ce qui a été
corrigé ensuite. Elle améliore la traçabilité et permet d'analyser les erreurs du
modèle.

## 10. Limites et améliorations possibles

Les principales limites sont :

- seulement 11 CV fictifs, donc pas de preuve de généralisation ;
- modèle local de petite taille sujet aux omissions et hallucinations ;
- absence d'OCR intégré pour les PDF scannés ;
- relecture réalisée à partir du texte extrait, encore à valider humainement ;
- barème pédagogique proposé, non officiel ;
- règles par mots-clés parfois limitées par les formulations possibles ;
- scores linguistiques et niveaux déclarés non authentifiés ;
- une mise en page PDF complexe peut dégrader l'ordre du texte extrait.

Améliorations envisageables :

1. intégrer un OCR avec mesure de confiance ;
2. construire un jeu de validation plus large et relu indépendamment ;
3. proposer une interface de relecture champ par champ ;
4. comparer plusieurs modèles locaux ;
5. ajouter des tests sur davantage de mises en page et de formulations ;
6. versionner formellement le barème et le schéma ;
7. mesurer séparément précision, rappel et taux d'hallucination par rubrique ;
8. protéger davantage les données si le projet utilise un jour de vrais CV.

## 11. Proposition de présentation en 8 à 10 minutes

### 1. Introduction — 45 secondes

> « Notre projet automatise l'analyse factuelle de CV. Il transforme les PDF en
> données structurées, applique une grille explicite et produit une note expliquée.
> Notre principe principal est de ne jamais demander au modèle de décider de la
> note : Ollama extrait les faits, Python les contrôle et calcule le résultat. »

### 2. Architecture — 1 minute

Montrer le schéma du PDF vers les sorties. Présenter les trois modules : pipeline,
données et évaluation.

### 3. Extraction — 2 minutes

Présenter `extrait_pdf()`, puis `structure_cv()`. Insister sur les six appels par
rubrique, le JSON Schema, les deux tentatives et la reprise intermédiaire.

### 4. Contrôles et traçabilité — 1 minute 30

Présenter `valide_cv()`, les empreintes, `provenance.json` et
`applique_relecture()`. Montrer une correction avec `avant`, `apres`, `raison`
et `extraits_source`.

### 5. Notation — 2 minutes

Montrer les huit critères et un exemple de calcul. Expliquer la différence entre
`note_sur20` et `points_a_verifier`.

### 6. Résultats — 1 minute

Montrer un graphique et une synthèse. Indiquer que 21 tests passent et que les
contrôles ciblés passent de 31/44 avant relecture à 44/44 après relecture.

### 7. Limites et conclusion — 1 minute

> « Le projet démontre une chaîne complète, reproductible et explicable, mais pas
> une admission automatique. Le petit modèle nécessite une relecture, le barème
> doit être validé et les 11 CV ne suffisent pas pour conclure à une généralisation. »

## 12. Démonstration conseillée

Une démonstration courte est plus sûre qu'une régénération Ollama en direct :

1. laisser `AUTORISER_GENERATION = False` ;
2. exécuter le notebook avec les caches vérifiés ;
3. montrer le tableau de relecture ;
4. afficher une synthèse individuelle ;
5. montrer le graphique des notes et des points à vérifier ;
6. ouvrir un JSON brut puis la correction correspondante ;
7. terminer par `sorties/validation.md` et les tests.

Éviter de dépendre d'une génération en direct : elle peut être longue et rendre
la présentation moins prévisible. Le cache vérifié démontre déjà la
reproductibilité et l'intégrité des résultats.

## 13. Questions probables du jury

### « Pourquoi ne pas demander directement la note à l'IA ? »

Parce qu'une note générée serait moins stable et moins explicable. Ici, le modèle
se limite à l'extraction ; le calcul est écrit en Python, contrôlable et testable.

### « Comment savez-vous que le modèle n'invente pas ? »

Le schéma et le prompt réduisent le risque, mais ne l'éliminent pas. C'est pourquoi
les textes sources sont conservés, les corrections contiennent des citations et
les résultats livrés ont été relus. Le rapport montre d'ailleurs des erreurs
réelles du modèle brut.

### « À quoi sert le cache ? »

Il évite de refaire des appels coûteux et permet une démonstration sans Ollama.
Les empreintes garantissent qu'il n'est réutilisé que si toutes les sources et
la configuration correspondent.

### « Quelle différence entre validation et relecture ? »

La validation contrôle la structure et les types. La relecture contrôle la
fidélité des faits par rapport au texte. Un JSON peut être valide tout en étant
factuellement faux.

### « Pourquoi existe-t-il des points à vérifier ? »

Ils empêchent de confondre une information absente avec un résultat nul certain.
Ils indiquent l'incertitude sans offrir automatiquement les points.

### « Les résultats sont-ils équitables ? »

Les règles excluent notamment le nom, l'âge, le genre, la nationalité, l'adresse
et la réputation supposée du lycée. Cependant, un barème peut toujours introduire
des choix discutables : il est présenté comme une proposition à valider, pas
comme une mesure objective universelle.

### « Les notes de référence ont-elles influencé le système ? »

Non. Elles sont chargées après l'extraction et après le calcul. Elles ne sont ni
dans le prompt ni dans `evaluation.py` et servent uniquement à comparer deux
méthodes.

### « Que se passe-t-il si le PDF change ? »

Son empreinte change. Le cache est invalidé et les anciennes corrections ne sont
plus applicables tant qu'une nouvelle relecture n'a pas été créée.

### « Peut-on utiliser ce projet sur de vrais candidats ? »

Pas tel quel pour décider d'une admission. Il faudrait renforcer la protection
des données, évaluer le système sur un corpus plus large, faire relire les
extractions et faire valider officiellement le barème.

## 14. Les trois messages à retenir

1. **Séparation des responsabilités :** le modèle extrait, Python évalue.
2. **Traçabilité :** sources, empreintes, provenance et corrections sont conservées.
3. **Prudence :** la note est expliquée et provisoire ; les incertitudes et les
   limites restent visibles.
