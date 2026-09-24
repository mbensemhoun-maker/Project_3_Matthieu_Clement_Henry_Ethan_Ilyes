"""Create semantic embeddings for CV text (downloads the model on first use)."""
from pathlib import Path
import numpy as np

def embed_texts(texts, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit("Install requirements.txt to use embeddings") from exc
    model = SentenceTransformer(model_name)
    return np.asarray(model.encode(list(texts), show_progress_bar=True, normalize_embeddings=True))

if __name__ == "__main__":
    from preprocess import load_data
    cvs, _ = load_data()
    vectors = embed_texts(cvs["cv_text"].fillna(""))
    out = Path(__file__).resolve().parents[1] / "models" / "cv_embeddings.npy"
    np.save(out, vectors)
    print(f"Saved {len(vectors)} embeddings to {out}")
