from __future__ import annotations

import json
import math
from typing import Dict, List, Tuple

from ..core.metrics import compute_metrics


def _default_artifact() -> Dict[str, object]:
    return {
        "version": 1,
        "threshold": 0.0,
        "bias": 0.0,
        "length_penalty": 0.0,
        "positive_keywords": {},
        "negative_keywords": {},
    }


def parse_artifact(raw: str) -> Dict[str, object]:
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    base = _default_artifact()
    if isinstance(data, dict):
        base.update(data)
    return base


def _token_score(text: str, artifact: Dict[str, object]) -> float:
    lower = text.lower()
    score = float(artifact.get("bias") or 0.0)
    score += len(lower) * float(artifact.get("length_penalty") or 0.0)

    for token, weight in (artifact.get("positive_keywords") or {}).items():
        if token.lower() in lower:
            score += float(weight)
    for token, weight in (artifact.get("negative_keywords") or {}).items():
        if token.lower() in lower:
            score += float(weight)
    return score


def score_to_probability(score: float) -> float:
    return 1.0 / (1.0 + math.exp(-score))


def evaluate_records(records: List[dict], artifact: Dict[str, object]) -> Tuple[Dict[str, float], List[dict], List[dict], List[dict]]:
    output_rows = []
    for row in records:
        p = score_to_probability(_token_score(row["text"], artifact))
        pred = 1 if p >= float(artifact.get("threshold") or 0.0) else 0
        output_rows.append({
            "id": row["id"],
            "label": row["label"],
            "prob": round(p, 6),
            "pred": pred,
            "text": row["text"],
        })

    metrics = compute_metrics(output_rows, scores_key="prob")
    errors = [
        {"id": o["id"], "label": o["label"], "pred": o["pred"], "prob": o["prob"], "text": o["text"]}
        for o in output_rows
        if o["label"] != o["pred"]
    ]

    return metrics, errors, output_rows, []


def evaluate_artifact(artifact_text: str, splits: Dict[str, List[dict]]):
    artifact = parse_artifact(artifact_text)
    train_metrics, train_errors, _, _ = evaluate_records(splits["train"], artifact)
    dev_metrics, dev_errors, _, _ = evaluate_records(splits["dev"], artifact)
    test_metrics, test_errors, _, _ = evaluate_records(splits["test"], artifact)
    return {
        "metrics_train": train_metrics,
        "metrics_dev": dev_metrics,
        "metrics_test": test_metrics,
        "errors_train": train_errors,
        "errors_dev": dev_errors,
        "errors_test": test_errors,
    }
