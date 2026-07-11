export function DisclaimerBar({ modelVersion }: { modelVersion?: string }) {
  return (
    <div className="border-b bg-amber-50 px-4 py-1.5 text-xs text-amber-900">
      Decision-support only — not a lending decision.
      {modelVersion && <span className="ml-2 text-amber-700">Model {modelVersion}</span>}
    </div>
  );
}
