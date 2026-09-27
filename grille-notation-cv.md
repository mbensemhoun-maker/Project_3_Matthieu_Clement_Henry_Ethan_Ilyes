# Barème pédagogique des CV — Albert School

**Statut : proposition explicite à valider par l’équipe et le professeur.**
Les poids de la grille initiale sont conservés. Les règles ci-dessous remplacent
les appréciations implicites par des calculs reproductibles. Elles ne sont pas
présentées comme le barème officiel d’Albert School.

Le code de référence est `src/evaluation.py`. Les notes de `cv-test/notes-reference.csv`
ne servent jamais à choisir les points : elles sont comparées après le calcul.

## Les huit critères — 20 points

| Critère | Maximum | Règles d’attribution |
|---|---:|---|
| Excellence académique | 6 | Mention explicitement écrite : très bien 6 ; bien 4,5 ; assez bien 3,5 ; sans mention 2. Une mention absente ou non reconnue laisse 6 points à vérifier. |
| Aptitude quantitative | 4 | Spécialité maths +1,5 ; au moins une spécialité NSI/physique/sciences de l’ingénieur +0,5 ; concours scientifique explicitement mentionné +0,5 ; résultat de maths jusqu’à +1,5 selon le tableau ci-dessous. |
| Compétences data / tech | 2 | Socle 0,5 ; langage technique reconnu +0,5 ; outil data ou Excel avancé +0,25 ; projet technique décrit +0,5 (+0,25 si inachevé) ; certification data obtenue +0,25. Chaque bonus est attribué au plus une fois. |
| Anglais et langues | 2 | Anglais jusqu’à 1,5 selon les niveaux/tests ci-dessous ; autre langue que français/anglais explicitement mentionnée +0,5. |
| Expérience professionnelle | 3 | Socle 0,5 ; première expérience professionnelle +0,75 ; au moins deux expériences +0,75 ; missions décrites +0,5 ; régularité ou durée explicite suffisante +0,5. |
| Engagement et responsabilités | 2 | Activité collective mentionnée +0,5 ; responsabilité explicite +0,75 ; action liée à cette responsabilité décrite +0,75. |
| Ouverture internationale | 0,5 | Socle 0,25, même sans séjour ; études, échange scolaire ou immersion linguistique explicite +0,25. Un voyage familial seul ne reçoit pas le bonus. |
| Liens factuels avec Business & Data | 0,5 | +0,25 par rubrique présentant un lien explicite, parmi formation, compétences et expériences ; plafond 0,5. Ce calcul décrit des liens, sans juger la motivation ni la personnalité. |

Aucun point n’est attribué selon le nom, l’âge, le genre, la nationalité, l’adresse,
la réputation supposée de l’établissement ou le redoublement. Ces derniers
éléments de parcours peuvent être cités factuellement dans la synthèse.

### Résultats en mathématiques

| Résultat explicite sur 20 | Bonus |
|---|---:|
| Moins de 10 | 0 |
| De 10 inclus à 12 exclu | 0,5 |
| De 12 inclus à 14 exclu | 0,75 |
| De 14 inclus à 16 exclu | 1 |
| 16 ou plus | 1,5 |

Une unique note de maths peut être utilisée. Pour plusieurs trimestres clairement
identifiés, le dernier est retenu, même si sa note baisse. Plusieurs résultats
sans ordre clair demandent une vérification ; aucun n’est choisi parce qu’il est
le meilleur. Une moyenne générale ne remplace jamais une note de mathématiques.
Une note absente laisse 1,5 point à vérifier.

### Anglais

Niveau explicitement annoncé : C1/C2 = 1,5 ; B2 = 1 ; B1 = 0,75 ; A1/A2,
« scolaire », « notions » ou « débutant » = 0,5. Un niveau auto-évalué reste
signalé comme déclaratif. La présence d’un nom de certificat ne prouve pas son authenticité.

En l’absence de niveau CECRL explicite, un score avec son échelle peut être utilisé :

| Test et échelle | 1,5 point | 1 point | 0,75 point | 0,5 point |
|---|---:|---:|---:|---:|
| TOEFL /120 | ≥100 | ≥80 | ≥60 | en dessous |
| TOEIC /990 | ≥900 | ≥750 | ≥550 | en dessous |
| IELTS /9 | ≥7 | ≥6 | ≥5 | en dessous |

Ce sont des **seuils du projet**, pas des équivalences officielles entre tests
et niveaux. Une échelle inconnue, un niveau ambigu ou l’absence d’anglais
laissent jusqu’à 1,5 point à vérifier.

### Précisions sur les bonus

- Langages reconnus : Python, SQL, R, JavaScript, Java, C, C++, HTML, CSS,
  TypeScript, MATLAB, Julia. HTML/CSS sont inclus comme technologies web.
- Outils reconnus : Power BI, Tableau, pandas, NumPy, matplotlib, Excel accompagné
  d’une mention explicite de niveau avancé, TCD ou recherchev. Les libellés
  techniques non reconnus restent visibles et demandent une revue.
- Le bonus projet concerne une réalisation technique décrite ; « non finalisé »,
  « non achevé », « en cours », « commencé » ou « pas de mise en ligne » limitent le bonus.
- Une certification explicitement en cours ne reçoit pas le bonus obtenu.
- Expériences : stages, alternances, jobs étudiants, emplois. Le bénévolat
  associatif relève de l’engagement. Une simple « observation » sans autres
  missions ne reçoit pas le bonus des tâches décrites.
- Régularité/durée : au moins quatre semaines explicitement chiffrées, un mois,
  deux étés/deux années, ou une récurrence explicite (par semaine, week-end,
  samedis/dimanches, régulier). Les périodes calendaires ne sont pas converties
  automatiquement en durées. Un type inconnu réserve les points encore possibles ;
  une durée manquante peut réserver le bonus de durée.
- Responsabilités : président/vice-président, trésorier, capitaine, fondateur,
  secrétaire, responsable ou coordinateur. Les actions décrites doivent être
  associées à ce rôle (organisation, gestion, animation, budget, équipe, etc.).
- Liens Business & Data : formation avec maths/NSI/SES/gestion/finance/informatique ;
  compétences techniques identifiées ; ou missions data, comptables, commerciales,
  de vente, de gestion ou auprès de clients. Ces règles par mots-clés ont des limites.

## Informations manquantes et note provisoire

Une liste vide signifie « aucun élément mentionné », jamais « le candidat n’en a
jamais fait ». Les socles des critères tech, expérience et international permettent
un point de départ explicite pour les candidats sans ces expériences.

Une rubrique illisible rend tous ses points à vérifier. Une information nécessaire
absente ou ambiguë peut réserver une partie des points. Le notebook affiche :

- **note_sur20** : somme des points attribués par les règles ;
- **points_a_verifier** : maximum supplémentaire dépendant des informations manquantes ;
- **plafond_apres_verification** : somme des deux, sans dépasser 20.

Les points à vérifier ne sont pas accordés. Aucune renormalisation n’est faite.
Ce maximum ne couvre pas les erreurs d’extraction : un fait mal transcrit peut
modifier aussi les points déjà attribués. Toutes les notes sont des propositions
pédagogiques à relire avec les sources ; aucun seuil automatique d’admission n’est appliqué.
