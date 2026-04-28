from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def _latest_batch(records: List[Dict], batch_id: str) -> List[Dict]:
    return [r for r in records if str(r.get("batch_id")) == str(batch_id)]


def generate_report(records: List[Dict], output: Path) -> None:
    if not records:
        output.write_text("# Autoresearch Report\n\nNo experiments have been run yet.\n", encoding="utf-8")
        return

    lines = ["# Autoresearch Report", "", "Generated from `experiments.jsonl` (append-only).", ""]

    lines.append("## Latest status")
    best = sorted(
        [r for r in records if isinstance(r.get("metrics_dev"), dict)],
        key=lambda r: r.get("metrics_dev", {}).get("kappa", 0.0)
        + 0.3 * r.get("metrics_dev", {}).get("macro_f1", 0.0),
        reverse=True,
    )
    if best:
        top = best[0]
        lines.extend(
            [
                f"- Best dev candidate: iter {top['iter']} / batch {top['batch_id']}",
                f"- Hash: `{top['artifact_hash']}`",
                f"- Dev metrics: κ={top['metrics_dev'].get('kappa', 0.0):.4f}, ",
                f"macro-F1={top['metrics_dev'].get('macro_f1', 0.0):.4f}, ",
                f"spearman={top['metrics_dev'].get('spearman', 0.0):.4f}",
            ]
        )

    lines.append("")
    lines.append("## By batch")
    batches = sorted({r.get("batch_id") for r in records})
    lines.extend(["| batch | iter | parent | plan | dev κ | dev F1 | dev Spearman | rationale |", "| --- | --- | --- | --- | --- | --- | --- | --- |",])
    for batch_id in batches:
        rows = sorted(_latest_batch(records, batch_id), key=lambda r: int(r.get("iter", 0)))
        for row in rows:
            m = row.get("metrics_dev", {})
            lines.append(
                f"| {batch_id} | {row.get('iter')} | {str(row.get('parent'))[:10]} | {row.get('plan_id')[:16]} | "
                f"{m.get('kappa', 0.0):.4f} | {m.get('macro_f1', 0.0):.4f} | {m.get('spearman', 0.0):.4f} | {row.get('rationale', '').replace('|', '-')[:80]} |"
            )

    plan_stats = defaultdict(lambda: {"proposed": 0, "wins": 0})
    if records:
        for i, row in enumerate(records):
            plan = row.get("plan_id", "unknown")
            plan_stats[plan]["proposed"] += 1
            if row.get("is_parent_next"):
                plan_stats[plan]["wins"] += 1

        lines.append("")
        lines.append("## Plan aggregates")
        lines.append("| plan_id | proposed | won_next | mean Δ dev κ |")
        lines.append("| --- | --- | --- | --- |")
        for plan_id, stat in sorted(plan_stats.items()):
            deltas = []
            for row in records:
                if row.get("plan_id") != plan_id:
                    continue
                deltas.append(row.get("metrics_dev", {}).get("kappa", 0.0))
            mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
            lines.append(f"| {plan_id} | {stat['proposed']} | {stat['wins']} | {mean_delta:.4f} |")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
