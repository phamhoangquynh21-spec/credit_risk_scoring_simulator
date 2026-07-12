"""Concrete credit DataSources: synthetic generator and raw-UCI CSV file."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..generate_data import generate_raw
from .base import DataSource, validate_raw_schema


class SyntheticSource(DataSource):
    """Wraps ``generate_raw`` — the deterministic synthetic UCI-shaped dataset."""

    name = "synthetic"
    description = "Synthetic UCI-format credit dataset (src.generate_data)."

    def __init__(self, n: int = 30_000, seed: int = 42):
        self.n = n
        self.seed = seed

    def load(self) -> pd.DataFrame:
        return generate_raw(n=self.n, seed=self.seed)


class CsvSource(DataSource):
    """Reads a raw-UCI-schema CSV (e.g. the real UCI file in data/raw/)."""

    name = "csv"
    description = "Raw-UCI-schema CSV file on disk."

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"CsvSource: no such file: {self.path}")
        df = pd.read_csv(self.path)
        return validate_raw_schema(df, origin=str(self.path))
