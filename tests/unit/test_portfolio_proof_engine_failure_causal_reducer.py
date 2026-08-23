"""Tests for the fleet failure-causal reducer.

Covers the task's 22 mandated scenarios, plus 6 additional tests from a deeper production-hardening
pass (see WORKLOG.md / module_handoffs/fleet-causal-reducer/*/KNOWN_LIMITATIONS.md for why: real
owner-audit and PF-01 evidence surfaced gaps -- a missing `confidence` field, opaque high-volume
clusters that would otherwise over-merge, cross-pipeline weak-signal merges, and a false
"reproducible" claim already found in this codebase -- that the task's own decision table did not
originally defend against). Plus a small set of construction-validation tests for the security
properties named in the task's SECURITY AND HONESTY section.
"""

from __future__ import annotations

import pytest
from portfolio_proof_engine_fixtures import make_receipt
from pydantic import ValidationError

from readme_agent.supervisor.portfolio_proof_engine.failure_causal_reducer import (
    DependencyFingerprintSnapshotV1,
    FailureObservationV1,
    reduce_fleet_failures,
)


def _make_observation(
    *,
    org_repo: str = "acme/widget",
    stage: str = "CANDIDATE_ASSEMBLED",
    failure_reason: str | None = "boom",
    ecosystem: str | None = None,
    family: str | None = None,
    blocked_category: str | None = None,
    causal_component: str | None = None,
    structured_error_code: str | None = None,
    gate_or_check_id: str | None = None,
    structured_error_args: tuple[tuple[str, str], ...] = (),
    dependency_fingerprint: dict[str, object] | None = None,
    exception_type: str | None = None,
    evidence_ref: str | None = None,
    observed_at: str | None = None,
    last_observed_at: str | None = None,
    attempt_count: int = 1,
    pipeline_source: str | None = None,
    known_reproducibility_verdict: str | None = None,
    provider_call_count: int | None = 0,
    receipt_overrides: dict[str, object] | None = None,
) -> FailureObservationV1:
    receipt_kwargs: dict[str, object] = {
        "org_repo": org_repo,
        "stage": stage,
        "status": "FAILED",
        "failure_reason": failure_reason,
        "ecosystem": ecosystem,
        "provider_call_count": provider_call_count,
    }
    if receipt_overrides:
        receipt_kwargs.update(receipt_overrides)
    receipt = make_receipt(**receipt_kwargs)
    return FailureObservationV1(
        receipt=receipt,
        family=family,
        blocked_category=blocked_category,
        causal_component=causal_component,
        structured_error_code=structured_error_code,
        gate_or_check_id=gate_or_check_id,
        structured_error_args=structured_error_args,
        dependency_fingerprint=dependency_fingerprint,
        exception_type=exception_type,
        evidence_ref=evidence_ref,
        observed_at=observed_at,
        last_observed_at=last_observed_at,
        attempt_count=attempt_count,
        pipeline_source=pipeline_source,
        known_reproducibility_verdict=known_reproducibility_verdict,
    )


# --- 1. Same structured cause clusters across repositories -----------------------------------


