# Skill: RAG chunking and ingestion

Load this before writing the policy-doc ingestion pipeline.

## Chunking
Chunk by section header, not fixed token count — each policy doc is already
organized into numbered/titled sections, and splitting mid-section produces
worse retrieval than splitting on the natural boundary.

## Metadata to keep per chunk
- `doc_code`     (e.g. MRG-POL-102)
- `doc_title`
- `section_title`
This lets the agent cite which policy doc a rule came from, not just repeat
the rule text.

## Store
Postgres via pgvector, same connection pool as inventory (see skills/postgres-connection-patterns.md). One table: `policy_chunks`, defined in db/init.sql.

## Test set
Use the "answerable questions" implied by the 7 PDFs themselves, e.g.:
"can we reorder item 7", "what's the approval threshold for a $15,000 order",
"what's the safety stock formula". Good first retrieval eval set — no new
data needed.
