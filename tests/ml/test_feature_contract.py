"""Tests for the 28-feature contract (Stage 3.2)."""
from __future__ import annotations

import pandas as pd
import pytest

from src.ml import feature_contract as fc
from src.ml.feature_contract import FeatureContractError


def _valid_row() -> dict:
    """A single contract-valid feature dict covering all 28 features."""
    row = {
        "limit_bal": 120000.0,
        "sex": 2, "education": 1, "marriage": 2, "age": 35,
        "avg_bill_amt": 30000.0, "avg_pay_amt": 4000.0,
        "credit_utilization": 0.25, "months_delayed_count": 1,
        "payment_trend": 500.0,
    }
    row.update({c: 0 for c in fc.config.PAY_COLS})
    row.update({c: 30000.0 for c in fc.config.BILL_COLS})
    row.update({c: 4000.0 for c in fc.config.PAY_AMT_COLS})
    return row


def test_contract_covers_28_features():
    assert len(fc.FEATURE_CONTRACT) == 28
    assert len(fc.FEATURE_NAMES) == len(set(fc.FEATURE_NAMES)) == 28


def test_valid_frame_and_row_pass():
    fc.validate_row(_valid_row())
    fc.validate_frame(pd.DataFrame([_valid_row()]))


def test_missing_feature_raises_naming_it():
    row = _valid_row()
    del row["credit_utilization"]
    with pytest.raises(FeatureContractError, match="credit_utilization: missing"):
        fc.validate_row(row)

    frame = pd.DataFrame([_valid_row()]).drop(columns=["age"])
    with pytest.raises(FeatureContractError, match="age: missing"):
        fc.validate_frame(frame)


def test_wrong_dtype_raises():
    frame = pd.DataFrame([_valid_row()])
    frame["limit_bal"] = "not-a-number"
    with pytest.raises(FeatureContractError, match="limit_bal: not numeric"):
        fc.validate_frame(frame)

    row = _valid_row()
    row["age"] = "thirty"
    with pytest.raises(FeatureContractError, match="age: not a number"):
        fc.validate_row(row)


def test_out_of_range_raises():
    row = _valid_row()
    row["age"] = 5  # below 18
    with pytest.raises(FeatureContractError, match=r"age: 5 not in \[18, 100\]"):
        fc.validate_row(row)

    frame = pd.DataFrame([_valid_row()])
    frame.loc[0, "pay_0"] = 99  # above max 8
    with pytest.raises(FeatureContractError, match="pay_0: out of range"):
        fc.validate_frame(frame)


def test_bad_category_raises():
    row = _valid_row()
    row["sex"] = 7  # only {1, 2} allowed
    with pytest.raises(FeatureContractError, match="sex: 7 not one of"):
        fc.validate_row(row)

    frame = pd.DataFrame([_valid_row()])
    frame.loc[0, "education"] = 9  # only {1,2,3,4}
    with pytest.raises(FeatureContractError, match="education: values"):
        fc.validate_frame(frame)


def test_boolean_is_not_accepted_as_number():
    row = _valid_row()
    row["marriage"] = True  # bool must not pass as an int category
    with pytest.raises(FeatureContractError, match="marriage: not a number"):
        fc.validate_row(row)


def test_boolean_column_rejected_by_validate_frame():
    # bool is numeric to pandas but invalid; validate_frame must agree with
    # validate_row and reject it.
    frame = pd.DataFrame([_valid_row()])
    frame["months_delayed_count"] = pd.Series([True], dtype=bool)
    with pytest.raises(FeatureContractError, match="months_delayed_count: not numeric"):
        fc.validate_frame(frame)


def test_overpayer_negative_utilization_passes():
    # A legitimate overpayer has a negative average bill, hence negative
    # utilisation (avg_bill_amt / limit_bal). Must NOT be falsely rejected.
    row = _valid_row()
    row["avg_bill_amt"] = -8000.0
    row["credit_utilization"] = -8000.0 / 50000.0  # ~= -0.16
    row["limit_bal"] = 50000.0
    row.update({c: -8000.0 for c in fc.config.BILL_COLS})
    fc.validate_row(row)
    fc.validate_frame(pd.DataFrame([row]))
