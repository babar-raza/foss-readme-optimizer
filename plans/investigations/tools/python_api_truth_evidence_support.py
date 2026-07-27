"""Real-repository helpers for the Python public API evidence builder."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.python_public_api import inspect_python_public_api
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import capture_repository_snapshot

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
PYTHON_IMAGE = "python@sha256:13f0881a239ca0d27fb8b2539536ace85f7d680a707bfaa178571e1dbfe85a91"


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
    entry = require_listed(ORG_REPO)
    snapshot = capture_repository_snapshot(entry, representative)
    surface = inspect_python_public_api(
        snapshot.root_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    example = MinimalExamplePolicy(
        language="python",
        class_name="readme_example",
        code=(
            "from aspose.threed import Node, Scene\n\n"
            "scene = Scene()\n"
            'node = Node("README proof")\n'
            "assert scene.root_node is not None\n"
            'assert node.name == "README proof"\n'
            "assert node.child_nodes == []\n"
        ),
        evidence_paths=["aspose/threed/Scene.py", "aspose/threed/Node.py"],
        required_symbols=["Scene", "Node", "Scene.root_node", "Node.child_nodes"],
    )
    verification = verify_local_product_example(snapshot, example)
    return (
        {
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "inventory_sha256": snapshot.inventory_sha256,
            "baseline_tree_clean": not _git(representative, "status", "--porcelain=v1"),
            "baseline_head": _git(representative, "rev-parse", "HEAD"),
        },
        surface.model_dump(mode="json"),
        verification.model_dump(mode="json"),
    )


def docker_inventory() -> dict[str, list[str]]:
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
