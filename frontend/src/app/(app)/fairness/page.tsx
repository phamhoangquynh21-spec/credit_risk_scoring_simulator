import { createServerSupabase } from "@/lib/supabase/server";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/Badge";
import { EmptyState } from "@/components/states";
import { WarnTriangle, CheckIcon } from "@/components/icons";
import { pct, fmtInt, fmtUTC } from "@/lib/format";

export const dynamic = "force-dynamic";

const RULE = 0.8;

type FairResult = {
  attribute: string;
  grp: string;
  n: number;
  selection_rate: number | null;
  recall: number | null;
  precision: number | null;
  disparity_ratio: number | null;
};

const f3 = (v: number | null) => (v == null ? "—" : v.toFixed(3));
const f2 = (v: number | null) => (v == null ? "—" : v.toFixed(2));

export default async function FairnessPage() {
  const supabase = await createServerSupabase();

  const { data: run } = await supabase
    .from("fairness_runs")
    .select("id, run_at, model_version_id")
    .order("run_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!run?.id) {
    return (
      <>
        <PageHeader eyebrow="Governance" title="Fairness &amp; responsible AI"
          subtitle="Per-group audit of the champion model against the four-fifths (0.80) disparity rule." />
        <div className="content">
          <div className="card"><div className="card-body">
            <EmptyState
              title="No fairness audit has been run yet"
              message="Once a fairness audit runs for the champion model, its per-group selection rates and four-fifths (0.80) results appear here. Audits are executed server-side and stored with their model version for reproducibility."
            />
          </div></div>
        </div>
      </>
    );
  }

  const [{ data: resultsRaw }, { data: mv }] = await Promise.all([
    supabase.from("fairness_results")
      .select("attribute, grp, n, selection_rate, recall, precision, disparity_ratio")
      .eq("run_id", run.id),
    supabase.from("model_versions").select("semver, threshold").eq("id", run.model_version_id).maybeSingle(),
  ]);

  const results = ([...(resultsRaw ?? [])] as FairResult[]).sort(
    (a, b) => a.attribute.localeCompare(b.attribute) || (a.disparity_ratio ?? 1) - (b.disparity_ratio ?? 1),
  );

  const ratioOf = (r: FairResult) => r.disparity_ratio ?? 1;
  const failing = results.filter((r) => ratioOf(r) < RULE);
  const worst = results.reduce<FairResult | null>(
    (m, r) => (m == null || ratioOf(r) < ratioOf(m) ? r : m), null);
  const anyFail = failing.length > 0;

  const semver = mv?.semver ?? "—";
  const threshold = mv?.threshold;
  const runStamp = fmtUTC(run.run_at) ?? run.run_at;

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Fairness &amp; responsible AI"
        subtitle="Per-group audit of the champion model against the four-fifths (0.80) disparity rule."
        context={[
          { k: "Audit run", v: `${run.id.slice(0, 8)} · ${runStamp}` },
          { k: "Model", v: semver },
        ]}
      />
      <div className="content">
        {/* Status banner — calm, factual, with a next step */}
        <div className={`status-banner ${anyFail ? "warn" : "ok"}`} role="status">
          <div>
            <div className="big">{worst ? ratioOf(worst).toFixed(3) : "—"}</div>
            <div className="eyebrow" style={{ color: "inherit" }}>worst ratio</div>
          </div>
          <div>
            {anyFail && worst ? (
              <>
                <h2>{worst.attribute} disparity is below the 0.80 threshold — review required</h2>
                <p>
                  Group “{worst.grp}” is selected at {pct(ratioOf(worst), 1)} of the rate of the most-selected
                  group in “{worst.attribute}”. This finding is disclosed, not yet mitigated. Reweighing and
                  per-group threshold experiments would ship through governance sign-off, not a silent retrain.
                </p>
              </>
            ) : (
              <>
                <h2>All groups are within the 0.80 rule</h2>
                <p>
                  No group falls below four-fifths of the most-selected group’s rate in this run. Passing the
                  ratio test is not a fairness certification — this is detection only, on synthetic data.
                </p>
              </>
            )}
          </div>
          <span className={`badge ${anyFail ? "badge-warn" : "badge-ok"}`} style={{ marginLeft: "auto", flexShrink: 0 }}>
            {anyFail ? <WarnTriangle /> : <CheckIcon />}
            {anyFail ? "Action needed" : "Within rule"}
          </span>
        </div>

        <div className="grid cols-2" style={{ marginBottom: "var(--space-4)" }}>
          {/* Disparity ratio chart */}
          <div className="card">
            <div className="card-head">
              <h2>Selection-rate ratio by group</h2>
              <span className="hint">vs. most-selected group · 1.00 = parity</span>
            </div>
            <div className="card-body">
              {results.map((r) => {
                const ratio = ratioOf(r);
                const fail = ratio < RULE;
                return (
                  <div className="grp-row" key={`${r.attribute}-${r.grp}`}>
                    <span className="g">{r.attribute}: {r.grp}</span>
                    <div className="ratio-bar" role="img"
                      aria-label={`${r.attribute} ${r.grp}: ratio ${ratio.toFixed(3)}, ${fail ? "below" : "at or above"} the 0.80 rule.`}>
                      <div className="ratio-fill"
                        style={{ width: `${Math.min(ratio, 1) * 100}%`, background: fail ? "var(--risk-medium)" : "var(--chart-1)" }} />
                      <div className="ratio-rule" />
                    </div>
                    <span className="v">{ratio.toFixed(3)}</span>
                  </div>
                );
              })}
              <figcaption>
                Bars at or right of the 0.80 rule line pass; amber marks a failing group. Ratios use each
                group’s selection rate (share recommended for approval) against the most-selected group.
              </figcaption>
            </div>
          </div>

          {/* Method explainer */}
          <div className="card">
            <div className="card-head"><h2>How this audit works</h2><span className="hint">Method &amp; scope</span></div>
            <div className="card-body" style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
              <p style={{ margin: 0 }}><strong style={{ color: "var(--color-text)" }}>The four-fifths rule.</strong> For each protected attribute, every group’s selection rate is compared to the most-selected group. A ratio under 0.80 flags adverse impact and requires review.</p>
              <p style={{ margin: 0 }}><strong style={{ color: "var(--color-text)" }}>What we measure.</strong> Selection rate, recall, and precision per group, computed at the current decision threshold{threshold != null ? <> (<span className="mono">{threshold.toFixed(2)}</span>)</> : ""}.</p>
              <p style={{ margin: 0 }}><strong style={{ color: "var(--color-text)" }}>What this is not.</strong> Detection only. Passing the ratio test is not a fairness certification, and this synthetic data cannot validate fairness for any real population.</p>
              <div className="callout callout-warn">
                <WarnTriangle />
                <span>Every audit run is stored with its model version and inputs, so this page is reproducible for examiners.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Per-group table */}
        <div className="card">
          <div className="card-head">
            <h2>Per-group results</h2>
            <span className="hint">Audit run {run.id.slice(0, 8)}{threshold != null ? ` · threshold ${threshold.toFixed(2)}` : ""}</span>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Attribute</th>
                  <th scope="col">Group</th>
                  <th scope="col" className="num">n</th>
                  <th scope="col" className="num">Selection rate</th>
                  <th scope="col" className="num">Recall</th>
                  <th scope="col" className="num">Precision</th>
                  <th scope="col" className="num">Disparity ratio</th>
                  <th scope="col">0.80 rule</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => {
                  const ratio = ratioOf(r);
                  const fail = ratio < RULE;
                  return (
                    <tr key={`${r.attribute}-${r.grp}`}>
                      <td>{r.attribute}</td>
                      <td>{r.grp}</td>
                      <td className="num">{fmtInt(r.n)}</td>
                      <td className="num">{f3(r.selection_rate)}</td>
                      <td className="num">{f2(r.recall)}</td>
                      <td className="num">{f2(r.precision)}</td>
                      <td className="num" style={fail ? { color: "var(--risk-medium)", fontWeight: 600 } : undefined}>{ratio.toFixed(3)}</td>
                      <td><StatusBadge status={fail ? "fail" : "pass"} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mono" style={{ padding: "var(--space-3) var(--space-5)", borderTop: "1px solid var(--color-border)", fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
            audit {run.id.slice(0, 8)} · model {semver} · run {runStamp} · audit records retained for governance review
          </div>
        </div>
      </div>
    </>
  );
}
