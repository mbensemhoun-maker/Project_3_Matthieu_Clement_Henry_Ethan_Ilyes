# Vérifications

`exemples_manuels/` contient les trois exemples historiques saisis à la main.
Ils servent uniquement aux tests du code. Le notebook ne les charge jamais.

`attendus_cv.json` est une référence factuelle limitée, relue dans les 11 textes :
mention du bac, langages explicitement cités, nombre de stages et notes de maths.
Elle ne contient aucune note d’admission, n’est jamais envoyée au modèle et
n’est jamais utilisée pour remplacer ses réponses.

Les tests vérifient aussi les informations manquantes, les bornes des scores,
les critères expliqués, la provenance et l’invalidation des caches modifiés.
Le contrôle de ces quelques champs ne démontre pas une extraction parfaite.
