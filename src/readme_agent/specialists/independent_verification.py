"""Independent verification specialist (Wave 8b/8c) -- domain
`independent_verification`, the ninth specialist. This module's own `run()`
is the post-hoc, cross-domain-audit facet of `VER-001`'s two-facet design
(see `capabilities/domains.py`'s own docstring for the full design and the
in-graph pre-apply gate, the other facet -- wired directly into
`specialists/readme_presentation.py::_verify_node` instead, since that one
needs to run BEFORE `readme_presentation`'s own commit, not after every
domain's record step like this one).

Reads sibling `DomainStateV1` state the same way `cross_surface_validation`
already does -- no capability dispatch of its own. `details["checks_
performed"]` always names exactly what this run's own logic covers,
self-describing its real scope so a partial rollout never reads as a wider
audit than what actually ran (8b shipped `evidence_completeness` only; 8c
adds `requirement_mapping`/`adversarial_cross_domain`).

Honestly post-hoc, like `cross_surface_validation`: cannot block the current
run's already-applied effects (that's `_verify_node`'s job, in `readme_
presentation.py`), only surface a finding for the next planning turn or
scheduled run.

**8c's three additions:**
- **Requirement mapping** (`VER-001`'s own Build Checklist line): a coarse,
  honest "was the evidence-producing capability exercised and did it succeed
  this run" per `requirement_ids`-declaring capability -- never a semantic
  judgment of whether a requirement's prose acceptance text is satisfied
  (that stays a human `IMPLEMENTED` call, per `GOV-007`'s existing
  mechanical-vs-human distinction). Only capabilities with an unambiguous
  domain attribution are mapped this pass (data-driven via
  `_CAPABILITY_DOMAIN_OVERRIDE`, not an if/elif chain) -- an unscoped
  capability (e.g. `get_product_facts`) has no single owning domain to
  attribute a verdict to, and is honestly left unmapped rather than guessed.
- **Adversarial cross-domain check**: a second-order check on top of
  `cross_surface_validation`'s own first-order `inconsistencies` list -- did
  `readme_presentation` commit a real change in the same run a sibling
  already flagged an unresolved inconsistency about.
- **Failure-escalation visibility**: surfaces every sibling's
  `consecutive_failure_count`/`last_failure_reason` (Wave 8a) in one place,
  rather than requiring a human to check each domain individually.
"""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities import registry
from readme_agent.capabilities.domains import (
    COMMUNITY_FILES_PRESENTATION,
    CROSS_SURFACE_VALIDATION,
    GITHUB_GENERATED_SURFACE_AUDIT,
    INDEPENDENT_VERIFICATION,
    METADATA_PRESENTATION,
    PACKAGE_RELEASE_AUDIT,
    PRESENTATION_BENCHMARKING,
    README_PRESENTATION,
    README_RECONCILIATION,
    VISUAL_PREPARATION,
)
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1
from readme_agent.verification.completeness import check_evidence_complete

DOMAIN = INDEPENDENT_VERIFICATION
# Every other registered domain, in registration order -- checked at
# specialists/registry.py::_build() time (this specialist is registered
# last, so every dependency is already registered earlier, satisfying that
# gate) -- an explicit literal tuple, mirroring cross_surface_validation.
# DEPENDS_ON's own style, not a dynamic "all domains" computation.
DEPENDS_ON = (
    README_RECONCILIATION,
    GITHUB_GENERATED_SURFACE_AUDIT,
    PACKAGE_RELEASE_AUDIT,
    METADATA_PRESENTATION,
    COMMUNITY_FILES_PRESENTATION,
    CROSS_SURFACE_VALIDATION,
    README_PRESENTATION,
    VISUAL_PREPARATION,
    PRESENTATION_BENCHMARKING,
)

_CHECKS_PERFORMED = [
    "evidence_completeness",
    "requirement_mapping",
    "adversarial_cross_domain",
]

