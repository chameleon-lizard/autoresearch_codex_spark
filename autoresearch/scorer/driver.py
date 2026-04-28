from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

from ..core.utils import artifact_hash
from ..core.utils import write_atomic
from .predictor import evaluate_artifact


def _cache_path(cache_root: Path, hash_value: str) -> Path:
    return cache_root / hash_value / "result.json"


def read_cache(cache_root: Path, hash_value: str) -> Dict:
    path = _cache_path(cache_root, hash_value)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_cache(cache_root: Path, hash_value: str, artifact_text: str, score: Dict) -> None:
    payload = dict(score)
    payload["artifact_text"] = artifact_text
    path = _cache_path(cache_root, hash_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, json.dumps(payload, indent=2, sort_keys=True))


def score_single(artifact_text: str, splits: Dict[str, List[dict]], cache_root: Path) -> Dict:
    h = artifact_hash(artifact_text)
    cached = read_cache(cache_root, h)
    if cached:
        return cached
    score = evaluate_artifact(artifact_text, splits)
    score["artifact_hash"] = h
    write_cache(cache_root, h, artifact_text, score)
    return score


def score_candidates(candidates: List[str], splits: Dict[str, List[dict]], parallelism: int, cache_root: Path) -> Dict[str, Dict]:
    seen = {}
    output: Dict[str, Dict] = {}
    missing = []

    for text in candidates:
        h = artifact_hash(text)
        if h in seen:
            output[h] = seen[h]
            continue
        cached = read_cache(cache_root, h)
        if cached:
            output[h] = cached
        else:
            missing.append(text)
            seen[h] = None

    if not missing:
        return output

    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as ex:
        futures = {ex.submit(score_single, text, splits, cache_root): text for text in missing}
        for future in as_completed(futures):
            text = futures[future]
            result = future.result()
            h = artifact_hash(text)
            output[h] = result

    return output
