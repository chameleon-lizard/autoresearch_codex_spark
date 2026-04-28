# autoresearch package documentation

This package implements a task-agnostic, offline-safe autoresearch loop with four major components:

1. **Core primitives** (`autoresearch/core`): dataset loading, deterministic splits, artifact hashing, experiment log persistence.
2. **Scoring layer** (`autoresearch/scorer`): deterministic artifact scorer with on-disk cache.
3. **Refinement stages** (`autoresearch/stages`):
   - Stage A: disagreement diagnosis.
   - Stage B: batch proposal generation (single-edit siblings).
   - Stage C: parent selection.
   - Stage M: merge synthesis of parent artifacts.
4. **Orchestrator/CLI** (`autoresearch/runner.py`, `autoresearch/cli.py`): batch loop and user commands.

### Determinism and resumability
- Artifact identity is SHA-256-based and content-based.
- Scores are written into `cache/<hash>/result.json`.
- `state/experiments.jsonl` is append-only.
- `state/experiments_report.md` is regenerated on each batch.

### State and artifact semantics
Artifacts are JSON blobs with score-relevant fields:
- `threshold`: prediction threshold.
- `bias`: score offset.
- `length_penalty`: per-character penalty.
- `positive_keywords`: token -> positive boost.
- `negative_keywords`: token -> negative penalty.

Each proposal changes only one of these components.
