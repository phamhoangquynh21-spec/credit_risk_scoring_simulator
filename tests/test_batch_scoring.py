"""Tests for explain.score_batch — the CSV batch-scoring logic behind the
dashboard's 'Batch Scoring (CSV)' tab."""

import pytest

from src.explain import score_batch
from src.generate_data import generate_raw
from src.preprocessing import clean_data, engineer_features, split_data
from src.train_model import train_advanced


@pytest.fixture(scope="module")
def model_and_features():
    df = engineer_features(clean_data(generate_raw(n=1_500, seed=3)))
    X_train, _, y_train, _ = split_data(df)
    model = train_advanced(X_train, y_train, model_type="randomforest")
    return model, list(X_train.columns)


def test_score_batch_raw_uci_format(model_and_features):
    model, feats = model_and_features
    raw = generate_raw(n=25, seed=9)
    out = score_batch(model, feats, raw)
    assert len(out) == 25
    assert out["risk_score"].between(0, 100).all()
    assert set(out["risk_band"]).issubset({"Low", "Medium", "High"})
    # Original columns are preserved alongside the scores.
    assert "LIMIT_BAL" in out.columns


def test_score_batch_accepts_snake_case_without_target(model_and_features):
    model, feats = model_and_features
    cleaned = clean_data(generate_raw(n=10, seed=4)).drop(
        columns=["default_payment_next_month"])
    out = score_batch(model, feats, cleaned)
    assert len(out) == 10
    assert "risk_score" in out.columns


def test_score_batch_missing_column_raises(model_and_features):
    model, feats = model_and_features
    raw = generate_raw(n=5, seed=9).drop(columns=["AGE"])
    with pytest.raises(ValueError, match="age"):
        score_batch(model, feats, raw)
