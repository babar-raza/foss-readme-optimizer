"""README presentation specialist (Wave 7g, extended Wave 8b) -- domain
`readme_presentation`, the seventh specialist, deliberately separate from the
read-only `readme_reconciliation` domain (a different concern: reconciliation
only classifies upstream drift, never renders or writes anything). This is
the one place in the whole project that dispatches a real mutating
capability.

Four-node graph, `render` -> `verify` -> `commit` -> `record` (Wave 8b added
`verify`; every other specialist is two nodes -- `readme_presentation` needs
the extra steps because the write itself is independently gated before it's
attempted, then gated again on a real durable backend and `mode == "full"`,
unlike a plain classify-then-persist domain):

- `render` dispatches the existing, unscoped, read-only `render_readme_
  candidate` -- computes the skip-vs-render decision and, only if a real
  gap exists, the one existing LLM call. No filesystem write happens here.
- `verify` (Wave 8b, `VER-001`) dispatches the new, domain-scoped
  `verify_readme_candidate` under `caller_domain=INDEPENDENT_VERIFICATION`
  -- a distinct capability, under a distinct domain, from `render`/`commit`'s
  own `README_PRESENTATION` (the one deliberate exception to "one module,
  one domain identity" in this codebase, documented in `capabilities/
  domains.py`). A reject sets `accepted_status` directly, reusing `commit`'s
  own already-existing `"ERROR:"`-prefix early-return guard below -- zero new
  logic needed there. Short-circuits (zero cost) when there's nothing to
  verify, protecting `VER-003`'s "no unnecessary work" on the common
  steady-state path.
- `commit`, only when `render` decided a write is actually needed
  (`needs_write`) and `verify` didn't reject, dispatches the new,
  domain-scoped `commit_readme_write` via `dispatch_gated_effect()` -- the
  real write, and, only when `mode == "full"`, one real local git commit
  into the local work clone (never pushed). Requires a real durable backend:
  `dispatch_gated_effect()`'s own signature takes `backend: StateBackend`,
  not `StateBackend | None` -- there is no idempotency ledger without one,
  so this specialist refuses to attempt a mutating dispatch at all rather
  than mutate unsafely, degrading honestly (a clear `details["note"]`, never
  a crash) exactly like `cross_surface_validation`'s own no-backend path.
- `record` persists this domain's `DomainStateV1`, same as every other
  specialist.

Every node touching `details` builds its return via `state/domain_state.py::
merge_details()`, never a bare `{"details": {...}}` literal -- `DomainStateV1.
details` has no LangGraph merge reducer (last-write-wins for the whole
field), and this is the first specialist graph with three-or-more sequential
nodes that each need to see accumulating `details` keys (found by
adversarial review during Wave 8 design: a naively-written `verify` node
would have silently erased `render`'s own `render_result` before `commit`'s
`assert render_result is not None` ever ran).

`accepted_status` uses the same generic FIRST_OBSERVATION/NO_CHANGE/CHANGED
verdict every other domain uses (via `facts_hash` directly, decision #11's
own canonical "did the underlying facts change" signal) -- never the
orchestrator's own GENERATED/COMPLIANT_NO_CHANGE/STALE_NONCOMPLIANT
vocabulary, which lives in `details["render_status"]` instead. Using that
vocabulary directly as `accepted_status` would break the supervisor's
`CONVERGED_NO_TRACKED_CHANGE` shortcut permanently for this domain, since it
checks the literal string `"NO_CHANGE"` -- the same correction already made
for `metadata_presentation` (Wave 7d) applies here for the same reason.

Unifies the accepted-state ledger with the CLI path's own (`ORC-004`):
`commit_readme_write`'s executor stays deliberately stateless (decision
#26(b)) -- this specialist's own `commit` node calls `orchestrator.
record_accepted_readme_state()` directly after a successful write, using its
own durable backend from `config["configurable"]`, exactly matching every
other specialist's `record` node being the sole owner of durable writes."""

