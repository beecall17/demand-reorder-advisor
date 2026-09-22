# ADR-0003: MLflow from v1, local SQLite backend, on the same training notebook

**Status:** accepted

## Context
The roadmap placed MLflow experiment tracking in v1 (not deferred to v3) as
the data-science-track counterpart to Langfuse on the agent track. The
Prophet models were already trained and backtested in
`notebooks/02_prophet_forecast_model.ipynb` without tracking wired in, so
this was added retroactively to the same notebook rather than treated as
separate new scope.

While implementing, `mlflow.set_tracking_uri("file:./mlruns")` failed
outright: the installed MLflow version has put the plain filesystem
tracking backend into maintenance mode and refuses new writes, requiring a
database backend even for fully local, single-user use.

## Decision
Use MLflow Tracking with a local SQLite backend
(`sqlite:///mlflow.db`) and an explicit, absolute artifact location
(`REPO_ROOT/mlartifacts`) -- still zero external infra and zero cost, just
a different local file format than originally planned. One run per
batch-training pass (not one per store-item model) logs params, per-category
backtest metrics, and summary-table artifacts. The Model Registry is not
used in v1 -- 500 separate per-series models don't map cleanly onto its
single-model abstraction without an artificial wrapper; a `model_family`
tag on the run is the lightweight substitute.

## Consequences
- No behavior change from the original plan at the "local, no server, free"
  level -- SQLite is still one file on disk.
- Caught twice during implementation, and both fixes are now load-bearing
  conventions, not one-off patches: (1) MLflow's default artifact location
  resolves relative to process cwd, which silently nested artifacts under
  `notebooks/mlartifacts` when run from a notebook -- fixed by passing an
  absolute `artifact_location` at experiment creation, the same class of
  fix already applied to `data.py`/`forecast.py`'s path handling. (2)
  Re-running the cell-append script against an already-modified notebook
  duplicated the MLflow section and logged two runs instead of one --
  fixed by rebuilding the notebook from its original source before
  reapplying the change, not patching a patched file.
- `mlflow ui --backend-store-uri sqlite:///mlflow.db` from the repo root
  browses results locally.
- If the MLflow <-> Langfuse link (run ID passed as span metadata) is
  needed once the agent exists, both systems are now confirmed working
  locally and ready to be cross-referenced.
