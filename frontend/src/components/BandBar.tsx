"use client";
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { bandColor } from "@/lib/format";

export function BandBar({ counts }: { counts: { Low: number; Medium: number; High: number } }) {
  const data = (["Low", "Medium", "High"] as const).map((b) => ({ band: b, count: counts[b] }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data}>
          <XAxis dataKey="band" /><YAxis allowDecimals={false} /><Tooltip />
          <Bar dataKey="count">
            {data.map((d) => <Cell key={d.band} fill={bandColor(d.band)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
