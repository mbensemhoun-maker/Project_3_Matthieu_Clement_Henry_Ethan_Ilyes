# Réponses JSON du modèle

Un JSON court par CV : `<id_candidat>.json`, produit par
`extraction/pipeline.py` avec le [prompt](../prompt.md).
Les faits ne sont pas doublés et le modèle ne renvoie aucun compteur.

Les textes d'entrée sont dans `datas_extract/`. Une clé `OPENAI_API_KEY` est
nécessaire pour appeler le modèle. Aucun JSON réel n'est inclus pour le moment.
Les trois exemples manuels se trouvent séparément dans `analyse/exemples/`.

`meta.id_candidat` et `meta.fichier_source` sont renseignés par le pipeline.
Le second conserve le nom du PDF, utilisé pour joindre les notes de référence.

Ouvrir `analyse_cv.ipynb` pour l'analyse ou lancer :

```bash
python3 analyse/controle_coherence.py sorties/
python3 analyse/agrege.py sorties/
python3 analyse/stats.py
```

Les anciennes réponses avec `donnees_normalisees` doivent être régénérées
avec `--force`. Une réponse non conforme est enregistrée en `.brut.txt`,
ignorée par l'analyse et par Git, pour permettre son diagnostic.
