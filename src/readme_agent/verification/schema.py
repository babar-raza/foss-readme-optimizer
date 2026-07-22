"""Typed shape for a verifier's own verdict (Wave 8, `VER-001`/`VER-002`).
Stored as a plain dict (via `.model_dump(mode="json")`) inside the owning
domain's own `DomainStateV1.details["verification"]`, mirroring
`HandoffFindingV1`'s already-established "validated shape embedded in the
existing generic escape hatch" convention -- not a new top-level `RunStateV1`
field, which would reintroduce the single-slot-for-multiple-writers bug
decisions #32/#34 already found and fixed.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class VerificationVerdictV1(BaseModel):
    domain: str
    capability_id: str
    verdict: Literal["accept", "reject"]
    reason: str | None = None
    checks: dict[str, bool] = Field(default_factory=dict)
    requirement_map: dict[str, bool] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
