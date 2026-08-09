"""Tests for the versioned cached-product-truth acceptance boundary."""

import pytest

from readme_agent.facts.acceptance_contract import (
    _COMPONENT_FILES,
    README_TRUTH_FIELDS,
    _component_hash,
    _scoped_component_files,
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactConflictV2,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


def _facts(*, missing_field: str | None = None) -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision="a" * 40,
    )
    renderable_values = {
        "product.audience": ["Developers using Java"],
        "product.problems_solved": ["Process widget files"],
        "product.capabilities": ["Create and inspect widgets"],
        "product.formats": ["WGT"],
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "contract-fixture"),
            field=field,
            value=(
                None if field == missing_field else renderable_values.get(field, {"field": field})
            ),
            source=source,
            verification_state="missing" if field == missing_field else "verified",
            authoritative_owner="repository-owner",
            confidence=0.0 if field == missing_field else 1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo="org/repo",
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def test_contract_hash_covers_every_named_acceptance_component():
    contract = current_fact_acceptance_contract()

    assert contract.required_fields == README_TRUTH_FIELDS
    assert set(contract.component_hashes) == {
        "acquisition_truth",
        "classification_semantics",
        "conflict_semantics",
        "drafting_and_example_selection",
        "fact_schema",
        "fact_eligibility",
        "evidence_polarity",
        "root_role_selection",
        "visitor_render_eligibility",
        "documentation_catalog",
    }
    assert contract.recollect_on_component_change == (
        "fact_schema",
        "fact_eligibility",
        "acquisition_truth",
        "drafting_and_example_selection",
        "evidence_polarity",
        "root_role_selection",
        "documentation_catalog",
    )
    assert len(contract.canonical_hash()) == 64
    assert all(len(digest) == 64 for digest in contract.component_hashes.values())
    assert "../ecosystems/registry_request.py" in _COMPONENT_FILES["acquisition_truth"]
    assert "acquisition_pins.py" in _COMPONENT_FILES["acquisition_truth"]
    assert "python_repository_examples.py" in _COMPONENT_FILES["drafting_and_example_selection"]
    assert "verified_repository_examples.py" in _COMPONENT_FILES["drafting_and_example_selection"]
    assert "deterministic_truth_salvage.py" in _COMPONENT_FILES["drafting_and_example_selection"]
    assert "interpretive_resolution.py" in _COMPONENT_FILES["drafting_and_example_selection"]
    assert (
        "../capabilities/draft_product_truth.py"
        in _COMPONENT_FILES["drafting_and_example_selection"]
    )
    assert {
        "aspose_org_dependency_snapshot.py",
        "aspose_org_format_adapter.py",
        "aspose_org_format_contract.py",
    }.issubset(_COMPONENT_FILES["drafting_and_example_selection"])
    assert {
        "curated_readme_evidence.py",
        "curated_constraint_evidence.py",
        "curated_python_api_ast.py",
        "curated_python_api_eligibility.py",
        "curated_python_api_projection.py",
        "curated_python_dependencies.py",
        "curated_python_development.py",
        "curated_python_evidence.py",
        "curated_python_example_validation.py",
        "curated_python_fixture_inventory.py",
        "curated_python_import_shadowing.py",
        "curated_python_pdf_evidence.py",
        "curated_python_pdf_guidance.py",
        "curated_python_public_surface.py",
        "curated_repository_assets.py",
    }.issubset(_COMPONENT_FILES["root_role_selection"])


def test_component_or_rule_change_changes_the_contract_hash():
    contract = current_fact_acceptance_contract()

    component_changed = contract.model_copy(
        update={
            "component_hashes": {
                **contract.component_hashes,
                "evidence_polarity": "0" * 64,
            }
        }
    )
    membership_changed = contract.model_copy(
        update={"required_fields": (*contract.required_fields, "product.limitations")}
    )

    assert component_changed.canonical_hash() != contract.canonical_hash()
    assert membership_changed.canonical_hash() != contract.canonical_hash()


def test_ecosystem_contract_excludes_unrelated_fact_adapters():
    python_acquisition = _scoped_component_files("acquisition_truth", "python", "page")
    net_acquisition = _scoped_component_files("acquisition_truth", "net", "3d")
    python_roots = _scoped_component_files("root_role_selection", "python", "page")
    net_roots = _scoped_component_files("root_role_selection", "net", "3d")

    assert "python_example_verifier.py" in python_acquisition
    assert "dotnet_example_verifier.py" not in python_acquisition
    assert "dotnet_example_verifier.py" in net_acquisition
    assert "python_example_verifier.py" not in net_acquisition
    assert "curated_python_evidence.py" in python_roots
    assert "curated_python_evidence.py" not in net_roots


@pytest.mark.parametrize("ecosystem", ["python", "net"])
def test_family_owned_contract_requires_family_context(ecosystem):
    with pytest.raises(ValueError, match="family is required"):
        current_fact_acceptance_contract(ecosystem)


def test_dotnet_family_adapter_hash_is_scoped_to_3d():
    three_d = _scoped_component_files("drafting_and_example_selection", "net", "3d")
    pdf = _scoped_component_files("drafting_and_example_selection", "net", "pdf")

    assert "dotnet_3d_format_functionality.py" in three_d
    assert "dotnet_3d_format_functionality.py" not in pdf
    email = _scoped_component_files("drafting_and_example_selection", "net", "email")
    assert "dotnet_email_format_functionality.py" in email
    assert "dotnet_email_format_functionality.py" not in pdf


