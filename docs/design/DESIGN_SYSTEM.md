# Credit Risk Scoring Simulator — Design System

**Status:** design exploration for review — not wired to the backend
**Applies to:** the production dashboard (`frontend/`, Next.js 16 + Tailwind)
**Companion files:** [`tokens.css`](tokens.css) (drop-in CSS variables) · [`mockups/`](mockups/) (five static screens) · [`README.md`](README.md) (reviewer guide)

The product is a risk desk, not a consumer app. Every choice below optimizes for the same three
things: **numbers you can trust at a glance, provenance on every claim, and a hard visual line
between what the model says and what a human decides.**

---

## 1. Design direction

- **Personality:** institutional, calm, exact. Closer to a trading terminal's discipline than a
  marketing site's warmth, but with generous line-height and real labels — analysts read this for
  hours.
- **Signature element:** the **model-estimate / human-decision split**. Model output always sits in
  a card with a blue left border under a `MODEL ESTIMATE` tag; the decision form always sits in a
  separate card with a slate left border and sunken header under a `YOUR DECISION` tag. This is the
  one pattern a reviewer should remember after closing the tab.
- **Numbers are typographic events.** Every metric, probability, id, and timestamp is set in the
  mono face with tabular figures. Prose stays in the sans. The mono/sans split *is* the visual
  rhythm of the product — it lets the eye separate data from commentary without extra chrome.
- **Color is spent on risk, nothing else.** The chrome is neutral and navy; teal/amber/red appear
  only where risk or state is being communicated. When a screen looks colorful, something needs
  attention — that is the intent.

---

## 2. Color system

All values live in [`tokens.css`](tokens.css). Components must reference the semantic variables,
never raw hex.

### 2.1 Brand ramp (institutional azure)

| Token | Hex | Use |
|---|---|---|
| `--brand-50` | `#EEF3FB` | tinted fills |
| `--brand-100` | `#D8E4F5` | tinted fills |
| `--brand-200` | `#B3C9EC` | info borders |
| `--brand-300` | `#85A8DF` | — |
| `--brand-400` | `#5482CD` | — |
| `--brand-500` | `#2F63B4` | accent / chart-1 |
| `--brand-600` | `#1F4E97` | **primary** (buttons, active nav) |
| `--brand-700` | `#183E7A` | primary hover |
| `--brand-800` | `#14315F` | — |
| `--brand-900` | `#10264A` | — |
| `--brand-950` | `#0A1830` | sidebar background |

### 2.2 Neutral ramp (cool ink)

`--neutral-0 #FFFFFF · 25 #FBFCFE · 50 #F5F7FA · 100 #EDF1F6 · 200 #DFE5EE · 300 #C7D0DD ·
400 #9AA6B8 · 500 #6B7789 · 600 #4C5766 · 700 #374150 · 800 #232C39 · 900 #151C27 · 950 #0D131C`

Semantic aliases (light): `--color-bg: neutral-25`, `--color-surface: neutral-0`,
`--color-border: neutral-200`, `--color-text: neutral-900`, `--color-text-secondary: neutral-600`,
`--color-text-muted: neutral-500`.

### 2.3 Risk-band scale — the load-bearing decision

**Deliberately not green/amber/red.** Low is **teal**, which keeps a blue component and stays
separable from red under deuteranopia and protanopia; the three bands also step in lightness, so
they remain ordered in grayscale. Additionally, **color never carries the band alone**: badges
always pair the color with the band's text label and a leading dot/icon.

| Band | Light solid | Light surface / border / text | Dark solid | Dark surface / border / text |
|---|---|---|---|---|
| **Low** | `--risk-low: #0F766E` | `#E7F3F0` / `#B6DBD3` / `#0B5952` | `#34D3B7` | `#0E2A27` / `#1E4A44` / `#7BE7D4` |
| **Medium** | `--risk-medium: #B45309` | `#FBEFDD` / `#F0D3A6` / `#8A3F06` | `#F5B23E` | `#2E2411` / `#55431A` / `#F8CE82` |
| **High** | `--risk-high: #B42318` | `#FBE9E7` / `#F1C2BC` / `#8C1B12` | `#F98E80` | `#331A18` / `#5A2C28` / `#FBB3AA` |

Contrast, measured (WCAG relative-luminance formula): light solids on white — `#0F766E` 5.5:1,
`#B45309` 5.0:1, `#B42318` 6.6:1; dark solids on the dark surface `#121A24` — `#34D3B7` 9.3:1,
`#F5B23E` 9.4:1, `#F98E80` 7.7:1; band text-on-surface pairs all ≥6.6:1. The dark values are
lightened, desaturated variants — never the light hexes inverted.

