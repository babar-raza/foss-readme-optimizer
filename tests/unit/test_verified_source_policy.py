"""Prove exact, fail-closed source-policy reconciliation through the verified seam."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.presentation import verified_source_policy
from readme_agent.presentation.verified_source_policy import build_verified_source_policy_edits
from readme_agent.presentation.verified_template_runtime import (
    build_verified_template_document_candidate,
)
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.registry.models import LinkAllocationPolicyV1
from tests.unit.test_readme_contextual_links import _verified_facts, _verified_plan


def test_policy_edits_only_visitor_spans_with_typed_authority(monkeypatch) -> None:
    relationship_fact = SimpleNamespace(
        verification_state="verified",
        has_unresolved_conflict=False,
    )
    facts = SimpleNamespace(
        selected_fact_ids={"relationship.commercial_foss": "relationship:verified"},
        fact_by_id=lambda fact_id: relationship_fact,
    )
    monkeypatch.setattr(
        verified_source_policy,
        "enterprise_product_name_from_facts",
        lambda facts: "Aspose.3D",
    )
    source = """Aspose.3D FOSS retains valuable prose around the commercial On-Premise edition.

Keep [external guidance](https://example.test/guide), but not
[stale Aspose docs](https://docs.aspose.com/3d/python-net/).

```text
commercial On-Premise edition https://docs.aspose.com/3d/python-net/
```
"""

    edits = build_verified_source_policy_edits(source, facts)  # type: ignore[arg-type]
    rendered = source
    for edit in reversed(edits):
        start = len(rendered.encode("utf-8")[: edit.source_byte_start].decode("utf-8"))
        end = len(rendered.encode("utf-8")[: edit.source_byte_end].decode("utf-8"))
        rendered = rendered[:start] + edit.replacement + rendered[end:]

    assert "valuable prose around the Aspose.3D Enterprise Edition" in rendered
    assert "[external guidance](https://example.test/guide)" in rendered
    assert "stale Aspose docs" in rendered
    assert "https://docs.aspose.com/3d/python-net/" not in rendered.split("```text", 1)[0]
    assert (
        "commercial On-Premise edition https://docs.aspose.com" in rendered.split("```text", 1)[1]
    )
    terminology_edit = next(
        edit
        for edit in edits
        if "readme.enterprise_edition_terminology" in edit.configured_standard_ids
    )
    assert terminology_edit.fact_ids == ["relationship:verified"]
    assert all(edit.configured_standard_ids for edit in edits)


def test_policy_blocks_terminology_without_relationship_fact(monkeypatch) -> None:
    facts = SimpleNamespace(
        selected_fact_ids={},
        fact_by_id=lambda fact_id: (_ for _ in ()).throw(KeyError(fact_id)),
    )
    monkeypatch.setattr(
        verified_source_policy,
        "enterprise_product_name_from_facts",
        lambda facts: "Aspose.3D",
    )

    with pytest.raises(ValueError, match="requires an accepted commercial/FOSS relationship fact"):
        build_verified_source_policy_edits(
            "Aspose.3D FOSS relates to the commercial On-Premise edition.\n",
            facts,  # type: ignore[arg-type]
        )


def test_preservation_reconciles_links_and_terminology_before_allocation() -> None:
    facts = _verified_facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    source = (
        "# Aspose.Cells FOSS for Java\n\n"
        "Exact opening value before "
        "[FOSS family](https://products.aspose.org/cells/) and after.\n\n"
        "## Repository notes\n\n"
        "Keep this exact valuable detail before the "
        "[commercial On-Premise edition](https://products.aspose.com/cells/java/) "
        "and after it.\n\n"
        "Keep [external guidance](https://example.test/guide) exact while dropping "
        "[stale docs](https://docs.aspose.com/cells/java/) and "
        "https://kb.aspose.com/cells/java/.\n"
    )
    catalogs = load_aspose_link_catalogs()
    candidate, plan = build_verified_template_document_candidate(
        facts,
        source,
        revision,
        _verified_plan(facts, source),
        link_catalogs=catalogs,
        link_allocation_policy=LinkAllocationPolicyV1(),
    )
    validation = validate_readme_document_candidate(
        source, candidate, plan, facts, link_catalogs=catalogs
    )

    assert validation.checks["contextual_links"] is True
    assert "policy_corrections_have_exact_partial_lineage failed" not in validation.errors
    assert "Exact opening value before FOSS family and after." in candidate
    assert "Aspose.Cells Enterprise Edition and after it." in candidate
    assert "[external guidance](https://example.test/guide)" in candidate
    assert all(term not in candidate for term in ("commercial On-Premise", "docs.aspose.com"))
    assert "kb.aspose.com" not in candidate
    assert candidate.count("products.aspose.org") == 1
    assert candidate.count("products.aspose.com") == 1
    policy_bindings = [
        binding
        for binding in plan.candidate_content_provenance
        if binding.provenance_id.startswith("source.policy.")
    ]
    assert {
        standard for binding in policy_bindings for standard in binding.configured_standard_ids
    } == {"readme.contextual_links", "readme.enterprise_edition_terminology"}
    terminology_binding = next(
        binding
        for binding in policy_bindings
        if "readme.enterprise_edition_terminology" in binding.configured_standard_ids
    )
    assert terminology_binding.fact_ids == [facts.selected_fact_ids["relationship.commercial_foss"]]
    assert plan.composition_ledger is not None
    exact_fragments = [
        segment.content_text
        for segment in plan.composition_ledger.segments
        if segment.origin == "source_preserved"
    ]
    assert any("Keep this exact valuable detail before the " in text for text in exact_fragments)
    assert any(" and after it." in text for text in exact_fragments)

    policy_resolutions = [
        resolution
        for resolution in plan.source_claim_resolutions
        if resolution.resolution == "presentation_policy_correction"
    ]
    assert policy_resolutions and all(item.policy_corrections for item in policy_resolutions)
    target = policy_resolutions[0]
    forged = target.policy_corrections[0].model_copy(update={"candidate_content_sha256": "0" * 64})
    forged_plan = plan.model_copy(
        update={
            "source_claim_resolutions": [
                item.model_copy(
                    update={"policy_corrections": [forged, *item.policy_corrections[1:]]}
                )
                if item.claim_id == target.claim_id
                else item
                for item in plan.source_claim_resolutions
            ]
        }
    )
    forged_validation = validate_readme_document_candidate(
        source, candidate, forged_plan, facts, link_catalogs=catalogs
    )
    assert "policy_corrections_have_exact_partial_lineage failed" in forged_validation.errors
