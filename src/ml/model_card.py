"""Auto-generated model cards (Stage 7.2).

Builds a Markdown model card from the live model registry + latest fairness
results via the public ``src.db`` API. Read-only: no training, no DB writes.
A card is generated per model version so governance has a standing, auditable
record of what each version is, how it performs, and how it behaves across
protected groups.
"""
from __future__ import annotations

from pathlib import Path

from src import config
from src.db import get_latest_run_results, get_model_version

DECISION_SUPPORT_DISCLAIMER = (
    "This model is a DECISION-SUPPORT tool only. Its scores and explanations "
    "inform a human credit decision; they do not make one. Feature "
    "contributions are not proof of causation, and the model must not be used "
    "as the sole basis for an adverse action."
)

FOUR_FIFTHS = 0.8

MODEL_CARDS_DIR = config.REPORTS_DIR / "model_cards"


def _metrics_lines(metrics: dict) -> list[str]:
    """Render the metrics jsonb as a flat bullet list (skips the mlflow ref)."""
    lines = []
    for key, value in metrics.items():
        if key == "mlflow_run_id":
            continue
        if isinstance(value, dict):
            lines.append(f"- **{key}:**")
            for sub_key, sub_value in value.items():
                lines.append(f"  - {sub_key}: {sub_value}")
        else:
            lines.append(f"- **{key}:** {value}")
    return lines or ["- _(no metrics recorded)_"]


def _fairness_lines(results: list[dict]) -> list[str]:
    """Render fairness results as a table, flagging groups below the 0.8 rule."""
    if not results:
        return ["_No fairness run recorded for this model version._"]
    lines = [
        "| Attribute | Group | n | Selection rate | Recall | Precision | Disparity ratio | 0.8 rule |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in results:
        ratio = row.get("disparity_ratio")
        passes = "—" if ratio is None else ("PASS" if ratio >= FOUR_FIFTHS else "**FAIL**")
        lines.append(
            f"| {row.get('attribute','')} | {row.get('grp','')} | {row.get('n','')} "
            f"| {row.get('selection_rate','')} | {row.get('recall','')} "
            f"| {row.get('precision','')} | {ratio} | {passes} |"
        )
    return lines


def generate_model_card(semver, client=None) -> str:
    """Return a Markdown model card for ``semver`` (raises if it does not exist)."""
    mv = get_model_version(semver, client=client)
    if mv is None:
        raise ValueError(f"model version {semver!r} not found")
    metrics = mv.get("metrics") or {}
    fairness = get_latest_run_results(mv["id"], client=client)

    lines = [
        f"# Model Card — {mv['semver']}",
        "",
        f"- **Algorithm:** {mv.get('algo', '')}",
        f"- **Lifecycle stage:** {mv.get('stage', '')}",
        f"- **Decision threshold:** {mv.get('threshold', '')}",
        f"- **Trained on:** {mv.get('trained_on', '')}",
    ]
    if mv.get("approved_by"):
        lines.append(f"- **Governance approver:** {mv['approved_by']}")
    if metrics.get("mlflow_run_id"):
        lines.append(f"- **MLflow run:** {metrics['mlflow_run_id']}")
    lines.append(f"- **Created:** {mv.get('created_at', '')}")
    lines += [
        "",
        "## Metrics",
        *_metrics_lines(metrics),
        "",
        "## Intended use & limitations",
        "",
        DECISION_SUPPORT_DISCLAIMER,
        "",
        "## Fairness (four-fifths / 0.8 rule)",
        "",
        *_fairness_lines(fairness),
        "",
    ]
    return "\n".join(lines)


def save_model_card(semver, path=None, client=None) -> Path:
    """Write the model card to ``reports/model_cards/<semver>.md`` (or ``path``)."""
    card = generate_model_card(semver, client=client)
    out = Path(path) if path is not None else MODEL_CARDS_DIR / f"{semver}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(card, encoding="utf-8")
    return out
