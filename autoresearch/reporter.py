from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def _latest_batch(records: List[Dict], batch_id: str) -> List[Dict]:
    return [r for r in records if str(r.get("batch_id")) == str(batch_id)]


def _score(row: Dict) -> float:
    metrics = row.get("metrics_dev", {})
    return 0.50 * metrics.get("kappa", 0.0) + 0.30 * metrics.get("macro_f1", 0.0) + 0.20 * metrics.get("spearman", 0.0)


def _parent_iter_from_label(row: Dict) -> int | None:
    parent = row.get("parent")
    if isinstance(parent, str) and parent.startswith("iter="):
        try:
            return int(parent.split("=", 1)[1])
        except ValueError:
            return None
    return None


def generate_report(records: List[Dict], output: Path) -> None:
    if not records:
        output.write_text("# Autoresearch Report\n\nNo experiments have been run yet.\n", encoding="utf-8")
        return

    latest_by_iter = {int(r.get("iter", 0)): r for r in records}
    lines = ["# Autoresearch Report", "", "Generated from `experiments.jsonl` (append-only).", ""]

    lines.append("## Latest status")
    best = sorted([r for r in records if isinstance(r.get("metrics_dev"), dict)], key=_score, reverse=True)
    if best:
        top = best[0]
        lines.extend(
            [
                f"- Best candidate: iter {top['iter']} / batch {top['batch_id']}",
                f"- Hash: `{top['artifact_hash']}`",
                f"- Dev: κ={top['metrics_dev'].get('kappa', 0.0):.4f}, macro-F1={top['metrics_dev'].get('macro_f1', 0.0):.4f}, spearman={top['metrics_dev'].get('spearman', 0.0):.4f}",
                f"- Train: κ={top['metrics_train'].get('kappa', 0.0):.4f}, macro-F1={top['metrics_train'].get('macro_f1', 0.0):.4f}, spearman={top['metrics_train'].get('spearman', 0.0):.4f}",
                f"- Test: κ={top['metrics_test'].get('kappa', 0.0):.4f}, macro-F1={top['metrics_test'].get('macro_f1', 0.0):.4f}, spearman={top['metrics_test'].get('spearman', 0.0):.4f}",
            ]
        )

    lines.append("")
    lines.append("## By batch")
    batches = sorted({r.get("batch_id") for r in records})
    lines.extend(
        [
            "| batch | iter | parent | plan | dev κ | dev F1 | dev Spearman | test κ | test F1 | selection mode | rationale |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for batch_id in batches:
        rows = sorted(_latest_batch(records, batch_id), key=lambda r: int(r.get("iter", 0)))
        for row in rows:
            mdev = row.get("metrics_dev", {})
            mtest = row.get("metrics_test", {})
            lines.append(
                f"| {batch_id} | {row.get('iter')} | {str(row.get('parent'))[:10]} | {str(row.get('plan_id'))[:16]} | "
                f"{mdev.get('kappa', 0.0):.4f} | {mdev.get('macro_f1', 0.0):.4f} | {mdev.get('spearman', 0.0):.4f} | "
                f"{mtest.get('kappa', 0.0):.4f} | {mtest.get('macro_f1', 0.0):.4f} | {row.get('selection_mode', '-') } | {row.get('rationale', '').replace('|', '-')[:100]} |"
            )

    plan_stats = defaultdict(lambda: {"proposed": 0, "wins": 0, "deltas": []})

    for row in records:
        if int(row.get("iter", 0)) == 0:
            continue
        plan = row.get("plan_id", "unknown")
        plan_stats[plan]["proposed"] += 1
        if row.get("is_parent_next"):
            plan_stats[plan]["wins"] += 1

        parent_iter = _parent_iter_from_label(row)
        if parent_iter is None:
            continue
        parent_row = latest_by_iter.get(parent_iter)
        if not parent_row:
            continue

        child_kappa = row.get("metrics_dev", {}).get("kappa", 0.0)
        parent_kappa = parent_row.get("metrics_dev", {}).get("kappa", 0.0)
        plan_stats[plan]["deltas"].append(child_kappa - parent_kappa)

    lines.append("")
    lines.append("## Plan aggregates")
    lines.append("| plan_id | proposed | won_next | mean Δ=dev κ | mean abs Δ|")
    lines.append("| --- | --- | --- | --- | --- |")
    for plan_id, stat in sorted(plan_stats.items()):
        deltas = stat["deltas"]
        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        mean_abs = sum(abs(x) for x in deltas) / len(deltas) if deltas else 0.0
        lines.append(f"| {plan_id} | {stat['proposed']} | {stat['wins']} | {mean_delta:.4f} | {mean_abs:.4f} |")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
