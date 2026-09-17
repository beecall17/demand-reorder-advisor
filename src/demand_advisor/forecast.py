"""Prophet training, backtesting, and artifact I/O for one (store, item)
series at a time. See skills/forecasting-model-io.md before editing this
file -- the model and its preprocessing must stay versioned as a pair.

Serialization uses Prophet's own model_to_json/model_from_json, not raw
pickle -- Prophet's docs recommend this specifically because raw-pickled
models can break across pandas/numpy version upgrades, while the JSON
format is stable. This is the one exception to the project's general
joblib/pickle convention, and it's a deliberate one.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_from_json, model_to_json

# Resolved relative to the repo root (this file's location), not the
# process cwd -- see the same note in data.py. Notebooks run with cwd set
# to their own folder, which would otherwise silently nest this under
# notebooks/models/.
REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "models" / "prophet"


# def to_prophet_frame(df: pd.DataFrame, store: int, item: int) -> pd.DataFrame:
#     """Preprocessing step -- the 'feature pipeline' half of the artifact
#     pair. Must be reused identically at inference time; never re-derive
#     this by hand elsewhere.
#     """
#     series = df[(df["store"] == store) & (df["item"] == item)]
#     out = series[["date", "sales"]].rename(columns={"date": "ds", "sales": "y"})
#     return out.sort_values("ds").reset_index(drop=True)


def train(prophet_df: pd.DataFrame, **prophet_kwargs) -> Prophet:
    defaults = dict(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
    )
    defaults.update(prophet_kwargs)
    model = Prophet(**defaults)
    model.fit(prophet_df)
    return model


def wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Absolute Percentage Error -- robust to the many
    near-zero-sales days a per-store-item series has, unlike plain MAPE
    which blows up when actuals are near zero.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return float("nan")
    return float(np.sum(np.abs(y_true - y_pred)) / denom)


def backtest(prophet_df: pd.DataFrame, holdout_days: int = 90, **prophet_kwargs) -> dict:
    """Time-based split: train on everything before the holdout window,
    forecast across it, score against the actuals. Never use a random
    split on time series data -- it leaks future information into training.
    """
    cutoff = prophet_df["ds"].max() - pd.Timedelta(days=holdout_days)
    train_df = prophet_df[prophet_df["ds"] <= cutoff]
    test_df = prophet_df[prophet_df["ds"] > cutoff]

    model = train(train_df, **prophet_kwargs)
    future = model.make_future_dataframe(periods=holdout_days, freq="D")
    forecast = model.predict(future)

    merged = test_df.merge(forecast[["ds", "yhat"]], on="ds", how="left")
    merged["yhat"] = merged["yhat"].clip(lower=0)

    return {
        "model": model,
        "forecast": forecast,
        "wape": wape(merged["y"], merged["yhat"]),
        "mae": float(np.mean(np.abs(merged["y"] - merged["yhat"]))),
        "test_df": merged,
    }


def save_model(model: Prophet, store: int, item: int, path: Path = MODEL_DIR) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    fp = path / f"store_{store}_item_{item}.json"
    fp.write_text(model_to_json(model))
    return fp


def load_model(store: int, item: int, path: Path = MODEL_DIR) -> Prophet:
    fp = path / f"store_{store}_item_{item}.json"
    return model_from_json(fp.read_text())


# def batch_train_all(df: pd.DataFrame, path: Path = MODEL_DIR, **prophet_kwargs) -> pd.DataFrame:
#     """Trains and saves one model per (store, item) combination on the
#     FULL history (no holdout) -- the backtest for accuracy reporting is a
#     separate step with its own held-out window. Returns a small summary
#     frame, not the fitted models themselves, to keep memory bounded while
#     training 500 series.
#     """
#     rows = []
#     combos = df[["store", "item"]].drop_duplicates().itertuples(index=False)
#     for store, item in combos:
#         # 1. Filter data for the current store and item combination
#         sub_df = df[(df["store"] == store) & (df["item"] == item)].copy()
#         sub_df = sub_df.rename(columns={"date": "ds", "sales": "y"})

#         # 2. Train and save using the filtered subset
#         model = train(sub_df, **prophet_kwargs)
#         fp = save_model(model, store, item, path)

#         # 3. Record metrics based on the specific series subset
#         rows.append(
#             {
#                 "store": store,
#                 "item": item,
#                 "n_days": len(sub_df),
#                 "mean_daily_sales": sub_df["y"].mean() if "y" in sub_df.columns else None,
#                 "artifact": str(fp),
#             }
#         )

#     return pd.DataFrame(rows)


def batch_train_all(df: pd.DataFrame, path: Path = MODEL_DIR, **prophet_kwargs) -> pd.DataFrame:
    """Trains and saves one model per (store, item) combination on the
    FULL history (no holdout). Returns a summary dataframe.
    """
    rows = []
    combos = df[["store", "item"]].drop_duplicates().itertuples(index=False)

    for store, item in combos:
        # 1. Filter data for the current store and item combination
        # (Assuming df already has 'ds' and 'y' columns)
        sub_df = df[(df["store"] == store) & (df["item"] == item)].copy()

        # 2. Train and save using the filtered subset
        model = train(sub_df, **prophet_kwargs)
        fp = save_model(model, store, item, path)

        # 3. Record metrics based on the specific series subset
        rows.append(
            {
                "store": store,
                "item": item,
                "n_days": len(sub_df),
                "mean_daily_sales": sub_df["y"].mean() if "y" in sub_df.columns else None,
                "artifact": str(fp),
            }
        )

    return pd.DataFrame(rows)
