"""Revision-addressed snapshot evidence for the canonical local POC."""

import hashlib
import json
from pathlib import Path

from readme_agent import paths
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1
from readme_agent.supervisor.local_poc_evidence import (
    mark_local_poc_profiled,
    write_local_poc_product_facts,
    write_local_poc_readme_candidate,
    write_local_poc_snapshot,
)


def _snapshot(tmp_path: Path, *, readme: bool = True) -> RepositorySnapshotV1:
    if readme:
        (tmp_path / "README.md").write_text("# Product\n", encoding="utf-8")
    return RepositorySnapshotV1(
        org_repo="acme/product",
        source_revision="a" * 40,
        snapshot_root=str(tmp_path),
        readme_path="README.md" if readme else None,
        readme_sha256="b" * 64 if readme else None,
        inventory_sha256="c" * 64,
        captured_at="2026-07-25T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/product.git", git_tree_sha256="c" * 64
        ),
    )


def test_snapshot_bundle_is_revision_addressed_idempotent_and_checksum_complete(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)

    bundle = write_local_poc_snapshot(snapshot)
    second = write_local_poc_snapshot(snapshot)

    assert bundle == second
    assert (bundle / "source" / "README.md").read_text(encoding="utf-8") == "# Product\n"
    assert (bundle / "source" / "revision.json").is_file()
    assert (bundle / "manifest.json").is_file()
    assert (bundle / "sha256sums.txt").is_file()
    assert '"complete": false' in (bundle / "manifest.json").read_text(encoding="utf-8")


def test_missing_readme_is_explicit_evidence_not_a_fake_empty_readme(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")

    bundle = write_local_poc_snapshot(_snapshot(tmp_path, readme=False))

    assert (bundle / "source" / "readme-absence.json").is_file()
    assert not (bundle / "source" / "README.md").exists()


def test_profile_boundary_updates_manifest_without_claiming_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = write_local_poc_snapshot(snapshot)

    mark_local_poc_profiled(snapshot, bundle)

    manifest = (bundle / "manifest.json").read_text(encoding="utf-8")
    assert '"lifecycle_status": "PROFILED"' in manifest
    assert '"complete": false' in manifest
    assert '"SNAPSHOTTED"' in manifest
    assert '"PROFILED"' in manifest


def test_product_facts_boundary_writes_provenance_conflicts_and_acquisition(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://acme/product",
        source_revision=snapshot.source_revision,
    )
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "local-evidence-test"),
            field=field,
            value={"field": field},
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    facts = ProductFactsV2(
        org_repo=snapshot.org_repo,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )

    bundle = write_local_poc_product_facts(
        snapshot,
        facts,
        findings=[],
        resolution_source="repository_and_policy",
        local_verification_contract_hash="v" * 64,
        fact_acceptance_contract_hash="a" * 64,
        fact_acceptance_component_hashes={"evidence_polarity": "b" * 64},
    )

    assert (bundle / "facts" / "product-facts.json").is_file()
    assert (bundle / "facts" / "provenance.json").is_file()
    assert (bundle / "facts" / "conflicts.json").is_file()
    assert (bundle / "facts" / "acquisition.json").is_file()
    checksum_inventory = (bundle / "sha256sums.txt").read_text(encoding="utf-8")
    assert "facts/product-facts.json" in checksum_inventory
    assert "facts/provenance.json" in checksum_inventory
    assert "source/revision.json" not in checksum_inventory  # this unit starts at the facts stage
    manifest = (bundle / "manifest.json").read_text(encoding="utf-8")
    assert '"lifecycle_status": "FACTS_READY"' in manifest
    assert facts.canonical_hash() in manifest
    assert '"local_verification_contract_hash": "' + ("v" * 64) + '"' in manifest


