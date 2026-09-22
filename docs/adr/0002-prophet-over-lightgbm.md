# ADR-0002: Prophet over LightGBM for v1 forecasting, one model per (store, item)

**Status:** accepted

## Context
Two forecasting approaches were on the table: Prophet (decomposable
trend/seasonality model) and LightGBM (gradient-boosted trees over engineered
lag/calendar features). The demand signal in this dataset is dominated by
yearly and weekly seasonal cycles per item category (confirmed visually in
`notebooks/01_data_prep_and_exploration.ipynb`), with no complex cross-feature
interactions to exploit -- no price, promotion, or competitor data sits
alongside the sales series.

A separate question sat underneath the model choice: forecast at the
(store, item) level directly (500 series), or forecast at the item level
and disaggregate to stores via a static multiplier.

## Decision
Use Prophet, one model per (store, item) combination (500 models total),
trained on full history and serialized via Prophet's own `model_to_json` /
`model_from_json` (not raw pickle -- see `skills/forecasting-model-io.md`).
LightGBM remains a documented alternative, not implemented, in case v1's
limitations point at a need for cross-item or cross-feature modeling that
Prophet structurally can't express.

Per-(store, item) modeling was chosen over item-level-plus-disaggregation
because Prophet's fit cost is low (~0.5s/series, ~4 minutes for all 500) and
per-series models let each store's actual weekday/promotional pattern show
up directly, rather than being flattened into a single multiplier per store
format tier.

## Consequences
- No feature engineering pipeline is needed for v1 -- Prophet takes a plain
  `(ds, y)` frame. This removes an entire class of train/serve-skew risk
  that a lag-feature approach would carry (though the model-artifact
  versioning discipline in `skills/forecasting-model-io.md` still applies).
- 500 small JSON artifacts (a few KB each) instead of one large model file --
  easy to lazy-load exactly the (store, item) pair a query needs, at the cost
  of 500 files to manage instead of one.
- Backtested WAPE varies by category (see notebook 02): ~0.18 for winter/
  holiday/back-to-school items, ~0.24 for the sampled summer item. Tracked
  per-category, not hidden behind a single blended average.
- Documented limitation, not a blocker: Prophet has no mechanism to encode
  company policy, current inventory, or cross-item substitution effects --
  this is by design (see the limitations section closing notebook 02) and is
  exactly what the RAG/inventory/MCP layer exists to add on top, not
  something the forecasting model itself should attempt.
- If v2's documented limitations ever point at needing external regressors
  (e.g. a live promotions calendar) or cross-series effects, that's the
  trigger to revisit LightGBM or Prophet's own regressor support -- not
  something to pre-build now.
