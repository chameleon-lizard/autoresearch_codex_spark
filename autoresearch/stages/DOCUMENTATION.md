# Stages module documentation

## Stage A (`stage_a.py`)
Summarises train-disagreement patterns into compact false-positive / false-negative signals.

## Stage B (`stage_b.py`)
- Proposes up to 5 single-edit sibling candidates.
- Serialises candidate blocks with `<PROMPT>...</PROMPT>`.
- `propose_candidates(...)` executes a retry loop over configured temperatures, validates format, and writes `stage_b_attempt_<n>.txt` for any parse failure.
- Keeps proposal metadata (`plan_id`, `rationale`, `artifact_text`) required for plan attribution.

## Stage C (`stage_c.py`)
Selects next parent from history with a weighted dev-score objective and merges when recent history plateaus.

## Stage M (`stage_m.py`)
Merges two or more parent artifacts by averaging numeric fields and keyword tables.
