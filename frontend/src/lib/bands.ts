import { riskBand } from "./format";

export function bandCounts(scores: number[]) {
  const c = { Low: 0, Medium: 0, High: 0 };
  for (const s of scores) c[riskBand(s)]++;
  return c;
}
