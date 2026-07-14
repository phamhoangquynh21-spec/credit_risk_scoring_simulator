"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const STAGES = ["staging", "champion", "retired"];

/* Governance-only model promotion. Posts to the JWT-forwarding
   /api/model/promote route handler; the ML service independently enforces the
   governance role and the champion-approval rule. */
export function PromoteControl({ semver, currentStage }: { semver: string; currentStage: string }) {
  const router = useRouter();
  const [stage, setStage] = useState(STAGES.find((s) => s !== currentStage) ?? "staging");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  async function promote() {
    if (!window.confirm(`Promote ${semver} to “${stage}”? This is recorded to the audit trail.`)) return;
    setBusy(true); setMsg(null);
    try {
      const r = await fetch("/api/model/promote", {
        method: "POST",
        body: JSON.stringify({ semver, to_stage: stage }),
      });
      const b = await r.json();
      if (!r.ok) throw new Error(b.error ?? `HTTP ${r.status}`);
      setMsg({ kind: "ok", text: `Now ${b.stage ?? stage}.` });
      router.refresh();
    } catch (e) {
      setMsg({ kind: "err", text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
      <label className="eyebrow" htmlFor={`stage-${semver}`}>Promote to</label>
      <select id={`stage-${semver}`} value={stage} onChange={(e) => setStage(e.target.value)}
        style={{ fontFamily: "inherit", fontSize: "var(--text-sm)", border: "1px solid var(--color-border-strong)", borderRadius: "var(--radius-md)", padding: "var(--space-1) var(--space-2)", background: "var(--color-surface)", color: "var(--color-text)", minHeight: 32 }}>
        {STAGES.filter((s) => s !== currentStage).map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
      <button type="button" className="btn btn-ghost" onClick={promote} disabled={busy}>
        {busy ? "Working…" : "Promote"}
      </button>
      {msg && (
        <span role="status" style={{ fontSize: "var(--text-xs)", color: msg.kind === "ok" ? "var(--success)" : "var(--danger)" }}>
          {msg.text}
        </span>
      )}
    </div>
  );
}
