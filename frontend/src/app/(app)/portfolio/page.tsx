import { createServerSupabase } from "@/lib/supabase/server";
import { PageHeader } from "@/components/PageHeader";
import { MetricTile } from "@/components/MetricTile";
import { EmptyState } from "@/components/states";
import { pct, fmtInt } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function PortfolioPage() {
  const supabase = await createServerSupabase();
  const { data: pf } = await supabase.from("portfolios")
    .select("id, name, row_count").eq("is_demo", true).limit(1).maybeSingle();
  // Sample rows for a lightweight distribution (avoid pulling the full book).
  const { data: rows } = await supabase.from("portfolio_rows")
    .select("features").eq("portfolio_id", pf?.id ?? "").limit(2000);
  const feats = (rows ?? []).map((r) => r.features as Record<string, number>);
  const total = feats.length;
  const defaults = feats.filter((f) => f["default.payment.next.month"] === 1).length;
  const byEdu = groupRate(feats, (f) => eduLabel(f["education"]));
  const byUtil = groupRate(feats, (f) => utilBucket(f));

  return (
    <>
      <PageHeader
        eyebrow="Portfolio"
        title={pf?.name ?? "Portfolio risk monitor"}
        subtitle={
          total
            ? `${fmtInt(pf?.row_count ?? total)} synthetic accounts · analysing a ${fmtInt(total)}-row sample.`
            : "Batch-scored synthetic credit-card accounts."
        }
        context={[{ k: "Data", v: "labeled demo book" }]}
      />
      <div className="content">
        {total ? (
          <>
            <div className="grid kpi-row" style={{ marginBottom: "var(--space-4)" }}>
              <MetricTile
                label="Sample default rate"
                value={pct(defaults / total)}
                help={`${fmtInt(defaults)} defaults in ${fmtInt(total)} sampled accounts`}
              />
              <MetricTile label="Accounts sampled" value={fmtInt(total)} help="Lightweight sample of the book" />
            </div>

            <div className="grid cols-2">
              <SegmentTable title="Default rate by education" heading="Education" rows={byEdu} />
              <SegmentTable title="Default rate by utilisation" heading="Utilisation" rows={byUtil} order={UTIL_ORDER} />
            </div>

            <p className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-4)" }}>
              rates observed from labeled outcomes (default.payment.next.month) · decision-support only
            </p>
          </>
        ) : (
          <div className="card"><div className="card-body">
            <EmptyState
              title="No portfolio rows yet"
              message="Upload a CSV of applicants to score your first batch and populate the portfolio monitor."
            />
          </div></div>
        )}
      </div>
    </>
  );
}

const UTIL_ORDER = ["Under 30%", "30 – 60%", "60 – 90%", "Over 90%"];

function SegmentTable({
  title, heading, rows, order,
}: {
  title: string; heading: string; rows: Record<string, { rate: number; n: number }>; order?: string[];
}) {
  const entries = Object.entries(rows);
  entries.sort(([a], [b]) =>
    order ? order.indexOf(a) - order.indexOf(b) : rows[b].rate - rows[a].rate);
  return (
    <div className="card">
      <div className="card-head"><h2>{title}</h2><span className="hint">Sampled accounts</span></div>
      <div className="table-wrap">
        <table className="data-table" style={{ minWidth: 320 }}>
          <thead>
            <tr>
              <th scope="col">{heading}</th>
              <th scope="col" className="num">Accounts</th>
              <th scope="col" className="num">Default rate</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([label, v]) => (
              <tr key={label}>
                <td>{label}</td>
                <td className="num">{fmtInt(v.n)}</td>
                <td className="num">{pct(v.rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function groupRate(rows: Record<string, number>[], keyFn: (r: Record<string, number>) => string) {
  const agg: Record<string, { n: number; d: number }> = {};
  for (const r of rows) {
    const g = keyFn(r);
    agg[g] ??= { n: 0, d: 0 };
    agg[g].n++; if (r["default.payment.next.month"] === 1) agg[g].d++;
  }
  const out: Record<string, { rate: number; n: number }> = {};
  for (const [k, { n, d }] of Object.entries(agg)) out[k] = { rate: n ? d / n : 0, n };
  return out;
}
function eduLabel(v: number) {
  return ({ 1: "Graduate school", 2: "University", 3: "High school" } as Record<number, string>)[v] ?? "Other";
}
function utilBucket(f: Record<string, number>) {
  const limit = f["limit_bal"] ?? f["LIMIT_BAL"] ?? 0;
  const bill = f["bill_amt1"] ?? f["BILL_AMT1"] ?? 0;
  const u = limit > 0 ? bill / limit : 0;
  if (u < 0.3) return "Under 30%";
  if (u < 0.6) return "30 – 60%";
  if (u < 0.9) return "60 – 90%";
  return "Over 90%";
}
