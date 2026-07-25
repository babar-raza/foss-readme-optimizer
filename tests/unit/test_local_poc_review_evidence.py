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
    )

    final = json.loads((bundle_dir / "review" / "final-verdict.json").read_text(encoding="utf-8"))
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert final["verdict"] == "DETERMINISTIC_VALIDATION_FAILED"
    assert final["deterministic_validation_passed"] is False
    assert manifest["lifecycle_status"] == "DETERMINISTIC_VALIDATION_FAILED"
    assert "DETERMINISTIC_VALIDATION_FAILED" in manifest["completed_stages"]
