"""Read-only intake classifies routes without accepting README claims."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.registry.intake import classify_readonly_intake, intake_contract_hash
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _entry(*, configured: bool = True, active: bool = True) -> ProductEntry:
    return ProductEntry(
        registry_schema_version=2,
        provider_identity={
            "provider": "github",
            "repository_id": 123,
            "node_id": "R_test",
        },
        family="example",
        platform="python",
        repo_name="Example",
        repo_url="https://github.com/example-org/Example",
        clone_url="https://github.com/example-org/Example.git",
        active=active,
        discovered_via="test",
        mode="disabled",
        ecosystem="python" if configured else None,
        policy_profile="example-python" if configured else None,
    )


def _snapshot(root: Path, readme: str | None) -> RepositorySnapshotV1:
    readme_hash = None
    if readme is not None:
        (root / "README.md").write_text(readme, encoding="utf-8")
        readme_hash = hashlib.sha256(readme.encode("utf-8")).hexdigest()
    return RepositorySnapshotV1(
        org_repo="example-org/Example",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        readme_path="README.md" if readme is not None else None,
        readme_sha256=readme_hash,
        inventory_sha256="b" * 64,
        captured_at="2026-07-29T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://github.com/example-org/Example.git",
            git_tree_sha256="b" * 64,
        ),
    )


def test_substantial_readme_is_only_fast_path_eligible(tmp_path):
    readme = """# Example

A repository-specific product explanation for developers.

## Installation

Install the package from the verified source.

## Quick start

```python
from example import Product
Product().run()
```

## Documentation

See the [API reference](https://example.invalid/reference).

## Contributing

Contributions are welcome under the repository policy.

## License

The project is MIT licensed.
""" + ("Repository-specific detail. " * 45)

    result = classify_readonly_intake(_entry(), _snapshot(tmp_path, readme))

    assert result.outcome == "READY_FAST_PATH"
    assert result.target_remote_effects_allowed is False
    assert result.target_local_effects_allowed is False
    assert result.signals is not None
    assert result.signals.code_block_count == 1
    assert "facts and independent approval remain mandatory" in result.reason


def test_short_or_missing_readme_uses_full_pipeline(tmp_path):
    short = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, "# Example\n\nSmall but valuable maintainer note.\n"),
    )
    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing = classify_readonly_intake(_entry(), _snapshot(missing_root, None))

    assert short.outcome == "READY_FULL_PIPELINE"
    assert missing.outcome == "READY_FULL_PIPELINE"


def test_unconfigured_repository_is_narrowly_blocked_without_write_authority(tmp_path):
    result = classify_readonly_intake(
        _entry(configured=False),
        _snapshot(tmp_path, "# Valuable existing README\n"),
    )

    assert result.outcome == "BLOCKED_CLASSIFICATION"
    assert result.target_remote_effects_allowed is False
    assert result.target_local_effects_allowed is False


def test_archived_repository_is_not_applicable(tmp_path):
    result = classify_readonly_intake(
        _entry(active=False),
        _snapshot(tmp_path, "# Archived\n"),
    )
    assert result.outcome == "NOT_APPLICABLE"


def test_unknown_ecosystem_is_an_explicit_unsupported_block(tmp_path):
    entry = _entry()
    entry = entry.model_copy(update={"ecosystem": "unknown"})

    result = classify_readonly_intake(entry, _snapshot(tmp_path, "# Unknown\n"))

    assert result.outcome == "BLOCKED_UNSUPPORTED"


@pytest.mark.parametrize(
    "ecosystem",
    ["python", "net", "java", "cpp", "typescript", "rust", "go"],
)
def test_every_supported_ecosystem_enters_a_readme_route(tmp_path, ecosystem):
    root = tmp_path / ecosystem
    root.mkdir()
    entry = _entry().model_copy(
        update={
            "platform": ecosystem,
            "ecosystem": ecosystem,
            "policy_profile": f"example-{ecosystem}",
        }
    )

    result = classify_readonly_intake(
        entry,
        _snapshot(root, f"# {ecosystem}\n\nValuable maintainer context.\n"),
    )

    assert result.outcome == "READY_FULL_PIPELINE"


def test_classification_configuration_change_invalidates_the_contract():
    blocked = _entry(configured=False)
    configured = _entry(configured=True)

    assert intake_contract_hash(blocked) != intake_contract_hash(configured)
