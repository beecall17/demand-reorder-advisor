# ADR-0001: PostgreSQL (via Docker Compose) with pgvector, instead of SQLite + Chroma

**Status:** accepted

## Context
Phase 0 originally specified a synthetic SQLite inventory database, with
Chroma planned separately for the policy-document vector store. Two separate
storage engines for two related lookups adds operational surface area
without a matching benefit at this project's scale, and SQLite's
single-writer model doesn't reflect how a live inventory system actually
behaves under concurrent access.

## Decision
Use PostgreSQL for both structured inventory data and vector storage (via
the pgvector extension), run locally through Docker Compose using the
official `pgvector/pgvector` image. Access it through a single asyncpg
connection pool, configured via one `DATABASE_URL` environment variable.
Schema is bootstrapped automatically via `db/init.sql`, mounted into the
container's init directory.

Docker Compose is used for the database specifically, starting in Phase 0 --
this is a separate decision from containerizing the application itself in
v3, not an early jump to that milestone. Running infra dependencies
(databases, queues) in Docker during local development, while application
code still runs directly, is standard practice independent of when the app
gets containerized.

## Consequences
- One database engine to reason about instead of two; inventory rows and
  policy-doc embeddings can be joined in a single query if that's ever
  useful (e.g. "policy chunks relevant to low-stock items").
- The connection pool and `DATABASE_URL` pattern used in dev are the same
  ones a deployed version would use -- swapping to a managed Postgres
  instance (Neon, Supabase, Railway all have free tiers) later is a
  one-line env change, not a rewrite.
- Adds a Docker dependency to local setup that SQLite wouldn't have
  required. Acceptable trade-off given Docker is already planned for v3;
  this uses it slightly earlier, for the database only.
- `docker compose down -v` / `up -d` replaces SQLite's "just delete the
  file" reset simplicity with one extra command -- not meaningfully harder.
- Embedding dimension in `policy_chunks.embedding` is a placeholder (384)
  until an embedding model is chosen during RAG ingestion; must be updated
  before the first real ingest run or all vector inserts will fail on a
  dimension mismatch.
