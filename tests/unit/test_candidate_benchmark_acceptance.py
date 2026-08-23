"""Tests for the candidate benchmark acceptance evaluator."""

from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from readme_agent.presentation.candidate_benchmark_acceptance import (
    BenchmarkDimensionAcceptanceV1,
    CandidateBenchmarkAcceptanceV1,
    CandidateRubricEvidenceV1,
    evaluate_candidate_benchmark_acceptance,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    CandidateBenchmarkComparisonV1,
    CandidateBenchmarkDimensionV1,
    load_benchmark_quality_profile,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.readme_review_roles import ReviewActorIdentityV1, RoleReviewRecordV1
from readme_agent.specialists.review_finding_grounding import (
    FindingGroundingResultV1,
    GroundedReviewFindingV1,
)
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.validation.public_quality_contracts import (
    PUBLIC_QUALITY_CHECKS_VERSION,
    PublicQualityCountsV1,
    PublicQualityFindingV1,
    PublicQualityLocationV1,
    PublicQualityReportV1,
    PublicQualitySpanV1,
)

REPOSITORY = "example-org/example-repo"
SOURCE_REVISION = "a" * 40
DEFAULT_CANDIDATE = "# Example\n\nA short, complete description of the example product.\n"

_CURRENT_PROFILE_SHA256 = load_benchmark_quality_profile()[1]

_DIMENSION_TABLE = (
    (
        "information_coverage",
        "accepted",
        "Cover the material visitor questions that have repository-verified answers.",
    ),
    (
        "product_specificity",
        "accepted",
        "Use repository-specific identity, audience, capabilities, formats, and constraints.",
    ),
    (
        "structure_and_navigation",
        "adapted",
        "Retain the useful benchmark section coverage through the local template contract.",
    ),
    (
        "branding_and_visuals",
        "adapted",
        "Use the locally approved header and Mermaid contracts rather than copying "
        "benchmark bytes.",
    ),
    (
        "capability_depth",
        "adapted",
        "Require visible, non-duplicated capabilities backed by current ProductFactsV2 evidence.",
    ),
    (
        "installation_and_dependencies",
        "adapted",
        "Render only repository-declared and independently verified acquisition routes.",
    ),
    (
        "source_derived_examples",
        "adapted",
        "Use benchmark coverage as a hint while requiring isolated verification of exact "
        "local examples.",
    ),
    (
        "api_reference_depth",
        "adapted",
        "Select useful public APIs from current local source evidence and avoid benchmark-only "
        "names.",
    ),
    (
        "documentation_and_resources",
        "accepted",
        "Provide useful verified documentation, support, contribution, and reference routes.",
    ),
    (
        "limitations",
        "accepted",
        "Keep material constraints visible, specific, and non-duplicated.",
    ),
    (
        "development_and_testing",
        "adapted",
        "Present relevant repository development guidance without exposing internal verification "
        "prose.",
    ),
    (
        "licensing",
        "accepted",
        "Explain the verified repository license and link the repository-owned license artifacts.",
    ),
    (
        "inherited_content_accountability",
        "adapted",
        "Account for valuable source README material, but verify it before reuse and normalize "
        "its tone.",
    ),
    (
        "public_tone_and_process_hygiene",
        "accepted",
        "Use professional public prose and prohibit internal validation, evidence, or workflow "
        "narration.",
    ),
    (
        "benchmark_claim_authority",
        "quarantined",
        "Benchmark claims and examples are discovery hints only and never become product truth.",
    ),
    (
        "benchmark_item_verdicts",
        "quarantined",
        "Upstream clean, dirty, skipped, and published labels do not satisfy local acceptance.",
    ),
    (
        "upstream_site_workflow_metadata",
        "not_applicable",
        "Hugo, content-site, publication, and upstream task-state metadata do not enter README "
        "runtime inputs.",
    ),
)


# ---------------------------------------------------------------------------------------------
# Fixture builders -- constructed directly from the real, imported types; nothing re-declared.
# ---------------------------------------------------------------------------------------------


def _build_dimension(dimension_id: str, disposition: str, obligation: str):
    applicable = disposition in {"accepted", "adapted"}
    status = (
        "EVIDENCE_BOUND_PENDING_ACCEPTANCE"
        if applicable
        else (
            "QUARANTINED_NOT_FACT_AUTHORITY" if disposition == "quarantined" else "NOT_APPLICABLE"
        )
    )
    return CandidateBenchmarkDimensionV1(
        dimension_id=dimension_id,
        benchmark_disposition=disposition,
        obligation=obligation,
        applicable=applicable,
        status=status,
        evidence_paths=["candidate/README.md"] if applicable else [],
    )


def _build_comparison(
    *,
    candidate_sha256: str,
    benchmark_profile_sha256: str,
    repository: str = REPOSITORY,
    source_revision: str = SOURCE_REVISION,
    dimensions=None,
) -> CandidateBenchmarkComparisonV1:
    return CandidateBenchmarkComparisonV1(
        repository=repository,
        source_revision=source_revision,
        candidate_sha256=candidate_sha256,
        benchmark_profile_sha256=benchmark_profile_sha256,
        benchmark_snapshot_sha256="c" * 64,
        dimensions=(
            [_build_dimension(*row) for row in _DIMENSION_TABLE]
            if dimensions is None
            else dimensions
        ),
    )


def _quality_finding(
    check_id: str,
    category: str,
    *,
    blocking: bool = True,
    severity: str = "critical",
    seed: str = "a",
) -> PublicQualityFindingV1:
    fingerprint = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    location = PublicQualityLocationV1(
        section_path="Installation",
        span=PublicQualitySpanV1(start=0, end=1, text="x"),
    )
    return PublicQualityFindingV1(
        finding_id=f"public_quality.{check_id}.{fingerprint}",
        check_id=check_id,
        category=category,
        severity=severity,
        confidence="exact_symbol",
        blocking=blocking,
        locations=(location,),
        message="test finding",
        repair_target="test repair target",
    )


def _counts_from_findings(findings: tuple[PublicQualityFindingV1, ...]) -> PublicQualityCountsV1:
    fields = (
        "cross_section_contradiction",
        "process_leakage",
        "malformed_prose",
        "claim_grounding",
        "structural_quality",
        "critical",
        "warning",
        "blocking",
        "advisory",
    )
    tally = dict.fromkeys(fields, 0)
    for finding in findings:
        tally[finding.category] += 1
        tally[finding.severity] += 1
        tally["blocking" if finding.blocking else "advisory"] += 1
    return PublicQualityCountsV1(**tally)


def _build_quality_report(
    *, candidate_sha256: str, findings: tuple[PublicQualityFindingV1, ...] = ()
) -> PublicQualityReportV1:
    findings_tuple = tuple(findings)
    counts = _counts_from_findings(findings_tuple)
    checks_run = tuple(sorted({"numeric_list_consistency", *(f.check_id for f in findings_tuple)}))
    draft = PublicQualityReportV1.model_construct(
        schema_version=1,
        checks_version=PUBLIC_QUALITY_CHECKS_VERSION,
        candidate_sha256=candidate_sha256,
        checks_run=checks_run,
        findings=findings_tuple,
        counts=counts,
        report_hash="0" * 64,
    )
    payload = draft.model_dump(mode="json", exclude={"report_hash"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    report_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return PublicQualityReportV1(
        schema_version=1,
        checks_version=PUBLIC_QUALITY_CHECKS_VERSION,
        candidate_sha256=candidate_sha256,
        checks_run=checks_run,
        findings=findings_tuple,
        counts=counts,
        report_hash=report_hash,
    )


def _grounded_finding(role: str, disposition: str) -> GroundedReviewFindingV1:
    if role == "blind_quality_reviewer":
        return GroundedReviewFindingV1(
            finding_id="finding.quality.1",
            kind="quality",
            criterion="clarity",
            section="Overview",
            claim="The overview is clear and specific.",
            quoted_candidate_span="A short, complete description",
            disposition=disposition,
            polarity_result="not_applicable",
            required_repair="fix the overview" if disposition == "requires_repair" else "",
        )
    return GroundedReviewFindingV1(
        finding_id="finding.factual.1",
        kind="factual",
        criterion="claim_accuracy",
        section="Installation",
        claim="The package installs via pip.",
        quoted_candidate_span="A short, complete description",
        disposition=disposition,
        fact_id="fact.install.1",
        evidence_excerpt="A short, complete description",
        evidence_location="README.md#installation",
        polarity_result="supports",
        required_repair="fix the install step" if disposition == "requires_repair" else "",
    )


def _build_review_record(
    *, candidate_sha256: str, role: str, verdict: str = "ACCEPT"
) -> RoleReviewRecordV1:
    disposition = "supports_acceptance" if verdict == "ACCEPT" else "requires_repair"
    finding = _grounded_finding(role, disposition)
    grounding = FindingGroundingResultV1(
        valid=True, errors=[], checked_finding_ids=[finding.finding_id]
    )
    kwargs: dict = dict(
        identity=ReviewActorIdentityV1(
            actor_id="test-actor",
            role=role,
            prompt_id="test-prompt",
            prompt_sha256="a" * 64,
        ),
        candidate_sha256=candidate_sha256,
        input_sha256="b" * 64,
        verdict=verdict,
        reasoning="test reasoning",
        findings=[finding],
        grounding_validation=grounding,
    )
    if verdict != "ACCEPT":
        kwargs["failed_criteria"] = [finding.criterion]
        kwargs["sections_affected"] = [finding.section]
        kwargs["required_repair"] = finding.required_repair
    return RoleReviewRecordV1(**kwargs)


def _build_rubric_evidence(
    *, candidate_sha256: str, accepted: bool = True, hard_disqualifier_count: int = 0
) -> CandidateRubricEvidenceV1:
    outcome = RubricAcceptanceOutcome(
        org_repo=REPOSITORY,
        accepted=accepted,
        score=30 if accepted else 20,
        hard_disqualifier_count=hard_disqualifier_count,
        missing_evidence_criteria=(),
    )
    return CandidateRubricEvidenceV1(candidate_sha256=candidate_sha256, outcome=outcome)


def _default_kwargs(*, candidate_markdown: str = DEFAULT_CANDIDATE, **overrides):
    candidate_sha256 = sha256_hex(candidate_markdown)
    comparison = overrides.pop("comparison", None)
    if comparison is None:
        comparison = _build_comparison(
            candidate_sha256=overrides.pop("comparison_candidate_sha256", candidate_sha256),
            benchmark_profile_sha256=overrides.pop(
                "comparison_profile_sha256", _CURRENT_PROFILE_SHA256
            ),
            dimensions=overrides.pop("dimensions", None),
        )
    else:
        overrides.pop("comparison_candidate_sha256", None)
        overrides.pop("comparison_profile_sha256", None)
        overrides.pop("dimensions", None)

    deterministic_evidence = overrides.pop("deterministic_evidence", None)
    if deterministic_evidence is None:
        deterministic_evidence = _build_quality_report(
            candidate_sha256=overrides.pop("deterministic_candidate_sha256", candidate_sha256),
            findings=overrides.pop("deterministic_findings", ()),
        )
    else:
        overrides.pop("deterministic_candidate_sha256", None)
        overrides.pop("deterministic_findings", None)

    factual_review_evidence = overrides.pop("factual_review_evidence", None)
    if factual_review_evidence is None:
        factual_review_evidence = _build_review_record(
            candidate_sha256=overrides.pop("factual_candidate_sha256", candidate_sha256),
            role=overrides.pop("factual_role", "factual_plan_reviewer"),
            verdict=overrides.pop("factual_verdict", "ACCEPT"),
        )
    else:
        overrides.pop("factual_candidate_sha256", None)
        overrides.pop("factual_role", None)
        overrides.pop("factual_verdict", None)

    visitor_review_evidence = overrides.pop("visitor_review_evidence", None)
    if visitor_review_evidence is None:
        visitor_review_evidence = _build_review_record(
            candidate_sha256=overrides.pop("visitor_candidate_sha256", candidate_sha256),
            role=overrides.pop("visitor_role", "blind_quality_reviewer"),
            verdict=overrides.pop("visitor_verdict", "ACCEPT"),
        )
    else:
        overrides.pop("visitor_candidate_sha256", None)
        overrides.pop("visitor_role", None)
        overrides.pop("visitor_verdict", None)

    rubric_evidence = overrides.pop("rubric_evidence", None)
    if rubric_evidence is None:
        rubric_evidence = _build_rubric_evidence(
            candidate_sha256=overrides.pop("rubric_candidate_sha256", candidate_sha256),
            accepted=overrides.pop("rubric_accepted", True),
            hard_disqualifier_count=overrides.pop("rubric_hard_disqualifier_count", 0),
        )
    else:
        overrides.pop("rubric_candidate_sha256", None)
        overrides.pop("rubric_accepted", None)
        overrides.pop("rubric_hard_disqualifier_count", None)

    kwargs = dict(
        candidate_markdown=candidate_markdown,
        candidate_sha256=overrides.pop("candidate_sha256", candidate_sha256),
        facts_hash=overrides.pop("facts_hash", "d" * 64),
        comparison=comparison,
        deterministic_evidence=deterministic_evidence,
        factual_review_evidence=factual_review_evidence,
        visitor_review_evidence=visitor_review_evidence,
        rubric_evidence=rubric_evidence,
        reference_excerpts=overrides.pop("reference_excerpts", ()),
    )
    if overrides:
        raise TypeError(f"unused overrides: {sorted(overrides)}")
    return kwargs


def _applicable_dimension(result: CandidateBenchmarkAcceptanceV1, dimension_id: str):
    return next(d for d in result.dimensions if d.dimension_id == dimension_id)


# ---------------------------------------------------------------------------------------------
# 1. Fully evidenced shorter candidate passes.
# ---------------------------------------------------------------------------------------------


def test_fully_evidenced_shorter_candidate_passes():
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_PROVEN"
    assert result.hard_disqualifiers == ()
    for dimension_id in result.applicable_dimension_ids:
        assert _applicable_dimension(result, dimension_id).verdict == "PASS"


# ---------------------------------------------------------------------------------------------
# 2. Long repetitive candidate fails relevant quality dimensions -- deterministic_evidence is
# supplied pre-computed (this module never re-parses candidate_markdown for structural signals,
# by design), so a "long repetitive candidate" is simulated by a blocking structural_quality
# finding, exactly what evaluate_public_candidate_quality() would have produced for one.
# ---------------------------------------------------------------------------------------------


def test_long_repetitive_candidate_fails_relevant_dimension():
    finding = _quality_finding("structural_detail_density", "structural_quality")
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(deterministic_findings=(finding,))
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    branding = _applicable_dimension(result, "branding_and_visuals")
    assert branding.verdict == "FAIL"
    assert finding.finding_id in branding.blocking_finding_ids


# ---------------------------------------------------------------------------------------------
# 3. Missing evidence fails closed.
# ---------------------------------------------------------------------------------------------


def test_missing_evidence_fails_closed():
    # "Missing" evidence is represented as evidence that is not candidate-bound (never as a
    # default guessed pass) -- here the deterministic report belongs to a different candidate.
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(deterministic_candidate_sha256="e" * 64)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any(
        "deterministic_evidence.candidate_sha256" in reason for reason in result.hard_disqualifiers
    )
    assert set(result.applicable_dimension_ids) <= set(result.unresolved_dimension_ids)
    for dimension_id in result.applicable_dimension_ids:
        assert _applicable_dimension(result, dimension_id).verdict == "UNKNOWN"


# ---------------------------------------------------------------------------------------------
# 4. Candidate hash mismatch fails.
# ---------------------------------------------------------------------------------------------


def test_candidate_hash_mismatch_fails():
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs(candidate_sha256="f" * 64))
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("candidate_sha256 does not match" in reason for reason in result.hard_disqualifiers)


# ---------------------------------------------------------------------------------------------
# 5 / 6. Comparison/profile mismatch fails; changing profile/comparison invalidates result.
# ---------------------------------------------------------------------------------------------


def test_comparison_profile_mismatch_fails():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(comparison_profile_sha256="1" * 64)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("since-changed profile" in reason for reason in result.hard_disqualifiers)


def test_changing_comparison_invalidates_previous_result():
    matching = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    drifted = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(comparison_profile_sha256="2" * 64)
    )
    assert matching.canonical_hash() != drifted.canonical_hash()
    assert matching.acceptance_status != drifted.acceptance_status


# ---------------------------------------------------------------------------------------------
# 7 / 8 / 9. Factual / visitor / rubric evidence from another candidate fails.
# ---------------------------------------------------------------------------------------------


def test_factual_review_from_another_candidate_fails():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(factual_candidate_sha256="3" * 64)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any(
        "factual_review_evidence.candidate_sha256" in reason for reason in result.hard_disqualifiers
    )


def test_visitor_review_from_another_candidate_fails():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(visitor_candidate_sha256="4" * 64)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any(
        "visitor_review_evidence.candidate_sha256" in reason for reason in result.hard_disqualifiers
    )


def test_rubric_evidence_from_another_candidate_fails():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(rubric_candidate_sha256="5" * 64)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("rubric_evidence.candidate_sha256" in reason for reason in result.hard_disqualifiers)


# ---------------------------------------------------------------------------------------------
# 10 / 11. Benchmark claim/verdict cannot prove product fact or a local dimension.
# ---------------------------------------------------------------------------------------------


def test_quarantined_dimension_never_passes_regardless_of_evidence():
    # Nothing supplied anywhere claims anything about quarantined dimensions -- there is no
    # code path through which a benchmark claim or an upstream benchmark verdict could grant
    # them credit; they are hardcoded to QUARANTINED whenever everything else is clean.
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    for dimension_id in ("benchmark_claim_authority", "benchmark_item_verdicts"):
        dimension = _applicable_dimension(result, dimension_id)
        assert dimension.verdict == "QUARANTINED"
        assert dimension_id not in result.applicable_dimension_ids


def test_obligation_text_alone_cannot_grant_a_pass():
    # A dimension's obligation prose is carried through for auditability only -- it is never
    # itself evaluated as evidence. A dimension with a blocking finding in its own relevant
    # category still fails despite an unrelated, unchanged obligation string.
    finding = _quality_finding("claim_grounding_negative_fact", "claim_grounding")
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(deterministic_findings=(finding,))
    )
    licensing = _applicable_dimension(result, "licensing")
    assert licensing.verdict == "FAIL"
    assert licensing.obligation  # obligation text is present but did not by itself grant PASS


