# Project Progress

## Implemented
- [x] Core config and environment-based settings.
- [x] Deterministic dataset load + synthetic fallback generation.
- [x] Stratified train/dev/test split.
- [x] Artifact hashing + cache addressing.
- [x] On-disk cached scoring with parallel execution.
- [x] Stage A disagreement summarization.
- [x] Stage B single-edit sibling proposals.
- [x] Stage C parent selection with merge-trigger heuristic.
- [x] Stage M merge synthesis.
- [x] Append-only experiment log with crash-safe reader logic.
- [x] Report regeneration command path.
- [x] CLI surface: `run`, `report`, `reset`, `score`.
- [x] Per-module documentation files.

## Planned
- [ ] Add explicit stage-B parsing retry logs and attempt metadata dumps.
- [ ] Add formal schema validation for artifact JSON.
- [ ] Add unit tests for all critical modules.
- [ ] Add Docker and deployment scripts.
- [ ] Add optional external scorer wrapper subprocess path.
