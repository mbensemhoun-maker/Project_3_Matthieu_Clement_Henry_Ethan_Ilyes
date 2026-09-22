# Grille de notation des CV — Albert School x Mines Paris PSL

## Contexte

Cette grille sert à évaluer les CV de candidats souhaitant rejoindre le programme
Business & Data porté par Albert School en partenariat avec les Mines Paris PSL.
Chaque CV est noté sur **20 points**, répartis sur 8 critères pondérés.

## Barème

| # | Critère | Poids | Ce qu'on cherche dans le CV |
|---|---|---|---|
| 1 | **Excellence académique** | 5 pts | Mention au bac, filière (générale/techno), établissement, classe prépa ou équivalent, moyenne/rang si mentionné, redoublement éventuel |
| 2 | **Aptitude quantitative** | 3 pts | Spécialités scientifiques (maths, NSI, physique), résultats en maths, concours scientifiques (olympiades, etc.) |
| 3 | **Compétences data/tech** | 3 pts | Langages (Python, SQL, R…), outils (Excel avancé, Power BI, Tableau), projets data/ML mentionnés, certifications (Coursera, DataCamp) |
| 4 | **Anglais et langues** | 2 pts | Score certifié (TOEFL/TOEIC/IELTS/Cambridge), séjours linguistiques, autres langues |
| 5 | **Expérience professionnelle** | 3 pts | Stages, jobs étudiants, alternances — pertinence, durée, niveau de responsabilité |
| 6 | **Engagement associatif / leadership** | 2 pts | Bureau d'association, junior entreprise, entrepreneuriat, responsabilités prises |
| 7 | **Ouverture internationale** | 1 pt | Séjour d'études à l'étranger, échange scolaire, double nationalité/mobilité |
| 8 | **Cohérence du parcours** | 1 pt | Fil conducteur visible entre formation, expériences et choix de candidature |
| | **Total** | **20 pts** | |

## Notes de méthode

- Les critères 1, 2, 4 sont majoritairement **factuels** (mentions, scores,
  spécialités) : extractibles par OCR + règles/regex.
- Les critères 3, 5, 6, 8 nécessitent une **évaluation qualitative** du contenu
  (pertinence, niveau de responsabilité, cohérence) : jugement par un LLM
  plutôt qu'un simple pattern matching.
- Le critère 8 (cohérence du parcours) est le plus subjectif de la grille —
  à surveiller particulièrement lors des tests de fiabilité du système.
