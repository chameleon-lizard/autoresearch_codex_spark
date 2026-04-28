from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List


def split_dataset(dataset: List[dict], train_ratio: float, dev_ratio: float, seed: int, limit: int | None = None):
    if limit is not None:
        dataset = dataset[:limit]

    if not dataset:
        return {"train": [], "dev": [], "test": []}

    by_label: Dict[int, List[dict]] = defaultdict(list)
    for row in dataset:
        by_label[int(row["label"])].append(row)

    rng = random.Random(seed)

    train: List[dict] = []
    dev: List[dict] = []
    test: List[dict] = []

    for _, rows in by_label.items():
        rows = list(rows)
        rng.shuffle(rows)
        n = len(rows)

        n_train = int(round(n * train_ratio))
        n_dev = int(round(n * dev_ratio))

        if n_train + n_dev > n:
            n_train = max(1, n - n_dev)
        n_test = n - n_train - n_dev
        if n_test < 0:
            n_test = max(0, n - n_train)

        train.extend(rows[:n_train])
        dev.extend(rows[n_train : n_train + n_dev])
        test.extend(rows[n_train + n_dev : n_train + n_dev + n_test])

    for split in (train, dev, test):
        rng.shuffle(split)

    return {"train": train, "dev": dev, "test": test}
