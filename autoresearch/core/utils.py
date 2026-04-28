from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_artifact_text(text: str) -> str:
    """Canonicalise artifact text for stable hashing.

    If the artifact is valid JSON, serialise with stable key ordering; otherwise use
    raw text stripped of trailing newline characters.
    """
    if not text:
        return ""
    try:
        obj = json.loads(text)
        return json.dumps(obj, sort_keys=True, indent=None)
    except Exception:
        return text.strip()


def artifact_hash(text: str) -> str:
    normalised = canonical_artifact_text(text)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


def write_atomic(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", encoding="utf-8") as fp:
        fp.write(data)
        fp.flush()
    tmp.replace(path)


def append_jsonl_line(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8", buffering=1) as fp:
        fp.write(line)
        fp.write("\n")
        fp.flush()
        os.fsync(fp.fileno())
