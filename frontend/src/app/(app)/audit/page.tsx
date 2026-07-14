import { PageHeader } from "@/components/PageHeader";
import { AuditTrail } from "@/components/AuditTrail";

export default function AuditPage() {
  return (
    <>
      <PageHeader
        eyebrow="Admin"
        title="Audit trail"
        subtitle="Append-only record of scoring, decisions, and governance actions. Exported from the ML service for governance and compliance."
        context={[{ k: "Source", v: "audit_logs" }]}
      />
      <div className="content">
        <AuditTrail />
      </div>
    </>
  );
}
