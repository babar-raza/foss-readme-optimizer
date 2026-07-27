"""TypeScript package/export layout and pinned toolchain contracts."""

from __future__ import annotations

import hashlib
import json

import pytest

from readme_agent.ecosystems.typescript_api_schema import TypeScriptConsumerExampleV1
from readme_agent.ecosystems.typescript_package_layout import (
    inspect_typescript_package_layout,
)
from readme_agent.facts import typescript_consumer, typescript_toolchain
from readme_agent.facts.typescript_consumer import prove_typescript_consumer
from readme_agent.facts.typescript_toolchain import (
    TypeScriptToolchainArtifactV1,
    TypeScriptToolchainLockV1,
    ensure_typescript_toolchain,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_export_map_prefers_declarations_and_blocks_undeclared_subpaths(tmp_path):
    _write_json(
        tmp_path / "package.json",
        {
            "name": "@scope/widget",
            "version": "1.2.3",
            "main": "./wrong/root.js",
            "types": "./wrong/root.d.ts",
            "exports": {
                ".": {
                    "types": "./dist/index.d.ts",
                    "import": "./dist/index.js",
                    "require": "./dist/index.cjs",
                },
                "./feature": {
                    "types": "./dist/feature.d.ts",
                    "default": "./dist/feature.js",
                },
                "./features/*": "./dist/features/*.js",
            },
        },
    )
    _write_json(
        tmp_path / "tsconfig.json",
        {"compilerOptions": {"rootDir": "src", "outDir": "dist"}},
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("export class Widget {}", encoding="utf-8")

    layout = inspect_typescript_package_layout(tmp_path)

    assert layout.exports_restrict_subpaths is True
    assert layout.canonical_import == "@scope/widget"
    assert [entry.import_specifier for entry in layout.entry_points] == [
        "@scope/widget",
        "@scope/widget/feature",
    ]
    assert layout.entry_points[0].declaration_path == "./dist/index.d.ts"
    assert layout.entry_points[0].runtime_path == "./dist/index.js"
    assert layout.entry_points[0].declaration_preferred is True
    assert "types" in layout.entry_points[0].conditions
    assert layout.unsupported_export_patterns == ["./features/*"]


def test_legacy_source_indexes_project_to_built_deep_imports(tmp_path):
    _write_json(
        tmp_path / "package.json",
        {
            "name": "@scope/widget",
            "version": "1.2.3",
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
        },
    )
    _write_json(
        tmp_path / "tsconfig.json",
        {"compilerOptions": {"rootDir": "src", "outDir": "dist"}},
    )
    source = tmp_path / "src" / "vendor" / "widget"
    source.mkdir(parents=True)
    (source / "index.ts").write_text(
        "export class Widget { public value = 1; private _secret = 2; }",
        encoding="utf-8",
    )

    layout = inspect_typescript_package_layout(tmp_path)
    deep = next(entry for entry in layout.entry_points if entry.declared_by == "legacy_index")

    assert deep.import_specifier == "@scope/widget/dist/vendor/widget"
    assert deep.declaration_path == "dist/vendor/widget/index.d.ts"
    assert deep.runtime_path == "dist/vendor/widget/index.js"
    assert layout.canonical_import == deep.import_specifier


def test_wildcard_only_exports_are_typed_and_fail_closed_before_execution(tmp_path, monkeypatch):
    _write_json(
        tmp_path / "package.json",
        {
            "name": "@scope/widget",
            "exports": {"./features/*": "./dist/features/*.js"},
        },
    )
    _write_json(
        tmp_path / "tsconfig.json",
        {"compilerOptions": {"rootDir": "src", "outDir": "dist"}},
    )
    (tmp_path / "src").mkdir()
    package = inspect_typescript_package_layout(tmp_path)

    assert package.entry_points == []
    assert package.canonical_import is None
    assert package.unsupported_export_patterns == ["./features/*"]

    snapshot = RepositorySnapshotV1(
        org_repo="fixture/package",
        source_revision="1234567",
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="0" * 64,
        captured_at="2026-07-27T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/fixture/package.git",
            git_tree_sha256="0" * 64,
        ),
    )
    monkeypatch.setattr(typescript_consumer, "verify_repository_snapshot", lambda snapshot: None)
    example = TypeScriptConsumerExampleV1(
        import_specifier="@scope/widget/features/public",
        required_symbols=["Feature"],
        code=(
            "import { Feature } from '@scope/widget/features/public';\n"
            "const feature: Feature = new Feature();\n"
        ),
    )

    with pytest.raises(ValueError, match="no supported concrete export entry point"):
        prove_typescript_consumer(snapshot, package, example)


def test_pinned_toolchain_uses_existing_hash_verified_archives(tmp_path, monkeypatch):
    content = b"inert compiler archive"
    artifact = TypeScriptToolchainArtifactV1(
        name="typescript",
        version="1.0.0",
        filename="typescript.tgz",
        url="https://invalid.example/typescript.tgz",
        sha256=hashlib.sha256(content).hexdigest(),
    )
    monkeypatch.setattr(
        typescript_toolchain,
        "TOOLCHAIN_LOCK",
        TypeScriptToolchainLockV1(
            compiler_version="1.0.0",
            immutable_image=typescript_toolchain.NODE_22_IMAGE,
            artifacts=[artifact],
        ),
    )
    (tmp_path / artifact.filename).write_bytes(content)

    resolved = ensure_typescript_toolchain(tmp_path)

    assert resolved == {"typescript": tmp_path / artifact.filename}


def test_pinned_toolchain_rejects_archive_hash_mismatch(tmp_path, monkeypatch):
    artifact = TypeScriptToolchainArtifactV1(
        name="typescript",
        version="1.0.0",
        filename="typescript.tgz",
        url="https://invalid.example/typescript.tgz",
        sha256="0" * 64,
    )
    monkeypatch.setattr(
        typescript_toolchain,
        "TOOLCHAIN_LOCK",
        TypeScriptToolchainLockV1(
            compiler_version="1.0.0",
            immutable_image=typescript_toolchain.NODE_22_IMAGE,
            artifacts=[artifact],
        ),
    )
    (tmp_path / artifact.filename).write_bytes(b"tampered")

    with pytest.raises(ValueError, match="hash mismatch"):
        ensure_typescript_toolchain(tmp_path)


def test_consumer_rejects_wrong_subpath_before_toolchain_or_execution(tmp_path, monkeypatch):
    _write_json(
        tmp_path / "package.json",
        {
            "name": "fixture-package",
            "exports": {".": {"types": "./dist/index.d.ts"}},
        },
    )
    (tmp_path / "src").mkdir()
    package = inspect_typescript_package_layout(tmp_path)
    snapshot = RepositorySnapshotV1(
        org_repo="fixture/package",
        source_revision="1234567",
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="0" * 64,
        captured_at="2026-07-27T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/fixture/package.git",
            git_tree_sha256="0" * 64,
        ),
    )
    monkeypatch.setattr(typescript_consumer, "verify_repository_snapshot", lambda snapshot: None)
    example = TypeScriptConsumerExampleV1(
        import_specifier="fixture-package/private",
        required_symbols=["Secret"],
        code=(
            "import { Secret } from 'fixture-package/private';\n"
            "const secret: Secret = new Secret();\n"
        ),
    )

    with pytest.raises(ValueError, match="undeclared or inaccessible"):
        prove_typescript_consumer(snapshot, package, example)
