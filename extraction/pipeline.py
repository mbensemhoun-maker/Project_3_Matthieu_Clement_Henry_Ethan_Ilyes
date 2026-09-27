"""Etape 2 : texte -> LLM -> sorties/*.json

    python3 extraction/extrait_texte.py cv-test/    # etape 1, d'abord
    export OPENAI_API_KEY=sk-...
    python3 extraction/pipeline.py --limite 2       # essai sur 2 CV
    python3 extraction/pipeline.py                  # les 11

Applique le prompt de prompt.md a chaque texte de datas_extract/ et ecrit un JSON
par candidat. Ne lit jamais les PDF : c'est extrait_texte.py qui s'en charge,
ce qui permet de relancer l'extraction LLM autant qu'on veut sans les relire,
et de corriger un texte a la main avant de le passer au modele.

Puis :

    python3 analyse/controle_coherence.py sorties/
    python3 analyse/agrege.py sorties/ && python3 analyse/stats.py
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from analyse.donnees import valide_cv


def prompt_depuis_markdown(chemin: Path) -> str:
    """Extrait le prompt du bloc ``` de prompt.md.

    Le prompt vit dans la doc plutot que dans le code : c'est lui que l'equipe
    relit et modifie, et une copie dans un .py finirait par diverger.
    """
    texte = chemin.read_text(encoding="utf-8")
    blocs = re.findall(r"^```(?:text)?\n(.*?)^```", texte, re.MULTILINE | re.DOTALL)
    if not blocs:
        raise SystemExit(f"Aucun bloc ``` trouve dans {chemin}")
    # Le premier bloc est le prompt ; les suivants sont des exemples de code.
    return blocs[0].strip()


def construit_message(entree: dict) -> str:
    """Remplit les variables du prompt.

    On fait un remplacement direct plutot que d'utiliser ChatPromptTemplate :
    le prompt contient le gabarit JSON complet, donc des centaines d'accolades
    que le moteur de template prendrait pour des variables. Il faudrait toutes
    les echapper en {{ }}, ce qui rendrait prompt.md illisible pour l'equipe.
    """
    # Une seule passe conserve les eventuelles accolades du CV telles quelles.
    return re.sub(
        r"\{(donnees_extraites|id_candidat|fichier_source)\}",
        lambda match: entree[match[1]],
        entree["prompt"],
    )


def nettoie_json(reponse: str) -> str:
    """Retire ce que le modele ajoute autour du JSON malgre la consigne.

    Mode d'echec le plus courant : un bloc ```json, ou une phrase
    d'introduction. On coupe aux accolades extremes.
    """
    texte = reponse.strip()
    texte = re.sub(r"^```(?:json)?\s*|\s*```$", "", texte, flags=re.MULTILINE).strip()
    # Laisser le parseur refuser une liste, meme si elle contient un objet.
    if texte.startswith("["):
        return texte
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("aucun objet JSON dans la reponse")
    return texte[debut : fin + 1]


