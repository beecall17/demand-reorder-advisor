"""Core inventory data access. See skills/postgres-connection-patterns.md
before editing.

Business logic lives here as a plain async function, not inside the MCP
server. The MCP server (mcp_inventory_server.py) is a thin adapter that
exposes this same function externally over the MCP protocol; the agent
calls it directly, in-process, since round-tripping through MCP transport
to reach code in the same codebase would add latency for no benefit. The
MCP server exists so a *different* future consumer (a separate process,
v2's multi-agent system, Claude Desktop, Cline) has a standard way to reach
this data without depending on this module directly.
"""
import os
from pathlib import Path

import asyncpg
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://advisor:advisor_dev_password@localhost:5432/demand_advisor",
)

_pool: asyncpg.Pool | None = None


class InventoryRecord(BaseModel):
    store_id: int
    item_id: int
    on_hand: int
    last_updated: str


async def get_pool() -> asyncpg.Pool:
    """One pool per process, created on first use, reused for every query.
    Never open a fresh connection per request -- see
    skills/postgres-connection-patterns.md.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def get_inventory(store_id: int, item_id: int) -> InventoryRecord:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT store_id, item_id, on_hand, last_updated "
            "FROM inventory WHERE store_id = $1 AND item_id = $2",
            store_id, item_id,
        )
    if row is None:
        raise ValueError(f"no inventory row for store={store_id} item={item_id} "
                          f"-- has scripts/seed_inventory.py been run?")
    return InventoryRecord(
        store_id=row["store_id"], item_id=row["item_id"],
        on_hand=row["on_hand"], last_updated=row["last_updated"].isoformat(),
    )


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# --- sync bridge for v1's sync agent -----------------------------------

_loop: object | None = None


def _get_loop():
    """A single persistent event loop for the process lifetime, NOT
    asyncio.run() per call. asyncio.run() creates and tears down a new
    loop every invocation, which breaks pool reuse -- asyncpg pools are
    bound to the loop they were created on, so a second asyncio.run() call
    fails trying to reuse a pool from an already-closed loop. Hit this for
    real during testing (two sequential calls to the sync wrapper), not a
    hypothetical -- see the traceback preserved in
    docs/adr/0006-single-event-loop-for-sync-bridge.md.
    """
    import asyncio
    global _loop
    if _loop is None:
        _loop = asyncio.new_event_loop()
    return _loop


def get_inventory_sync(store_id: int, item_id: int) -> InventoryRecord:
    """Sync wrapper for v1's sync agent. Runs on the single persistent
    loop above, not a fresh asyncio.run() per call.
    """
    return _get_loop().run_until_complete(get_inventory(store_id, item_id))
