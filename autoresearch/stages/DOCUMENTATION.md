# Stages module documentation

## Stage A (`stage_a.py`)
Summarises train-disagreement patterns into short false-positive / false-negative token descriptions.

## Stage B (`stage_b.py`)
Proposes `K` sibling candidates from one parent. Each sibling applies a single edit:
- threshold move
- bias move
- length penalty move
- keyword add/adjust

Each sibling gets a unique `plan_id` for attribution.

## Stage C (`stage_c.py`)
Selects the next parent by weighted dev metric score. If recent scores plateau, emits merge mode with top parents.

## Stage M (`stage_m.py`)
Merges two+ parents by averaging numeric fields and averaging shared keyword weights.
