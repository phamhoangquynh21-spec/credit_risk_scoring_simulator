"use client";
import { useState } from "react";
import { defaultApplicant, type Applicant } from "@/lib/applicant";
import { ScoreResult } from "./ScoreResult";

const PAYS = ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"];

export function ApplicantForm() {
  const [a, setA] = useState<Applicant>(defaultApplicant());
  const [result, setResult] = useState<{ score: number; version: string; factors: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(k: string, v: number) { setA((p) => ({ ...p, [k]: v })); }

  async function submit() {
    setLoading(true); setError(null);
    try {
      const [p, e] = await Promise.all([
        fetch("/api/predict", { method: "POST", body: JSON.stringify(a) }).then(r => r.json()),
        fetch("/api/explain", { method: "POST", body: JSON.stringify(a) }).then(r => r.json()),
      ]);
      if (p.error) throw new Error(p.error);
      setResult({ score: p.risk_score, version: p.model_version ?? "—", factors: (e.top_factors ?? e.factors ?? []).slice(0, 5) });
    } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-3">
        <Num label="Credit limit" k="limit_bal" a={a} set={set} />
        <Num label="Age" k="age" a={a} set={set} />
        <Num label="Sex (1=M,2=F)" k="sex" a={a} set={set} />
        <Num label="Education (1-4)" k="education" a={a} set={set} />
        <Num label="Marriage (1-3)" k="marriage" a={a} set={set} />
        <div className="text-sm font-medium">Repayment status (−1 duly … 8 late)</div>
        <div className="grid grid-cols-3 gap-2">
          {PAYS.map((p) => <Num key={p} label={p} k={p} a={a} set={set} />)}
        </div>
        <button onClick={submit} disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50">
          {loading ? "Scoring…" : "Score applicant"}
        </button>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      </div>
      <div>{result
        ? <ScoreResult score={result.score} modelVersion={result.version} factors={result.factors} />
        : <p className="text-sm text-gray-400">Enter a profile and score to see the result.</p>}</div>
    </div>
  );
}

function Num({ label, k, a, set }:
  { label: string; k: string; a: Record<string, number>; set: (k: string, v: number) => void }) {
  return (
    <label className="block text-sm">
      <span className="text-gray-600">{label}</span>
      <input type="number" value={a[k]} onChange={(e) => set(k, Number(e.target.value))}
        className="mt-1 w-full rounded border px-2 py-1" />
    </label>
  );
}
