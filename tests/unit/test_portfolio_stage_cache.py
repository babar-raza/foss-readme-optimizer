"""Tests for reusable stage-bounded portfolio product-truth bundles."""

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor import portfolio_stage_cache
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    StageArtifactV1,
    StageReceiptV1,
)
from readme_agent.supervisor.product_truth import PreparedProductTruthV1
from tests.unit.test_state_backend import FakeStateBackend


def _facts() -> ProductFactsV2:
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field),
            field=field,
            value=None,
            source=FactSourceV2(
                source_type="mechanical_repository",
                location="repository://acme/widget",
                source_revision="a" * 40,
            ),
            verification_state="missing",
            authoritative_owner="repository-owner",
            confidence=0.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo="acme/widget",
        facts=records,
        selected_fact_ids={record.field: record.fact_id for record in records},
    )


def test_completed_bounded_status_requires_current_checksum_valid_bundle(
    monkeypatch,
    tmp_path,
):
    facts = _facts()
    source_revision = "a" * 40
    backend = FakeStateBackend()
    backend.save(
        facts.org_repo,
        RunStateV2(
            org_repo=facts.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                org_repo=facts.org_repo,
                source_revision=source_revision,
                status="FACTS_READY",
                facts_hash=facts.canonical_hash(),
            ),
        ),
        None,
    )
    bundle_dir = tmp_path / source_revision
    write_redacted_json(bundle_dir / "facts" / "product-facts.json", facts)
    write_redacted_json(
        bundle_dir / "manifest.json",
        {
            "org_repo": facts.org_repo,
            "source_revision": source_revision,
            "lifecycle_status": "FACTS_READY",
            "facts_hash": facts.canonical_hash(),
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED", "FACTS_READY"],
        },
    )
    refresh_sha256sums(bundle_dir)
    monkeypatch.setattr(
        portfolio_stage_cache,
        "load_prepared_product_truth",
        lambda org_repo, state_backend, revision: PreparedProductTruthV1(
            facts=facts,
            findings=[],
            proposed_product_truth=None,
            resolution_source="durable_revision_cache",
            lifecycle_status="FACTS_READY",
            bundle_dir=str(bundle_dir),
        ),
    )

    assert (
        portfolio_stage_cache.completed_bounded_product_truth_status(
            backend,
            facts.org_repo,
            bundle_dir,
            "FACTS_READY",
        )
        == "FACTS_READY"
    )

    write_redacted_json(bundle_dir / "facts" / "product-facts.json", {"tampered": True})
    assert (
        portfolio_stage_cache.completed_bounded_product_truth_status(
            backend,
            facts.org_repo,
            bundle_dir,
            "FACTS_READY",
        )
        is None
    )


def test_candidate_stage_cache_requires_matching_reducer_receipt(monkeypatch, tmp_path):
    facts = _facts()
    source_revision = "a" * 40
    backend = FakeStateBackend()
    backend.save(
        facts.org_repo,
        RunStateV2(
            org_repo=facts.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                org_repo=facts.org_repo,
                source_revision=source_revision,
                status="CANDIDATE_GENERATED",
                facts_hash=facts.canonical_hash(),
                candidate_hash="b" * 64,
            ),
        ),
        None,
    )
    bundle_dir = tmp_path / source_revision
    receipt = StageReceiptV1(
        campaign_id="c" * 64,
        work_id="d" * 64,
        target_stage="CANDIDATE_GENERATED",
        org_repo=facts.org_repo,
        source_revision=source_revision,
        fence_token="e" * 64,
        output_hash="f" * 64,
        result_sha256="1" * 64,
        artifact_inventory=[StageArtifactV1(path="candidate/README.md", sha256="2" * 64, size=1)],
    )
    write_redacted_json(
        bundle_dir / "receipts" / "CANDIDATE_GENERATED.json",
        receipt,
    )
    write_redacted_json(
        bundle_dir / "manifest.json",
        {
            "org_repo": facts.org_repo,
            "source_revision": source_revision,
            "lifecycle_status": "CANDIDATE_GENERATED",
            "facts_hash": facts.canonical_hash(),
            "campaign_id": receipt.campaign_id,
            "complete": False,
            "completed_stages": ["FACTS_READY", "CANDIDATE_GENERATED"],
            "stage_receipts": {
                "CANDIDATE_GENERATED": {
                    "work_id": receipt.work_id,
                    "output_hash": receipt.output_hash,
                    "receipt_path": "receipts/CANDIDATE_GENERATED.json",
                }
            },
        },
    )
    refresh_sha256sums(bundle_dir)
    monkeypatch.setattr(
        portfolio_stage_cache,
        "load_prepared_product_truth",
        lambda org_repo, state_backend, revision: PreparedProductTruthV1(
            facts=facts,
            findings=[],
            proposed_product_truth=None,
            resolution_source="durable_revision_cache",
            lifecycle_status="CANDIDATE_GENERATED",
            bundle_dir=str(bundle_dir),
        ),
    )

    assert (
        portfolio_stage_cache.completed_bounded_product_truth_status(
            backend,
            facts.org_repo,
            bundle_dir,
            "CANDIDATE_GENERATED",
        )
        == "CANDIDATE_GENERATED"
    )

    manifest = bundle_dir / "manifest.json"
    changed = manifest.read_text(encoding="utf-8").replace(receipt.work_id, "9" * 64)
    manifest.write_text(changed, encoding="utf-8")
    refresh_sha256sums(bundle_dir)
    assert (
        portfolio_stage_cache.completed_bounded_product_truth_status(
            backend,
            facts.org_repo,
            bundle_dir,
            "CANDIDATE_GENERATED",
        )
        is None
    )
