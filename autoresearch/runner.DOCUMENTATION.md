# Loop runner documentation

`LoopRunner` coordinates full operation:

1. Load dataset + deterministic split.
2. Ensure bootstrap iteration exists.
3. Acquire loop lock in state directory.
4. Resolve next parent via Stage C.
5. Run Stage A and build compact/full history context.
6. Run Stage B with retry parsing; write failure artifacts to batch directory.
7. Score K candidates in parallel with cache reuse.
8. Mark best candidate as `is_parent_next`.
9. Append rows to append-only `experiments.jsonl`.
10. Regenerate `state/experiments_report.md` and capture notebook snapshots.

Commands exposed via `loop`:
- `run [--max-iters N] [--limit N]`
- `report`
- `reset`
- `score <artifact-or-path>`
