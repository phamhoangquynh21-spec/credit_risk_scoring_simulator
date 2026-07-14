"use client";
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";

export type TrendPoint = { label: string; volume: number; highRiskPct: number };

/* Trailing monthly trend: scoring volume (area+line) and high-risk share (line).
   Two series distinguished by BOTH color and line style (dashed vs solid) so the
   chart reads without color. Carries an aria-label takeaway + caption. */
export function TrendChart({
  data,
  ariaLabel,
  caption,
}: {
  data: TrendPoint[];
  ariaLabel: string;
  caption: string;
}) {
  return (
    <figure>
      <div className="legend" style={{ marginBottom: "var(--space-4)" }}>
        <span className="k"><span className="swatch" style={{ background: "var(--chart-3)" }} />Accounts scored</span>
        <span className="k"><span className="swatch" style={{ background: "var(--chart-1)" }} />High-risk share (%)</span>
      </div>
      <div style={{ width: "100%", height: 240 }} role="img" aria-label={ariaLabel}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -8 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
              tickLine={false} axisLine={{ stroke: "var(--chart-grid)" }} />
            <YAxis yAxisId="vol" tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
              tickLine={false} axisLine={false} allowDecimals={false} width={40} />
            <YAxis yAxisId="pct" orientation="right" tick={{ fill: "var(--chart-axis)", fontSize: 11 }}
              tickLine={false} axisLine={false} width={40} unit="%" />
            <Tooltip
              contentStyle={{
                background: "var(--color-surface)", border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)", fontSize: "var(--text-xs)", color: "var(--color-text)",
              }}
            />
            <Area yAxisId="vol" type="monotone" dataKey="volume" name="Accounts scored"
              stroke="var(--chart-3)" strokeWidth={2} strokeDasharray="5 4"
              fill="var(--chart-3)" fillOpacity={0.14} />
            <Line yAxisId="pct" type="monotone" dataKey="highRiskPct" name="High-risk share (%)"
              stroke="var(--chart-1)" strokeWidth={2.5} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  );
}
