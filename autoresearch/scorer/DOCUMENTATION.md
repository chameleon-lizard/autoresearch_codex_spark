# Scorer module documentation

The scorer module owns deterministic candidate evaluation.

## Predictor
- Parses artifact JSON.
- Converts each text into a confidence score from token hits, bias and length penalty.
- Produces probabilities, thresholded predictions, errors, and per-split metrics.

## Cache
- Score results live under `state/cache/<artifact_hash>/result.json`.
- Cache contains full artifact text and all split-level metrics.

## Driver
- Scores candidates in parallel with `ThreadPoolExecutor`.
- Reuses cached outputs whenever available.
- Returns a mapping by artifact hash to score payload.
