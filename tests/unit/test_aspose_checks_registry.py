"""T3 -- the vendored check-battery registry: derived inventory, classification,
and real end-to-end invocation of the underlying vendored functions."""

from __future__ import annotations

from readme_agent.validation.aspose_checks import load_check_registry


def test_registry_loads_the_complete_derived_inventory():
    """T14/resolution-7: the count is never a hand-maintained constant."""

    registry = load_check_registry()

    assert len(registry) >= 80  # derived, not pinned -- see module docstring
    assert all(name.startswith("check_") for name in registry)
    assert all(callable(d.function) for d in registry.values())


def test_every_check_gets_a_severity_and_scope_classification():
    registry = load_check_registry()

    for descriptor in registry.values():
        assert descriptor.severity in ("hard_gate", "heuristic")
        assert descriptor.scope in ("section", "document_global")
        if descriptor.scope == "section":
            assert descriptor.section is not None
        else:
            assert descriptor.section is None


def test_a_check_explicitly_downgraded_from_hard_gate_classifies_as_heuristic():
    """Real vendored docstring: 'Heuristic (downgraded from an originally-
    planned hard gate the moment this ran against...)' -- the classifier
    must read this as heuristic (current status), not hard_gate (history)."""

    registry = load_check_registry()

    descriptor = registry["check_dependency_scope_claim_matches_evidence"]
    assert descriptor.severity == "heuristic"


def test_an_unmarked_check_fails_closed_to_hard_gate():
    registry = load_check_registry()

    descriptor = registry["check_no_leaked_docstring_artifacts"]
    assert descriptor.doc_summary == ""
    assert descriptor.severity == "hard_gate"


def test_diagram_checks_are_classified_as_the_at_a_glance_section():
    registry = load_check_registry()

    diagram_checks = [d for name, d in registry.items() if name.startswith("check_diagram_")]
    assert len(diagram_checks) >= 10
    assert all(d.scope == "section" and d.section == "At a Glance" for d in diagram_checks)


def test_disposition_reconciliation_checks_are_document_global():
    """Cross-unit duplicate/coverage checks inherently span the whole
    document -- must never be classified as scoped to one section."""

    registry = load_check_registry()

    for name in (
        "check_content_unit_disposition_coverage",
        "check_structural_unit_disposition_coverage",
        "check_content_unit_probable_duplicate",
    ):
        assert registry[name].scope == "document_global"


def test_invoke_rejects_an_unaccepted_keyword_argument():
    registry = load_check_registry()
    descriptor = registry["check_required_sections"]

    import pytest

    with pytest.raises(TypeError, match="does not accept"):
        descriptor.invoke(readme_text="# X", some_unexpected_kwarg=True)


# --- Real end-to-end invocation of actual vendored functions ---


def test_check_required_sections_real_invocation_finds_missing_sections():
    registry = load_check_registry()
    descriptor = registry["check_required_sections"]

    missing = descriptor.invoke(readme_text="# Just a title\n\nNo sections here.\n")

    assert isinstance(missing, list)
    assert len(missing) > 0  # a bare title is missing every required H2


def test_check_heading_title_case_real_invocation_on_compliant_text():
    registry = load_check_registry()
    descriptor = registry["check_heading_title_case"]

    findings = descriptor.invoke(readme_text="# My Product\n\n## Installation\n\nText.\n")

    assert findings == []


def test_check_no_excluded_domain_links_real_invocation_flags_forum_link():
    registry = load_check_registry()
    descriptor = registry["check_no_excluded_domain_links"]

    findings = descriptor.invoke(
        readme_text="See [the forum](https://forum.aspose.com/t/example) for help."
    )

    assert len(findings) >= 1


def test_check_enterprise_edition_naming_real_invocation_on_clean_text():
    registry = load_check_registry()
    descriptor = registry["check_enterprise_edition_naming"]

    findings = descriptor.invoke(
        readme_text="# Aspose.Cells FOSS for Java\n\nNo commercial links.\n"
    )

    assert findings == []


def test_check_diagram_shape_real_invocation_on_absent_diagram():
    registry = load_check_registry()
    descriptor = registry["check_diagram_shape"]

    findings = descriptor.invoke(markdown_text="# Product\n\nNo diagram at all here.\n")

    assert isinstance(findings, list)
