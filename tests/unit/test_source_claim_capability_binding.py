"""Prove fail-closed feature-detail matching at the public dispatcher seam."""

from __future__ import annotations

from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.source_claim_structured_matching import (
    structured_source_claim_fact_ids,
)
from tests.unit.test_source_claim_structured_matching_exact import _facts


def _slides_api_facts():
    facts = _facts(["Verified presentation processing"])
    api = facts.selected_fact("api.public_surface")
    members = {
        "Presentation": ["save", "slides", "images", "source_format"],
        "SlideCollection": [
            "add_clone",
            "add_empty_slide",
            "remove",
            "remove_at",
            "to_array",
            "as_i_enumerable",
        ],
        "LineFormat": [
            "width",
            "dash_style",
            "begin_arrowhead_style",
            "join_style",
            "alignment",
        ],
        "Comment": ["author", "created_time", "parent_comment", "position"],
        "Images": ["from_file", "from_stream"],
        "ImageCollection": ["add_image"],
        "PPImage": ["binary_data", "replace_image"],
    }
    value = {
        "classes": [
            {
                "name": name,
                "module": "aspose.slides",
                "members": [{"name": member} for member in class_members],
            }
            for name, class_members in members.items()
        ]
    }
    replacement = api.model_copy(update={"value": value})
    return facts.model_copy(
        update={
            "facts": [replacement if fact.fact_id == api.fact_id else fact for fact in facts.facts]
        }
    )


def _ids(source: str, capability: str) -> set[str]:
    facts = _facts([capability])
    claim = assess_material_claims(source)[0]
    text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    return structured_source_claim_fact_ids(source, claim, text, facts)


def test_feature_detail_rejects_near_semantic_capability() -> None:
    source = "# Product\n\n## Features\n\n- Render imaginary widgets\n"

    assert _ids(source, "Render verified widgets") == set()


def test_feature_detail_rejects_unknown_technical_identifier() -> None:
    source = "# Product\n\n## Features\n\n- Render with `UnknownWidget`\n"

    assert _ids(source, "Render with Widget") == set()


def test_feature_detail_accepts_distinct_public_api_helper_names() -> None:
    source = "# Product\n\n## Features\n\n- Use Widget and Renderer helpers\n"
    facts = _facts(["Render verified widgets"])
    claim = assess_material_claims(source)[0]
    text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()

    assert structured_source_claim_fact_ids(source, claim, text, facts) == {
        facts.selected_fact("api.public_surface").fact_id
    }


def test_feature_detail_accepts_complete_public_api_member_entailment() -> None:
    facts = _slides_api_facts()
    api_id = facts.selected_fact("api.public_surface").fact_id

    for detail in (
        "**Lines** — Width, dash style, arrows, join and alignment",
        "**Comments** — Threaded comments with authors, timestamps, and positions",
        "**Images** — Embed from file, bytes, or stream",
    ):
        source = f"# Product\n\n## Features\n\n- {detail}\n"
        claim = assess_material_claims(source)[0]
        text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
        assert structured_source_claim_fact_ids(source, claim, text, facts) == {api_id}


def test_feature_detail_rejects_any_unsupported_api_member_or_qualifier() -> None:
    facts = _slides_api_facts()

    for detail in (
        "**Slides** — Add, remove, clone, reorder, and iterate slides",
        "**Presentation I/O** — Open, create, and save `.pptx` files with full round-trip fidelity",
    ):
        source = f"# Product\n\n## Features\n\n- {detail}\n"
        claim = assess_material_claims(source)[0]
        text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
        assert structured_source_claim_fact_ids(source, claim, text, facts) == set()
