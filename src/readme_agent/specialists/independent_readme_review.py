"""Independent, adversarial README-quality reviewer (`RPOC-022`/`RPOC-023`,
sprint charter Part B.2 Phase 2 Lane V / Part C.4) -- the genuinely new
LLM-backed product-quality judgment call this project did not have before:
neither `_verify_node`'s own deterministic gate (`specialists/readme_
presentation.py`) nor `specialists/independent_verification.py`'s post-hoc
cross-domain audit ever asks an LLM "is this candidate README actually
good," only whether it is schema/structurally/citation-valid (the former) or
whether every domain's own evidence is complete (the latter).

**Plain function, not a `LangGraph` `StateGraph`, on purpose** -- mirrors
`specialists/readme_factuality.py`'s own shape, the one other specialist in
this directory that is a single bounded LLM/capability-backed check rather
than a multi-node render/verify/commit/record pipeline. Every other
specialist here is a `StateGraph(DomainStateV1)` because it is registered as
its own `capabilities/domains.py` domain in `specialists/registry.py`, whose
own `_build()` fail-loud completeness gate (`orphaned_domains`) REQUIRES
every `KNOWN_DOMAINS` entry to have a matching specialist. This module is
deliberately NOT registered as a domain and NOT added to `specialists/
registry.py` -- per this taskcard's own scope, wiring it into the existing
render -> verify -> commit graph is a later taskcard's job (RPOC-050/051),
not this one's. Inventing a new domain identity now, only to leave it
unwired, would either sit as a permanent `KNOWN_DOMAINS` orphan (a build-time
`ConfigError`) or force a premature, throwaway registration -- a plain,
directly-callable function avoids both and is the honest shape for
"standalone, callable specialist" the taskcard asks for.

**Own separate context, never a pass-through of `_verify_node`'s own
assembled objects** -- `run_independent_readme_review()` independently
dispatches `get_product_facts` for its own `ProductFactsV2` view (the same
"re-fetch, never trust the caller's already-assembled facts" discipline
`readme_factuality.py::evaluate_candidate_factuality()` already established
for its own, adjacent, pre-effect gate), and takes `presentation_plan`/
`deterministic_validation_result` as explicit, individually-typed parameters
-- never a shared `DomainStateV1.details` dict reused from any other node.
The deterministic validation result is treated as exactly what the prompt's
own `user_template` tells the model it is: read-only reference context to
weigh, never something this function (or the model) may rubber-stamp as
already having done the quality-judgment job.

**Model route**: `env.py::JOB_MODEL_ROUTING["independent_readme_review"]` ->
`qwen3-next`, live-characterized in `plans/investigations/evidence/
independent-readme-reviewer-route-characterization-2026-07-25/
characterization-and-recommendation.md` (RPOC-020) against this exact 5-way
verdict shape.

**LLM client: `llm/reviewer_client.py::LiveIndependentReviewClient`** --
the reviewer uses the existing forced-native-tool transport rather than
freeform JSON. The governed heterogeneous qualification exposed malformed
or duplicated JSON responses at portfolio scale even though the earlier
small route probe passed. Forced tool calling was already the project's
live-proven structured-output mechanism (`llm/verifier_client.py`), so the
review adapter reuses it with a strict five-way verdict schema and preserves
the existing `AnalysisResult` seam for fixture clients. Prompt content still
comes only from `prompts/verification/independent_readme_review.yaml` through
`llm/verification_prompts.py`.

**Repair loop (`RPOC-023`)**: `run_independent_review_with_repair_loop()`
bounds regeneration to `MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS` (see its own
comment for why =2) and structurally never lets a `BLOCKED_*` verdict reach
the `REPAIRING` transition -- only `REJECT_REPAIRABLE` falls through past the
early `outcome_kind == "blocked"` return. A fact conflict or an unverifiable
specific claim needs new evidence, not a reworded README; regenerating prose
against the same facts is not expected to fix either, and `RPOC-070`'s own
lifecycle vocabulary agrees: `AGENT_REVIEW_REJECTED` is the only "the
reviewer said no" status it defines, and nothing requires taking its legal
`-> REPAIRING` edge immediately -- stopping at `AGENT_REVIEW_REJECTED`, with
a reason string naming the verdict and (for a blocked verdict) that it was
never eligible for repair, keeps every transition attempted here legal
against `state/readme_poc_lifecycle.py::_README_POC_TRANSITIONS` while still
making the distinction real and durable, not just documented in a comment.
"""

