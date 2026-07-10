import pytest
from pydantic import ValidationError

from services.ml.schemas import Applicant


def _valid() -> dict:
    return {
        "limit_bal": 120000, "sex": 2, "education": 2, "marriage": 1, "age": 35,
        "pay_0": 0, "pay_2": 0, "pay_3": 0, "pay_4": 0, "pay_5": 0, "pay_6": 0,
        "bill_amt1": 5000, "bill_amt2": 4000, "bill_amt3": 3000,
        "bill_amt4": 2000, "bill_amt5": 1000, "bill_amt6": 500,
        "pay_amt1": 2000, "pay_amt2": 2000, "pay_amt3": 1000,
        "pay_amt4": 1000, "pay_amt5": 500, "pay_amt6": 500,
    }


def test_valid_applicant_builds_raw_row():
    a = Applicant(**_valid())
    row = a.to_raw_row()
    assert row["LIMIT_BAL"] == 120000
    assert row["PAY_0"] == 0
    assert row["BILL_AMT6"] == 500
    assert len(row) == 23


def test_rejects_negative_age():
    d = _valid(); d["age"] = -1
    with pytest.raises(ValidationError):
        Applicant(**d)


def test_rejects_bad_sex_code():
    d = _valid(); d["sex"] = 9
    with pytest.raises(ValidationError):
        Applicant(**d)


def test_rejects_extra_field():
    d = _valid(); d["credit_utilization"] = 0.5   # engineered, must not be accepted
    with pytest.raises(ValidationError):
        Applicant(**d)
