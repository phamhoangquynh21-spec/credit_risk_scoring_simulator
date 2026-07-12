"""HMDA / FFIEC loader (free, public US mortgage lending data).

Normalises an HMDA Loan/Application Register (LAR) sample down to the
demographic + outcome columns the fairness pipeline needs. The fairness audit
itself is Stage 7 — this only produces the tidy frame it consumes.

Attribution: HMDA data, Consumer Financial Protection Bureau / FFIEC (public).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# HMDA LAR column -> normalised name.
_RENAME = {
    "derived_sex": "sex",
    "derived_race": "race",
    "derived_ethnicity": "ethnicity",
    "action_taken": "action_taken",
    "loan_amount": "loan_amount",
    "income": "income",
}
# action_taken codes (HMDA): 1 = originated, 3 = denied.
_ORIGINATED = 1
_DENIED = 3


def load(path: str | Path) -> pd.DataFrame:
    """Load an HMDA LAR CSV sample into a normalised fairness-ready frame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"HMDA loader: no such file: {path}")
    df = pd.read_csv(path)

    missing = [c for c in _RENAME if c not in df.columns]
    if missing:
        raise ValueError(f"HMDA loader: missing expected columns {missing}")

    out = df[list(_RENAME)].rename(columns=_RENAME).copy()
    out["action_taken"] = pd.to_numeric(out["action_taken"], errors="coerce").astype("Int64")
    out["loan_amount"] = pd.to_numeric(out["loan_amount"], errors="coerce")
    out["income"] = pd.to_numeric(out["income"], errors="coerce")
    # Binary outcomes for fairness comparison. fillna(False) keeps a row with a
    # missing action_taken (NA on the nullable Int64 column) from aborting the
    # whole load; such rows map to 0 on both outcomes.
    out["originated"] = out["action_taken"].eq(_ORIGINATED).fillna(False).astype(int)
    out["denied"] = out["action_taken"].eq(_DENIED).fillna(False).astype(int)
    return out
