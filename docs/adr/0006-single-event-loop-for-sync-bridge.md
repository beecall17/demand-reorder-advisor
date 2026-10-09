# ADR-0006: Single persistent event loop for the sync/async bridge, not asyncio.run() per call

**Status:** accepted

## Context
`agent.py`'s `recommend_reorder()` is synchronous (matches instructor's sync
client usage), but `inventory.get_inventory()` is async (per
`skills/postgres-connection-patterns.md`'s pool-based access pattern). The
first implementation bridged this with `asyncio.run(get_inventory(...))`
inside `_get_inventory_context()`.

This broke on the second call in the same process, with a real traceback:
`RuntimeError: ... got Future ... attached to a different loop`, followed by
`InterfaceError: cannot perform operation: another operation is in
progress`. `asyncio.run()` creates a new event loop and tears it down after
each call; the connection pool is a lazily-created module-level singleton
bound to whichever loop existed when it was first created. The second call's
new loop couldn't reuse a pool tied to the first (now-closed) loop.

## Decision
Bridge sync-to-async with a single persistent event loop, created once and
reused for the process lifetime (`inventory._get_loop()` /
`get_inventory_sync()`), not `asyncio.run()` per call. The pool is created
once, on that one loop, and stays valid for every subsequent call.

## Consequences
- Confirmed fixed by testing the actual failure scenario (three sequential
  inventory lookups, then two full agent calls in the same process) --
  not just re-running the same single call that happened to work once.
- `tests/test_agent.py`'s existing tests now implicitly require a live,
  seeded Postgres database (`DATABASE_URL` set) to pass -- inventory is no
  longer a stub, so these are now integration tests in practice, not pure
  unit tests. Worth splitting into a mocked-inventory unit tier and a
  real-database integration tier once the RAG and forecast tools are wired
  in too and this pattern repeats three times over, not before.
- This pattern (one persistent loop, `_sync` wrapper functions) is the
  template for wiring in the forecast and RAG tools next -- don't
  reintroduce `asyncio.run()` per call for those either.
