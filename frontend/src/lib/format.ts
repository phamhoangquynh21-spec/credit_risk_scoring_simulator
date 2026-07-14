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

// Probability (0–1) → band, using the ML core's boundaries
// (Low < 0.20 · Medium 0.20–0.50 · High > 0.50).
export function probBand(p: number): Band {
  if (p < 0.2) return "Low";
  if (p <= 0.5) return "Medium";
  return "High";
}

export function pct(x: number, digits = 1): string {
  return `${(x * 100).toFixed(digits)}%`;
}

export function fmtInt(n: number): string {
  return n.toLocaleString("en-US");
}

// Compact UTC stamp like "2026-07-11 18:00 UTC" for provenance lines.
export function fmtUTC(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())} UTC`;
}
