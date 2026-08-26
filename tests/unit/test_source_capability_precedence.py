"""Prove authored capability prose yields to strictly better-bound source bullets."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_capability_precedence import (
    authored_cluster_loses_source_facts,
    source_capability_bullet_fact_ids,
)

ROOT = Path(__file__).resolve().parents[2]
CPP = ROOT / "runs/readme-poc/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp"
CPP_REV = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"


def _cpp() -> tuple[str, ProductFactsV2] | None:
    facts_path = CPP / CPP_REV / "facts/product-facts.json"
    source_path = CPP / CPP_REV / "source/README.md"
    if not facts_path.is_file() or not source_path.is_file():
        return None
    return (
        source_path.read_text(encoding="utf-8"),
        ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8")),
    )


def test_source_without_capability_bullets_never_takes_precedence() -> None:
    """A README with no Key Capabilities bullets must leave authoring untouched."""

    facts_bundle = _cpp()
    if facts_bundle is None:  # pragma: no cover - canary artifacts absent
        return
    _source, facts = facts_bundle
    plain = "# Product\n\n## Installation\n\nInstall it.\n"

    assert source_capability_bullet_fact_ids(plain, facts) == frozenset()
    assert not authored_cluster_loses_source_facts(plain, facts, ())


def test_authored_prose_yields_when_it_binds_fewer_facts() -> None:
    """PF05 cpp canary: the source bullets bind product.capabilities *and*
    product.problems_solved, so authored prose binding only the former is a net
    loss of grounding and must not replace them."""

    facts_bundle = _cpp()
    if facts_bundle is None:  # pragma: no cover - canary artifacts absent
        return
    source, facts = facts_bundle

    bound = {
        facts.fact_by_id(fact_id).field
        for fact_id in source_capability_bullet_fact_ids(source, facts)
    }
    assert "product.capabilities" in bound
    assert "product.problems_solved" in bound

    assert authored_cluster_loses_source_facts(source, facts, ("product.capabilities",))


def test_authored_prose_is_kept_when_it_binds_everything_the_source_does() -> None:
    """The rule is about lost grounding, not about preferring source on principle."""

    facts_bundle = _cpp()
    if facts_bundle is None:  # pragma: no cover - canary artifacts absent
        return
    source, facts = facts_bundle

    assert not authored_cluster_loses_source_facts(
        source,
        facts,
        ("product.capabilities", "product.problems_solved"),
    )
