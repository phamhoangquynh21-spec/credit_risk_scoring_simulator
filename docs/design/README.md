# Design exploration — reviewer guide

**For:** Adam
**What this is:** a design system + five static, self-contained HTML mockups for the production
dashboard. Nothing here touches `frontend/` or talks to a backend — open the files, click around,
and decide what sticks before any implementation work starts.

**How to review:** open any file in `mockups/` directly in a browser (no server needed). The
sidebar links navigate between the five screens. The "Theme" button in each header flips dark mode.
Resize the window — everything works down to phone width, and wide tables scroll inside their own
frame instead of breaking the page.

---

## Why it looks the way it does

A credit-risk tool earns trust differently from a consumer app. The choices that matter:

- **One hard rule made visible.** The platform's non-negotiable — predictions are not decisions —
  is a *layout* rule here, not a footnote. Model output always sits in a blue-edged "Model
  estimate" card; the human decision is a separate slate-edged "Your decision" card with its own
  heading. Screen 02 shows the full pattern.
- **Risk colors that survive colorblindness and dark mode.** Low is teal (not green) so it stays
  separable from red under the common color-vision deficiencies; the three bands also step in
  lightness, and a badge always carries the band's name in text. Light and dark values are tuned
  separately — all pairs measure ≥4.5:1 (most ≥5:1).
- **Two typefaces, two jobs.** IBM Plex Sans for prose and labels, IBM Plex Mono for every number,
  id, and timestamp. Figures line up in tables, probabilities read like ledger entries, and the
  eye can tell data from commentary instantly.
- **Provenance on every score.** Model version, AUC, data-as-of, and prediction id ride along as a
  quiet mono meta-line wherever a score appears — the habit examiners expect.
- **Calm, honest failure language.** The fairness page states a failing audit as a fact with a
  next step. The cold-start delay on the free Render tier is told to the user in plain words on
  the scoring form. No alarm styling, no over-promising.
- **Almost no motion.** Hovers and state changes at 120–180ms, nothing else animates. A risk desk
  should feel settled.

Details and exact values: [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md). Drop-in variables:
[`tokens.css`](tokens.css).

---

## The screens

| File | One line |
|---|---|
| `mockups/01-executive-overview.html` | KPI tiles (default rate, approvals, AUC, fairness status), trend chart, band mix, audit-trail activity — the executive's morning glance. |
| `mockups/02-single-applicant-assessment.html` | Applicant form → probability + band + cost-tuned threshold scale + SHAP factors, then the separated human-decision card. The flagship screen. |
| `mockups/03-portfolio-risk-monitor.html` | Filterable portfolio table with band badges, donut band mix, and band-by-utilisation segments — the risk manager's working view. |
| `mockups/04-fairness-responsible-ai.html` | Per-group disparity table, 0.80-rule status banner (age-group 0.599 finding disclosed), ratio chart with the rule line — the compliance view. |
| `mockups/05-explainability-center.html` | Global feature importance + a single prediction's SHAP waterfall from baseline 0.221 to score 0.382. |

Sample data is consistent across screens (portfolio "Q3-Demo-Book", applicant `APP-2024-10491`,
prediction `pr_9f3ce2`, model `credit-default-xgb v2.3.1`, threshold 0.31) and obviously synthetic.

---

## Open design questions for Adam

1. **Threshold "0.31".** The mockups render the cost-tuned threshold (FN:FP = 5:1) as `0.31` to
   make the scale readable. The real value comes out of Stage 3 calibration — fine to treat the
   number as placeholder, but should the UI show the threshold at all to analysts, or only to
   manager/compliance roles?
2. **Decision framing.** "Approve / Refer / Decline" render with equal visual weight so the UI
   never nudges. An alternative is to visually de-emphasize whichever option contradicts the
   system suggestion — more guidance, more nudge. Which posture do you want?
3. **Disclaimer bar density.** It's persistent and sticky on every screen. On small screens it
   costs real estate. Keep it always visible, or allow it to collapse to an icon after first view
   per session (it would still print on exports)?
4. **IBM Plex delivery.** The design assumes IBM Plex Sans/Mono via `next/font` (self-hosted,
   no CDN at runtime). The mockups use system fallbacks. Confirm you're happy adding the font
   files to the repo (~300KB woff2 total).
5. **Proposed, not in scope yet:** a compact "model card" popover when clicking the model-version
   chip (metrics, training data, approval), and an override-rate tile on the executive screen fed
   by `override_logs`. Both fit the schema but are new UI surface — flagging rather than baking in.
6. **Dark mode default.** Currently the OS preference wins with a manual toggle. Risk desks often
   prefer forced-light for print parity. Preference?

---

## What implementation would take

- Copy `tokens.css` into `frontend/src/app/` and import it in the root layout; map Tailwind theme
  colors to the CSS variables.
- The mockups' component patterns map 1:1 onto the existing components (`MetricTile`, `ScoreResult`,
  `DisclaimerBar`, `Sidebar`) — this is a restyle plus the new screens, not a rebuild.
- Charts: everything shown is achievable with plain SVG or Recharts; no heavy chart dependency
  required.
