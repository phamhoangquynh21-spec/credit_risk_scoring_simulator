export type Band = "Low" | "Medium" | "High";

export function riskBand(score: number): Band {
  if (score < 33) return "Low";
  if (score < 66) return "Medium";
  return "High";
}

// Returns the design-system risk-band color as a CSS custom-property reference
// (theme-aware). Callers use it as an SVG/CSS fill.
export function bandColor(band: string): string {
  return band === "Low"
    ? "var(--risk-low)"
    : band === "Medium"
    ? "var(--risk-medium)"
    : "var(--risk-high)";
}