# Stable, arbitrary fingerprint for the "no durable backend supplied" case --
# not derived from any real fact, just needs to be constant so a rerun with
# no backend still classifies FIRST_OBSERVATION once, then NO_CHANGE.
_NO_BACKEND_FINGERPRINT = sha256_text("independent_verification:no_backend")

# Data, not conditional logic: capabilities dispatched from within a
# DIFFERENT domain's own specialist graph than their own `allowed_domains`
# declares. `commit_readme_write`/`verify_readme_candidate` are both
# dispatched from `specialists/readme_presentation.py`'s own render ->
# verify -> commit chain -- their real-run outcome lives in `readme_
# presentation`'s own `DomainStateV1`, not in a specialist registered under
# their own `allowed_domains` (`independent_verification` never runs
# `verify_readme_candidate` itself; it only reads sibling state, post-hoc).
_CAPABILITY_DOMAIN_OVERRIDE: dict[str, str] = {
    "commit_readme_write": README_PRESENTATION,
    "verify_readme_candidate": README_PRESENTATION,
    # Wave 8.6 (`VER-006` reversal): same reasoning as the two entries above
    # -- dispatched from readme_presentation's own _verify_node, under
    # caller_domain=INDEPENDENT_VERIFICATION, never from a specialist
    # registered under its own allowed_domains.
    "verify_prose_quality": README_PRESENTATION,
}


def _requirement_map(domain_states: dict) -> dict[str, dict]:
    requirement_map: dict[str, dict] = {}
    for manifest in registry.list_all():
        if not manifest.requirement_ids:
            continue
        owning_domain = _CAPABILITY_DOMAIN_OVERRIDE.get(
            manifest.capability_id,
            manifest.allowed_domains[0] if manifest.allowed_domains else None,
        )
        if owning_domain is None:
            continue  # unscoped -- no unambiguous domain attribution this pass
        sibling = domain_states.get(owning_domain)
        exercised = (
            sibling is not None
            and sibling.accepted_status is not None
            and not sibling.accepted_status.startswith("ERROR:")
        )
        for requirement_id in manifest.requirement_ids:
            requirement_map[requirement_id] = {
                "domain": owning_domain,
                "capability_id": manifest.capability_id,
                "exercised_without_error": exercised,
            }
    return requirement_map


def _adversarial_findings(domain_states: dict) -> list[dict]:
    cross_surface = domain_states.get(CROSS_SURFACE_VALIDATION)
    inconsistencies = cross_surface.details.get("inconsistencies", []) if cross_surface else []
    if not inconsistencies:
        return []

    readme = domain_states.get(README_PRESENTATION)
    committed = bool(readme and readme.details.get("committed"))
    if not committed:
        return []

    return [
        {
            "finding": "readme_presentation committed a real change in the same run "
            "cross_surface_validation flagged an unresolved cross-surface inconsistency",
            "inconsistencies": inconsistencies,
        }
    ]


