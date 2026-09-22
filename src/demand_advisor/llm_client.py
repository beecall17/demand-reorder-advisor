"""Modular LLM client. See skills/litellm-config-patterns.md before editing.

One Router instance, constructed once, imported everywhere else -- agent
code never calls a provider SDK or even bare litellm.completion() directly.
"""

import os

import litellm
from litellm import Router

MODEL_LIST = [
    {
        "model_name": "primary",
        "litellm_params": {
            "model": "groq/llama-3.3-70b-specdec",
            "api_key": os.getenv("GROQ_API_KEY"),
        },
    },
    {
        "model_name": "fallback",
        "litellm_params": {
            "model": "gemini/gemini-3.5-flash",
            "api_key": os.getenv("GOOGLE_API_KEY"),
        },
    },
]

_router: Router | None = None


def _maybe_enable_langfuse() -> None:
    """Activates only if real Langfuse keys are present in the environment.
    Safe to call with no keys set -- e.g. in tests or before an account
    exists -- it just no-ops rather than erroring.
    """
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]


def get_router() -> Router:
    global _router
    if _router is None:
        _maybe_enable_langfuse()
        _router = Router(
            model_list=MODEL_LIST,
            fallbacks=[{"primary": ["fallback"]}],
            num_retries=2,
            retry_after=2,  # seconds between retries
            allowed_fails=1,  # trip to fallback after 1 failure, don't wait for a full outage
        )
        litellm.cache = litellm.Cache()  # in-memory response cache, on by default
    return _router
