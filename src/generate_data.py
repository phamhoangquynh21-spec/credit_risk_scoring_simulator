"""Generate a synthetic dataset that mirrors the UCI 'Default of Credit Card
Clients' structure, written to data/raw/ in the *original* raw format.

Why synthetic: the project is built without downloading the licensed UCI file.
The generator reproduces the real schema (column names, category codes, value
ranges, ~22% default rate, class imbalance) AND embeds a coherent, learnable
signal so a model can genuinely reach AUC >= 0.75 — the relationships are not
random noise.

Design: each customer has an unobserved latent "financial distress" r. Repayment
delays and credit utilisation increase with r; the default outcome is drawn from
a logistic function of r plus mild demographic effects plus noise. Because the
observed features and the outcome share the same latent driver, the features are
genuinely predictive, with the noise term capping AUC at a realistic level.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_raw(n: int = 30_000, seed: int = 42) -> pd.DataFrame:
    """Return a DataFrame in the original UCI raw format (uppercase columns,
    raw category codes including the 'invalid' ones that clean_data fixes)."""
    rng = np.random.default_rng(seed)

    # Latent financial distress, standardised.
    r = rng.normal(0.0, 1.0, n)

    # --- Demographics ------------------------------------------------------
    sex = rng.choice([1, 2], size=n, p=[0.40, 0.60])
    # EDUCATION includes undocumented codes 0, 5, 6 that clean_data folds to 'other'.
    education = rng.choice(
        [1, 2, 3, 4, 5, 6, 0], size=n,
        p=[0.35, 0.47, 0.16, 0.010, 0.006, 0.003, 0.001],
    )
    marriage = rng.choice([1, 2, 3, 0], size=n, p=[0.455, 0.53, 0.01, 0.005])
    age = np.clip(rng.normal(35, 9, n), 21, 79).round().astype(int)

    # Credit limit: lower limits skew toward higher distress.
    limit_base = rng.lognormal(mean=11.6, sigma=0.55, size=n)  # ~NT$ tens/hundreds of thousands
    limit_bal = np.clip(limit_base * (1 - 0.15 * r), 10_000, 1_000_000)
    limit_bal = (limit_bal / 10_000).round() * 10_000  # UCI limits are round numbers

    # --- Repayment status (PAY_*) -----------------------------------------
    # Higher distress => more months delayed. Base state -1 (paid duly) / 0.
    def _pay_status(weight: float) -> np.ndarray:
        latent = weight * r + rng.normal(0, 0.7, n)
        status = np.zeros(n, dtype=int)
        status[latent < -0.3] = -1            # paid duly
        status[(latent >= -0.3) & (latent < 0.8)] = 0  # revolving / minimal
        for k, thr in enumerate([0.8, 1.4, 2.0, 2.6, 3.2, 3.8, 4.4, 5.0], start=1):
            status[latent >= thr] = k
        return np.clip(status, -2, 8)

    # PAY_0 (most recent) carries the strongest weight, older months taper off.
    pay_weights = {"PAY_0": 1.30, "PAY_2": 1.05, "PAY_3": 0.85,
                   "PAY_4": 0.70, "PAY_5": 0.60, "PAY_6": 0.50}
    pay = {col: _pay_status(w) for col, w in pay_weights.items()}

    # --- Bill & payment amounts -------------------------------------------
    # Utilisation rises with distress; bills are a fraction of the limit.
    utilisation = np.clip(0.35 + 0.30 * r + rng.normal(0, 0.15, n), 0.0, 1.6)
    bill_cols, pay_amt_cols = {}, {}
    prev_bill = utilisation * limit_bal
    for i in range(1, 7):
        month_noise = rng.normal(1.0, 0.12, n)
        bill = np.clip(prev_bill * month_noise, 0, None).round(0)
        bill_cols[f"BILL_AMT{i}"] = bill.astype(int)
        # Distressed customers pay a smaller share of their bill.
        pay_share = np.clip(0.55 - 0.28 * r + rng.normal(0, 0.12, n), 0.02, 1.0)
        pay_amt = (bill * pay_share).round(0)
        pay_amt_cols[f"PAY_AMT{i}"] = np.clip(pay_amt, 0, None).astype(int)
        prev_bill = bill

    # --- Default outcome ---------------------------------------------------
    edu_effect = np.select(
        [education == 3, np.isin(education, [4, 5, 6, 0])],
        [0.20, 0.10], default=0.0,
    )
    logit = (
        -1.85                       # intercept -> ~22% base rate
        + 1.55 * r                  # shared latent driver
        + 0.20 * (age < 25)         # very young slightly riskier
        + edu_effect
        + rng.normal(0, 0.85, n)    # irreducible noise -> caps AUC realistically
    )
    default = rng.binomial(1, _sigmoid(logit))

    df = pd.DataFrame({
        "ID": np.arange(1, n + 1),
        "LIMIT_BAL": limit_bal.astype(int),
        "SEX": sex,
        "EDUCATION": education,
        "MARRIAGE": marriage,
        "AGE": age,
        **pay,
        **bill_cols,
        **pay_amt_cols,
        "default.payment.next.month": default,
    })
    return df


def main() -> None:
    config.DATA_RAW.mkdir(parents=True, exist_ok=True)
    df = generate_raw()
    df.to_csv(config.RAW_CSV, index=False)
    rate = df["default.payment.next.month"].mean()
    print(f"Wrote {len(df):,} rows to {config.RAW_CSV}")
    print(f"Default rate: {rate:.1%}  (class imbalance as expected)")


if __name__ == "__main__":
    main()
