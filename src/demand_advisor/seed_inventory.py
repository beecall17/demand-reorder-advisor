"""Seeds the inventory table for all 500 (store, item) combinations.

Starting stock is set as a multiple of each series' average daily sales
("days of cover"), varied per series so some combinations land near or
below a realistic reorder point (interesting test cases for the agent) and
some are well-stocked. The 4 discontinued/restricted items (7, 22, 40, 45)
get a modest leftover amount deliberately -- the agent should recognize
these from policy, not because inventory happens to read zero.

Prefers real historical averages from data/processed/sales_clean.parquet
(what your actual pipeline produces). Falls back to the synthetic
generator's own known base levels if that file isn't present -- this
sandbox doesn't have it (fresh container each turn), so this run uses the
fallback; your environment should use the real-data path.

Simulated "today" is 2018-01-01, not the real calendar date -- see
docs/adr/0005-simulated-today-anchor-date.md.
"""
import asyncio
from pathlib import Path

import asyncpg
import numpy as np
import pandas as pd

from src.demand_advisor.inventory import DATABASE_URL

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = REPO_ROOT / "data" / "processed" / "sales_clean.parquet"
SIMULATED_TODAY = pd.Timestamp("2018-01-01", tz="UTC")

RESTRICTED_ITEMS = {7, 22, 40, 45}

# Fallback only -- used when data/processed/sales_clean.parquet isn't
# available (e.g. this sandbox). Mirrors synthetic_data.py's ITEM_META base
# levels so the fallback stays consistent with the real generator instead
# of drifting from it.
_FALLBACK_ITEM_BASE = {
    1: 10, 2: 9, 3: 14, 4: 16, 5: 11, 6: 8, 7: 6, 8: 13,
    9: 9, 10: 8, 11: 12, 12: 18, 13: 10, 14: 22, 15: 11, 16: 15,
    17: 12, 18: 9, 19: 7, 20: 13, 21: 10, 22: 8, 23: 14, 24: 11,
    25: 10, 26: 9, 27: 16, 28: 15, 29: 9, 30: 13, 31: 8, 32: 7,
    33: 11, 34: 12, 35: 14, 36: 20, 37: 13, 38: 10, 39: 9, 40: 6,
    41: 17, 42: 10, 43: 12, 44: 14, 45: 7, 46: 10, 47: 18, 48: 11,
    49: 16, 50: 8,
}
_FALLBACK_STORE_MULT = {1: 1.35, 2: 1.30, 3: 1.32, 4: 1.00, 5: 0.95,
                         6: 1.05, 7: 0.98, 8: 0.55, 9: 0.50, 10: 0.52}


def compute_avg_daily_sales() -> pd.DataFrame:
    """Returns a (store, item, avg_daily_sales) frame, preferring the real
    last-90-days average from processed data, falling back to the known
    generator base levels if that file isn't present.
    """
    if PROCESSED_PATH.exists():
        df = pd.read_parquet(PROCESSED_PATH)
        cutoff = df["date"].max() - pd.Timedelta(days=90)
        recent = df[df["date"] > cutoff]
        avg = recent.groupby(["store", "item"])["sales"].mean().reset_index()
        avg.columns = ["store_id", "item_id", "avg_daily_sales"]
        print(f"using real historical averages from {PROCESSED_PATH}")
        return avg

    print(f"WARNING: {PROCESSED_PATH} not found -- using fallback estimates "
          f"consistent with synthetic_data.py's known base levels, not real "
          f"computed history. Re-run this script in an environment that has "
          f"the processed data for accurate seeding.")
    rows = []
    for store_id, mult in _FALLBACK_STORE_MULT.items():
        for item_id, base in _FALLBACK_ITEM_BASE.items():
            rows.append({"store_id": store_id, "item_id": item_id,
                         "avg_daily_sales": base * mult})
    return pd.DataFrame(rows)


def compute_starting_stock(avg_df: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = avg_df.copy()
    days_of_cover = rng.uniform(5, 20, size=len(out))
    out["on_hand"] = (out["avg_daily_sales"] * days_of_cover).round().astype(int)

    # Restricted items: modest leftover stock regardless of the random draw
    # above -- these should read as "some stock, don't reorder" per policy,
    # not "zero, nothing to decide about."
    restricted_mask = out["item_id"].isin(RESTRICTED_ITEMS)
    out.loc[restricted_mask, "on_hand"] = (
        out.loc[restricted_mask, "avg_daily_sales"] * rng.uniform(5, 15, size=restricted_mask.sum())
    ).round().astype(int)

    out["on_hand"] = out["on_hand"].clip(lower=0)
    return out[["store_id", "item_id", "on_hand"]]


async def seed(rows: pd.DataFrame) -> None:
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=5)
    async with pool.acquire() as conn:
        await conn.executemany(
            "INSERT INTO inventory (store_id, item_id, on_hand, last_updated) "
            "VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (store_id, item_id) DO UPDATE "
            "SET on_hand = EXCLUDED.on_hand, last_updated = EXCLUDED.last_updated",
            [(int(r.store_id), int(r.item_id), int(r.on_hand), SIMULATED_TODAY.to_pydatetime())
             for r in rows.itertuples()],
        )
    await pool.close()


def main() -> None:
    avg_df = compute_avg_daily_sales()
    stock_df = compute_starting_stock(avg_df)
    asyncio.run(seed(stock_df))
    print(f"seeded {len(stock_df)} inventory rows, simulated today = {SIMULATED_TODAY.date()}")

    low = stock_df.merge(avg_df, on=["store_id", "item_id"])
    low["days_cover"] = low["on_hand"] / low["avg_daily_sales"].clip(lower=0.1)
    print(f"days-of-cover range: {low['days_cover'].min():.1f} to {low['days_cover'].max():.1f}")
    print(f"restricted items seeded: "
          f"{stock_df[stock_df['item_id'].isin(RESTRICTED_ITEMS)].to_dict('records')}")


if __name__ == "__main__":
    main()
