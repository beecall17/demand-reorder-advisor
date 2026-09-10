# Skill: forecasting model artifact I/O

Load this before saving or loading the trained forecast model.

## Rule
Always persist the trained model AND the exact feature-engineering function
together, versioned as a pair. Loading the model without the matching
feature code is how train/serve skew happens silently.

## Pattern
- `models/forecast_model_v1.pkl`    — the fitted model (joblib)
- `models/feature_pipeline_v1.pkl`  — the fitted transformer/feature function,
  saved alongside it, same version suffix
- Never edit the feature engineering function after a model is trained
  against it without bumping the version suffix on both files together.
