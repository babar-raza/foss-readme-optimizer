"""Orchestrates agentic `product_truth` drafting + gating + a bounded repair
loop (`RPOC-033`, sprint charter Part B.2 Phase 2 Lane F, design Part C.5).

`facts/agentic_drafting.py::draft_product_truth()` produces exactly one
candidate draft; this module is where that draft becomes something trusted
enough to report: `capabilities`/`formats` are routed through
`facts/policy_evidence.py::evidence_fact_candidate()` and drafted limitations
through its stricter `limitation_fact_candidate()` polarity gate;
`audience`/`problems_solved` are routed through the EXISTING, UNMODIFIED
`facts/interpretive_evidence.py::groundedness_fact_candidate()` (the new
citation/lexical-coverage gate `RPOC-032` built for exactly this kind of
free-text claim); `minimal_example` is routed through
`facts/local_verification.py`'s real per-ecosystem verifier
(`RPOC-034`/`035`). Any field that comes back `blocked` from any of these
three mechanisms is never silently dropped or guessed past
(`OWN-009`/`OWN-010`): it is re-drafted with the gate's own specific failure
reasons fed back as a hint, bounded to
`MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS` retries (matching
`MAX_PROSE_REPAIR_ATTEMPTS`/`MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS`'s own
small-integer-with-a-documented-limitation convention), and escalated as a
BACKLOG-shaped finding once the bound is exhausted -- the same shape
`specialists/independent_readme_review.py::_build_backlog_finding()`
already established.

**Never writes to `config/policies/*.yml`.** The whole point of this
capability's own `GOV-014` reviewability bar: it returns a proposed
`product_truth`-shaped result (validated against the real `registry.models.
ProductTruthPolicy`, so it is provably policy-YAML-compatible) plus the
resulting `ProductFactsV2`, for a human or a later, separate persistence
step to act on -- this module has no write path of its own, deliberately.

Orchestration logic (`orchestrate_product_truth_draft()`) is a pure function
over already-resolved inputs (a `ProductFactsV2`, a repo root, a
draft-producing callable, a minimal-example-verifying callable) -- kept
separate from `execute()`'s own wiring (registry lookup, clone, live LLM
client, real disposable build) so it is directly unit-testable against a
fake draft/verify callable and a real temp-directory repo root, exercising
the REAL gates for real, never a reimplementation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.facts import agentic_drafting
from readme_agent.facts.agentic_drafting import DraftProductTruthV1
from readme_agent.facts.code_normalization import normalize_generated_code
from readme_agent.facts.example_quality import generated_example_quality_failures
from readme_agent.facts.interpretive_evidence import groundedness_fact_candidate
from readme_agent.facts.local_verification import (
    LocalProductVerificationV1,
    verify_local_product_example,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.policy_evidence import (
    evidence_fact_candidate,
    evidence_failures,
    limitation_fact_candidate,
)
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.repository_examples import repository_readme_example_candidates
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import (
    README_DRAFTABLE_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy, ProductTruthPolicy
from readme_agent.repository_snapshot import (
    RepositorySnapshotV1,
    capture_repository_snapshot,
    local_fact_verification_allowed,
)

CAPABILITY_ID = "draft_product_truth"

# RPOC-033: same small-integer-with-documented-limitation convention as
# `MAX_PROSE_REPAIR_ATTEMPTS`/`MAX_INDEPENDENT_REVIEW_REPAIR_ATTEMPTS` --
# both already =2 for the identical reason: no operational history yet to
# justify a different value, and every attempt costs one more live LLM call
# (and, for `example.minimal`, potentially one more real disposable build).
MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS = 2

# The fields this capability drafts and gates -- excluded wholesale from the
# pre-existing `facts_so_far` candidates before the freshly-gated versions
# are added back in (see `execute()`), so a repository that already has a
# hand-authored `product_truth` (this taskcard's own live dry-run anchor,
# `aspose-cells-foss`) does not have its existing higher-precedence
# `approved_policy` facts silently win over -- and thereby mask -- what
# THIS draft actually produced. The returned `product_facts_v2` answers
# "what would ProductFactsV2 look like if this draft were adopted", which is
# this capability's actual job for its real target repos (the 27 with no
# product_truth at all, where these fields are already `missing` anyway).
_GATED_FIELDS: tuple[str, ...] = README_DRAFTABLE_PRODUCT_FIELDS

# The 3 evidence-backed fields, re-fed forward as fresh citable grounding
# material for `product.audience`/`product.problems_solved` once they pass
# their own gate -- see `orchestrate_product_truth_draft()`'s own docstring
# and `facts/agentic_drafting.py::_SELF_REFERENTIAL_FIELDS`'s docstring for
# why this is real, legitimate grounding (mechanically re-checkable against
# real repository files), not a shortcut around either gate.
_EVIDENCE_BACKED_FIELDS: tuple[str, ...] = (
    "product.capabilities",
    "product.formats",
    "product.limitations",
)

DraftFn = Callable[[dict[str, list[str]] | None, ProductFactsV2], DraftProductTruthV1]
VerifyExampleFn = Callable[[MinimalExamplePolicy], LocalProductVerificationV1 | None]


def _reset_fields_to_missing(
    facts_so_far: ProductFactsV2, fields: tuple[str, ...]
) -> ProductFactsV2:
    """Returns a copy of `facts_so_far` with every field in `fields` reset to
    an honest `missing` placeholder -- used once, at the start of
    `execute()`, so a repository's own PRE-EXISTING `product_truth` (e.g.
    this taskcard's own live dry-run anchor, `aspose-cells-foss`) never
    leaks into this drafting pass as ground truth to copy or cite. Every
    field this capability drafts starts from the same honest "nothing
    established yet" baseline, whether or not the real repository already
    has a hand-authored policy -- the only way to keep the dry-run
    comparison meaningful."""
    kept = [fact for fact in facts_so_far.facts if fact.field not in fields]
    selected = {
        field_name: fact_id
        for field_name, fact_id in facts_so_far.selected_fact_ids.items()
        if field_name not in fields
    }
    for field_name in fields:
        missing = FactRecordV2(
            fact_id=descriptive_fact_id(field_name, "not-yet-drafted"),
            field=field_name,
            value=None,
            source=FactSourceV2(
                source_type="mechanical_repository",
                location=f"repository://{facts_so_far.org_repo}",
                retrieved_at="1970-01-01T00:00:00+00:00",
            ),
            verification_state="missing",
            authoritative_owner="repository-owner",
            confidence=0.0,
            affected_surfaces=SURFACE_DEPENDENCIES[field_name],
        )
        kept.append(missing)
        selected[field_name] = missing.fact_id
    return ProductFactsV2(
        org_repo=facts_so_far.org_repo,
        facts=kept,
        selected_fact_ids=selected,
        package_root_roles=facts_so_far.package_root_roles,
    )


def _replace_facts(
    facts_so_far: ProductFactsV2, updates: dict[str, FactRecordV2]
) -> ProductFactsV2:
    """Returns a copy of `facts_so_far` with each `updates` field's currently-
    selected fact swapped out for the given one -- used between repair
    iterations to fold this SAME draft's own freshly-gated
    capabilities/formats/limitations back in as citable grounding for the
    next attempt's `product.audience`/`product.problems_solved`. Removes the
    old fact for that field before adding the new one (never accumulates
    both), keeping `ProductFactsV2`'s own fact_id-uniqueness invariant
    intact regardless of how many repair rounds run."""
    kept = [fact for fact in facts_so_far.facts if fact.field not in updates]
    kept.extend(updates.values())
    selected = dict(facts_so_far.selected_fact_ids)
    for field_name, fact in updates.items():
        selected[field_name] = fact.fact_id
    return ProductFactsV2(
        org_repo=facts_so_far.org_repo,
        facts=kept,
        selected_fact_ids=selected,
        package_root_roles=facts_so_far.package_root_roles,
    )


class DraftProductTruthOrchestrationResultV1(BaseModel):
    """`orchestrate_product_truth_draft()`'s own return value. `gated_facts`
    always has exactly the 6 `_GATED_FIELDS` keys, whatever the outcome --
    a field that never passes still has its final (still-`blocked`)
    `FactRecordV2` recorded here, never omitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    draft: DraftProductTruthV1
    gated_facts: dict[str, FactRecordV2]
    findings: list[dict] = Field(default_factory=list)
    repair_attempts: int


