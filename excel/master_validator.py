"""
excel/master_validator.py
--------------------------
Loads and validates the Master Data File locally.
Contents are NEVER written to database or sent over network.
"""
import pandas as pd

REQUIRED = ["Party-Code", "Party-Name", "Bank-Account-No", "IFSC-Code"]


class MasterFileError(Exception):
    pass


def load_master_file(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path, dtype=str) if file_path.lower().endswith(".csv") \
             else pd.read_excel(file_path, dtype=str)
    except Exception as e:
        raise MasterFileError(f"Cannot read master file: {e}")

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise MasterFileError(f"Missing columns: {', '.join(missing)}")

    return df[REQUIRED].dropna(how="all").reset_index(drop=True)


def normalize(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).upper()
