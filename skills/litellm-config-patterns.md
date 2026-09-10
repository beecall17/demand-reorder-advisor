# Skill: litellm config patterns

Load this before touching src/demand_advisor/llm_client.py.

## What litellm gives us for free
- Retries: set `num_retries` on the call or router.
- Rate limiting: router-level RPM/TPM caps per model.
- Fallback: `Router` with a `fallbacks` list — Groq primary, Gemini Flash
  fallback.
- Caching: `litellm.cache = Cache(...)` — turn on before any agent calls,
  it's nearly free and covers the "bonus" caching requirement in v1.

## Pattern
One `Router` instance, constructed in one place, imported everywhere else.
Never instantiate a provider client directly in agent code.

## Don't
Don't hand-roll retry/backoff logic — it duplicates what the Router already
does and is a common source of silent bugs (double-retrying).