def construit_chaine(modele: str, temperature: float):
    """Chaine LCEL : dict -> message -> LLM -> texte."""
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.runnables import RunnableLambda
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise SystemExit("LangChain manquant : pip install -r extraction/requirements.txt")

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY absent de l'environnement")

    llm = ChatOpenAI(
        model=modele,
        # Reduit la variabilite des reponses, sans garantir leur identite.
        temperature=temperature,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    return RunnableLambda(construit_message) | llm | StrOutputParser()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", default=RACINE / "datas_extract", type=Path)
    parser.add_argument("-o", "--sortie", default=RACINE / "sorties", type=Path)
    parser.add_argument("-p", "--prompt", default=RACINE / "prompt.md", type=Path)
    parser.add_argument("-m", "--modele", default="gpt-4o-mini")
    parser.add_argument("-t", "--temperature", type=float, default=0.0)
    parser.add_argument("--limite", type=int, help="ne traiter que les N premiers CV")
    parser.add_argument("--concurrence", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="retraiter les CV deja extraits")
    parser.add_argument(
        "--texte-seul",
        action="store_true",
        help="montrer ce qui partirait au LLM et s'arreter (ni cle ni cout)",
    )
    args = parser.parse_args()
    if args.limite is not None and args.limite < 1:
        parser.error("--limite doit etre positif")
    if args.concurrence < 1:
        parser.error("--concurrence doit etre positif")

    fichiers = sorted(args.dossier.glob("*.txt"))
    if args.limite:
        fichiers = fichiers[: args.limite]
    if not fichiers:
        print(f"Aucun .txt dans {args.dossier}/", file=sys.stderr)
        if list(args.dossier.glob("*.pdf")):
            print("Ce dossier contient des PDF : lancer d'abord", file=sys.stderr)
            print(f"  python3 extraction/extrait_texte.py {args.dossier}", file=sys.stderr)
        return 1

    prompt = prompt_depuis_markdown(args.prompt)
    for variable in ["{donnees_extraites}", "{id_candidat}", "{fichier_source}"]:
        if variable not in prompt:
            parser.error(f"Le prompt doit contenir {variable}. Utiliser le nouveau prompt.md.")
    args.sortie.mkdir(parents=True, exist_ok=True)

    entrees, ignores, erreurs_entree = [], [], []
    for fichier in fichiers:
        destination = args.sortie / f"{fichier.stem}.json"
        if destination.exists() and not args.force:
            try:
                existant = json.loads(destination.read_text(encoding="utf-8"))
                erreurs = valide_cv(existant)
                if erreurs:
                    raise ValueError("; ".join(erreurs))
                if existant["meta"] != {"id_candidat": fichier.stem, "fichier_source": f"{fichier.stem}.pdf"}:
                    raise ValueError("Identifiants du JSON incompatibles avec son fichier source")
            except (OSError, UnicodeError, ValueError) as erreur:
                erreurs_entree.append(f"{destination.name} : {erreur}. Corriger ou regenerer avec --force.")
            ignores.append(fichier.name)
            continue
        texte = fichier.read_text(encoding="utf-8").strip()
        if not texte:
            # extrait_texte.py ecrit un .txt vide quand le PDF n'a pas de couche
            # texte. Envoyer ca au LLM produirait un JSON tout null,
            # indistinguable d'un CV reellement vide -- et facture.
            erreurs_entree.append(f"{fichier.name} : texte vide, verifier l'extraction du PDF")
            continue
        entrees.append(
            {
                "prompt": prompt,
                "donnees_extraites": texte,
                "id_candidat": fichier.stem,
                # Le nom du PDF d'origine, cle de jointure avec notes-reference.csv.
                "fichier_source": f"{fichier.stem}.pdf",
                "_destination": destination,
                "_nom": fichier.name,
            }
        )

    if ignores:
        print(f"{len(ignores)} CV deja extrait(s), ignore(s) (--force pour refaire)")
    if erreurs_entree:
        print("\n".join(erreurs_entree), file=sys.stderr)
        return 1
    if not entrees:
        print("Rien a traiter.")
        return 0

    if args.texte_seul:
        for entree in entrees:
            texte = entree["donnees_extraites"]
            print(f"  {entree['_nom']:28} {len(texte):6} caracteres, {len(texte.splitlines()):3} lignes")
        print(f"\n{len(entrees)} CV prets. Sans --texte-seul, ils partiraient au {args.modele}.")
        return 0

    chaine = construit_chaine(args.modele, args.temperature)
    print(f"{len(entrees)} CV -> {args.modele} (concurrence {args.concurrence})")

    reponses = chaine.batch(entrees, config={"max_concurrency": args.concurrence})

    ecrits, echecs = 0, []
    for entree, reponse in zip(entrees, reponses):
        try:
            donnees = json.loads(nettoie_json(reponse))
            if not isinstance(donnees, dict):
                raise ValueError("La reponse doit etre un objet JSON")
            # Les identifiants viennent du fichier, pas du modele.
            donnees["meta"] = {"id_candidat": entree["id_candidat"], "fichier_source": entree["fichier_source"]}
            erreurs = valide_cv(donnees)
            if erreurs:
                raise ValueError("; ".join(erreurs))
        except (ValueError, json.JSONDecodeError) as e:
            echecs.append((entree["_nom"], str(e)))
            # On garde la reponse brute : sans elle, impossible de savoir si le
            # modele a mal repondu ou si c'est le nettoyage qui a rate.
            brut = entree["_destination"].with_suffix(".brut.txt")
            brut.write_text(reponse, encoding="utf-8")
            continue

        entree["_destination"].write_text(
            json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ecrits += 1

    print(f"\n{ecrits} JSON ecrit(s) dans {args.sortie}/")
    for nom, erreur in echecs:
        print(f"  echec : {nom} ({erreur}) -- reponse brute conservee", file=sys.stderr)

    if ecrits:
        print("\nEtape suivante :")
        print(f"  python3 analyse/controle_coherence.py {args.sortie}")
        print(f"  python3 analyse/agrege.py {args.sortie} && python3 analyse/stats.py")

    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
