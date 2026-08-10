"""Exact repository resource-link binding regressions."""

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.readme.source_claim_repository_asset_binding import (
    repository_asset_source_claim_fact_ids,
)


def _facts() -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://PUBLIC_API.md,CHANGELOG.md,examples/example.py",
        source_revision="a" * 40,
    )
    documentation = FactRecordV2(
        fact_id="repository.documentation_assets:test",
        field="repository.documentation_assets",
        value={
            "entries": [
                {"path": "PUBLIC_API.md", "sha256": "b" * 64},
                {"path": "CHANGELOG.md", "sha256": "c" * 64},
            ]
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.documentation"],
    )
    examples = FactRecordV2(
        fact_id="repository.examples:test",
        field="repository.examples",
        value={"files": [{"path": "examples/example.py", "sha256": "d" * 64}]},
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.examples"],
    )
    return ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo="example/product",
        facts=[documentation, examples],
        selected_fact_ids={
            documentation.field: documentation.fact_id,
            examples.field: examples.fact_id,
        },
        package_root_roles=None,
    )


def test_checksum_bound_resource_sentences_bind_every_relative_target() -> None:
    text = (
        "For the stable API summary, see [PUBLIC_API.md](PUBLIC_API.md).\n"
        "For runnable scenarios, see [examples](examples).\n"
    )

    assert repository_asset_source_claim_fact_ids(text, _facts()) == {
        "repository.documentation_assets:test",
        "repository.examples:test",
    }


def test_unknown_or_remote_resource_target_fails_closed() -> None:
    assert not repository_asset_source_claim_fact_ids("See [unknown](UNKNOWN.md).", _facts())
    assert not repository_asset_source_claim_fact_ids(
        "See [remote](https://attacker.invalid/resource).", _facts()
    )
