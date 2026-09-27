# Vérification du rendu — 11 CV fictifs

Vérification du 2026-09-27 (UTC).

## Ce qui a été exécuté

- Lecture des **11 PDF** et conservation des **11 textes** dans `datas_extract/`.
- Structuration réelle avec **Ollama llama3.2:3b installé sur l’ordinateur**, rubrique par rubrique.
- Conservation des **11 JSON originaux assemblés**, des empreintes et du journal des appels dans `provenance.json`.
- Relecture des textes par l’assistant et corrections documentées dans `relectures.json`.
- Exécution complète des **9 cellules Python** du notebook sur les 11 dossiers, en mode cache vérifié sans nouvel appel.
- Réussite de la suite `python3 -m unittest discover -s tests -v` : contrôles des scores, données manquantes, PDF sans texte, réponses tronquées, normalisation, caches, corrections et 11 dossiers.
- Génération des tableaux, des huit sous-notes par candidat, des graphiques et des synthèses.

## Fidélité : avant et après relecture

Quatre repères sont contrôlés par CV : mention du bac, liste des langages techniques,
nombre de stages et notes de mathématiques. Le texte source a servi à établir
`tests/attendus_cv.json`. Cette référence est construite par le même assistant
que la relecture ; **ce n’est pas une évaluation indépendante**.

Résultat brut du modèle : **31/44 contrôles ciblés conformes**.
Après relecture : **44/44**. Ces comptes ne mesurent pas toutes les omissions
ni toutes les erreurs de reformulation. **102 champs** ont été modifiés
lors de la relecture, y compris les normalisations de présentation.

| Candidat | Brut du modèle | Après relecture | Champs modifiés | Note /20 | Points à vérifier |
|---|---:|---:|---:|---:|---:|
| 01_lea_vasseur | 4/4 | 4/4 | 13 | 18.5 | 0 |
| 02_nathan_girard | 4/4 | 4/4 | 9 | 19 | 0 |
| 03_camille_roussel | 3/4 | 4/4 | 12 | 17 | 0 |
| 04_hugo_lefebvre | 3/4 | 4/4 | 10 | 11.75 | 1.5 |
| 05_ines_benali | 2/4 | 4/4 | 9 | 11.5 | 1.5 |
| 06_theo_barbier | 2/4 | 4/4 | 10 | 9.75 | 0 |
| 07_manon_petit | 3/4 | 4/4 | 9 | 10.5 | 0 |
| 08_adam_fontaine | 3/4 | 4/4 | 6 | 11.75 | 0 |
| 09_sarah_da_silva | 3/4 | 4/4 | 7 | 9.25 | 1.5 |
| 10_kevin_dubreuil | 2/4 | 4/4 | 9 | 4 | 1.5 |
| 11_chloe_renard | 2/4 | 4/4 | 8 | 4.5 | 1.5 |

## Erreurs réellement observées

Le modèle a notamment inventé des stages ou des séjours, confondu langues et
langages informatiques, dupliqué des expériences, omis des notes et perdu le
contexte de certains trimestres. Par exemple, « StatsLigue2 » était absent du CV
de Léa ; le niveau B1 concernait l’espagnol, pas l’anglais.

Les réponses originales restent consultables. Les corrections indiquent le chemin
du champ, son ancienne et sa nouvelle valeur, une justification et des extraits
du texte source. Les empreintes empêchent d’appliquer une ancienne relecture à
une réponse régénérée. Les libellés équivalents de types d’expérience peuvent être
normalisés en Python ; ces transformations sont consignées dans le journal.

Certaines générations ont demandé une reprise après erreur de format ou réponse
incomplète. Les résultats intermédiaires évitent de refaire les rubriques déjà obtenues.
Les trois exemples historiques saisis à la main sont réservés aux tests et ne
remplacent jamais les réponses du modèle dans le notebook.

## Limites à présenter

- Le petit modèle installé **n’est pas suffisamment fiable pour noter de nouveaux
  dossiers sans relecture**. Les résultats livrés utilisent les corrections
  documentées ; un nouveau dossier ne bénéficie pas automatiquement de cette revue.
- La relecture a été réalisée par l’assistant à partir des textes extraits, pas
  par un jury. La validation humaine de l’équipe reste à faire.
- Le barème détaillé est une proposition pédagogique explicite, pas le barème
  officiel d’Albert School. Il favorise certains faits documentés selon les règles
  choisies ; les écarts aux notes de référence sont descriptifs.
- Les points à vérifier ne sont pas ajoutés à la note et ne couvrent pas toutes
  les erreurs possibles d’extraction. Aucune décision d’admission n’est automatisée.
- Les PDF scannés nécessitent un OCR séparé. Onze CV fictifs ne suffisent pas à
  démontrer une généralisation à toutes les mises en page ou à tous les parcours.
