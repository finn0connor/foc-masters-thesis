import os
from pathlib import Path

DATA_DIR = Path(os.environ.get(
    "THESIS_DATA",
    r"C:\Users\FOCONNO1\OneDrive - Trinity College Dublin\5th Year\MAI Project\thesis-data",
))
RAW_DIR = DATA_DIR / "individual_csvs"   # one subfolder per category, e.g. outturn\
PROCESSED_DIR = DATA_DIR / "processed"