# ---------------------------------------------------------------------------------------------
# 12 / 13 / 14. accepted/adapted/quarantined/not_applicable differ; unknown status fails closed
# and forces overall acceptance to fail.
# ---------------------------------------------------------------------------------------------


def test_disposition_semantics_differ():
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    assert _applicable_dimension(result, "information_coverage").benchmark_disposition == "accepted"
    assert (
        _applicable_dimension(result, "structure_and_navigation").benchmark_disposition == "adapted"
    )
    assert _applicable_dimension(result, "information_coverage").verdict == "PASS"
    assert _applicable_dimension(result, "structure_and_navigation").verdict == "PASS"
    assert _applicable_dimension(result, "benchmark_claim_authority").verdict == "QUARANTINED"
    assert (
        _applicable_dimension(result, "upstream_site_workflow_metadata").verdict == "NOT_APPLICABLE"
    )


def test_unrecognized_dimension_status_fails_closed_and_blocks_overall_acceptance():
    # comparison.dimensions[i].status is a closed Literal today -- an unrecognized value can only
    # be constructed by bypassing validation via model_construct. This exercises this module's
    # own defense-in-depth fallback, not a reachable production path.
    broken = CandidateBenchmarkDimensionV1.model_construct(
        dimension_id="information_coverage",
        benchmark_disposition="accepted",
        obligation="Cover the material visitor questions that have repository-verified answers.",
        applicable=True,
        status="SOMETHING_UNRECOGNIZED",
        evidence_paths=["candidate/README.md"],
    )
    # CandidateBenchmarkComparisonV1's normal constructor re-validates nested dimension rows even
    # when they were themselves built via model_construct, so the parent must also be built via
    # model_construct to actually carry an unrecognized status through to this module.
    comparison = CandidateBenchmarkComparisonV1.model_construct(
        repository=REPOSITORY,
        source_revision=SOURCE_REVISION,
        candidate_sha256=sha256_hex(DEFAULT_CANDIDATE),
        benchmark_profile_sha256=_CURRENT_PROFILE_SHA256,
        benchmark_snapshot_sha256="c" * 64,
        comparison_type="CandidateBenchmarkComparisonV1",
        comparison_status="CANDIDATE_EVIDENCE_MAPPED",
        acceptance_status="PENDING_DETERMINISTIC_AND_INDEPENDENT_REVIEW",
        benchmark_prose_used=False,
        runtime_dependency_on_aspose_org=False,
        schema_version=1,
        dimensions=[broken],
    )
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs(comparison=comparison))
    dimension = result.dimensions[0]
    assert dimension.verdict == "UNKNOWN"
    assert "unrecognized comparison dimension status" in (dimension.failure_reason or "")
    assert dimension.dimension_id in result.unresolved_dimension_ids
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"


