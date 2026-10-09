"""The v1 agent. Deterministic orchestration (this module calls each
"tool" itself, in code) plus exactly one LLM call that synthesizes a
structured recommendation from the gathered context.

The LLM deciding *which* tools to call is a v2 "agentic loop" concept, not
v1 -- see docs/ROADMAP.md. Keeping v1 deterministic makes it easier to tell,
when something goes wrong, whether the bug is in a tool or in the LLM's
reasoning over already-correct context.

STUB NOTICE: two of the three _get_*_context() functions below still
return hardcoded fake data. Inventory is now wired to the real database
(src/demand_advisor/inventory.py) -- see docs/adr/0005 for why "today" is
simulated as 2018-01-01, not the real calendar date. Remaining stubs:
  - _get_forecast_context   -> src/demand_advisor/forecast.py (already built,
                               just needs wiring in -- see forecast.load_model)
  - _get_policy_context     -> pgvector RAG retrieval (not yet built)
"""
import instructor

from .inventory import get_inventory_sync
from .llm_client import get_router
from .schemas import ReorderRecommendation

_client: instructor.Instructor | None = None


def _get_client() -> instructor.Instructor:
    global _client
    if _client is None:
        # JSON mode, not the TOOLS/function-calling mode: works consistently
        # across providers (Groq's Llama models and Gemini both handle plain
        # JSON-in-content reliably), and is directly testable with litellm's
        # mock_response without needing real API keys -- TOOLS mode expects
        # a tool_call in the response, which mock_response doesn't produce.
        _client = instructor.from_litellm(get_router().completion, mode=instructor.Mode.JSON)
    return _client


# --- tool context ---------------------------------------------------

def _get_forecast_context(store_id: int, item_id: int) -> str:
    return "STUB forecast: predicted demand next 7 days = [18, 20, 19, 22, 25, 30, 28] units/day"


def _get_inventory_context(store_id: int, item_id: int) -> str:
    # Real lookup now, not a stub. See inventory.get_inventory_sync's
    # docstring for why this uses a persistent event loop, not asyncio.run().
    record = get_inventory_sync(store_id, item_id)
    return (f"{record.on_hand} units currently on hand "
            f"(as of {record.last_updated}, simulated 'today' is 2018-01-01)")


def _get_policy_context(store_id: int, item_id: int) -> str:
    return "STUB policy: no restrictions found for this item; store max capacity 200 units/SKU"


# --- prompt + agent entry point -----------------------------------------

PROMPT_TEMPLATE = """You are a retail supply chain reorder advisor.

Store: {store_id}
Item: {item_id}

Demand forecast:
{forecast_context}

Current inventory:
{inventory_context}

Company policy:
{policy_context}

Based on this, recommend a reorder quantity. Set requires_approval to true
if the estimated order value exceeds $2,000 (assume $15/unit if no price is
given). List any policy_flags that apply, even if none block the order.
"""


def recommend_reorder(store_id: int, item_id: int, mock_response: str | None = None) -> ReorderRecommendation:
    forecast_ctx = _get_forecast_context(store_id, item_id)
    inventory_ctx = _get_inventory_context(store_id, item_id)
    policy_ctx = _get_policy_context(store_id, item_id)

    prompt = PROMPT_TEMPLATE.format(
        store_id=store_id, item_id=item_id,
        forecast_context=forecast_ctx,
        inventory_context=inventory_ctx,
        policy_context=policy_ctx,
    )

    client = _get_client()
    kwargs = dict(
        model="primary",
        messages=[{"role": "user", "content": prompt}],
        response_model=ReorderRecommendation,
    )
    if mock_response is not None:
        kwargs["mock_response"] = mock_response

    return client.chat.completions.create(**kwargs)
