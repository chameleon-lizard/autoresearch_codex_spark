# Core module documentation

## Paths
`make_paths()` builds all root/state/cache directories from `AUTORESEARCH_STATE_DIR`.

## Dataset
`load_ground_truth_dataset()` reads JSONL lines with keys `{id,text,label}`.
If the file is absent, it creates a deterministic synthetic 200-row fallback.

## Splitter
`split_dataset()` performs deterministic stratified splitting by label.

## Metrics
`core/metrics.py` provides:
- Cohen kappa
- macro-F1
- Spearman correlation between labels and prediction probabilities

## Hash and log helpers
- `artifact_hash()` uses deterministic canonical JSON serialisation.
- `append_jsonl_line()` adds one experiment line at a time.
- `ExperimentStore` keeps append-only operations and robust readback.
