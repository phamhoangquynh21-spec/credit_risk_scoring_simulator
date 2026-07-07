# Credit Risk Scoring Simulator — Business Report

*Prepared for non-technical stakeholders (Risk Managers).*

## 1. What this tool does
It estimates the probability that a credit-card customer will **miss their next
payment (default)**, expresses it as a **0–100 risk score** with a Low / Medium /
High band, and — crucially — explains **why** each customer received that score.

## 2. Headline results
| Metric | Value | What it means |
|---|---|---|
| AUC-ROC | **0.793** | Ability to rank risky vs. safe customers (target ≥ 0.75 — **met**). |
| Recall (defaulters caught) | 71.3% | Share of true defaulters the model flags. |
| Precision | 44.2% | Of those flagged, the share who truly default. |
| Baseline (simple model) AUC | 0.791 | The advanced model (xgboost) is our production candidate. |

On a test set of **6,000 customers**, the model correctly cleared
**3,280** good payers and caught **1,021** defaulters, while **missing 410**
defaulters (false negatives) and unnecessarily flagging **1,289** good payers.

## 3. Why false negatives matter most
A missed defaulter (false negative) is usually far more expensive than a
wrongly-flagged good customer. The decision threshold should therefore be tuned
to the business cost of each error, not left at the naive 50% cut-off.

## 4. Transparency & fairness
Every score comes with its **top contributing factors** (via SHAP), so a manager
can see, e.g., *"flagged high risk because of recent late payments and high credit
utilisation."* We also ran a **fairness audit** across sex, education and age; the
largest disparity is on age group and is disclosed in the fairness report.

## 5. Limitations (read before trusting any number)
- Built on **synthetic data** mirroring the UCI Taiwan (2005) dataset — **not real
  customers**, and not calibrated to the Australian market.
- No transaction-level, bureau, or macroeconomic data.
- This is a **portfolio demonstration**, not a production lending system.

## 6. Recommendation
The approach is sound and interview-ready: it hits the accuracy target, is fully
explainable, and treats fairness as a first-class concern. Next steps would be to
validate on real, recent, local data and to tune the decision threshold to actual
default-loss economics.
