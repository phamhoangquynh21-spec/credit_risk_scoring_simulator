import { InfoIcon } from "./icons";

/* Mandatory, persistent decision-support disclaimer. Part of the shell on every
   screen — not dismissible. `clause` is the optional screen-specific sentence. */
export function DisclaimerBar({ clause }: { clause?: string }) {
  return (
    <div className="disclaimer" role="note">
      <InfoIcon />
      <span>
        <strong>Decision-support only.</strong>{" "}
        {clause ??
          "This platform estimates and explains risk. It never approves or declines credit — a person makes every lending decision."}
      </span>
      <span className="sep">·</span>
      <span>Synthetic demonstration data</span>
    </div>
  );
}
