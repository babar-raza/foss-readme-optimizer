"""Deterministic remaining-work and stop-authority contract."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.finding_status import classify_specialist_findings

# Ordered routes from an observed finding to general-planner-visible,
# read-only capabilities that can still add evidence or produce a candidate.
# The specialist tier remains responsible for domain-scoped capabilities.
_CAPABILITY_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "readme_presentation:STALE_NONCOMPLIANT",
        (
            "detect_readme_gaps",
            "get_product_facts",
            "verify_package_acquisition",
            "render_readme_candidate",
        ),
    ),
    (
        "readme_presentation:BLOCKED_VALIDATION_FAILED",
        (
            "detect_readme_gaps",
            "get_product_facts",
            "verify_package_acquisition",
            "render_readme_candidate",
        ),
    ),
    (
        "metadata_presentation:",
        ("get_product_facts", "verify_package_acquisition"),
    ),
    (
        "cross_surface_validation:",
        ("get_product_facts", "detect_readme_gaps"),
    ),
    (
        "presentation_benchmarking:",
        (
            "verify_package_acquisition",
            "check_install_path",
            "get_product_facts",
            "detect_readme_gaps",
            "render_readme_candidate",
        ),
    ),
)


class WorkLedgerV1(BaseModel):
    """One run's deterministic account of findings, proposals, and next work."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    unresolved_findings: tuple[str, ...] = ()
    ready_proposals: tuple[str, ...] = ()
    attempted_capability_ids: tuple[str, ...] = ()
    eligible_capability_ids: tuple[str, ...] = ()

    @property
    def stop_allowed(self) -> bool:
        """A planner may stop only when no deterministic next action remains."""

        return not self.eligible_capability_ids


def _routes_for_finding(finding: str) -> tuple[str, ...]:
    for prefix, capability_ids in _CAPABILITY_ROUTES:
        if finding.startswith(prefix):
            return capability_ids
    return ()


def build_work_ledger(
    specialist_results: Mapping[str, DomainStateV1] | None,
    *,
    attempted_capability_ids: Iterable[str] = (),
) -> WorkLedgerV1:
    """Build a stable ledger without trusting planner prose or stop requests."""

    finding_status = classify_specialist_findings(specialist_results)
    attempted = tuple(dict.fromkeys(attempted_capability_ids))
    attempted_set = set(attempted)
    eligible: list[str] = []
    for finding in finding_status.unresolved:
        for capability_id in _routes_for_finding(finding):
            if capability_id not in attempted_set and capability_id not in eligible:
                eligible.append(capability_id)
    return WorkLedgerV1(
        unresolved_findings=finding_status.unresolved,
        ready_proposals=finding_status.proposals,
        attempted_capability_ids=attempted,
        eligible_capability_ids=tuple(eligible),
    )
