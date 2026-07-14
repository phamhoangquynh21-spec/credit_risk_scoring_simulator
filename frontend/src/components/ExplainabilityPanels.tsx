"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { defaultApplicant } from "@/lib/applicant";
import type { Band } from "@/lib/format";
import { BandBadge } from "./Badge";
import { InfoIcon } from "./icons";
import { Skeleton, ErrorState } from "./states";

type Factor = { feature: string; friendly: string; contribution: number; direction: string };
type ReasonCode = { label: string; arrow: string; direction: string; magnitude: number };
type ExplainResp = {
  risk_score: number;
  risk_band: string;
  model_version: string;
  top_factors: Factor[];
  reason_codes: ReasonCode[];
  disclaimer: string;
};
type State =
  | { kind: "loading" }
  | { kind: "ok"; data: ExplainResp }
  | { kind: "error"; message: string };

const BANDS: Band[] = ["Low", "Medium", "High"];

export function ExplainabilityPanels() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let alive = true;
    fetch("/api/explain", { method: "POST", body: JSON.stringify(defaultApplicant()) })
      .then(async (r) => {
        const body = await r.json();
        if (!alive) return;
        if (!r.ok) { setState({ kind: "error", message: body.error ?? `HTTP ${r.status}` }); return; }
        setState({ kind: "ok", data: body as ExplainResp });
      })
      .catch((e) => { if (alive) setState({ kind: "error", message: (e as Error).message }); });
    return () => { alive = false; };
  }, []);

  if (state.kind === "error") {
    return (
      <div className="card"><div className="card-body">
        <ErrorState
          title="Could not load explanations"
          message="The model service did not respond. It may be waking from idle — the first request after a quiet period can take up to a minute. Retry shortly."
        />
      </div></div>
    );
  }

  const loading = state.kind === "loading";
  const data = state.kind === "ok" ? state.data : null;
  const factors = data?.top_factors ?? [];
  const byMag = [...factors].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const maxAbs = byMag.reduce((m, f) => Math.max(m, Math.abs(f.contribution)), 0) || 1;
  const band = data && BANDS.includes(data.risk_band as Band) ? (data.risk_band as Band) : null;

  return (
    <div className="grid cols-2">
      {/* Global feature importance */}
      <div className="card">
        <div className="card-head">
          <h2>Global feature importance</h2>
          <span className="hint">Absolute SHAP magnitude</span>
        </div>
        <div className="card-body">
          {loading ? (
            <SkeletonRows />
          ) : (
            <>
              {byMag.map((f) => (
                <div className="imp-row" key={f.feature}>
                  <span className="f" title={f.friendly}>{f.friendly}</span>
                  <div className="imp-track">
                    <div className="imp-bar" style={{ width: `${(Math.abs(f.contribution) / maxAbs) * 100}%` }} />
                  </div>
                  <span className="v">{Math.abs(f.contribution).toFixed(3)}</span>
                </div>
              ))}
              <figcaption>
                Ranked by the absolute size of each feature’s SHAP contribution for a representative applicant,
                computed live by the model. Score a custom profile on the{" "}
                <Link href="/assess" style={{ color: "var(--color-accent)" }}>Assess applicant</Link> screen.
              </figcaption>
            </>
          )}
        </div>
      </div>

      {/* Single-prediction breakdown */}
      <div className="card">
        <div className="card-head">
          <h2>Single-prediction breakdown</h2>
          <span className="hint">Representative applicant</span>
        </div>
        <div className="card-body">
          {loading ? (
            <SkeletonRows />
          ) : data ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-4)", flexWrap: "wrap" }}>
                <span className="mono" style={{ fontSize: "var(--text-lg)", fontWeight: 500 }}>{data.risk_score.toFixed(1)}</span>
                {band ? <BandBadge band={band} suffix="risk" /> : <span className="badge badge-neutral">{data.risk_band}</span>}
                <span className="badge badge-neutral">model {data.model_version}</span>
              </div>

              <div className="shap">
                {byMag.map((f) => {
                  const up = f.contribution > 0;
                  const w = (Math.abs(f.contribution) / maxAbs) * 50; // half-track each side
                  return (
                    <div className="shap-row" key={f.feature}>
                      <span className="f" title={f.friendly}>{f.friendly}</span>
                      <div className="shap-track" role="img"
                        aria-label={`${f.friendly} ${up ? "raised" : "lowered"} the score by ${Math.abs(f.contribution).toFixed(3)}.`}>
                        <div className={`shap-bar ${up ? "up" : "down"}`} style={{ width: `${w}%` }} />
                      </div>
                      <span className="v">{up ? "+" : "−"}{Math.abs(f.contribution).toFixed(3)}</span>
                    </div>
                  );
                })}
              </div>

              <div className="legend" style={{ margin: "var(--space-4) 0" }}>
                <span className="k"><span className="swatch" style={{ background: "var(--contrib-up)" }} />raised the score</span>
                <span className="k"><span className="swatch" style={{ background: "var(--contrib-down)" }} />lowered the score</span>
              </div>

              {data.reason_codes?.length ? (
                <ul style={{ listStyle: "none", margin: "0 0 var(--space-4)", padding: 0, display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                  {data.reason_codes.map((c, i) => (
                    <li key={i} style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                      <span className="mono" style={{ color: c.direction === "increases" ? "var(--contrib-up)" : "var(--contrib-down)" }}>{c.arrow}</span>{" "}
                      {c.label} — {c.direction} risk
                    </li>
                  ))}
                </ul>
              ) : null}

              <div className="callout callout-info">
                <InfoIcon />
                <span>{data.disclaimer || "These values show how much each feature contributed to this score relative to the model's baseline. Contribution is not causation."}</span>
              </div>

              <div className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-4)" }}>
                method shap_tree · model {data.model_version}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SkeletonRows() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={18} />)}
    </div>
  );
}
