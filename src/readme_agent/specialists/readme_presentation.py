"""README presentation specialist (Wave 7g, extended Wave 8b) -- domain
`readme_presentation`, the seventh specialist, deliberately separate from the
read-only `readme_reconciliation` domain (a different concern: reconciliation
only classifies upstream drift, never renders or writes anything). This is
the one place in the whole project that dispatches a real mutating
capability.

Five-node graph, `render` -> `verify` -> `review` -> `commit` -> `record`
(Wave 8b added `verify`; RPOC-050/051 added `review`; every other specialist
is two nodes -- `readme_presentation` needs the extra steps because the
write itself is independently gated before it's attempted -- twice, by two
structurally different verifiers -- then gated again on a real durable
backend and `mode == "full"`, unlike a plain classify-then-persist domain):

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
- `review` (RPOC-050/051): only ever consulted after `verify`'s own
  deterministic gate has already accepted (same short-circuit discipline) --
  materializes the real 8-file proposal-evidence bundle and dispatches the
  new, domain-scoped `verify_readme_proposal_bundle` capability against it
  (a second, independent, from-scratch deterministic re-check: schema/
  checksum/citation/reconstruction) WHEN a real `ReadmeDocumentPlanV1` is
  available (today, honestly, never -- see `_review_node`'s own docstring
  for the found, already-tracked, out-of-scope reason: `RDM-003`/`RDM-004`/
  `OWN-011`/`L8-007`), then calls `specialists/independent_readme_review.
  py::run_independent_review_with_repair_loop()` directly, unconditionally
  (an AGENTIC quality review -- product specificity, overpromotion,
  generic-template symptoms -- deliberately not itself a domain/capability,
  see that module's own docstring). Either check rejecting sets
  `accepted_status` the same `"ERROR:"`-prefixed way, so `commit` still
  needs no new logic of its own to skip the write. This is the closing half
  of `VER-001`'s "sole authority accepting it before it becomes applied" for
  the one real write this project has -- `check_verifiers_are_wired.py`'s
  own `verify_readme_proposal_bundle` finding.
- `commit`, only when `render` decided a write is actually needed
  (`needs_write`) and neither `verify` nor `review` rejected, dispatches the
  new, domain-scoped `commit_readme_write` via `dispatch_gated_effect()` --
  the real write, and, only when `mode == "full"`, one real local git commit
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

from readme_agent import paths
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import generate_run_id, write_readme_proposal_bundle
from readme_agent.orchestrator import record_accepted_readme_state
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import current_repository_snapshot
from readme_agent.specialists.independent_readme_review import (
    run_independent_review_with_repair_loop,
)
from readme_agent.specialists.readme_factuality import evaluate_candidate_factuality
from readme_agent.state.backend import StateBackend
from readme_agent.state.change_detection import classify_surface
from readme_agent.state.domain_state import merge_details, save_domain_with_failure_tracking
from readme_agent.state.readme_poc_lifecycle import record_readme_candidate_artifacts
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor.execution_context import proposal_only_active
from readme_agent.supervisor.local_poc_evidence import write_local_poc_readme_candidate
from readme_agent.supervisor.product_truth import load_prepared_product_truth
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
    wiring_arguments: dict = {}
    backend: StateBackend | None = config["configurable"].get("backend")
    current_revision = config["configurable"].get("current_revision")
    if backend is not None and current_revision is not None:
        prepared = load_prepared_product_truth(org_repo, backend, current_revision)
        if prepared is not None:
            wiring_arguments["product_facts_v2"] = prepared.facts.model_dump(mode="json")
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
        wiring_arguments["prior_facts_hash"] = state.accepted_facts_hash
        prior_fingerprint = state.details.get("fresh_fingerprint")
        if prior_fingerprint is not None:
            wiring_arguments["prior_content_fingerprint"] = prior_fingerprint
        prior_status = state.details.get("render_status")
        if prior_status is not None:
            wiring_arguments["prior_status"] = prior_status

    tool_call = {
        "function": {"name": "render_readme_candidate", "arguments": json.dumps(arguments)}
    }
    dispatch = dispatch_tool_call(
        tool_call,
        _READ_ONLY_PERMISSIONS,
        caller_domain=DOMAIN,
        extra_kwargs=wiring_arguments,
    )
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


def _dispatch_build_presentation_plan(org_repo: str, render_result: dict):
    """Build from independently re-derived facts; candidate text is wiring-only."""

    tool_call = {
        "function": {
            "name": "build_presentation_plan",
            "arguments": json.dumps({"org_repo": org_repo}),
        }
    }
    return dispatch_tool_call(
        tool_call,
        _READ_ONLY_PERMISSIONS,
        caller_domain=DOMAIN,
        extra_kwargs={
            "original_text": render_result["original_text"],
            "source_text": render_result.get("source_text", render_result["original_text"]),
            "candidate_text": render_result["final_text"],
            "source_revision": render_result["source_revision"],
            "product_facts_v2": render_result.get("product_facts_v2"),
        },
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


def _dispatch_regenerate(org_repo: str, product_facts_v2: dict | None):
    render_tool_call = {
        "function": {
            "name": "render_readme_candidate",
            "arguments": json.dumps({"org_repo": org_repo, "force_regenerate": True}),
        }
    }
    return dispatch_tool_call(
        render_tool_call,
        _READ_ONLY_PERMISSIONS,
        caller_domain=DOMAIN,
        extra_kwargs={"product_facts_v2": product_facts_v2},
    )


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
        plan_dispatch = _dispatch_build_presentation_plan(org_repo, current_render_result)
        if plan_dispatch.outcome != "executed":
            return {
                "accepted_status": (
                    f"ERROR:presentation_plan:{plan_dispatch.outcome}:{plan_dispatch.error}"
                )
            }
        assert plan_dispatch.result is not None
        presentation_plan = plan_dispatch.result
        presentation_plan_record = {
            **presentation_plan,
            "git_patch_proof": {
                key: value
                for key, value in presentation_plan["git_patch_proof"].items()
                if key != "patch"
            },
        }
        # RPOC-050: the raw patch text itself -- stripped from
        # `presentation_plan_record` above (no documented rationale found in
        # this repo's own history for why, beyond the general size concern
        # `_commit_node`'s own `render_result`-stripping comment states
        # explicitly for the candidate text; git history shows it was simply
        # never carried forward, `f8b83a4`) -- is kept here, in a separate
        # key, only long enough to reach `_review_node` below, which
        # materializes the real proposal-bundle artifact this specialist
        # never had before (RPOC-051). Never added to `presentation_plan_
        # record` itself: that dict is what every reject-path return above
        # and below durably persists via `_record_node`, and the patch adds
        # nothing to a rejected candidate's own evidence value.
        patch_text = presentation_plan["git_patch_proof"].get("patch", "")
        if not presentation_plan["executable"]:
            validation_errors = presentation_plan.get("document_validation", {}).get("errors", [])
            return {
                "accepted_status": (
                    "ERROR:presentation_plan:blocked"
                    + (f":{validation_errors}" if validation_errors else "")
                ),
                "details": merge_details(
                    state,
                    render_result=current_render_result,
                    presentation_plan=presentation_plan_record,
                ),
            }

        if proposal_only_active():
            if backend is None:
                return {"accepted_status": "ERROR:local_poc_candidate_requires_durable_state"}
            snapshot = current_repository_snapshot(org_repo)
            if snapshot is None:
                return {"accepted_status": "ERROR:local_poc_candidate_snapshot_missing"}
            try:
                (
                    local_bundle_dir,
                    assessment_hash,
                    presentation_plan_hash,
                    candidate_hash,
                ) = write_local_poc_readme_candidate(
                    snapshot,
                    current_render_result,
                    presentation_plan,
                )
                record_readme_candidate_artifacts(
                    backend,
                    org_repo,
                    source_revision=snapshot.source_revision,
                    assessment_hash=assessment_hash,
                    presentation_plan_hash=presentation_plan_hash,
                    candidate_hash=candidate_hash,
                    evidence_refs=[
                        str(local_bundle_dir / "assessment" / "current-readme-assessment.json"),
                        str(local_bundle_dir / "planning" / "readme-document-plan.json"),
                        str(local_bundle_dir / "candidate" / "README.md"),
                        str(local_bundle_dir / "candidate" / "README.patch"),
                        str(local_bundle_dir / "candidate" / "claim-map.json"),
                    ],
                )
            except Exception as exc:  # noqa: BLE001 -- fail closed before review/effect
                return {
                    "accepted_status": (
                        f"ERROR:local_poc_candidate_persistence:{type(exc).__name__}:{exc}"
                    )
                }

        factuality = evaluate_candidate_factuality(
            org_repo,
            current_render_result["original_text"],
            current_render_result["final_text"],
            _READ_ONLY_PERMISSIONS,
            source_text=current_render_result.get(
                "source_text", current_render_result["original_text"]
            ),
            product_facts_v2=current_render_result.get("product_facts_v2"),
        )
        if not factuality.valid:
            reason = factuality.error or (
                f"claim_conflicts={len(factuality.claim_conflicts)},"
                f"protected_losses={len(factuality.protected_content_losses)}"
            )
            return {
                "accepted_status": f"ERROR:factuality_rejected:{reason}",
                "details": merge_details(
                    state,
                    render_result=current_render_result,
                    presentation_plan=presentation_plan_record,
                    factuality=factuality.model_dump(mode="json"),
                ),
            }

        dispatch = _dispatch_verify_readme_candidate(org_repo, current_render_result)
        if dispatch.outcome != "executed":
            return {"accepted_status": f"ERROR:{dispatch.outcome}:{dispatch.error}"}
        assert dispatch.result is not None
        verification = dispatch.result
        if verification["verdict"] == "reject":
            return {
                "accepted_status": f"ERROR:verification_rejected:{verification['reason']}",
                "details": merge_details(
                    state,
                    render_result=current_render_result,
                    presentation_plan=presentation_plan_record,
                    verification=verification,
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
            "presentation_plan": presentation_plan_record,
            # RPOC-050/051: the real patch text, present only long enough for
            # `_review_node` to materialize the proposal bundle -- stripped
            # back out before `_commit_node`/`_record_node` (see
            # `_review_node`'s own docstring), the same "large, only needed
            # one node further" treatment `_commit_node` already gives
            # `render_result`.
            "presentation_plan_patch": patch_text,
            "verification": verification,
            "factuality": factuality.model_dump(mode="json"),
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

        regenerate_dispatch = _dispatch_regenerate(
            org_repo, current_render_result.get("product_facts_v2")
        )
        if regenerate_dispatch.outcome != "executed":
            return {
                "accepted_status": (
                    f"ERROR:{regenerate_dispatch.outcome}:{regenerate_dispatch.error}"
                )
            }
        assert regenerate_dispatch.result is not None
        current_render_result = regenerate_dispatch.result
        repair_attempts += 1


def _dispatch_verify_readme_proposal_bundle(bundle_dir):
    tool_call = {
        "function": {
            "name": "verify_readme_proposal_bundle",
            "arguments": json.dumps({"bundle_dir": str(bundle_dir)}),
        }
    }
    return dispatch_tool_call(
        tool_call, _READ_ONLY_PERMISSIONS, caller_domain=INDEPENDENT_VERIFICATION
    )


def _review_node(state: DomainStateV1, config: RunnableConfig) -> dict:
    """RPOC-050/051: the independent, author != verifier bundle-plus-agentic
    gate between `_verify_node`'s own deterministic accept and `_commit_
    node`'s write -- closes the "verifier not wired into production" gap
    (`scripts/governance/check_verifiers_are_wired.py`'s own finding against
    `verify_readme_proposal_bundle`/`verify_cross_pilot_specificity`): before
    this node existed, both functions were reachable only from a test or a
    standalone `plans/investigations/tools/*.py` script, never from a real
    `supervise` run.

    Same top-of-function `"ERROR:"` guard, and the same "nothing was written
    this run" short-circuit `_verify_node` itself uses (`VER-003`'s "no
    unnecessary work") -- this node only has real work to do on the one path
    that reaches it with a genuine new candidate: `_verify_node`'s own
    deterministic accept.

    (a) materializes the real 8-file proposal bundle (`evidence/writer.py::
    write_readme_proposal_bundle()`) from this run's own already-computed
    render/presentation-plan/patch, plus a freshly (re-)dispatched
    `get_product_facts` -- never a pass-through of any other node's own
    assembled facts.

    (b) dispatches the new, domain-scoped `verify_readme_proposal_bundle`
    capability against that materialized bundle -- the DETERMINISTIC
    bundle-completeness re-check (schema/checksum/citation/independent-
    reconstruction, all re-derived from disk, never trusting what was just
    written).

    (c) calls `independent_readme_review.run_independent_review_with_repair_
    loop()` directly -- a plain function call, not a capability dispatch:
    that module's own docstring explains why it is deliberately NOT
    registered as a domain/capability (inventing one now, only to leave it
    permanently unwired past this one call site, would either sit as a
    `KNOWN_DOMAINS` orphan or force a premature registration). This is the
    AGENTIC quality review, with its own bounded regenerate-and-reverify
    repair loop.

    (d) either check rejecting sets `accepted_status` to the same
    `"ERROR:"`-prefixed shape this graph already uses everywhere else, so
    `_commit_node`'s existing top-of-function guard (unchanged) naturally
    skips the write.

    The raw patch text (`presentation_plan_patch`, RPOC-050) is consumed here
    and then explicitly dropped before merging forward -- the same "large,
    only needed one node further" treatment `_commit_node` already gives
    `render_result`, so it never survives into the durably-persisted record
    on this node's own accept path."""
    if (state.accepted_status or "").startswith("ERROR:"):
        return {}

    render_result = state.details.get("render_result")
    assert render_result is not None  # guaranteed by _render_node whenever no ERROR was set

    if not render_result["needs_write"]:
        # Nothing written this run -- nothing to bundle or independently
        # review either.
        return {}

    presentation_plan_record = state.details.get("presentation_plan")
    patch_text = state.details.get("presentation_plan_patch")
    verification = state.details.get("verification")
    # guaranteed together by _verify_node's own accept-path details_update
    # whenever needs_write is True and no ERROR was set above.
    assert presentation_plan_record is not None
    assert verification is not None

    state_without_patch = state.model_copy(
        update={
            "details": {
                key: value
                for key, value in state.details.items()
                if key != "presentation_plan_patch"
            }
        }
    )

    org_repo = config["configurable"]["org_repo"]

    # RPOC-051(a)/(b): the deterministic bundle re-check can only run when
    # `_verify_node`'s own `build_presentation_plan` dispatch actually took
    # its document-plan branch (`build_presentation_plan.execute()`, guarded
    # there by `find_presentation_span(candidate_text) is not None`) --
    # `verify_readme_proposal_bundle()`'s own schema requires a real
    # `ReadmeDocumentPlanV1`; the legacy branch produces `readme_document_
    # plan={}`, which is not one. Found live while wiring this node: today's
    # real `render_readme_candidate` pipeline (`readme/candidate_pipeline.
    # py`) never emits the whole-document presentation-span wrapper `find_
    # presentation_span` looks for (confirmed: no reference to it anywhere in
    # that module), so this specialist's own render -> verify sequence always
    # takes the legacy branch in production today -- a pre-existing,
    # already-tracked gap (`RDM-003`/`RDM-004`/`OWN-011`/`L8-007`, all
    # `PARTIAL`: "future approved regions... remain open"), not something
    # RPOC-050/051 is scoped to close. Skipped honestly here (a real,
    # legible `details["bundle_verification"]` record, never silently
    # absent) rather than materializing a bundle guaranteed to fail
    # `verify_readme_proposal_bundle()`'s own schema load and misreporting a
    # real candidate as bundle-rejected for a reason that has nothing to do
    # with its own actual quality.
    document_plan_available = bool(presentation_plan_record.get("readme_document_plan"))
    bundle_verification_record: dict
    if document_plan_available:
        product_facts_v2 = render_result.get("product_facts_v2")
        if product_facts_v2 is None:
            return {"accepted_status": "ERROR:verified_product_facts_missing_from_candidate"}

        entry = require_listed(org_repo)
        # Reuses _verify_node's own per-call run_nonce (already unique per
        # specialist run() invocation, see compute_verification_token()'s
        # own docstring) as this bundle's directory identity -- one run, one
        # bundle, rather than minting a second, unrelated run id.
        run_id = verification.get("nonce") or generate_run_id()
        bundle_dir = paths.readme_proposal_bundle_dir(entry.org, entry.repo_name, run_id)
        write_readme_proposal_bundle(
            bundle_dir,
            original_readme=render_result["original_text"],
            candidate_readme=render_result["final_text"],
            patch_text=patch_text or "",
            product_facts_v2=product_facts_v2,
            readme_assessment_v1=presentation_plan_record["readme_assessment"],
            readme_document_plan_v1=presentation_plan_record["readme_document_plan"],
            claim_map_v1=presentation_plan_record["claim_map"],
            repository_presentation_plan_v1=presentation_plan_record.get("presentation_plan") or {},
            document_validation=presentation_plan_record.get("document_validation") or {},
        )

        bundle_dispatch = _dispatch_verify_readme_proposal_bundle(bundle_dir)
        if bundle_dispatch.outcome != "executed" or bundle_dispatch.result is None:
            return {"accepted_status": f"ERROR:{bundle_dispatch.outcome}:{bundle_dispatch.error}"}
        bundle_verdict = bundle_dispatch.result
        bundle_verification_record = {
            "status": "checked",
            "bundle_dir": str(bundle_dir),
            **bundle_verdict,
        }
        if not bundle_verdict["verified"]:
            return {
                "accepted_status": (
                    f"ERROR:bundle_verification_rejected:{'; '.join(bundle_verdict['failures'])}"
                ),
                "details": merge_details(
                    state_without_patch, bundle_verification=bundle_verification_record
                ),
            }
    else:
        bundle_verification_record = {
            "status": "skipped",
            "reason": "no readme_document_plan for this candidate -- build_presentation_plan "
            "took its legacy, non-document-plan branch (no whole-document presentation-span "
            "wrapper on the candidate), which verify_readme_proposal_bundle's own schema "
            "cannot verify",
        }

    # `backend` is deliberately NOT threaded through here, even though a real
    # one is available in `config["configurable"]` -- `run_independent_
    # review_with_repair_loop()` records its verdict via `record_review_
    # verdict()` -> `transition_readme_poc_status()`, which enforces
    # `state/readme_poc_lifecycle.py::_README_POC_TRANSITIONS` strictly:
    # `AGENT_APPROVED`/`AGENT_REVIEW_REJECTED` are only legal moves FROM
    # `CANDIDATE_GENERATED`. Nothing in production today drives an org_repo's
    # `readme_poc_lifecycle` through `DISCOVERED -> SNAPSHOTTED -> ... ->
    # CANDIDATE_GENERATED` first (confirmed: no call site anywhere in `src/`
    # outside this module's own siblings) -- RPOC-070's lifecycle-driving
    # wiring is a separate, not-yet-built concern, out of RPOC-050/051's own
    # scope. Passing the real backend through here would make every real
    # accept path raise `StateBackendError` (`DISCOVERED -> AGENT_APPROVED`
    # is not a legal transition) instead of returning a verdict -- a crash
    # this taskcard exists to prevent, not cause. `backend=None` degrades
    # exactly as `run_independent_readme_review()`'s own docstring already
    # documents for an absent backend: the real verdict is still returned
    # and still recorded in this node's own `details` below, just without
    # the separate RPOC-070 durable lifecycle side record.
    # Wrapped in try/except (not bare -- every other failure mode in this
    # graph is a checked outcome, never an uncaught exception): `run_
    # independent_review_with_repair_loop()`'s own default `regenerate_
    # context` (`independent_readme_review.independent_render_context()`,
    # engaged only on a real REJECT_REPAIRABLE verdict) dispatches `build_
    # presentation_plan` with no `caller_domain` at all -- found live while
    # wiring this node: since that capability is domain-scoped (`allowed_
    # domains=[README_PRESENTATION]`), every regeneration attempt raises
    # `RuntimeError` there. A real, pre-existing bug in `independent_readme_
    # review.py` (out of this taskcard's scope -- that module is other-lane
    # work this taskcard was explicitly told to read, not edit), only newly
    # EXPOSED, not introduced, by this node being its first caller that can
    # reach a real REJECT_REPAIRABLE verdict in production. This except
    # converts it into the same `"ERROR:"`-prefixed shape every other
    # failure here already uses, so a bug in that module's own regeneration
    # path degrades this run honestly instead of crashing the whole graph.
    try:
        review_outcome = run_independent_review_with_repair_loop(
            org_repo,
            None,
            {
                "original_text": render_result["original_text"],
                "final_text": render_result["final_text"],
                "presentation_plan": presentation_plan_record,
                "deterministic_validation_result": verification,
                "product_facts_v2": render_result.get("product_facts_v2"),
            },
        )
    except Exception as exc:  # noqa: BLE001 -- see comment above
        return {
            "accepted_status": f"ERROR:independent_review_exception:{type(exc).__name__}: {exc}",
            "details": merge_details(
                state_without_patch, bundle_verification=bundle_verification_record
            ),
        }
    independent_review_record = review_outcome.model_dump(mode="json")
    if review_outcome.outcome_kind != "accepted":
        return {
            "accepted_status": (
                f"ERROR:independent_review_{review_outcome.outcome_kind}:"
                f"{review_outcome.final_review.verdict}"
            ),
            "details": merge_details(
                state_without_patch,
                bundle_verification=bundle_verification_record,
                independent_review=independent_review_record,
            ),
        }

    return {
        "details": merge_details(
            state_without_patch,
            bundle_verification=bundle_verification_record,
            independent_review=independent_review_record,
        )
    }


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

    if proposal_only_active():
        return {
            "accepted_facts_hash": facts_hash,
            "accepted_status": classification.classification,
            "details": merge_details(
                state_without_render_result,
                **base_details,
                written=False,
                committed=False,
                proposal_only=True,
                note="local-POC profile stops at an independently reviewed proposal",
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
    graph.add_node("review", _review_node)
    graph.add_node("commit", _commit_node)
    graph.add_node("record", _record_node)
    graph.add_edge(START, "render")
    graph.add_edge("render", "verify")
    graph.add_edge("verify", "review")
    graph.add_edge("review", "commit")
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
