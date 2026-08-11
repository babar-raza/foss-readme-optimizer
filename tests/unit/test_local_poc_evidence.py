"""Revision-addressed snapshot evidence for the canonical local POC."""

import hashlib
import json
from pathlib import Path

import pytest

from readme_agent import paths
from readme_agent.errors import RepositorySnapshotError
from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums
from readme_agent.facts.root_role_schema import (
    PackageRootRoleInventoryV1,
    PackageRootRoleV1,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.llm import prompt_registry
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1
from readme_agent.supervisor import local_poc_evidence, local_poc_snapshot_evidence
from readme_agent.supervisor.local_poc_evidence import (
    mark_local_poc_profiled,
    write_local_poc_product_facts,
    write_local_poc_readme_candidate,
    write_local_poc_snapshot,
)
from readme_agent.supervisor.presentation_component_versions import SelectedDependencyV1
from readme_agent.supervisor.stage_dependencies import (
    build_stage_dependency_manifest,
    current_candidate_stage_dependency_manifest,
)


def test_private_stage_manifest_omits_retry_local_runtime_accounting(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setattr(
        local_poc_snapshot_evidence,
        "local_bundle_llm_accounting_fields",
        lambda _bundle, _prior: {
            "llm_accounting_status": "EXACT",
            "llm_call_count": 1,
            "llm_call_ids": ["retry-local-call"],
        },
    )
    private = tmp_path / "private"
    local_poc_snapshot_evidence.write_local_poc_manifest(
        private,
        {"schema_version": 1, "source_revision": "a" * 40},
        include_runtime_accounting=False,
    )
    private_manifest = json.loads((private / "manifest.json").read_text(encoding="utf-8"))
    assert "llm_accounting_status" not in private_manifest
    assert "llm_call_count" not in private_manifest
    assert "llm_call_ids" not in private_manifest

    compatibility = tmp_path / "compatibility"
    local_poc_snapshot_evidence.write_local_poc_manifest(
        compatibility,
        {"schema_version": 1, "source_revision": "a" * 40},
    )
    compatibility_manifest = json.loads(
        (compatibility / "manifest.json").read_text(encoding="utf-8")
    )
    assert compatibility_manifest["llm_call_ids"] == ["retry-local-call"]


def _snapshot(
    tmp_path: Path,
    *,
    readme: bool = True,
    captured_at: str = "2026-07-25T00:00:00+00:00",
) -> RepositorySnapshotV1:
    if readme:
        (tmp_path / "README.md").write_text("# Product\n", encoding="utf-8")
    readme_sha256 = (
        hashlib.sha256((tmp_path / "README.md").read_bytes()).hexdigest() if readme else None
    )
    return RepositorySnapshotV1(
        org_repo="acme/product",
        source_revision="a" * 40,
        snapshot_root=str(tmp_path),
        readme_path="README.md" if readme else None,
        readme_sha256=readme_sha256,
        inventory_sha256="c" * 64,
        captured_at=captured_at,
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
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["complete"] is False
    assert manifest["prompt_hashes_by_id"] == prompt_registry.prompt_hashes()
    assert manifest["prompt_dependency_hashes"]["FACTS_COLLECTING"]
    assert verify_sha256sums(bundle)


def test_snapshot_seals_checksum_valid_intake_bundle_created_for_new_revision(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = paths.readme_poc_repository_dir("acme", "product", snapshot.source_revision)
    intake_receipt = bundle / "intake" / "preflight.json"
    intake_receipt.parent.mkdir(parents=True)
    intake_receipt.write_text('{"outcome":"READY_FAST_PATH"}\n', encoding="utf-8")
    refresh_sha256sums(bundle)

    result = write_local_poc_snapshot(snapshot)

    assert result == bundle
    assert json.loads(intake_receipt.read_text(encoding="utf-8")) == {"outcome": "READY_FAST_PATH"}
    assert (bundle / "source" / "revision.json").is_file()
    assert (bundle / "manifest.json").is_file()
    assert verify_sha256sums(bundle)


def test_snapshot_rejects_unsealed_revision_directory_outside_intake_namespace(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = paths.readme_poc_repository_dir("acme", "product", snapshot.source_revision)
    unexpected = bundle / "candidate" / "README.md"
    unexpected.parent.mkdir(parents=True)
    unexpected.write_text("# Unsealed candidate\n", encoding="utf-8")
    refresh_sha256sums(bundle)

    with pytest.raises(RepositorySnapshotError, match="intake-only"):
        write_local_poc_snapshot(snapshot)

    assert unexpected.read_text(encoding="utf-8") == "# Unsealed candidate\n"
    assert not (bundle / "source").exists()


def test_same_revision_recapture_preserves_every_bundle_byte_and_mtime(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    first_root = tmp_path / "first-capture"
    second_root = tmp_path / "second-capture"
    first_root.mkdir()
    second_root.mkdir()
    first = _snapshot(first_root)
    bundle = write_local_poc_snapshot(first)
    before = {
        path.relative_to(bundle).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in bundle.rglob("*")
        if path.is_file()
    }

    second = _snapshot(
        second_root,
        captured_at="2026-07-26T12:34:56+00:00",
    )
    assert write_local_poc_snapshot(second) == bundle
    after = {
        path.relative_to(bundle).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in bundle.rglob("*")
        if path.is_file()
    }

    assert after == before
    persisted = RepositorySnapshotV1.model_validate_json(
        (bundle / "source" / "revision.json").read_text(encoding="utf-8")
    )
    assert persisted.captured_at == first.captured_at
    assert persisted.snapshot_root == first.snapshot_root
    assert verify_sha256sums(bundle)


def test_snapshot_identity_mismatch_fails_without_overwriting_sealed_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = write_local_poc_snapshot(snapshot)
    before = {path: path.read_bytes() for path in bundle.rglob("*") if path.is_file()}
    mismatched = snapshot.model_copy(update={"inventory_sha256": "d" * 64})

    with pytest.raises(RepositorySnapshotError, match="inventory"):
        write_local_poc_snapshot(mismatched)

    assert {path: path.read_bytes() for path in bundle.rglob("*") if path.is_file()} == before
    assert verify_sha256sums(bundle)


def test_checksum_corruption_fails_without_repair_or_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = write_local_poc_snapshot(snapshot)
    revision_path = bundle / "source" / "revision.json"
    revision_path.write_text("{}\n", encoding="utf-8")
    corrupt_bytes = revision_path.read_bytes()
    corrupt_inventory = (bundle / "sha256sums.txt").read_bytes()

    with pytest.raises(RepositorySnapshotError, match="checksum inventory"):
        write_local_poc_snapshot(snapshot)

    assert revision_path.read_bytes() == corrupt_bytes
    assert (bundle / "sha256sums.txt").read_bytes() == corrupt_inventory
    assert not verify_sha256sums(bundle)


@pytest.mark.parametrize("failure", ["missing", "malformed"])
def test_invalid_revision_with_self_consistent_inventory_fails_closed(
    tmp_path, monkeypatch, failure
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = write_local_poc_snapshot(snapshot)
    revision_path = bundle / "source" / "revision.json"
    if failure == "missing":
        revision_path.unlink()
    else:
        revision_path.write_text("{}\n", encoding="utf-8")
    refresh_sha256sums(bundle)
    before = {path: path.read_bytes() for path in bundle.rglob("*") if path.is_file()}

    with pytest.raises(RepositorySnapshotError, match="RepositorySnapshotV1"):
        write_local_poc_snapshot(snapshot)

    assert {path: path.read_bytes() for path in bundle.rglob("*") if path.is_file()} == before
    assert verify_sha256sums(bundle)


def test_source_readme_mismatch_with_valid_inventory_fails_without_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = write_local_poc_snapshot(snapshot)
    persisted_readme = bundle / "source" / "README.md"
    persisted_readme.write_text("# Replaced evidence\n", encoding="utf-8")
    refresh_sha256sums(bundle)
    before = {path: path.read_bytes() for path in bundle.rglob("*") if path.is_file()}

    with pytest.raises(RepositorySnapshotError, match="sealed README differs"):
        write_local_poc_snapshot(snapshot)

    assert {path: path.read_bytes() for path in bundle.rglob("*") if path.is_file()} == before
    assert verify_sha256sums(bundle)


def test_missing_readme_is_explicit_evidence_not_a_fake_empty_readme(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")

    bundle = write_local_poc_snapshot(_snapshot(tmp_path, readme=False))

    assert (bundle / "source" / "readme-absence.json").is_file()
    assert not (bundle / "source" / "README.md").exists()
    before = {
        path.relative_to(bundle).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in bundle.rglob("*")
        if path.is_file()
    }
    recaptured = _snapshot(
        tmp_path,
        readme=False,
        captured_at="2026-07-27T00:00:00+00:00",
    )
    assert write_local_poc_snapshot(recaptured) == bundle
    assert {
        path.relative_to(bundle).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in bundle.rglob("*")
        if path.is_file()
    } == before
    assert verify_sha256sums(bundle)


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
        package_root_roles=PackageRootRoleInventoryV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            selection_state="selected",
            selected_product_manifest_path="pom.xml",
            selection_rationale=["sole product root"],
            roots=[
                PackageRootRoleV1(
                    path=".",
                    ecosystem="java",
                    manifest_path="pom.xml",
                    role="product",
                    confidence=1.0,
                    parsed_identity={"artifact_id": "product"},
                    rationale=["selected as the distributed product root"],
                )
            ],
        ),
    )

    bundle = write_local_poc_product_facts(
        snapshot,
        facts,
        findings=[],
        resolution_source="agent_draft",
        proposed_product_truth={"audience": ["Product users"]},
        prompt_hash=prompt_registry.prompt_hash("draft_product_truth"),
        local_verification_contract_hash="v" * 64,
        fact_acceptance_contract_hash="a" * 64,
        fact_acceptance_component_hashes={"evidence_polarity": "b" * 64},
    )
    proposal_path = bundle / "facts" / "proposed-product-truth.json"
    assert proposal_path.is_file()

    bundle = write_local_poc_product_facts(
        snapshot,
        facts,
        findings=[],
        resolution_source="repository_and_policy",
        local_verification_contract_hash="v" * 64,
        fact_acceptance_contract_hash="a" * 64,
        fact_acceptance_component_hashes={"evidence_polarity": "b" * 64},
    )

    assert not proposal_path.exists()
    assert verify_sha256sums(bundle)
    assert (bundle / "facts" / "product-facts.json").is_file()
    assert (bundle / "facts" / "provenance.json").is_file()
    assert (bundle / "facts" / "conflicts.json").is_file()
    assert (bundle / "facts" / "acquisition.json").is_file()
    persisted_facts = json.loads(
        (bundle / "facts" / "product-facts.json").read_text(encoding="utf-8")
    )
    assert persisted_facts["package_root_roles"]["selected_product_manifest_path"] == "pom.xml"
    assert persisted_facts["package_root_roles"]["roots"][0]["role"] == "product"
    checksum_inventory = (bundle / "sha256sums.txt").read_text(encoding="utf-8")
    assert "facts/product-facts.json" in checksum_inventory
    assert "facts/provenance.json" in checksum_inventory
    assert "source/revision.json" not in checksum_inventory  # this unit starts at the facts stage
    manifest = (bundle / "manifest.json").read_text(encoding="utf-8")
    assert '"lifecycle_status": "FACTS_READY"' in manifest
    assert facts.canonical_hash() in manifest
    assert '"local_verification_contract_hash": "' + ("v" * 64) + '"' in manifest

    mark_local_poc_profiled(snapshot, bundle)

    assert (bundle / "manifest.json").read_text(encoding="utf-8") == manifest


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
        "product.identity": {"name": "Product", "family": "cells", "ecosystem": "java"},
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
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["lifecycle_status"] == "CANDIDATE_GENERATED"
    assert manifest["local_verification_contract_hash"] == "v" * 64
    assert len(manifest["repair_budget_origin_hash"]) == 64
    checksum_inventory = (bundle / "sha256sums.txt").read_text(encoding="utf-8")
    assert "assessment/current-readme-assessment.json" in checksum_inventory
    assert "candidate/README.md" in checksum_inventory
    prior_facts_text = (bundle / "facts" / "product-facts.json").read_text(encoding="utf-8")
    changed_records = [
        (
            fact.model_copy(update={"value": ["Read and convert product files"]})
            if fact.field == "product.capabilities"
            else fact
        )
        for fact in facts.facts
    ]
    changed_facts = facts.model_copy(update={"facts": changed_records})
    receipts = bundle / "receipts"
    receipts.mkdir()
    (receipts / "CANDIDATE_GENERATED.json").write_text(
        '{"target_stage": "CANDIDATE_GENERATED"}\n', encoding="utf-8"
    )
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["acceptance_authority"] = "sealed_stage_receipts"
    manifest["stage_receipts"] = {
        "CANDIDATE_GENERATED": {
            "receipt_path": "receipts/CANDIDATE_GENERATED.json",
        }
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    refresh_sha256sums(bundle)

    write_local_poc_product_facts(
        snapshot,
        changed_facts,
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
    assert "acceptance_authority" not in invalidated_manifest
    assert "stage_receipts" not in invalidated_manifest
    superseded = bundle / "superseded" / candidate_hash[:16]
    assert (superseded / "candidate" / "README.md").read_text(encoding="utf-8") == candidate
    superseded_record = json.loads((superseded / "superseded.json").read_text(encoding="utf-8"))
    assert superseded_record["candidate_hash"] == candidate_hash
    assert superseded_record["candidate_binding"] == "manifest_bound"
    assert "product fact or fact-acceptance dependency changed" in superseded_record["reason"]
    assert "candidate/README.md" in (superseded / "sha256sums.txt").read_text(encoding="utf-8")
    assert (superseded / "facts" / "product-facts.json").read_text(
        encoding="utf-8"
    ) == prior_facts_text
    assert (superseded / "receipts" / "CANDIDATE_GENERATED.json").is_file()
    for name in ("assessment", "planning", "candidate", "review", "receipts"):
        assert not (bundle / name).exists()
    assert (
        ProductFactsV2.model_validate_json(
            (bundle / "facts" / "product-facts.json").read_text(encoding="utf-8")
        )
        == changed_facts
    )
    assert verify_sha256sums(bundle)

    receipts.mkdir()
    (receipts / "AGENT_APPROVED.json").write_text(
        '{"target_stage": "AGENT_APPROVED"}\n', encoding="utf-8"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["acceptance_authority"] = "sealed_stage_receipts"
    manifest["stage_receipts"] = {
        "AGENT_APPROVED": {"receipt_path": "receipts/AGENT_APPROVED.json"}
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    refresh_sha256sums(bundle)

    write_local_poc_product_facts(
        snapshot,
        changed_facts,
        findings=[],
        resolution_source="repository_and_policy",
        local_verification_contract_hash="w" * 64,
        fact_acceptance_contract_hash="a" * 64,
        fact_acceptance_component_hashes={"evidence_polarity": "b" * 64},
    )
    assert not receipts.exists()
    receipt_only_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "acceptance_authority" not in receipt_only_manifest
    assert "stage_receipts" not in receipt_only_manifest
    assert verify_sha256sums(bundle)
    assert [path.name for path in (bundle / "superseded").iterdir()] == [candidate_hash[:16]]


def test_unchanged_candidate_bytes_with_new_dependency_key_reopens_stale_acceptance(
    tmp_path, monkeypatch
):
    """Regression for L8-VPY-03A `deterministic_manifest_dependency_key_mismatch`.

    A shared rendering/component dependency (e.g. the Mermaid renderer) can change
    without altering the composed README bytes. `same_candidate` previously keyed only
    on `candidate_hash`, so it preserved a stale `AGENT_APPROVED`/`NO_OP_PROVEN`
    lifecycle while still stamping the manifest's `candidate_stage_dependency_key`
    forward -- leaving the review/no-op artifacts bound to the superseded key with no
    signal to regenerate them. The manifest must instead reopen at CANDIDATE_GENERATED
    whenever the dependency key moves, independent of candidate byte equality.
    """

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://acme/product",
        source_revision=snapshot.source_revision,
    )
    values = {
        "product.identity": {"name": "Product", "family": "cells", "ecosystem": "java"},
        "product.audience": ["Java developers"],
        "product.problems_solved": ["Read product files"],
        "product.capabilities": ["Read files"],
        "product.formats": ["Product files"],
        "product.compatibility": {"minimum_runtime": "Java 11"},
        "product.limitations": ["Read-only fixture"],
        "example.minimal": {"language": "java", "code": "public class Example {}"},
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "dependency-key-drift-test"),
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
    render_result = {"source_revision": snapshot.source_revision, "final_text": candidate}
    presentation_plan = {
        "readme_assessment": assessment.model_dump(mode="json"),
        "readme_document_plan": document_plan.model_dump(mode="json"),
        "claim_map": claim_map.model_dump(mode="json"),
        "presentation_plan": {"repository": snapshot.org_repo},
        "git_patch_proof": {"patch": "fixture patch\n"},
        "executable": True,
    }

    bundle, *_ = write_local_poc_readme_candidate(snapshot, render_result, presentation_plan)

    manifest_path = bundle / "manifest.json"
    approved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    approved_manifest["lifecycle_status"] = "NO_OP_PROVEN"
    approved_manifest["complete"] = True
    approved_manifest["completed_stages"] = [
        *approved_manifest["completed_stages"],
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
    ]
    manifest_path.write_text(json.dumps(approved_manifest, indent=2) + "\n", encoding="utf-8")
    refresh_sha256sums(bundle)

    real_dependency_manifest = current_candidate_stage_dependency_manifest(
        repository=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="unknown",
    )
    changed_dependency_manifest = build_stage_dependency_manifest(
        repository=real_dependency_manifest.repository,
        source_revision=real_dependency_manifest.source_revision,
        stage=real_dependency_manifest.stage,
        ecosystem=real_dependency_manifest.ecosystem,
        dependencies=[
            *real_dependency_manifest.dependencies,
            SelectedDependencyV1(
                dependency_id="header_visual_synthetic_change",
                files={"src/readme_agent/verification/mermaid_render.py": "f" * 64},
                semantic_scope="cosmetic",
                earliest_affected_stage="PLAN_READY",
            ),
        ],
    )
    assert changed_dependency_manifest.stage_key != real_dependency_manifest.stage_key
    monkeypatch.setattr(
        local_poc_evidence,
        "current_candidate_stage_dependency_manifest",
        lambda **_kwargs: changed_dependency_manifest,
    )

    reopened_bundle, *_ = write_local_poc_readme_candidate(
        snapshot, render_result, presentation_plan
    )

    assert reopened_bundle == bundle
    reopened_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert reopened_manifest["candidate_hash"] == approved_manifest["candidate_hash"]
    assert (
        reopened_manifest["candidate_stage_dependency_key"] == changed_dependency_manifest.stage_key
    )
    assert reopened_manifest["lifecycle_status"] == "CANDIDATE_GENERATED"
    assert reopened_manifest["complete"] is False
    assert "AGENT_APPROVED" not in reopened_manifest["completed_stages"]
    assert "NO_OP_PROVEN" not in reopened_manifest["completed_stages"]
    assert verify_sha256sums(bundle)
