"use client";
import { useEffect, useState } from "react";

type State =
  | { kind: "loading" }
  | { kind: "ok"; auc: number; semver: string }
  | { kind: "empty" }
  | { kind: "error"; message: string };

/* Model discrimination (AUC) tile. Fetches the champion model card from the ML
   service via the JWT-forwarding /api/model route handler, with explicit
   loading / empty / error states (the Render service may cold-start). */
export function ModelAucTile() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let alive = true;
    fetch("/api/model")
      .then(async (r) => {
        const body = await r.json();
        if (!alive) return;
        if (!r.ok) { setState({ kind: "error", message: body.error ?? `HTTP ${r.status}` }); return; }
        const auc = body?.metrics?.auc_roc;
        if (typeof auc !== "number") { setState({ kind: "empty" }); return; }
        setState({ kind: "ok", auc, semver: body.semver ?? "—" });
      })
      .catch((e) => { if (alive) setState({ kind: "error", message: (e as Error).message }); });
    return () => { alive = false; };
  }, []);

  return (
    <div className="card metric">
      <div className="eyebrow">Model discrimination (AUC)</div>
      {state.kind === "loading" && (
        <div style={{ marginTop: "var(--space-2)" }}>
          <div className="skeleton" style={{ height: 34, width: 96 }} aria-hidden />
          <span className="sr-only">Loading model metrics…</span>
        </div>
      )}
      {state.kind === "ok" && (
        <>
          <div className="val">{state.auc.toFixed(2)}</div>
          <div className="foot">held-out test set · {state.semver}</div>
        </>
      )}
      {state.kind === "empty" && (
        <>
          <div className="val">—</div>
          <div className="foot">No AUC reported by the model service.</div>
        </>
      )}
      {state.kind === "error" && (
        <>
          <div className="val">—</div>
          <div className="foot" role="alert">
            Model service unavailable. It may be waking from idle — retry shortly.
          </div>
        </>
      )}
    </div>
  );
}
