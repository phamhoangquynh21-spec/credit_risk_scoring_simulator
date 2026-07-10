from services.ml.scoring import score_one, explain_one


def _risky_raw():
    return {"LIMIT_BAL": 50000, "SEX": 1, "EDUCATION": 3, "MARRIAGE": 2, "AGE": 24,
            "PAY_0": 3, "PAY_2": 2, "PAY_3": 2, "PAY_4": 1, "PAY_5": 0, "PAY_6": 0,
            "BILL_AMT1": 48000, "BILL_AMT2": 47000, "BILL_AMT3": 46000,
            "BILL_AMT4": 45000, "BILL_AMT5": 44000, "BILL_AMT6": 43000,
            "PAY_AMT1": 1000, "PAY_AMT2": 1000, "PAY_AMT3": 1000,
            "PAY_AMT4": 1000, "PAY_AMT5": 1000, "PAY_AMT6": 1000}


def test_score_one_returns_valid_fields():
    out = score_one(_risky_raw())
    assert 0.0 <= out["probability"] <= 1.0
    assert 0.0 <= out["risk_score"] <= 100.0
    assert out["risk_band"] in {"Low", "Medium", "High"}


def test_risky_applicant_scores_high():
    out = score_one(_risky_raw())
    assert out["risk_band"] in {"Medium", "High"}


def test_explain_one_returns_top_factors():
    factors = explain_one(_risky_raw())
    assert 1 <= len(factors) <= 5
    assert {"feature", "friendly", "contribution", "direction"} <= set(factors[0])