Band boundaries shown in the UI (from the ML core): Low < 0.20 · Medium 0.20–0.50 · High > 0.50,
with the cost-tuned decision threshold (currently 0.31 for v2.3.1, FN:FP = 5:1) drawn as a separate
tick — bands and threshold are related but distinct concepts and the UI never conflates them.

### 2.4 Semantic states

| State | Light | Dark | Notes |
|---|---|---|---|
| `--success` | `#067647` | `#35C285` | reserved for system health / confirmations, **never** risk bands |
| `--warning` | `#B45309` | `#F5B23E` | shares risk-medium amber (one amber in the product) |
| `--danger` | `#B42318` | `#F98E80` | shares risk-high red |
| `--info` | `#1F4E97` | `#4E86D6` | model-provenance callouts |

### 2.5 SHAP contribution pair

`--contrib-up: #B42318` (pushes P(default) up) and `--contrib-down: #0F766E` (pushes it down) —
the same red/teal as the risk scale, so "red = more risk" is one consistent rule everywhere.
Bars are always signed, drawn from a zero line, and labeled with the numeric value.

### 2.6 Categorical chart palette

`--chart-1 #2F63B4 · --chart-2 #B45309 · --chart-3 #0F766E · --chart-4 #6D4AD1 ·
--chart-5 #A16207 · --chart-6 #64748B` (dark: `#4E86D6 · #F5B23E · #34D3B7 · #A78BFA · #D6A24E ·
#94A3B8`), plus `--chart-grid` and `--chart-axis`. Multi-series lines also vary line style
(solid/dashed), not color alone.

---

## 3. Typography

**Pairing: IBM Plex Sans (UI + prose) / IBM Plex Mono (all numerals, ids, timestamps, code).**
One superfamily, two voices: they share skeletons so the page reads as one product, while the mono
face gives figures the "ledger" precision a risk desk expects. In the Next.js app load both via
`next/font`; the static mockups fall back to the system stacks below with no layout surprises.

```css
--font-sans: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, "Segoe UI",
             Roboto, "Helvetica Neue", Arial, sans-serif;
--font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", "Cascadia Mono", "Segoe UI Mono",
             Consolas, "Liberation Mono", monospace;
```

Scale (rem at 16px root):

| Token | Size | Weight | Use |
|---|---|---|---|
| `--text-xs` | 12px | 600, uppercase, `+0.06em` tracking | eyebrows, table headers, meta lines |
| `--text-sm` | 13px | 400/500 | dense tables, secondary copy, buttons |
| `--text-base` | 15px | 400 | body / UI default |
| `--text-md` | 17px | 600 | card titles |
| `--text-lg` | 22px | 600 | page titles |
| `--text-xl` | 30px | 600 | display (rare) |
| `--text-metric` | 28px | 500 mono | KPI values |

Rules: numerals always `font-variant-numeric: tabular-nums`; body line-height 1.55; headings 1.25;
no font below 12px anywhere.

---

## 4. Spacing, radius, elevation, motion

- **Spacing** — 4pt grid, dashboard-dense: `--space-1..16` = 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px.
  Card padding `--space-5`, page gutter `--space-6`, grid gap `--space-4`.
- **Radius** — restrained: `--radius-sm 4px` (inputs’ focus), `--radius-md 6px` (controls),
  `--radius-lg 8px` (cards), `--radius-full 999px` (badges only). Nothing pill-shaped except badges.
- **Shadows** — `--shadow-xs` on resting cards; `--shadow-md` on menus/popovers; `--shadow-lg` on
  modals. Elevation communicates layering, never decoration.
- **Motion** — `--dur-fast 120ms` (hover), `--dur-base 180ms` (state changes), `--dur-slow 240ms`
  (panels), easing `--ease-out`. No entrance choreography, no animated numbers — a risk tool should
  feel settled. `prefers-reduced-motion` collapses everything to instant.
- **Layout** — fixed sidebar `--sidebar-width: 248px`; content `--content-max: 1360px`; sidebar
  collapses to a top bar below 860px; KPI grids step 4 → 2 → 1 columns.

---

## 5. Component direction

### Buttons
- **Primary** (`--color-primary` fill): exactly one per screen — the main verb ("Score applicant",
  "Record decision", "Export audit pack").
- **Ghost** (border + transparent): secondary actions.
- Danger styling is reserved for destructive verbs, not for "Decline" (a legitimate business
  outcome, presented neutrally so the UI never nudges the decision).
- 36–40px min height, visible focus ring (`--focus-ring`), disabled at 45% opacity with no hover.

### Cards & metric tiles
Card = `--color-surface`, 1px `--color-border`, `--radius-lg`, `--shadow-xs`, header row with title
+ context hint. Metric tile = eyebrow label, mono value (`--text-metric`), delta with direction
icon + comparison caption. A delta arrow never appears without its comparison period in words.

