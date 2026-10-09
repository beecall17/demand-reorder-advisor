"""Minimal MCP server wrapping the inventory lookup. See
skills/mcp-server-minimal.md before editing.

One tool only: get_inventory. No write operations in v1 -- the agent only
reads inventory, it doesn't update it.

This server exposes src.demand_advisor.inventory.get_inventory over the MCP
protocol for external consumers (a separate process, v2's multi-agent
system, Claude Desktop, Cline). The v1 agent itself calls that function
directly in-process -- it does not go through this server. See
inventory.py's module docstring for the reasoning.

NOTE on SDK version: as of the installed `mcp` package (2.x), FastMCP was
renamed to MCPServer with a new import path
(mcp.server.mcpserver.MCPServer, not mcp.server.fastmcp.FastMCP). This file
uses the current API. If you're following older MCP tutorials referencing
FastMCP, they're describing the pre-2.0 SDK.

Run standalone: python -m src.demand_advisor.mcp_inventory_server
"""
from mcp.server.mcpserver import MCPServer

from src.demand_advisor.inventory import InventoryRecord, get_inventory

server = MCPServer(name="inventory-lookup")


@server.tool()
async def inventory_lookup(store_id: int, item_id: int) -> InventoryRecord:
    """Look up current on-hand inventory for a given store and item."""
    return await get_inventory(store_id, item_id)


if __name__ == "__main__":
    server.run()
