"""Load a trained baseline and predict a score for one CV text."""
from pathlib import Path
import joblib
ROOT = Path(__file__).resolve().parents[1]

def predict(text, model_path=ROOT / "models" / "scorer.pkl"):
    if not Path(model_path).exists():
        raise FileNotFoundError(f"No trained model at {model_path}; run python src/train.py first")
    model = joblib.load(model_path)
    score = float(model.predict([text])[0])
    return max(0.0, min(20.0, score))
