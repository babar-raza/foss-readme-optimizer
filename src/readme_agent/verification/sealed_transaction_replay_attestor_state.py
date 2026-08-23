"""Mutable attestation accumulator shared by replay proof phases."""

from __future__ import annotations

from dataclasses import dataclass, field

from readme_agent.evidence.redaction import redact_secret_like_values
from readme_agent.verification.sealed_transaction_replay_results import ReplayDriftFindingV1


@dataclass
class _AttestationState:
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    findings: list[ReplayDriftFindingV1] = field(default_factory=list)

    def record(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks[name] = bool(ok)
        if not ok:
            self.failures.append(redact_secret_like_values(detail or name)[:400])
        return bool(ok)
