import { createServerSupabase } from "@/lib/supabase/server";

export default async function PortfolioPage() {
  const supabase = await createServerSupabase();
  const { data: pf } = await supabase.from("portfolios")
    .select("id, name, row_count").eq("is_demo", true).limit(1).single();
  // Sample rows for a lightweight distribution (avoid pulling all 30k).
  const { data: rows } = await supabase.from("portfolio_rows")
    .select("features").eq("portfolio_id", pf?.id ?? "").limit(2000);
  const feats = (rows ?? []).map((r) => r.features as Record<string, number>);
  const total = feats.length;
  const defaults = feats.filter((f) => f["default.payment.next.month"] === 1).length;
  const byEdu = groupRate(feats, (f) => eduLabel(f["education"]));
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Portfolio Risk Monitor</h1>
        <p className="text-sm text-gray-500">
          {pf?.name} · {pf?.row_count?.toLocaleString()} customers (showing a {total.toLocaleString()}-row sample)
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <div className="rounded-lg border p-4">
          <div className="text-xs uppercase text-gray-500">Sample default rate</div>
          <div className="mt-1 text-2xl font-semibold">{total ? ((defaults / total) * 100).toFixed(1) : "—"}%</div>
        </div>
      </div>
      <div>
        <h2 className="mb-2 text-sm font-medium">Default rate by education</h2>
        <table className="text-sm">
          <thead><tr><th className="p-2 text-left">Education</th><th className="p-2 text-right">Default rate</th></tr></thead>
          <tbody>
            {Object.entries(byEdu).map(([label, v]) => (
              <tr key={label}><td className="p-2">{label}</td>
                <td className="p-2 text-right tabular-nums">{(v * 100).toFixed(1)}%</td></tr>
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
  const out: Record<string, number> = {};
  for (const [k, { n, d }] of Object.entries(agg)) out[k] = n ? d / n : 0;
  return out;
}
function eduLabel(v: number) {
  return { 1: "Graduate school", 2: "University", 3: "High school" }[v] ?? "Other";
}
