# sorties/

Un JSON par CV, produit par [prompt.md](../prompt.md).

Le dossier est vide : le pipeline OCR + appel LLM qui lit `cv-test/*.pdf` et
écrit ici reste à brancher. En attendant, les scripts d'analyse tournent sur
`analyse/fixtures/`.

Attendu pour chaque fichier :

- un JSON valide, sans texte autour (le mode d'échec le plus courant est un
  modèle qui encadre sa réponse de ``` ou d'une phrase d'introduction) ;
- `meta.id_candidat` renseigné, sinon le nom du fichier sert d'identifiant ;
- `meta.fichier_source` avec le nom du PDF d'origine (`01_lea_vasseur.pdf`),
  qui sert de clé de jointure avec `cv-test/notes-reference.csv`.

Une fois les JSON en place :

```
python3 analyse/controle_coherence.py sorties/
python3 analyse/agrege.py sorties/
python3 analyse/stats.py
```
