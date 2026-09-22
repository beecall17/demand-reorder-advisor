# End-to-end roadmap — demand-reorder-advisor

This is the reference plan. When a new idea comes up mid-build, check it
against this document before adding it to the current phase.

## Build philosophy (unchanged)

Complexity is added in response to a documented limitation, never in advance
of one. Each phase ships something real — a deployed app, a trained model, a
written limitations doc — before the next phase starts.

## Two tracks, one project

This project runs two different operational lifecycles side by side, and
they're tracked with two different tools on purpose — conflating them is a
common mistake worth naming explicitly:

| | Data science track | Agent track |
|---|---|---|
| **What it governs** | The Prophet forecasting model | The LLM agent(s) built on top |
| **Tool** | MLflow | Langfuse |
| **Cadence** | Offline, batch, run on retrain | Online, per request |
| **Tracks** | Experiment runs, params, metrics, model versions | Traces, spans, tool calls, cost, latency, eval scores |
| **Starts** | v1 (not v3) | v1 (not v3) |

They meet at one point: the agent's forecast-lookup tool calls a specific
MLflow-tracked model version. Worth keeping that link explicit — log the
MLflow run ID as metadata on the corresponding Langfuse span — rather than
letting the two systems drift apart with no way to trace an agent's bad
recommendation back to which model version produced the forecast it used.

## Tool decisions so far (ADR log)

| ADR | Decision |
|---|---|
| 0001 | PostgreSQL + pgvector via Docker Compose, over SQLite + Chroma |
| 0002 | Prophet over LightGBM, one model per (store, item), 500 total |
| 0003 *(new, this doc)* | MLflow from v1, local file store (`./mlruns`), no server to run |
| 0004 *(new, this doc)* | Langfuse over LangSmith, Cloud Hobby tier from v1, self-host deferred to v3 |

**On ADR-0004 specifically:** Langfuse's free Hobby tier gives 50,000
units/month (a unit is any trace, span, or score — a single multi-step agent
call can burn 5-20 units, so this comfortably covers dev and eval volume,
not production traffic), 30-day retention, 2 users, no card required.
Langfuse is MIT-licensed and self-hostable at unlimited volume, but
self-hosting means running Postgres + ClickHouse + Redis + blob storage —
meaningfully heavier than the single Postgres container this project
already runs. That's a real infra step up, not a checkbox, which is why it's
placed in v3 alongside the rest of the production-hardening work, not v1.

---

## Phase 0 — Setup ✅ complete

- [x] Synthetic sales dataset matching the Kaggle schema (10 stores × 50
      items, 2013-2017), seasonality tied to the policy docs' categories
- [x] 7 synthetic company policy PDFs (Meridian Retail Group)
- [x] Repo scaffold: `.clinerules`, `skills/`, pinned deps, ADR template
- [x] PostgreSQL + pgvector running via Docker Compose
- [x] Prophet models trained and backtested for all 500 store-item pairs
- [x] Limitations of the forecast-only model written down (closing
      `notebooks/02_prophet_forecast_model.ipynb`)

---

## v1 — Single agent MVP (current phase)

### Data science sub-track (MLflow)

- [x] Wire MLflow into the training notebook — it was trained without it,
      so this is retroactive, not new scope. One run per batch-training pass:
  - **params**: `seasonality_mode`, `yearly_seasonality`, `weekly_seasonality`,
    holdout window length
  - **metrics**: WAPE/MAE per representative category series, plus the
    aggregate distribution stats already computed in the notebook
  - **artifacts**: the backtest summary table, the two evidence plots
  - Register a `prophet-demand-v1` entry in the Model Registry pointing at
    this run — not one registry entry per (store, item); 500 individual
    registrations isn't what the registry is for
- [x] Local file store (`mlflow.set_tracking_uri("file:./mlruns")`) is
      enough for v1 — `mlflow ui` locally to browse, no server, no cost

### Agent track (Langfuse)

