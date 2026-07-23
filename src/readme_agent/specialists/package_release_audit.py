"""Package/release auditor (Wave 7c) -- domain `package_release_audit`, the
third domain-scoped specialist. Class D per `docs/github-surface-control.md`/
`repository-presentation-surface-model.md` (releases, packages):
product-agent owned, audit/handoff only *for the actual release/package
registry itself* -- `OWN-004`/`OWN-013` forbid this domain from publishing,
replacing, or editing a real GitHub Release or package-registry entry, and
this specialist has no such path. **Scope correction, 2026-07-22**: this does
not mean a package-resolution finding is a permanent dead end -- the README's
own presentation text describing a package coordinate is repository-file
content (`OWN-002`/`OWN-008`), a different domain's job
(`readme_presentation`/`readme_reconciliation`), not this one's. This
specialist's `HandoffFindingV1` record is this domain's own correct,
one-way output; a later reconciliation pass in the `readme_presentation`
domain may use the same underlying `verify_package_acquisition` evidence to
correct README prose -- that is not this specialist writing anything, it is
a different domain consuming the same verified fact.

Dispatches two capabilities: the new, domain-scoped `audit_package_release_
surfaces` (GitHub Releases) and the existing, unscoped `check_install_path`
(Wave 2 -- live Maven Central resolution via `ecosystems/resolver.py`),
rather than reimplementing package resolution a second time (GOVERNANCE.md
"no silent duplicates"). When the package fails to resolve against its
stated registry -- a real, common finding across this project's own
portfolio survey (`docs/presentation-standard.md`: "none of these FOSS
artifacts appear to be published to Maven Central yet") -- records a
minimal, one-way `HandoffFindingV1` (`state/schema.py`) into this domain's
`DomainStateV1.details["handoff_findings"]`. An empty release list is not
itself treated as an anomaly (many real FOSS repos legitimately never cut a
GitHub Release) -- only genuine package-resolution failure is handoff-worthy
here."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import PACKAGE_RELEASE_AUDIT
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.readme.facts import sha256_text
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import save_domain
from readme_agent.state.schema import DomainStateV1, HandoffFindingV1

DOMAIN = PACKAGE_RELEASE_AUDIT
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _fingerprint(audit: dict) -> str:
    canonical = json.dumps(audit, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def _dispatch(capability_id: str, org_repo: str):
    tool_call = {
        "function": {"name": capability_id, "arguments": json.dumps({"org_repo": org_repo})}
    }
    return dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)


def _classify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]

    release_dispatch = _dispatch("audit_package_release_surfaces", org_repo)
    if release_dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{release_dispatch.outcome}:{release_dispatch.error}"}
    assert release_dispatch.result is not None
    release_audit = release_dispatch.result

    install_dispatch = _dispatch("check_install_path", org_repo)
    if install_dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{install_dispatch.outcome}:{install_dispatch.error}"}
    assert install_dispatch.result is not None
    install_result = install_dispatch.result

    combined = {**release_audit, **install_result}
    fingerprint = _fingerprint(combined)
    classification = classify_surface(
        current_fingerprint=fingerprint, prior_fingerprint=state.accepted_facts_hash
    )

    handoff_findings: list[dict] = []
    if install_result.get("install_path_resolved") is False:
        finding = HandoffFindingV1(
            surface="packages",
            anomaly="install path did not resolve against the live package registry",
            evidence={"detail": install_result.get("evidence")},
        )
        handoff_findings.append(finding.model_dump(mode="json"))

    return {
        "accepted_facts_hash": fingerprint,
        "accepted_status": classification.classification,
        "details": {**combined, "handoff_findings": handoff_findings},
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
    prior accepted state for this domain (if any), runs the two-node graph,
    and returns the resulting `DomainStateV1` -- already durably recorded by
    the `record` node when `backend` is not `None`.

    `current_revision` (Wave 8.6, `ORC-003` reversal prerequisite): threaded
    through to `_record_node()`'s own `save_domain()` call -- see
    `state/domain_state.py::save_domain()`'s own docstring."""
    prior_domain_state = None
    if backend is not None:
        try:
            prior = backend.load(org_repo)
        except StateBackendError as exc:
            print(
                f"warning: durable state read failed, continuing without it: {exc}",
                file=sys.stderr,
            )
            prior = None
        if prior is not None:
            prior_domain_state = prior.domain_states.get(DOMAIN)

    initial_state = prior_domain_state or DomainStateV1(domain=DOMAIN)
    result = _GRAPH.invoke(
        initial_state,
        config={
            "configurable": {
                "org_repo": org_repo,
                "backend": backend,
                "current_revision": current_revision,
            }
        },
    )
    return DomainStateV1(**result)
