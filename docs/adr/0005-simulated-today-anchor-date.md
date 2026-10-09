# ADR-0005: Simulated "today" anchored to training cutoff (2018-01-01), not the real calendar date

**Status:** accepted

## Context
Training data ends 2017-12-31. The real calendar date during development is
2026 -- a 9-year gap. Inventory seed data and forecast horizons both need a
reference "today," and naively using the real calendar date would mean
asking Prophet to forecast dates 9 years past anything it was fit on.

## Decision
The simulated "today" for this project is **2018-01-01** (immediately
after the training cutoff), not the real calendar date. All forecasts,
inventory `last_updated` timestamps, and reorder-decision framing are
relative to this simulated date.

## Consequences
- Forecasts stay inside a defensible range of the training data instead of
  extrapolating a linear trend 9 years forward, which Prophet's own
  documentation warns against and which would likely produce meaningless
  numbers.
- Matches how a real production system actually behaves -- it retrains
  periodically and is never forecasting more than weeks/months past its own
  training data, not how far the calendar has moved since the model shipped.
- If the project is demoed to someone, "today" can be *labeled* as the
  present day in the UI without changing the underlying simulated clock --
  that's a presentation choice, not a modeling one.
- Revisit this the moment the forecasting model is retrained on more recent
  data (real Kaggle data swap, or a rolling retrain) -- the anchor date
  moves with the training cutoff, it isn't hardcoded permanently at
  2018-01-01.
