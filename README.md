# demand-reorder-advisor

Single-agent demand forecasting and policy/inventory verification system,
built as a portfolio project. Full problem framing lives in
[docs/Problem_brief.md](docs/Problem_brief.md) — read that before this file.

## Status
**Phase 0 — setup.** No agent code yet.

## Quickstart
```bash
make setup
cp .env.example .env   # fill in API keys
```

## Structure
- `data/policy_docs/` — 7 synthetic company policy PDFs (Meridian Retail
  Group), keyed to the Kaggle dataset's Item IDs 1-50 and Store IDs 1-10.
- `skills/` — pattern notes for specific implementation areas, read before
  writing code in that area.
- `docs/adr/` — one file per architectural decision, using the template.
- `src/demand_advisor/` — application code (empty until v1 build starts).
- `evals/` — eval scenarios and harness.

## Architecture decisions
See `docs/adr/` — each decision gets its own file, added as they're made,
not written in advance.
