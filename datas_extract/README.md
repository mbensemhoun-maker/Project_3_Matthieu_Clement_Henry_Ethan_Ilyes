# Données extraites des CV

Ce dossier contient le texte des PDF, **avant** leur mise en JSON par
[`prompt.md`](../prompt.md). Un fichier `.txt` UTF-8 par CV, avec le même nom
que le PDF source :

```text
cv-test/01_lea_vasseur.pdf
    -> datas_extract/01_lea_vasseur.txt
    -> sorties/01_lea_vasseur.json
```

## Extraire les PDF

Depuis la racine du projet :

```bash
python3 -m pip install -r extraction/requirements.txt
python3 extraction/extrait_texte.py
```

Le script lit la couche texte de toutes les pages. Il conserve les fichiers
`.txt` déjà présents ; `python3 extraction/extrait_texte.py --force` les régénère.
Il ne produit ni JSON normalisé ni notes.

Un PDF scanné sans couche texte demande un **OCR séparé**. Le script signale
les extractions entièrement vides et écrit un `.txt` vide pour ces CV ; le
pipeline ne les envoie pas au modèle. La présence de texte ne garantit pas que les éléments
graphiques ou les colonnes ont été correctement récupérés : vérifier
l'extraction avant de l'envoyer au modèle. Une correction du texte doit rester
fidèle au PDF.

## Fournir les données au prompt

Pour chaque `.txt`, fournir à `prompt.md` :

- `{texte_ocr}` : le contenu du fichier texte (nom historique du paramètre,
  également utilisé pour les PDF avec une couche texte native) ;
- `{id_candidat}` : le nom du fichier sans extension, par exemple `01_lea_vasseur` ;
- `{fichier_source}` : le nom du PDF d'origine, par exemple `01_lea_vasseur.pdf`.

Les éventuels signalements d'illisibilité, de troncature ou d'incertitude
doivent accompagner les données extraites. Le prompt ne retourne pas lire le
PDF pour les vérifier ou les réparer.

`extraction/pipeline.py` parcourt **uniquement les `.txt`**, applique le prompt
une fois par CV, vérifie que la réponse est un JSON valide et l'enregistre
dans `sorties/<id_candidat>.json`. Il utilise `<id_candidat>.pdf` comme nom de
source : conserver cette convention pour les PDF d'origine.

```bash
python3 extraction/pipeline.py datas_extract/ --texte-seul
python3 extraction/pipeline.py datas_extract/ --limite 2
```

La seconde commande nécessite `OPENAI_API_KEY` et déclenche des appels LLM
facturés. Aucun appel LLM n'a encore été lancé sur les CV de test.
Ce README ne doit pas être envoyé comme un CV. Ne pas envoyer
`cv-test/notes-reference.csv` au modèle : ce fichier sert à comparer les
résultats après traitement.

`analyse/agrege.py` transforme ensuite les JSON en CSV, et
`analyse/stats.py` lit ces CSV dans `analyse/`.