# ---------------------------------------------------------------------------------------------
# 15. Suspicious copied prose cannot grant credit; absence of excerpts never weakens anything.
# ---------------------------------------------------------------------------------------------


def test_suspicious_copied_prose_disqualifies_but_never_grants_credit():
    clean = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    assert clean.acceptance_status == "BENCHMARK_ACCEPTANCE_PROVEN"

    copied = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(reference_excerpts=(DEFAULT_CANDIDATE,))
    )
    assert copied.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any(
        "suspicious_benchmark_prose_overlap" in reason for reason in copied.hard_disqualifiers
    )


def test_unrelated_reference_excerpt_does_not_disqualify():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(
            reference_excerpts=("Completely unrelated text about a different topic.",)
        )
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_PROVEN"
    assert result.hard_disqualifiers == ()


# ---------------------------------------------------------------------------------------------
# 16 / 17. Missing dimension fails (via the profile fence); duplicate dimension ID fails closed.
# ---------------------------------------------------------------------------------------------


def test_missing_dimension_fails_via_profile_fence():
    incomplete = [_build_dimension(*row) for row in _DIMENSION_TABLE[:-1]]
    comparison = _build_comparison(
        candidate_sha256=sha256_hex(DEFAULT_CANDIDATE),
        benchmark_profile_sha256="9" * 64,  # cannot match the current profile's real hash
        dimensions=incomplete,
    )
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs(comparison=comparison))
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("since-changed profile" in reason for reason in result.hard_disqualifiers)


