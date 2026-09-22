"""Structured output schema for the v1 agent's final answer. See
skills/pydantic-structured-outputs.md before editing.
"""

from pydantic import BaseModel, Field


class ReorderRecommendation(BaseModel):
    store_id: int
    item_id: int
    recommended_quantity: int = Field(ge=0)
    rationale: str
    policy_flags: list[str] = Field(default_factory=list)
    requires_approval: bool
    estimated_order_value: float = Field(ge=0)
