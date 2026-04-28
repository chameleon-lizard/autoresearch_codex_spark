from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .utils import append_jsonl_line


class ExperimentStore:
    def __init__(self, experiments_log: Path):
        self.log_path = experiments_log

    def append(self, payload: Dict[str, Any]) -> None:
        payload = dict(payload)
        payload.setdefault("ts", datetime.utcnow().isoformat() + "Z")
        append_jsonl_line(self.log_path, payload)

    def load(self) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # Keep parsing robust to interrupted writes.
                    continue
        return out

    def latest(self) -> Dict[str, Any] | None:
        rows = self.load()
        if not rows:
            return None
        return rows[-1]

    def filter(self, *, metric: str | None = None, split: str = "dev") -> List[Dict[str, Any]]:
        rows = self.load()
        if not metric:
            return rows
        return [r for r in rows if r.get(f"metrics_{split}", {}).get(metric) is not None]

    def reset(self) -> None:
        if self.log_path.exists():
            self.log_path.unlink()

    def by_hash(self, artifact_hash: str) -> List[Dict[str, Any]]:
        return [r for r in self.load() if r.get("artifact_hash") == artifact_hash]

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