# The single-review function in this module is retained for compatibility,
# governed diagnostics, and the historical golden set. The production
# presentation gate injects `separated_readme_review.run_separated_readme_review`
# into the bounded repair loop; this single route is no longer acceptance
# authority for a candidate.

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny, ValidationError, model_validator

from readme_agent import env
from readme_agent.capabilities.dispatcher import DispatchResult, dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.reviewer_client import LiveIndependentReviewClient
from readme_agent.llm.verification_prompts import (
    build_independent_readme_review_messages,
    build_independent_readme_review_retry_message,
)
from readme_agent.readme.fact_grounding import fact_strings
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2, ReadmePocStatusV2
from readme_agent.state.readme_poc_lifecycle import transition_readme_poc_status

_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}
_MAX_SEMANTIC_RESPONSE_ATTEMPTS = 2

# `observed_by` identity recorded on every lifecycle transition this module
# makes -- one stable string, matching this module's own name (and the
# prompt's `model_route`/`prompt_id`), so every transition history entry is
# traceable back to this specific reviewer without guessing among several
# plausible spellings.
_OBSERVED_BY = "independent_readme_review"
# Compatibility seam for existing fixture injection. The implementation is
# now the forced-schema reviewer client, but callers that monkeypatch the
# specialist's historical client name continue to replace the real transport.
LiveAnalysisClient = LiveIndependentReviewClient

IndependentReviewVerdictV1 = Literal[
    "ACCEPT",
    "REJECT_REPAIRABLE",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
    "SYSTEM_FAILURE",
]