def _extract_failure_reasons(fact: FactRecordV2) -> list[str]:
    """Failure reasons already produced by whichever real gate blocked this
    field -- never re-derived or paraphrased here. `evidence_fact_candidate()`
    stores them under `value["evidence_failures"]`, `groundedness_fact_
    candidate()` under `value["groundedness_failures"]`; `_gate_minimal_
    example()` below follows the identical `evidence_failures` key for its
    own pre-check, and a `verification_detail` string for a local-build
    failure past that pre-check."""
    value = fact.value
    if not isinstance(value, dict):
        return [f"{fact.field}: blocked with no structured failure detail"]
    for key in ("evidence_failures", "groundedness_failures", "quality_failures"):
        reasons = value.get(key)
        if reasons:
            return list(reasons)
    detail = value.get("verification_detail")
    return [detail] if detail else [f"{fact.field}: blocked with no structured failure detail"]


def _local_verification_detail(result: LocalProductVerificationV1 | None) -> str:
    """Return bounded compiler feedback that a repair attempt can act on."""

    if result is None:
        return "local build/example verification was not executed for this draft"
    execution = result.example_compile or result.build
    if execution is None or execution.return_code == 0:
        return result.detail
    diagnostic = "\n".join(part.strip() for part in (execution.stderr, execution.stdout) if part)
    if not diagnostic:
        return result.detail
    # The process runs under example_execution.secret_free_environment().
    # Keep the first compiler diagnostics (where syntax/type errors appear),
    # bounded so repair prompts and evidence cannot grow with build logs.
    diagnostic = diagnostic[:2000]
    return f"{result.detail}; compiler diagnostic:\n{diagnostic}"


