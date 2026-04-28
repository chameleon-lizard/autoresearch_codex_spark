from __future__ import annotations

import json
from typing import Iterable, List


def _load(raw: str):
    return json.loads(raw)


def _dump(artifact) -> str:
    return json.dumps(artifact, sort_keys=True, indent=2)


def merge_artifacts(parent_artifacts: Iterable[str]) -> str:
    parents = [_load(raw) for raw in parent_artifacts]
    if not parents:
        return _dump({"version": 1})

    merged = {"version": 1}
    merged["threshold"] = sum(float(p.get("threshold", 0.0)) for p in parents) / len(parents)
    merged["bias"] = sum(float(p.get("bias", 0.0)) for p in parents) / len(parents)
    merged["length_penalty"] = sum(float(p.get("length_penalty", 0.0)) for p in parents) / len(parents)

    pos = {}
    neg = {}
    for parent in parents:
        for token, weight in (parent.get("positive_keywords") or {}).items():
            pos[token] = pos.get(token, 0.0) + float(weight)
        for token, weight in (parent.get("negative_keywords") or {}).items():
            neg[token] = neg.get(token, 0.0) + float(weight)
    merged["positive_keywords"] = {k: round(v / len(parents), 4) for k, v in pos.items()}
    merged["negative_keywords"] = {k: round(v / len(parents), 4) for k, v in neg.items()}
    return _dump(merged)
