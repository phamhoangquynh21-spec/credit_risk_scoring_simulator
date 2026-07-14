import { PageHeader } from "@/components/PageHeader";
import { SystemHealth } from "@/components/SystemHealth";

export default function SystemPage() {
  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="System health"
        subtitle="Live liveness and readiness probes for the model scoring service."
        context={[{ k: "Service", v: "credit-risk-ml" }]}
      />
      <div className="content">
        <SystemHealth />
        <p style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-4)" }}>
          The scoring service sleeps when idle; the first probe after a quiet period may take up to a minute to
          return while it wakes.
        </p>
      </div>
    </>
  );
}
