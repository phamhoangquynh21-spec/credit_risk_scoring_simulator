# MANIFEST — Credit Risk Scoring Simulator

The committed human record of what this project's data and model actually
are. `scripts/verify.py` checks the repository against this file.

**This file is the reference, not a report.** If `verify.py` reports a
mismatch, the signal is to investigate what changed — a re-ingested CSV, a
retrain, an upgraded library. It is never a licence to edit the numbers
below until the check passes. Editing this file to silence a failure
destroys the only independent record the verifier has.

## Provenance

Source: UCI Machine Learning Repository, *Default of Credit Card Clients*
(dataset 350), <https://archive.ics.uci.edu/dataset/350/>.

`data/raw/credit_card_default.csv` is produced by `scripts/ingest_uci.py`,
which downloads the official zip, reads the `.xls` with `header=1`, keeps
the 25 documented columns and renames the target to its dotted form. The
CSV is committed, so the pipeline's input is fixed and hashable.

## Reproducibility

Every value in the `metrics` block below was reproduced bit-for-bit —
including both AUC-ROC figures, which are floats over 6,000 predicted
probabilities — on 2026-08-04, in the environment recorded under
`environment`. Independent corroboration: `models/metrics.json` was
regenerated on 2026-08-03 and its values are identical to those committed
on 2026-07-10 in b868304; that commit's diff is line-endings only.

Re-check with:

    python3 scripts/verify.py --retrain

The pipeline is deterministic because `split_data` fixes
`random_state=42`, both estimators fix `random_state=42`, and
`GridSearchCV` scores a fixed grid. That determinism is what makes exact
equality — rather than a tolerance — the correct assertion here.

It is *observed* determinism, on one machine and one set of library
versions. It is not a guarantee across versions, which is exactly why
`environment` is recorded and checked separately.

## Environment

`environment` records the versions these numbers were observed under.
`requirements.txt` states floors (`>=`) for installation. The two answer
different questions and are expected to differ; neither is wrong.

A version mismatch exits 2 and means *the environment changed*. A metric
mismatch exits 1 and means *the results changed*. Do not conflate them:
the first calls for a deliberate re-record, the second for investigation.

## The record

```json
{
  "raw_data": {
    "path": "data/raw/credit_card_default.csv",
    "sha256": "f7b7d22d1f8dd27dadb25d4b78d8a4ae7c441ab6cc12d1ea58c0efc54d4d1788",
    "rows": 30000,
    "columns": [
      "ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE",
      "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
      "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5",
      "BILL_AMT6",
      "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5",
      "PAY_AMT6",
      "default.payment.next.month"
    ]
  },
  "derived": {
    "target_positives": 6636,
    "default_rate": 0.2212,
    "n_train": 24000,
    "n_test": 6000,
    "test_positives": 1327,
    "features": [
      "limit_bal", "sex", "education", "marriage", "age",
      "pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6",
      "bill_amt1", "bill_amt2", "bill_amt3", "bill_amt4", "bill_amt5",
      "bill_amt6",
      "pay_amt1", "pay_amt2", "pay_amt3", "pay_amt4", "pay_amt5",
      "pay_amt6",
      "avg_bill_amt", "avg_pay_amt", "credit_utilization",
      "months_delayed_count", "payment_trend"
    ]
  },
  "metrics": {
    "model_type": "xgboost",
    "baseline": {
      "auc_roc": 0.7426649364279171,
      "precision": 0.4694006309148265,
      "recall": 0.560663149962321,
      "f1": 0.510989010989011,
      "accuracy": 0.7626666666666667,
      "confusion_matrix": [[3832, 841], [583, 744]]
    },
    "advanced": {
      "auc_roc": 0.7802116763378456,
      "precision": 0.4529123571039739,
      "recall": 0.6269781461944235,
      "f1": 0.5259165613147914,
      "accuracy": 0.75,
      "confusion_matrix": [[3668, 1005], [495, 832]]
    }
  },
  "environment": {
    "python": "3.14.6",
    "pandas": "3.0.3",
    "numpy": "2.4.6",
    "scikit-learn": "1.9.0",
    "xgboost": "3.3.0",
    "joblib": "1.5.3",
    "scipy": "1.18.0"
  }
}
```

## Notes on individual values

- `default_rate` is exactly `6636 / 30000 = 0.2212`. `verify.py` recounts
  the positives from the CSV rather than trusting the stored float.
- `n_train` / `n_test` follow from `test_size=0.2` over 30,000 rows.
  `test_positives` is 1,327 for both models, consistent with a stratified
  split of 6,636 positives (`6636 × 0.2 = 1327.2`).
- `features` is 28 columns and is *derivable*: the raw header lowercased,
  minus `ID` and the target, plus the five names in `config.ENGINEERED`.
  `verify.py` re-derives it rather than trusting the list, which is what
  catches `src/config.py` drifting away from `models/metrics.json`.
- `confusion_matrix` is `[[TN, FP], [FN, TP]]`, per
  `src/train_model.evaluate_model`.
- `precision`, `recall`, `f1` and `accuracy` are all recomputable from
  the confusion matrix alone, and were confirmed to match the stored
  floats with a delta of exactly 0.0. `auc_roc` is *not* — it needs the
  predicted probabilities, which are never persisted, so only
  `--retrain` can check it.
