"""Streamlit dashboard — the interactive front end. Technical_Spec.md section 8.

Four tabs:
  1. Single Customer Prediction  (US1, US2)
  2. Model Performance           (US3)
  3. Segment Analysis            (US4)
  4. Limitations & Disclaimer    (US5)

Run with:  streamlit run src/dashboard.py
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import roc_curve

# Support both `streamlit run src/dashboard.py` and `python -m src.dashboard`.
try:
    from . import config, fairness
    from .explain import explain_in_plain_language, risk_score
    from .preprocessing import split_data
except ImportError:  # pragma: no cover - executed only under `streamlit run`
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src import config, fairness
    from src.explain import explain_in_plain_language, risk_score
    from src.preprocessing import split_data


st.set_page_config(page_title="Credit Risk Scoring Simulator", page_icon="💳", layout="wide")

BAND_COLOR = {"Low": "#2ca02c", "Medium": "#ff7f0e", "High": "#d62728"}


# ---------------------------------------------------------------------------
# Cached loaders (Technical_Spec.md section 8: cache to meet <2s response)
# ---------------------------------------------------------------------------
@st.cache_resource
def load_bundle():
    return joblib.load(config.MODEL_PATH)


@st.cache_data
def load_metrics():
    with open(config.METRICS_PATH) as fh:
        return json.load(fh)


@st.cache_data
def load_processed():
    return pd.read_csv(config.PROCESSED_CSV)


@st.cache_data
def get_test_split():
    df = load_processed()
    X_train, X_test, y_train, y_test = split_data(df)
    return X_test, y_test


def build_customer_row(inp: dict, feature_cols: list[str]) -> pd.DataFrame:
    """Turn form inputs into a single engineered feature row (same logic as
    preprocessing.engineer_features)."""
    row = {
        "limit_bal": inp["limit_bal"],
        "sex": inp["sex"],
        "education": inp["education"],
        "marriage": inp["marriage"],
        "age": inp["age"],
    }
    for col in config.PAY_COLS:
        row[col] = inp[col]
    for col in config.BILL_COLS:
        row[col] = inp["avg_bill"]
    for col in config.PAY_AMT_COLS:
        row[col] = inp["avg_pay"]

    row["avg_bill_amt"] = float(inp["avg_bill"])
    row["avg_pay_amt"] = float(inp["avg_pay"])
    row["credit_utilization"] = (
        inp["avg_bill"] / inp["limit_bal"] if inp["limit_bal"] else 0.0
    )
    row["months_delayed_count"] = sum(1 for c in config.PAY_COLS if inp[c] > 0)
    row["payment_trend"] = 0.0  # constant monthly payments in this simplified form

    return pd.DataFrame([row])[feature_cols]


# ---------------------------------------------------------------------------
# Tab 1 — Single Customer Prediction
# ---------------------------------------------------------------------------
def tab_prediction(bundle):
    model = bundle["model"]
    feature_cols = bundle["features"]

    st.header("Single Customer Prediction")
    st.caption("Enter a customer profile to get a default-risk score and the "
               "factors driving it.")

    with st.form("customer_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            limit_bal = st.number_input("Credit limit (NT$)", 10_000, 1_000_000,
                                        150_000, step=10_000)
            age = st.number_input("Age", 21, 79, 35)
            sex = st.selectbox("Sex", options=[1, 2],
                               format_func=lambda v: config.SEX_LABELS[v])
        with c2:
            education = st.selectbox("Education", options=[1, 2, 3, 4],
                                     format_func=lambda v: config.EDUCATION_LABELS[v])
            marriage = st.selectbox("Marital status", options=[1, 2, 3],
                                    format_func=lambda v: config.MARRIAGE_LABELS[v])
            avg_bill = st.number_input("Average monthly bill (NT$)", 0, 1_000_000,
                                       50_000, step=5_000)
        with c3:
            avg_pay = st.number_input("Average monthly payment (NT$)", 0, 1_000_000,
                                      25_000, step=5_000)
            st.markdown("**Repayment status** (−1 = paid duly, 0 = revolving, "
                        "1–8 = months late)")

        st.markdown("**Repayment history (last 6 months)**")
        pcols = st.columns(6)
        pay_vals = {}
        labels = ["Most recent", "2 mo", "3 mo", "4 mo", "5 mo", "6 mo"]
        for col, pc, lab in zip(config.PAY_COLS, pcols, labels):
            pay_vals[col] = pc.number_input(lab, -2, 8, 0, key=f"in_{col}")

        submitted = st.form_submit_button("Score customer", type="primary")

    if not submitted:
        return

    inp = {"limit_bal": limit_bal, "sex": sex, "education": education,
           "marriage": marriage, "age": age, "avg_bill": avg_bill,
           "avg_pay": avg_pay, **pay_vals}
    X_row = build_customer_row(inp, feature_cols)

    score = risk_score(model, X_row)
    band = config.risk_band(score)

    m1, m2 = st.columns([1, 2])
    with m1:
        st.metric("Risk score (0–100)", f"{score:.1f}")
        st.markdown(
            f"<h3 style='color:{BAND_COLOR[band]}'>Risk band: {band}</h3>",
            unsafe_allow_html=True,
        )
    with m2:
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": BAND_COLOR[band]},
                   "steps": [{"range": [0, 33], "color": "#e6f4ea"},
                             {"range": [33, 66], "color": "#fef0e3"},
                             {"range": [66, 100], "color": "#fde8e8"}]},
        ))
        gauge.update_layout(height=220, margin=dict(t=20, b=10))
        st.plotly_chart(gauge, use_container_width=True)

    st.subheader("Why this score? (top contributing factors)")
    explanations = explain_in_plain_language(model, X_row.iloc[0])
    exp_df = pd.DataFrame(explanations)
    fig = px.bar(
        exp_df.iloc[::-1], x="contribution", y="friendly", orientation="h",
        color="contribution", color_continuous_scale="RdBu_r",
        labels={"contribution": "SHAP impact on risk", "friendly": ""},
    )
    fig.update_layout(height=300, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
    for e in explanations:
        st.write(f"- {e['sentence']}")


# ---------------------------------------------------------------------------
# Tab 2 — Model Performance
# ---------------------------------------------------------------------------
def tab_performance(bundle, metrics):
    st.header("Model Performance")
    adv = metrics["advanced"]
    base = metrics["baseline"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("AUC-ROC", f"{adv['auc_roc']:.3f}",
              help="Target ≥ 0.75 (PRD success metric)")
    c2.metric("Precision", f"{adv['precision']:.3f}")
    c3.metric("Recall", f"{adv['recall']:.3f}")
    c4.metric("F1", f"{adv['f1']:.3f}")
    st.caption(f"Advanced model: **{metrics['model_type']}**  ·  "
               f"Baseline (Logistic Regression) AUC: {base['auc_roc']:.3f}")

    model = bundle["model"]
    X_test, y_test = get_test_split()
    proba = model.predict_proba(X_test)[:, 1]

    left, right = st.columns(2)
    with left:
        st.subheader("ROC curve")
        fpr, tpr, _ = roc_curve(y_test, proba)
        roc = go.Figure()
        roc.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines",
                                 name=f"AUC = {adv['auc_roc']:.3f}"))
        roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                                 line=dict(dash="dash", color="gray"),
                                 name="Random"))
        roc.update_layout(xaxis_title="False positive rate",
                          yaxis_title="True positive rate", height=380)
        st.plotly_chart(roc, use_container_width=True)

    with right:
        st.subheader("Confusion matrix")
        cm = np.array(adv["confusion_matrix"])
        cm_fig = px.imshow(
            cm, text_auto=True, color_continuous_scale="Blues",
            labels=dict(x="Predicted", y="Actual", color="Count"),
            x=["No default", "Default"], y=["No default", "Default"],
        )
        cm_fig.update_layout(height=380, coloraxis_showscale=False)
        st.plotly_chart(cm_fig, use_container_width=True)
        tn, fp, fn, tp = cm.ravel()
        st.caption(f"False negatives (missed defaulters): **{fn}** — the costliest "
                   f"error type for a lender.")

    st.subheader("Global feature importance")
    if hasattr(model, "feature_importances_"):
        imp = pd.DataFrame({
            "feature": bundle["features"],
            "importance": model.feature_importances_,
        }).sort_values("importance", ascending=True).tail(15)
        imp_fig = px.bar(imp, x="importance", y="feature", orientation="h")
        imp_fig.update_layout(height=450)
        st.plotly_chart(imp_fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 3 — Segment Analysis
# ---------------------------------------------------------------------------
def tab_segments(bundle):
    st.header("Segment Analysis")
    st.caption("How predicted risk varies across customer segments.")

    model = bundle["model"]
    df = load_processed().copy()
    df["risk_score"] = model.predict_proba(df[bundle["features"]])[:, 1] * 100
    df["age_group"] = pd.cut(df["age"], bins=fairness.AGE_BINS,
                             labels=fairness.AGE_LABELS)
    df["sex_label"] = df["sex"].map(config.SEX_LABELS)
    df["education_label"] = df["education"].map(config.EDUCATION_LABELS)

    seg = st.radio("Segment by", ["Sex", "Education", "Age group"], horizontal=True)
    col = {"Sex": "sex_label", "Education": "education_label",
           "Age group": "age_group"}[seg]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"Risk score distribution by {seg.lower()}")
        box = px.box(df, x=col, y="risk_score", color=col)
        box.update_layout(height=420, showlegend=False)
        st.plotly_chart(box, use_container_width=True)
    with c2:
        st.subheader(f"Average risk score by {seg.lower()}")
        avg = df.groupby(col, observed=True)["risk_score"].mean().reset_index()
        bar = px.bar(avg, x=col, y="risk_score", color=col)
        bar.update_layout(height=420, showlegend=False)
        st.plotly_chart(bar, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 4 — Limitations & Disclaimer
# ---------------------------------------------------------------------------
def tab_limitations(bundle):
    st.header("Limitations & Disclaimer")

    st.warning(
        "**This is a portfolio simulation, not a production credit decision "
        "system.** It must not be used to make real lending decisions.")

    st.markdown(
        """
