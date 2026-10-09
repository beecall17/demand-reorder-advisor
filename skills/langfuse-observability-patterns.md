# Skill: Langfuse observability patterns

Load this before touching tracing/eval code, or `llm_client.py`'s callback
setup.

## How it's wired
Through litellm's built-in callback, not the Langfuse SDK directly:
```python
litellm.success_callback = ["langfuse"]
litellm.failure_callback = ["langfuse"]
```
This is set conditionally in `llm_client._maybe_enable_langfuse()` -- only
activates if `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are present in
the environment. No keys set (e.g. in tests, or before the account exists)
means it silently no-ops rather than erroring. This is why
`tests/test_agent.py` can run with no Langfuse account at all.

## What this cannot verify locally
Nothing in this repo's test suite can confirm a trace actually lands in a
Langfuse project -- that requires a real account and real keys. Once
`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` are in `.env`, run any real (not
mock_response) agent call and check the Langfuse dashboard directly. Don't
trust "the code didn't error" as proof tracing works -- confirm the trace
is visible.

## What should show up per trace, once wired to real tools
One trace per `recommend_reorder()` call, containing:
- A span per tool call (forecast, inventory, policy RAG) once those replace
  the stubs in `agent.py`
- The final structured-output generation call, with the parsed
  `ReorderRecommendation` visible
- Cost and latency, tracked automatically by the litellm integration

## Eval harness (once there's something real to evaluate)
Log the 10-15 hand-written scenarios as a Langfuse Dataset, not just ad hoc
test calls. Score each run (schema-valid? policy correctly applied? right
store/item?) as a Langfuse Score attached to that dataset run -- this is
what makes the v1-vs-v2 regression comparison in `docs/ROADMAP.md` possible
later.
