"""
excel/matching_engine.py
-------------------------
Matches Payment File rows against Master Data File.
Both Party-Code AND Party-Name must match (case-insensitive,
whitespace-normalized) the same master record.

Reasons for invalid rows:
  Party Code Not Found  — code absent from master
  Party Name Mismatch   — code found, but name differs
  Both Mismatch         — neither code nor name found
  Duplicate Entry       — same valid pair seen before in this file
  Invalid Amount        — amount missing or not numeric
"""
import pandas as pd
from excel.master_validator import normalize


def match_payments(master_df: pd.DataFrame, payment_df: pd.DataFrame):
    """Returns (valid_rows, invalid_rows) as lists of dicts."""

    by_code = {}
    all_names = set()
    for _, row in master_df.iterrows():
        code = normalize(row["Party-Code"])
        name = normalize(row["Party-Name"])
        if code and code not in by_code:
            by_code[code] = row
        if name:
            all_names.add(name)

    valid, invalid = [], []
    seen = set()

    for _, prow in payment_df.iterrows():
        code = normalize(prow["Party-Code"])
        name = normalize(prow["Party-Name"])
        amount = prow["Amount"]
        raw_amount = prow.get("_amount_raw", amount)
        bad_amount = pd.isna(amount)

        master_row = by_code.get(code)

        if master_row is None:
            reason = "Both Mismatch" if name not in all_names else "Party Code Not Found"
            if bad_amount:
                reason += "; Invalid Amount"
            invalid.append({"Party-Name": prow["Party-Name"], "Party-Code": prow["Party-Code"],
                             "Amount": raw_amount, "Reason": reason})
            continue

        if normalize(master_row["Party-Name"]) != name:
            reason = "Party Name Mismatch" + ("; Invalid Amount" if bad_amount else "")
            invalid.append({"Party-Name": prow["Party-Name"], "Party-Code": prow["Party-Code"],
                             "Amount": raw_amount, "Reason": reason})
            continue

        if (code, name) in seen:
            invalid.append({"Party-Name": prow["Party-Name"], "Party-Code": prow["Party-Code"],
                             "Amount": raw_amount, "Reason": "Duplicate Entry"})
            continue

        if bad_amount:
            invalid.append({"Party-Name": prow["Party-Name"], "Party-Code": prow["Party-Code"],
                             "Amount": raw_amount, "Reason": "Invalid Amount"})
            continue

        seen.add((code, name))
        valid.append({
            "Party-Name": master_row["Party-Name"],
            "Party-Code": master_row["Party-Code"],
            "Bank-Account-No": master_row["Bank-Account-No"],
            "IFSC-Code": master_row["IFSC-Code"],
            "Amount": amount,
        })

    return valid, invalid
