from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, Iterable, List


def split_dataset(dataset: List[dict], train_ratio: float, dev_ratio: float, seed: int, limit: int | None = None):
    if limit:
        dataset = dataset[:limit]

    if not dataset:
        return {"train": [], "dev": [], "test": []}

    by_label: Dict[int, List[dict]] = defaultdict(list)
    for row in dataset:
        by_label[int(row["label"])].append(row)

    random.Random(seed).shuffle(dataset)
    train: List[dict] = []
    dev: List[dict] = []
    test: List[dict] = []

    for _, rows in by_label.items():
        n = len(rows)
        n_train = max(1, int(n * train_ratio))
        n_dev = max(0, int(n * dev_ratio))
        n_test = n - n_train - n_dev
        if n_test <= 0:
            n_test = max(0, n - n_train)
        if n_train + n_dev + n_test != n:
            n_test = n - (n_train + n_dev)

        train.extend(rows[:n_train])
        dev.extend(rows[n_train : n_train + n_dev])
        test.extend(rows[n_train + n_dev : n_train + n_dev + n_test])

    # Deterministic per-label order then shuffle globally for reproducibility
    random.Random(seed).shuffle(train)
    random.Random(seed).shuffle(dev)
    random.Random(seed).shuffle(test)

    return {"train": train, "dev": dev, "test": test}
