# Skill: Postgres connection patterns

Load this before writing any DB access code (inventory lookups or pgvector
queries).

## Rule
One connection pool per process, created once at startup, reused for every
query. Never open a fresh connection per request -- that's the #1 thing that
makes a demo project behave differently from a live system.

## Pattern (asyncpg)
- Create the pool once, in the MCP server's startup/lifespan hook:
  `pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10)`
- Acquire per-query, release automatically: `async with pool.acquire() as conn:`
- Store the pool on app state, not as a module-level global created at
  import time -- import-time DB connections break testing and hot-reload.

## Connection string
Single `DATABASE_URL` env var, same variable name whether pointing at local
Docker Postgres or a managed instance later. This is what makes moving from
local dev to a real deployment a one-line env change, not a code change.

## pgvector specifics
Register the vector type once per connection (`await register_vector(conn)`)
so pgvector columns come back as Python arrays/lists, not raw strings. Do
this in the same startup hook that creates the pool. Embedding dimension in
`db/init.sql` is a placeholder -- update it to match whichever embedding
model gets chosen during RAG ingestion, before the first real ingest run.

## Local reset
`docker compose down -v` wipes the volume for a clean slate;
`docker compose up -d` recreates it and re-runs db/init.sql. Don't hand-write
reset scripts -- the volume flag already does this.
