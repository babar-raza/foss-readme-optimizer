"""RepositoryPresentationPlanV1 referential-integrity tests."""

import pytest
from pydantic import ValidationError

from readme_agent.facts.gating import TechnicalClaimV1
from readme_agent.presentation.schema import (
    PlannedSourceSpanV1,
    PresentationActionV1,
    RepositoryPresentationPlanV1,
)


def _blocked_action(action_id: str, depends_on: list[str]) -> PresentationActionV1:
    return PresentationActionV1(
        action_id=action_id,
        surface_id="readme",
        region_id="readme.resources",
        disposition="blocked",
        depends_on=depends_on,
        ownership_class="repository_file",
        proposed_operation="local_patch",
        validators=["independent_verifier"],
        rollback="discard candidate",
        stop_conditions=["facts unavailable"],
    )


def test_unknown_action_dependency_fails_closed():
    with pytest.raises(ValidationError, match="unknown dependencies"):
        RepositoryPresentationPlanV1(
            org_repo="acme/widget",
            immutable_base_revision="abc123",
            facts_hash="1" * 64,
            source_sha256="2" * 64,
            archetype="java-library",
            findings=[],
            actions=[_blocked_action("readme.resources", ["missing.action"])],
        )


def test_action_dependency_cycle_fails_closed():
    with pytest.raises(ValidationError, match="dependency cycle"):
        RepositoryPresentationPlanV1(
            org_repo="acme/widget",
            immutable_base_revision="abc123",
            facts_hash="1" * 64,
            source_sha256="2" * 64,
            archetype="java-library",
            findings=[],
            actions=[
                _blocked_action("readme.first", ["readme.second"]),
                _blocked_action("readme.second", ["readme.first"]),
            ],
        )


def test_action_fact_ids_must_equal_claim_citation_union():
    claim = TechnicalClaimV1(
        claim_id="readme.license",
        surface_id="readme.license",
        text="License: MIT",
        fact_ids=["product.license:primary"],
    )

    with pytest.raises(ValidationError, match="exactly equal"):
        PresentationActionV1(
            action_id="readme.resources",
            surface_id="readme",
            region_id="readme.resources",
            disposition="blocked",
            claims=[claim],
            fact_ids=["documentation.links:primary"],
            ownership_class="repository_file",
            proposed_operation="local_patch",
            validators=["claim_citations"],
            rollback="discard candidate",
            stop_conditions=["facts unavailable"],
        )


def test_ownership_class_and_operation_must_be_coherent():
    with pytest.raises(ValidationError, match="incompatible with ownership"):
        PresentationActionV1(
            action_id="readme.resources",
            surface_id="readme",
            region_id="readme.resources",
            disposition="blocked",
            ownership_class="settings_api",
            proposed_operation="local_patch",
            validators=["surface_ownership"],
            rollback="discard candidate",
            stop_conditions=["ownership changed"],
        )


def test_planned_source_span_rejects_traversal_and_bad_hashes():
    with pytest.raises(ValidationError, match="repository-relative"):
        PlannedSourceSpanV1(
            path="../escape",
            byte_start=0,
            byte_end=0,
            expected_sha256="1" * 64,
            replacement_sha256="2" * 64,
            purpose="escape repository",
        )
    with pytest.raises(ValidationError, match="lowercase SHA-256"):
        PlannedSourceSpanV1(
            path="README.md",
            byte_start=0,
            byte_end=0,
            expected_sha256="short",
            replacement_sha256="2" * 64,
            purpose="invalid hash",
        )
