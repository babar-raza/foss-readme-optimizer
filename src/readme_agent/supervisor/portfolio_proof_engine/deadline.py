"""Global deadline + per-stage timeout for one mode-driver invocation.

Mirrors the existing `--portfolio-time-budget-seconds` semantics in
`commands_supervision.py::_cmd_supervise_registry` (checked only *between* repositories, never
mid-stage) but generalizes it with an explicit per-stage timeout too. Every mode driver checks
`expired()` only between repositories/stages, after the current atomic receipt write completes --
so an expiring deadline always leaves the remaining work resumable and never converts a timeout
into a factual rejection.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DeadlineBudget:
    total_seconds: float | None
    per_stage_seconds: float | None = None
    _started: float = field(default_factory=time.monotonic, repr=False)

    def elapsed(self) -> float:
        return time.monotonic() - self._started

    def expired(self) -> bool:
        return self.total_seconds is not None and self.elapsed() >= self.total_seconds

    def remaining(self) -> float | None:
        if self.total_seconds is None:
            return None
        return max(0.0, self.total_seconds - self.elapsed())

    def stage_timed_out(self, stage_started_at: float) -> bool:
        if self.per_stage_seconds is None:
            return False
        return time.monotonic() - stage_started_at >= self.per_stage_seconds
