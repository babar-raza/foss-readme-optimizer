"""Fact-owned Aspose target validation tests."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.catalog_documentation import catalog_documentation_fact
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.catalog import load_aspose_link_catalogs, normalize_target_url
from readme_agent.links.fact_owned_targets import accepted_fact_owned_targets
from readme_agent.registry.loader import require_listed

ROOT = Path(__file__).resolve().parents[2]
ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"


def _facts_with_real_documentation() -> ProductFactsV2:
    base = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "readmes"
            / "verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    fact = catalog_documentation_fact(require_listed(ORG_REPO))
    assert fact is not None
    payload = base.model_dump(mode="json")
    payload["org_repo"] = ORG_REPO
    payload["facts"] = [item for item in payload["facts"] if item["field"] != "documentation.links"]
    payload["facts"].append(fact.model_dump(mode="json"))
    payload["selected_fact_ids"][fact.field] = fact.fact_id
    identity_id = payload["selected_fact_ids"]["product.identity"]
    identity = next(item for item in payload["facts"] if item["fact_id"] == identity_id)
    identity["value"] = {
        **identity["value"],
        "family": "3d",
        "platform": "python",
        "repository": ORG_REPO,
    }
    return ProductFactsV2.model_validate(payload)


def test_exact_source_catalog_documentation_targets_are_fact_owned() -> None:
    targets = accepted_fact_owned_targets(
        _facts_with_real_documentation(),
        load_aspose_link_catalogs(),
    )

    assert set(targets) == {
        normalize_target_url("https://docs.aspose.org/3d/python/"),
        normalize_target_url("https://kb.aspose.org/3d/python/"),
        normalize_target_url("https://reference.aspose.org/3d/python/"),
    }
    assert {target.fact_id for target in targets.values()} == {
        "documentation.links:governed-aspose-org-catalog"
    }


def test_catalog_or_product_mismatch_fails_closed() -> None:
    facts = _facts_with_real_documentation()
    payload = facts.model_dump(mode="json")
    fact_id = payload["selected_fact_ids"]["documentation.links"]
    documentation = next(item for item in payload["facts"] if item["fact_id"] == fact_id)
    documentation["value"][0]["record_id"] = "org:docs:3d:python:not-the-record"

    assert not accepted_fact_owned_targets(
        ProductFactsV2.model_validate(payload),
        load_aspose_link_catalogs(),
    )
