import type { NavIcon } from "@/lib/nav";

/* Stroke-based line icons matching the design mockups. Presentational only. */

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  strokeWidth: 1.8,
  "aria-hidden": true,
} as const;

export function NavGlyph({ name }: { name: NavIcon }) {
  switch (name) {
    case "grid":
      return (
        <svg {...base}>
          <rect x="3" y="3" width="7" height="9" /><rect x="14" y="3" width="7" height="5" />
          <rect x="14" y="12" width="7" height="9" /><rect x="3" y="16" width="7" height="5" />
        </svg>
      );
    case "search":
      return (<svg {...base}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></svg>);
    case "rows":
      return (<svg {...base}><path d="M3 6h18M3 12h18M3 18h18" /></svg>);
    case "scale":
      return (<svg {...base}><path d="M12 3v18M5 7l-3 6h6zM19 7l-3 6h6zM4 7h16" /></svg>);
    case "bulb":
      return (
        <svg {...base}>
          <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1h6c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2z" />
        </svg>
      );
    case "gauge":
      return (<svg {...base}><path d="M12 13l4-4M4 20a8 8 0 1 1 16 0" /><circle cx="12" cy="13" r="1.4" /></svg>);
  }
}

export function BrandMark() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 3v18h18" /><path d="M7 15l4-5 3 3 5-7" />
    </svg>
  );
}

export function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="12" r="9" /><path d="M12 8h.01M11 12h1v4h1" />
    </svg>
  );
}

export function WarnTriangle() {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} strokeLinecap="round" aria-hidden>
      <path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17h.01" />
    </svg>
  );
}

export function CheckIcon() {
  return (<svg viewBox="0 0 24 24" fill="none" strokeWidth={2} aria-hidden><path d="M20 6L9 17l-5-5" /></svg>);
}

export function ThemeIcon() {
  return (<svg {...base}><path d="M21 12.8A8 8 0 1 1 11.2 3a6 6 0 0 0 9.8 9.8z" /></svg>);
}

export function SignOutIcon() {
  return (<svg {...base}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></svg>);
}

export function ArrowUp() {
  return (<svg viewBox="0 0 24 24" fill="none" strokeWidth={2.2} aria-hidden><path d="M12 19V5m0 0l-6 6m6-6l6 6" /></svg>);
}
export function ArrowDown() {
  return (<svg viewBox="0 0 24 24" fill="none" strokeWidth={2.2} aria-hidden><path d="M12 5v14m0 0l6-6m-6 6l-6-6" /></svg>);
}
export function DashIcon() {
  return (<svg viewBox="0 0 24 24" fill="none" strokeWidth={2.2} aria-hidden><path d="M5 12h14" /></svg>);
}
export function DownloadIcon() {
  return (<svg {...base}><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16" /></svg>);
}
export function InboxIcon() {
  return (<svg {...base}><path d="M3 12h5l2 3h4l2-3h5M4 8l2-4h12l2 4v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" /></svg>);
}
