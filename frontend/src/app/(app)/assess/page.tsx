import { ApplicantForm } from "@/components/ApplicantForm";

export default function AssessPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Single Applicant Assessment</h1>
        <p className="text-sm text-gray-500">Score one applicant and see the factors behind it.</p>
      </div>
      <ApplicantForm />
    </div>
  );
}