def test_candidate_boundary_writes_assessment_plan_patch_claim_map_and_hashes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://acme/product",
        source_revision=snapshot.source_revision,
    )
    values = {
        "product.identity": {"name": "Product", "ecosystem": "java"},
        "product.audience": ["Java developers"],
        "product.problems_solved": ["Read product files"],
        "product.capabilities": ["Read files"],
        "product.formats": ["Product files"],
        "product.compatibility": {"minimum_runtime": "Java 11"},
        "product.limitations": ["Read-only fixture"],
        "example.minimal": {
            "language": "java",
            "code": "public class Example {}",
        },
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "candidate-evidence-test"),
            field=field,
            value=values.get(field, {"field": field}),
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    facts = ProductFactsV2(
        org_repo=snapshot.org_repo,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )
    write_local_poc_product_facts(
        snapshot,
        facts,
        findings=[],
        resolution_source="repository_and_policy",
        local_verification_contract_hash="v" * 64,
        fact_acceptance_contract_hash="a" * 64,
        fact_acceptance_component_hashes={"evidence_polarity": "b" * 64},
    )
    source_text = (tmp_path / "README.md").read_text(encoding="utf-8")
    candidate, document_plan = build_readme_document_candidate(
        snapshot.org_repo,
        source_text,
        facts,
        base_revision=snapshot.source_revision,
    )
    assessment = assess_readme_document(
        snapshot.org_repo,
        source_text,
        facts,
        base_revision=snapshot.source_revision,
    )
    claim_map = build_readme_claim_map(
        document_plan,
        facts,
        source_text=source_text,
        candidate_text=candidate,
    )

    bundle, assessment_hash, plan_hash, candidate_hash = write_local_poc_readme_candidate(
        snapshot,
        {
            "source_revision": snapshot.source_revision,
            "final_text": candidate,
        },
        {
            "readme_assessment": assessment.model_dump(mode="json"),
            "readme_document_plan": document_plan.model_dump(mode="json"),
            "claim_map": claim_map.model_dump(mode="json"),
            "presentation_plan": {"repository": snapshot.org_repo},
            "git_patch_proof": {"patch": "fixture patch\n"},
            "executable": True,
        },
    )

    assert assessment_hash == assessment.canonical_hash()
    expected_presentation_plan_hash = hashlib.sha256(
        json.dumps(
            {"repository": snapshot.org_repo},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert plan_hash == expected_presentation_plan_hash
    assert candidate_hash == document_plan.candidate_sha256
    assert (bundle / "assessment" / "current-readme-assessment.json").is_file()
    evidence_map = json.loads(
        (bundle / "assessment" / "evidence-map.json").read_text(encoding="utf-8")
    )
    assert evidence_map["material_claims"] == [
        claim.model_dump(mode="json") for claim in assessment.material_claims
    ]
    assert (bundle / "planning" / "readme-document-plan.json").is_file()
    assert (bundle / "planning" / "agentic-composition-plan.json").is_file()
    assert (bundle / "candidate" / "README.md").read_text(encoding="utf-8") == candidate
    assert (bundle / "candidate" / "README.patch").read_text(encoding="utf-8") == (
        "fixture patch\n"
    )
    assert (bundle / "candidate" / "claim-map.json").is_file()
    manifest = (bundle / "manifest.json").read_text(encoding="utf-8")
    assert '"lifecycle_status": "CANDIDATE_GENERATED"' in manifest
    assert '"local_verification_contract_hash": "' + ("v" * 64) + '"' in manifest
    checksum_inventory = (bundle / "sha256sums.txt").read_text(encoding="utf-8")
    assert "assessment/current-readme-assessment.json" in checksum_inventory
    assert "candidate/README.md" in checksum_inventory

    write_local_poc_product_facts(
        snapshot,
        facts,
        findings=[],
        resolution_source="repository_and_policy",
        local_verification_contract_hash="w" * 64,
        fact_acceptance_contract_hash="a" * 64,
        fact_acceptance_component_hashes={"evidence_polarity": "b" * 64},
    )
    invalidated_manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert invalidated_manifest["lifecycle_status"] == "FACTS_READY"
    assert invalidated_manifest["local_verification_contract_hash"] == "w" * 64
    assert "candidate_hash" not in invalidated_manifest
