"""Prove exact structured capability and public-API source-claim binding."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.curated_readme_evidence import curated_repository_fact_candidates
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding
from readme_agent.readme.source_claim_structured_matching import (
    structured_source_claim_fact_ids,
)

_NOTE_REVISION = "6d97a522a9ed24708687911f1aabb76e2dea2da7"
_NOTE_FEATURE_OFFSETS = (1120, 1174, 1255, 1280, 1354, 1400, 1442, 1485, 1562, 1626)
_NOTE_API_OFFSETS = (
    3848,
    4018,
    4228,
    4266,
    4353,
    4445,
    4558,
    4613,
    4876,
    4960,
    5213,
    5272,
    5944,
    5979,
    6346,
    6832,
    6882,
    6963,
    7020,
    7077,
    7213,
    7832,
    7935,
    7977,
    8014,
    8043,
    8108,
    8168,
    8214,
    8311,
    8333,
    8395,
    8446,
    8674,
)


def _api_class(name: str, *surfaces: str) -> dict:
    return {
        "name": name,
        "module": "acme",
        "qualified_name": f"acme.{name}",
        "bases": [],
        "constructor": None,
        "members": [
            {
                "name": surface.split("(", 1)[0].split(":", 1)[0],
                "surface": surface,
                "return_annotation": None,
                "declared_by": name,
                "inherited": False,
                "source_path": f"src/acme/{name.casefold()}.py",
                "source_sha256": "a" * 64,
                "line": index + 2,
            }
            for index, surface in enumerate(surfaces)
        ],
        "source_path": f"src/acme/{name.casefold()}.py",
        "source_sha256": "b" * 64,
        "line": 1,
    }


def _facts(
    capability_values: list[str],
    *,
    api_state: str = "verified",
) -> ProductFactsV2:
    base = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    original_capability = base.selected_fact("product.capabilities")
    capability = original_capability.model_copy(
        update={"verification_state": "verified", "value": capability_values}
    )
    api = FactRecordV2(
        fact_id="api.public_surface:exact-structured-test",
        field="api.public_surface",
        value={
            "modules": [
                {
                    "module": "acme",
                    "exports": ["Widget", "Renderer"],
                    "source_path": "src/acme/__init__.py",
                }
            ],
            "classes": [
                _api_class("Widget", "render(target)"),
                _api_class("Renderer", "save(target)"),
            ],
        },
        source=base.selected_fact("product.identity").source,
        verification_state=api_state,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    return base.model_copy(
        update={
            "facts": [
                capability if fact.fact_id == original_capability.fact_id else fact
                for fact in base.facts
            ]
            + [api],
            "selected_fact_ids": {
                **base.selected_fact_ids,
                "api.public_surface": api.fact_id,
            },
        }
    )


def _structured_ids(source: str, facts: ProductFactsV2, *, claim_index: int = 0) -> set[str]:
    claim = assess_material_claims(source)[claim_index]
    text = source.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    return structured_source_claim_fact_ids(source, claim, text, facts)


def test_exact_capability_class_list_binds_capability_and_api_coordinates() -> None:
    source = "- `Widget`, `Renderer`\n"
    facts = _facts(["Widget, Renderer"])

    binding = complete_source_claim_fact_binding(source, assess_material_claims(source)[0], facts)

    assert binding is not None
    assert binding.fact_ids == frozenset(
        {
            facts.selected_fact_ids["product.capabilities"],
            facts.selected_fact_ids["api.public_surface"],
        }
    )
    assert {coordinate.path for coordinate in binding.fact_coordinates} >= {
        "/classes/Widget",
        "/classes/Renderer",
    }
    assert any(coordinate.path.startswith("/items/") for coordinate in binding.fact_coordinates)


def test_exact_nested_member_binds_only_when_member_surface_matches() -> None:
    source = "- `Widget`\n  - `render(target)`\n"
    facts = _facts(["render(target)"])

    assert _structured_ids(source, facts, claim_index=1) == {
        facts.selected_fact_ids["product.capabilities"],
        facts.selected_fact_ids["api.public_surface"],
    }

    unsupported = "- `Widget`\n  - `remove(target)`\n"
    unsupported_facts = _facts(["remove(target)"])
    assert _structured_ids(unsupported, unsupported_facts, claim_index=1) == set()


def test_capability_similarity_never_substitutes_for_exact_value() -> None:
    facts = _facts(["Render verified widgets"])

    assert _structured_ids("- Render production widgets\n", facts) == set()

    punctuation_changed = _facts(["Widget render target"])
    assert _structured_ids("- `Widget.render(target)`\n", punctuation_changed) == set()


def test_technical_capability_fails_closed_without_accepted_api_fact() -> None:
    source = "- `Widget`\n"
    facts = _facts(["Widget"], api_state="unverified")

    assert _structured_ids(source, facts) == set()


def test_exact_nontechnical_capability_binds_without_api_fact() -> None:
    source = "- Render verified widgets\n"
    facts = _facts(["Render verified widgets"], api_state="unverified")

    assert _structured_ids(source, facts) == {facts.selected_fact_ids["product.capabilities"]}


def test_feature_prose_cannot_match_format_facts_through_ordinary_words() -> None:
    source = (
        "# Product\n\n## Key Capabilities\n\n"
        "Maintainer-specific deployment note with no verified fact.\n"
    )
    facts = _facts(["Render verified widgets"])

    assert _structured_ids(source, facts) == set()


def test_current_note_feature_and_api_deferrals_have_accepted_fact_ids() -> None:
    root = Path(__file__).resolve().parents[2]
    repository = root / "runs/baseline/aspose-note-foss__Aspose.Note-FOSS-for-Python"
    facts_path = (
        root
        / "runs/readme-poc/aspose-note-foss__Aspose.Note-FOSS-for-Python"
        / _NOTE_REVISION
        / "facts/product-facts.json"
    )
    if not repository.is_dir() or not facts_path.is_file():
        pytest.skip("current real-Note offline proof artifacts are not present")

    source = (repository / "README.md").read_text(encoding="utf-8")
    assert hashlib.sha256(source.encode()).hexdigest() == (
        "180a16f74735201783dd7db5987cae2bed9cf619b51f28f8528b386b531177d4"
    )
    base = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    curated = curated_repository_fact_candidates(
        repository,
        _NOTE_REVISION,
        None,
        ecosystem="python",
    )
    replacements = {fact.field: fact for fact in curated}
    facts = ProductFactsV2.model_validate(
        {
            **base.model_dump(mode="python"),
            "facts": [fact for fact in base.facts if fact.field not in replacements]
            + list(replacements.values()),
            "selected_fact_ids": {
                **base.selected_fact_ids,
                **{field: fact.fact_id for field, fact in replacements.items()},
            },
        }
    )
    claims = {claim.source_byte_start: claim for claim in assess_material_claims(source)}

    bindings = {
        offset: complete_source_claim_fact_binding(source, claims[offset], facts)
        for offset in (*_NOTE_FEATURE_OFFSETS, *_NOTE_API_OFFSETS)
    }

    assert len(_NOTE_FEATURE_OFFSETS) == 10
    assert len(_NOTE_API_OFFSETS) == 34
    assert all(binding is not None and binding.fact_ids for binding in bindings.values())
