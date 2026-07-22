"""Cross-surface validator (Wave 7f) -- domain `cross_surface_validation`,
the sixth specialist, and the first with no capability of its own. Mitigates
two specialists independently forming an opinion about the same underlying
fact (`OWN-011`'s own noted multi-specialist risk) by reading sibling
domains' already-recorded `DomainStateV1` entries directly via
`backend.load(org_repo)` -- no new capability dispatch, per the plan's own
scope for this sub-wave.

Today's one real comparison: `readme_reconciliation`'s `details
["license_claim"]` (what the README's own text currently says about its
license, added in this same wave via `classify_upstream_change`'s regex
classifier) against `community_files_presentation`'s `details[
"detected_license"]` (the LICENSE file's own classification, GitHub's SPDX
id first, falling back to file-content classification -- same `license.
auditor.detect_license()` `orchestrator.py` already uses). Both facts came
from Wave 7f's own minimal, additive enrichment of two already-shipped
specialists -- not a new business-logic capability, per `GOVERNANCE.md`
"no silent duplicates"/"thin wrapper" convention.

**This only works with a real backend.** Sibling domains' `record` nodes
write via `save_domain()` only when `backend is not None`; without one,
there is no way to see what an earlier-run sibling just computed in this
same pass (`supervisor/loop.py`'s specialist-tier loop does not thread an
in-memory results dict between specialists, by design -- `state/backend.py`
is the one shared channel). Degrades honestly, not silently: with no
backend, this domain reports on a fixed, stable fingerprint (still correctly
FIRST_OBSERVATION once, then NO_CHANGE forever after) and an empty
`inconsistencies` list, never fabricating a comparison it cannot make.

**Ordering, not just insertion-order luck**: `specialists/registry.py`'s new
`SpecialistManifest.depends_on` declares this domain depends on
`readme_reconciliation` and `community_files_presentation` -- checked at
build time (`_build()`) so a future reordering or mid-list insertion of a
new specialist fails loudly instead of silently reading stale/absent sibling
state."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.domains import (
    COMMUNITY_FILES_PRESENTATION,
    CROSS_SURFACE_VALIDATION,
    README_RECONCILIATION,
)
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1

DOMAIN = CROSS_SURFACE_VALIDATION
DEPENDS_ON = (README_RECONCILIATION, COMMUNITY_FILES_PRESENTATION)

# Stable, arbitrary fingerprint for the "no durable backend supplied" case --
# not derived from any real fact, just needs to be constant so a rerun with
# no backend still classifies FIRST_OBSERVATION once, then NO_CHANGE.
_NO_BACKEND_FINGERPRINT = sha256_text("cross_surface_validation:no_backend")


def _fingerprint(license_claim: str | None, detected_license: str | None) -> str:
    canonical = json.dumps(
        {"license_claim": license_claim, "detected_license": detected_license},
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_text(canonical)


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
                "inconsistencies": [],
                "note": "no durable state backend supplied -- cannot read sibling domain state",
            },
        }

    # A real backend but no prior RunStateV1 (e.g. every sibling this pass
    # failed and was isolated) is a normal, non-error case -- both facts
    # below stay None, correctly producing an empty comparison rather than
    # an error.
    sibling_run_state = config["configurable"].get("sibling_run_state")
    domain_states = sibling_run_state.domain_states if sibling_run_state is not None else {}
    readme_domain = domain_states.get(README_RECONCILIATION)
    community_domain = domain_states.get(COMMUNITY_FILES_PRESENTATION)
    license_claim = readme_domain.details.get("license_claim") if readme_domain else None
    detected_license = (
        community_domain.details.get("detected_license") if community_domain else None
    )

    # `MEM-005` (found by independent production-reliability review,
    # 2026-07-20): flags when a comparison above is being made against a
    # dependency that has no trustworthy persisted state, naming which
    # sibling and why, instead of silently treating an unavailable fact as
    # indistinguishable from "both sides genuinely agree." Two real,
    # checkable conditions from this domain's own backend-persisted read
    # (`accepted_status is None` -- the sibling has never once recorded a
    # successful run; an `"ERROR:"`-prefixed status -- forward-looking
    # defense, not reachable today since every specialist's own `_record_
    # node` already skips persisting an ERROR state, mirroring `repair.py::
    # classify_failure()`'s own `"validation_failed"` branch being similarly
    # forward-looking). **Honestly narrower than MEM-005's own full trigger
    # scenario**: a sibling that hard-fails in this *exact* pass (`supervisor/
    # loop.py`'s `except Exception` branch) produces an in-memory-only
    # `DomainStateV1`, never persisted -- this function only ever sees the
    # backend's last-persisted (potentially stale-from-an-earlier-run) record
    # for that sibling, which is normally a perfectly ordinary-looking status,
    # not `None`/`"ERROR:"`-prefixed. Closing that exact case would require
    # threading this run's in-memory `specialist_results` through the
    # generic `run_domain()`/`SpecialistManifest.run` dispatch signature used
    # by every specialist -- a larger, more invasive change than this
    # narrower, still-real fix, left open rather than silently claimed done.
    stale_sibling_data = {}
    for sibling_name, sibling_domain in (
        (README_RECONCILIATION, readme_domain),
        (COMMUNITY_FILES_PRESENTATION, community_domain),
    ):
        status = sibling_domain.accepted_status if sibling_domain is not None else None
        if status is None:
            stale_sibling_data[sibling_name] = "no persisted state -- never successfully recorded"
        elif status.startswith("ERROR:"):
            stale_sibling_data[sibling_name] = f"last persisted status was {status!r}"

    inconsistencies = []
    if (
        license_claim is not None
        and detected_license is not None
        and license_claim != detected_license
    ):
        inconsistencies.append(
            {
                "surface": "license",
                "description": (
                    f"README text claims license {license_claim!r} but the LICENSE file "
                    f"classifies as {detected_license!r}"
                ),
                "evidence": {
                    "readme_reconciliation_license_claim": license_claim,
                    "community_files_presentation_detected_license": detected_license,
                },
            }
        )

    fingerprint = _fingerprint(license_claim, detected_license)
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )
    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": {
            "inconsistencies": inconsistencies,
            "compared": {
                "readme_reconciliation_license_claim": license_claim,
                "community_files_presentation_detected_license": detected_license,
            },
            "stale_sibling_data": stale_sibling_data,
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
    (threaded through as `sibling_run_state`, so `_classify_node` sees the
    same read rather than hitting the backend a second time). Returns the
    resulting `DomainStateV1` -- already durably recorded by the `record`
    node when `backend` is not `None`.

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
