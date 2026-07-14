import { ArrowUp, ArrowDown, DashIcon } from "./icons";

type Delta = { dir: "up" | "down" | "neutral"; text: string; caption: string };

/* KPI metric tile: eyebrow label, mono value, and either a plain help caption
   or a delta (direction arrow + change + comparison period in words). A delta
   arrow never appears without its comparison period. */
export function MetricTile({
  label,
  value,
  help,
  delta,
  children,
}: {
  label: string;
  value: React.ReactNode;
  help?: string;
  delta?: Delta;
  children?: React.ReactNode;
}) {
  return (
    <div className="card metric">
      <div className="eyebrow">{label}</div>
      {children ?? <div className="val">{value}</div>}
      {delta ? (
        <div className="foot">
          <span className={`delta ${delta.dir}`}>
            {delta.dir === "up" ? <ArrowUp /> : delta.dir === "down" ? <ArrowDown /> : <DashIcon />}
            {delta.text}
          </span>
          {delta.caption}
        </div>
      ) : help ? (
        <div className="foot">{help}</div>
      ) : null}
    </div>
  );
}
