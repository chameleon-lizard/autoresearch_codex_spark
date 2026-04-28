# Autoresearch Project Wiki

## Purpose
This repository implements the task-agnostic autoresearch loop from `DesignDoc.md`, including:
- deterministic and cached scoring,
- append-only experiment history,
- batch proposal / selection,
- crash-safe resumability,
- full operational observability.

## Runtime components
- `autoresearch/config.py`: central runtime configuration and environment overrides.
- `autoresearch/core/*`: dataset loading, split, metrics, state paths, and log store.
- `autoresearch/scorer/*`: scoring engine and cache.
- `autoresearch/stages/*`: Stage A (diagnosis), Stage B (proposal + parsing/retry), Stage C (selection), Stage M (merge).
- `autoresearch/runner.py`: batch control loop and notebook snapshots.
- `autoresearch/reporter.py`: report regeneration from append-only JSONL.
- `autoresearch/cli.py`: command surface (`run`, `report`, `reset`, `score`).

## Data flow
1. Load dataset and stratified train/dev/test split.
2. Score bootstrap artifact (`iter=0`) and append to `state/experiments.jsonl`.
3. Per batch:
   - Stage C picks next parent / merge candidate.
   - Stage A renders disagreement summary from parent train errors.
   - Runner builds compact/full history context.
   - Stage B proposes up to `K` single-edit siblings and validates candidate serialization with retry.
   - All non-duplicate candidates score in parallel.
   - Candidate rows are appended to the log in one batch with `batch_id` and `is_parent_next` marking.
4. Regenerate report and write batch note snapshots.

## Invariants
- Artifact hash = `sha256(serialise(artifact))[:16]`.
- Scores are cached under `state/cache/<hash>/result.json`.
- Iteration log is strictly append-only JSONL.
- Parent selection can request merge mode during plateaus.

## Observability
- per-batch diagnostics are under `state/batches/<batch>/notes_before.md`, `notes_after.md`.
- Stage-B parse failures are written as `stage_b_attempt_<n>.txt` with parse metadata.
- Current state marker at `state/loop.lock` while running.
- Report is regenerated after each batch at `state/experiments_report.md`.

## Completion status
- All DesignDoc behaviors are represented in code, including retry/reasoning handling, attempt diagnostics, and merge/replay semantics.
- External LLM/judge wrappers are intentionally mocked by deterministic, cacheable local heuristics in this repository implementation.
