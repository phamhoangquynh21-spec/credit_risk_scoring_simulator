# Technical Spec — Credit Risk Scoring Simulator

**Companion document to PRD.md** — read both before starting any Claude Code session.

---

## 1. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Data handling | pandas, numpy | |
| ML | scikit-learn (LogisticRegression, RandomForestClassifier), xgboost | |
| Explainability | shap | Required for US2 |
| Visualization | plotly, matplotlib, seaborn | Plotly for interactive dashboard charts |
| Dashboard | streamlit | |
| Testing | pytest | |
| Environment | venv + requirements.txt | |
| Version control | Git + GitHub | |
| AI coding agent | Claude Code | |

## 2. Repository Structure

```
credit-risk-simulator/
├── data/
│   ├── raw/                      # original UCI CSV, untouched
│   └── processed/                # cleaned, feature-engineered data
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_modeling.ipynb
│   └── 03_fairness_audit.ipynb
├── src/
│   ├── __init__.py
│   ├── preprocessing.py          # load_data(), clean_data(), engineer_features()
│   ├── train_model.py            # train_baseline(), train_advanced(), save_model()
│   ├── explain.py                # get_shap_values(), explain_single_customer()
│   ├── fairness.py               # run_fairness_audit()
│   └── dashboard.py              # Streamlit app entrypoint
├── tests/
│   ├── test_preprocessing.py
│   └── test_model_pipeline.py
├── models/
│   └── model.pkl                 # serialized trained model (gitignored if large)
├── reports/
│   ├── business_report.pdf
│   └── fairness_audit_report.md
├── README.md
├── requirements.txt
└── .gitignore
```

## 3. Data Schema (Data Dictionary)

| Column | Type | Description |
|---|---|---|
| LIMIT_BAL | float | Credit limit (NT dollar) |
| SEX | int | 1 = male, 2 = female |
| EDUCATION | int | 1 = graduate school, 2 = university, 3 = high school, 4 = other |
| MARRIAGE | int | 1 = married, 2 = single, 3 = other |
| AGE | int | Age in years |
| PAY_0 ... PAY_6 | int | Repayment status, past 6 months (-1 = paid duly, 1-9 = months delayed) |
| BILL_AMT1 ... BILL_AMT6 | float | Bill statement amount, past 6 months |
| PAY_AMT1 ... PAY_AMT6 | float | Prior payment amount, past 6 months |
| default.payment.next.month | int (target) | 0 = no default, 1 = default |

**Engineered features (to be created in `engineer_features()`):**
- `avg_bill_amt`: mean of BILL_AMT1–6
- `avg_pay_amt`: mean of PAY_AMT1–6
- `credit_utilization`: avg_bill_amt / LIMIT_BAL
- `months_delayed_count`: count of PAY_0–6 > 0
- `payment_trend`: trend in PAY_AMT over 6 months (increasing/decreasing)

## 4. Function-Level Spec (`src/preprocessing.py`)

```python
def load_data(path: str) -> pd.DataFrame:
    """Load raw CSV from data/raw/. Returns raw DataFrame."""

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values, fix invalid category codes (e.g. EDUCATION=0,5,6 -> 'other'),
    rename columns to snake_case. Returns cleaned DataFrame."""

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered features listed in section 3. Returns DataFrame ready for modeling."""

def split_data(df: pd.DataFrame, target_col: str, test_size: float = 0.2, random_state: int = 42):
    """Stratified train/test split (stratify on target due to class imbalance).
    Returns X_train, X_test, y_train, y_test."""
```

## 5. Function-Level Spec (`src/train_model.py`)

```python
def train_baseline(X_train, y_train) -> sklearn.linear_model.LogisticRegression:
    """Train Logistic Regression with class_weight='balanced'. Returns fitted model."""

def train_advanced(X_train, y_train, model_type: str = "xgboost") -> object:
    """Train RandomForest or XGBoost with cross-validation for hyperparameter selection.
    Returns fitted model."""

def evaluate_model(model, X_test, y_test) -> dict:
    """Return dict with auc_roc, precision, recall, f1, confusion_matrix."""

def save_model(model, path: str) -> None:
    """Serialize model to models/model.pkl using joblib."""
```

## 6. Function-Level Spec (`src/explain.py`)

```python
def get_shap_values(model, X) -> shap.Explanation:
    """Compute SHAP values for the given model and feature set."""

def explain_single_customer(model, customer_row: pd.Series) -> list[tuple[str, float]]:
    """Return top 5 features driving this customer's prediction, as
    (feature_name, contribution) pairs, sorted by absolute impact."""
```

## 7. Function-Level Spec (`src/fairness.py`)

```python
def run_fairness_audit(model, X_test, y_test, protected_attrs: list[str]) -> pd.DataFrame:
    """For each protected attribute (sex, age_group, education), compute
    predicted positive rate and recall by group. Returns comparison table
    for inclusion in fairness_audit_report.md."""
```

## 8. Dashboard Spec (`src/dashboard.py`)

**Tabs:**
1. **Single Customer Prediction** — input form (credit limit, age, sex, education, marriage, repayment history) → risk score (0–100), risk band, SHAP explanation chart (US1, US2)
2. **Model Performance** — AUC-ROC curve, confusion matrix, precision/recall, global feature importance (US3)
3. **Segment Analysis** — risk score distribution by age group, sex, education (US4)
4. **Limitations & Disclaimer** — model limitations, dataset context (Taiwan 2005), fairness audit summary (US5)

**Performance requirement:** use `@st.cache_data` for data loading and `@st.cache_resource` for model loading to meet the <2 second response requirement.

## 9. Testing Plan

| Test file | Covers |
|---|---|
| `test_preprocessing.py` | `clean_data()` handles invalid category codes; `engineer_features()` produces expected columns and no NaNs |
| `test_model_pipeline.py` | End-to-end: load → clean → engineer → split → train → predict produces valid probability output (0–1 range) |

Run with: `pytest tests/ -v`

## 10. Deployment Plan

1. Push repository to GitHub (public, with README, no raw PII — UCI dataset is already anonymized).
2. Add `requirements.txt` with pinned versions.
3. Deploy `src/dashboard.py` via Streamlit Community Cloud, linking to GitHub repo.
4. Verify public link loads within 2 seconds and all 4 tabs function correctly.
5. Add deployed link to README.md and resume/portfolio.

## 11. Weekly Task Breakdown (for Claude Code sessions)

| Week | Session focus | Reference |
|---|---|---|
| 1 | `preprocessing.py` + `01_eda.ipynb` | Section 3, 4 |
| 2 | `train_model.py` + baseline/advanced models | Section 5 |
| 3 | `explain.py`, `fairness.py`, `dashboard.py` (tabs 1–3) | Section 6, 7, 8 |
| 4 | `dashboard.py` (tab 4), tests, deployment, README, business report | Section 8, 9, 10 |

**Rule for Claude Code sessions:** start each session by pasting only the relevant function-level spec section above — not the entire document — to keep context focused and outputs consistent.

## 12. requirements.txt (initial draft)

```
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
xgboost>=2.0
shap>=0.44
streamlit>=1.30
plotly>=5.18
matplotlib>=3.8
seaborn>=0.13
pytest>=7.4
joblib>=1.3
```
