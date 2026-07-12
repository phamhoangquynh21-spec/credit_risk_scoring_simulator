# PRD — Credit Risk Scoring Simulator

**Author:** Adam Pham
**Date:** 30 June 2026
**Status:** Approved for development
**Dataset:** UCI "Default of Credit Card Clients" (Taiwan, 30,000 records)

---

## 1. Vision & Purpose

Build a credit risk scoring tool that predicts the probability of a customer defaulting on their next credit card payment, combined with an interactive dashboard that explains *why* a customer is scored as high or low risk. The project demonstrates the intersection of Finance domain knowledge and Data Science/ML engineering, targeting a portfolio-quality, interview-ready deliverable.

This is a simulation of a real fintech/BNPL risk-assessment workflow, built end-to-end in 3–4 weeks.

## 2. Problem Statement

Lenders need to assess credit default risk quickly and transparently. A purely "black box" prediction is not enough — both technical analysts and non-technical risk managers need to understand and trust the model's output before using it for decisions. There is also a regulatory/ethical obligation to check whether the model is fair across demographic groups.

## 3. Target Users (Personas)

| Persona | Needs |
|---|---|
| **Risk Analyst** (technical) | Wants to input a customer profile and get a risk score; wants to see model performance metrics (AUC, confusion matrix, feature importance) |
| **Risk Manager** (non-technical) | Wants a visual dashboard with plain-language explanations of why a customer is risky; wants segment-level breakdowns |

## 4. Goals & Success Metrics

| Goal | Metric | Target |
|---|---|---|
| Predictive performance | AUC-ROC | ≥ 0.75 |
| Explainability | SHAP-based per-customer explanation available | 100% of predictions |
| Fairness | Fairness audit completed across gender, age, education | Documented, gaps disclosed |
| Usability | Dashboard loads and returns prediction | < 2 seconds |
| Delivery | Public deployed link + GitHub repo + business report | Complete by end of Week 4 |

## 5. Scope

### In Scope (MVP, Weeks 1–2)
- EDA on the UCI dataset (missing values, distributions, target imbalance, correlations)
- Baseline model: Logistic Regression
- Advanced model: Random Forest and/or XGBoost
- Streamlit dashboard: single-customer prediction + risk band (Low/Medium/High)

### In Scope (Extended, Weeks 3–4)
- SHAP global + local explainability
- Fairness audit across protected attributes (sex, age, education)
- Model performance tab (AUC, confusion matrix, precision/recall, feature importance)
- Segment comparison charts
- Unit tests (pytest) for preprocessing and inference pipeline
- Public deployment (Streamlit Community Cloud or Hugging Face Spaces)
- Business report (PDF/slides) summarizing findings for non-technical stakeholders

### Out of Scope (explicitly excluded to prevent scope creep)
- Deep learning / neural networks (not justified for this tabular dataset size)
- Real-time production API with authentication
- Live/streaming data ingestion
- Multi-user login system
- Mobile app version

## 6. User Stories & Acceptance Criteria

| ID | User Story | Acceptance Criteria |
|---|---|---|
| US1 | As a Risk Analyst, I want to input a customer's profile and receive a risk score | System returns a 0–100 risk score and a risk band (Low/Medium/High) in under 2 seconds |
| US2 | As a Risk Manager, I want to see why a customer was scored as high risk | Dashboard shows top 3–5 contributing factors via SHAP, in plain language |
| US3 | As a Risk Analyst, I want to see overall model performance | Dashboard has a "Model Performance" tab with AUC-ROC, confusion matrix, precision/recall |
| US4 | As a Risk Manager, I want to compare risk across customer segments | Dashboard shows risk score distribution by age, sex, education |
| US5 | As any user, I want to understand the model's limitations | Dashboard has a "Limitations & Disclaimer" section, including fairness audit findings |

## 7. Dataset

- **Source:** UCI Machine Learning Repository — "Default of Credit Card Clients Dataset"
- **Size:** 30,000 rows, 24 features + 1 target (`default.payment.next.month`)
- **Key features:** credit limit (LIMIT_BAL), sex, education, marital status, age, repayment status for 6 months (PAY_0–PAY_6), bill statement amounts (BILL_AMT1–6), prior payment amounts (PAY_AMT1–6)
- **License:** Public, free for academic/portfolio use (cite source in README)
- **Known limitation:** Data collected in Taiwan (2005) — demographic and economic context differs from Australia; this must be stated explicitly as a limitation in the final report.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Class imbalance (fewer defaults than non-defaults) | High | Medium | Use class_weight, evaluate via AUC not accuracy |
| Overfitting on Random Forest/XGBoost | Medium | High | Cross-validation, regularization, train/test gap monitoring |
| Scope creep | High | High | Strict adherence to MVP scope above; new ideas go to "Future Work" |
| Timeline slippage | Medium | Medium | Weekly milestone review (see Technical Spec timeline) |
| Inconsistent AI-generated code across sessions | Medium | Medium | Always reference Technical_Spec.md when starting a new Claude Code session |

## 9. Definition of Done

- [ ] All 5 user stories meet acceptance criteria
- [ ] AUC-ROC ≥ 0.75 on held-out test set
- [ ] Fairness audit completed and documented
- [ ] Dashboard deployed publicly with working link
- [ ] README.md complete (goals, setup, results, limitations, future work)
- [ ] pytest suite passes
- [ ] Business report (non-technical) produced

## 10. Future Work (explicitly out of scope now)

- Incorporate transaction-level behavioral data if available
- Automated fairness mitigation (not just detection)
- Real-time API for production use
- Extend to BNPL-specific dataset for closer alignment with fintech use case