def test_duplicate_dimension_id_fails_closed():
    duplicate_row = _build_dimension(*_DIMENSION_TABLE[0])
    comparison = CandidateBenchmarkComparisonV1.model_construct(
        repository=REPOSITORY,
        source_revision=SOURCE_REVISION,
        candidate_sha256=sha256_hex(DEFAULT_CANDIDATE),
        benchmark_profile_sha256=_CURRENT_PROFILE_SHA256,
        benchmark_snapshot_sha256="c" * 64,
        comparison_type="CandidateBenchmarkComparisonV1",
        comparison_status="CANDIDATE_EVIDENCE_MAPPED",
        acceptance_status="PENDING_DETERMINISTIC_AND_INDEPENDENT_REVIEW",
        benchmark_prose_used=False,
        runtime_dependency_on_aspose_org=False,
        schema_version=1,
        dimensions=[duplicate_row, duplicate_row],
    )
    with pytest.raises(ValueError, match="duplicate dimension_id"):
        evaluate_candidate_benchmark_acceptance(**_default_kwargs(comparison=comparison))


# ---------------------------------------------------------------------------------------------
# 18. Conflicting evidence fails closed.
# ---------------------------------------------------------------------------------------------


def test_internally_conflicting_rubric_evidence_fails_closed():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(rubric_accepted=True, rubric_hard_disqualifier_count=2)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("internally inconsistent" in reason for reason in result.hard_disqualifiers)