import json
import sys
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import generate_run_id
from readme_agent.orchestrator import record_accepted_readme_state
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import merge_details, save_domain_with_failure_tracking
from readme_agent.state.schema import DomainStateV1
from readme_agent.verification.checks import compute_verification_token

DOMAIN = README_PRESENTATION
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}
_WRITE_PERMISSIONS: set[PermissionClass] = _READ_ONLY_PERMISSIONS | {"local_write"}
# Wave 8.6 (`VER-006` reversal): no operational history yet to justify a
# different value -- mirrors ESCALATION_ALERT_THRESHOLD's/DOSSIER_TOKEN_
# BUDGET's own precedent. Known, honest limitation: `render_readme_candidate`
# has no "repair hint" input yet, so a bounded regenerate-and-reverify retry
# may re-produce an identical paragraph at temperature=0.0 -- still safe
# (bounded, never silently commits a still-flagged candidate, correctly
# escalates to BLOCKED once exhausted), just not guaranteed to *fix*
# anything without a future hint-threading follow-up.
MAX_PROSE_REPAIR_ATTEMPTS = 2


def _render_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    org_repo = config["configurable"]["org_repo"]
    arguments: dict = {"org_repo": org_repo}
    # Production-reliability fix (found by independent review, 2026-07-20):
    # without this, a fresh work clone -- the normal case on an ephemeral CI
    # runner, RUN-001 -- can never see this domain's own prior accepted
    # facts_hash, so the render pipeline's durable-skip path never engages
    # here, unlike orchestrator.py's own CLI path (decision #38). The result
    # was a real LLM call on every single run with any upstream commit at
    # all, not just one touching tracked content. This domain's own
    # DomainStateV1, recorded durably by `_commit_node` below, already IS
    # the accepted record needed -- supplied here as plain values, keeping
    # `render_readme_candidate` itself stateless (decision #26(b)).
    if state.accepted_facts_hash is not None:
        arguments["prior_facts_hash"] = state.accepted_facts_hash
        prior_fingerprint = state.details.get("fresh_fingerprint")
        if prior_fingerprint is not None:
            arguments["prior_content_fingerprint"] = prior_fingerprint
        prior_status = state.details.get("render_status")
        if prior_status is not None:
            arguments["prior_status"] = prior_status

    tool_call = {
        "function": {"name": "render_readme_candidate", "arguments": json.dumps(arguments)}
    }
    dispatch = dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)
    if dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}

    assert dispatch.result is not None
    return {"details": merge_details(state, render_result=dispatch.result)}


def _dispatch_verify_readme_candidate(org_repo: str, render_result: dict):
    verify_tool_call = {
        "function": {
            "name": "verify_readme_candidate",
            "arguments": json.dumps(
                {
                    "org_repo": org_repo,
                    "facts_hash": render_result["facts_hash"],
                    "fresh_fingerprint": render_result["fresh_fingerprint"],
                    "status": render_result["status"],
                    "needs_write": render_result["needs_write"],
                    "final_text": render_result["final_text"],
                }
            ),
        }
    }
    return dispatch_tool_call(
        verify_tool_call, _READ_ONLY_PERMISSIONS, caller_domain=INDEPENDENT_VERIFICATION
    )


def _dispatch_prose_quality_check(
    org_repo: str, final_text: str, state_backend: StateBackend | None = None
):
    prose_tool_call = {
        "function": {
            "name": "verify_prose_quality",
            "arguments": json.dumps({"org_repo": org_repo, "final_text": final_text}),
        }
    }
    return dispatch_tool_call(
        prose_tool_call,
        _READ_ONLY_PERMISSIONS,
        caller_domain=INDEPENDENT_VERIFICATION,
        state_backend=state_backend,
    )


def _dispatch_regenerate(org_repo: str):
    render_tool_call = {
        "function": {
            "name": "render_readme_candidate",
            "arguments": json.dumps({"org_repo": org_repo, "force_regenerate": True}),
        }
    }
    return dispatch_tool_call(render_tool_call, _READ_ONLY_PERMISSIONS, caller_domain=DOMAIN)


