"""Etape 1 : PDF -> texte brut, un .txt par CV.

    python3 extraction/extrait_texte.py cv-test/ -o data/txt/

Aucun appel LLM, donc gratuit et rejouable autant qu'on veut.

Pourquoi passer par des fichiers plutot que d'enchainer directement sur le LLM :
on peut ouvrir les .txt et voir ce que le modele va reellement lire. Un CV mal
lu se repere la, avant de payer l'appel, et se corrige a la main si besoin.
C'est aussi ce qui permet de relancer l'extraction LLM sans relire les PDF.

Ce n'est pas de l'OCR au sens strict : on lit la couche texte deja presente
dans le PDF. Un CV scanne en image ressort vide -- le script le signale.
Brancher un vrai OCR revient a remplacer texte_du_pdf().
"""

import argparse
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def texte_du_pdf(chemin: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("pypdf manquant : pip install -r extraction/requirements.txt")

    reader = PdfReader(str(chemin))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", default=RACINE / "cv-test", type=Path)
    parser.add_argument("-o", "--sortie", default=RACINE / "data" / "txt", type=Path)
    parser.add_argument("--force", action="store_true", help="reecrire les .txt existants")
    args = parser.parse_args()

    pdfs = sorted(args.dossier.glob("*.pdf"))
    if not pdfs:
        print(f"Aucun PDF dans {args.dossier}/", file=sys.stderr)
        return 1

    args.sortie.mkdir(parents=True, exist_ok=True)
    ecrits, ignores, vides = 0, 0, []

    for pdf in pdfs:
        destination = args.sortie / f"{pdf.stem}.txt"
        if destination.exists() and not args.force:
            ignores += 1
            continue

        texte = texte_du_pdf(pdf)
        if not texte:
            # On ecrit quand meme le fichier vide : son existence dit que le PDF
            # a ete traite, et sa taille nulle dit qu'il faut un OCR. Sans ca,
            # un PDF scanne serait indistinguable d'un PDF pas encore traite.
            vides.append(pdf.name)

        destination.write_text(texte, encoding="utf-8")
        ecrits += 1
        print(f"  {pdf.name:28} {len(texte):6} car.  {len(texte.splitlines()):3} lignes"
              + ("   <- VIDE, OCR necessaire" if not texte else ""))

    print(f"\n{ecrits} fichier(s) ecrit(s) dans {args.sortie}/")
    if ignores:
        print(f"{ignores} deja present(s), ignore(s) (--force pour refaire)")
    if vides:
        print(f"\n{len(vides)} PDF sans couche texte, a passer a un OCR :", file=sys.stderr)
        for nom in vides:
            print(f"  {nom}", file=sys.stderr)

    if ecrits:
        print(f"\nEtape suivante :\n  python3 extraction/pipeline.py {args.sortie}")
    return 1 if vides else 0


if __name__ == "__main__":
    sys.exit(main())
