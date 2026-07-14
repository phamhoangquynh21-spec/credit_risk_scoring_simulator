"use client";
import { useState } from "react";
import { defaultApplicant, type Applicant } from "@/lib/applicant";
import { ScoreResult, type ScoreData } from "./ScoreResult";

const PAYS = ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"];

export function ApplicantForm() {
  const [a, setA] = useState<Applicant>(defaultApplicant());
  const [result, setResult] = useState<ScoreData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(k: string, v: number) { setA((p) => ({ ...p, [k]: v })); }

  async function submit() {
    setLoading(true); setError(null);
    try {
      const [p, e] = await Promise.all([
        fetch("/api/predict", { method: "POST", body: JSON.stringify(a) }).then((r) => r.json()),
        fetch("/api/explain", { method: "POST", body: JSON.stringify(a) }).then((r) => r.json()),
      ]);
      if (p.error) throw new Error(p.error);
      setResult({
        score: p.risk_score,
        modelVersion: p.model_version ?? "—",
        probability: p.probability,
        threshold: p.threshold_used,
        band: p.risk_band,
        recommendation: p.recommendation,
        predictionId: p.prediction_id,
        disclaimer: e.disclaimer,
        factors: (e.top_factors ?? e.factors ?? []).slice(0, 6),
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="assess-grid">
      {/* Applicant form */}
      <div className="card">
        <div className="card-head"><h2>Applicant profile</h2><span className="hint">UCI schema</span></div>
        <div className="card-body">
          <fieldset>
            <legend>Credit &amp; demographics</legend>
            <Num label="Credit limit (NT$)" k="limit_bal" a={a} set={set} />
            <div className="field-row">
              <Num label="Age" k="age" a={a} set={set} />
              <Num label="Sex (1=M, 2=F)" k="sex" a={a} set={set} />
            </div>
            <div className="field-row">
              <Num label="Education (1–4)" k="education" a={a} set={set} />
              <Num label="Marriage (1–3)" k="marriage" a={a} set={set} />
            </div>
          </fieldset>
          <fieldset>
            <legend>Repayment status (−1 duly … 8 late)</legend>
            <div className="field-row" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
              {PAYS.map((p) => <Num key={p} label={p} k={p} a={a} set={set} />)}
            </div>
          </fieldset>
          <button onClick={submit} disabled={loading} className="btn btn-primary">
            {loading ? "Scoring…" : "Score applicant"}
          </button>
          {error && <p role="alert" style={{ color: "var(--danger)", fontSize: "var(--text-sm)", marginTop: "var(--space-3)" }}>{error}</p>}
          <p className="help" style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: "var(--space-3) 0 0" }}>
            First score after idle may take up to a minute while the scoring service wakes.
          </p>
        </div>
      </div>

      {/* Prediction + decision */}
      <div>
        {result ? (
          <ScoreResult {...result} />
        ) : (
          <div className="card"><div className="card-body">
            <p style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
              Fill in the applicant profile and run the scorer to see the model estimate, its top factors,
              and the decision panel.
            </p>
          </div></div>
        )}
      </div>
    </div>
  );
}

function Num({ label, k, a, set }:
  { label: string; k: string; a: Record<string, number>; set: (k: string, v: number) => void }) {
  return (
    <div className="field">
      <label htmlFor={`f-${k}`}>{label}</label>
      <input id={`f-${k}`} className="mono-input" type="number" value={a[k]}
        onChange={(e) => set(k, Number(e.target.value))} />
    </div>
  );
}