def _gate_minimal_example(
    example: MinimalExamplePolicy,
    root: Path,
    source_revision: str | None,
    observed_at: str,
    verify_example_fn: VerifyExampleFn,
) -> FactRecordV2:
    """Mirrors `facts/provider.py::_local_verification_facts()`'s own
    two-phase shape: a cheap `evidence_failures()` pre-check for the
    example's own `evidence_paths`/`required_symbols` BEFORE ever attempting
    a real disposable build (never waste a build on a citation that is
    already invalid), then the real per-ecosystem verifier."""
    source = FactSourceV2(
        source_type="agent_drafted",
        location="agent-draft://example.minimal",
        source_revision=source_revision,
        retrieved_at=observed_at,
    )
    pre_check_failures = evidence_failures(root, example.evidence_paths, example.required_symbols)
    quality_failures = generated_example_quality_failures(example.language, example.code)
    if pre_check_failures or quality_failures:
        return FactRecordV2(
            fact_id=descriptive_fact_id("example.minimal", "agent-drafted-blocked"),
            field="example.minimal",
            value={
                "language": example.language,
                "class_name": example.class_name,
                "code": example.code,
                "evidence_failures": pre_check_failures,
                "quality_failures": quality_failures,
            },
            source=source,
            verification_state="blocked",
            authoritative_owner="repository-owner",
            confidence=0.0,
            affected_surfaces=SURFACE_DEPENDENCIES["example.minimal"],
        )

    local_result = verify_example_fn(example)
    outcome = local_result.outcome if local_result is not None else "BLOCKED_LOCAL_VERIFICATION"
    detail = _local_verification_detail(local_result)
    verified = (
        local_result is not None
        and local_result.truth_eligible
        and outcome == "SOURCE_BUILD_VERIFIED"
    )
    return FactRecordV2(
        fact_id=descriptive_fact_id("example.minimal", "agent-drafted-example"),
        field="example.minimal",
        value={
            "language": example.language,
            "class_name": example.class_name,
            "code": example.code,
            "verification_outcome": outcome,
            "verification_detail": detail,
            **(local_result.fact_projection() if local_result is not None else {}),
        },
        source=source,
        verification_state="verified" if verified else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if verified else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["example.minimal"],
    )


def _normalize_draft_example(draft: DraftProductTruthV1) -> DraftProductTruthV1:
    """Normalize generated code before both verification and evidence output."""

    example = draft.minimal_example
    normalized = normalize_generated_code(example.code)
    if normalized == example.code:
        return draft
    return draft.model_copy(
        update={"minimal_example": example.model_copy(update={"code": normalized})}
    )


