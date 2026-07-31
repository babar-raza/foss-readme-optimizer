"""Accepted stage receipts repair stale compatibility-manifest identities."""

import json

from readme_agent.evidence.writer import sha256_file, write_redacted_json, write_redacted_text
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.local_poc_manifest_recovery import (
    reconcile_approved_manifest_from_receipt,
)
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    StageArtifactV1,
    StageReceiptV1,
    canonical_sha256,
)

ORG_REPO = "org/repo"
SOURCE_REVISION = "a" * 40


def test_approved_manifest_recovers_only_from_matching_receipt_and_artifacts(tmp_path):
    bundle = tmp_path / SOURCE_REVISION
    candidate_path = bundle / "candidate" / "README.md"
    assessment_path = bundle / "assessment" / "current-readme-assessment.json"
    plan_path = bundle / "planning" / "presentation-plan.json"
    write_redacted_text(candidate_path, "# Product\n")
    assessment = ReadmeAssessmentV1.model_validate(
        {
            "org_repo": ORG_REPO,
            "immutable_base_revision": SOURCE_REVISION,
            "source_sha256": "b" * 64,
            "facts_hash": "c" * 64,
            "sections": [
                {
                    "section_id": "heading:0",
                    "heading": "Product",
                    "level": 1,
                    "source_byte_start": 0,
                    "source_byte_end": 10,
                    "disposition": "preserve",
                    "evidence": ["source README"],
                    "rationale": "Retain the verified heading.",
                }
            ],
        }
    )
    write_redacted_json(assessment_path, assessment)
    write_redacted_json(plan_path, {"operations": []})
    candidate_hash = sha256_file(candidate_path)[0]
    assessment_hash = assessment.canonical_hash()
    plan_hash = canonical_sha256({"operations": []})
    lifecycle = ReadmePocLifecycleStateV2(
        status="AGENT_APPROVED",
        source_revision=SOURCE_REVISION,
        facts_hash="c" * 64,
        assessment_hash=assessment_hash,
        presentation_plan_hash=plan_hash,
        candidate_hash=candidate_hash,
    )
    state = RunStateV2(org_repo=ORG_REPO, readme_poc_lifecycle=lifecycle)
    artifacts = [
        StageArtifactV1(
            path=path.relative_to(bundle).as_posix(),
            sha256=sha256_file(path)[0],
            size=path.stat().st_size,
        )
        for path in (assessment_path, candidate_path, plan_path)
    ]
    receipt = StageReceiptV1(
        campaign_id="d" * 64,
        work_id="e" * 64,
        target_stage="CANDIDATE_GENERATED",
        org_repo=ORG_REPO,
        source_revision=SOURCE_REVISION,
        fence_token="f" * 64,
        output_hash="1" * 64,
        result_sha256="2" * 64,
        artifact_inventory=artifacts,
    )
    write_redacted_json(bundle / "receipts" / "CANDIDATE_GENERATED.json", receipt)
    write_redacted_json(
        bundle / "manifest.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "lifecycle_status": "AGENT_APPROVED",
            "assessment_hash": "3" * 64,
            "presentation_plan_hash": "4" * 64,
            "candidate_hash": "5" * 64,
            "stage_receipts": {
                "CANDIDATE_GENERATED": {
                    "work_id": receipt.work_id,
                    "output_hash": receipt.output_hash,
                }
            },
        },
    )

    assert reconcile_approved_manifest_from_receipt(state, bundle) is True
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["assessment_hash"] == assessment_hash
    assert manifest["presentation_plan_hash"] == plan_hash
    assert manifest["candidate_hash"] == candidate_hash
    assert reconcile_approved_manifest_from_receipt(state, bundle) is False


def test_approved_manifest_recovery_refuses_artifact_drift(tmp_path):
    bundle = tmp_path / SOURCE_REVISION
    candidate_path = bundle / "candidate" / "README.md"
    write_redacted_text(candidate_path, "# Current\n")
    state = RunStateV2(
        org_repo=ORG_REPO,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="AGENT_APPROVED",
            source_revision=SOURCE_REVISION,
            facts_hash="c" * 64,
            assessment_hash="d" * 64,
            presentation_plan_hash="e" * 64,
            candidate_hash=sha256_file(candidate_path)[0],
        ),
    )
    write_redacted_json(
        bundle / "manifest.json",
        {
            "stage_receipts": {
                "CANDIDATE_GENERATED": {
                    "work_id": "1" * 64,
                    "output_hash": "2" * 64,
                }
            }
        },
    )

    assert reconcile_approved_manifest_from_receipt(state, bundle) is False
