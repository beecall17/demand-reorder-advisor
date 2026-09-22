import json

import pytest

from src.demand_advisor.agent import recommend_reorder
from src.demand_advisor.schemas import ReorderRecommendation

VALID_MOCK = json.dumps({
    "store_id": 3, "item_id": 26,
    "recommended_quantity": 150,
    "rationale": "Forecasted demand exceeds on-hand stock within capacity limits.",
    "policy_flags": [],
    "requires_approval": True,
    "estimated_order_value": 2250.0,
})


def test_agent_returns_valid_structured_output():
    result = recommend_reorder(store_id=3, item_id=26, mock_response=VALID_MOCK)
    assert isinstance(result, ReorderRecommendation)
    assert result.store_id == 3
    assert result.item_id == 26
    assert result.recommended_quantity == 150
    assert result.requires_approval is True


def test_agent_rejects_invalid_quantity():
    bad_mock = json.dumps({
        "store_id": 3, "item_id": 26,
        "recommended_quantity": -50,   # invalid: schema requires >= 0
        "rationale": "test",
        "policy_flags": [],
        "requires_approval": False,
        "estimated_order_value": 100.0,
    })
    with pytest.raises(Exception):
        recommend_reorder(store_id=3, item_id=26, mock_response=bad_mock)


def test_agent_rejects_missing_required_field():
    incomplete_mock = json.dumps({
        "store_id": 3, "item_id": 26,
        "recommended_quantity": 10,
        # missing rationale, policy_flags, requires_approval, estimated_order_value
    })
    with pytest.raises(Exception):
        recommend_reorder(store_id=3, item_id=26, mock_response=incomplete_mock)