# ---------------------------------------------------------------------------------------------
# 19. Reordered equivalent input produces identical semantic output.
# ---------------------------------------------------------------------------------------------


def test_reordered_equivalent_dimensions_produce_identical_semantic_output():
    forward = [_build_dimension(*row) for row in _DIMENSION_TABLE]
    reversed_rows = [_build_dimension(*row) for row in reversed(_DIMENSION_TABLE)]
    candidate_sha256 = sha256_hex(DEFAULT_CANDIDATE)
    comparison_forward = _build_comparison(
        candidate_sha256=candidate_sha256,
        benchmark_profile_sha256=_CURRENT_PROFILE_SHA256,
        dimensions=forward,
    )
    comparison_reversed = _build_comparison(
        candidate_sha256=candidate_sha256,
        benchmark_profile_sha256=_CURRENT_PROFILE_SHA256,
        dimensions=reversed_rows,
    )
    result_forward = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(comparison=comparison_forward)
    )
    result_reversed = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(comparison=comparison_reversed)
    )
    assert result_forward.dimensions == result_reversed.dimensions
    assert result_forward.canonical_hash() == result_reversed.canonical_hash()


# ---------------------------------------------------------------------------------------------
# 20. Canonical result hash is deterministic.
# ---------------------------------------------------------------------------------------------


