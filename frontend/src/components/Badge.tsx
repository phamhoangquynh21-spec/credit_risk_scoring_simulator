import type { Band } from "@/lib/format";
import { WarnTriangle, CheckIcon } from "./icons";

const BAND_CLASS: Record<Band, string> = {
  Low: "badge-low",
  Medium: "badge-medium",
  High: "badge-high",
};

/* Risk-band badge: color is always paired with a leading dot AND the band word,
   so the band never reads by color alone (colorblind-safe requirement). */
export function BandBadge({ band, suffix }: { band: Band; suffix?: string }) {
  return (
    <span className={`badge ${BAND_CLASS[band]}`}>
      <span className="dot" aria-hidden />
      {band}{suffix ? ` ${suffix}` : ""}
    </span>
  );
}

/* Pass/Fail badge for the four-fifths rule and similar checks. Icon + word. */
export function StatusBadge({ status }: { status: "pass" | "fail" }) {
  return status === "pass" ? (
    <span className="badge badge-ok"><CheckIcon />Passes</span>
  ) : (
    <span className="badge badge-warn"><WarnTriangle />Fails</span>
  );
}

/* Neutral informational badge (e.g. "Awaiting", "System suggests: Refer"). */
export function NeutralBadge({ children }: { children: React.ReactNode }) {
  return <span className="badge badge-neutral">{children}</span>;
}
