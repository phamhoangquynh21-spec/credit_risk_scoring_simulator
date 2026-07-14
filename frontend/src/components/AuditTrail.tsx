"use client";
import { useEffect, useState } from "react";
import { fmtUTC } from "@/lib/format";
import { EmptyState, ErrorState, Skeleton } from "./states";

type Event = {
  id: number | string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: unknown;
  created_at: string;
};
type State =
  | { kind: "loading" }
  | { kind: "ok"; events: Event[] }
  | { kind: "forbidden" }
  | { kind: "error"; message: string };

export function AuditTrail() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let alive = true;
    fetch("/api/audit")
      .then(async (r) => {
        const body = await r.json();
        if (!alive) return;
        if (!r.ok) {
          const msg: string = body.error ?? `HTTP ${r.status}`;
          if (msg.includes("403") || /forbidden|role/i.test(msg)) { setState({ kind: "forbidden" }); return; }
          setState({ kind: "error", message: msg });
          return;
        }
        setState({ kind: "ok", events: body.events ?? [] });
      })
      .catch((e) => { if (alive) setState({ kind: "error", message: (e as Error).message }); });
    return () => { alive = false; };
  }, []);

  if (state.kind === "loading") {
    return (
      <div className="card"><div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} height={18} />)}
      </div></div>
    );
  }
  if (state.kind === "forbidden") {
    return (
      <div className="card"><div className="card-body">
        <EmptyState
          title="Audit trail is restricted"
          message="The audit export is available to governance and compliance roles. Ask an administrator if you need access."
        />
      </div></div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="card"><div className="card-body">
        <ErrorState title="Could not load the audit trail" message="The audit service did not respond. It may be waking from idle — retry shortly." />
      </div></div>
    );
  }
  if (!state.events.length) {
    return (
      <div className="card"><div className="card-body">
        <EmptyState title="No audit events yet" message="Scoring, decisions, and governance actions are recorded here as they happen." />
      </div></div>
    );
  }

  return (
    <div className="card">
      <div className="card-head"><h2>Recent audit events</h2><span className="hint">Newest first · up to 100</span></div>
      <div className="table-wrap">
        <table className="data-table" style={{ minWidth: 720 }}>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">Action</th>
              <th scope="col">Entity</th>
              <th scope="col">Entity id</th>
              <th scope="col">Actor</th>
              <th scope="col">Detail</th>
            </tr>
          </thead>
          <tbody>
            {state.events.map((e) => (
              <tr key={String(e.id)}>
                <td className="mono">{fmtUTC(e.created_at) ?? e.created_at}</td>
                <td>{e.action}</td>
                <td>{e.entity_type}</td>
                <td className="id">{e.entity_id ?? "—"}</td>
                <td className="mono">{e.actor_id ? e.actor_id.slice(0, 8) : "system"}</td>
                <td style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  title={typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail)}>
                  {e.detail && Object.keys(e.detail as object).length ? JSON.stringify(e.detail) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