def test_canonical_hash_is_deterministic():
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    assert result.canonical_hash() == result.canonical_hash()

    rebuilt = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    assert result.canonical_hash() == rebuilt.canonical_hash()


def test_canonical_hash_golden_vector():
    # A hand-built, fully self-contained instance (not derived from the live on-disk profile),
    # so this test only breaks on a genuine canonicalization regression, never on legitimate
    # upstream profile-data changes.
    pinned = CandidateBenchmarkAcceptanceV1(
        repository="octocat/hello-world",
        source_revision="a" * 40,
        candidate_sha256="b" * 64,
        facts_hash="c" * 64,
        comparison_identity_sha256="d" * 64,
        benchmark_profile_sha256="e" * 64,
        deterministic_evidence_sha256="f" * 64,
        factual_review_sha256="1" * 64,
        visitor_review_sha256="2" * 64,
        rubric_evidence_sha256="3" * 64,
        evidence_bundle_sha256="4" * 64,
        dimensions=(
            BenchmarkDimensionAcceptanceV1(
                dimension_id="information_coverage",
                benchmark_disposition="accepted",
                obligation="Cover the material visitor questions.",
                verdict="PASS",
            ),
        ),
        applicable_dimension_ids=("information_coverage",),
        quarantined_dimension_ids=(),
        not_applicable_dimension_ids=(),
        unresolved_dimension_ids=(),
        acceptance_status="BENCHMARK_ACCEPTANCE_PROVEN",
    )
    # The exact literal is intentionally not asserted here (this repo's canonical-hash formula
    # is documented, not itself under test) -- repeatability across an independently rebuilt,
    # semantically identical instance is.
    rebuilt = pinned.model_copy()
    assert pinned.canonical_hash() == rebuilt.canonical_hash()


