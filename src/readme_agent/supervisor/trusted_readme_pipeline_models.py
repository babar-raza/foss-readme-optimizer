"""Typed results for the canonical trusted README pipeline."""

from pydantic import BaseModel, ConfigDict

from readme_agent.state.lifecycle_schema import AssuranceReadmePocStatusV1


class TrustedReadmePipelineResultV1(BaseModel):
    """Terminal result of one canonical trusted-lane invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AssuranceReadmePocStatusV1
    reached: bool
    candidate_sha256: str | None = None
    evidence_dir: str | None = None
    blocked_reason: str | None = None
    cache_reused: bool = False