# `REJECT_REPAIRABLE` is the only verdict the repair loop ever regenerates
# for. The three below are grouped because they share the same consequence
# for the repair loop (never enter it), not because they are otherwise
# equivalent -- `record_review_verdict()`'s own `reason` string still names
# the exact verdict, never collapses them into one label.
_BLOCKED_VERDICTS: frozenset[str] = frozenset(
    {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE", "SYSTEM_FAILURE"}
)

# RPOC-023: small-integer-constant-with-a-comment-explaining-the-bound, same
# convention as `MAX_PROSE_REPAIR_ATTEMPTS` (`specialists/readme_
# presentation.py`) and `MAX_REPAIR_ATTEMPTS` (`supervisor/repair.py`) --
# both already =2 for the same reason: no operational history yet to justify
# a different value, and every attempt costs one more live LLM call plus one
# more real candidate regeneration. Known, honest limitation, the same shape
# as `MAX_PROSE_REPAIR_ATTEMPTS`'s own docstring: `render_readme_candidate`
# remains deliberately small because each attempt repeats composition,
# deterministic validation, bundle verification, and independent review.
MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS = 2


class IndependentReadmeReviewResultV1(BaseModel):
    """The exact 5-field verdict shape `prompts/verification/independent_
    readme_review.yaml`'s own system prompt commits the model to returning.
    `extra="forbid"` -- an LLM response carrying an unexpected extra key is a
    schema drift worth failing loudly on, never silently ignored."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: IndependentReviewVerdictV1
    reasoning: str
    failed_criteria: list[str] = Field(default_factory=list)
    sections_affected: list[str] = Field(default_factory=list)
    required_repair: str = ""
    preserve: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_verdict_payload(self) -> IndependentReadmeReviewResultV1:
        if self.verdict == "ACCEPT":
            if self.failed_criteria or self.sections_affected or self.required_repair:
                raise ValueError("ACCEPT cannot carry failure or repair instructions")
            return self
        if self.verdict == "REJECT_REPAIRABLE" and (
            not self.failed_criteria
            or not self.sections_affected
            or not self.required_repair.strip()
        ):
            raise ValueError(
                "REJECT_REPAIRABLE requires failed criteria, affected sections, and repair text"
            )
        if self.verdict in {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"} and (
            not self.failed_criteria or not self.sections_affected
        ):
            raise ValueError("fact-blocking verdicts require failed criteria and affected sections")
        return self


class _AnalysisClientLike(Protocol):
    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


def _accepted_literal_phrases(facts: ProductFactsV2) -> set[str]:
    accepted: set[str] = set()
    for fact_id in facts.selected_fact_ids.values():
        fact = facts.fact_by_id(fact_id)
        if fact.verification_state not in {"verified", "policy_approved"}:
            continue
        if fact.has_unresolved_conflict:
            continue
        accepted.update(phrase.casefold() for phrase in fact_strings(fact.value))
    return accepted


def _contradicted_missing_evidence_claims(
    review: IndependentReadmeReviewResultV1,
    facts: ProductFactsV2,
) -> list[str]:
    """Find claims the reviewer called unsupported despite literal accepted evidence."""

    if review.verdict != "BLOCKED_MISSING_EVIDENCE":
        return []
    review_text = f"{review.reasoning}\n{review.required_repair}"
    quoted = [
        *re.findall(r'["“]([^"”\n]{8,})["”]', review_text),
        *re.findall(r"[‘']([^’'\n]{8,})[’']", review_text),
    ]
    accepted = _accepted_literal_phrases(facts)
    return sorted({claim for claim in quoted if claim.strip().casefold() in accepted})


def _accepted_literal_fact_refs(
    facts: ProductFactsV2,
    contradicted_claims: list[str],
) -> list[dict[str, str]]:
    """Return the exact selected facts that disprove a reviewer's absence claim."""

    claims_by_normalized = {claim.strip().casefold(): claim for claim in contradicted_claims}
    refs: list[dict[str, str]] = []
    for fact_id in facts.selected_fact_ids.values():
        fact = facts.fact_by_id(fact_id)
        if fact.verification_state not in {"verified", "policy_approved"}:
            continue
        if fact.has_unresolved_conflict:
            continue
        for phrase in fact_strings(fact.value):
            quoted_claim = claims_by_normalized.get(phrase.casefold())
            if quoted_claim is None:
                continue
            refs.append(
                {
                    "quoted_claim": quoted_claim,
                    "fact_id": fact.fact_id,
                    "field": fact.field,
                    "verification_state": fact.verification_state,
                }
            )
    return sorted(refs, key=lambda item: (item["quoted_claim"].casefold(), item["fact_id"]))


def run_independent_readme_review(
    org_repo: str,
    original_readme_text: str,
    candidate_readme_text: str,
    presentation_plan: dict,
    deterministic_validation_result: dict,
    *,
    client: _AnalysisClientLike | None = None,
    backend: StateBackend | None = None,
    repair_attempt: int = 0,
    product_facts_v2: dict | ProductFactsV2 | None = None,
) -> IndependentReadmeReviewResultV1:
    """The one bounded LLM-backed check (mirrors `readme_factuality.py::
    evaluate_candidate_factuality()`'s own shape): consumes the exact
    run-scoped `ProductFactsV2` graph when supplied, or independently fetches
    it for compatibility callers,
    calls the live `independent_readme_review` route, and validates the
    response into `IndependentReadmeReviewResultV1`.

    `presentation_plan`/`deterministic_validation_result` are accepted as
    plain, already-JSON-serializable dicts -- read-only reference context
    the reviewer weighs, not evidence this function re-derives itself
    (re-deriving them would mean re-running `readme_presentation.py`'s
    entire render/plan/validate pipeline here, which is not this reviewer's
    job; see `independent_render_context()` below for the one place this
    module DOES perform that chain, for its own repair loop).

    `get_product_facts` dispatch failure degrades to a locally-synthesized
    `SYSTEM_FAILURE` result -- no LLM call is made (protects against paying
    for a call against genuinely unusable input) -- mirroring `readme_
    factuality.py`'s own "degrade honestly with a structured object, never
    raise" convention for the identical failure mode. A genuine LLM-call or
    response-schema failure, by contrast, is allowed to propagate as
    `LLMError`, matching every other freeform-analysis capability in this
    codebase (`compare_against_presentation_standard.py`/`review_visual_
    asset_accuracy.py`'s own stated "LLMError propagates... on any gateway
    failure" convention) -- never silently mapped to a fabricated verdict.

    `backend`/`repair_attempt`: when `backend` is supplied, this function
    The reviewer remains independent through its separate prompt, client,
    identity, and evidence record; independence does not permit it to observe
    a different repository revision or fact graph. This function also calls
    `record_review_verdict()` before returning, recording the
    verdict as a real README-POC lifecycle transition (`RPOC-070`).
    `backend=None` degrades honestly (no durable record), same posture every
    other specialist in this codebase already uses for an absent backend."""
    product_facts: ProductFactsV2 | None = None
    if product_facts_v2 is not None:
        product_facts = ProductFactsV2.model_validate(product_facts_v2)
    else:
        facts_dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "get_product_facts",
                    "arguments": json.dumps({"org_repo": org_repo}),
                }
            },
            _READ_ONLY_PERMISSIONS,
            caller_domain=INDEPENDENT_VERIFICATION,
        )
        if facts_dispatch.outcome == "executed" and facts_dispatch.result is not None:
            product_facts = ProductFactsV2.model_validate(facts_dispatch.result["product_facts_v2"])
        else:
            review = IndependentReadmeReviewResultV1(
                verdict="SYSTEM_FAILURE",
                reasoning=(
                    f"independent review could not obtain ProductFactsV2 for {org_repo} "
                    f"(get_product_facts:{facts_dispatch.outcome}:{facts_dispatch.error}) -- "
                    "review is genuinely impossible without grounding facts; this is a system "
                    "failure, not a quality verdict"
                ),
            )
    if product_facts is not None:
        resolved_client: _AnalysisClientLike = client or LiveAnalysisClient(
            env.llm_base_url(),
            env.llm_api_key(),
            env.llm_model_for_job("independent_readme_review"),
            max_tokens=2400,
        )
        messages = build_independent_readme_review_messages(
            org_repo,
            original_readme_text,
            candidate_readme_text,
            json.dumps(product_facts.model_dump(mode="json"), sort_keys=True, default=str),
            json.dumps(presentation_plan, sort_keys=True, default=str),
            json.dumps(deterministic_validation_result, sort_keys=True, default=str),
        )
        for semantic_attempt in range(_MAX_SEMANTIC_RESPONSE_ATTEMPTS):
            result: AnalysisResult = resolved_client.analyze(messages)
            try:
                review = IndependentReadmeReviewResultV1.model_validate(result.parsed)
            except ValidationError as exc:
                raise LLMError(
                    f"independent_readme_review response did not match the required verdict "
                    f"schema: {exc}"
                ) from exc
            contradicted_claims = _contradicted_missing_evidence_claims(review, product_facts)
            if not contradicted_claims:
                break
            if semantic_attempt + 1 == _MAX_SEMANTIC_RESPONSE_ATTEMPTS:
                raise LLMError(
                    "independent reviewer repeatedly classified literal accepted fact text as "
                    f"missing evidence: {contradicted_claims}"
                )
            accepted_fact_refs = _accepted_literal_fact_refs(product_facts, contradicted_claims)
            messages = [
                *messages,
                build_independent_readme_review_retry_message(
                    json.dumps(accepted_fact_refs, ensure_ascii=False, sort_keys=True)
                ),
            ]

    if backend is not None:
        record_review_verdict(backend, org_repo, review, repair_attempt=repair_attempt)
    return review


