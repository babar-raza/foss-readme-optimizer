"""Repository-bound license paths and readable license presentation."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.license_location import repository_license_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts() -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = proof["current_pilots"][0]
    return (
        ProductFactsV2.model_validate(pilot["product_facts_v2"]),
        pilot["snapshot"]["source_revision"],
    )


def _with_license_location(facts: ProductFactsV2, location: str) -> ProductFactsV2:
    selected = facts.selected_fact("product.license")
    replacement = selected.model_copy(
        update={"source": selected.source.model_copy(update={"location": location})}
    )
    return facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == selected.fact_id else fact for fact in facts.facts
            ]
        }
    )


def test_license_badge_and_prose_use_the_verified_repository_path():
    facts, revision = _facts()
    facts = _with_license_location(facts, "repository://LICENSE.txt")
    source = """# Product

## License

[MIT](LICENSE.txt).
"""

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )

    assert plan.header_visuals is not None
    license_badge = next(badge for badge in plan.header_visuals.badges if badge.kind == "license")
    assert license_badge.target_url == "LICENSE.txt"
    assert "[MIT License](LICENSE.txt)" in candidate
    assert "permits use, modification, distribution, and commercial use" in candidate
    assert "\n[MIT](LICENSE.txt).\n" not in candidate
    assert "](LICENSE)" not in candidate


def test_unsafe_or_external_license_locations_fall_back_to_conventional_path():
    facts, _revision = _facts()
    license_fact = facts.selected_fact("product.license")

    for location in (
        "https://example.test/LICENSE",
        "repository://../LICENSE",
        "repository://C:/secrets/LICENSE",
        "repository://LICENSE.txt?raw=1",
    ):
        changed = license_fact.model_copy(
            update={"source": license_fact.source.model_copy(update={"location": location})}
        )
        assert repository_license_path(changed) == "LICENSE"


def test_license_location_encodes_safe_repository_filenames():
    facts, _revision = _facts()
    license_fact = facts.selected_fact("product.license")
    changed = license_fact.model_copy(
        update={
            "source": license_fact.source.model_copy(
                update={"location": "repository://legal/MIT License.txt"}
            )
        }
    )

    assert repository_license_path(changed) == "legal/MIT%20License.txt"