def _verify_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    """Wave 8b (`VER-001`): the independent verifier's pre-apply gate --
    dispatches `verify_readme_candidate` under `caller_domain=
    INDEPENDENT_VERIFICATION`, a distinct capability under a distinct domain
    from this module's own `render`/`commit` nodes. A reject sets
    `accepted_status` directly to the same `"ERROR:"`-prefixed shape every
    other failure in this graph already uses -- `_commit_node`'s own
    existing top-of-function guard (below) then skips the write with zero
    new logic there.

    Wave 8.6 (`VER-006` reversal): additive, only ever consulted AFTER the
    deterministic gate above has already accepted -- zero extra cost on a
    deterministic reject, protecting VER-003's "no unnecessary work". A
    corroborated prose-quality flag triggers a bounded regenerate-and-
    reverify retry (both gates re-run fresh against the new candidate, never
    just the prose check alone) before finally escalating to BLOCKED --
    `MAX_PROSE_REPAIR_ATTEMPTS`'s own comment states the known limitation
    (no hint-threading yet, so a retry may reproduce an identical paragraph
    at temperature=0.0 -- still safe, just not guaranteed to fix anything)."""
    if (state.accepted_status or "").startswith("ERROR:"):
        return {}

    render_result = state.details.get("render_result")
    assert render_result is not None  # guaranteed by _render_node whenever no ERROR was set

    if not render_result["needs_write"]:
        # Nothing to write -- no candidate to gate. Protects VER-003's "no
        # unnecessary work" on the common steady-state path.
        return {}

    org_repo = config["configurable"]["org_repo"]
    backend: StateBackend | None = config["configurable"].get("backend")
    current_render_result = render_result
    repair_attempts = 0
    # TC-28 (decision #46's own deferred scope from TC-15): one fresh value
    # per _verify_node call (i.e. per specialist run() invocation), reused
    # across this call's own internal prose-repair retries below -- never
    # persisted, never read back from a prior run. See compute_verification_
    # token()'s own docstring for exactly what replaying an old run's token
    # would otherwise get away with.
    run_nonce = generate_run_id()

    while True:
        dispatch = _dispatch_verify_readme_candidate(org_repo, current_render_result)
        if dispatch.outcome != "executed":
            return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}
        assert dispatch.result is not None
        verification = dispatch.result
        if verification["verdict"] == "reject":
            return {
                "accepted_status": f"ERROR:verification_rejected:{verification['reason']}",
                "details": merge_details(
                    state, render_result=current_render_result, verification=verification
                ),
            }

        # TC-15 (decision #46, F3): computed ONLY on this real accept path,
        # from this exact candidate's own facts_hash/fresh_fingerprint --
        # `_commit_node` reads this back rather than hardcoding a literal
        # "accept" string, and `commit_readme_write.py::precheck()`
        # independently re-derives the same value and rejects on mismatch.
        verification = {
            **verification,
            "nonce": run_nonce,
            "token": compute_verification_token(
                org_repo,
                current_render_result["facts_hash"],
                current_render_result["fresh_fingerprint"],
                run_nonce,
            ),
        }

        prose_dispatch = _dispatch_prose_quality_check(
            org_repo, current_render_result["final_text"], state_backend=backend
        )
        if prose_dispatch.outcome != "executed":
            return {"accepted_status": f"ERROR:{prose_dispatch.outcome}:{prose_dispatch.error}"}
        assert prose_dispatch.result is not None
        prose_quality = prose_dispatch.result

        details_update = {
            "render_result": current_render_result,
            "verification": verification,
            "prose_quality": prose_quality,
            "prose_quality_repair_attempts": repair_attempts,
        }

        if not (prose_quality["flagged"] and prose_quality["corroborated"]):
            return {"details": merge_details(state, **details_update)}

        if repair_attempts >= MAX_PROSE_REPAIR_ATTEMPTS:
            return {
                "accepted_status": (
                    f"ERROR:verification_rejected:prose_quality_flagged:{prose_quality['reason']}"
                ),
                "details": merge_details(state, **details_update),
            }

        regenerate_dispatch = _dispatch_regenerate(org_repo)
        if regenerate_dispatch.outcome != "executed":
            return {
                "accepted_status": (
                    f"ERROR:{regenerate_dispatch.outcome}:{regenerate_dispatch.error}"
                )
            }
        assert regenerate_dispatch.result is not None
        current_render_result = regenerate_dispatch.result
        repair_attempts += 1


