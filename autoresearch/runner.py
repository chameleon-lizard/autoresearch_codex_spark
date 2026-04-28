from __future__ import annotations

import argparse
import json
import os
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
from .scorer.driver import score_single
from .scorer.predictor import evaluate_artifact
from .stages import diagnose_failures, merge_artifacts, propose_candidates, select_parent
from .stages.stage_b import StageBParseError
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

    def _select_parent(self, records):
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

    def _score_single_text(self, artifact_text: str, splits):
        return score_single(artifact_text, splits, self.paths.cache_dir)

    def _candidate_key(self, row: dict) -> float:
        metrics = row.get("metrics_dev", {})
        return 0.50 * metrics.get("kappa", 0.0) + 0.30 * metrics.get("macro_f1", 0.0) + 0.20 * metrics.get("spearman", 0.0)

    def _history_context(self, records):
        if not records:
            return "No history yet."

        lines = []
        lines.append("## Best-so-far lineage\n")
        valid = [r for r in records if isinstance(r.get("metrics_dev"), dict)]
        if valid:
            best = sorted(valid, key=lambda r: self._candidate_key(r), reverse=True)[0]
            lines.append(
                "BEST_ITER={iter} parent={parent} plan={plan} dev_kappa={dev[kappa]} macro_f1={dev[macro_f1]} spearman={dev[spearman]}\n".format(
                    iter=best["iter"],
                    parent=best.get("parent"),
                    plan=best.get("plan_id"),
                    dev={
                        "kappa": best["metrics_dev"].get("kappa", 0.0),
                        "macro_f1": best["metrics_dev"].get("macro_f1", 0.0),
                        "spearman": best["metrics_dev"].get("spearman", 0.0),
                    },
                )
            )
            lines.append(f"BEST_ARTIFACT:\n{best.get('artifact_text', '')[:900]}\n")

        lines.append("## Recent history\n")
        for row in records[-max(1, self.config.history_last_n) :]:
            dev = row.get("metrics_dev", {})
            line = (
                f"iter={row.get('iter')} batch={row.get('batch_id')} parent={row.get('parent')} plan={row.get('plan_id')} "
                f"kappa={dev.get('kappa', 0.0):.4f} f1={dev.get('macro_f1', 0.0):.4f} rho={dev.get('spearman', 0.0):.4f}"
            )
            lines.append(line)

        compact = [
            f"iter={r.get('iter')} batch={r.get('batch_id')} parent={r.get('parent')} plan={r.get('plan_id')}"
            f" score={self._candidate_key(r):.4f}"
            for r in records
            if int(r.get("iter", 0)) != 0
        ]
        lines.append("\n## Compact history entries")
        for line in compact[: min(len(compact), 40)]:
            lines.append(f"- {line}")

        return "\n".join(lines)

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

        lock_payload = {
            "pid": os.getpid(),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "state_dir": str(self.paths.root),
        }
        self.paths.lockfile.write_text(json.dumps(lock_payload, indent=2), encoding="utf-8")

        max_batches = max_iters if max_iters is not None else 10_000_000

        try:
            for _ in range(max_batches):
                records = self.store.load()
                batch_index = len(records)
                batch_id = str(batch_index).zfill(3)
                batch_dir = self.paths.batches_dir / batch_id
                batch_dir.mkdir(parents=True, exist_ok=True)

                notes_before = self._read_notes()
                (batch_dir / "notes_before.md").write_text(notes_before, encoding="utf-8")

                decision = self._select_parent(records)
                print(f"[batch {batch_id}] Stage C decision: {decision['mode']}")
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

                parent_score = None
                for row in reversed(records):
                    if row["artifact_text"] == parent_artifact:
                        parent_score = row
                        break
                if not parent_score:
                    parent_score = self._score_single_text(parent_artifact, splits)

                summary = diagnose_failures(parent_score.get("errors_train", []))
                history_render = self._history_context(records)
                note_snapshot = self._read_notes()
                summary = summary + "\n\n" + history_render + "\n\nuser_notes:\n" + note_snapshot

                print(f"[batch {batch_id}] Stage A summary (preview): {summary[:1200]}")

                candidate_count = max(1, min(self.config.batch_size, 5))
                try:
                    candidates = propose_candidates(
                        parent_artifact,
                        summary,
                        k=candidate_count,
                        retry_temperatures=self.config.retry_temperatures,
                        batch_dir=batch_dir,
                        max_retries=self.config.max_retries,
                    )
                except StageBParseError:
                    candidates = [
                        {
                            "plan_id": f"{artifact_hash(parent_artifact)[:8]}_fallback_parent_{batch_id}",
                            "rationale": "fallback because Stage-B parse failed",
                            "artifact_text": parent_artifact,
                        }
                    ]

                candidate_texts = [c["artifact_text"] for c in candidates]
                scored = score_candidates(candidate_texts, splits, self.config.parallelism, self.paths.cache_dir)
                by_hash = {artifact_hash(text): text for text in candidate_texts}

                known_hashes = {r.get("artifact_hash") for r in records}
                candidate_rows = []
                for _, (score_key, payload) in enumerate(sorted(scored.items(), key=lambda item: item[0])):
                    if score_key in known_hashes:
                        continue
                    iteration = self._next_iteration()
                    candidate = by_hash[score_key]
                    candidate_meta = next((c for c in candidates if c["artifact_text"] == candidate), {})
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
                            metrics_train=payload.get("metrics_train", {}),
                            metrics_dev=payload.get("metrics_dev", {}),
                            metrics_test=payload.get("metrics_test", {}),
                            diagnosis=summary,
                            is_parent_next=False,
                            errors_train=payload.get("errors_train", []),
                            errors_dev=payload.get("errors_dev", []),
                            errors_test=payload.get("errors_test", []),
                        ).to_dict()
                    )
                    known_hashes.add(score_key)

                if candidate_rows:
                    best_candidate = max(candidate_rows, key=lambda row: self._candidate_key(row))
                    best_hash = best_candidate["artifact_hash"]
                    for row in candidate_rows:
                        if row["artifact_hash"] == best_hash:
                            row["is_parent_next"] = True
                            break

                    for row in candidate_rows:
                        self.store.append(row)
                else:
                    print(f"[batch {batch_id}] No non-duplicate proposals produced. Generating fallback variant.")
                    fallback = self._score_single_text(parent_artifact, splits)
                    fallback_row = CandidateResult(
                        iteration=self._next_iteration(),
                        batch_id=batch_id,
                        ts=datetime.utcnow().isoformat() + "Z",
                        artifact_hash=fallback.get("artifact_hash", artifact_hash(parent_artifact)),
                        artifact_text=parent_artifact,
                        parent=parent_label,
                        plan_id="fallback",
                        rationale="no-new-hash batch fallback",
                        selection_mode=decision["mode"],
                        selection_parent_ids=decision.get("parent_iters", []),
                        metrics_train=fallback.get("metrics_train", {}),
                        metrics_dev=fallback.get("metrics_dev", {}),
                        metrics_test=fallback.get("metrics_test", {}),
                        diagnosis=summary,
                        is_parent_next=True,
                        errors_train=fallback.get("errors_train", []),
                        errors_dev=fallback.get("errors_dev", []),
                        errors_test=fallback.get("errors_test", []),
                    ).to_dict()
                    self.store.append(fallback_row)

                records = self.store.load()
                generate_report(records, self.paths.report_path)

                notes_after = self._read_notes()
                (batch_dir / "notes_after.md").write_text(notes_after, encoding="utf-8")

                metadata = {
                    "last_batch_id": batch_id,
                    "last_iter": records[-1]["iter"] if records else 0,
                    "last_decision": decision,
                    "last_parent_label": parent_label,
                    "candidates_proposed": len(candidate_rows),
                    "ts": datetime.utcnow().isoformat() + "Z",
                }
                (self.paths.metadata_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")

                if max_iters is not None and len(records) >= max_iters + 1:
                    break

                time.sleep(0)
        finally:
            if self.paths.lockfile.exists():
                self.paths.lockfile.unlink()

    def report(self) -> str:
        records = self.store.load()
        generate_report(records, self.paths.report_path)
        return str(self.paths.report_path)

    def reset(self) -> None:
        self.paths.experiments_log.unlink(missing_ok=True)
        self.paths.report_path.unlink(missing_ok=True)
        self.paths.metadata_path.unlink(missing_ok=True)
        self.paths.lockfile.unlink(missing_ok=True)
        if self.paths.batches_dir.exists():
            shutil.rmtree(self.paths.batches_dir)
        if self.paths.iterations_dir.exists():
            shutil.rmtree(self.paths.iterations_dir)
        self.paths.iterations_dir.mkdir(parents=True, exist_ok=True)
        self.paths.batches_dir.mkdir(parents=True, exist_ok=True)

    def score_artifact(self, artifact_source: str, limit: int | None = None):
        dataset = self._load_dataset(limit)
        splits = split_dataset(
            dataset,
            train_ratio=self.config.split_train_ratio,
            dev_ratio=self.config.split_dev_ratio,
            seed=self.config.random_seed,
            limit=limit,
        )
        return evaluate_artifact(artifact_source, splits)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("loop")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Start infinite or bounded loop")
    run_cmd.add_argument("--max-iters", type=int, default=None)
    run_cmd.add_argument("--limit", type=int, default=None)

    sub.add_parser("report", help="Regenerate report from log")

    sub.add_parser("reset", help="Reset state (keep cache)")

    score_cmd = sub.add_parser("score", help="Score one artifact")
    score_cmd.add_argument("artifact", type=str)
    score_cmd.add_argument("--limit", type=int, default=None)

    return parser


def parse_artifact_input(raw: str) -> str:
    p = Path(raw)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8")
    return raw
