"""Valide la structure du JSON court avant son analyse."""

import argparse
import sys
from pathlib import Path

if __package__:
    from .donnees import RACINE, charge_dossier
else:
    from donnees import RACINE, charge_dossier


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", type=Path, default=RACINE / "sorties")
    args = parser.parse_args()
    try:
        candidats = charge_dossier(args.dossier)
    except ValueError as erreur:
        print(erreur, file=sys.stderr)
        return 1
    print(f"{len(candidats)} JSON valides. La fidelite aux CV reste a verifier dans datas_extract/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