def _commit_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    if (state.accepted_status or "").startswith("ERROR:"):
        return {}

    render_result = state.details.get("render_result")
    assert render_result is not None  # guaranteed by _render_node whenever no ERROR was set

    # `render_result` carries the full candidate text -- large, and only
    # ever needed here to build this node's own outputs. Explicitly dropped
    # before merging forward, so it never survives into the durably-
    # persisted record (unlike `verification`, from `_verify_node`, which is
    # small and worth keeping visible in evidence) -- `merge_details()`
    # itself has no way to express "forward everything except this one
    # key," so that filtering happens here, once, rather than at every call
    # site below.
    state_without_render_result = state.model_copy(
        update={"details": {k: v for k, v in state.details.items() if k != "render_result"}}
    )

    facts_hash = render_result["facts_hash"]
    # TC-15 (decision #46, F3): the real, re-derivable token `_verify_node`
    # computed on its own actual `accept` path for this exact candidate --
    # never a hardcoded literal. Falls back to a guaranteed-mismatching
    # placeholder if somehow absent (a needs_write candidate reaching here
    # with no recorded verification is itself a wiring bug this must not
    # paper over as a silent "accept").
    verification_verdict = state.details.get("verification", {}).get(
        "token", "MISSING_VERIFICATION_TOKEN"
    )
    # TC-28: the same nonce _verify_node minted its token with -- precheck()
    # re-derives compute_verification_token() from these two values plus
    # facts_hash/fresh_fingerprint below, so both must travel together.
    verification_nonce = state.details.get("verification", {}).get("nonce", "MISSING_NONCE")
    classification = classify_surface(
        current_fingerprint=facts_hash, prior_fingerprint=state.accepted_facts_hash
    )
    base_details = {
        "render_status": render_result["status"],
        "llm_called": render_result["llm_called"],
        "llm_calls": render_result["llm_calls"],
        # Wave 7 production-reliability fix: next run's _render_node reads
        # this back as prior_content_fingerprint, completing the
        # fresh-runner durable-skip signal alongside accepted_facts_hash.
        "fresh_fingerprint": render_result["fresh_fingerprint"],
    }

    if not render_result["needs_write"]:
        return {
            "accepted_facts_hash": facts_hash,
            "accepted_status": classification.classification,
            "details": merge_details(
                state_without_render_result, **base_details, written=False, committed=False
            ),
        }

    org_repo = config["configurable"]["org_repo"]
    backend: StateBackend | None = config["configurable"].get("backend")
    if backend is None:
        return {
            "accepted_facts_hash": facts_hash,
            "accepted_status": classification.classification,
            "details": merge_details(
                state_without_render_result,
                **base_details,
                written=False,
                committed=False,
                note="no durable state backend supplied -- refusing to dispatch a mutating "
                "capability without one (dispatch_gated_effect requires a real backend, not None)",
            ),
        }

    commit_tool_call = {
        "function": {
            "name": "commit_readme_write",
            "arguments": json.dumps(
                {
                    "org_repo": org_repo,
                    "facts_hash": facts_hash,
                    "fresh_fingerprint": render_result["fresh_fingerprint"],
                    "status": render_result["status"],
                    "needs_write": render_result["needs_write"],
                    "final_text": render_result["final_text"],
                    # Wave 8b (`VER-001`); hardened Wave 8.6+ (TC-15, F3): the
                    # structural guarantee -- this capability's own required
                    # argument means it cannot be dispatched at all without
                    # it, so a future wiring bug that skips `_verify_node`
                    # fails closed. Previously a hardcoded literal "accept"
                    # (which `precheck()` alone could not distinguish from a
                    # forged/copy-pasted call); now the real, re-derivable
                    # token `_verify_node` computed on its own actual accept
                    # path for THIS candidate -- `precheck()` independently
                    # re-derives the same value and rejects on any mismatch,
                    # including this value being the guaranteed-mismatching
                    # placeholder above.
                    "verification_verdict": verification_verdict,
                    "verification_nonce": verification_nonce,
                }
            ),
        }
    }
    gated = dispatch_gated_effect(
        commit_tool_call, _WRITE_PERMISSIONS, backend, org_repo, caller_domain=DOMAIN
    )

    if gated.outcome == "already_applied":
        effect_result = gated.cached_result or {}
        return {
            "accepted_facts_hash": facts_hash,
            "accepted_status": classification.classification,
            "details": merge_details(
                state_without_render_result,
                **base_details,
                **effect_result,
                ledger_outcome="already_applied",
            ),
        }
    if gated.outcome == "blocked_pending_reconciliation":
        return {"accepted_status": f"ERROR:blocked_pending_reconciliation:{gated.detail}"}

    assert gated.dispatch is not None
    if gated.dispatch.outcome != "executed":
        return {"accepted_status": f"ERROR:{gated.dispatch.outcome}:{gated.dispatch.error}"}

    effect_result = gated.dispatch.result or {}
    record_accepted_readme_state(
        backend,
        org_repo,
        facts_hash,
        render_result["status"],
        None,
        render_result["fresh_fingerprint"],
    )
    return {
        "accepted_facts_hash": facts_hash,
        "accepted_status": classification.classification,
        "details": merge_details(state_without_render_result, **base_details, **effect_result),
    }