def record_review_verdict(
    backend: StateBackend,
    org_repo: str,
    review: IndependentReadmeReviewResultV1,
    *,
    repair_attempt: int = 0,
    observed_by: str = _OBSERVED_BY,
) -> ReadmePocLifecycleStateV2:
    """Records one review outcome as a real `RPOC-070` lifecycle transition.

    `ACCEPT` -> `AGENT_APPROVED` (the final gate this specialist owns; moving
    further, e.g. into `HUMAN_REVIEW_READY`, is a later stage's job).

    `REJECT_REPAIRABLE` -> `AGENT_REVIEW_REJECTED`; factual blocks and a
    reviewer-system failure retain their distinct V2 lifecycle statuses.
    This preserves the first failed boundary for the automatic resolver,
    rather than laundering every non-accept into a repairable prose task.
    """
    if review.verdict == "ACCEPT":
        return transition_readme_poc_status(
            backend,
            org_repo,
            "AGENT_APPROVED",
            observed_by=observed_by,
            reason=review.reasoning or "independent review accepted the candidate",
        )

    statuses: dict[str, ReadmePocStatusV2] = {
        "REJECT_REPAIRABLE": "AGENT_REVIEW_REJECTED",
        "BLOCKED_FACT_CONFLICT": "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE": "BLOCKED_MISSING_EVIDENCE",
        "SYSTEM_FAILURE": "SYSTEM_FAILURE",
    }
    status = statuses[review.verdict]
    kind = "blocked, not repair-eligible" if review.verdict in _BLOCKED_VERDICTS else "repairable"
    reason = (
        f"verdict={review.verdict} ({kind}), review pass {repair_attempt + 1} "
        f"(max repair attempts {MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS}): {review.reasoning}"
    )
    return transition_readme_poc_status(
        backend,
        org_repo,
        status,
        observed_by=observed_by,
        reason=reason,
        evidence_refs=list(review.failed_criteria),
    )


