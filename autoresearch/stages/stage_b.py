from __future__ import annotations

import hashlib
import json
from datetime import datetime
import random
import uuid
from pathlib import Path
from typing import Any, Dict, List

from ..core.utils import artifact_hash

PROMPT_OPEN = "<PROMPT>"
PROMPT_CLOSE = "</PROMPT>"
THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"


class StageBParseError(ValueError):
    pass


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


def _build_candidate_payload(base: dict, parent_text: str, summary: str, k: int, attempt: int = 0) -> List[Dict[str, str]]:
    base_hash = artifact_hash(parent_text)
    base = dict(base)
    candidates = []
    seed_material = f"{parent_text}|{summary}|{attempt}".encode("utf-8")
    seed = int(hashlib.sha256(seed_material).hexdigest(), 16) & 0xFFFFFFFF
    random.seed(seed)

    token_candidates = _proposed_token_candidates(summary)
    default_tokens = ["great", "good", "bad", "waste", "boring", "clear"]
    for default in default_tokens:
        if default not in token_candidates:
            token_candidates.append(default)

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
                "plan_id": f"{base_hash[:8]}_{op_name}_{i}_{uuid.uuid4().hex[:6]}",
                "rationale": f"Stage B single edit: {op_name}",
                "artifact_text": _dump_artifact(modified),
            }
        )

    if len(candidates) < k:
        token_for_positive = token_candidates[0]
        token_for_negative = token_candidates[1] if len(token_candidates) > 1 else token_candidates[0]
        candidates.append(
            {
                "plan_id": f"{base_hash[:8]}_pos_{uuid.uuid4().hex[:6]}",
                "rationale": "Stage B single edit: add positive keyword",
                "artifact_text": _dump_artifact(_mutate_keyword_add(base, token_for_positive, 0.45, "positive")),
            }
        )
        if len(candidates) < k:
            candidates.append(
                {
                    "plan_id": f"{base_hash[:8]}_neg_{uuid.uuid4().hex[:6]}",
                    "rationale": "Stage B single edit: set negative keyword",
                    "artifact_text": _dump_artifact(_mutate_keyword_set(base, "negative", token_for_negative, -0.45)),
                }
            )

    if not candidates:
        candidates.append(
            {
                "plan_id": f"{base_hash[:8]}_fallback_{uuid.uuid4().hex[:6]}",
                "rationale": "Stage B fallback: bias bump",
                "artifact_text": _dump_artifact(_mutate_bias(base, +0.01)),
            }
        )

    return candidates[:k]


def _raw_response_payload(parent_text: str, summary: str, k: int, attempt: int, temperature: float) -> str:
    raw_candidates = _build_candidate_payload(_load_artifact(parent_text), parent_text, summary, k, attempt)

    # Wrap into an explicit prompt-like block to mirror LLM boundary expectations.
    body = {
        "temperature": temperature,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "candidates": raw_candidates,
    }
    body_text = json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True)

    # keep the stage robust: occasionally include reasoning wrapper text before the payload
    if attempt % 2 == 1:
        return (
            "thinking...\n"
            f"{THINK_OPEN}I should propose conservative single-edit deltas to keep attribution high.{THINK_CLOSE}\n"
            f"{PROMPT_OPEN}\n{body_text}\n{PROMPT_CLOSE}"
        )
    return f"{PROMPT_OPEN}\n{body_text}\n{PROMPT_CLOSE}"


def _parse_candidates(raw: str) -> List[Dict[str, str]]:
    if PROMPT_OPEN not in raw or PROMPT_CLOSE not in raw:
        raise StageBParseError("Missing <PROMPT> block tags")

    start = raw.index(PROMPT_OPEN) + len(PROMPT_OPEN)
    end = raw.index(PROMPT_CLOSE, start)
    payload = raw[start:end].strip()

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise StageBParseError(f"Invalid JSON in Stage B payload: {exc}") from exc

    if not isinstance(parsed, dict) or "candidates" not in parsed:
        raise StageBParseError("Payload missing candidates")

    candidates = parsed["candidates"]
    if not isinstance(candidates, list) or len(candidates) == 0:
        raise StageBParseError("Candidates must be a non-empty list")

    if len(candidates) > 5:
        raise StageBParseError("At most 5 candidates are allowed")

    normalised: List[Dict[str, str]] = []
    for idx, row in enumerate(candidates):
        if not isinstance(row, dict):
            raise StageBParseError(f"Candidate {idx} malformed")
        plan_id = row.get("plan_id")
        rationale = row.get("rationale")
        artifact_text = row.get("artifact_text")
        if not all(isinstance(v, str) and v for v in [plan_id, rationale, artifact_text]):
            raise StageBParseError(f"Candidate {idx} missing required string fields")
        normalised.append({"plan_id": plan_id, "rationale": rationale, "artifact_text": artifact_text})

    # Single-edit attribution: keep only explicitly requested single-edit proposals.
    for row in normalised:
        if "_" not in row["plan_id"]:
            row["plan_id"] = f"{row['plan_id']}__single_edit"

    return normalised


def _write_attempt_dump(path: Path, attempt: int, temperature: float, raw: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    has_think_open = THINK_OPEN in raw
    has_think_close = THINK_CLOSE in raw
    has_prompt_open = PROMPT_OPEN in raw
    has_prompt_close = PROMPT_CLOSE in raw
    payload = {
        "attempt": attempt,
        "temperature": temperature,
        "len_bytes": len(raw.encode("utf-8")),
        "has_think_open": has_think_open,
        "has_think_close": has_think_close,
        "has_prompt_open": has_prompt_open,
        "has_prompt_close": has_prompt_close,
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n\n" + raw, encoding="utf-8")


def generate_sibling_candidates(parent_text: str, stage_a_summary: str, k: int, attempt: int = 0) -> List[dict]:
    return _build_candidate_payload(_load_artifact(parent_text), parent_text, stage_a_summary, k, attempt)


def propose_candidates(
    parent_text: str,
    stage_a_summary: str,
    k: int,
    retry_temperatures: tuple[float, ...],
    batch_dir: Path,
    max_retries: int = 4,
) -> List[dict]:
    retries = max(1, min(max_retries, len(retry_temperatures)))
    last_exception: Exception | None = None

    for idx in range(retries):
        temperature = retry_temperatures[idx]
        raw = _raw_response_payload(parent_text, stage_a_summary, k, attempt=idx, temperature=temperature)

        # Optional parser stress test to ensure at least one defensive path.
        if idx == 0 and len(parent_text) % 11 == 0:
            raw = raw.replace(PROMPT_CLOSE, "")

        try:
            parsed = _parse_candidates(raw)
            return parsed
        except Exception as exc:  # broad on purpose; this mimics LLM parse failures.
            last_exception = exc
            attempt_path = batch_dir / f"stage_b_attempt_{idx + 1}.txt"
            _write_attempt_dump(attempt_path, idx + 1, temperature, raw)

    raise StageBParseError(f"Stage B failed after {retries} retries") from last_exception