### Dataset context
- Built on a **synthetic dataset that mirrors the structure** of the UCI
  *Default of Credit Card Clients* dataset (Taiwan, 2005). The synthetic data
  reproduces the schema and realistic relationships but is **not real customer
  data**.
- The original UCI context (Taiwan, 2005) differs from the Australian market;
  economic and demographic conditions are not directly transferable.

### Modelling limitations
- Trained on tabular application/repayment features only — no transaction-level
  behaviour, macroeconomic signals, or bureau data.
- Class imbalance (~22% default): evaluated primarily via **AUC-ROC** rather than
  accuracy, which would be misleading.
- A **false negative** (predicting safe when the customer defaults) is far more
  costly to a lender than a false positive; the operating threshold should be
  tuned to business cost, not left at 0.5.

### Fairness audit summary (US5)
        """
    )

    X_test, y_test = get_test_split()
    audit = fairness.run_fairness_audit(bundle["model"], X_test, y_test)
    st.dataframe(audit, use_container_width=True)

    st.markdown("**Disparity summary** (ratio of min/max across groups — "
                "1.0 = perfectly equal):")
    st.dataframe(fairness.disparity_summary(audit), use_container_width=True)
    st.caption(
        "Any protected-attribute group showing a materially different selection "
        "or recall rate is disclosed here rather than silently accepted. In a real "
        "deployment this would trigger a bias-mitigation review before go-live.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.title("💳 Credit Risk Scoring Simulator")
    st.caption("Predict the probability of next-month credit card default — and "
               "explain *why*. A Finance × Data Science portfolio project.")

    if not config.MODEL_PATH.exists():
        # Self-bootstrap so the app works on a fresh deploy (e.g. Streamlit Cloud)
        # without a committed model artifact.
        with st.spinner("First run: generating data and training the model "
                        "(this takes a minute)…"):
            try:
                from .train_model import run_training
            except ImportError:
                from src.train_model import run_training
            run_training()
        st.success("Model trained. Loading dashboard…")

    bundle = load_bundle()
    metrics = load_metrics()

    t1, t2, t3, t4 = st.tabs([
        "Single Customer Prediction", "Model Performance",
        "Segment Analysis", "Limitations & Disclaimer",
    ])
    with t1:
        tab_prediction(bundle)
    with t2:
        tab_performance(bundle, metrics)
    with t3:
        tab_segments(bundle)
    with t4:
        tab_limitations(bundle)


if __name__ == "__main__":
    main()
