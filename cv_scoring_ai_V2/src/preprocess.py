"""Load and validate the CV and reference score tables."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCORE_COLUMNS = [
    "excellence_academique_sur6", "aptitude_quantitative_sur4",
    "competences_data_tech_sur2", "anglais_langues_sur2",
    "experience_pro_sur3", "engagement_associatif_sur2",
    "ouverture_internationale_sur0.5", "coherence_parcours_sur0.5",
]

def load_data(data_dir=ROOT / "data"):
    cvs = pd.read_csv(data_dir / "cvs.csv", encoding="utf-8-sig")
    scores = pd.read_csv(data_dir / "scores.csv", sep=";", encoding="utf-8-sig")
    required = {"candidate_id", "source_file", "cv_text"}
    missing = required - set(cvs.columns)
    if missing:
        raise ValueError(f"cvs.csv missing columns: {sorted(missing)}")
    cvs["candidate_id"] = cvs["candidate_id"].astype(str)
    scores["candidate_id"] = scores["fichier"].astype(str).str.removesuffix(".pdf").str.lower()
    scores = scores.rename(columns={"total_sur20": "total_score"})
    return cvs, scores
