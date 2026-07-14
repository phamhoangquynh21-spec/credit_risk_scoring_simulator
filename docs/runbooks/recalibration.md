# Runbook — Recalibrating the model on new portfolio data

**When to run this:** whenever a new, more representative dataset becomes
available — a real local (e.g. Australian) lending portfolio, a fresh vintage of
the UCI/HMDA data, or bureau/open-banking data once its external gate clears
(see [`docs/data_sources.md`](../data_sources.md)). Recalibration is how the
platform's L2 limitation ("not calibrated to any live portfolio") is removed once
the data exists — it is a documented procedure, not new code.

**Who runs it:** an ML engineer performs steps 1–5; a **governance** role must
perform step 6 (promotion is gated on approval).

**Invariant:** the current champion keeps serving untouched until step 6. Nothing
here overwrites `models/model.pkl` or the live champion before governance signs off.

---

## Procedure

### 1. Ingest the new data through a `DataSource`
Use the connector for the source rather than ad-hoc loading, so schema validation
and provenance are consistent:

- Real UCI / any raw-UCI CSV → `src.data.sources.CsvSource(path)`
- A gated source (bureau, open banking, Freddie Mac) → its `src.data.connectors.gated`
  connector, which stays disabled until its feature flag **and** credentials are set
  (`freddie_enabled` / `bureau_enabled` / `openbanking_enabled`).

Macro context features (RBA/ABS/APRA) are ingested separately into
`macro_indicators` via `src.data.connectors.{rba,abs,apra}.ingest(...)`.

### 2. Temporal (out-of-time) split
Split the new data by time, not at random: train on the older window, validate and
calibrate on the most recent window. This measures the model the way it will be
used — predicting the future from the past — and avoids leakage.

### 3. Retrain and register — as a new version, in `staging`
Retrain via the existing pipeline (`src.train_model.run_training`, which logs to
MLflow when available) and register the result with `src.ml.registry.register_from_training(...)`
at stage `staging`. Do **not** promote yet. The incumbent champion is unaffected.

### 4. Recalibrate probabilities
Wrap the retrained estimator with `src.ml.calibration.calibrate(...)` (isotonic, or
Platt below ~1000 rows) fit on the calibration window from step 2. Record the Brier
score before/after and save the calibration curve to `reports/`. Recompute the
cost-sensitive decision threshold with `src.ml.threshold.optimize_threshold(...)`
(FN:FP = 5:1) on the calibration window and store it on the new model version.

### 5. Rerun fairness + mitigation
Run `src.fairness.run_fairness_audit(...)` on the recent window, persist results with
`src.db.fairness_repo`, and evaluate mitigation with
`src.ml.mitigation.evaluate_mitigation(...)` (four-fifths / 0.8 rule; reweighing and
per-group-threshold experiments). Generate the model card:
`src.ml.model_card.save_model_card(<new_semver>)`. Attach the card + fairness table
to the governance review.

> Per-group thresholds are an **experiment for governance to weigh**, not an
> auto-applied fix — applying different cut-offs by a protected attribute can itself
> be disparate treatment. The card documents the accuracy-vs-fairness trade-off.

### 6. Governance approval → promote to champion
A **governance** role reviews the model card, calibration, and fairness results and,
if satisfied, promotes the new version:

```python
promote_model(new_semver, "champion", approved_by=<governance_user_id>)
```

Promotion to `champion` **requires** `approved_by` — without it the call is refused
before any write, and the incumbent champion is never disturbed. The promotion is
audit-logged (approver + demoted predecessor). Only now does serving switch to the
recalibrated model.

### 7. Post-promotion monitoring
Confirm drift/quality monitors (`src.monitoring`) treat the new version's training
window as the reference distribution, and watch the first days of live drift +
label-delayed performance before considering the recalibration complete.
