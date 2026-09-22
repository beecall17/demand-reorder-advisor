"""MLflow experiment tracking for the forecasting model. See
skills/mlflow-tracking-patterns.md before editing this file.

Local SQLite backend for v1 -- no server to run, no cost. NOTE: MLflow's
plain filesystem store ('file:./mlruns') is in maintenance mode as of the
installed version and refuses new writes -- a database backend is required
even for fully local use. SQLite is still just one file on disk, so this
doesn't change the "no infra" nature of the v1 decision, only the URI
scheme. Deliberately does NOT log the 500 Prophet model JSON files as
MLflow artifacts (that would duplicate ~130MB of storage for no benefit) --
instead the run is tagged with the models/ directory path so it stays
traceable without duplicating the artifacts themselves.
"""
from pathlib import Path

import mlflow
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "mlflow.db"
EXPERIMENT_NAME = "prophet-demand-forecast"


def init() -> None:
    mlflow.set_tracking_uri(f"sqlite:///{DB_PATH}")
    # mlflow.set_experiment() alone resolves a relative default artifact
    # location against the process cwd (same class of bug fixed in
    # data.py/forecast.py) -- create the experiment with an explicit,
    # absolute artifact_location the first time so it doesn't end up
    # nested under notebooks/ when run from there.
    existing = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if existing is None:
        artifact_location = f"file://{REPO_ROOT / 'mlartifacts'}"
        mlflow.create_experiment(EXPERIMENT_NAME, artifact_location=artifact_location)
    mlflow.set_experiment(EXPERIMENT_NAME)


def _safe_metric_name(label: str) -> str:
    """MLflow metric names must be simple identifiers -- 'winter (parka)'
    becomes 'winter'."""
    return label.split(" ")[0].strip("()").lower()


def log_batch_run(
    prophet_kwargs: dict,
    holdout_days: int,
    backtest_summary: pd.DataFrame,
    batch_summary: pd.DataFrame,
    model_dir: Path,
    extra_artifacts: list[Path] | None = None,
) -> str:
    """One MLflow run per batch-training pass. Returns the run ID.

    backtest_summary: columns [item, category, wape, mae] -- from the
        representative-series backtest.
    batch_summary: columns [store, item, n_days, mean_daily_sales, artifact]
        -- from forecast.batch_train_all().
    """
    init()
    tmp_dir = REPO_ROOT / "mlruns_tmp_artifacts"
    tmp_dir.mkdir(exist_ok=True)

    with mlflow.start_run(run_name="batch_train_all") as run:
        mlflow.log_params({
            **prophet_kwargs,
            "holdout_days": holdout_days,
            "n_series": len(batch_summary),
        })

        for _, row in backtest_summary.iterrows():
            name = _safe_metric_name(row["category"])
            mlflow.log_metric(f"wape_{name}", row["wape"])
            mlflow.log_metric(f"mae_{name}", row["mae"])

        mlflow.log_metric("wape_mean_representative", backtest_summary["wape"].mean())
        mlflow.log_metric("mean_daily_sales_all_series", batch_summary["mean_daily_sales"].mean())
        mlflow.log_metric("n_models_trained", len(batch_summary))

        bt_path = tmp_dir / "backtest_summary.csv"
        batch_path = tmp_dir / "batch_summary.csv"
        backtest_summary.to_csv(bt_path, index=False)
        batch_summary.to_csv(batch_path, index=False)
        mlflow.log_artifact(str(bt_path))
        mlflow.log_artifact(str(batch_path))

        for p in (extra_artifacts or []):
            mlflow.log_artifact(str(p))

        mlflow.set_tag("model_family", "prophet-demand-v1")
        mlflow.set_tag("model_artifact_dir", str(model_dir.relative_to(REPO_ROOT)))

        return run.info.run_id
