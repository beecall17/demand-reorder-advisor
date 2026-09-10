# Skill: minimal MCP server (inventory lookup)

Load this before writing the inventory MCP server.

## Scope
One tool only: `get_inventory(store_id: int, item_id: int) -> InventoryRecord`.
Reads from Postgres via the shared connection pool (see skills/postgres-connection-patterns.md), not a file-based DB. Do not add write operations in v1 — the agent
only reads inventory, it doesn't update it.

## Why this is the one thing wrapped in MCP
This is the only piece of v1 that a different tool/agent would plausibly also
need to query later. The forecast model and the RAG index are
single-agent-specific; inventory is a shared resource. Full reasoning is
logged as an ADR in docs/adr/.

## Pattern
Use the official MCP Python SDK's `FastMCP` server class. Keep the schema for
`InventoryRecord` as a Pydantic model shared with the rest of the app.
