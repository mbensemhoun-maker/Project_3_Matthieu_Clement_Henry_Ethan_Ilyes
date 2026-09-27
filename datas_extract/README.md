# Texte extrait des CV

Un fichier `.txt` UTF-8 par PDF, avec le même nom sans extension.
Ce dossier contient les 11 CV fictifs de test avant leur mise en JSON.

```bash
python3 extraction/extrait_texte.py
```

Les fichiers existants sont conservés ; `--force` les régénère. Les PDF
scannés sans couche texte demandent un OCR séparé. Vérifier l'ordre des
colonnes et les éventuelles omissions avant d'envoyer un texte au modèle.

Le pipeline fournit au prompt le contenu dans `{donnees_extraites}`, le nom
sans extension dans `{id_candidat}` et le nom du PDF dans `{fichier_source}`.
Les éventuels signalements d'illisibilité doivent accompagner le texte.

```bash
python3 extraction/pipeline.py --texte-seul  # vérification gratuite
python3 extraction/pipeline.py --limite 2    # appels au modèle, clé API requise
```

Le pipeline lit uniquement les `.txt`, pas ce README ni les notes de référence.
Le résultat est enregistré dans `sorties/`, puis analysé dans
`analyse_cv.ipynb`. Le notebook calcule lui-même tous les indicateurs.
