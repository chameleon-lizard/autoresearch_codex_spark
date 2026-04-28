from __future__ import annotations

import json
import random
import uuid
import hashlib
from typing import List

from ..core.utils import artifact_hash


def _load_artifact(raw: str):
    return json.loads(raw)


def _dump_artifact(artifact) -> str:
    return json.dumps(artifact, sort_keys=True, indent=2)


def _mutate_threshold(artifact, magnitude: float) -> dict:
    art = dict(artifact)
    art["threshold"] = round(float(art.get("threshold") or 0.0) + magnitude, 4)
    return art


def _mutate_bias(artifact, magnitude: float) -> dict:
    art = dict(artifact)
    art["bias"] = round(float(art.get("bias") or 0.0) + magnitude, 4)
    return art


def _mutate_keyword_add(artifact, token: str, weight: float, which: str) -> dict:
    art = dict(artifact)
    target = dict(art.get(f"{which}_keywords") or {})
    target[token] = round(float(target.get(token, 0.0)) + weight, 4)
    art[f"{which}_keywords"] = target
    return art


def _mutate_keyword_set(artifact, which: str, token: str, weight: float) -> dict:
    art = dict(artifact)
    target = dict(art.get(f"{which}_keywords") or {})
    target[token] = round(weight, 4)
    art[f"{which}_keywords"] = target
    return art


def _proposed_token_candidates(summary: str) -> List[str]:
    tokens = []
    for line in summary.replace("-", " ").replace(":", " ").replace(",", " ").split():
        clean = "".join(ch.lower() for ch in line if ch.isalpha())
        if len(clean) >= 4:
            tokens.append(clean)
    return list(dict.fromkeys(tokens))


def generate_sibling_candidates(parent_text: str, stage_a_summary: str, k: int, attempt: int = 0) -> List[dict]:
    base = _load_artifact(parent_text)
    candidates = []
    seed_material = f"{parent_text}|{stage_a_summary}|{attempt}".encode("utf-8")
    seed = int(hashlib.sha256(seed_material).hexdigest(), 16) & 0xFFFFFFFF
    random.seed(seed)

    token_candidates = _proposed_token_candidates(stage_a_summary)
    default_tokens = ["great", "good", "bad", "waste", "boring", "clear"]
    token_candidates.extend([t for t in default_tokens if t not in token_candidates])

    operations = [
        ("threshold_up", lambda a: _mutate_threshold(a, +0.05)),
        ("threshold_down", lambda a: _mutate_threshold(a, -0.05)),
        ("bias_up", lambda a: _mutate_bias(a, +0.03)),
        ("bias_down", lambda a: _mutate_bias(a, -0.03)),
        ("length_penalty_up", lambda a: dict(a, length_penalty=round(float(a.get("length_penalty") or 0.0) + 0.002, 4)),
        ),
        ("length_penalty_down", lambda a: dict(a, length_penalty=round(float(a.get("length_penalty") or 0.0) - 0.002, 4)),
        ),
    ]

    for i, (op_name, op) in enumerate(operations):
        if len(candidates) >= k:
            break
        modified = op(base)
        candidates.append(
            {
                "plan_id": f"{artifact_hash(parent_text)[:8]}_{op_name}_{i}_{uuid.uuid4().hex[:6]}",
                "rationale": f"Stage B single edit: {op_name}",
                "artifact_text": _dump_artifact(modified),
            }
        )

    token_ops = [
        lambda a, t=token_candidates[0]: _mutate_keyword_add(a, t, 0.45, "positive"),
        lambda a, t=token_candidates[1] if len(token_candidates) > 1 else token_candidates[0]: _mutate_keyword_set(a, "negative", t, -0.45),
    ]

    for idx, op in enumerate(token_ops):
        if len(candidates) >= k:
            break
        modified = op(base)
        candidates.append(
            {
                "plan_id": f"{artifact_hash(parent_text)[:8]}_token_{idx}_{uuid.uuid4().hex[:6]}",
                "rationale": "Stage B single edit: keyword adjustment",
                "artifact_text": _dump_artifact(modified),
            }
        )

    if not candidates:
        modified = _mutate_bias(base, 0.01)
        candidates.append(
            {
                "plan_id": f"{artifact_hash(parent_text)[:8]}_fallback_{uuid.uuid4().hex[:6]}",
                "rationale": "fallback single-step bias bump",
                "artifact_text": _dump_artifact(modified),
            }
        )

    return candidates[:k]