- [ ] Create a Langfuse Cloud (Hobby) project, get the public/secret keys
- [ ] Wire via litellm's built-in callback — `litellm.success_callback =
      ["langfuse"]` — this is nearly free given litellm is already the
      client layer (see `skills/litellm-config-patterns.md`)
- [ ] Every tool call the agent makes (forecast lookup, policy RAG
      retrieval, MCP inventory read) becomes a span inside one trace per
      user query — not a flat log line per call
- [ ] Eval harness scenarios logged as a Langfuse Dataset; each run scored
      (schema-valid output? policy correctly applied? right store/item
      identified?) and attached as Langfuse Scores, not just printed to
      console

### Connecting tissue (as previously scoped, recapped here)

- [ ] Policy PDFs → chunk by section → embed → ingest into `policy_chunks`
      (pgvector)
- [ ] MCP server wrapping the inventory lookup (`skills/mcp-server-minimal.md`)
- [ ] litellm client with retry/fallback/caching on by default
- [ ] instructor + Pydantic structured output for the agent's final answer
- [ ] One agent, one entry point: "what should I restock for store 3 next
      week" in, structured recommendation out
- [ ] Streamlit UI
- [ ] Deploy to Render (free tier)
- [ ] Extend the limitations doc to cover the full agent, not just the
      forecast model

### v1 exit criteria

- [ ] Deployed, clickable URL
- [ ] MLflow experiment with the full batch training run logged
- [ ] Langfuse project with traces for all 10-15 eval scenarios
- [ ] Written limitations doc — this is what justifies v2's scope, not
      written in advance of it

---

## v2 — Multi-agent (driven by v1's limitations)

- Decompose into separate agents only in response to what v1's limitations
  doc actually says — likely candidates to test for, not assume: context
  overload from combining forecasting reasoning and policy compliance in
  one prompt, no self-critique step, no clean insertion point for human
  approval
- LangGraph orchestration, context engineering, human-in-the-loop approval
  gate above a dollar threshold
- **MLflow**: if the forecast model changes at all in v2, the new run is
  logged and compared against v1's run in MLflow's run-comparison view —
  this is exactly the built-in feature for this, not something to build by
  hand
- **Langfuse**: run the same eval dataset through both v1's single agent
  and v2's multi-agent graph, compare scores side by side. This is the
  regression evidence that justifies the added complexity actually helped —
  without it, v2 is just "more agents," not a demonstrated improvement

---

## v3 — Production-readiness

- Dockerize the app itself (separate from the Postgres-in-Docker decision
  already made in Phase 0), CI/CD via GitHub Actions
- Kubernetes demonstrated locally (kind/minikube), not run as a paid
  cluster continuously
- Self-hosted vLLM (Colab + ngrok) — deliberately not in v1, where it would
  only cost time fighting infrastructure instead of the business problem;
  by v3 the fallback/retry patterns from litellm exist to absorb its
  instability
- **MLflow**: move the tracking URI from local file store to a small
  self-hosted server only if collaboration or persistence beyond local disk
  becomes a real need — otherwise the v1 setup remains correct, don't
  upgrade infra that isn't limiting anything yet
- **Langfuse**: self-host only if free-tier volume or data residency
  becomes a real constraint, not by default — MIT-licensed, docker-compose
  available, but genuinely heavier infra (Postgres + ClickHouse + Redis +
  blob storage) than anything this project has needed so far
- Performance/reliability hardening: async/batch request handling, response
  caching, graceful degradation, circuit-breaking
- Written scaling document: KV caching, token cost, load balancing, and
  where a tool like llm-d would fit at real scale — analysis, not
  implementation, per the standing decision on this

---

## Open question

Confirmed default: **Langfuse Cloud (Hobby tier)** for v1, self-host
deferred to v3 only if actually needed. If you meant LangSmith when you
said Langfuse, say so and this document (plus `.env.example` and the
`skills/` notes) gets updated to match — small change at this stage, not a
rebuild.
