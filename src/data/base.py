"""DataSource interface + the raw UCI schema every credit source must emit.

A ``DataSource`` yields a frame in the *original* UCI raw format (uppercase
columns, dotted target) so the existing ``src.preprocessing.clean_data`` chain
consumes it unchanged — synthetic, real-UCI CSV, or a gated feed all look
identical downstream.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

# Raw UCI schema (matches src/generate_data.generate_raw and scripts/ingest_uci).
RAW_COLUMNS = (
    ["ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
     "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    + [f"BILL_AMT{i}" for i in range(1, 7)]
    + [f"PAY_AMT{i}" for i in range(1, 7)]
    + ["default.payment.next.month"]
)


class DataSource(ABC):
    """A named source that returns credit rows in the raw UCI schema."""

    #: short machine name, e.g. "synthetic", "csv"
    name: str = ""
    #: one-line human description
    description: str = ""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Return a DataFrame with exactly ``RAW_COLUMNS`` (raw UCI format)."""


def validate_raw_schema(df: pd.DataFrame, origin: str) -> pd.DataFrame:
    """Return ``df`` reordered to ``RAW_COLUMNS`` or raise a helpful error.

    ``origin`` names the source (a path or connector) so schema mismatches point
    at the offending file rather than a bare column list.
    """
    have = set(df.columns)
    want = set(RAW_COLUMNS)
    missing = [c for c in RAW_COLUMNS if c not in have]
    extra = [c for c in df.columns if c not in want]
    if missing or extra:
        raise ValueError(
            f"{origin}: not a raw-UCI-schema frame. "
            f"missing={missing or 'none'} unexpected={extra or 'none'}. "
            f"Expected columns: {RAW_COLUMNS}"
        )
    return df[RAW_COLUMNS]
