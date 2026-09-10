# Problem brief — demand-driven reorder advisory

## Core business problem 

A retail supply chain team needs to decide, on a recurring basis, how much of
each SKU to reorder per store. That decision currently requires manually
cross-referencing three disconnected sources: historical sales patterns, live
inventory counts, and written company policy (restricted items, budget caps,
shelf-space limits). No single source of truth combines them, so decisions are
slow, inconsistent, and occasionally violate policy simply because nobody
re-read the policy doc that day.

Nothing in this statement names a technique. Forecasting models, agents, RAG,
and orchestration are all *choices* made below — never assume one before
testing whether it's needed.

