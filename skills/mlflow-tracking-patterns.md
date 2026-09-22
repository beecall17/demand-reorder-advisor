# Skill: MLflow tracking patterns

Load this before editing src/demand_advisor/tracking.py or the batch
training cell in notebooks/02_prophet_forecast_model.ipynb.

## Scope for v1
Local SQLite backend (`sqlite:///mlflow.db`) -- no server to run, no cost.
Note: MLflow's plain filesystem store (`file:./mlruns`) is in maintenance
mode as of the installed version and rejects new writes -- a database
backend is required even for fully local, single-user use. SQLite is still
just one file on disk, so this doesn't change the "no infra" nature of the
decision. Browse results with `mlflow ui --backend-store-uri
sqlite:///mlflow.db` from the repo root.

## What gets logged, and what doesn't
- Log: prophet params, per-category backtest WAPE/MAE, aggregate stats,
  the summary tables as CSV artifacts.
- Do NOT log the 500 Prophet model JSON files (~130MB) as MLflow
  artifacts -- that duplicates storage for no benefit. Instead tag the run
  with the model directory's relative path (`model_artifact_dir`) so it
  stays traceable without duplication.

## One run per batch-training pass
Not one run per (store, item) -- 500 runs would make the MLflow UI useless
for comparison. `tracking.log_batch_run()` takes the already-computed
backtest and batch summaries and logs one run that represents the whole
pass.

## Model Registry
Deliberately not used in v1. Prophet's 500 separate per-series models don't
map cleanly onto MLflow's single-model registry abstraction without an
artificial pyfunc wrapper that adds complexity without adding value here.
The `model_family` tag on each run (e.g. `prophet-demand-v1`) is the
lightweight substitute -- revisit real registry usage only if a documented
v1/v2 limitation specifically calls for it.

## The MLflow <-> Langfuse link
If the agent's forecast-lookup tool ever needs to reference which model
version produced a given forecast, pass the MLflow run ID through as
metadata on the corresponding Langfuse span -- don't let the two systems
drift apart with no way to trace an agent decision back to a model version.
