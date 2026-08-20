"""Read-only intake classifies routes without accepting README claims."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.registry.intake import classify_readonly_intake, intake_contract_hash
from readme_agent.registry.loader import find_entry, load_policy
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


def _snapshot(
    root: Path,
    readme: str | None,
    *,
    revision: str = "a" * 40,
    substantive: bool = True,
) -> RepositorySnapshotV1:
    """`substantive=True` (the default) writes one ordinary source file
    alongside any README, so existing routing-focused fixtures continue to
    represent a genuinely processable repository under the tree-shape gate
    (`registry/intake.py::classify_readonly_intake`'s new
    `BLOCKED_NO_SUBSTANTIVE_CONTENT` branch). Tests that specifically exercise
    that gate pass `substantive=False` and construct the tree by hand."""

    readme_hash = None
    if readme is not None:
        (root / "README.md").write_text(readme, encoding="utf-8")
        readme_hash = hashlib.sha256(readme.encode("utf-8")).hexdigest()
    if substantive:
        (root / "example_source.py").write_text("value = 1\n", encoding="utf-8")
    return RepositorySnapshotV1(
        org_repo="example-org/Example",
        source_revision=revision,
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


def test_empty_repository_is_terminally_unprocessable(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()

    result = classify_readonly_intake(_entry(), _snapshot(root, None, substantive=False))

    assert result.outcome == "BLOCKED_NO_SUBSTANTIVE_CONTENT"
    assert "empty" in result.reason
    assert result.target_remote_effects_allowed is False
    assert result.target_local_effects_allowed is False


def test_readme_only_is_terminally_unprocessable(tmp_path):
    result = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, "# Only a README\n", substantive=False),
    )

    assert result.outcome == "BLOCKED_NO_SUBSTANTIVE_CONTENT"
    assert "README" in result.reason


@pytest.mark.parametrize("license_name", ["LICENSE", "COPYING", "NOTICE"])
def test_readme_plus_license_variant_is_terminally_unprocessable(tmp_path, license_name):
    (tmp_path / license_name).write_text("Permissive license text.\n", encoding="utf-8")

    result = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, "# Example\n", substantive=False),
    )

    assert result.outcome == "BLOCKED_NO_SUBSTANTIVE_CONTENT"
    assert "LICENSE" in result.reason


@pytest.mark.parametrize("license_name", ["LICENSE", "COPYING", "NOTICE"])
def test_license_variant_only_without_readme_is_terminally_unprocessable(tmp_path, license_name):
    (tmp_path / license_name).write_text("Permissive license text.\n", encoding="utf-8")

    result = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, None, substantive=False),
    )

    assert result.outcome == "BLOCKED_NO_SUBSTANTIVE_CONTENT"


def test_readme_plus_one_substantive_file_is_processable(tmp_path):
    result = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, "# Example\n\nShort note.\n", substantive=True),
    )

    assert result.outcome == "READY_FULL_PIPELINE"


def test_substantive_repository_without_license_is_processable(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "module.py").write_text("value = 1\n", encoding="utf-8")

    result = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, "# Example\n\nShort note.\n", substantive=False),
    )

    assert result.outcome == "READY_FULL_PIPELINE"
    assert not (tmp_path / "LICENSE").exists()


def test_nested_substantive_file_is_processable(tmp_path):
    nested = tmp_path / "src" / "pkg" / "deep"
    nested.mkdir(parents=True)
    (nested / "module.py").write_text("value = 1\n", encoding="utf-8")

    result = classify_readonly_intake(
        _entry(),
        _snapshot(tmp_path, None, substantive=False),
    )

    assert result.outcome == "READY_FULL_PIPELINE"


def test_processability_reevaluates_when_source_revision_changes(tmp_path):
    """A repo that is README-only at one pinned revision and gains a
    substantive file at a later revision must classify each snapshot on its
    own tree -- no outcome is carried over from one `source_revision` to
    another (the real cache/dedup key downstream is keyed on exactly this
    field, per `state/readme_poc_intake.py::intake_preflight_dedup_key`)."""

    old_root = tmp_path / "old"
    old_root.mkdir()
    old_snapshot = _snapshot(old_root, "# Example\n", revision="a" * 40, substantive=False)

    new_root = tmp_path / "new"
    new_root.mkdir()
    new_snapshot = _snapshot(new_root, "# Example\n", revision="b" * 40, substantive=True)

    entry = _entry()
    old_result = classify_readonly_intake(entry, old_snapshot)
    new_result = classify_readonly_intake(entry, new_snapshot)

    assert old_result.outcome == "BLOCKED_NO_SUBSTANTIVE_CONTENT"
    assert new_result.outcome == "READY_FULL_PIPELINE"
    assert old_result.source_revision != new_result.source_revision
    assert old_result.canonical_hash() != new_result.canonical_hash()
    # Contract hash is unaffected by tree content -- revision alone carries
    # the content-change signal into the downstream dedup key.
    assert old_result.contract_hash == new_result.contract_hash == intake_contract_hash(entry)


def test_real_psd_registry_entries_are_terminally_unprocessable(tmp_path):
    """Live proof the generic shape rule, not a PSD-specific branch, is what
    fires: a real registry entry (loaded the same way production code does)
    whose pinned tree is exactly one file, `README.md` -- the actual shape of
    both live PSD repositories per the 2026-08-20 registry-processability
    audit."""

    for org_repo in (
        "aspose-psd-foss/Aspose.PSD-FOSS-for-.NET",
        "aspose-psd-foss/Aspose.PSD-FOSS-for-Python",
    ):
        entry = find_entry(org_repo)
        assert entry is not None
        load_policy(entry.policy_profile)  # real policy profile resolves; not read by the gate

        root = tmp_path / entry.repo_name
        root.mkdir()

        snapshot = _snapshot(root, "# FOSS placeholder\n", substantive=False)
        result = classify_readonly_intake(entry, snapshot)

        assert result.outcome == "BLOCKED_NO_SUBSTANTIVE_CONTENT"


def test_real_3d_typescript_registry_entry_is_processable_without_license(tmp_path):
    """Live proof that missing LICENSE never blocks a real, substantive
    registry entry -- `3d/typescript`'s real live shape per the same audit
    (190 files, 0 LICENSE-class files, 188 substantive)."""

    entry = find_entry("aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript")
    assert entry is not None
    load_policy(entry.policy_profile)

    root = tmp_path / entry.repo_name
    (root / "src").mkdir(parents=True)
    (root / "src" / "index.ts").write_text("export const value = 1;\n", encoding="utf-8")

    snapshot = _snapshot(root, "# 3D for TypeScript\n", substantive=False)
    result = classify_readonly_intake(entry, snapshot)

    assert result.outcome != "BLOCKED_NO_SUBSTANTIVE_CONTENT"
    assert not (root / "LICENSE").exists()
