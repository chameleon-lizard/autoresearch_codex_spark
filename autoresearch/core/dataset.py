from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, List

from .types import DatasetRecord


def _parse_dataset_line(raw: str) -> DatasetRecord:
    payload = json.loads(raw)
    return DatasetRecord(
        id=int(payload["id"]),
        text=str(payload["text"]),
        label=int(payload["label"]),
    )


def load_ground_truth_dataset(path: str, limit: int | None = None) -> List[DatasetRecord]:
    p = Path(path)
    if p.exists():
        with p.open("r", encoding="utf-8") as fp:
            rows = [_parse_dataset_line(line) for line in fp if line.strip()]
        if limit is not None:
            return rows[:limit]
        return rows

    # Deterministic synthetic fallback dataset
    random.seed(0)
    positives = [
        "great", "wonderful", "excellent", "positive", "uplifting", "amazing",
        "strong", "improved", "recommend", "clean", "clear",
    ]
    negatives = [
        "bad", "hate", "boring", "weak", "terrible", "broken",
        "slow", "poor", "waste", "hard", "noisy",
    ]
    records: List[DatasetRecord] = []
    for idx in range(1, 201):
        word = random.choice(positives if idx <= 100 else negatives)
        label = 1 if idx <= 100 else 0
        tail = random.choice([
            "the result was", "this review says", "the process is", "the sample looked",
            "users observed", "it felt",
        ])
        text = f"{tail} {word} and {random.choice(['clear', 'solid', 'fragile', 'confusing'])}"
        records.append(DatasetRecord(id=idx, text=text, label=label))

    if limit is not None:
        return records[:limit]
    return records


def dataset_to_list(records: List[DatasetRecord]) -> List[dict[str, Any]]:
    return [{"id": r.id, "text": r.text, "label": r.label} for r in records]
