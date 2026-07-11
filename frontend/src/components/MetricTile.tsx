export function MetricTile({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {help && <div className="mt-1 text-xs text-gray-400">{help}</div>}
    </div>
  );
}
