import { ApplicantForm } from "@/components/ApplicantForm";
import { PageHeader } from "@/components/PageHeader";

export default function AssessPage() {
  return (
    <>
      <PageHeader
        eyebrow="Assessment"
        title="Assess an applicant"
        subtitle="Enter the applicant's profile, review the model's estimate and its drivers, then record your decision."
      />
      <div className="content">
        <ApplicantForm />
      </div>
    </>
  );
}
