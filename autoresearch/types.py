from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DatasetRecord:
    id: int
    text: str
    label: int


@dataclass
class ScoreArtifacts:
    kappa: float
    macro_f1: float
    spearman: float


@dataclass
class ScoreResult:
    artifact_hash: str
    artifact_text: str
    metrics_train: Dict[str, float]
    metrics_dev: Dict[str, float]
    metrics_test: Dict[str, float]
    train_errors: List[Dict[str, Any]] = field(default_factory=list)
    dev_errors: List[Dict[str, Any]] = field(default_factory=list)
    test_errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CandidateResult:
    iteration: int
    batch_id: str
    ts: str
    artifact_hash: str
    artifact_text: str
    parent: Optional[str]
    plan_id: str
    rationale: str
    selection_mode: str
    selection_parent_ids: List[str]
    metrics_train: Dict[str, float]
    metrics_dev: Dict[str, float]
    metrics_test: Dict[str, float]
    diagnosis: str
    is_parent_next: bool = False
    errors_train: List[Dict[str, Any]] = field(default_factory=list)
    errors_dev: List[Dict[str, Any]] = field(default_factory=list)
    errors_test: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iter": self.iteration,
            "ts": self.ts,
            "artifact_hash": self.artifact_hash,
            "batch_id": self.batch_id,
            "parent": self.parent,
            "plan_id": self.plan_id,
            "rationale": self.rationale,
            "selection_mode": self.selection_mode,
            "selection_parent_ids": self.selection_parent_ids,
            "metrics_train": self.metrics_train,
            "metrics_dev": self.metrics_dev,
            "metrics_test": self.metrics_test,
            "diagnosis": self.diagnosis,
            "is_parent_next": self.is_parent_next,
            "artifact_text": self.artifact_text,
            "errors_train": self.errors_train,
            "errors_dev": self.errors_dev,
            "errors_test": self.errors_test,
        }
