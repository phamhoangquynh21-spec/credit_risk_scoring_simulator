"use client";
import { useEffect, useState } from "react";
import { CheckIcon, WarnTriangle } from "./icons";
import { ErrorState, Skeleton } from "./states";

type Probe = { ok: boolean; status: number; latency: number; body?: unknown; error?: string };
type SysResp = { health: Probe; ready: Probe };
type State =
  | { kind: "loading" }
  | { kind: "ok"; data: SysResp }
  | { kind: "error"; message: string };

export function SystemHealth() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let alive = true;
    fetch("/api/system")
      .then(async (r) => {
        const body = await r.json();
        if (!alive) return;
        if (!r.ok) { setState({ kind: "error", message: body.error ?? `HTTP ${r.status}` }); return; }
        setState({ kind: "ok", data: body as SysResp });
      })
      .catch((e) => { if (alive) setState({ kind: "error", message: (e as Error).message }); });
    return () => { alive = false; };
  }, []);

  if (state.kind === "loading") {
    return (
      <div className="grid cols-2">
        {["Liveness", "Readiness"].map((t) => (
          <div className="card" key={t}><div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            <Skeleton height={20} width={140} /><Skeleton height={16} /><Skeleton height={16} width="60%" />
          </div></div>
        ))}
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="card"><div className="card-body">
        <ErrorState title="Could not reach the model service" message="The health probes did not respond. The service may be waking from idle — retry in a moment." />
      </div></div>
    );
  }

  return (
    <div className="grid cols-2">
      <ProbeCard title="Liveness" endpoint="/health" probe={state.data.health} />
      <ProbeCard title="Readiness" endpoint="/ready" probe={state.data.ready} />
    </div>
  );
}

function ProbeCard({ title, endpoint, probe }: { title: string; endpoint: string; probe: Probe }) {
  return (
    <div className="card">
      <div className="card-head">
        <h2>{title}</h2>
        <span className="hint mono">{endpoint}</span>
      </div>
      <div className="card-body">
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
          <span className={`badge ${probe.ok ? "badge-ok" : "badge-warn"}`}>
            {probe.ok ? <CheckIcon /> : <WarnTriangle />}
            {probe.ok ? "Healthy" : "Unavailable"}
          </span>
          <span className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
            HTTP {probe.status || "—"} · {probe.latency} ms
          </span>
        </div>
        {probe.error ? (
          <p style={{ fontSize: "var(--text-sm)", color: "var(--danger)" }}>{probe.error}</p>
        ) : (
          <pre className="mono" style={{ margin: 0, fontSize: "var(--text-xs)", color: "var(--color-text-secondary)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {JSON.stringify(probe.body, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
