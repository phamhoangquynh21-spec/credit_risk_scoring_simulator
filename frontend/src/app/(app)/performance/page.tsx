import { createServerSupabase } from "@/lib/supabase/server";
import { MetricTile } from "@/components/MetricTile";

export default async function PerformancePage() {
  const supabase = await createServerSupabase();
  const { data: champ } = await supabase.from("model_versions")
    .select("semver, algo, metrics").eq("stage", "champion").limit(1).single();
  const m = (champ?.metrics ?? {}) as Record<string, number>;
  const cm = (m.confusion_matrix as unknown as number[][]) ?? [[0, 0], [0, 0]];
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Model Performance</h1>
        <p className="text-sm text-gray-500">
          Champion: {champ?.semver} ({champ?.algo}) · target AUC ≥ 0.75
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricTile label="AUC-ROC" value={fmt(m.auc_roc)} help="Ranking quality (≥0.75 target)" />
        <MetricTile label="Recall" value={fmt(m.recall)} help="Defaulters caught" />
        <MetricTile label="Precision" value={fmt(m.precision)} />
        <MetricTile label="F1" value={fmt(m.f1)} />
      </div>
      <div>
        <h2 className="mb-2 text-sm font-medium">Confusion matrix (test set)</h2>
        <table className="text-sm">
          <tbody>
            <tr><td className="p-2 text-gray-500">TN {cm[0]?.[0]}</td><td className="p-2">FP {cm[0]?.[1]}</td></tr>
            <tr><td className="p-2 font-medium text-red-600">FN {cm[1]?.[0]}</td><td className="p-2">TP {cm[1]?.[1]}</td></tr>
          </tbody>
        </table>
        <p className="mt-1 text-xs text-gray-400">False negatives (missed defaulters) are the costliest error.</p>
      </div>
    </div>
  );
}

function fmt(v?: number) { return v == null ? "—" : v.toFixed(3); }
