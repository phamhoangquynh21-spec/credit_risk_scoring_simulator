import { PageHeader } from "@/components/PageHeader";
import { ExplainabilityPanels } from "@/components/ExplainabilityPanels";

export default function ExplainabilityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Explainability center"
        subtitle="What drives the model globally, and how a single score decomposes."
        context={[{ k: "Method", v: "SHAP TreeExplainer" }]}
      />
      <div className="content">
        <ExplainabilityPanels />
        <p style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", marginTop: "var(--space-5)", maxWidth: "78ch" }}>
          Global importance answers <em>“what does the model weigh overall?”</em>; the breakdown answers{" "}
          <em>“why did this applicant get this score?”</em>. Both read live from the model’s SHAP explainer, and
          contribution is never causation — a factor moving the score is not proof that changing it would change
          the outcome.
        </p>
      </div>
    </>
  );
}
