"""Autoresearch loop implementation.

The package follows a module layout mirroring the stages in the design document:
- core: deterministic data and state helpers
- scorer: artifact scoring + cache
- stages: proposer/diagnoser/selector/merger
- runner: orchestration loop and CLI glue points
"""

from .config import AutoresearchConfig, load_config
from .runner import LoopRunner

__all__ = ["AutoresearchConfig", "load_config", "LoopRunner"]
