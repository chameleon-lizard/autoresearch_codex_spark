from __future__ import annotations

import argparse
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

from . import config
from .core.dataset import dataset_to_list, load_ground_truth_dataset
from .core.paths import make_paths
from .core.splitter import split_dataset
from .core.state import ExperimentStore
from .core.types import CandidateResult
from .core.utils import artifact_hash
from .scorer.driver import score_candidates
from .stages import diagnose_failures, generate_sibling_candidates, merge_artifacts, select_parent
from .reporter import generate_report


class LoopRunner:
    def __init__(self, config_path: str | None = None, overrides: dict | None = None):
        self.config = config.load_config(config_path, overrides)
        self.paths = make_paths(self.config.state_dir)
        self.paths.ensure()
        self.store = ExperimentStore(self.paths.experiments_log)

    def _load_dataset(self, limit: int | None):
        rows = load_ground_truth_dataset(self.config.dataset_path, limit=limit)
        return dataset_to_list(rows)

    def _next_iteration(self) -> int:
        return len(self.store.load()) + 1

    def _select_parent(self):
        records = self.store.load()
        return select_parent(records, self.config.history_last_n)

    def _find_record(self, iteration: int):
        for row in self.store.load():
            if int(row.get("iter", -1)) == iteration:
                return row
        return None

    def _artifact_from_record(self, record):
        if record:
            return record.get("artifact_text")
        return self.config.initial_artifact

    def _read_notes(self) -> str:
        return self.paths.read_text(self.paths.notes_path)

    def run(self, max_iters: int | None = None, limit: int | None = None) -> None:
        dataset = self._load_dataset(limit)
        splits = split_dataset(
            dataset,
            train_ratio=self.config.split_train_ratio,
            dev_ratio=self.config.split_dev_ratio,
            seed=self.config.random_seed,
            limit=limit,
        )

        records = self.store.load()
        if not records:
            batch_id = "000"
            base = self.config.initial_artifact
            from .scorer.predictor import evaluate_artifact

            scores = evaluate_artifact(base, splits)
            seed_candidate = CandidateResult(
                iteration=0,
                batch_id=batch_id,
                ts=datetime.utcnow().isoformat() + "Z",
                artifact_hash=artifact_hash(base),
                artifact_text=base,
                parent=None,
                plan_id="init",
                rationale="bootstrap initial artifact",
                selection_mode="init",
                selection_parent_ids=[],
                metrics_train=scores["metrics_train"],
                metrics_dev=scores["metrics_dev"],
                metrics_test=scores["metrics_test"],
                diagnosis="",
                is_parent_next=True,
                errors_train=scores["errors_train"],
                errors_dev=scores["errors_dev"],
                errors_test=scores["errors_test"],
            )
            self.store.append(seed_candidate.to_dict())
            records.append(seed_candidate.to_dict())
            generate_report(records, self.paths.report_path)

        max_batches = max_iters if max_iters is not None else 10_000_000
        for _ in range(max_batches):
            records = self.store.load()
            batch_index = len(records)
            batch_id = str(batch_index).zfill(3)
            batch_dir = self.paths.batches_dir / batch_id
            batch_dir.mkdir(parents=True, exist_ok=True)

            notes_before = self._read_notes()
            (batch_dir / "notes_before.md").write_text(notes_before, encoding="utf-8")

            decision = self._select_parent()
            if decision["mode"] == "merge":
                parent_iters = decision.get("parent_iters", [])
                selected_records = [self._find_record(i) for i in parent_iters]
                selected_records = [r for r in selected_records if r]
                parent_artifact = merge_artifacts([r["artifact_text"] for r in selected_records])
                parent_label = "merge"
            else:
                parent_record = self._find_record(int(decision.get("iter", 0)))
                if parent_record is None:
                    parent_record = self._find_record(0)
                parent_artifact = self._artifact_from_record(parent_record)
                parent_label = f"iter={parent_record.get('iter', 0)}"

            # Candidate generation (Stage B) and parent diagnosis (Stage A)
            parent_score = None
            for row in reversed(records):
                if row["artifact_text"] == parent_artifact:
                    parent_score = row
                    break
            if not parent_score:
                parent_score = self._score_single_text(parent_artifact, splits)

            summary = diagnose_failures(parent_score.get("errors_train", []))
            note_snapshot = self._read_notes()
            summary = summary + "\n\n" + "notes:\n" + note_snapshot

            candidates = generate_sibling_candidates(
                parent_artifact,
                summary,
                k=max(1, min(self.config.batch_size, 5)),
            )

            candidate_texts = [c["artifact_text"] for c in candidates]
            scored = score_candidates(candidate_texts, splits, self.config.parallelism, self.paths.cache_dir)
            by_hash = {artifact_hash(text): text for text in candidate_texts}

            candidate_rows = []
            for _, (score_key, payload) in enumerate(sorted(scored.items(), key=lambda item: item[0])):
                iteration = self._next_iteration()
                candidate = by_hash[score_key]
                # map metadata from candidate descriptor
                candidate_meta = next((c for c in candidates if c["artifact_text"] == candidate), {})
                score = payload
                candidate_rows.append(
                    CandidateResult(
                        iteration=iteration,
                        batch_id=batch_id,
                        ts=datetime.utcnow().isoformat() + "Z",
                        artifact_hash=score_key,
                        artifact_text=candidate,
                        parent=parent_label,
                        plan_id=candidate_meta.get("plan_id", f"plan_{iteration}"),
                        rationale=candidate_meta.get("rationale", "stage_b:proposal"),
                        selection_mode=decision["mode"],
                        selection_parent_ids=decision.get("parent_iters", []),
                        metrics_train=score.get("metrics_train", {}),
                        metrics_dev=score.get("metrics_dev", {}),
                        metrics_test=score.get("metrics_test", {}),
                        diagnosis=summary,
                        is_parent_next=False,
                        errors_train=score.get("errors_train", []),
                        errors_dev=score.get("errors_dev", []),
                        errors_test=score.get("errors_test", []),
                    ).to_dict()
                )

            # mark local best and append rows
            if candidate_rows:
                best_candidate = max(candidate_rows, key=lambda row: row["metrics_dev"].get("kappa", 0.0))
                best_hash = best_candidate["artifact_hash"]
                for row in candidate_rows:
                    if row["artifact_hash"] == best_hash:
                        row["is_parent_next"] = True
                        break

                for row in candidate_rows:
                    self.store.append(row)

            records = self.store.load()
            generate_report(records, self.paths.report_path)

            notes_after = self._read_notes()
            (batch_dir / "notes_after.md").write_text(notes_after, encoding="utf-8")

            # persist lightweight metadata for resuming and diagnostics
            metadata = {
                "last_batch_id": batch_id,
                "last_iter": records[-1]["iter"],
                "last_decision": decision,
            }
            (self.paths.metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            time.sleep(0)

    def _score_single_text(self, artifact_text: str, splits):
        from .scorer.driver import score_single

        return score_single(artifact_text, splits, self.paths.cache_dir)

    def report(self) -> str:
        records = self.store.load()
        generate_report(records, self.paths.report_path)
        return str(self.paths.report_path)

    def reset(self) -> None:
        # Keep cache and dataset artifacts; clear only run state and reports.
        self.paths.experiments_log.unlink(missing_ok=True)
        self.paths.report_path.unlink(missing_ok=True)
        self.paths.metadata_path.unlink(missing_ok=True)
        if self.paths.batches_dir.exists():
            shutil.rmtree(self.paths.batches_dir)
        if self.paths.iterations_dir.exists():
            shutil.rmtree(self.paths.iterations_dir)
        self.paths.batches_dir.mkdir(parents=True, exist_ok=True)
        self.paths.iterations_dir.mkdir(parents=True, exist_ok=True)

    def score_artifact(self, artifact_source: str, limit: int | None = None):
        dataset = self._load_dataset(limit)
        splits = split_dataset(
            dataset,
            train_ratio=self.config.split_train_ratio,
            dev_ratio=self.config.split_dev_ratio,
            seed=self.config.random_seed,
            limit=limit,
        )
        from .scorer.predictor import evaluate_artifact

        return evaluate_artifact(artifact_source, splits)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("loop")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Start infinite or bounded loop")
    run_cmd.add_argument("--max-iters", type=int, default=None)
    run_cmd.add_argument("--limit", type=int, default=None)

    report_cmd = sub.add_parser("report", help="Regenerate report from log")

    reset_cmd = sub.add_parser("reset", help="Reset state (keep cache)")

    score_cmd = sub.add_parser("score", help="Score one artifact")
    score_cmd.add_argument("artifact", type=str)
    score_cmd.add_argument("--limit", type=int, default=None)

    return parser


def parse_artifact_input(raw: str) -> str:
    p = Path(raw)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8")
    return raw
