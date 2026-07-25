"""Run-scoped ProductFactsV2 propagation and repository isolation."""

from __future__ import annotations

import pytest

from readme_agent.capabilities import render_readme_candidate
from readme_agent.facts.context import current_product_facts, product_facts_scope
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


def _facts(org_repo: str = "acme/widget") -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location=f"repository://{org_repo}",
        source_revision="a" * 40,
    )
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "context-test"),
            field=field,
            value={"field": field},
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo=org_repo,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def test_product_facts_scope_restores_prior_context_and_rejects_cross_repo_access():
    facts = _facts()
    assert current_product_facts() is None

    with product_facts_scope(facts):
        assert current_product_facts("acme/widget") is facts
        with pytest.raises(RuntimeError, match="belong to"):
            current_product_facts("other/repository")

    assert current_product_facts() is None


def test_canonical_renderer_consumes_the_run_scoped_graph(monkeypatch):
    facts = _facts()
    observed = {}

    monkeypatch.setattr(render_readme_candidate, "find_entry", lambda org_repo: None)

    def prepare(org_repo, product_facts):
        observed["org_repo"] = org_repo
        observed["facts"] = product_facts
        return {"status": "GENERATED"}

    monkeypatch.setattr(render_readme_candidate, "prepare_idea_fidelity_candidate", prepare)

    with product_facts_scope(facts):
        result = render_readme_candidate.execute("acme/widget")

    assert result["status"] == "GENERATED"
    assert observed == {"org_repo": "acme/widget", "facts": facts}
