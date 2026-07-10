import pandas as pd
import pytest

from scripts.ingest_uci import transform_uci


def _fake_xls_frame():
    # Mimics pd.read_excel(xls, header=1): ID column + 23 features + verbose target
    cols = (["ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
             "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
            + [f"BILL_AMT{i}" for i in range(1, 7)]
            + [f"PAY_AMT{i}" for i in range(1, 7)]
            + ["default payment next month"])
    row = [1, 20000, 2, 2, 1, 24, 2, 2, -1, -1, -2, -2,
           3913, 3102, 689, 0, 0, 0, 0, 689, 0, 0, 0, 0, 1]
    return pd.DataFrame([row], columns=cols)


def test_transform_renames_target_to_dotted_name():
    out = transform_uci(_fake_xls_frame())
    assert "default.payment.next.month" in out.columns
    assert "default payment next month" not in out.columns


def test_transform_keeps_id_and_all_feature_columns():
    out = transform_uci(_fake_xls_frame())
    assert out.shape == (1, 25)  # ID + 23 features + target
    for col in ["ID", "LIMIT_BAL", "PAY_0", "BILL_AMT6", "PAY_AMT1"]:
        assert col in out.columns


def test_transform_rejects_frame_missing_columns():
    bad = _fake_xls_frame().drop(columns=["AGE"])
    with pytest.raises(ValueError, match="AGE"):
        transform_uci(bad)