def _gate_draft(
    draft: DraftProductTruthV1,
    facts_so_far: ProductFactsV2,
    root: Path,
    source_revision: str | None,
    observed_at: str,
    verify_example_fn: VerifyExampleFn,
) -> dict[str, FactRecordV2]:
    """Routes each field through its real, unmodified gate -- never a
    reimplementation. `capabilities`/`formats` ->
    `evidence_fact_candidate()` (identical call shape
    `facts/repository_ingestion.py::ingest_repository_product_facts()`
    already uses for a human-authored policy's own `product_truth`);
    `limitations` -> `limitation_fact_candidate()`, which additionally
    prevents positive API-existence evidence from proving a negative
    limitation.
    `audience`/`problems_solved` -> `groundedness_fact_candidate()`.
    `minimal_example` -> `_gate_minimal_example()` above."""
    return {
        "product.capabilities": evidence_fact_candidate(
            root, source_revision, observed_at, "product.capabilities", draft.capabilities
        ),
        "product.formats": evidence_fact_candidate(
            root, source_revision, observed_at, "product.formats", draft.formats
        ),
        "product.limitations": limitation_fact_candidate(
            root, source_revision, observed_at, draft.limitations
        ),
        "product.audience": groundedness_fact_candidate(
            "product.audience", draft.audience, facts_so_far, source_revision, observed_at
        ),
        "product.problems_solved": groundedness_fact_candidate(
            "product.problems_solved",
            draft.problems_solved,
            facts_so_far,
            source_revision,
            observed_at,
        ),
        "example.minimal": _gate_minimal_example(
            draft.minimal_example, root, source_revision, observed_at, verify_example_fn
        ),
    }


def _build_finding(org_repo: str, field_name: str, fact: FactRecordV2, attempts: int) -> dict:
    """BACKLOG-shaped finding (`plans/GOVERNANCE.md` `GOV-014`), same dict
    shape `specialists/independent_readme_review.py::_build_backlog_
    finding()` already established for the identical "bounded repair
    attempts exhausted, still blocked" outcome -- `OWN-010` requires this
    surfaced as a finding, never a silent guess."""
    return {
        "repository": org_repo,
        "field": field_name,
        "status": "BLOCKED",
        "reason": (
            f"draft_product_truth: field {field_name!r} still blocked after "
            f"{attempts}/{MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS} repair attempts"
        ),
        "actionable": True,
        "repair_attempts": attempts,
        "failure_reasons": _extract_failure_reasons(fact),
    }


def orchestrate_product_truth_draft(
    org_repo: str,
    facts_so_far: ProductFactsV2,
    root: Path,
    source_revision: str | None,
    observed_at: str,
    *,
    draft_fn: DraftFn,
    verify_example_fn: VerifyExampleFn,
) -> DraftProductTruthOrchestrationResultV1:
    """The bounded draft -> gate -> repair cycle. `draft_fn(repair_hints,
    current_facts)` produces one candidate draft (`None` hints on the first
    attempt, the prior attempt's own per-field failure reasons on a repair
    attempt). Stops as soon as every field passes, or once
    `MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS` repair attempts are exhausted
    -- whichever comes first -- exactly mirroring `specialists/independent_
    readme_review.py::run_independent_review_with_repair_loop()`'s own
    "one initial attempt + N repairs, always terminates, always escalates
    rather than looping forever" shape.

    `current_facts` starts as `facts_so_far` and is augmented after every
    gate pass: whichever of `product.capabilities`/`formats`/`limitations`
    just came back `verified` is folded in (`_replace_facts()`), so a
    SUBSEQUENT repair attempt's `product.audience`/`product.problems_solved`
    drafting can cite THIS SAME draft's own freshly-verified technical
    claims -- real, independently re-checkable grounding material, and for
    a repository with no pre-existing `product_truth` at all (this
    capability's actual target case), very often the only rich descriptive
    vocabulary available at all. The FIRST attempt has no such augmentation
    yet (nothing has been gated), so `product.audience`/`problems_solved`
    commonly only pass starting on a repair attempt -- an expected shape of
    this design, not a defect."""
    current_facts = facts_so_far
    hints: dict[str, list[str]] | None = None
    attempt = 0
    draft: DraftProductTruthV1
    gated: dict[str, FactRecordV2]
    while True:
        draft = _normalize_draft_example(draft_fn(hints, current_facts))
        gated = _gate_draft(
            draft, current_facts, root, source_revision, observed_at, verify_example_fn
        )
        passed_evidence_facts = {
            field_name: fact
            for field_name, fact in gated.items()
            if field_name in _EVIDENCE_BACKED_FIELDS and fact.verification_state == "verified"
        }
        if passed_evidence_facts:
            current_facts = _replace_facts(current_facts, passed_evidence_facts)
        blocked = {
            field_name: fact
            for field_name, fact in gated.items()
            if fact.verification_state == "blocked"
        }
        if not blocked or attempt >= MAX_PRODUCT_TRUTH_DRAFT_REPAIR_ATTEMPTS:
            break
        hints = {field_name: _extract_failure_reasons(fact) for field_name, fact in blocked.items()}
        attempt += 1

    example_fact = gated.get("example.minimal")
    if example_fact is not None and example_fact.verification_state == "blocked":
        for repository_example in repository_readme_example_candidates(
            root,
            draft.minimal_example.language,
            supporting_paths=draft.minimal_example.evidence_paths,
        ):
            fallback_fact = _gate_minimal_example(
                repository_example,
                root,
                source_revision,
                observed_at,
                verify_example_fn,
            )
            if fallback_fact.verification_state != "verified":
                continue
            draft = draft.model_copy(update={"minimal_example": repository_example})
            gated["example.minimal"] = fallback_fact
            break

    blocked = {
        field_name: fact
        for field_name, fact in gated.items()
        if fact.verification_state == "blocked"
    }
    findings = [
        _build_finding(org_repo, field_name, fact, attempt) for field_name, fact in blocked.items()
    ]
    return DraftProductTruthOrchestrationResultV1(
        draft=draft, gated_facts=gated, findings=findings, repair_attempts=attempt
    )


