"""Tests for current-revision verified truth retention during recollection."""

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.facts.verified_truth_retention import retain_current_verified_truth

CURRENT_REVISION = "b" * 40
PRIOR_REVISION = "a" * 40


def _fact(*, revision: str, state: str, suffix: str) -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"product.formats:{suffix}",
        field="product.formats",
        value=["Output format: XML"] if state == "verified" else {"reason": "unavailable"},
        source=FactSourceV2(
            source_type=(
                "approved_documentation" if state == "verified" else "mechanical_repository"
            ),
            location=f"evidence://{suffix}",
            source_revision=revision,
        ),
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state == "verified" else 0.0,
        affected_surfaces=["readme.capabilities"],
    )


def _base(fact: FactRecordV2) -> ProductFactsV2:
    return ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo="acme/widget",
        facts=[fact],
        selected_fact_ids={fact.field: fact.fact_id},
        package_root_roles=None,
    )


def test_unavailable_recollection_does_not_erase_current_verified_truth() -> None:
    verified = _fact(revision=CURRENT_REVISION, state="verified", suffix="knowledge")
    blocked = _fact(revision=CURRENT_REVISION, state="blocked", suffix="native")
    replacements = {"product.formats": blocked}

    retain_current_verified_truth(_base(verified), replacements, fields=("product.formats",))

    assert replacements["product.formats"] is verified


def test_stale_verified_truth_does_not_replace_current_observation() -> None:
    stale = _fact(revision=PRIOR_REVISION, state="verified", suffix="knowledge")
    blocked = _fact(revision=CURRENT_REVISION, state="blocked", suffix="native")
    replacements = {"product.formats": blocked}

    retain_current_verified_truth(_base(stale), replacements, fields=("product.formats",))

    assert replacements["product.formats"] is blocked


def test_verified_recollection_is_not_overwritten() -> None:
    established = _fact(revision=CURRENT_REVISION, state="verified", suffix="knowledge")
    replacement = _fact(revision=CURRENT_REVISION, state="verified", suffix="native")
    replacements = {"product.formats": replacement}

    retain_current_verified_truth(_base(established), replacements, fields=("product.formats",))

    assert replacements["product.formats"] is replacement
