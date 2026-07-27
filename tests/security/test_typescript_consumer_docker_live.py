"""Real TypeScript built-package consumer proof in the hardened Docker boundary."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from readme_agent.ecosystems.typescript_api_schema import TypeScriptConsumerExampleV1
from readme_agent.ecosystems.typescript_package_layout import (
    inspect_typescript_package_layout,
)
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.typescript_consumer import prove_typescript_consumer
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import capture_repository_snapshot

REPRESENTATIVE = Path(
    os.environ.get(
        "README_AGENT_TYPESCRIPT_REPRESENTATIVE",
        "runs/baseline/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript",
    )
)
ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"


def _commit_fixture(root: Path) -> None:
    for argv in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "fixture@example.invalid"],
        ["git", "config", "user.name", "Fixture"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "fixture"],
    ):
        subprocess.run(argv, cwd=root, check=True, capture_output=True, text=True)


@pytest.mark.live
def test_real_aspose_typescript_build_exposes_compiler_resolved_public_symbols():
    if not REPRESENTATIVE.is_dir():
        pytest.skip("real TypeScript baseline clone is unavailable")
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, REPRESENTATIVE)
    package = inspect_typescript_package_layout(REPRESENTATIVE)
    example = TypeScriptConsumerExampleV1(
        import_specifier="@aspose/3d/dist/aspose/threed",
        required_symbols=["Node", "Node.childNodes", "Scene", "Scene.rootNode"],
        code=(
            "import { Node, Scene } from '@aspose/3d/dist/aspose/threed';\n"
            "const scene: Scene = new Scene();\n"
            "const root: Node = scene.rootNode;\n"
            "const children: Node[] = root.childNodes;\n"
            "console.log(children.length);\n"
        ),
    )

    proof = prove_typescript_consumer(snapshot, package, example)

    assert proof.accepted is True, proof
    assert proof.surface is not None
    assert proof.surface.compiler_version == "5.8.3"
    assert proof.built_artifact_sha256 is not None
    assert set(proof.verified_symbols) == set(example.required_symbols)
    assert proof.isolated_execution.policy.network_mode == "none"
    assert proof.isolated_execution.cleanup.complete is True


@pytest.mark.live
def test_canonical_local_verifier_uses_the_isolated_typescript_consumer():
    if not REPRESENTATIVE.is_dir():
        pytest.skip("real TypeScript baseline clone is unavailable")
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, REPRESENTATIVE)
    example = MinimalExamplePolicy(
        language="typescript",
        class_name="readme_example",
        code=(
            "import { Node, Scene } from '@aspose/3d/dist/aspose/threed';\n"
            "const scene: Scene = new Scene();\n"
            "const root: Node = scene.rootNode;\n"
            "const children: Node[] = root.childNodes;\n"
            "console.log(children.length);\n"
        ),
        evidence_paths=["src/aspose/threed/Scene.ts", "src/aspose/threed/Node.ts"],
        required_symbols=["Scene", "Scene.rootNode", "Node", "Node.childNodes"],
    )

    verification = verify_local_product_example(snapshot, example)

    assert verification.outcome == "SOURCE_BUILD_VERIFIED", verification
    assert verification.truth_eligible is True
    assert verification.typescript_package is not None
    assert verification.typescript_package.canonical_import == "@aspose/3d/dist/aspose/threed"
    assert verification.isolated_execution is not None
    assert verification.isolated_execution.policy.network_mode == "none"
    assert verification.isolated_execution.cleanup.complete is True


@pytest.mark.live
def test_compiler_surface_covers_types_members_and_rejects_private_api(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (tmp_path / "package.json").write_text(
        '{"name":"fixture-package","version":"1.0.0",'
        '"main":"dist/index.js","types":"dist/index.d.ts",'
        '"exports":{".":{"types":"./dist/index.d.ts","require":"./dist/index.js"}}}',
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions":{"target":"ES2020","module":"commonjs",'
        '"declaration":true,"outDir":"dist","rootDir":"src","strict":true},'
        '"include":["src/**/*"]}',
        encoding="utf-8",
    )
    (source / "index.ts").write_text(
        "export interface Config { enabled: boolean }\n"
        "export type ID = string;\n"
        "export enum Mode { Fast, Safe }\n"
        "export function create(): Widget { return new Widget(); }\n"
        "export class Widget {\n"
        "  public readonly value = 1;\n"
        "  private secret = 2;\n"
        "  protected hidden = 3;\n"
        "  #hard = 4;\n"
        "  public run(): Mode { return Mode.Fast; }\n"
        "}\n",
        encoding="utf-8",
    )
    stale = tmp_path / "dist"
    stale.mkdir()
    (stale / "index.d.ts").write_text("export declare class Stale {}\n", encoding="utf-8")
    _commit_fixture(tmp_path)
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, tmp_path)
    package = inspect_typescript_package_layout(tmp_path)
    accepted_example = TypeScriptConsumerExampleV1(
        import_specifier="fixture-package",
        required_symbols=[
            "Config",
            "Config.enabled",
            "ID",
            "Mode",
            "Mode.Fast",
            "Widget",
            "Widget.run",
            "Widget.value",
            "create",
        ],
        code=(
            "import { Config, ID, Mode, Widget, create } from 'fixture-package';\n"
            "const config: Config = { enabled: true };\n"
            "const id: ID = 'fixture';\n"
            "const widget: Widget = create();\n"
            "const mode: Mode = widget.run();\n"
            "console.log(config.enabled, id, mode === Mode.Fast, widget.value);\n"
        ),
    )

    accepted = prove_typescript_consumer(snapshot, package, accepted_example)

    assert accepted.accepted is True, accepted
    assert accepted.surface is not None
    names = {symbol.qualified_name for symbol in accepted.surface.symbols}
    assert set(accepted_example.required_symbols) <= names
    assert {"Stale", "Widget.secret", "Widget.hidden", "Widget.#hard"}.isdisjoint(names)

    private_example = TypeScriptConsumerExampleV1(
        import_specifier="fixture-package",
        required_symbols=["Widget", "Widget.secret"],
        code=(
            "import { Widget } from 'fixture-package';\n"
            "const widget = new Widget();\n"
            "console.log(widget.secret);\n"
        ),
    )
    rejected = prove_typescript_consumer(snapshot, package, private_example)
    assert rejected.accepted is False
    assert "Widget.secret" in rejected.missing_symbols
    assert any("private" in diagnostic.lower() for diagnostic in rejected.diagnostics)


@pytest.mark.live
def test_real_stale_root_declaration_is_rejected():
    if not REPRESENTATIVE.is_dir():
        pytest.skip("real TypeScript baseline clone is unavailable")
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, REPRESENTATIVE)
    package = inspect_typescript_package_layout(REPRESENTATIVE)
    stale_root = TypeScriptConsumerExampleV1(
        import_specifier="@aspose/3d",
        required_symbols=["Scene"],
        code=(
            "import { Scene } from '@aspose/3d';\n"
            "const scene: Scene = new Scene();\n"
            "console.log(scene.rootNode);\n"
        ),
    )

    proof = prove_typescript_consumer(snapshot, package, stale_root)

    assert proof.accepted is False
    assert "Scene" in proof.missing_symbols
    assert any("cannot find module" in diagnostic.lower() for diagnostic in proof.diagnostics)
