"""Central configuration: paths, column definitions, and risk-band thresholds.

Keeping every column name and path in one place means preprocessing, training,
explainability, fairness and the dashboard all speak the same vocabulary.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_CSV = DATA_RAW / "credit_card_default.csv"
PROCESSED_CSV = DATA_PROCESSED / "credit_card_default_processed.csv"
MODEL_PATH = MODELS_DIR / "model.pkl"
METRICS_PATH = MODELS_DIR / "metrics.json"

# ---------------------------------------------------------------------------
# Column groups (in cleaned / snake_case form)
# ---------------------------------------------------------------------------
TARGET = "default_payment_next_month"

# Repayment status columns (UCI convention skips PAY_1).
PAY_COLS = ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"]
BILL_COLS = [f"bill_amt{i}" for i in range(1, 7)]
PAY_AMT_COLS = [f"pay_amt{i}" for i in range(1, 7)]
CATEGORICAL = ["sex", "education", "marriage"]

ENGINEERED = [
    "avg_bill_amt",
    "avg_pay_amt",
    "credit_utilization",
    "months_delayed_count",
    "payment_trend",
]

# Human-readable labels for categorical codes (used in the dashboard & fairness).
SEX_LABELS = {1: "Male", 2: "Female"}
EDUCATION_LABELS = {1: "Graduate school", 2: "University", 3: "High school", 4: "Other"}
MARRIAGE_LABELS = {1: "Married", 2: "Single", 3: "Other"}

# ---------------------------------------------------------------------------
# Risk bands: map a 0-100 score to a plain-language band (US1).
# ---------------------------------------------------------------------------
RISK_BANDS = [
    ("Low", 0, 33),
    ("Medium", 33, 66),
    ("High", 66, 100),
]


def risk_band(score_0_100: float) -> str:
    """Return the risk band label for a 0-100 risk score."""
    for label, low, high in RISK_BANDS:
        if low <= score_0_100 < high:
            return label
    return "High"  # score == 100 falls here


def feature_columns(df) -> list[str]:
    """Return the ordered list of model feature columns present in ``df``.

    Everything except the target and the (optional) id column.
    """
    drop = {TARGET, "id"}
    return [c for c in df.columns if c not in drop]
