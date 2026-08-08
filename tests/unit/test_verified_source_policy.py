"""Prove exact, fail-closed source-policy reconciliation through the verified seam."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.presentation import verified_source_policy
from readme_agent.presentation.verified_source_policy import build_verified_source_policy_edits
from readme_agent.presentation.verified_template_document import (
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
        selected_fact=lambda field: (_ for _ in ()).throw(KeyError(field)),
        facts=[],
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


def test_unverified_link_prose_is_not_reinserted_or_claimed_as_partial_lineage() -> None:
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
    assert "Exact opening value before" not in candidate
    assert "Enterprise Edition and after it." not in candidate
    assert "external guidance" not in candidate
    assert all(term not in candidate for term in ("commercial On-Premise", "docs.aspose.com"))
    assert "kb.aspose.com" not in candidate
    assert candidate.count("products.aspose.org") == 1
    assert candidate.count("products.aspose.com") == 1
    assert not [
        binding
        for binding in plan.candidate_content_provenance
        if binding.provenance_id.startswith("source.policy.")
    ]
    assert not [
        resolution
        for resolution in plan.source_claim_resolutions
        if resolution.resolution == "presentation_policy_correction"
    ]
    assert any("claim accountability has" in item for item in validation.errors)
