# Project Progress

## Implemented
- [x] Core config and environment-based settings.
- [x] Deterministic dataset load + synthetic fallback generation.
- [x] Deterministic stratified train/dev/test split.
- [x] Artifact hashing + cache addressing.
- [x] On-disk cached scoring with parallel execution.
- [x] Stage A disagreement summarization with failure token extraction.
- [x] Stage B proposal generation with single-edit restriction.
- [x] Stage B proposal parser + temperature-based retry loop.
- [x] Stage B parse failure diagnostics (`stage_b_attempt_<n>.txt`) with parse metadata.
- [x] Stage C selection and plateau-triggered merge selection.
- [x] Stage M merge synthesis.
- [x] Append-only experiment log + line-buffered append writes.
- [x] Report regeneration command path and per-plan aggregates.
- [x] CLI surface: `run`, `report`, `reset`, `score`.
- [x] Multi-instance state directory support via `AUTORESEARCH_STATE_DIR`.
- [x] Batch notebook snapshotting before/after each run and loop lockfile.
- [x] Module-level documentation and operational runbook.

## Planned
- [ ] Add formal schema validation for artifacts and result payloads.
- [ ] Add unit tests for splitter, scorer cache, selector, and report deltas.
- [ ] Add optional external LLM judge/merger wrappers while preserving the same interface.
- [ ] Add explicit stage-level timeout/latency metrics and health checks.
