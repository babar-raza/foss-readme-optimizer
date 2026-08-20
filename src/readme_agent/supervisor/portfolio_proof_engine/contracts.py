"""Typed 15-stage receipt model for the portfolio proof engine.

Distinct from `supervisor/portfolio_scheduler/contracts.py`'s sealed low-level
CANDIDATE_GENERATED/DETERMINISTIC_VALIDATED promotion receipts: that module is the sole
promotion authority for the durable `ReadmePocLifecycleStateV2`, tightly coupled to its own
status-transition rules. `ProofStageReceiptV1` never promotes or mutates that lifecycle -- it is
a read-only *observation*, written after driving a repository through the real entry points
(`commands_supervision.cmd_supervise`, `supervisor/intake.py`), of what stage the repository has
reached and what evidence proves it. Two receipts with the same `canonical_hash()` represent the
same observation and are never recomputed; a later stage's receipt must never reuse evidence
bound to a different source/facts/prompt/candidate identity than its own recorded hashes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from readme_agent.supervisor.portfolio_scheduler.contracts import canonical_sha256, utc_now_iso

ProofStageV1 = Literal[
    "INTAKE",
    "SOURCE_BOUND",
    "FACTS_READY",
    "SECTION_PACKETS_READY",
    "SECTIONS_AUTHORED",
    "CANDIDATE_ASSEMBLED",
    "DETERMINISTIC_VALIDATED",
    "FACTUAL_REVIEWED",
    "VISITOR_REVIEWED",
    "RUBRIC_SCORED",
    "ACCEPTED",
    "REASSESS_REQUIRED",
    "TERMINAL_SKIPPED",
    "BLOCKED_INPUT",
    "SYSTEM_FAILURE",
]

# Canonical forward progression, used only to pick the "latest" receipt and to derive a
# dashboard's next-causal-action -- never an execution order (REASSESS_REQUIRED/
# TERMINAL_SKIPPED/BLOCKED_INPUT/SYSTEM_FAILURE are terminal side-branches, not later stages).
STAGE_ORDER: tuple[ProofStageV1, ...] = (
    "INTAKE",
    "SOURCE_BOUND",
    "FACTS_READY",
    "SECTION_PACKETS_READY",
    "SECTIONS_AUTHORED",
    "CANDIDATE_ASSEMBLED",
    "DETERMINISTIC_VALIDATED",
    "FACTUAL_REVIEWED",
    "VISITOR_REVIEWED",
    "RUBRIC_SCORED",
    "ACCEPTED",
    "REASSESS_REQUIRED",
    "TERMINAL_SKIPPED",
    "BLOCKED_INPUT",
    "SYSTEM_FAILURE",
)

TERMINAL_STAGES: frozenset[ProofStageV1] = frozenset(
    {"ACCEPTED", "REASSESS_REQUIRED", "TERMINAL_SKIPPED", "BLOCKED_INPUT", "SYSTEM_FAILURE"}
)

ProofModeV1 = Literal["preflight", "facts-only", "canaries", "fleet", "failed-only"]

MODE_CAMPAIGN_SALT = "portfolio-proof-engine-campaign-v1"


def campaign_id_for_mode(mode: ProofModeV1) -> str:
    """Stable per-mode grouping key.

    Deliberately independent of registry content or time: resumability is proven per-repository,
    per-stage by each receipt's own bound hashes (source/facts/prompt/candidate/contract), not by
    varying the campaign identity. The same mode always writes into the same receipt tree, so a
    second identical invocation finds and reuses its own prior receipts.
    """

    return canonical_sha256({"salt": MODE_CAMPAIGN_SALT, "mode": mode})


class ProofStageReceiptV1(BaseModel):
    """One bound observation of a repository's progress through a proof stage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    ecosystem: str | None = None
    source_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,64}$")
    contract_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    facts_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    prompt_hash: str | None = None
    schema_hash: str | None = None
    version_hash: str | None = None
    candidate_hash: str | None = None
    predecessor_receipt_hash: str | None = None
    stage: ProofStageV1
    status: Literal["OK", "FAILED"] = "OK"
    failure_reason: str | None = Field(default=None, max_length=500)
    elapsed_seconds: float = Field(ge=0.0)
    provider_call_count: int = Field(ge=0)
    generated_at: str = Field(default_factory=utc_now_iso)

    @field_validator("org_repo")
    @classmethod
    def _org_repo_shape(cls, value: str) -> str:
        if value.count("/") != 1 or any(not part for part in value.split("/")):
            raise ValueError("org_repo must look like 'org/repo'")
        return value

    @field_validator("failure_reason")
    @classmethod
    def _failure_reason_bound_to_status(cls, value: str | None, info) -> str | None:
        status = info.data.get("status")
        if status == "FAILED" and not value:
            raise ValueError("a FAILED receipt requires a bounded failure_reason")
        if status == "OK" and value:
            raise ValueError("an OK receipt must not carry a failure_reason")
        return value

    def canonical_hash(self) -> str:
        return canonical_sha256(self.model_dump(mode="json", exclude={"generated_at"}))


class RubricAcceptanceOutcome(BaseModel):
    """The small, stable outcome contract `rubric.py`'s 30-criterion evaluator produces and
    `stage_classifier.py` consumes to distinguish RUBRIC_SCORED from ACCEPTED. Kept here (not in
    `rubric.py`) so the two modules never need to import each other."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    accepted: bool
    score: int = Field(ge=0, le=30)
    hard_disqualifier_count: int = Field(ge=0)
    missing_evidence_criteria: tuple[int, ...] = Field(default_factory=tuple)

    def bounded_summary(self) -> str:
        if self.accepted:
            return "30/30, zero hard disqualifiers"
        parts = [f"{self.score}/30"]
        if self.hard_disqualifier_count:
            parts.append(f"{self.hard_disqualifier_count} hard disqualifier(s)")
        if self.missing_evidence_criteria:
            parts.append(
                "missing evidence for criteria "
                + ",".join(str(i) for i in self.missing_evidence_criteria)
            )
        return "; ".join(parts)[:500]
