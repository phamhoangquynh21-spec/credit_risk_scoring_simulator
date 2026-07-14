"""Tests for auto-generated model cards (Stage 7.2). Offline, monkeypatched."""
from __future__ import annotations

import pytest

from src.ml import model_card

_MV = {
    "id": "mv-1",
    "semver": "1.2.3",
    "algo": "xgboost",
    "stage": "champion",
    "threshold": 0.31,
    "trained_on": "uci-real",
    "approved_by": "gov-1",
    "metrics": {"auc_roc": 0.78, "brier": 0.14, "mlflow_run_id": "run-9"},
    "created_at": "2026-07-13T00:00:00Z",
}
_FAIR = [
    {"attribute": "age_group", "grp": "21-30", "n": 400, "selection_rate": 0.19,
     "recall": 0.61, "precision": 0.52, "disparity_ratio": 0.60},
    {"attribute": "age_group", "grp": "61+", "n": 120, "selection_rate": 0.31,
     "recall": 0.70, "precision": 0.55, "disparity_ratio": 1.0},
]


def test_generate_model_card_contains_identity_metrics_and_fairness(monkeypatch):
    monkeypatch.setattr(model_card, "get_model_version",
                        lambda semver, client=None: _MV if semver == "1.2.3" else None)
    monkeypatch.setattr(model_card, "get_latest_run_results",
                        lambda mv_id, client=None: _FAIR)

    card = model_card.generate_model_card("1.2.3")

    assert "Model Card — 1.2.3" in card
    assert "xgboost" in card and "champion" in card and "0.31" in card
    assert "0.78" in card                      # metric rendered
    assert "run-9" in card                     # mlflow ref rendered
    assert "gov-1" in card                     # governance approver rendered
    assert "age_group" in card and "21-30" in card
    assert "**FAIL**" in card                  # 0.60 < 0.8 flagged
    assert model_card.DECISION_SUPPORT_DISCLAIMER in card


def test_generate_model_card_without_fairness_run(monkeypatch):
    monkeypatch.setattr(model_card, "get_model_version",
                        lambda semver, client=None: _MV)
    monkeypatch.setattr(model_card, "get_latest_run_results",
                        lambda mv_id, client=None: [])
    card = model_card.generate_model_card("1.2.3")
    assert "No fairness run recorded" in card
    assert model_card.DECISION_SUPPORT_DISCLAIMER in card


def test_generate_model_card_unknown_semver_raises(monkeypatch):
    monkeypatch.setattr(model_card, "get_model_version",
                        lambda semver, client=None: None)
    with pytest.raises(ValueError, match="not found"):
        model_card.generate_model_card("9.9.9")


def test_save_model_card_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(model_card, "get_model_version",
                        lambda semver, client=None: _MV)
    monkeypatch.setattr(model_card, "get_latest_run_results",
                        lambda mv_id, client=None: _FAIR)
    out = model_card.save_model_card("1.2.3", path=tmp_path / "card.md")
    assert out.exists()
    assert "Model Card — 1.2.3" in out.read_text(encoding="utf-8")
