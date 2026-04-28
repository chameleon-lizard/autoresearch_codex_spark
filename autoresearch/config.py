from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _to_float_tuple(raw: Optional[str]) -> Tuple[float, ...]:
    if not raw:
        return (0.0, 0.4, 0.7, 0.9)
    values = [part.strip() for part in raw.split(",") if part.strip()]
    return tuple(float(v) for v in values)


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.loads(fp.read())


def default_initial_artifact() -> str:
    return json.dumps(
        {
            "version": 1,
            "threshold": 0.0,
            "bias": 0.0,
            "length_penalty": -0.001,
            "positive_keywords": {
                "great": 0.8,
                "excellent": 0.75,
                "love": 0.65,
                "wonderful": 0.62,
                "recommend": 0.6,
            },
            "negative_keywords": {
                "bad": -0.7,
                "hate": -0.85,
                "terrible": -0.8,
                "boring": -0.7,
                "waste": -0.85,
            },
        },
        indent=2,
        sort_keys=True,
    )


@dataclass(frozen=True)
class AutoresearchConfig:
    state_dir: str = ".autoresearch_state"
    dataset_path: str = "data/ground_truth.jsonl"
    batch_size: int = 3
    parallelism: int = 4
    random_seed: int = 42
    split_train_ratio: float = 0.4
    split_dev_ratio: float = 0.2
    split_test_ratio: float = 0.4
    max_retries: int = 4
    retry_temperatures: Tuple[float, ...] = (0.0, 0.4, 0.7, 0.9)
    history_last_n: int = 5
    initial_artifact: str = None

    def __post_init__(self):
        object.__setattr__(self, "initial_artifact", self.initial_artifact or default_initial_artifact())


def load_config(config_path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> AutoresearchConfig:
    """Load config from JSON/env/defaults.

    The design intentionally keeps CLI surface minimal: most behaviour is in this
    config object and environment variables.
    """

    values: Dict[str, Any] = {}

    if config_path is None:
        config_path = os.environ.get("AUTORESEARCH_CONFIG_PATH")
    if config_path:
        loaded = _read_json(Path(config_path))
        values.update(loaded)

    env_overrides = {
        "state_dir": os.environ.get("AUTORESEARCH_STATE_DIR"),
        "dataset_path": os.environ.get("AUTORESEARCH_DATASET_PATH"),
        "batch_size": os.environ.get("AUTORESEARCH_BATCH_SIZE"),
        "parallelism": os.environ.get("AUTORESEARCH_PARALLELISM"),
        "random_seed": os.environ.get("AUTORESEARCH_RANDOM_SEED"),
        "split_train_ratio": os.environ.get("AUTORESEARCH_TRAIN_RATIO"),
        "split_dev_ratio": os.environ.get("AUTORESEARCH_DEV_RATIO"),
        "split_test_ratio": os.environ.get("AUTORESEARCH_TEST_RATIO"),
        "retry_temperatures": os.environ.get("AUTORESEARCH_RETRY_TEMPERATURES"),
        "history_last_n": os.environ.get("AUTORESEARCH_HISTORY_LAST_N"),
        "initial_artifact": os.environ.get("AUTORESEARCH_INITIAL_ARTIFACT_JSON"),
    }

    for key, raw in env_overrides.items():
        if raw is None:
            continue
        if key == "state_dir" or key == "dataset_path" or key == "initial_artifact":
            values[key] = raw
        elif key == "retry_temperatures":
            values[key] = list(_to_float_tuple(raw))
        elif key in {"batch_size", "parallelism", "random_seed", "history_last_n"}:
            values[key] = int(raw)
        else:
            values[key] = float(raw)

    if overrides:
        values.update(overrides)

    # cast mutable defaults safely
    retry_temperatures = values.get("retry_temperatures")
    if retry_temperatures is not None and not isinstance(retry_temperatures, tuple):
        values["retry_temperatures"] = tuple(float(x) for x in retry_temperatures)

    config = AutoresearchConfig(**{**vars(AutoresearchConfig()), **values})

    if isinstance(config.retry_temperatures, list):
        object.__setattr__(config, "retry_temperatures", tuple(config.retry_temperatures))

    return config


def persist_config(path: Path, config: AutoresearchConfig) -> None:
    payload = {
        "state_dir": config.state_dir,
        "dataset_path": config.dataset_path,
        "batch_size": config.batch_size,
        "parallelism": config.parallelism,
        "random_seed": config.random_seed,
        "split_train_ratio": config.split_train_ratio,
        "split_dev_ratio": config.split_dev_ratio,
        "split_test_ratio": config.split_test_ratio,
        "max_retries": config.max_retries,
        "retry_temperatures": list(config.retry_temperatures),
        "history_last_n": config.history_last_n,
        "initial_artifact": config.initial_artifact,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
