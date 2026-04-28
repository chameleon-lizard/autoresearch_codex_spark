from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StatePaths:
    root: Path

    @property
    def cache_dir(self) -> Path:
        return self.root / "cache"

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def iterations_dir(self) -> Path:
        return self.state_dir / "iterations"

    @property
    def batches_dir(self) -> Path:
        return self.state_dir / "batches"

    @property
    def experiments_log(self) -> Path:
        return self.state_dir / "experiments.jsonl"

    @property
    def report_path(self) -> Path:
        return self.state_dir / "experiments_report.md"

    @property
    def notes_path(self) -> Path:
        return self.root / "notes.md"

    @property
    def metadata_path(self) -> Path:
        return self.state_dir / "metadata.json"

    @property
    def lockfile(self) -> Path:
        return self.state_dir / "loop.lock"

    def ensure(self) -> None:
        for p in [self.root, self.cache_dir, self.state_dir, self.iterations_dir, self.batches_dir, self.notes_path]:
            if p.suffix:
                continue
            p.mkdir(parents=True, exist_ok=True)
        if not self.notes_path.exists():
            self.notes_path.write_text("## USER\n\n## AGENT\n", encoding="utf-8")


def make_paths(state_dir: str) -> StatePaths:
    return StatePaths(Path(state_dir).expanduser().resolve())
