# Report generator documentation

`generate_report(records, output)` reads append-only rows from `experiments.jsonl` and renders:
- latest best-dev summary
- per-batch candidate table
- plan aggregate table (`proposed`, `wins`, `mean Δ`)

The report is deterministic and can be regenerated at any time with `loop report`.
