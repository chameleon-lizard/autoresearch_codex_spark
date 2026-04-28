# Operations Runbook

## Scope
This runbook is for running and maintaining the local autoresearch loop service.

## Build and start
- Install: `pip install -r requirements.txt`
- Run one bounded iteration batch:
  - `loop run --max-iters 3`
- Run indefinitely: `loop run`
- Refresh report only: `loop report`

## Environment variables
| Variable | Required | Description | Example |
| --- | --- | --- | --- |
| `AUTORESEARCH_STATE_DIR` | No | Root state path | `/tmp/autoresearch/runA` |
| `AUTORESEARCH_DATASET_PATH` | No | Dataset JSONL path | `data/ground_truth.jsonl` |
| `AUTORESEARCH_BATCH_SIZE` | No | Candidates per batch (1..5) | `3` |
| `AUTORESEARCH_PARALLELISM` | No | Candidate scoring parallel workers | `4` |
| `AUTORESEARCH_RANDOM_SEED` | No | Deterministic splitting seed | `42` |
| `AUTORESEARCH_TRAIN_RATIO` | No | Train fraction | `0.4` |
| `AUTORESEARCH_DEV_RATIO` | No | Dev fraction | `0.2` |
| `AUTORESEARCH_TEST_RATIO` | No | Test fraction | `0.4` |
| `AUTORESEARCH_RETRY_TEMPERATURES` | No | Retry temperatures (CSV) | `0.0,0.4,0.7,0.9` |
| `AUTORESEARCH_HISTORY_LAST_N` | No | Recent-context window for selector | `5` |

## Health checks
- Check loop liveness by file timestamp: `tail -f state/experiments_report.md`
- Verify scoring cache growth: list `state/cache`.
- Confirm latest run: inspect last line `tail -n 1 state/experiments.jsonl`.

## Logs
- Main append-only log: `state/experiments.jsonl`
- Generated report: `state/experiments_report.md`
- Per-batch notebook snapshots: `state/batches/<batch>/notes_before.md`, `notes_after.md`

To query parse/score issues, inspect `state/batches/*/stage_b_attempt_*.txt`.

## Common failures
- **Corrupt log line**: ignored by JSON parser and skipped. Re-run `loop report` for reconciliation.
- **Cache miss flood**: check env config/path and dataset hash drift if reloading unexpectedly.
- **No improvement over batches**: inspect selector rationale in report and adjust stage prompts/sources.
- **Selector overfit signs**: watch train/dev/test gap in report; pause run and adjust plan or dataset.
- **Permission or stale state lock**: remove `state/loop.lock` if safe.

## Backup and restore
- Backup: copy `state/` and dataset file.
- Restore: replace `state/` with backup; no migration needed for this version.

## Scale up/down
- Scale parallelism with `AUTORESEARCH_PARALLELISM`.
- Run multiple independent instances by setting different `AUTORESEARCH_STATE_DIR`.

## Update/rollback
- Update by git pull/merge.
- Rollback by `git checkout <tag>` and restore `state/` if needed.

## Deployment reset
- `loop reset` resets run state but keeps cache.
