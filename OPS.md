# Operations Runbook

## Scope
Runbook for an AI operator managing this repo locally.

## Build and start
- Install: `pip install -r requirements.txt`
- Run one bounded batch: `loop run --max-iters 3`
- Run indefinitely: `loop run`
- Regenerate report: `loop report`
- Reset run state (retain cache): `loop reset`
- Score an artifact file: `loop score path/to/artifact.json`

## Environment variables
| Variable | Required | Description | Example |
| --- | --- | --- | --- |
| `AUTORESEARCH_STATE_DIR` | No | Root state path | `/tmp/autoresearch/runA` |
| `AUTORESEARCH_DATASET_PATH` | No | Dataset JSONL path | `data/ground_truth.jsonl` |
| `AUTORESEARCH_BATCH_SIZE` | No | Proposal count per batch | `3` |
| `AUTORESEARCH_PARALLELISM` | No | Score parallel workers | `4` |
| `AUTORESEARCH_RANDOM_SEED` | No | Deterministic seed for split and generation | `42` |
| `AUTORESEARCH_TRAIN_RATIO` | No | Train fraction | `0.4` |
| `AUTORESEARCH_DEV_RATIO` | No | Dev fraction | `0.2` |
| `AUTORESEARCH_TEST_RATIO` | No | Test fraction | `0.4` |
| `AUTORESEARCH_MAX_RETRIES` | No | Max Stage-B parse retries | `4` |
| `AUTORESEARCH_RETRY_TEMPERATURES` | No | Stage-B retry temperatures CSV | `0.0,0.4,0.7,0.9` |
| `AUTORESEARCH_HISTORY_LAST_N` | No | Compact history window | `5` |
| `AUTORESEARCH_INITIAL_ARTIFACT_JSON` | No | Inline seed artifact JSON | `'{"version":1,...}'` |

## State and health checks
- State root: `<state>/state`.
- Running lock: `<state>/state/loop.lock`.
- Log: `<state>/state/experiments.jsonl`.
- Report: `<state>/state/experiments_report.md`.
- Cache: `<state>/cache/<hash>/result.json`.
- Batch snapshots: `<state>/state/batches/<batch>/notes_before.md`, `notes_after.md`.
- Stage-B retries: `<state>/state/batches/<batch>/stage_b_attempt_<n>.txt`.

Quick checks:
- `loop report`
- `tail -f <state>/state/experiments_report.md`
- `tail -n 5 <state>/state/experiments.jsonl`

## Recovery playbook
- If run aborts mid-batch, restart `loop run`; log is append-only.
- Remove stale lock if process is dead: `rm <state>/state/loop.lock`.
- On parse storms, inspect latest `stage_b_attempt_*.txt` for parse diagnostics and reduce candidate budget or inspect summary/context.
- To replay state, keep `state/` and rerun `loop report`.

## Backup and restore
- Backup state directories: `state/`, `state/cache/`, `state/batches/`, `state/experiments.jsonl`, `state/experiments_report.md`.
- Restore by copying these paths into target `AUTORESEARCH_STATE_DIR`.

## Scale and update
- Increase `AUTORESEARCH_PARALLELISM` for faster scoring.
- Increase `AUTORESEARCH_BATCH_SIZE` (1..5) for broader search.
- Switch to new config by updating env vars or restarting with persisted `--max-iters` values.
- Rollback by checking out prior git revision and restoring state.
