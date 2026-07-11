"use client";
import { bandColor, riskBand } from "@/lib/format";

type Factor = { friendly: string; contribution: number; direction: string };
export function ScoreResult({ score, modelVersion, factors }:
  { score: number; modelVersion: string; factors: Factor[] }) {
  const band = riskBand(score);
  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4">
        <div className="text-xs uppercase text-gray-500">Model output (prediction)</div>
        <div className="mt-1 flex items-baseline gap-3">
          <span className="text-3xl font-bold tabular-nums">{score.toFixed(1)}</span>
          <span className="rounded px-2 py-0.5 text-sm font-medium text-white"
            style={{ background: bandColor(band) }}>{band} risk</span>
        </div>
        <div className="mt-1 text-xs text-gray-400">Model {modelVersion} · SHAP contributions, not causal proof</div>
      </div>
      <div className="rounded-lg border p-4">
        <div className="mb-2 text-sm font-medium">Top contributing factors</div>
        <ul className="space-y-1 text-sm">
          {factors.map((f, i) => (
            <li key={i} className="flex justify-between">
              <span>{f.friendly}</span>
              <span className={f.contribution > 0 ? "text-red-600" : "text-green-600"}>
                {f.direction} risk
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded border border-dashed p-3 text-xs text-gray-500">
        Decision panel (human decision) — recording approve/refer/decline is a future release.
        This score is decision-support only.
      </div>
    </div>
  );
}
