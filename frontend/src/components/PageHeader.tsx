import { ThemeToggle } from "./ThemeToggle";

export type ContextItem = { k: string; v: string };

/* Shared page header: eyebrow + title + subtitle on the left, a provenance
   context strip + theme toggle + optional actions on the right. */
export function PageHeader({
  eyebrow,
  title,
  subtitle,
  context = [],
  actions,
}: {
  eyebrow: string;
  title: React.ReactNode;
  subtitle?: string;
  context?: ContextItem[];
  actions?: React.ReactNode;
}) {
  return (
    <header className="header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        {subtitle && <p className="sub">{subtitle}</p>}
      </div>
      <div className="context-strip">
        {context.map((c) => (
          <div className="context-item" key={c.k}>
            <span className="k">{c.k}</span>
            <span className="v">{c.v}</span>
          </div>
        ))}
        <div className="toolbar">
          <ThemeToggle />
          {actions}
        </div>
      </div>
    </header>
  );
}