### Tables
Sunken uppercase header row; row hover `--color-surface-sunken`; numerics right-aligned mono with
tabular figures; ids in mono. Wide tables scroll inside their own container (`overflow-x: auto`,
`min-width` on the table) — the page body never scrolls horizontally. Every table states its result
count and sort order in plain words ("Showing 1–7 of 247 · sorted by P(default), highest first").

### Forms
Visible labels above fields (never placeholder-only); helper text under complex fields; required
marked with `*`; derived read-only fields visually sunken; errors in `--danger` text next to the
field with a recovery hint; radio-card group for the decision (Approve / Refer / Decline) with
equal visual weight.

### Badges (risk bands)
`badge-low/medium/high` = band surface + band border + band text token + leading dot + the word.
Never color-only, never icon-only. The same component renders the fairness Pass/Fail and system
states with the semantic tokens.

### Charts
- Trend = line (+20%-opacity area for volume); composition = stacked bar or donut (≤4 slices);
  SHAP = signed horizontal bars from a zero line; fairness = ratio bars with the 0.80 rule as an
  annotated reference line.
- Every chart: visible legend, axis units, `--chart-grid` gridlines lighter than the data, an
  `aria-label` sentence stating the takeaway, and a caption. Data tables offered on export.
- Empty / loading / error chart states are designed states (see §6), not blank axes.

### Prediction vs. decision (mandatory pattern)
1. **Model zone**: `MODEL ESTIMATE` tag (blue), card with 3px `--color-primary` left border.
   Contains probability, band, threshold scale, SHAP factors, the "contribution is not causation"
   callout, and the provenance meta line.
2. **Human zone**: `YOUR DECISION` tag (slate), card with 3px `--neutral-500` left border and a
   sunken header. Contains the action radio group, the required rationale field (audit-logged),
   and the record button. The system suggestion appears as a neutral badge — informative, not
   preselected styling that pressures agreement.
3. The two zones are separate cards with separate headings; a screen reader hits two distinct
   labeled sections.

### Disclaimer bar (mandatory)
Sticky, full-width, amber surface, on **every** screen:
*"Decision-support only. …"* + a screen-specific clause + "Synthetic demonstration data".
It is part of the shell, not a dismissible toast.

### Provenance meta line (mandatory on scoring surfaces)
A mono, muted line: `model: credit-default-xgb v2.3.1 · AUC 0.78 · data as of 2026-07-11 18:00 UTC
· prediction id`. Appears on every surface that shows a score.

---

## 6. UX acceptance rules

A screen ships only if all of these hold:

1. **Prediction ≠ decision.** Model output and human decision are visually and semantically
   separate zones (tags, borders, separate cards). Nothing in the model zone is clickable into an
   approval; the system never auto-approves or auto-declines.
2. **Provenance everywhere.** Every scoring surface shows model version, data-as-of timestamp, and
   the decision-support disclaimer.
3. **Contribution, not causation.** Any SHAP display carries the "contributed to the score, not
   causation" note. Copy uses "contributed to" language exclusively (test-guarded in Stage 3).
4. **Explicit empty / loading / error states.**
   - *Empty:* what's missing + the action to fill it ("No portfolios yet. Upload a CSV to score
     your first batch.").
   - *Loading:* skeleton tiles/rows (not spinners) for >300ms waits; the Render cold start gets
     honest copy: "First score after idle may take up to a minute while the scoring service wakes."
   - *Error:* what failed + a retry path; never a blank chart or a raw status code.
5. **Accessible risk color.** Band colors meet 4.5:1 in both themes; band/state is always
   color + label + shape; multi-series charts vary line style.
6. **Keyboard & focus.** Every interactive element reachable in visual order with a visible
   `--focus-ring`; tables sortable via keyboard; charts carry text alternatives (`aria-label`
   takeaway + caption); `prefers-reduced-motion` respected.
7. **No horizontal body scroll** at any width ≥360px; wide tables scroll in their own container.
8. **Calm failure language.** Errors and risk findings are stated factually with a next step —
   never alarm styling, never blame ("Age-group disparity is below the 0.80 threshold — review
   required", not "FAIRNESS VIOLATION!").

---

## 7. Voice & copy rules

- Plain verbs on controls: "Score applicant", "Record decision", "Export audit pack".
- The model "estimates" and "suggests"; people "decide". Never "the system approved".
- Numbers carry their unit and comparison in words next to them.
- Honest about limits, in the interface's own voice: synthetic data, detection-only fairness,
  cold-start latency are stated where the user meets them, not buried in a footer.
