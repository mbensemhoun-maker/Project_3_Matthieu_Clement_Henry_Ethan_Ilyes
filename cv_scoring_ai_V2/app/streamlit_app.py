"""Small local demo for the exploratory scoring baseline."""
import sys
from pathlib import Path
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from predict import predict

st.set_page_config(page_title="CV Scoring AI", page_icon="??")
st.title("CV Scoring AI ? prototype")
st.caption("Exploratory estimate trained on the reference scores. Always review the CV and rubric manually.")
text = st.text_area("Paste CV text", height=300)
if st.button("Estimate score", type="primary", disabled=not text.strip()):
    try:
        st.metric("Estimated total", f"{predict(text):.1f} / 20")
    except FileNotFoundError:
        st.error("Model not trained yet. From cv_scoring_ai, run: python src/train.py")
