"use client";
import { riskBand, type Band } from "@/lib/format";
import { BandBadge, NeutralBadge } from "./Badge";
import { InfoIcon } from "./icons";

type Factor = { friendly: string; contribution: number; direction: string };

export type ScoreData = {
  score: number;
  modelVersion: string;
  factors: Factor[];
  probability?: number;
  threshold?: number;
  band?: string;
  recommendation?: string;
  predictionId?: string;
  disclaimer?: string;
};

const BANDS: Band[] = ["Low", "Medium", "High"];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/* Model-estimate zone and human-decision zone, visually and semantically
   separate (mockup 02). The model zone never triggers an approval; the decision
   options are equal-weight with no preselection. */
export function ScoreResult({ score, modelVersion, factors, probability, threshold, band, recommendation, predictionId, disclaimer }: ScoreData) {
  const resolvedBand: Band = band && BANDS.includes(band as Band) ? (band as Band) : riskBand(score);
  const maxAbs = factors.reduce((m, f) => Math.max(m, Math.abs(f.contribution)), 0) || 1;
  const showScale = typeof probability === "number" && typeof threshold === "number";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      {/* MODEL ESTIMATE ZONE */}
      <section aria-labelledby="pred-h">
        <div className="zone-label">
          <span className="tag tag-model">Model estimate</span>
          <span className="note">Produced by the scoring service. No action is taken from this.</span>
        </div>
        <div className="card prediction-card">
          <div className="card-head">
            <h2 id="pred-h">Estimated risk</h2>
            <BandBadge band={resolvedBand} suffix="risk" />
          </div>
          <div className="card-body">
            <div className="score-row">
              <div>
                <div className="prob-value">{showScale ? `${(probability! * 100).toFixed(1)}%` : score.toFixed(1)}</div>
                <div className="prob-label">
                  {showScale ? "Estimated probability of default next month" : "Model risk score (0–100)"}
                </div>
              </div>
              {showScale && (
                <div>
                  <div className="threshold-scale" role="img"
                    aria-label={`Probability ${(probability! * 100).toFixed(1)}% relative to the decision threshold of ${(threshold! * 100).toFixed(0)}%.`}>
                    <div className="track" />
                    <div className="tick" style={{ left: `${threshold! * 100}%` }} />
                    <div className="tick-label" style={{ left: `${threshold! * 100}%` }}>threshold {threshold!.toFixed(2)}</div>
                    <div className="marker" style={{ left: `${Math.min(probability! * 100, 100)}%` }}>
                      <div className="lbl">{probability!.toFixed(3)}</div>
                      <div className="pin" />
                    </div>
                  </div>
                  <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", margin: "var(--space-2) 0 0" }}>
                    Threshold shown to all roles. Bands: Low &lt; 0.20 · Medium 0.20–0.50 · High &gt; 0.50.
                  </p>
                </div>
              )}
            </div>

            <h3 style={{ fontSize: "var(--text-sm)", margin: "var(--space-6) 0 var(--space-3)", display: "flex", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
              Top factors in this score
              <span className="legend" style={{ fontSize: "var(--text-xs)" }}>
                <span className="k"><span className="swatch" style={{ background: "var(--contrib-up)" }} />raised the score</span>
                <span className="k"><span className="swatch" style={{ background: "var(--contrib-down)" }} />lowered the score</span>
              </span>
            </h3>
            <div className="shap">
              {factors.map((f, i) => {
                const up = f.contribution > 0;
                const w = (Math.abs(f.contribution) / maxAbs) * 50;
                return (
                  <div className="shap-row" key={i}>
                    <span className="f" title={f.friendly}>{f.friendly}</span>
                    <div className="shap-track">
                      <div className={`shap-bar ${up ? "up" : "down"}`} style={{ width: `${w}%` }} />
                    </div>
                    <span className="v">{up ? "+" : "−"}{Math.abs(f.contribution).toFixed(3)}</span>
                  </div>
                );
              })}
            </div>

            <div className="callout callout-info" style={{ marginTop: "var(--space-4)" }}>
              <InfoIcon />
              <span>{disclaimer || "These values show how much each feature contributed to this score relative to the model's baseline. Contribution is not causation — a factor moving the score is not proof it would change the outcome."}</span>
            </div>

            <div className="meta-line">
              <span>model: {modelVersion}</span>
              {showScale && <span>threshold {threshold!.toFixed(2)}</span>}
              {predictionId && <span>prediction id: {predictionId.slice(0, 12)}</span>}
            </div>
          </div>
        </div>
      </section>

      {/* HUMAN DECISION ZONE */}
      <section aria-labelledby="dec-h">
        <div className="zone-label">
          <span className="tag tag-human">Your decision</span>
          <span className="note">The model recommends; a person decides.</span>
        </div>
        <div className="card decision-card">
          <div className="card-head">
            <h2 id="dec-h">Record the human decision</h2>
            {recommendation && <NeutralBadge>System suggests: {cap(recommendation)}</NeutralBadge>}
          </div>
          <div className="card-body">
            <div className="decision-options" role="radiogroup" aria-label="Final action">
              {(["Approve", "Refer", "Decline"] as const).map((opt) => (
                <div className="decision-opt" key={opt}>
                  <input type="radio" name="action" id={`opt-${opt}`} disabled />
                  <label htmlFor={`opt-${opt}`}>
                    <strong>{opt}</strong>
                    <small>{opt === "Approve" ? "Open the account" : opt === "Refer" ? "Send to senior review" : "Do not open the account"}</small>
                  </label>
                </div>
              ))}
            </div>
            <div className="field">
              <label htmlFor="notes">Reason for your decision</label>
              <textarea id="notes" className="decision-textarea" disabled
                placeholder="Recording decisions to the audit trail is a future release. This score is decision-support only." />
            </div>
            <button type="button" className="btn btn-primary" disabled>Record decision</button>
          </div>
        </div>
      </section>
    </div>
  );
}
