# Core module documentation

## Paths
`make_paths()` builds all root/state/cache directories from `AUTORESEARCH_STATE_DIR`.

## Dataset
`load_ground_truth_dataset()` reads JSONL lines with keys `{id,text,label}`.
If the file is absent, it creates a deterministic synthetic fallback (seeded).

## Splitter
`split_dataset()` performs deterministic stratified split by label using a seeded random instance.

## Metrics
`core/metrics.py` provides:
- Cohen kappa
- macro-F1
- Spearman rank correlation

## Hash and log helpers
- `artifact_hash()` uses deterministic canonical JSON serialisation.
- `append_jsonl_line()` is line-flushed + `fsync` for append-only log writes.
- `ExperimentStore` provides resilient read and append semantics.
