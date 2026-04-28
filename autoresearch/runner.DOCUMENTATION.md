# Loop runner documentation

`LoopRunner` coordinates full operation:

1. Load dataset + deterministic split.
2. Ensure initial bootstrap iteration if needed.
3. Load history and run Stage C.
4. Apply Stage B over parent, run parallel scoring, append candidate rows.
5. Mark best dev candidate as next parent candidate marker.
6. Regenerate report and persist notes snapshots.

Commands exposed via `loop`:
- `run [--max-iters N] [--limit N]`
- `report`
- `reset`
- `score <artifact-or-path>`
