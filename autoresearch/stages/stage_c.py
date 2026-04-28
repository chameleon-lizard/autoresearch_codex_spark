from __future__ import annotations

from typing import Dict, List


def _score_candidate(record: Dict) -> float:
    metrics = record.get("metrics_dev", {})
    return 0.50 * metrics.get("kappa", 0.0) + 0.30 * metrics.get("macro_f1", 0.0) + 0.20 * metrics.get("spearman", 0.0)


def _recent_plateau(records: List[Dict]) -> bool:
    if len(records) < 4:
        return False
    scores = [_score_candidate(r) for r in records[-4:]]
    return max(scores) - min(scores) < 0.005


def select_parent(records: List[Dict], history_last_n: int = 5) -> Dict:
    if not records:
        return {"mode": "iter", "iter": -1, "rationale": "Initial bootstrap."}

    ranked = sorted(records, key=_score_candidate, reverse=True)
    best = ranked[0]
    if _recent_plateau(records) and len(records) >= 6:
        # Trigger a merge mode as an exploration cycle breaker.
        unique_top = sorted(ranked[:6], key=lambda r: r.get("metrics_dev", {}).get("kappa", 0.0), reverse=True)
        if len(unique_top) >= 2:
            return {
                "mode": "merge",
                "iter": None,
                "parent_iters": [int(unique_top[0]["iter"]), int(unique_top[1]["iter"])],
                "rationale": "Recent plateau detected. Re-synthesise from two strongest parents.",
            }

    # Keep recency signal alive by limiting to last N as fallback.
    if best.get("is_parent_next", False):
        return {"mode": "iter", "iter": int(best["iter"]), "rationale": "Best candidate is explicitly marked as next parent."}

    last_window = records[-max(1, history_last_n) :]
    if last_window:
        ranked_window = sorted(last_window, key=_score_candidate, reverse=True)
        return {
            "mode": "iter",
            "iter": int(ranked_window[0]["iter"]),
            "rationale": "Selected strongest candidate from recent context (history-limited).",
        }

    return {"mode": "iter", "iter": int(best["iter"]), "rationale": "Selected global best dev metric."}
