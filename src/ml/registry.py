"""MLflow model registry (Stage 3.1).

``mlflow`` is imported LAZILY inside every function so importing ``src.ml`` (or
this module) never requires mlflow — serving/deploy stay unaffected and the new
dependency lives only in ``requirements-train.txt``. Runs are logged to a local
file store under ``mlruns/`` at the project root; the resulting run_id is
threaded into the ``model_versions.metrics`` JSON (key ``mlflow_run_id``) so no
new DB column/migration is needed.
"""
from __future__ import annotations

from .. import config

# Local file-based tracking store — no MLflow server required.
MLFLOW_TRACKING_DIR = config.PROJECT_ROOT / "mlruns"
EXPERIMENT_NAME = "credit_risk_scoring"
RUN_ID_METRIC_KEY = "mlflow_run_id"


def _tracking_uri() -> str:
    """file:// URI for the local mlruns/ store."""
    return MLFLOW_TRACKING_DIR.as_uri()


def log_training_run(params: dict, metrics: dict,
                     artifact_path: str | None) -> str:
    """Log a training run to the local MLflow file store; return its run_id.

    Logs ``params`` and ``metrics`` and, when ``artifact_path`` is given, the
    artifact file. mlflow is imported lazily.
    """
    import mlflow

    mlflow.set_tracking_uri(_tracking_uri())
    mlflow.set_experiment(EXPERIMENT_NAME)
    with mlflow.start_run() as run:
        if params:
            mlflow.log_params(params)
        if metrics:
            mlflow.log_metrics(metrics)
        if artifact_path:
            mlflow.log_artifact(artifact_path)
        return run.info.run_id


def register_from_training(semver, algo, metrics: dict, trained_on, threshold,
                           run_id, stage="staging", client=None) -> dict:
    """Register a model version, storing the MLflow run_id inside the metrics.

    The run_id is placed under ``metrics[RUN_ID_METRIC_KEY]`` so the existing
    ``model_versions.metrics`` JSON column carries the MLflow linkage without a
    schema change. Delegates the insert to ``src.db.register_model_version``.
    """
    from .. import db

    enriched = {**metrics, RUN_ID_METRIC_KEY: run_id}
    return db.register_model_version(
        semver, algo, enriched, trained_on, threshold,
        stage=stage, client=client,
    )
