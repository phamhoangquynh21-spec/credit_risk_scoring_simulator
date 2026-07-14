import { createServerSupabase } from "@/lib/supabase/server";
import { PageHeader } from "@/components/PageHeader";
import { MetricTile } from "@/components/MetricTile";
import { EmptyState } from "@/components/states";

export const dynamic = "force-dynamic";

export default async function PerformancePage() {
  const supabase = await createServerSupabase();
  const { data: champ } = await supabase.from("model_versions")
    .select("semver, algo, metrics, threshold").eq("stage", "champion").maybeSingle();
  const m = (champ?.metrics ?? {}) as Record<string, number>;
  const cm = (m.confusion_matrix as unknown as number[][]) ?? [[0, 0], [0, 0]];
  const hasMetrics = m.auc_roc != null;

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Model performance"
        subtitle="Champion model quality on the held-out test split (target AUC ≥ 0.75)."
        context={[
          { k: "Model", v: champ?.semver ?? "—" },
          { k: "Algorithm", v: champ?.algo ?? "—" },
          ...(champ?.threshold != null ? [{ k: "Threshold", v: champ.threshold.toFixed(2) }] : []),
        ]}
      />
      <div className="content">
        {hasMetrics ? (
          <>
            <div className="grid kpi-row" style={{ marginBottom: "var(--space-4)" }}>
              <MetricTile label="AUC-ROC" value={fmt(m.auc_roc)} help="Ranking quality (≥ 0.75 target)" />
              <MetricTile label="Recall" value={fmt(m.recall)} help="Share of defaulters caught" />
              <MetricTile label="Precision" value={fmt(m.precision)} help="Share of flagged that default" />
              <MetricTile label="F1" value={fmt(m.f1)} help="Balance of precision and recall" />
            </div>
            <div className="card">
              <div className="card-head"><h2>Confusion matrix</h2><span className="hint">Held-out test set</span></div>
              <div className="card-body">
                <div className="table-wrap">
                  <table className="data-table" style={{ minWidth: 360 }}>
                    <thead>
                      <tr><th scope="col"></th><th scope="col" className="num">Predicted good</th><th scope="col" className="num">Predicted default</th></tr>
                    </thead>
                    <tbody>
                      <tr><td>Actual good</td><td className="num">{fmtInt(cm[0]?.[0])}</td><td className="num">{fmtInt(cm[0]?.[1])}</td></tr>
                      <tr><td>Actual default</td>
                        <td className="num" style={{ color: "var(--danger)", fontWeight: 600 }}>{fmtInt(cm[1]?.[0])}</td>
                        <td className="num">{fmtInt(cm[1]?.[1])}</td></tr>
                    </tbody>
                  </table>
                </div>
                <p style={{ marginTop: "var(--space-3)", fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                  False negatives (missed defaulters, lower-left) are the costliest error — the decision threshold
                  is cost-tuned to reduce them.
                </p>
              </div>
            </div>
          </>
        ) : (
          <div className="card"><div className="card-body">
            <EmptyState
              title="No champion metrics available"
              message="Once a model version is promoted to champion with recorded metrics, its AUC, recall, precision and confusion matrix appear here."
            />
          </div></div>
        )}
      </div>
    </>
  );
}

function fmt(v?: number) { return v == null ? "—" : v.toFixed(3); }
function fmtInt(v?: number) { return v == null ? "—" : v.toLocaleString("en-US"); }
