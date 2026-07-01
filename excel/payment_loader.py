"""
excel/payment_loader.py
------------------------
Loads and validates the Payment Party File locally.
Contents are NEVER written to database or sent over network.
"""
import pandas as pd

REQUIRED = ["Party-Code", "Party-Name", "Amount"]


class PaymentFileError(Exception):
    pass


def load_payment_file(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path, dtype=str) if file_path.lower().endswith(".csv") \
             else pd.read_excel(file_path, dtype=str)
    except Exception as e:
        raise PaymentFileError(f"Cannot read payment file: {e}")

    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise PaymentFileError(f"Missing columns: {', '.join(missing)}")

    df = df[REQUIRED].dropna(how="all").copy()
    df["_amount_raw"] = df["Amount"]
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return df.reset_index(drop=True)
