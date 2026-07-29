"""Local README-POC review evidence preserves exact terminal semantics."""

import json

import pytest

from readme_agent.supervisor.local_poc_review_evidence import (
    write_local_poc_review_evidence,
)


def _seed_manifest(bundle_dir):
    bundle_dir.mkdir()
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lifecycle_status": "CANDIDATE_GENERATED",
                "complete": False,
                "completed_stages": ["CANDIDATE_GENERATED"],
            }
        ),
        encoding="utf-8",
    )


def test_blocked_fact_verdict_remains_distinct_from_repairable_rejection(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _seed_manifest(bundle_dir)

    write_local_poc_review_evidence(
        bundle_dir,
        deterministic_validation={"verdict": "accept"},
        independent_review={"verdict": "BLOCKED_FACT_CONFLICT"},
        repair_history=[],
        lifecycle_status="BLOCKED_FACT_CONFLICT",
        deterministic_validation_passed=True,
        reviewer_standard_hash="review-v1",
    )

    final = json.loads((bundle_dir / "review" / "final-verdict.json").read_text(encoding="utf-8"))
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert final == {
        "agent_approved": False,
        "deterministic_validation_passed": True,
        "repair_attempts": 0,
        "verdict": "BLOCKED_FACT_CONFLICT",
    }
    assert manifest["lifecycle_status"] == "BLOCKED_FACT_CONFLICT"
    assert manifest["complete"] is False


def test_review_evidence_rejects_unknown_lifecycle_status(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _seed_manifest(bundle_dir)

    with pytest.raises(ValueError, match="unsupported local README review lifecycle status"):
        write_local_poc_review_evidence(
            bundle_dir,
            deterministic_validation={"verdict": "accept"},
            independent_review={"verdict": "UNKNOWN"},
            repair_history=[],
            lifecycle_status="UNKNOWN",
            deterministic_validation_passed=True,
            reviewer_standard_hash="review-v1",
        )


def test_deterministic_repair_failure_is_not_recorded_as_agent_rejection(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _seed_manifest(bundle_dir)

    write_local_poc_review_evidence(
        bundle_dir,
        deterministic_validation={"verdict": "reject", "reason": "protected content lost"},
        independent_review={"verdict": "REJECT_REPAIRABLE"},
        repair_history=[{"repair_attempt": 1}],
        lifecycle_status="DETERMINISTIC_VALIDATION_FAILED",
        deterministic_validation_passed=False,
        reviewer_standard_hash="review-v1",
    )

    final = json.loads((bundle_dir / "review" / "final-verdict.json").read_text(encoding="utf-8"))
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert final["verdict"] == "DETERMINISTIC_VALIDATION_FAILED"
    assert final["deterministic_validation_passed"] is False
    assert manifest["lifecycle_status"] == "DETERMINISTIC_VALIDATION_FAILED"
    assert manifest["reviewer_standard_hash"] == "review-v1"
    assert "DETERMINISTIC_VALIDATION_FAILED" in manifest["completed_stages"]


def test_repair_attempt_count_includes_rerouted_receipt_without_rereview(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _seed_manifest(bundle_dir)

    write_local_poc_review_evidence(
        bundle_dir,
        deterministic_validation={"verdict": "accept"},
        independent_review={"verdict": "REJECT_REPAIRABLE"},
        repair_history=[
            {
                "repair_attempt": 0,
                "repair_receipt": {
                    "repair_attempt": 1,
                    "candidate_changed": False,
                    "rereview_authorized": False,
                },
            }
        ],
        lifecycle_status="README_ASSESSED",
        deterministic_validation_passed=True,
        reviewer_standard_hash="review-v1",
    )

    final = json.loads((bundle_dir / "review" / "final-verdict.json").read_text(encoding="utf-8"))
    assert final["repair_attempts"] == 1


def test_separated_role_records_are_materialized_individually(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _seed_manifest(bundle_dir)

    write_local_poc_review_evidence(
        bundle_dir,
        deterministic_validation={"verdict": "accept"},
        independent_review={"verdict": "ACCEPT"},
        blind_quality_review={"verdict": "ACCEPT", "input_sha256": "a" * 64},
        factual_plan_review={"verdict": "ACCEPT", "input_sha256": "b" * 64},
        combined_review={"verdict": "ACCEPT", "identity_separation_valid": True},
        repair_history=[],
        lifecycle_status="AGENT_APPROVED",
        deterministic_validation_passed=True,
        reviewer_standard_hash="separated-review-v1",
    )

    review_dir = bundle_dir / "review"
    assert json.loads((review_dir / "blind-quality-review.json").read_text())["verdict"] == "ACCEPT"
    assert (
        json.loads((review_dir / "factual-plan-review.json").read_text())["input_sha256"]
        == "b" * 64
    )
    assert json.loads((review_dir / "combined-review.json").read_text())[
        "identity_separation_valid"
    ]
