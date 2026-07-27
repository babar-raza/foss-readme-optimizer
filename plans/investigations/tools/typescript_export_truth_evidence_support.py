"""Real-repository helpers for the TypeScript export-truth evidence builder."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.typescript_api_schema import TypeScriptConsumerExampleV1
from readme_agent.ecosystems.typescript_package_layout import inspect_typescript_package_layout
from readme_agent.facts.typescript_consumer import prove_typescript_consumer
from readme_agent.facts.typescript_toolchain import TOOLCHAIN_LOCK
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import capture_repository_snapshot

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
EXPECTED_IMPORT = "@aspose/3d/dist/aspose/threed"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def real_proof(
    representative: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Prove the built deep import and reject the stale declared root import."""

    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, representative)
    package = inspect_typescript_package_layout(representative)
    accepted_example = TypeScriptConsumerExampleV1(
        import_specifier=EXPECTED_IMPORT,
        required_symbols=["Node", "Node.childNodes", "Scene", "Scene.rootNode"],
        code=(
            f"import {{ Node, Scene }} from '{EXPECTED_IMPORT}';\n"
            "const scene: Scene = new Scene();\n"
            "const root: Node = scene.rootNode;\n"
            "const children: Node[] = root.childNodes;\n"
            "console.log(children.length);\n"
        ),
    )
    accepted = prove_typescript_consumer(snapshot, package, accepted_example)
    stale_example = TypeScriptConsumerExampleV1(
        import_specifier="@aspose/3d",
        required_symbols=["Scene"],
        code=(
            "import { Scene } from '@aspose/3d';\n"
            "const scene: Scene = new Scene();\n"
            "console.log(scene.rootNode);\n"
        ),
    )
    stale = prove_typescript_consumer(snapshot, package, stale_example)
    return (
        {
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "inventory_sha256": snapshot.inventory_sha256,
            "baseline_tree_clean": not _git(representative, "status", "--porcelain=v1"),
            "baseline_head": _git(representative, "rev-parse", "HEAD"),
        },
        accepted.model_dump(mode="json"),
        stale.model_dump(mode="json"),
    )


def docker_inventory() -> dict[str, list[str]]:
    """Return managed Docker resources still present after proof execution."""

    containers = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "label=readme-agent=true"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    volumes = subprocess.run(
        ["docker", "volume", "ls", "-q", "--filter", "label=readme-agent=true"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    return {"containers": sorted(containers), "volumes": sorted(volumes)}


def immutable_image() -> str:
    """Return the exact Node image used by the isolated consumer."""

    return TOOLCHAIN_LOCK.immutable_image