def _to_policy_shape(draft: DraftProductTruthV1) -> dict:
    """Converts the drafted, not-yet-gated claims into the exact
    `ProductTruthPolicy` dict shape a human would hand-author in
    `config/policies/*.yml` (see `config/policies/aspose-cells-foss.yml`'s
    own real `product_truth:` block) -- `InterpretiveClaimV1.text` for the
    two free-text fields, `EvidenceBackedProductFact`/`MinimalExamplePolicy`
    unchanged for the rest. Round-tripped through `ProductTruthPolicy.
    model_validate()` as a real, load-bearing sanity check, not just a
    comment -- proves this dict genuinely is policy-YAML-compatible rather
    than merely resembling it."""
    shape = {
        "audience": [claim.text for claim in draft.audience],
        "problems_solved": [claim.text for claim in draft.problems_solved],
        "capabilities": [fact.model_dump() for fact in draft.capabilities],
        "formats": [fact.model_dump() for fact in draft.formats],
        "limitations": [fact.model_dump() for fact in draft.limitations],
        "minimal_example": draft.minimal_example.model_dump(),
    }
    ProductTruthPolicy.model_validate(shape)
    return shape


def _promote_source_build_acquisition(
    facts_so_far: ProductFactsV2,
    gated_updates: dict[str, FactRecordV2],
) -> dict[str, FactRecordV2]:
    """Use the successful drafted-example build as source-acquisition proof."""

    updates = dict(gated_updates)
    verified_example = updates["example.minimal"]
    acquisition = facts_so_far.selected_fact("installation.verified_acquisition")
    if (
        verified_example.verification_state == "verified"
        and isinstance(verified_example.value, dict)
        and isinstance(acquisition.value, dict)
        and acquisition.value.get("method") == "source_build"
    ):
        updates["installation.verified_acquisition"] = acquisition.model_copy(
            update={
                "value": {
                    "method": "source_build",
                    "outcome": "SOURCE_BUILD_VERIFIED",
                    "detail": verified_example.value["verification_detail"],
                },
                "verification_state": "verified",
                "confidence": 1.0,
            }
        )
    return updates


