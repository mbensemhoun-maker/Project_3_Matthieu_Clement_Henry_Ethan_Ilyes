"""Pipeline LangChain : PDF -> texte -> LLM -> sorties/*.json

    python3 extraction/pipeline.py cv-test/ -o sorties/

Applique le prompt de prompt.md a chaque CV et ecrit un JSON par candidat.
C'est l'etape qui manquait entre les PDF et la chaine d'analyse.

    export OPENAI_API_KEY=sk-...
    python3 extraction/pipeline.py cv-test/ --limite 2   # essai sur 2 CV
    python3 extraction/pipeline.py cv-test/              # les 11

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


def prompt_depuis_markdown(chemin: Path) -> str:
    """Extrait le prompt du bloc ``` de prompt.md.

    Le prompt vit dans la doc plutot que dans le code : c'est lui que l'equipe
    relit et modifie, et une copie dans un .py finirait par diverger.
    """
    texte = chemin.read_text(encoding="utf-8")
    blocs = re.findall(r"^```\n(.*?)^```", texte, re.MULTILINE | re.DOTALL)
    if not blocs:
        raise SystemExit(f"Aucun bloc ``` trouve dans {chemin}")
    # Le premier bloc est le prompt ; les suivants sont des exemples de code.
    return blocs[0].strip()


def texte_du_pdf(chemin: Path) -> str:
    """Couche texte du PDF.

    Ce n'est PAS de l'OCR : ca ne lit que les PDF qui contiennent deja du texte.
    Un CV scanne en image ressortira vide, et le script le signale. Pour ces
    cas-la il faudra brancher un vrai OCR (tesseract, ou une API type Mistral
    OCR / Azure Document Intelligence) a la place de cette fonction.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("pypdf manquant : pip install -r extraction/requirements.txt")

    reader = PdfReader(str(chemin))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def construit_message(entree: dict) -> str:
    """Remplit les variables du prompt.

    On fait un remplacement direct plutot que d'utiliser ChatPromptTemplate :
    le prompt contient le gabarit JSON complet, donc des centaines d'accolades
    que le moteur de template prendrait pour des variables. Il faudrait toutes
    les echapper en {{ }}, ce qui rendrait prompt.md illisible pour l'equipe.
    """
    message = entree["prompt"]
    for cle, valeur in (
        ("{texte_ocr}", entree["texte_ocr"]),
        ("{id_candidat}", entree["id_candidat"]),
        ("{fichier_source}", entree["fichier_source"]),
    ):
        message = message.replace(cle, valeur)
    return message


def nettoie_json(reponse: str) -> str:
    """Retire ce que le modele ajoute autour du JSON malgre la consigne.

    Mode d'echec le plus courant : un bloc ```json, ou une phrase
    d'introduction. On coupe aux accolades extremes.
    """
    texte = reponse.strip()
    texte = re.sub(r"^```(?:json)?\s*|\s*```$", "", texte, flags=re.MULTILINE).strip()
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
        # temperature 0 : l'extraction doit etre reproductible d'un run a
        # l'autre, sinon on ne peut pas savoir si un changement de resultat
        # vient du prompt qu'on vient de modifier ou du hasard.
        temperature=temperature,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    return RunnableLambda(construit_message) | llm | StrOutputParser()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", nargs="?", default=RACINE / "cv-test", type=Path)
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
        help="extraire le texte des PDF et s'arreter, sans appeler le LLM (ni cle ni cout)",
    )
    args = parser.parse_args()

    pdfs = sorted(args.dossier.glob("*.pdf"))
    if args.limite:
        pdfs = pdfs[: args.limite]
    if not pdfs:
        print(f"Aucun PDF dans {args.dossier}/", file=sys.stderr)
        return 1

    prompt = prompt_depuis_markdown(args.prompt)
    args.sortie.mkdir(parents=True, exist_ok=True)

    entrees, ignores = [], []
    for pdf in pdfs:
        destination = args.sortie / f"{pdf.stem}.json"
        if destination.exists() and not args.force:
            ignores.append(pdf.name)
            continue
        texte = texte_du_pdf(pdf)
        if not texte:
            # Pas de couche texte : c'est un scan. Le signaler plutot que
            # d'envoyer une chaine vide au LLM, qui repondrait un JSON tout
            # null indistinguable d'un CV reellement vide.
            print(f"  {pdf.name} : aucune couche texte, OCR necessaire", file=sys.stderr)
            continue
        entrees.append(
            {
                "prompt": prompt,
                "texte_ocr": texte,
                "id_candidat": pdf.stem,
                "fichier_source": pdf.name,
                "_destination": destination,
                "_nom": pdf.name,
            }
        )

    if ignores:
        print(f"{len(ignores)} CV deja extrait(s), ignore(s) (--force pour refaire)")
    if not entrees:
        print("Rien a traiter.")
        return 0

    if args.texte_seul:
        for entree in entrees:
            texte = entree["texte_ocr"]
            print(f"  {entree['_nom']:28} {len(texte):6} caracteres, {len(texte.splitlines()):3} lignes")
        print(f"\n{len(entrees)} PDF lisibles. Sans --texte-seul, ils partiraient au LLM.")
        return 0

    chaine = construit_chaine(args.modele, args.temperature)
    print(f"{len(entrees)} CV -> {args.modele} (concurrence {args.concurrence})")

    reponses = chaine.batch(entrees, config={"max_concurrency": args.concurrence})

    ecrits, echecs = 0, []
    for entree, reponse in zip(entrees, reponses):
        try:
            donnees = json.loads(nettoie_json(reponse))
        except (ValueError, json.JSONDecodeError) as e:
            echecs.append((entree["_nom"], str(e)))
            # On garde la reponse brute : sans elle, impossible de savoir si le
            # modele a mal repondu ou si c'est le nettoyage qui a rate.
            brut = entree["_destination"].with_suffix(".brut.txt")
            brut.write_text(reponse, encoding="utf-8")
            continue

        # Le modele oublie souvent meta malgre le gabarit : on le remplit ici,
        # c'est la seule information qu'on connait mieux que lui.
        donnees.setdefault("meta", {})
        donnees["meta"]["id_candidat"] = entree["id_candidat"]
        donnees["meta"]["fichier_source"] = entree["fichier_source"]

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
