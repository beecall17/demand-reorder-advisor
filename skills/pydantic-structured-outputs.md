# Skill: pydantic structured outputs

Load this before defining any agent's output schema.

## Pattern
Every agent that produces a final answer returns a Pydantic model, enforced
via `instructor.from_litellm(...)` — never parse raw JSON strings from a
completion by hand.

## Convention for this project
The v1 agent's answer schema should include, at minimum:
- `recommended_quantity: int`
- `rationale: str`
- `policy_flags: list[str]`   (empty list if none triggered)
- `requires_approval: bool`
- `estimated_order_value: float`

Keep schemas flat where possible — nested schemas make instructor retries
more brittle.
