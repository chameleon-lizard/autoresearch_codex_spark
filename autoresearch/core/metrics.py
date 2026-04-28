from __future__ import annotations

from typing import Dict, List


def _binary_confusion_matrix(labels: List[int], preds: List[int]):
    tp = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(labels, preds) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(labels, preds) if y == 1 and p == 0)
    return tp, tn, fp, fn


def cohen_kappa(labels: List[int], preds: List[int]) -> float:
    tp, tn, fp, fn = _binary_confusion_matrix(labels, preds)
    n = tp + tn + fp + fn
    if n == 0:
        return 0.0

    p0 = (tp + tn) / n
    p_yes_ref = (tp + fn) / n
    p_yes_sys = (tp + fp) / n
    p_no_ref = (tn + fp) / n
    p_no_sys = (tn + fn) / n
    pe = p_yes_ref * p_yes_sys + p_no_ref * p_no_sys
    if pe >= 1.0:
        return 0.0
    return (p0 - pe) / (1 - pe)


def macro_f1(labels: List[int], preds: List[int]) -> float:
    tp1, tn1, fp1, fn1 = _binary_confusion_matrix(labels, preds)
    def f1_for_class(pos: int) -> float:
        if pos == 1:
            tp, fp, fn = tp1, fp1, fn1
        else:
            tp, fp, fn = tn1, fn1, fp1
        denom = 2 * tp + fp + fn
        return (2 * tp / denom) if denom > 0 else 0.0
    return (f1_for_class(1) + f1_for_class(0)) / 2


def spearman(labels: List[int], probs: List[float]) -> float:
    # Small-n correlation on rank-transformed probabilities
    n = len(labels)
    if n < 2:
        return 0.0
    order = sorted(range(n), key=lambda i: probs[i])
    labels_rank = [0.0] * n
    for rank, idx in enumerate(order):
        labels_rank[idx] = rank

    probs_rank = list(range(n))
    mean_l = sum(labels) / n
    mean_r = (n - 1) / 2
    cov = sum((lbl - mean_l) * (r - mean_r) for lbl, r in zip(labels, labels_rank))
    var_l = sum((lbl - mean_l) ** 2 for lbl in labels)
    var_r = sum((i - mean_r) ** 2 for i in range(n))
    if var_l == 0 or var_r == 0:
        return 0.0
    return cov / (var_l ** 0.5 * var_r ** 0.5)


def compute_metrics(records: List[dict], scores_key: str = "probs") -> Dict[str, float]:
    labels = [int(r["label"]) for r in records]
    probs = [float(r[scores_key]) for r in records]
    preds = [1 if p >= 0.5 else 0 for p in probs]
    return {
        "kappa": round(cohen_kappa(labels, preds), 6),
        "macro_f1": round(macro_f1(labels, preds), 6),
        "spearman": round(spearman(labels, probs), 6),
        "size": len(records),
    }
