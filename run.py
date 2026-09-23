"""Lance toute la chaine, du PDF aux statistiques.

    python3 run.py                    # tout
    python3 run.py --limite 2         # essai sur 2 CV avant de payer les 11
    python3 run.py --depuis controle  # reprend a une etape
    python3 run.py --jusqua llm       # s'arrete apres une etape

Les etapes, dans l'ordre :

    txt       cv-test/*.pdf   -> data/txt/*.txt      gratuit
    llm       data/txt/*.txt  -> sorties/*.json      FACTURE, un appel par CV
    controle  verifie les JSON                       gratuit
    agrege    sorties/*.json  -> analyse/*.csv       gratuit
    stats     analyse/*.csv   -> rapport             gratuit

La chaine s'arrete des qu'une etape echoue. En particulier, un controle de
coherence en erreur bloque les statistiques : mieux vaut pas de chiffres que
des chiffres faux. --ignorer-controle passe outre.
"""

import argparse
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
ETAPES = ["txt", "llm", "controle", "agrege", "stats"]


def commande_de(etape: str, args) -> list[str]:
    py = [sys.executable]
    if etape == "txt":
        return py + ["extraction/extrait_texte.py", str(args.cv)] + (["--force"] if args.force else [])
    if etape == "llm":
        cmd = py + ["extraction/pipeline.py", "-m", args.modele]
        if args.limite:
            cmd += ["--limite", str(args.limite)]
        if args.force:
            cmd += ["--force"]
        return cmd
    if etape == "controle":
        return py + ["analyse/controle_coherence.py", "sorties"]
    if etape == "agrege":
        return py + ["analyse/agrege.py", "sorties"]
    return py + ["analyse/stats.py"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--depuis", choices=ETAPES, default="txt")
    parser.add_argument("--jusqua", choices=ETAPES, default="stats")
    parser.add_argument("--cv", default=RACINE / "cv-test", type=Path)
    parser.add_argument("-m", "--modele", default="gpt-4o-mini")
    parser.add_argument("--limite", type=int, help="ne traiter que les N premiers CV")
    parser.add_argument("--force", action="store_true", help="refaire meme si les sorties existent")
    parser.add_argument(
        "--ignorer-controle",
        action="store_true",
        help="continuer malgre des erreurs de coherence (les stats seront fausses)",
    )
    args = parser.parse_args()

    debut, fin = ETAPES.index(args.depuis), ETAPES.index(args.jusqua)
    if debut > fin:
        print(f"--depuis {args.depuis} est apres --jusqua {args.jusqua}", file=sys.stderr)
        return 1
    a_faire = ETAPES[debut : fin + 1]

    if "llm" in a_faire:
        combien = f"{args.limite}" if args.limite else "tous les"
        print(f"L'etape llm appelle {args.modele} sur {combien} CV -- c'est facture.\n", flush=True)

    for numero, etape in enumerate(a_faire, 1):
        commande = commande_de(etape, args)
        print(f"\n{'=' * 60}\n[{numero}/{len(a_faire)}] {etape}\n{'=' * 60}", flush=True)
        code = subprocess.run(commande, cwd=RACINE).returncode

        if code == 0:
            continue
        if etape == "controle":
            if args.ignorer_controle:
                print("\nControle en erreur, poursuite demandee : les stats seront fausses.")
                continue
            print(
                "\nControle de coherence en erreur : la chaine s'arrete.\n"
                "Corriger le prompt et relancer, ou --ignorer-controle pour passer outre.",
                file=sys.stderr,
            )
            return 1
        if etape == "txt":
            # extrait_texte.py retourne 1 quand des PDF n'ont pas de couche
            # texte. Les autres CV sont extraits, la chaine peut continuer.
            print("\nCertains PDF demandent un OCR, les autres continuent.")
            continue

        print(f"\nEtape '{etape}' en echec (code {code}), la chaine s'arrete.", file=sys.stderr)
        return code

    print(f"\n{'=' * 60}\nTermine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