def test_python_family_adapter_hashes_invalidate_only_their_owner(tmp_path):
    component = "drafting_and_example_selection"
    family_files = {
        family: _scoped_component_files(component, "python", family)
        for family in ("3d", "page", "pdf", "barcode", "html")
    }
    for relative_path in set().union(*map(set, family_files.values())):
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"baseline:{relative_path}\n", encoding="utf-8")

    def hashes() -> dict[str, str]:
        return {
            family: _component_hash(tmp_path, relative_paths)
            for family, relative_paths in family_files.items()
        }

    baseline = hashes()
    three_d_adapter = tmp_path / "python_3d_format_functionality.py"
    three_d_adapter.write_text("changed 3d corroborator\n", encoding="utf-8")
    after_three_d = hashes()

    assert after_three_d["3d"] != baseline["3d"]
    assert after_three_d["page"] == baseline["page"]
    assert after_three_d["pdf"] == baseline["pdf"]
    assert after_three_d["barcode"] == baseline["barcode"]
    assert after_three_d["html"] == baseline["html"]

    common_adapter = tmp_path / "python_family_format_functionality.py"
    common_adapter.write_text("changed common Python corroborator\n", encoding="utf-8")
    after_common = hashes()

    assert all(after_common[family] != after_three_d[family] for family in family_files)


def test_classification_honors_the_contract_verification_states():
    facts = _facts()
    contract = current_fact_acceptance_contract().model_copy(
        update={"accepted_verification_states": ("policy_approved",)}
    )

    assert classify_product_truth(facts, contract) == "BLOCKED_MISSING_EVIDENCE"


def test_component_hash_is_checkout_line_ending_invariant(tmp_path):
    lf_root = tmp_path / "lf"
    crlf_root = tmp_path / "crlf"
    lf_root.mkdir()
    crlf_root.mkdir()
    lf = lf_root / "component.py"
    crlf = crlf_root / "component.py"
    lf.write_bytes(b"first = 1\nsecond = 2\n")
    crlf.write_bytes(b"first = 1\r\nsecond = 2\r\n")

    assert _component_hash(lf_root, ("component.py",)) == _component_hash(
        crlf_root, ("component.py",)
    )


def test_curated_fact_owner_change_invalidates_root_role_component(tmp_path):
    component_files = _COMPONENT_FILES["root_role_selection"]
    for relative_path in component_files:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"owner = {relative_path!r}\n", encoding="utf-8")
    baseline = _component_hash(tmp_path, component_files)
    owner = tmp_path / "curated_python_evidence.py"
    owner.write_text(owner.read_text(encoding="utf-8") + "contract = 2\n", encoding="utf-8")

    assert _component_hash(tmp_path, component_files) != baseline


def test_interpretive_resolution_change_invalidates_drafting_component(tmp_path):
    component_files = _COMPONENT_FILES["drafting_and_example_selection"]
    for relative_path in component_files:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"owner = {relative_path!r}\n", encoding="utf-8")
    baseline = _component_hash(tmp_path, component_files)
    owner = tmp_path / "interpretive_resolution.py"
    owner.write_text(owner.read_text(encoding="utf-8") + "contract = 2\n", encoding="utf-8")

    assert _component_hash(tmp_path, component_files) != baseline


def test_classification_uses_the_versioned_required_field_membership():
    facts = _facts(missing_field="product.limitations")
    contract = current_fact_acceptance_contract()

    assert classify_product_truth(facts, contract) == "FACTS_READY"
    stricter = contract.model_copy(
        update={"required_fields": (*contract.required_fields, "product.limitations")}
    )
    assert classify_product_truth(facts, stricter) == "BLOCKED_MISSING_EVIDENCE"


def test_missing_contract_field_fails_closed_instead_of_raising():
    facts = _facts()
    contract = current_fact_acceptance_contract().model_copy(
        update={"required_fields": (*README_TRUTH_FIELDS, "product.not_yet_defined")}
    )

    assert classify_product_truth(facts, contract) == "BLOCKED_MISSING_EVIDENCE"


def test_classification_uses_fact_eligibility_and_conflict_semantics():
    facts = _facts()
    audience = facts.selected_fact("product.audience")
    blocked_audience = audience.model_copy(update={"verification_state": "blocked"})
    blocked = facts.model_copy(
        update={
            "facts": [
                blocked_audience if fact.fact_id == audience.fact_id else fact
                for fact in facts.facts
            ]
        }
    )
    conflicting_audience = audience.model_copy(
        update={
            "verification_state": "conflicting",
            "conflicts": [
                FactConflictV2(
                    conflicting_fact_id=descriptive_fact_id(
                        "product.audience", "conflicting-fixture"
                    ),
                    conflicting_value=["Operators using Python"],
                    conflicting_source=audience.source,
                    status="unresolved",
                    reason="controlled conflict",
                    authoritative_owner="repository-owner",
                    affected_surfaces=["readme"],
                )
            ],
        }
    )
    conflicting = facts.model_copy(
        update={
            "facts": [
                conflicting_audience if fact.fact_id == audience.fact_id else fact
                for fact in facts.facts
            ]
        }
    )

    assert classify_product_truth(blocked) == "BLOCKED_MISSING_EVIDENCE"
    assert classify_product_truth(conflicting) == "BLOCKED_FACT_CONFLICT"


def test_verified_but_non_renderable_visitor_fact_is_not_accepted():
    facts = _facts()
    audience = facts.selected_fact("product.audience")
    non_renderable = audience.model_copy(update={"value": {"internal": "audience-code"}})
    altered = facts.model_copy(
        update={
            "facts": [
                non_renderable if fact.fact_id == audience.fact_id else fact for fact in facts.facts
            ]
        }
    )

    assert classify_product_truth(altered) == "BLOCKED_MISSING_EVIDENCE"