def test_tier1_error_code_wins_over_ecosystem_args_pipeline_differences():
    obs1 = _make_observation(
        org_repo="acme/one",
        ecosystem="python",
        structured_error_code="render_failed",
        gate_or_check_id="render_failed",
        structured_error_args=(("a", "1"),),
        pipeline_source="zero_provider_qualification",
    )
    obs2 = _make_observation(
        org_repo="acme/two",
        ecosystem="rust",
        structured_error_code="render_failed",
        gate_or_check_id="render_failed",
        structured_error_args=(("b", "2"),),
        pipeline_source="commands_poc_delivery",
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.member_org_repos == ("acme/one", "acme/two")
    assert cluster.fingerprint.level == "error_gate_check_code"


# --- 2. Similar prose with different codes remains separate -----------------------------------


def test_similar_prose_different_codes_stay_separate():
    obs1 = _make_observation(
        org_repo="acme/one",
        structured_error_code="render_failed",
        failure_reason="Something went wrong during render",
    )
    obs2 = _make_observation(
        org_repo="acme/two",
        structured_error_code="validation_rejected",
        failure_reason="Something went wrong during render",
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 2


# --- 3. Same code at different stages remains separate -----------------------------------------


def test_same_code_different_stage_stays_separate():
    obs1 = _make_observation(
        org_repo="acme/one", stage="CANDIDATE_ASSEMBLED", structured_error_code="X"
    )
    obs2 = _make_observation(
        org_repo="acme/two", stage="DETERMINISTIC_VALIDATED", structured_error_code="X"
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 2


# --- 4. Volatile IDs/paths do not fragment one cause -------------------------------------------


def test_volatile_ids_paths_do_not_fragment_tier6_cluster():
    obs1 = _make_observation(
        org_repo="acme/one",
        failure_reason=(
            "failed at 2026-08-20T10:00:00Z run-abc12345 in /tmp/foo123/bar (attempt #1)"
        ),
    )
    obs2 = _make_observation(
        org_repo="acme/two",
        failure_reason=(
            "failed at 2026-08-21T11:30:05Z run-def67890fe in "
            "C:\\Users\\bob\\AppData\\Local\\Temp\\xyz (attempt #4)"
        ),
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 1
    assert result.clusters[0].member_count == 2
    normalized = result.clusters[0].fingerprint.normalized_diagnostic
    assert "2026-08" not in normalized
    assert "run-abc12345" not in normalized
    assert "attempt" not in normalized.lower() or "<ATTEMPT>" in normalized


# --- 5. Ecosystem adapter defect stays ecosystem-scoped -----------------------------------------


def test_ecosystem_adapter_defect_stays_scoped():
    obs1 = _make_observation(
        org_repo="acme/one", ecosystem="rust", structured_error_code="rust_toolchain_missing"
    )
    obs2 = _make_observation(
        org_repo="acme/two", ecosystem="rust", structured_error_code="rust_toolchain_missing"
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.classification == "ecosystem_adapter_defect"
    assert cluster.distinct_ecosystems == ("rust",)


# --- 6. Proven shared-code defect crosses ecosystems --------------------------------------------


def test_shared_code_defect_crosses_ecosystems():
    obs1 = _make_observation(org_repo="acme/one", ecosystem="python", structured_error_code="X")
    obs2 = _make_observation(org_repo="acme/two", ecosystem="go", structured_error_code="X")
    obs3 = _make_observation(org_repo="acme/three", ecosystem="java", structured_error_code="X")
    result = reduce_fleet_failures(observations=[obs1, obs2, obs3])
    assert len(result.clusters) == 1
    assert result.clusters[0].classification == "shared_code_defect"
    assert result.clusters[0].distinct_ecosystems == ("go", "java", "python")


# --- 7. Repository evidence defect stays repository-scoped --------------------------------------


def test_repository_evidence_defect_stays_repo_scoped():
    obs = _make_observation(
        org_repo="acme/one", stage="FACTS_READY", failure_reason="missing evidence xyz"
    )
    result = reduce_fleet_failures(observations=[obs])
    cluster = result.clusters[0]
    assert cluster.classification == "repository_evidence_defect"
    assert cluster.member_org_repos == ("acme/one",)


# --- 8. Candidate quality rejection remains distinct from factual conflict ----------------------


def test_candidate_rejection_distinct_from_factual_conflict():
    shared_text = "candidate specific presentation issue with duplicated section"
    candidate_obs = _make_observation(
        org_repo="acme/candidate", stage="RUBRIC_SCORED", failure_reason=shared_text
    )
    factual_obs = _make_observation(
        org_repo="acme/factual",
        stage="FACTS_READY",
        blocked_category="agent_fixable",
        failure_reason=shared_text,
    )
    result = reduce_fleet_failures(observations=[candidate_obs, factual_obs])
    assert len(result.clusters) == 2
    classifications = {c.classification for c in result.clusters}
    assert classifications == {"candidate_specific_rejection", "repository_evidence_defect"}


# --- 9. Transient provider differs from deterministic rejection ---------------------------------


def test_transient_provider_differs_from_deterministic_rejection():
    transient_obs = _make_observation(
        org_repo="acme/one",
        exception_type="readme_agent.errors.LLMInfrastructureError",
        dependency_fingerprint={"control_plane_fingerprint": "v2"},
    )
    deterministic_obs = _make_observation(
        org_repo="acme/two", structured_error_code="validation_rejected"
    )
    snapshot = DependencyFingerprintSnapshotV1(
        by_org_repo={"acme/one": {"control_plane_fingerprint": "v1"}}
    )
    result = reduce_fleet_failures(
        observations=[transient_obs, deterministic_obs], dependency_snapshot=snapshot
    )
    by_repo = {c.member_org_repos[0]: c.classification for c in result.clusters}
    assert by_repo["acme/one"] == "transient_provider"
    assert by_repo["acme/two"] == "input_contract_mismatch"


# --- 10. External unchanged dependency recommends no retry --------------------------------------


def test_infra_external_recommends_no_retry_when_dependency_unchanged():
    obs = _make_observation(org_repo="acme/one", blocked_category="infra_external")
    result = reduce_fleet_failures(observations=[obs])
    cluster = result.clusters[0]
    assert cluster.classification == "infra_external"
    assert cluster.dependency_changed is False
    assert cluster.recommended_repair_scope == "external_dependency_wait"


# --- 11. Changed dependency permits reevaluation -------------------------------------------------


def test_changed_dependency_permits_reevaluation():
    obs = _make_observation(
        org_repo="acme/one",
        blocked_category="infra_external",
        dependency_fingerprint={"reviewer_standard_hash": "new"},
    )
    snapshot = DependencyFingerprintSnapshotV1(
        by_org_repo={"acme/one": {"reviewer_standard_hash": "old"}}
    )
    result = reduce_fleet_failures(observations=[obs], dependency_snapshot=snapshot)
    cluster = result.clusters[0]
    assert cluster.classification == "transient_provider"
    assert cluster.dependency_changed is True

    obs1 = _make_observation(org_repo="acme/three", dependency_fingerprint={"template_hash": "new"})
    obs2 = _make_observation(org_repo="acme/four", dependency_fingerprint={"template_hash": "new"})
    only_dep_snapshot = DependencyFingerprintSnapshotV1(
        global_dependencies={"template_hash": "old"}
    )
    result2 = reduce_fleet_failures(
        observations=[obs1, obs2], dependency_snapshot=only_dep_snapshot
    )
    assert len(result2.clusters) == 1
    assert result2.clusters[0].fingerprint.level == "dependency_fingerprint"


# --- 12. Corrupt evidence fails closed -----------------------------------------------------------


def test_corrupt_evidence_fails_closed():
    obs1 = _make_observation(org_repo="acme/one", observed_at="not-a-real-timestamp")
    obs2 = _make_observation(org_repo="acme/two", dependency_fingerprint={})
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.classification == "corrupt_or_stale_evidence"
    assert cluster.member_org_repos == ("acme/one", "acme/two")


# --- 13. Unknown remains possible -----------------------------------------------------------------


def test_unknown_remains_possible():
    obs = _make_observation(
        org_repo="acme/one", stage="SYSTEM_FAILURE", failure_reason="totally unexplained crash"
    )
    result = reduce_fleet_failures(observations=[obs])
    assert result.clusters[0].classification == "unknown"


# --- 14. Secrets are redacted


def test_secrets_are_redacted_in_normalized_diagnostic():
    obs1 = _make_observation(
        org_repo="acme/one", failure_reason="auth failed with token sk-abcdefghij1234567890"
    )
    result = reduce_fleet_failures(observations=[obs1])
    normalized = result.clusters[0].fingerprint.normalized_diagnostic
    assert "sk-abcdefghij1234567890" not in normalized
    assert "[REDACTED]" in normalized


# --- 15. Duplicate observations preserve attempt accounting


def test_duplicate_observations_preserve_attempt_accounting():
    obs = _make_observation(org_repo="acme/one", structured_error_code="X", attempt_count=1)
    dup = _make_observation(org_repo="acme/one", structured_error_code="X", attempt_count=2)
    result = reduce_fleet_failures(observations=[obs, dup])
    assert result.input_observation_count == 1
    merged = result.clusters[0].representative.observation
    assert merged.attempt_count == 3


# --- 16. Input ordering does not affect output/hash


def test_input_ordering_does_not_affect_output():
    obs1 = _make_observation(org_repo="acme/one", structured_error_code="X", ecosystem="python")
    obs2 = _make_observation(org_repo="acme/two", structured_error_code="Y", ecosystem="rust")
    obs3 = _make_observation(
        org_repo="acme/three", stage="FACTS_READY", failure_reason="evidence gap"
    )
    result_a = reduce_fleet_failures(observations=[obs1, obs2, obs3])
    result_b = reduce_fleet_failures(observations=[obs3, obs2, obs1])
    assert result_a.model_dump(exclude={"generated_at"}) == result_b.model_dump(
        exclude={"generated_at"}
    )


# --- 17. One failure is never lost


def test_one_failure_never_lost():
    observations = [
        _make_observation(org_repo=f"acme/repo{i}", failure_reason=f"unique issue {i}")
        for i in range(5)
    ]
    result = reduce_fleet_failures(observations=observations)
    covered = {repo for cluster in result.clusters for repo in cluster.member_org_repos}
    assert covered == {f"acme/repo{i}" for i in range(5)}
    assert result.unresolved_org_repos == ()


# --- 18. Minimal cohort is stable


def test_minimal_cohort_stable_independent_of_order():
    obs1 = _make_observation(
        org_repo="acme/one", structured_error_code="X", ecosystem="python", evidence_ref="e1.json"
    )
    obs2 = _make_observation(org_repo="acme/two", structured_error_code="X", ecosystem="rust")
    result_a = reduce_fleet_failures(observations=[obs1, obs2])
    result_b = reduce_fleet_failures(observations=[obs2, obs1])
    cohort_a = [(r.org_repo, r.selection_reason) for r in result_a.minimal_proof_cohort]
    cohort_b = [(r.org_repo, r.selection_reason) for r in result_b.minimal_proof_cohort]
    assert cohort_a == cohort_b


# --- 19. Avoided-retry arithmetic is correct


def test_avoided_retry_arithmetic_is_correct():
    observations = [
        _make_observation(org_repo=f"acme/repo{i}", structured_error_code="X") for i in range(4)
    ]
    result = reduce_fleet_failures(observations=observations)
    cluster = result.clusters[0]
    assert cluster.member_count == 4
    assert cluster.estimated_retries_avoided == 3
    assert result.total_estimated_retries_avoided == 3


# --- 20. A PF-01-like mixed fleet reduces meaningfully


def test_pf01_like_fixture_reduces_to_meaningful_clusters():
    """Modeled on real qualification.status_counts from this repo's own PF-01 evidence
    (plans/investigations/evidence/portfolio-proof-knowledge-acceptance-20260821/qualification-
    summary.json): 7 plan_unavailable, 12 render_failed, 10 validation_rejected == 29 failures.
    Group D is deliberately built genuinely opaque (no structured field at all, one shared generic
    message) because that is what the real validation_rejected bucket looks like
    (blocking_finding_count: 0 despite document_valid: false) -- a naive reducer would either
    over-merge it with false confidence or under-merge it into 10 unrelated tasks; this reducer
    must instead recognize it as one honestly-`unknown` cluster."""

    observations = []

    ecosystems_a = ["python", "python", "rust", "rust", "go", "go", "java"]
    for i, eco in enumerate(ecosystems_a):
        observations.append(
            _make_observation(
                org_repo=f"aspose/group-a-{i}",
                stage="SECTION_PACKETS_READY",
                gate_or_check_id="plan_unavailable",
                ecosystem=eco,
                failure_reason="zero-provider plan blocked by: draft_invalid",
            )
        )

    ecosystems_b = ["python", "python", "python", "go", "go", "go", "java", "java"]
    for i, eco in enumerate(ecosystems_b):
        observations.append(
            _make_observation(
                org_repo=f"aspose/group-b-{i}",
                stage="CANDIDATE_ASSEMBLED",
                structured_error_code="template_render_timeout",
                ecosystem=eco,
                failure_reason="ValueError: compiled verified presentation is invalid",
            )
        )

    for i in range(4):
        observations.append(
            _make_observation(
                org_repo=f"aspose/group-c-{i}",
                stage="CANDIDATE_ASSEMBLED",
                structured_error_code="rust_toolchain_missing",
                ecosystem="rust",
                failure_reason="cargo: toolchain not found",
            )
        )

    for i in range(10):
        observations.append(
            _make_observation(
                org_repo=f"aspose/group-d-{i}",
                stage="DETERMINISTIC_VALIDATED",
                failure_reason="native deterministic candidate failed one or more blocking checks",
            )
        )

    result = reduce_fleet_failures(observations=observations)

    assert result.input_observation_count == 29
    assert result.unresolved_org_repos == ()
    assert len(result.clusters) == 4

    classifications = [c.classification for c in result.clusters]
    assert classifications.count("shared_code_defect") == 2
    assert classifications.count("ecosystem_adapter_defect") == 1
    assert classifications.count("unknown") == 1

    member_counts: dict[str, list[int]] = {}
    for cluster in result.clusters:
        member_counts.setdefault(cluster.classification, []).append(cluster.member_count)
    assert sorted(member_counts["shared_code_defect"]) == [7, 8]
    assert member_counts["ecosystem_adapter_defect"] == [4]
    assert member_counts["unknown"] == [10]

    unknown_cluster = next(c for c in result.clusters if c.classification == "unknown")
    assert unknown_cluster.confidence == "low"
    assert "unstructured" in unknown_cluster.classification_reason

    assert len(result.minimal_proof_cohort) < 29
    opaque_repos = {f"aspose/group-d-{i}" for i in range(10)}
    cohort_repos = {r.org_repo for r in result.minimal_proof_cohort}
    assert opaque_repos.issubset(cohort_repos)


# --- 21. A PF-03-like sequence distinguishes four categories


def test_pf03_like_fixture_distinguishes_four_categories():
    """ILLUSTRATIVE / SYNTHETIC ONLY. PF-03 (`L8-PF-03-SEALED-CANDIDATE-NO-OP`,
    plans/investigations/control/level8-autonomous-mission-task-graph.yaml) is a real task ID
    scoped to exactly one repository (aspose-3d-foss/Aspose.3D-FOSS-for-Python), currently `TODO`
    with no evidence directory yet. The four category names in this test's title come from the
    module's own task brief, not from any observed PF-03 failure -- a hypothesis linking them to
    the concurrent `fix(review):` bounded-review-packet commit cluster could not be confirmed by
    any documented source during this module's research phase. This fixture is grounded in real
    code shapes instead (bounded-review packet language, `verifier_client.py`'s 401 handling, the
    real `readme_review_reducer` module) but must never be read as a replay of real PF-03 evidence.
    """

    observations = [
        _make_observation(
            org_repo="aspose/pf03-packet-repo",
            stage="SECTIONS_AUTHORED",
            failure_reason=(
                "bounded-review packet has no grounded findings for its own accepted facts -- "
                "orphan packet evidence"
            ),
        ),
        _make_observation(
            org_repo="aspose/pf03-auth-repo",
            exception_type="readme_agent.errors.LLMInfrastructureError",
            blocked_category="infra_external",
            dependency_fingerprint={"control_plane_fingerprint": "v2"},
            failure_reason="401 Unauthorized calling the LLM gateway",
        ),
        _make_observation(
            org_repo="aspose/pf03-reducer-repo-a",
            stage="VISITOR_REVIEWED",
            ecosystem="python",
            causal_component="readme_review_reducer",
            failure_reason="compatibility result reducer dropped a bounded_review_receipt field",
        ),
        _make_observation(
            org_repo="aspose/pf03-reducer-repo-b",
            stage="VISITOR_REVIEWED",
            ecosystem="go",
            causal_component="readme_review_reducer",
            failure_reason="compatibility result reducer dropped a bounded_review_receipt field",
        ),
    ]
    for i in range(4):
        observations.append(
            _make_observation(
                org_repo=f"aspose/pf03-presentation-repo-{i}",
                stage="RUBRIC_SCORED",
                failure_reason=(
                    f"candidate {i} repeats its capability list without new visitor value "
                    f"in section {i}"
                ),
            )
        )

    snapshot = DependencyFingerprintSnapshotV1(
        by_org_repo={"aspose/pf03-auth-repo": {"control_plane_fingerprint": "v1"}}
    )
    result = reduce_fleet_failures(observations=observations, dependency_snapshot=snapshot)

    assert result.unresolved_org_repos == ()
    assert result.input_observation_count == 8
    assert len(result.clusters) == 7

    classifications = [c.classification for c in result.clusters]
    assert classifications.count("repository_evidence_defect") == 1
    assert classifications.count("transient_provider") == 1
    assert classifications.count("shared_code_defect") == 1
    assert classifications.count("candidate_specific_rejection") == 4

    reducer_cluster = next(c for c in result.clusters if c.classification == "shared_code_defect")
    assert set(reducer_cluster.member_org_repos) == {
        "aspose/pf03-reducer-repo-a",
        "aspose/pf03-reducer-repo-b",
    }
    assert reducer_cluster.fingerprint.level == "stage_causal_component"

    presentation_clusters = [
        c for c in result.clusters if c.classification == "candidate_specific_rejection"
    ]
    assert all(c.member_count == 1 for c in presentation_clusters)
    presentation_repos = {c.member_org_repos[0] for c in presentation_clusters}
    assert presentation_repos == {f"aspose/pf03-presentation-repo-{i}" for i in range(4)}


# --- 22. No state write, retry or repair occurs


def test_no_state_write_or_io_occurs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    obs = _make_observation(org_repo="acme/one", structured_error_code="X")
    reduce_fleet_failures(observations=[obs])
    assert list(tmp_path.iterdir()) == []


# --- 23-28: deeper-pass production-hardening tests


def test_confidence_is_tier_derived():
    tier1 = reduce_fleet_failures(
        observations=[_make_observation(org_repo="acme/one", structured_error_code="X")]
    )
    tier4 = reduce_fleet_failures(
        observations=[_make_observation(org_repo="acme/two", exception_type="SomeError")]
    )
    tier6 = reduce_fleet_failures(
        observations=[
            _make_observation(org_repo="acme/three", failure_reason="unique unstructured text")
        ]
    )
    assert tier1.clusters[0].confidence == "high"
    assert tier4.clusters[0].confidence == "medium"
    assert tier6.clusters[0].confidence == "low"


def test_opaque_bulk_cluster_forces_unknown_low_confidence():
    observations = [
        _make_observation(
            org_repo=f"acme/repo{i}",
            failure_reason="native deterministic candidate failed one or more blocking checks",
        )
        for i in range(6)
    ]
    result = reduce_fleet_failures(observations=observations)
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.classification == "unknown"
    assert cluster.confidence == "low"
    assert cluster.recommended_repair_scope == "manual_classification_required"
    assert len(result.minimal_proof_cohort) == 6


def test_small_opaque_cluster_gets_best_effort_classification():
    small = [
        _make_observation(
            org_repo=f"acme/repo{i}", stage="FACTS_READY", failure_reason="missing evidence bundle"
        )
        for i in range(3)
    ]
    small_result = reduce_fleet_failures(observations=small)
    assert small_result.clusters[0].classification == "repository_evidence_defect"
    assert small_result.clusters[0].member_count == 3

    bulk = [
        _make_observation(
            org_repo=f"acme/bulk{i}", stage="FACTS_READY", failure_reason="missing evidence bundle"
        )
        for i in range(5)
    ]
    bulk_result = reduce_fleet_failures(observations=bulk)
    assert bulk_result.clusters[0].classification == "unknown"


def test_pipeline_source_prevents_weak_tier_cross_pipeline_merge():
    obs1 = _make_observation(
        org_repo="acme/one",
        exception_type="SomeError",
        pipeline_source="zero_provider_qualification",
    )
    obs2 = _make_observation(
        org_repo="acme/two", exception_type="SomeError", pipeline_source="commands_poc_delivery"
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    assert len(result.clusters) == 2

    obs3 = _make_observation(
        org_repo="acme/three",
        structured_error_code="X",
        pipeline_source="zero_provider_qualification",
    )
    obs4 = _make_observation(
        org_repo="acme/four", structured_error_code="X", pipeline_source="commands_poc_delivery"
    )
    result2 = reduce_fleet_failures(observations=[obs3, obs4])
    assert len(result2.clusters) == 1


def test_known_reproducibility_verdict_affects_representative_not_fingerprint():
    obs1 = _make_observation(org_repo="acme/one", structured_error_code="X", evidence_ref="e1.json")
    obs2 = _make_observation(
        org_repo="acme/two",
        structured_error_code="X",
        evidence_ref="e2.json",
        known_reproducibility_verdict="NO_OP_PROVEN",
    )
    result = reduce_fleet_failures(observations=[obs1, obs2])
    cluster = result.clusters[0]
    assert cluster.representative.org_repo == "acme/two"

    without_verdict = reduce_fleet_failures(
        observations=[
            _make_observation(
                org_repo="acme/one", structured_error_code="X", evidence_ref="e1.json"
            ),
            _make_observation(
                org_repo="acme/two", structured_error_code="X", evidence_ref="e2.json"
            ),
        ]
    )
    assert (
        without_verdict.clusters[0].fingerprint.fingerprint_hash
        == cluster.fingerprint.fingerprint_hash
    )


def test_required_closure_evidence_demands_zero_call_replay():
    obs1 = _make_observation(org_repo="acme/one", structured_error_code="X")
    result = reduce_fleet_failures(observations=[obs1])
    text = result.clusters[0].required_closure_evidence
    assert "NO_OP_PROVEN" in text
    assert "TRANSACTION_NO_OP_PROVEN" in text


# --- construction-validation / security properties


def test_non_failed_receipt_rejected_at_construction():
    with pytest.raises(ValidationError):
        FailureObservationV1(receipt=make_receipt(org_repo="acme/one", stage="INTAKE", status="OK"))


def test_evidence_ref_path_traversal_rejected_at_construction():
    with pytest.raises(ValidationError):
        _make_observation(org_repo="acme/one", evidence_ref="../../etc/passwd")


def test_evidence_ref_absolute_path_rejected_at_construction():
    with pytest.raises(ValidationError):
        _make_observation(org_repo="acme/one", evidence_ref="/etc/passwd")
    with pytest.raises(ValidationError):
        _make_observation(org_repo="acme/one", evidence_ref="C:/secrets/token.json")


def test_structured_error_args_must_be_sorted_and_unique():
    with pytest.raises(ValidationError):
        _make_observation(org_repo="acme/one", structured_error_args=(("b", "1"), ("a", "2")))
    with pytest.raises(ValidationError):
        _make_observation(org_repo="acme/one", structured_error_args=(("a", "1"), ("a", "2")))
