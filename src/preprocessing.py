"""Data loading, cleaning, feature engineering and splitting.

Implements the function-level spec in Technical_Spec.md section 4.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from . import config


def load_data(path: str | None = None) -> pd.DataFrame:
    """Load the raw CSV from data/raw/. Returns the raw DataFrame."""
    path = str(path) if path is not None else str(config.RAW_CSV)
    return pd.read_csv(path)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Fix invalid category codes, rename columns to snake_case, drop id.

    - EDUCATION codes 0/5/6 -> 4 ('other')
    - MARRIAGE code 0 -> 3 ('other')
    - rename the verbose target to ``default_payment_next_month``
    """
    df = df.copy()

    # Normalise column names to snake_case (LIMIT_BAL -> limit_bal, PAY_0 -> pay_0).
    rename = {c: c.lower() for c in df.columns}
    rename["default.payment.next.month"] = config.TARGET
    df = df.rename(columns=rename)

    # Fix invalid / undocumented category codes.
    df["education"] = df["education"].replace({0: 4, 5: 4, 6: 4})
    df["marriage"] = df["marriage"].replace({0: 3})

    # The id column carries no predictive value.
    df = df.drop(columns=[c for c in ["id"] if c in df.columns])

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add the engineered features from Technical_Spec.md section 3.

    Returns a DataFrame ready for modelling, with no NaNs in engineered columns.
    """
    df = df.copy()

    df["avg_bill_amt"] = df[config.BILL_COLS].mean(axis=1)
    df["avg_pay_amt"] = df[config.PAY_AMT_COLS].mean(axis=1)

    # Guard against divide-by-zero for a zero credit limit.
    df["credit_utilization"] = df["avg_bill_amt"] / df["limit_bal"].replace(0, np.nan)
    df["credit_utilization"] = df["credit_utilization"].fillna(0.0)

    df["months_delayed_count"] = (df[config.PAY_COLS] > 0).sum(axis=1)

    # Payment trend: most-recent minus oldest monthly payment (positive = improving).
    df["payment_trend"] = df["pay_amt1"] - df["pay_amt6"]

    return df


def split_data(
    df: pd.DataFrame,
    target_col: str = config.TARGET,
    test_size: float = 0.2,
    random_state: int = 42,
):
    """Stratified train/test split (stratify on target due to class imbalance).

    Returns X_train, X_test, y_train, y_test.
    """
    feature_cols = config.feature_columns(df)
    X = df[feature_cols]
    y = df[target_col]
    return train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )


def build_processed_dataset(raw_path: str | None = None) -> pd.DataFrame:
    """Convenience end-to-end: load -> clean -> engineer. Returns modelling-ready df."""
    return engineer_features(clean_data(load_data(raw_path)))
