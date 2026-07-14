import { createServerSupabase } from "@/lib/supabase/server";
import { PageHeader } from "@/components/PageHeader";
import { MetricTile } from "@/components/MetricTile";
import { ModelAucTile } from "@/components/ModelAucTile";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { BandBadge } from "@/components/Badge";
import { EmptyState } from "@/components/states";
import { WarnTriangle, CheckIcon } from "@/components/icons";
import { pct, fmtInt, fmtUTC } from "@/lib/format";
import type { Band } from "@/lib/format";

export const dynamic = "force-dynamic";

type PredRow = {
  probability: number;
  threshold_used: number;
  risk_band: string;
  created_at: string;
};
type ActivityRow = { id: string; risk_band: string; created_at: string };
type FairResult = { attribute: string; grp: string; disparity_ratio: number | null };

const BANDS: Band[] = ["Low", "Medium", "High"];

export default async function OverviewPage() {
  const supabase = await createServerSupabase();

  const [{ data: champ }, { data: pf }] = await Promise.all([
    supabase.from("model_versions").select("semver, metrics, threshold").eq("stage", "champion").maybeSingle(),
    supabase.from("portfolios").select("id, name, row_count").eq("is_demo", true).limit(1).maybeSingle(),
  ]);

  const [predsRes, activityRes, rowsRes, fairRunRes] = await Promise.all([
    pf?.id
      ? supabase.from("predictions").select("probability, threshold_used, risk_band, created_at")
          .eq("portfolio_id", pf.id).limit(5000)
      : Promise.resolve({ data: [] as PredRow[] }),
    supabase.from("predictions").select("id, risk_band, created_at").order("created_at", { ascending: false }).limit(6),
    pf?.id
      ? supabase.from("portfolio_rows").select("features").eq("portfolio_id", pf.id).limit(2000)
      : Promise.resolve({ data: [] as { features: Record<string, number> }[] }),
    supabase.from("fairness_runs").select("id, run_at").order("run_at", { ascending: false }).limit(1).maybeSingle(),
  ]);

  const preds = (predsRes.data ?? []) as PredRow[];
  const activity = (activityRes.data ?? []) as ActivityRow[];
  const rows = (rowsRes.data ?? []) as { features: Record<string, number> }[];

  // ---- Portfolio default rate (from labeled demo rows) ----
  const feats = rows.map((r) => r.features);
  const labeled = feats.length;
  const defaults = feats.filter((f) => f["default.payment.next.month"] === 1).length;
  const defaultRate = labeled ? defaults / labeled : null;

  // ---- Approvals recommended (probability below the row's threshold) ----
  const scored = preds.length;
  const approvals = preds.filter((p) => p.probability < p.threshold_used).length;

  // ---- Band distribution ----
  const bandCounts: Record<Band, number> = { Low: 0, Medium: 0, High: 0 };
  for (const p of preds) if (p.risk_band in bandCounts) bandCounts[p.risk_band as Band]++;

  // ---- Monthly trend (real, from prediction timestamps) ----
  const byMonth = new Map<string, { volume: number; high: number }>();
  for (const p of preds) {
    const key = p.created_at.slice(0, 7); // YYYY-MM
    const b = byMonth.get(key) ?? { volume: 0, high: 0 };
    b.volume++;
    if (p.risk_band === "High") b.high++;
    byMonth.set(key, b);
  }
  const trend: TrendPoint[] = [...byMonth.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, v]) => ({
      label: new Date(`${key}-01T00:00:00Z`).toLocaleString("en-US", { month: "short", timeZone: "UTC" }),
      volume: v.volume,
      highRiskPct: v.volume ? Number(((v.high / v.volume) * 100).toFixed(1)) : 0,
    }));

  // ---- Fairness status (worst disparity ratio in the latest run) ----
  let fairWorst: { ratio: number; group: string } | null = null;
  const fairRun = fairRunRes.data as { id: string } | null;
  if (fairRun?.id) {
    const { data: fres } = await supabase
      .from("fairness_results").select("attribute, grp, disparity_ratio").eq("run_id", fairRun.id);
    for (const r of (fres ?? []) as FairResult[]) {
      if (typeof r.disparity_ratio === "number" && (!fairWorst || r.disparity_ratio < fairWorst.ratio)) {
        fairWorst = { ratio: r.disparity_ratio, group: `${r.attribute}: ${r.grp}` };
      }
    }
  }
  const fairPass = fairWorst ? fairWorst.ratio >= 0.8 : null;

  const dataAsOf = preds.length
    ? fmtUTC(preds.reduce((m, p) => (p.created_at > m ? p.created_at : m), preds[0].created_at))
    : null;
  const context = [
    { k: "Model", v: champ?.semver ?? "—" },
    { k: "Data as of", v: dataAsOf ?? "synthetic demo" },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Executive overview"
        title="Portfolio health at a glance"
        subtitle="Demo book of synthetic credit-card accounts, scored against the champion model."
        context={context}
      />
      <div className="content">
        {/* KPI ROW */}
        <div className="grid kpi-row" style={{ marginBottom: "var(--space-4)" }}>
          <MetricTile
            label="Portfolio default rate"
            value={defaultRate == null ? "—" : pct(defaultRate)}
            help={defaultRate == null
              ? "No labeled accounts available."
              : `Observed across ${fmtInt(labeled)} labeled demo accounts.`}
          />
          <MetricTile
            label="Approvals recommended"
            value={scored ? fmtInt(approvals) : "—"}
            help={scored ? `of ${fmtInt(scored)} scored · below the decision threshold` : "No scored accounts yet."}
          />
          <ModelAucTile />
          <FairnessTile worst={fairWorst} pass={fairPass} />
        </div>

        {/* TREND + ACTIVITY */}
        <div className="grid cols-2-1">
          <div className="card">
            <div className="card-head">
              <h2>Scoring volume &amp; high-risk share</h2>
              <span className="hint">By month scored</span>
            </div>
            <div className="card-body">
              {trend.length >= 2 ? (
                <TrendChart
                  data={trend}
                  ariaLabel={`Line chart of accounts scored per month and the share banded High, across ${trend.length} months.`}
                  caption="Accounts scored per month (area) and the share landing in the High band (line). Both series are computed from stored predictions."
                />
              ) : (
                <EmptyState
                  title="Not enough history yet"
                  message="A monthly trend appears once accounts have been scored across at least two calendar months. Score a batch from the Portfolio monitor to build history."
                />
              )}
            </div>
          </div>

          <div className="card activity">
            <div className="card-head"><h2>Recent activity</h2><span className="hint">Latest scores</span></div>
            <div className="card-body" style={{ paddingTop: "var(--space-2)" }}>
              {activity.length ? (
                <ul>
                  {activity.map((a) => (
                    <li key={a.id}>
                      <span className="ic">
                        <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.8} aria-hidden>
                          <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
                        </svg>
                      </span>
                      <div>
                        <div className="t">
                          Account <span className="mono">{a.id.slice(0, 8)}</span> scored —{" "}
                          {BANDS.includes(a.risk_band as Band) ? <BandBadge band={a.risk_band as Band} /> : a.risk_band}
                        </div>
                        <div className="m">{fmtUTC(a.created_at) ?? a.created_at}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState title="No activity yet" message="Scored applicants and batches will appear here as they are recorded." />
              )}
            </div>
          </div>
        </div>

        {/* BAND DISTRIBUTION */}
        <div className="card" style={{ marginTop: "var(--space-4)" }}>
          <div className="card-head">
            <h2>Risk-band distribution</h2>
            <span className="hint">{scored ? `${fmtInt(scored)} accounts scored` : "No scored accounts"}</span>
          </div>
          <div className="card-body">
            {scored ? (
              <>
                <div style={{ display: "flex", height: 44, borderRadius: "var(--radius-md)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
                  {BANDS.map((b) => {
                    const w = (bandCounts[b] / scored) * 100;
                    if (w === 0) return null;
                    return (
                      <div key={b} className="mono"
                        style={{ width: `${w}%`, background: `var(--risk-${b.toLowerCase()})`, display: "grid", placeItems: "center", color: "#fff", fontSize: "var(--text-sm)" }}>
                        {w >= 8 ? `${w.toFixed(0)}%` : ""}
                      </div>
                    );
                  })}
                </div>
                <div className="legend" style={{ marginTop: "var(--space-3)" }}>
                  {BANDS.map((b) => (
                    <span className="k" key={b}><BandBadge band={b} /> {fmtInt(bandCounts[b])} accounts</span>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState title="No scored accounts yet" message="Score applicants or upload a portfolio to see how risk bands are distributed." />
            )}
          </div>
        </div>
      </div>
    </>
  );
}

function FairnessTile({ worst, pass }: { worst: { ratio: number; group: string } | null; pass: boolean | null }) {
  return (
    <div className="card metric">
      <div className="eyebrow">Fairness status</div>
      <div style={{ paddingTop: 6 }}>
        {pass == null ? (
          <span className="badge badge-neutral">No audit yet</span>
        ) : pass ? (
          <span className="badge badge-ok"><CheckIcon />Within 0.80 rule</span>
        ) : (
          <span className="badge badge-warn"><WarnTriangle />Review needed</span>
        )}
      </div>
      <div className="foot">
        {worst
          ? <>Worst ratio <span className="mono">{worst.ratio.toFixed(3)}</span> · {worst.group}</>
          : "Run a fairness audit to populate this."}
      </div>
    </div>
  );
}
