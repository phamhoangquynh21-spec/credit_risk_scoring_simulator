"""One-time ingest of the real UCI 'Default of Credit Card Clients' dataset.

Downloads the official zip, extracts the .xls, and writes it in the exact
format the existing pipeline expects (data/raw/credit_card_default.csv),
so `python -m src.train_model` retrains on REAL data with zero code changes.

License: UCI dataset, public for academic/portfolio use. Cited in README.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config  # noqa: E402

UCI_ZIP_URL = ("https://archive.ics.uci.edu/static/public/350/"
               "default+of+credit+card+clients.zip")
TARGET_VERBOSE = "default payment next month"

EXPECTED = (["ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
             "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
            + [f"BILL_AMT{i}" for i in range(1, 7)]
            + [f"PAY_AMT{i}" for i in range(1, 7)]
            + [TARGET_VERBOSE])


def transform_uci(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the raw xls frame and rename the target to the dotted form."""
    missing = [c for c in EXPECTED if c not in df.columns]
    if missing:
        raise ValueError(f"UCI frame missing expected columns: {missing}")
    out = df[EXPECTED].copy()
    return out.rename(columns={TARGET_VERBOSE: "default.payment.next.month"})


def download_raw() -> pd.DataFrame:
    import requests

    resp = requests.get(UCI_ZIP_URL, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xls_name = next(n for n in zf.namelist() if n.endswith(".xls"))
        with zf.open(xls_name) as fh:
            return pd.read_excel(fh, header=1, engine="xlrd")


def main() -> None:
    df = transform_uci(download_raw())
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.RAW_CSV, index=False)
    rate = df["default.payment.next.month"].mean()
    print(f"Wrote {len(df):,} REAL rows to {config.RAW_CSV}")
    print(f"Default rate: {rate:.4f} (expected ~0.2212)")


if __name__ == "__main__":
    main()
