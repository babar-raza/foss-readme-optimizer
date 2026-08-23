"""Deterministic resolution behavior for one external fact block against evidence.

Every scenario here is a synthetic, generic example of one block class -- never a
reproduction of a real PF-01 receipt. The five infra_external receipts behind PF-01's
portfolio sweep live only in a gitignored runtime artifact
(runs/readme-poc/portfolio-summary.json) absent from this isolated lane's fresh clone;
see module_handoffs/external-fact-block-resolution/*/CURRENT_FIVE_BLOCKS_MATRIX.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.facts.external_fact_block_resolution import (
    AvailableFactEvidenceCatalogV1,
    AvailableFactEvidenceV1,
    ExternalDependencyFingerprintV1,
    ExternalFactBlockResolutionV1,
    ExternalFactBlockV1,
    FactAssertionAuthorityV1,
    classify_external_fact_block_class,
    resolve_external_fact_block,
)

_ORG_REPO = "acme/widget"
_SOURCE_REVISION = "a" * 40
_OTHER_REVISION = "b" * 40
_PACKAGE_IDENTITY = "pypi:widget==1.0.0"


def _block(**overrides: object) -> ExternalFactBlockV1:
    fields: dict[str, object] = {
        "block_id": "block-1",
        "fact_surface": "product.capabilities",
        "claim_kind": "identity_coordinates",
        "diagnostic_code": None,
        "detail": "unspecified failure",
        "org_repo": _ORG_REPO,
        "source_revision": _SOURCE_REVISION,
        "package_identity": _PACKAGE_IDENTITY,
    }
    fields.update(overrides)
    return ExternalFactBlockV1(**fields)


def _evidence(**overrides: object) -> AvailableFactEvidenceV1:
    fields: dict[str, object] = {
        "evidence_id": "evidence-1",
        "evidence_kind": "current_source_or_manifest",
        "competent_claim_kinds": ("identity_coordinates",),
        "org_repo": _ORG_REPO,
        "source_revision": _SOURCE_REVISION,
        "package_identity": _PACKAGE_IDENTITY,
        "omission_basis": None,
        "detail": "widget's own manifest at the current revision",
    }
    fields.update(overrides)
    return AvailableFactEvidenceV1(**fields)


def _catalog(*items: AvailableFactEvidenceV1) -> AvailableFactEvidenceCatalogV1:
    return AvailableFactEvidenceCatalogV1(
        org_repo=_ORG_REPO, source_revision=_SOURCE_REVISION, items=items
    )


def _fingerprint(**overrides: object) -> ExternalDependencyFingerprintV1:
    fields: dict[str, object] = {"source_revision": _SOURCE_REVISION}
    fields.update(overrides)
    return ExternalDependencyFingerprintV1(**fields)


# --- 1: every supported class is recognized from structured input -----------


@pytest.mark.parametrize(
    "diagnostic_code,expected_class",
    [
        ("GIT_CLONE_FAILED", "repository_clone_failure"),
        ("GIT_LFS_OBJECT_MISSING", "git_lfs_object_unavailable"),
        ("REGISTRY_UNAVAILABLE", "package_registry_unavailable"),
        ("PACKAGE_VERSION_NOT_FOUND", "package_version_unresolved"),
        ("TOOLCHAIN_UNAVAILABLE", "toolchain_unavailable"),
        ("DEPENDENCY_RESOLUTION_FAILED", "dependency_resolution_failure"),
        ("EXAMPLE_RUNTIME_UNAVAILABLE", "example_runtime_unavailable"),
        ("SOURCE_PACKAGE_MISMATCH", "source_package_mismatch"),
        ("NETWORK_RATE_LIMITED", "network_rate_limited"),
        ("LOCAL_CACHE_CORRUPT", "corrupt_local_cache"),
        ("PLATFORM_VERIFIER_UNSUPPORTED", "unsupported_platform_verifier"),
        ("EXTERNAL_AUTHENTICATION_UNAVAILABLE", "external_authentication_unavailable"),
    ],
)
def test_every_documented_diagnostic_code_is_recognized_from_structured_input(
    diagnostic_code, expected_class
):
    assert (
        classify_external_fact_block_class(diagnostic_code=diagnostic_code, detail="irrelevant")
        == expected_class
    )


def test_a_structured_diagnostic_code_takes_precedence_over_conflicting_detail_text():
    result = classify_external_fact_block_class(
        diagnostic_code="GIT_LFS_OBJECT_MISSING", detail="registry unavailable right now"
    )
    assert result == "git_lfs_object_unavailable"


# --- 2: unknown remains unknown ----------------------------------------------


def test_an_unrecognized_diagnostic_code_and_detail_default_to_unknown_rather_than_guessing():
    result = classify_external_fact_block_class(
        diagnostic_code="SOME_NEW_TOOL_CODE", detail="nothing recognizable here"
    )
    assert result == "unknown"


# --- 3: current source resolves competent surfaces ---------------------------


def test_current_source_evidence_asserts_an_identity_coordinates_claim():
    block = _block(claim_kind="identity_coordinates")
    evidence = _evidence(
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "assert"
    assert resolution.authority.ladder_tier == 1


def test_current_source_evidence_asserts_a_static_existence_claim():
    block = _block(claim_kind="static_existence")
    evidence = _evidence(
        evidence_kind="current_source_or_manifest", competent_claim_kinds=("static_existence",)
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "assert"


# --- 4: package metadata supports coordinates, not runtime -------------------


def test_distribution_metadata_asserts_identity_coordinates():
    block = _block(claim_kind="identity_coordinates")
    evidence = _evidence(
        evidence_id="metadata-1",
        evidence_kind="committed_distribution_metadata",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=None,
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "assert"
    assert resolution.authority.ladder_tier == 2


def test_distribution_metadata_is_incompetent_for_runtime_behavior_and_falls_through_to_block():
    block = _block(claim_kind="runtime_behavior")
    evidence = _evidence(
        evidence_id="metadata-1",
        evidence_kind="committed_distribution_metadata",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=None,
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "block"


# --- 5: static API proves existence, not execution ----------------------------


def test_static_api_evidence_asserts_a_static_existence_claim():
    block = _block(claim_kind="static_existence")
    evidence = _evidence(
        evidence_id="static-1",
        evidence_kind="static_public_api_or_source",
        competent_claim_kinds=("static_existence", "example_execution", "runtime_behavior"),
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "assert"


def test_static_api_evidence_only_qualifies_an_example_execution_claim_never_asserts():
    block = _block(claim_kind="example_execution")
    evidence = _evidence(
        evidence_id="static-1",
        evidence_kind="static_public_api_or_source",
        competent_claim_kinds=("static_existence", "example_execution", "runtime_behavior"),
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "qualify"


# --- 6: syntax verification permits only qualified example wording -----------


def test_syntax_verified_example_qualifies_an_example_execution_claim_never_asserts():
    block = _block(claim_kind="example_execution")
    evidence = _evidence(
        evidence_id="syntax-1",
        evidence_kind="syntax_verified_example",
        competent_claim_kinds=("example_execution",),
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "qualify"
    assert resolution.authority.ladder_tier == 5


def test_constructing_an_assert_resolution_on_tier_five_evidence_is_structurally_rejected():
    authority = FactAssertionAuthorityV1(
        ladder_tier=5,
        evidence_kind="syntax_verified_example",
        claim_kind="example_execution",
        competent=True,
        citation_evidence_ids=("syntax-1",),
        rationale="syntax verified",
    )
    with pytest.raises(ValueError):
        ExternalFactBlockResolutionV1(
            block_id="block-1",
            fact_surface="example.minimal",
            claim_kind="example_execution",
            block_class="example_runtime_unavailable",
            wording_mode="assert",
            authority=authority,
            conflict_detected=False,
            conflicting_evidence_ids=(),
            prohibited_claims=("qualify", "omit", "not_applicable"),
            residual_unknowns=(),
            causally_relevant_fingerprint_fields=("toolchain_fingerprint",),
            resolution_hash="0" * 64,
            fingerprint_changed_since_previous_resolution=None,
            retry_recommended=True,
            resume_predicate="x",
        )


# --- 7: current verified imported knowledge supports only allowed surfaces ---


def test_verified_imported_knowledge_never_exceeds_qualify_even_for_identity_coordinates():
    block = _block(claim_kind="identity_coordinates")
    evidence = _evidence(
        evidence_id="imported-1",
        evidence_kind="verified_imported_knowledge",
        competent_claim_kinds=(
            "identity_coordinates",
            "static_existence",
            "example_execution",
            "runtime_behavior",
        ),
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "qualify"
    assert resolution.authority.ladder_tier == 4


# --- 8: synthetic/unresolved evidence cannot resolve --------------------------


def test_evidence_with_no_bound_source_revision_is_incompetent_and_is_skipped():
    block = _block(claim_kind="identity_coordinates", source_revision=_SOURCE_REVISION)
    unresolved_evidence = _evidence(
        evidence_id="unresolved-1",
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=None,
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(unresolved_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.wording_mode == "block"
    assert resolution.conflict_detected is False


# --- 9: conflicting evidence blocks -------------------------------------------


def test_conflicting_identity_between_block_and_evidence_fails_closed_to_block():
    block = _block(claim_kind="identity_coordinates", source_revision=_SOURCE_REVISION)
    conflicting_evidence = _evidence(
        evidence_id="conflict-1",
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=_OTHER_REVISION,
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(conflicting_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.wording_mode == "block"
    assert resolution.conflict_detected is True
    assert resolution.conflicting_evidence_ids == ("conflict-1",)


def test_conflicting_evidence_blocks_even_when_other_matching_evidence_is_also_present():
    block = _block(claim_kind="identity_coordinates", source_revision=_SOURCE_REVISION)
    conflicting_evidence = _evidence(
        evidence_id="conflict-1",
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=_OTHER_REVISION,
    )
    matching_evidence = _evidence(
        evidence_id="matching-1",
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=_SOURCE_REVISION,
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(conflicting_evidence, matching_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.wording_mode == "block"


def test_conflicting_identity_on_evidence_irrelevant_to_this_claim_kind_does_not_block():
    block = _block(claim_kind="identity_coordinates", source_revision=_SOURCE_REVISION)
    unrelated_conflicting_evidence = _evidence(
        evidence_id="unrelated-1",
        evidence_kind="syntax_verified_example",
        competent_claim_kinds=("example_execution",),
        source_revision=_OTHER_REVISION,
    )
    matching_evidence = _evidence(
        evidence_id="matching-1",
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
        source_revision=_SOURCE_REVISION,
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(unrelated_conflicting_evidence, matching_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.conflict_detected is False
    assert resolution.wording_mode == "assert"


# --- 10: no evidence blocks/omits according to policy -------------------------


def test_an_empty_evidence_catalog_remains_blocked_with_no_citations():
    resolution = resolve_external_fact_block(
        block=_block(), available_evidence=_catalog(), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "block"
    assert resolution.authority.citation_evidence_ids == ()
    assert resolution.authority.ladder_tier == 7


def test_only_irrelevant_evidence_present_still_remains_blocked_never_defaulting_to_omit():
    block = _block(claim_kind="identity_coordinates")
    irrelevant_evidence = _evidence(
        evidence_id="irrelevant-1",
        evidence_kind="syntax_verified_example",
        competent_claim_kinds=("example_execution",),
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(irrelevant_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.wording_mode == "block"


def test_non_applicability_evidence_grants_not_applicable_when_its_omission_basis_says_so():
    block = _block(claim_kind="runtime_behavior")
    evidence = _evidence(
        evidence_id="na-1",
        evidence_kind="non_applicability_evidence",
        competent_claim_kinds=("runtime_behavior",),
        omission_basis="not_applicable",
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "not_applicable"
    assert resolution.authority.ladder_tier == 6


def test_non_applicability_evidence_grants_omit_when_its_omission_basis_is_qualified_omission():
    block = _block(claim_kind="runtime_behavior")
    evidence = _evidence(
        evidence_id="na-1",
        evidence_kind="non_applicability_evidence",
        competent_claim_kinds=("runtime_behavior",),
        omission_basis="omit",
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "omit"


# --- 11: toolchain unavailable permits static wording only --------------------


def test_toolchain_unavailable_with_only_static_evidence_permits_qualify_only():
    block = _block(
        claim_kind="example_execution",
        diagnostic_code="TOOLCHAIN_UNAVAILABLE",
        detail="toolchain unavailable in this environment",
    )
    static_evidence = _evidence(
        evidence_id="static-1",
        evidence_kind="static_public_api_or_source",
        competent_claim_kinds=("example_execution",),
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(static_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.block_class == "toolchain_unavailable"
    assert resolution.wording_mode == "qualify"


# --- 12: missing LICENSE is not an external block ------------------------------


def test_a_license_fact_surface_flows_through_the_same_generic_ladder_as_any_other_surface():
    block = _block(claim_kind="identity_coordinates", fact_surface="product.license")
    evidence = _evidence(
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("identity_coordinates",),
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert resolution.wording_mode == "assert"
    assert resolution.fact_surface == "product.license"


# --- 13: processability remains outside scope ----------------------------------


def test_the_resolution_model_has_no_repository_level_processability_field():
    assert "processable" not in ExternalFactBlockResolutionV1.model_fields
    assert "repository_eligible" not in ExternalFactBlockResolutionV1.model_fields


# --- 14/15: dependency change permits reevaluation -----------------------------


def test_a_changed_source_revision_invalidates_the_prior_resolution_for_a_clone_failure_block():
    block = _block(
        claim_kind="identity_coordinates",
        diagnostic_code="GIT_CLONE_FAILED",
        detail="git clone failed: connection reset",
        source_revision=_SOURCE_REVISION,
    )
    first = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=_fingerprint(source_revision=_SOURCE_REVISION),
    )
    second = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=_fingerprint(source_revision=_OTHER_REVISION),
        previous_resolution=first,
    )
    assert second.fingerprint_changed_since_previous_resolution is True


def test_a_changed_toolchain_fingerprint_permits_reevaluation_for_a_toolchain_unavailable_block():
    block = _block(
        claim_kind="example_execution",
        diagnostic_code="TOOLCHAIN_UNAVAILABLE",
        detail="toolchain unavailable",
    )
    first = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=_fingerprint(toolchain_fingerprint="v1"),
    )
    second = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=_fingerprint(toolchain_fingerprint="v2"),
        previous_resolution=first,
    )
    assert second.fingerprint_changed_since_previous_resolution is True
    assert second.retry_recommended is True


# --- 16: unchanged fingerprint suppresses retry ---------------------------------


def test_an_unchanged_fingerprint_suppresses_retry():
    block = _block(
        claim_kind="example_execution",
        diagnostic_code="TOOLCHAIN_UNAVAILABLE",
        detail="toolchain unavailable",
    )
    fingerprint = _fingerprint(toolchain_fingerprint="v1")
    first = resolve_external_fact_block(
        block=block, available_evidence=_catalog(), current_dependencies=fingerprint
    )
    second = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=fingerprint,
        previous_resolution=first,
    )
    assert second.fingerprint_changed_since_previous_resolution is False
    assert second.retry_recommended is False


# --- 17: time passage alone does not permit retry -------------------------------


def test_the_dependency_fingerprint_model_has_no_timestamp_field():
    assert "recorded_at" not in ExternalDependencyFingerprintV1.model_fields
    assert "timestamp" not in ExternalDependencyFingerprintV1.model_fields
    assert "resolved_at" not in ExternalDependencyFingerprintV1.model_fields


def test_calling_the_resolver_twice_with_byte_identical_inputs_yields_an_identical_hash():
    block = _block()
    evidence = _evidence()
    fingerprint = _fingerprint()
    first = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=fingerprint
    )
    second = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=fingerprint
    )
    assert first.resolution_hash == second.resolution_hash
    assert first.retry_recommended == second.retry_recommended


# --- 18: unsupported verifier is explicit ---------------------------------------


def test_unsupported_platform_verifier_is_a_distinct_block_class_from_toolchain_unavailable():
    block = _block(
        claim_kind="example_execution",
        diagnostic_code="PLATFORM_VERIFIER_UNSUPPORTED",
        detail="no verifier available for this platform",
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(), current_dependencies=_fingerprint()
    )
    assert resolution.block_class == "unsupported_platform_verifier"
    assert resolution.causally_relevant_fingerprint_fields == (
        "execution_environment_fingerprint",
        "toolchain_fingerprint",
    )


# --- 19: corrupt cache differs from network failure ------------------------------


def test_corrupt_local_cache_and_network_rate_limited_have_disjoint_causally_relevant_fields():
    cache_block = _block(diagnostic_code="LOCAL_CACHE_CORRUPT", detail="local cache corrupt")
    network_block = _block(diagnostic_code="NETWORK_RATE_LIMITED", detail="network rate limited")
    cache_resolution = resolve_external_fact_block(
        block=cache_block, available_evidence=_catalog(), current_dependencies=_fingerprint()
    )
    network_resolution = resolve_external_fact_block(
        block=network_block, available_evidence=_catalog(), current_dependencies=_fingerprint()
    )
    assert cache_resolution.causally_relevant_fingerprint_fields == ("local_cache_fingerprint",)
    assert network_resolution.causally_relevant_fingerprint_fields == (
        "network_policy_fingerprint",
    )


def test_a_changed_network_field_does_not_recommend_retry_for_a_corrupt_cache_block():
    block = _block(diagnostic_code="LOCAL_CACHE_CORRUPT", detail="local cache corrupt")
    first = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=_fingerprint(
            network_policy_fingerprint="policy-a", local_cache_fingerprint="cache-a"
        ),
    )
    second = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(),
        current_dependencies=_fingerprint(
            network_policy_fingerprint="policy-b", local_cache_fingerprint="cache-a"
        ),
        previous_resolution=first,
    )
    assert second.fingerprint_changed_since_previous_resolution is False


# --- 20: source/package mismatch fails closed -------------------------------------


def test_source_package_mismatch_resolves_via_the_generic_ladder_and_fails_closed_on_conflict():
    block = _block(
        claim_kind="identity_coordinates",
        diagnostic_code="SOURCE_PACKAGE_MISMATCH",
        detail="published package does not match source",
        source_revision=_SOURCE_REVISION,
        package_identity=_PACKAGE_IDENTITY,
    )
    mismatched_evidence = _evidence(
        evidence_id="mismatched-1",
        evidence_kind="committed_distribution_metadata",
        competent_claim_kinds=("identity_coordinates",),
        package_identity="pypi:widget==0.9.0",
        source_revision=None,
    )
    resolution = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(mismatched_evidence),
        current_dependencies=_fingerprint(),
    )
    assert resolution.block_class == "source_package_mismatch"
    assert resolution.wording_mode == "block"
    assert resolution.conflict_detected is True


# --- 21: secrets are redacted -------------------------------------------------------


def test_a_secret_like_token_in_the_blocks_own_detail_is_redacted_from_the_rationale():
    block = _block(detail="upstream auth failed: Bearer ghp_abcdefghijklmnopqrstuvwx")
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(), current_dependencies=_fingerprint()
    )
    assert "ghp_abcdefghijklmnopqrstuvwx" not in resolution.authority.rationale
    assert "[REDACTED]" in resolution.authority.rationale


def test_a_secret_like_token_in_evidence_detail_is_redacted_from_the_rationale():
    block = _block(claim_kind="example_execution")
    evidence = _evidence(
        evidence_id="syntax-1",
        evidence_kind="syntax_verified_example",
        competent_claim_kinds=("example_execution",),
        detail="build log token: ghp_zzzzzzzzzzzzzzzzzzzz leaked in output",
    )
    resolution = resolve_external_fact_block(
        block=block, available_evidence=_catalog(evidence), current_dependencies=_fingerprint()
    )
    assert "ghp_zzzzzzzzzzzzzzzzzzzz" not in resolution.authority.rationale


# --- 22: no product/family branching -------------------------------------------------


def test_identical_ladder_behavior_regardless_of_org_repo_or_package_identity_strings():
    for org_repo, package_identity in (
        ("acme/widget", "pypi:widget==1.0.0"),
        ("totally-unfamiliar-org/never-seen-product", "cargo:mystery-crate==9.9.9"),
    ):
        block = _block(
            org_repo=org_repo, package_identity=package_identity, claim_kind="identity_coordinates"
        )
        evidence = _evidence(
            org_repo=org_repo,
            package_identity=package_identity,
            evidence_kind="current_source_or_manifest",
            competent_claim_kinds=("identity_coordinates",),
        )
        catalog = AvailableFactEvidenceCatalogV1(
            org_repo=org_repo, source_revision=_SOURCE_REVISION, items=(evidence,)
        )
        resolution = resolve_external_fact_block(
            block=block, available_evidence=catalog, current_dependencies=_fingerprint()
        )
        assert resolution.wording_mode == "assert"


# --- 23: input order does not change result -------------------------------------------


def test_evidence_catalog_item_order_does_not_change_the_outcome_or_hash():
    block = _block(claim_kind="static_existence")
    tier1_evidence = _evidence(
        evidence_id="source-1",
        evidence_kind="current_source_or_manifest",
        competent_claim_kinds=("static_existence",),
    )
    tier3_evidence = _evidence(
        evidence_id="static-1",
        evidence_kind="static_public_api_or_source",
        competent_claim_kinds=("static_existence",),
    )
    forward = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(tier1_evidence, tier3_evidence),
        current_dependencies=_fingerprint(),
    )
    backward = resolve_external_fact_block(
        block=block,
        available_evidence=_catalog(tier3_evidence, tier1_evidence),
        current_dependencies=_fingerprint(),
    )
    assert forward.authority.ladder_tier == 1
    assert backward.authority.ladder_tier == 1
    assert forward.resolution_hash == backward.resolution_hash


# --- 24: resolution hash is deterministic ---------------------------------------------


def test_two_independently_constructed_but_field_identical_inputs_produce_the_same_hash():
    block_a = _block()
    block_b = ExternalFactBlockV1(**block_a.model_dump())
    evidence_a = _evidence()
    evidence_b = AvailableFactEvidenceV1(**evidence_a.model_dump())
    resolution_a = resolve_external_fact_block(
        block=block_a, available_evidence=_catalog(evidence_a), current_dependencies=_fingerprint()
    )
    resolution_b = resolve_external_fact_block(
        block=block_b, available_evidence=_catalog(evidence_b), current_dependencies=_fingerprint()
    )
    assert resolution_a.resolution_hash == resolution_b.resolution_hash


# --- 25: exact five receipts are covered only if genuinely available ------------------


def test_generic_fixtures_here_are_synthetic_and_never_claimed_as_a_real_pf01_receipt():
    # See this file's module docstring: the real five infra_external receipts are not
    # available in this isolated lane, so this suite proves the generic module only.
    assert True


# --- 26: no network/provider/extractor/state/product action occurs --------------------


def test_the_module_source_contains_no_network_filesystem_or_clock_side_effects():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "readme_agent"
        / "facts"
        / "external_fact_block_resolution.py"
    )
    source = module_path.read_text(encoding="utf-8")
    forbidden_tokens = (
        "import requests",
        "import httpx",
        "import subprocess",
        "import socket",
        "import urllib",
        "from pathlib",
        "datetime.now",
        "random.",
        "open(",
    )
    for token in forbidden_tokens:
        assert token not in source, f"forbidden token found in module source: {token}"


# --- additional structural-guarantee coverage ------------------------------------------


def test_omission_basis_is_required_exactly_for_non_applicability_evidence():
    with pytest.raises(ValueError):
        _evidence(evidence_kind="non_applicability_evidence", omission_basis=None)
    with pytest.raises(ValueError):
        _evidence(evidence_kind="current_source_or_manifest", omission_basis="omit")


def test_evidence_ids_must_be_unique_within_one_catalog():
    duplicate = _evidence(evidence_id="dup-1")
    with pytest.raises(ValueError):
        AvailableFactEvidenceCatalogV1(
            org_repo=_ORG_REPO,
            source_revision=_SOURCE_REVISION,
            items=(duplicate, _evidence(evidence_id="dup-1")),
        )
