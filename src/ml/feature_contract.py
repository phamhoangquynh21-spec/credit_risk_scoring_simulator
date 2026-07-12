"""Explicit feature contract for the 28 model features (Stage 3.2).

A single source of truth for what each feature must look like: dtype and either
a numeric [min, max] range or a set of allowed categorical values. Names are
derived from ``src.config`` groups (never hardcoded twice). ``validate_frame``
is for train-time checks; ``validate_row`` is for per-predict checks and raises
a message clear enough to surface as a 422.

Bounds are deliberately generous where real data is legitimately wide (bill
amounts can be negative credit balances; utilisation can briefly exceed 1) so
the contract rejects corruption, not valid edge cases.
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import config

# Realistic outer bounds for monetary NT$ amounts in the UCI dataset.
_AMOUNT_MAX = 2_000_000.0


class FeatureContractError(ValueError):
    """Raised when a frame/row violates the feature contract."""


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    dtype: str  # "int" or "float" (both validated as numeric)
    min: float | None = None
    max: float | None = None
    allowed_values: tuple | None = None

    def describe(self) -> str:
        if self.allowed_values is not None:
            return f"one of {sorted(self.allowed_values)}"
        return f"in [{self.min}, {self.max}]"


def _build_contract() -> list[FeatureSpec]:
    specs: list[FeatureSpec] = [
        FeatureSpec("limit_bal", "float", min=0.0, max=_AMOUNT_MAX),
        FeatureSpec("sex", "int", allowed_values=tuple(config.SEX_LABELS)),
        FeatureSpec("education", "int", allowed_values=tuple(config.EDUCATION_LABELS)),
        FeatureSpec("marriage", "int", allowed_values=tuple(config.MARRIAGE_LABELS)),
        FeatureSpec("age", "int", min=18, max=100),
    ]
    # Repayment status codes: -2 (no consumption) .. 8 (8+ months delayed).
    specs += [FeatureSpec(c, "int", min=-2, max=8) for c in config.PAY_COLS]
    # Bill amounts can be negative (credit balance / overpayment).
    specs += [FeatureSpec(c, "float", min=-_AMOUNT_MAX, max=_AMOUNT_MAX)
              for c in config.BILL_COLS]
    # Payments are non-negative.
    specs += [FeatureSpec(c, "float", min=0.0, max=_AMOUNT_MAX)
              for c in config.PAY_AMT_COLS]
    # Engineered features.
    specs += [
        FeatureSpec("avg_bill_amt", "float", min=-_AMOUNT_MAX, max=_AMOUNT_MAX),
        FeatureSpec("avg_pay_amt", "float", min=0.0, max=_AMOUNT_MAX),
        FeatureSpec("credit_utilization", "float", min=0.0, max=10.0),
        FeatureSpec("months_delayed_count", "int", min=0, max=len(config.PAY_COLS)),
        FeatureSpec("payment_trend", "float", min=-_AMOUNT_MAX, max=_AMOUNT_MAX),
    ]
    return specs


FEATURE_CONTRACT: list[FeatureSpec] = _build_contract()
FEATURE_NAMES: list[str] = [s.name for s in FEATURE_CONTRACT]
_BY_NAME: dict[str, FeatureSpec] = {s.name: s for s in FEATURE_CONTRACT}


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_frame(df) -> None:
    """Validate a modelling DataFrame against the contract (train-time).

    Raises FeatureContractError listing every offending column and why.
    """
    import pandas as pd

    problems: list[str] = []

    for name in FEATURE_NAMES:
        if name not in df.columns:
            problems.append(f"{name}: missing")

    for spec in FEATURE_CONTRACT:
        if spec.name not in df.columns:
            continue
        col = df[spec.name]
        if not pd.api.types.is_numeric_dtype(col):
            problems.append(f"{spec.name}: not numeric (dtype {col.dtype})")
            continue
        if col.isna().any():
            problems.append(f"{spec.name}: contains NaN/null")
            continue
        if spec.allowed_values is not None:
            bad = set(col.unique()) - set(spec.allowed_values)
            if bad:
                problems.append(
                    f"{spec.name}: values {sorted(bad)} not {spec.describe()}")
        else:
            if (col < spec.min).any() or (col > spec.max).any():
                problems.append(f"{spec.name}: out of range, expected {spec.describe()}")

    if problems:
        raise FeatureContractError(
            "Feature contract violated: " + "; ".join(problems))


def validate_row(d: dict) -> None:
    """Validate a single feature dict (per-predict).

    Raises FeatureContractError with a message clear enough for a 422 response.
    """
    problems: list[str] = []

    for spec in FEATURE_CONTRACT:
        if spec.name not in d:
            problems.append(f"{spec.name}: missing")
            continue
        v = d[spec.name]
        if v is None or not _is_number(v):
            problems.append(f"{spec.name}: not a number (got {v!r})")
            continue
        if spec.allowed_values is not None:
            if v not in spec.allowed_values:
                problems.append(f"{spec.name}: {v} not {spec.describe()}")
        elif v < spec.min or v > spec.max:
            problems.append(f"{spec.name}: {v} not {spec.describe()}")

    if problems:
        raise FeatureContractError(
            "Feature contract violated: " + "; ".join(problems))
