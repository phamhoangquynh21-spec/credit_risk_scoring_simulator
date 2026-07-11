export type Band = "Low" | "Medium" | "High";

export function riskBand(score: number): Band {
  if (score < 33) return "Low";
  if (score < 66) return "Medium";
  return "High";
}

export function bandColor(band: string): string {
  return band === "Low" ? "#16a34a" : band === "Medium" ? "#d97706" : "#dc2626";
}