RepairLoopOutcomeKindV1 = Literal[
    "accepted",
    "blocked",
    "repair_exhausted",
    "repair_rerouted",
]


class RepairLoopOutcomeV1(BaseModel):
    """`run_independent_review_with_repair_loop()`'s own return value.

    `outcome_kind`: `"accepted"` (verdict was `ACCEPT`), `"blocked"` (verdict
    was one of the three `BLOCKED_*`/`SYSTEM_FAILURE` verdicts -- the repair
    loop never attempted a regeneration), or `"repair_exhausted"`
    (`REJECT_REPAIRABLE` every time, `MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS`
    real regenerations attempted, still rejected -- `escalation` is then
    populated, never left `None`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_kind: RepairLoopOutcomeKindV1
    final_review: SerializeAsAny[IndependentReadmeReviewResultV1]
    attempts: int
    review_call_count: int = Field(ge=1)
    escalation: dict | None = None
    repair_history: list[dict] = Field(default_factory=list)
    # The caller must continue with the accepted repaired candidate.  This is
    # runtime wiring, not evidence payload, so model_dump() excludes it.
    final_context: dict = Field(default_factory=dict, exclude=True, repr=False)


def _dispatch_render(
    org_repo: str,
    *,
    force_regenerate: bool = False,
    product_facts_v2: dict | None = None,
) -> DispatchResult:
    arguments: dict = {"org_repo": org_repo}
    if force_regenerate:
        arguments["force_regenerate"] = True
    return dispatch_tool_call(
        {"function": {"name": "render_readme_candidate", "arguments": json.dumps(arguments)}},
        _READ_ONLY_PERMISSIONS,
        extra_kwargs={"product_facts_v2": product_facts_v2},
        caller_domain=README_PRESENTATION,
    )


def _dispatch_presentation_plan(org_repo: str, render_result: dict) -> DispatchResult:
    return dispatch_tool_call(
        {
            "function": {
                "name": "build_presentation_plan",
                "arguments": json.dumps({"org_repo": org_repo}),
            }
        },
        _READ_ONLY_PERMISSIONS,
        extra_kwargs={
            "original_text": render_result["original_text"],
            "source_text": render_result.get("source_text", render_result["original_text"]),
            "candidate_text": render_result["final_text"],
            "source_revision": render_result["source_revision"],
            "product_facts_v2": render_result.get("product_facts_v2"),
        },
        caller_domain=README_PRESENTATION,
    )


def _dispatch_deterministic_validation(org_repo: str, render_result: dict) -> DispatchResult:
    return dispatch_tool_call(
        {
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
        },
        _READ_ONLY_PERMISSIONS,
        caller_domain=INDEPENDENT_VERIFICATION,
    )


def independent_render_context(
    org_repo: str,
    *,
    force_regenerate: bool = False,
    product_facts_v2: dict | None = None,
) -> dict:
    """This module's OWN independent render -> plan -> deterministic-validate
    chain -- dispatches the same three public capabilities `_verify_node`
    dispatches (`render_readme_candidate`, `build_presentation_plan`,
    `verify_readme_candidate`), but as this module's own separate call
    sequence, never by reading `specialists/readme_presentation.py`'s own
    `DomainStateV1`/`state.details`. This is the default candidate-
    regeneration path `run_independent_review_with_repair_loop()` uses when
    a caller does not inject its own `regenerate_context`.

    Returns `{"original_text", "final_text", "presentation_plan",
    "deterministic_validation_result"}` -- the exact shape `run_independent_
    readme_review()` and the repair loop both consume. Raises `RuntimeError`
    (matching `readme/candidate_pipeline.py`'s own "pipeline dispatch
    failed, abort" precedent -- e.g. its `push-block verification failed`
    check) on any dispatch failure: a broken render/plan/validate chain
    makes independent review meaningless to attempt, so this fails loud
    rather than fabricating a placeholder context."""
    render_dispatch = _dispatch_render(
        org_repo,
        force_regenerate=force_regenerate,
        product_facts_v2=product_facts_v2,
    )
    if render_dispatch.outcome != "executed" or render_dispatch.result is None:
        raise RuntimeError(
            f"render_readme_candidate:{render_dispatch.outcome}:{render_dispatch.error}"
        )
    render_result = render_dispatch.result

    plan_dispatch = _dispatch_presentation_plan(org_repo, render_result)
    if plan_dispatch.outcome != "executed" or plan_dispatch.result is None:
        raise RuntimeError(f"build_presentation_plan:{plan_dispatch.outcome}:{plan_dispatch.error}")

    validation_dispatch = _dispatch_deterministic_validation(org_repo, render_result)
    if validation_dispatch.outcome != "executed" or validation_dispatch.result is None:
        raise RuntimeError(
            f"verify_readme_candidate:{validation_dispatch.outcome}:{validation_dispatch.error}"
        )

    return {
        "original_text": render_result["original_text"],
        "final_text": render_result["final_text"],
        "presentation_plan": plan_dispatch.result,
        "deterministic_validation_result": validation_dispatch.result,
        "product_facts_v2": render_result.get("product_facts_v2"),
    }


def run_independent_review_with_repair_loop(
    org_repo: str,
    backend: StateBackend | None,
    initial_context: dict,
    *,
    client: _AnalysisClientLike | None = None,
    regenerate_context: Callable[[IndependentReadmeReviewResultV1, int], dict] | None = None,
    review_runner: (Callable[[str, dict, int], IndependentReadmeReviewResultV1] | None) = None,
    reviewer_standard_hash: str | None = None,
    review_observed_by: str = _OBSERVED_BY,
) -> RepairLoopOutcomeV1:
    """Compatibility wrapper for the dedicated repair-control module."""

    from readme_agent.specialists.readme_review_repair_loop import (
        run_independent_review_with_repair_loop as run_repair_loop,
    )

    return run_repair_loop(
        org_repo,
        backend,
        initial_context,
        client=client,
        regenerate_context=regenerate_context,
        review_runner=review_runner,
        reviewer_standard_hash=reviewer_standard_hash,
        review_observed_by=review_observed_by,
    )