def _failure_escalations(domain_states: dict) -> dict[str, dict]:
    escalations = {}
    for domain in DEPENDS_ON:
        sibling = domain_states.get(domain)
        if sibling is not None and sibling.consecutive_failure_count > 0:
            escalations[domain] = {
                "consecutive_failure_count": sibling.consecutive_failure_count,
                "last_failure_reason": sibling.last_failure_reason,
            }
    return escalations


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    backend_available = config["configurable"].get("backend_available", False)

    if not backend_available:
        classification = classify_surface(
            current_fingerprint=_NO_BACKEND_FINGERPRINT, prior_fingerprint=state.accepted_facts_hash
        )
        return {
            "accepted_facts_hash": _NO_BACKEND_FINGERPRINT,
            "accepted_status": classification.classification,
            "details": {
                "checks_performed": _CHECKS_PERFORMED,
                "completeness": {},
                "requirement_map": {},
                "adversarial_findings": [],
                "failure_escalations": {},
                "note": "no durable state backend supplied -- cannot read sibling domain state",
            },
        }

    # A real backend but no prior RunStateV1 (e.g. every sibling this pass
    # failed and was isolated, or this is the repo's very first run) is a
    # normal, non-error case -- every sibling below reads as absent, and
    # check_evidence_complete() correctly reports nothing missing for an
    # ERROR/None status rather than a false completeness alarm.
    sibling_run_state = config["configurable"].get("sibling_run_state")
    domain_states = sibling_run_state.domain_states if sibling_run_state is not None else {}

    completeness: dict[str, list[str]] = {}
    for domain in DEPENDS_ON:
        sibling = domain_states.get(domain)
        accepted_status = sibling.accepted_status if sibling is not None else None
        details = sibling.details if sibling is not None else {}
        missing = check_evidence_complete(domain, accepted_status, details)
        if missing:
            completeness[domain] = missing

    requirement_map = _requirement_map(domain_states)
    adversarial_findings = _adversarial_findings(domain_states)
    failure_escalations = _failure_escalations(domain_states)

    fingerprint = sha256_text(
        json.dumps(
            {
                "completeness": completeness,
                "requirement_map": requirement_map,
                "adversarial_findings": adversarial_findings,
                "failure_escalations": failure_escalations,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )
    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": {
            "checks_performed": _CHECKS_PERFORMED,
            "completeness": completeness,
            "requirement_map": requirement_map,
            "adversarial_findings": adversarial_findings,
            "failure_escalations": failure_escalations,
        },
    }


def _record_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    backend: StateBackend | None = config["configurable"].get("backend")
    org_repo = config["configurable"]["org_repo"]
    current_revision = config["configurable"].get("current_revision")
    timestamp = datetime.now(UTC).isoformat()

    if backend is not None and not (state.accepted_status or "").startswith("ERROR:"):
        try:
            save_domain(
                backend,
                org_repo,
                DOMAIN,
                state.model_copy(update={"domain": DOMAIN, "last_run_timestamp": timestamp}),
                current_revision=current_revision,
            )
        except StateBackendError as exc:
            print(
                f"warning: durable domain-state write-back failed, continuing without it: {exc}",
                file=sys.stderr,
            )
    return {"last_run_timestamp": timestamp}


def _build_graph():
    graph = StateGraph(DomainStateV1)
    graph.add_node("classify", _classify_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "record")
    graph.add_edge("record", END)
    return graph.compile()


_GRAPH = _build_graph()


def run(
    org_repo: str, backend: StateBackend | None, current_revision: str | None = None
) -> DomainStateV1:
    """Entry point `specialists/registry.py::run_domain()` calls. Loads the
    prior run state once -- both this domain's own prior accepted state (to
    seed the graph, like every other specialist) and the full `RunStateV1`
    (threaded through as `sibling_run_state`). Returns the resulting
    `DomainStateV1` -- already durably recorded by the `record` node when
    `backend` is not `None`.

    `current_revision` (Wave 8.6, `ORC-003` reversal prerequisite): threaded
    through to `_record_node()`'s own `save_domain()` call -- see
    `state/domain_state.py::save_domain()`'s own docstring."""
    prior = None
    if backend is not None:
        try:
            prior = backend.load(org_repo)
        except StateBackendError as exc:
            print(
                f"warning: durable state read failed, continuing without it: {exc}",
                file=sys.stderr,
            )
            prior = None

    prior_domain_state = prior.domain_states.get(DOMAIN) if prior is not None else None
    initial_state = prior_domain_state or DomainStateV1(domain=DOMAIN)
    result = _GRAPH.invoke(
        initial_state,
        config={
            "configurable": {
                "org_repo": org_repo,
                "backend": backend,
                "backend_available": backend is not None,
                "sibling_run_state": prior,
                "current_revision": current_revision,
            }
        },
    )
    return DomainStateV1(**result)