def execute(
    org_repo: str,
    *,
    client=None,
    repository_snapshot: RepositorySnapshotV1 | None = None,
    base_facts: ProductFactsV2 | None = None,
) -> dict:
    """Real wiring: consumes or fetches `ProductFactsV2` once and consumes
    the supervisor's immutable snapshot when injected. Direct callers still
    get a real on-disk baseline clone (`clone_baseline`, mirroring
    `capabilities/compare_against_presentation_standard.py`'s own
    established pattern for a capability that needs direct file reads, not
    just manifest parsing), builds a real `RepositorySnapshotV1` for the
    disposable local-verification path, then delegates the actual
    draft/gate/repair cycle to `orchestrate_product_truth_draft()`.

    `facts_so_far` is fetched exactly once and shared across the drafting
    closure AND the gating closure -- see `facts/agentic_drafting.py::
    draft_product_truth()`'s own docstring for why calling
    `collect_product_facts()` a second time per repair attempt would be
    genuinely wasteful (it can trigger a real local build), not just
    architecturally impure. Before drafting starts, `_GATED_FIELDS` are
    reset to `missing` (`_reset_fields_to_missing()`) so this drafting pass
    never sees -- and cannot copy from -- a repository's own pre-existing
    `product_truth`, whether or not one exists."""
    if repository_snapshot is not None and repository_snapshot.org_repo != org_repo:
        raise ValueError(
            f"injected repository snapshot belongs to {repository_snapshot.org_repo!r}, "
            f"not {org_repo!r}"
        )
    if base_facts is not None and base_facts.org_repo != org_repo:
        raise ValueError(
            f"injected product facts belong to {base_facts.org_repo!r}, not {org_repo!r}"
        )

    if base_facts is None:
        facts_result = collect_product_facts(org_repo)
        facts_so_far = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
    else:
        facts_so_far = base_facts
    drafting_facts_so_far = _reset_fields_to_missing(facts_so_far, _GATED_FIELDS)

    if repository_snapshot is None:
        entry = require_listed(org_repo)
        baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
        clone_baseline(entry, baseline_path)
        snapshot = capture_repository_snapshot(entry, baseline_path)
    else:
        snapshot = repository_snapshot
    observed_at = datetime.now(UTC).isoformat()

    def draft_fn(
        hints: dict[str, list[str]] | None, current_facts: ProductFactsV2
    ) -> DraftProductTruthV1:
        return agentic_drafting.draft_product_truth(
            org_repo, facts_so_far=current_facts, repair_hints=hints, client=client
        )

    def verify_example_fn(example: MinimalExamplePolicy) -> LocalProductVerificationV1 | None:
        if not local_fact_verification_allowed():
            return None
        return verify_local_product_example(snapshot, example)

    result = orchestrate_product_truth_draft(
        org_repo,
        drafting_facts_so_far,
        snapshot.root_path,
        snapshot.source_revision,
        observed_at,
        draft_fn=draft_fn,
        verify_example_fn=verify_example_fn,
    )

    gated_updates = _promote_source_build_acquisition(facts_so_far, result.gated_facts)
    candidates = [fact for fact in facts_so_far.facts if fact.field not in gated_updates]
    candidates.extend(gated_updates.values())
    resolved = resolve_product_facts(
        org_repo,
        candidates,
        missing_source=FactSourceV2(
            source_type="mechanical_repository",
            location=f"repository://{org_repo}",
            retrieved_at=observed_at,
        ),
        missing_field_surfaces=SURFACE_DEPENDENCIES,
        package_root_roles=facts_so_far.package_root_roles,
    )

    return {
        "org_repo": org_repo,
        "proposed_product_truth": _to_policy_shape(result.draft),
        "product_facts_v2": resolved.model_dump(mode="json"),
        "findings": result.findings,
        "repair_attempts": result.repair_attempts,
    }


MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Draft product truth",
    purpose="Read-only: drafts a proposed product_truth (audience, problems_solved, "
    "capabilities, formats, limitations, minimal_example) for a repository with no "
    "policy-authored product_truth yet, grounding every claim in mechanically-established "
    "objective facts and real repository context, then routes every field through the "
    "existing deterministic evidence/groundedness/local-verification gates with a bounded "
    "repair loop. Never writes to config/policies/*.yml -- the result is a reviewable "
    "proposal only.",
    category="product_facts",
    owner="readme_agent.capabilities.draft_product_truth",
    execution_type="agentic_analysis",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "proposed_product_truth": "object",
        "product_facts_v2": "object",
        "findings": "array",
        "repair_attempts": "integer",
    },
    preconditions=[
        "org_repo must be listed in data/products.json and have a policy_profile configured "
        "(same read-only gate as get_product_facts)",
    ],
    required_permissions=["read_only_local", "read_only_network"],
    side_effect_class="read_only_network",
    input_model=OrgRepoOnlyInputV1,
    tools_used=[
        "facts.agentic_drafting.draft_product_truth",
        "facts.policy_evidence.evidence_fact_candidate",
        "facts.interpretive_evidence.groundedness_fact_candidate",
        "facts.local_verification.verify_local_product_example",
        "facts.provider.collect_product_facts",
        "llm.analysis_client.LiveAnalysisClient",
    ],
    failure_modes=[
        "NotAllowlistedError if org_repo is not listed in data/products.json or has no "
        "policy_profile configured",
        "LLMError if the drafting model's response never validates against "
        "DraftProductTruthV1 (schema failure, not a gate-blocked field -- gate-blocked "
        "fields degrade to a finding, never an exception)",
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back; the drafted "
    "product_truth is a proposal only, never written to config/policies/*.yml",
    tests=["tests/unit/test_draft_product_truth_capability.py"],
    requirement_ids=["OWN-009", "OWN-010"],
)
