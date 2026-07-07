"""End-to-end pipeline tests — Technical_Spec.md section 9.

load -> clean -> engineer -> split -> train -> predict must yield valid
probabilities, and the advanced model must beat random on this signalled data.
"""

import numpy as np
import pytest

from src.explain import explain_single_customer, risk_score
from src.generate_data import generate_raw
from src.preprocessing import clean_data, engineer_features, split_data
from src.train_model import evaluate_model, train_advanced, train_baseline


@pytest.fixture(scope="module")
def split():
    df = engineer_features(clean_data(generate_raw(n=3_000, seed=11)))
    return split_data(df)


def test_baseline_produces_valid_probabilities(split):
    X_train, X_test, y_train, y_test = split
    model = train_baseline(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    assert proba.shape[0] == len(X_test)
    assert np.all((proba >= 0.0) & (proba <= 1.0))


def test_evaluate_model_returns_expected_keys(split):
    X_train, X_test, y_train, y_test = split
    model = train_baseline(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)
    for key in ["auc_roc", "precision", "recall", "f1", "confusion_matrix"]:
        assert key in metrics
    assert 0.0 <= metrics["auc_roc"] <= 1.0


def test_advanced_model_beats_random(split):
    X_train, X_test, y_train, y_test = split
    model = train_advanced(X_train, y_train, model_type="randomforest")
    metrics = evaluate_model(model, X_test, y_test)
    # Signal is real: AUC should be comfortably above chance.
    assert metrics["auc_roc"] > 0.65


def test_explain_single_customer_returns_top_features(split):
    X_train, X_test, y_train, y_test = split
    model = train_advanced(X_train, y_train, model_type="randomforest")
    pairs = explain_single_customer(model, X_test.iloc[0])
    assert len(pairs) == 5
    assert all(isinstance(name, str) for name, _ in pairs)
    # Sorted by absolute contribution (descending).
    contribs = [abs(c) for _, c in pairs]
    assert contribs == sorted(contribs, reverse=True)


def test_risk_score_in_range(split):
    X_train, X_test, y_train, y_test = split
    model = train_advanced(X_train, y_train, model_type="randomforest")
    score = risk_score(model, X_test.iloc[[0]])
    assert 0.0 <= score <= 100.0
