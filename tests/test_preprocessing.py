"""Tests for src/preprocessing.py — Technical_Spec.md section 9."""

import pandas as pd
import pytest

from src import config
from src.generate_data import generate_raw
from src.preprocessing import clean_data, engineer_features, split_data


@pytest.fixture(scope="module")
def raw_df():
    return generate_raw(n=2_000, seed=7)


@pytest.fixture(scope="module")
def clean_df(raw_df):
    return clean_data(raw_df)


def test_clean_data_fixes_invalid_education_codes(clean_df):
    # Codes 0, 5, 6 must be folded into 4 ("other").
    assert set(clean_df["education"].unique()).issubset({1, 2, 3, 4})


def test_clean_data_fixes_invalid_marriage_codes(clean_df):
    assert set(clean_df["marriage"].unique()).issubset({1, 2, 3})


def test_clean_data_renames_target_and_drops_id(clean_df):
    assert config.TARGET in clean_df.columns
    assert "default.payment.next.month" not in clean_df.columns
    assert "id" not in clean_df.columns


def test_clean_data_columns_are_snake_case(clean_df):
    assert "limit_bal" in clean_df.columns
    assert "pay_0" in clean_df.columns
    assert all(c == c.lower() for c in clean_df.columns)


def test_engineer_features_creates_expected_columns(clean_df):
    df = engineer_features(clean_df)
    for col in config.ENGINEERED:
        assert col in df.columns


def test_engineer_features_has_no_nans(clean_df):
    df = engineer_features(clean_df)
    assert not df[config.ENGINEERED].isna().any().any()


def test_credit_utilization_is_finite_with_zero_limit():
    # A zero credit limit must not produce inf/NaN utilisation.
    raw = generate_raw(n=50, seed=1)
    clean = clean_data(raw)
    clean.loc[clean.index[0], "limit_bal"] = 0
    df = engineer_features(clean)
    assert df["credit_utilization"].notna().all()
    assert (df["credit_utilization"].abs() < 1e9).all()


def test_split_data_is_stratified(clean_df):
    df = engineer_features(clean_df)
    X_train, X_test, y_train, y_test = split_data(df, test_size=0.2)
    assert len(X_test) == pytest.approx(0.2 * len(df), rel=0.05)
    # Stratification keeps the default rate stable across splits.
    assert y_train.mean() == pytest.approx(y_test.mean(), abs=0.03)
    assert config.TARGET not in X_train.columns
