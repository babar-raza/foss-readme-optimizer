"""Current fact-contract adapters for external block resolution."""

from __future__ import annotations

from readme_agent.facts.acceptance_contract import FactAcceptanceContractV1
from readme_agent.facts.external_fact_block_adapters import resolve_fact_record_block
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1

_REPO = "acme/widget"
_REVISION = "a" * 40


def _fact(
    fact_id: str,
    field: str,
    value: object,
    *,
    state: str = "verified",
    source_type: str = "mechanical_repository",
) -> FactRecordV2:
    return FactRecordV2.model_validate(
        {
            "fact_id": fact_id,
            "field": field,
            "value": value,
            "source": {
                "source_type": source_type,
                "location": f"repository://{field}",
                "source_revision": _REVISION,
            },
            "verification_state": state,
            "authoritative_owner": "repository-owner",
            "confidence": 1.0 if state == "verified" else 0.0,
            "affected_surfaces": ["readme"],
        }
    )


def _facts(*records: FactRecordV2) -> ProductFactsV2:
    return ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo=_REPO,
        facts=list(records),
        selected_fact_ids={record.field: record.fact_id for record in records},
        package_root_roles=None,
    )


def _snapshot() -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo=_REPO,
        source_revision=_REVISION,
        snapshot_root="C:/tmp/widget",
        readme_path="README.md",
        readme_sha256="1" * 64,
        inventory_sha256="2" * 64,
        package_roots=(),
        captured_at="2026-08-24T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/acme/widget.git",
            git_tree_sha256="2" * 64,
        ),
    )


def _contract() -> FactAcceptanceContractV1:
    return FactAcceptanceContractV1(
        required_fields=("example.minimal",),
        accepted_verification_states=("verified",),
        blocking_conflict_statuses=("unresolved",),
        recollect_on_component_change=("dependency_evidence",),
        visitor_render_fields=(),
        component_hashes={
            "dependency_evidence": "3" * 64,
            "drafting_and_example_selection": "4" * 64,
            "acquisition_truth": "5" * 64,
            "imported_knowledge": "6" * 64,
        },
    )


def test_source_package_mismatch_outranks_secondary_missing_tool_detail():
    example = _fact(
        "example.minimal:blocked",
        "example.minimal",
        {
            "verification_detail": "example rejected: undeclared or inaccessible package "
            "subpath; required executable is not available on PATH",
        },
        state="blocked",
    )
    api = _fact("api.public_surface:source", "api.public_surface", {"classes": []})
    decision = resolve_fact_record_block(
        example,
        facts=_facts(example, api),
        snapshot=_snapshot(),
        contract=_contract(),
    )
    assert decision.resolution.block_class == "source_package_mismatch"
    assert decision.recovery_action == "RESELECT_REPOSITORY_EXAMPLE"
    assert decision.blocked_category == "agent_fixable"


def test_acquisition_uses_same_revision_example_as_its_causal_failure():
    acquisition = _fact(
        "installation.verified_acquisition:blocked",
        "installation.verified_acquisition",
        {"detail": "isolated C++ source or exact consumer compilation failed"},
        state="blocked",
    )
    example = _fact(
        "example.minimal:blocked",
        "example.minimal",
        {"verification_detail": "fatal error: pugixml.hpp: No such file or directory"},
        state="blocked",
    )
    api = _fact("api.public_surface:source", "api.public_surface", {"classes": []})
    decision = resolve_fact_record_block(
        acquisition,
        facts=_facts(acquisition, example, api),
        snapshot=_snapshot(),
        contract=_contract(),
    )
    assert decision.resolution.block_class == "dependency_resolution_failure"
    assert decision.recovery_action == "RETRY_DECLARED_DEPENDENCY_VERIFICATION"


def test_product_source_failure_records_external_resume_boundary():
    example = _fact(
        "example.minimal:blocked",
        "example.minimal",
        {"verification_detail": "IndentationError: expected an indented block"},
        state="blocked",
    )
    api = _fact("api.public_surface:source", "api.public_surface", {"classes": []})
    decision = resolve_fact_record_block(
        example,
        facts=_facts(example, api),
        snapshot=_snapshot(),
        contract=_contract(),
    )
    assert decision.resolution.block_class == "product_source_failure"
    assert decision.recovery_action == "WAIT_FOR_SOURCE_REVISION"
    assert decision.blocked_category == "infra_external"


def test_unchanged_dependency_fingerprint_suppresses_duplicate_retry():
    example = _fact(
        "example.minimal:blocked",
        "example.minimal",
        {"verification_detail": "required executable is not available on PATH"},
        state="blocked",
    )
    facts = _facts(example)
    first = resolve_fact_record_block(
        example,
        facts=facts,
        snapshot=_snapshot(),
        contract=_contract(),
    )
    replay = resolve_fact_record_block(
        example,
        facts=facts,
        snapshot=_snapshot(),
        contract=_contract(),
        previous_resolution=first.resolution,
    )
    assert replay.resolution.fingerprint_changed_since_previous_resolution is False
    assert replay.resolution.retry_recommended is False


def test_manifest_evidence_retains_its_real_package_identity():
    acquisition = _fact(
        "installation.verified_acquisition:blocked",
        "installation.verified_acquisition",
        {
            "coordinate": {"name": "wrong-package"},
            "detail": "version not found",
        },
        state="blocked",
    )
    coordinates = _fact(
        "installation.coordinates:manifest",
        "installation.coordinates",
        [{"name": "real-package", "version": "1.0.0"}],
        source_type="mechanical_manifest",
    )
    decision = resolve_fact_record_block(
        acquisition,
        facts=_facts(acquisition, coordinates),
        snapshot=_snapshot(),
        contract=_contract(),
    )
    assert decision.block.package_identity == "wrong-package"
    assert decision.evidence_catalog.items[0].package_identity == "real-package==1.0.0"
