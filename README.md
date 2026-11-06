# Credit Risk Scoring Simulator

Predict the probability that a credit-card customer defaults on their next
payment — and explain *why*. A Finance × Data Science portfolio project with an
interactive Streamlit dashboard.

**Author:** Adam Pham · **Decision-support only** — this scores public research
data, never real lending decisions.

**Live app:** https://creditriskscoringsimulator-dzqtmjsoouv4ud4pk5siae.streamlit.app

## What it does

Given a customer's credit profile (limit, demographics, and six months of
repayment / bill / payment history), the dashboard returns:

- a **0–100 risk score** and a Low / Medium / High band;
- a **default probability** from the trained model;
- a **SHAP explanation** in plain language — *feature contributions, not proof
  of causation*;
- a **fairness read** across protected attributes (four-fifths / 0.8 rule).

Dashboard tabs: **Single Customer Prediction**, **Model Performance**,
**Segment Analysis**, **Batch Scoring (CSV upload)**, **Limitations & Disclaimer**.

## The data

Trained on the real **UCI *Default of Credit Card Clients*** dataset (Taiwan,
2005 — 30,000 records; public, cited), reaching **AUC ≈ 0.78** on the held-out
test set. The raw CSV is committed at `data/raw/credit_card_default.csv`
(re-download with `scripts/ingest_uci.py`). A structurally-identical
**synthetic generator** (`src/generate_data.py`) mirrors the UCI schema for tests.

## Repository layout

```
├── src/
│   ├── dashboard.py         # Streamlit app
│   ├── config.py            # paths, columns, risk bands
│   ├── generate_data.py     # synthetic UCI-shaped data
│   ├── preprocessing.py     # cleaning + feature engineering
│   ├── train_model.py       # Logistic Regression baseline + XGBoost/RandomForest
│   ├── explain.py           # SHAP explanations, risk score, batch scoring
│   ├── fairness.py          # fairness audit
│   └── generate_reports.py  # figures + business / fairness reports
├── data/raw/                # UCI dataset
├── models/                  # trained model.pkl + metrics.json
├── notebooks/               # EDA, modeling, fairness audit
├── reports/                 # business report, fairness audit, figures
├── scripts/ingest_uci.py    # download the UCI dataset
├── docs/                    # PRD, technical spec, project guide
└── tests/                   # pytest suite
```

## Running locally

```bash
py -m venv .venv                                   # Python 3.11+
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m streamlit run src/dashboard.py
.venv/Scripts/python.exe -m pytest                 # test suite
.venv/Scripts/python.exe -m src.train_model        # retrain (optional)
```

## Documentation

| Doc | What it is |
|---|---|
| [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) | Deep explainer of the project, per module |
| [`docs/PRD.md`](docs/PRD.md) | Product requirements |
| [`docs/Technical_Spec.md`](docs/Technical_Spec.md) | Technical specification |

## Honest limitations

- Scores **public research data** — not real customers, never a real lending
  decision.
- Fairness is measured and disclosed, not automatically mitigated.
- SHAP shows contribution, not causation — stated everywhere it appears.
