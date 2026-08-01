"""Evaluate fail-closed campaign admission for one registry revision."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.registry.revision import (
    RegistryRevisionV1,
    admitted_repository_names,
    products_registry_hash,
)


class RegistryRevisionGateV1(BaseModel):
    """Fail-closed campaign admission result for one exact revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    revision_id: str
    eligible: bool
    reasons: list[str]
    checked_at: str
    current_products_registry_hash: str


def evaluate_registry_revision(
    revision: RegistryRevisionV1,
    products: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> RegistryRevisionGateV1:
    """Reject every incomplete, stale, pending, unexplained, or drifted revision."""

    checked_at = now or datetime.now(UTC)
    products_hash = products_registry_hash(products)
    reasons: list[str] = []
    if not revision.complete:
        reasons.append("source_scan_incomplete")
    if revision.source_failures:
        reasons.append("source_failures_present")
    fresh_until = datetime.fromisoformat(revision.fresh_until)
    if fresh_until.tzinfo is None:
        fresh_until = fresh_until.replace(tzinfo=UTC)
    if checked_at > fresh_until:
        reasons.append("source_scan_stale")
    if revision.pending_intake:
        reasons.append("pending_intake_present")
    if revision.unexplained_observations:
        reasons.append("unexplained_observations_present")
    if products_hash != revision.products_registry_hash:
        reasons.append("products_registry_hash_drift")
    if admitted_repository_names(products) != revision.admitted_repositories:
        reasons.append("admitted_denominator_drift")
    return RegistryRevisionGateV1(
        revision_id=revision.revision_id,
        eligible=not reasons,
        reasons=reasons,
        checked_at=checked_at.isoformat(),
        current_products_registry_hash=products_hash,
    )