def _record_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    backend: StateBackend | None = config["configurable"].get("backend")
    org_repo = config["configurable"]["org_repo"]
    current_revision = config["configurable"].get("current_revision")
    timestamp = datetime.now(UTC).isoformat()

    if backend is not None:
        try:
            # Wave 8d (`VER-002`/"repair loops"): unconditional, unlike the
            # other eight specialists' plain `save_domain()` guard-and-skip
            # -- this function still preserves the last-good
            # accepted_facts_hash/accepted_status/details on an ERROR run
            # (the same safety property), but ALSO records consecutive_
            # failure_count/last_failure_reason so a repeated identical
            # failure becomes visible instead of indistinguishable from
            # one-off noise. Chosen for this domain first since it owns the
            # one real write this project has -- extending this to the
            # other eight specialists is a real, deliberately deferred
            # follow-up, not silently claimed done here.
            save_domain_with_failure_tracking(
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
    graph.add_node("render", _render_node)
    graph.add_node("verify", _verify_node)
    graph.add_node("commit", _commit_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "render")
    graph.add_edge("render", "verify")
    graph.add_edge("verify", "commit")
    graph.add_edge("commit", "record")
    graph.add_edge("record", END)
    return graph.compile()


_GRAPH = _build_graph()


def run(
    org_repo: str, backend: StateBackend | None, current_revision: str | None = None
) -> DomainStateV1:
    """Entry point `specialists/registry.py::run_domain()` calls. Loads the
    prior accepted state for this domain (if any), runs the four-node
    graph, and returns the resulting `DomainStateV1` -- already durably
    recorded by the `record` node when `backend` is not `None`.

    `current_revision` (Wave 8.6, `ORC-003` reversal prerequisite): threaded
    through to `_record_node()`'s own `save_domain_with_failure_tracking()`
    call -- see `state/domain_state.py::save_domain()`'s own docstring."""
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