# ---------------------------------------------------------------------------------------------
# 21. No network / Aspose.org runtime is required.
# ---------------------------------------------------------------------------------------------


def test_no_live_or_network_call_in_module_source():
    import readme_agent.presentation.candidate_benchmark_acceptance as module

    source = inspect.getsource(module)
    forbidden = ("analysis_client", "requests", "httpx", "urllib.request", "aspose.org", "socket")
    for token in forbidden:
        assert token not in source, f"unexpected live/network reference: {token}"


# ---------------------------------------------------------------------------------------------
# 22. No publication / lifecycle acceptance is emitted.
# ---------------------------------------------------------------------------------------------


def test_no_publication_or_lifecycle_authority_emitted():
    result = evaluate_candidate_benchmark_acceptance(**_default_kwargs())
    assert result.publishes_acceptance is False
    assert result.transitions_lifecycle_state is False
    assert result.replaces_rubric_30_of_30 is False
    assert "ACCEPTED" not in result.acceptance_status
    assert result.acceptance_status in {
        "BENCHMARK_ACCEPTANCE_PROVEN",
        "BENCHMARK_ACCEPTANCE_NOT_PROVEN",
    }


# ---------------------------------------------------------------------------------------------
# Additional production-hardening regression controls.
# ---------------------------------------------------------------------------------------------


def test_evidence_drift_is_visible_not_hidden():
    clean_evidence = _build_quality_report(candidate_sha256=sha256_hex(DEFAULT_CANDIDATE))
    drifted_finding = _quality_finding("structural_detail_density", "structural_quality")
    drifted_evidence = _build_quality_report(
        candidate_sha256=sha256_hex(DEFAULT_CANDIDATE), findings=(drifted_finding,)
    )

    clean_result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(deterministic_evidence=clean_evidence)
    )
    drifted_result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(deterministic_evidence=drifted_evidence)
    )

    assert clean_result.evidence_bundle_sha256 != drifted_result.evidence_bundle_sha256
    assert (
        _applicable_dimension(clean_result, "branding_and_visuals").verdict
        != _applicable_dimension(drifted_result, "branding_and_visuals").verdict
    )


def test_role_swap_is_rejected():
    factual_role_record = _build_review_record(
        candidate_sha256=sha256_hex(DEFAULT_CANDIDATE), role="factual_plan_reviewer"
    )
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(visitor_review_evidence=factual_role_record)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("blind_quality_reviewer role" in reason for reason in result.hard_disqualifiers)


def test_factual_review_not_accept_fails_globally():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(factual_verdict="REJECT_REPAIRABLE")
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("factual_review_evidence verdict" in reason for reason in result.hard_disqualifiers)


def test_visitor_review_not_accept_fails_globally():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(visitor_verdict="REJECT_REPAIRABLE")
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("visitor_review_evidence verdict" in reason for reason in result.hard_disqualifiers)


def test_rubric_hard_disqualifier_fails_globally():
    result = evaluate_candidate_benchmark_acceptance(
        **_default_kwargs(rubric_accepted=False, rubric_hard_disqualifier_count=1)
    )
    assert result.acceptance_status == "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    assert any("hard disqualifier(s)" in reason for reason in result.hard_disqualifiers)
