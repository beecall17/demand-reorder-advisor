"""Load and clean the raw sales data. Works identically whether
data/raw/train.csv is the synthetic generator's output or a real Kaggle
download -- both share the same date, store, item, sales schema.

Paths are resolved relative to the repo root (via this file's own location),
not the process's current working directory. Jupyter runs a notebook with
the notebook's own folder as cwd, not the repo root -- a cwd-relative
default here would silently write data/models into notebooks/data,
notebooks/models instead of the real top-level folders.
"""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = REPO_ROOT / "data" / "raw" / "train.csv"
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "sales_clean.parquet"


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    expected = {"date", "store", "item", "sales"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"missing expected columns: {missing}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce one row per (store, item, date) with no gaps, drop
    duplicates, and flag anything that looks wrong rather than silently
    discarding it.
    """
    before = len(df)

    df = df.drop_duplicates(subset=["date", "store", "item"], keep="last")

    negative = (df["sales"] < 0).sum()
    if negative:
        df = df[df["sales"] >= 0].copy()

    # Reindex every (store, item) pair onto the full date range so gaps
    # become explicit zero-sales days, not missing rows -- Prophet needs
    # a continuous daily series to learn weekly/yearly seasonality cleanly.
    full_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    filled = []
    gap_days = 0
    for (store, item), g in df.groupby(["store", "item"]):
        g = g.set_index("date").reindex(full_dates)
        gap_days += g["sales"].isna().sum()
        g["sales"] = g["sales"].fillna(0)
        g["store"] = store
        g["item"] = item
        g.index.name = "date"
        filled.append(g.reset_index())

    out = pd.concat(filled, ignore_index=True)
    out["store"] = out["store"].astype("int16")
    out["item"] = out["item"].astype("int16")
    out["sales"] = out["sales"].astype("int32")

    report = {
        "rows_in": before,
        "rows_out": len(out),
        "duplicates_dropped": before - len(df) - negative if before - len(df) - negative > 0 else 0,
        "negative_rows_dropped": int(negative),
        "gap_days_filled_with_zero": int(gap_days),
        "date_range": (str(out["date"].min().date()), str(out["date"].max().date())),
        "n_stores": out["store"].nunique(),
        "n_items": out["item"].nunique(),
    }
    return out, report


def save_processed(df: pd.DataFrame, path: Path = PROCESSED_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_processed(path: Path = PROCESSED_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)
