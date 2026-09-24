"""Train an exploratory baseline on reference total scores."""
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from preprocess import load_data

ROOT = Path(__file__).resolve().parents[1]

def main():
    cvs, scores = load_data()
    data = cvs.merge(scores[["candidate_id", "total_score"]], on="candidate_id", how="inner")
    data = data.dropna(subset=["cv_text", "total_score"])
    if len(data) < 3:
        raise SystemExit("Need at least 3 matched CVs with reference scores")
    model = Pipeline([("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1, 2), sublinear_tf=True)), ("regressor", Ridge(alpha=1.0))])
    model.fit(data["cv_text"], data["total_score"].astype(float))
    path = ROOT / "models" / "scorer.pkl"
    joblib.dump(model, path)
    print(f"Trained on {len(data)} CVs; saved {path}")
    print("Exploratory baseline only: this tiny dataset is not suitable for reliable deployment.")

if __name__ == "__main__":
    main()
