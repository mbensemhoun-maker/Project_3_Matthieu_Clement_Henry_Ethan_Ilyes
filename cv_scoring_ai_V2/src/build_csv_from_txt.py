"""Combine the text files in data/CV_TXT into data/cvs_from_txt.csv.

Run from any directory with:
    python src/build_csv_from_txt.py
"""
from pathlib import Path
import csv


PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_DIR / "data" / "CV_TXT"
OUTPUT_FILE = PROJECT_DIR / "data" / "cvs_from_txt.csv"


def build_csv() -> int:
    """Write one CSV row per TXT file and return the number of rows written."""
    txt_files = sorted(INPUT_DIR.glob("*.txt"), key=lambda path: path.name.lower())
    if not txt_files:
        raise FileNotFoundError(f"No .txt files found in {INPUT_DIR}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig makes the resulting CSV display correctly in Excel while remaining
    # readable as UTF-8 by Python and pandas.
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["Name", "Content"])
        writer.writeheader()
        for txt_file in txt_files:
            content = txt_file.read_text(encoding="utf-8")
            writer.writerow({"Name": txt_file.name, "Content": content})

    return len(txt_files)


if __name__ == "__main__":
    count = build_csv()
    print(f"Wrote {count} CVs to {OUTPUT_FILE}")
