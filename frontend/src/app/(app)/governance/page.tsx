import { createServerSupabase } from "@/lib/supabase/server";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/states";
import { PromoteControl } from "@/components/PromoteControl";

export const dynamic = "force-dynamic";

type ModelVersion = {
  semver: string;
  algo: string;
  stage: string;
  metrics: Record<string, number>;
  threshold: number;
  trained_on: string;
  created_at: string;
};

const STAGE_BADGE: Record<string, string> = {
  champion: "badge-ok",
  staging: "badge-warn",
  dev: "badge-neutral",
  retired: "badge-neutral",
};

export default async function GovernancePage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  const { data: profile } = user
    ? await supabase.from("profiles").select("role").eq("user_id", user.id).maybeSingle()
    : { data: null };
  const role = profile?.role ?? "analyst";
  const isGov = role === "governance" || role === "admin";

  const { data: versions } = await supabase
    .from("model_versions")
    .select("semver, algo, stage, metrics, threshold, trained_on, created_at")
    .order("created_at", { ascending: false });
  const rows = (versions ?? []) as ModelVersion[];

  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="Model governance"
        subtitle="The model registry: every version, its lifecycle stage, and its recorded metrics. Promotion is governance-gated and audit-logged."
        context={[{ k: "Your role", v: role }]}
      />
      <div className="content">
        {rows.length ? (
          <div className="grid" style={{ gap: "var(--space-4)" }}>
            {rows.map((mv) => {
              const m = mv.metrics ?? {};
              return (
                <div className="card" key={mv.semver}>
                  <div className="card-head">
                    <h2 className="mono">{mv.semver}</h2>
                    <span className={`badge ${STAGE_BADGE[mv.stage] ?? "badge-neutral"}`}>{mv.stage}</span>
                  </div>
                  <div className="card-body">
                    <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "var(--space-4)", margin: 0 }}>
                      <Field k="Algorithm" v={mv.algo} />
                      <Field k="AUC-ROC" v={num(m.auc_roc)} mono />
                      <Field k="Recall" v={num(m.recall)} mono />
                      <Field k="Precision" v={num(m.precision)} mono />
                      <Field k="Threshold" v={mv.threshold?.toFixed(2) ?? "—"} mono />
                      <Field k="Trained on" v={mv.trained_on ?? "—"} />
                    </dl>
                    {isGov && mv.stage !== "retired" && (
                      <div style={{ marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px solid var(--color-border)" }}>
                        <PromoteControl semver={mv.semver} currentStage={mv.stage} />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="card"><div className="card-body">
            <EmptyState title="No model versions registered" message="Trained model versions appear here once they are recorded in the registry." />
          </div></div>
        )}
        {!isGov && (
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-4)" }}>
            Promotion controls are available to the governance role only. You are viewing the registry read-only.
          </p>
        )}
      </div>
    </>
  );
}

function Field({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <dt className="eyebrow">{k}</dt>
      <dd className={mono ? "mono" : undefined} style={{ margin: "2px 0 0", fontSize: "var(--text-sm)", color: "var(--color-text)" }}>{v}</dd>
    </div>
  );
}
function num(v?: number) { return v == null ? "—" : v.toFixed(3); }
