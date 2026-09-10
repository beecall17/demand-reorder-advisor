-- Auto-run once by the postgres image on first container startup
-- (mounted into /docker-entrypoint-initdb.d/). Re-running the container
-- against an existing volume will NOT re-run this file -- use
-- `docker compose down -v` first for a clean slate.

CREATE EXTENSION IF NOT EXISTS vector;

-- Store IDs 1-10, Item IDs 1-50 -- matches the Kaggle dataset dimensions
-- and the item-category-reference / store-classification policy PDFs.
CREATE TABLE IF NOT EXISTS inventory (
    store_id     SMALLINT NOT NULL,
    item_id      SMALLINT NOT NULL,
    on_hand      INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (store_id, item_id)
);

-- Embedding dimension is a placeholder -- set this to match whichever
-- embedding model gets chosen on the RAG ingestion day (e.g. 384 for
-- all-MiniLM-L6-v2, 1536 for OpenAI text-embedding-3-small).
CREATE TABLE IF NOT EXISTS policy_chunks (
    id            SERIAL PRIMARY KEY,
    doc_code      TEXT NOT NULL,
    doc_title     TEXT NOT NULL,
    section_title TEXT,
    content       TEXT NOT NULL,
    embedding     VECTOR(384)
);
