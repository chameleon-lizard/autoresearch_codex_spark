# Autoresearch Project Wiki

## Purpose
This repository implements a deterministic, resumable LLM-style autoresearch loop, with clear auditability and low operational risk:
- deterministic scoring cache
- append-only experiment log
- batch proposal scoring
- safe reset/report/replay flow

## Runtime components
- `autoresearch/config.py`: central runtime configuration and env overrides.
- `autoresearch/core/*`: dataset, split, metrics, state handling.
- `autoresearch/scorer/*`: scoring engine and per-artifact cache.
- `autoresearch/stages/*`: A/B/C/M refiner logic.
- `autoresearch/runner.py`: the control loop.
- `autoresearch/cli.py`: user-facing command interface.

## Data flow
1. Ground-truth data is loaded and deterministically split train/dev/test.
2. Initial artifact is scored and logged as iteration 0.
3. Each batch runs Stage C, A, B, then scoring.
4. All candidate rows are appended to `state/experiments.jsonl`.
5. Report file is regenerated from the log.

## Persistence and audit
- Logs are immutable JSONL; earlier rows are never rewritten.
- Each row stores artifact, parent signal, plan ID, metrics, and error traces.
- Cache by hash avoids recompute.

## Current status (as implemented)
- Core loop, CLI, scoring, reporting, and docs are present.
- Parallel candidate scoring and cache hits are functional.
- Notebook integration exists via `state/notes.md` snapshots before/after each batch.
- Merge mode is available but may be conservative depending on recent plateaus.

## Planned follow-ups
- Replace synthetic scorer with actual external judge/LLM subprocess backend.
- Add explicit parser-retry diagnostics for malformed proposal attempts.
- Add structured unit tests for splitter, scorer cache, and selector.
- Add optional web dashboard for report rendering.
