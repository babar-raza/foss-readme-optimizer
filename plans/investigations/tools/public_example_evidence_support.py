"""Select and verify seven ecosystem examples for public-example evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.repository_examples import repository_readme_example_candidates
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import capture_repository_snapshot

REPRESENTATIVES = {
    "cpp": "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
    "dotnet": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
    "go": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
    "java": "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "python": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    "rust": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
    "typescript": "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
}

_PYTHON_EXAMPLE = MinimalExamplePolicy(
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

_TYPESCRIPT_EXAMPLE = MinimalExamplePolicy(
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


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def representative_roots(repo_root: Path) -> dict[str, Path]:
    """Return the seven immutable baseline roots keyed by ecosystem."""

    return {
        ecosystem: repo_root / "runs/baseline" / org_repo.replace("/", "__")
        for ecosystem, org_repo in REPRESENTATIVES.items()
    }


def _readme_example(root: Path, ecosystem: str) -> MinimalExamplePolicy:
    candidates = repository_readme_example_candidates(root, ecosystem)
    if not candidates:
        raise RuntimeError(f"{ecosystem} representative has no README example candidate")
    return candidates[0]


def _selected_example(root: Path, ecosystem: str) -> tuple[MinimalExamplePolicy, str]:
    if ecosystem == "python":
        return _PYTHON_EXAMPLE, "repository-source-backed correction of stale README example"
    if ecosystem == "typescript":
        return _TYPESCRIPT_EXAMPLE, "repository-source-backed correction of stale README import"
    if ecosystem == "go":
        source_path = "_examples/text_extraction/main.go"
        return (
            MinimalExamplePolicy(
                language="go",
                class_name="readme_example",
                code=(root / source_path).read_text(encoding="utf-8"),
                evidence_paths=[source_path],
                required_symbols=['pdf.Open("testdata/binder1.pdf")'],
            ),
            "repository-owned example source",
        )
    return _readme_example(root, ecosystem), "curated repository README"


def verify_representatives(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the canonical verifier for one real example in every ecosystem."""

    results: dict[str, Any] = {}
    controls: dict[str, Any] = {}
    roots = representative_roots(repo_root)
    for ecosystem in sorted(REPRESENTATIVES):
        org_repo = REPRESENTATIVES[ecosystem]
        root = roots[ecosystem]
        snapshot = capture_repository_snapshot(require_listed(org_repo), root)
        example, origin = _selected_example(root, ecosystem)
        result = verify_local_product_example(snapshot, example)
        results[ecosystem] = {
            "example_origin": origin,
            "example": example.model_dump(mode="json"),
            "verification": result.model_dump(mode="json"),
            "repository_clean": not _git(root, "status", "--porcelain=v1"),
        }

    for ecosystem in ("python", "typescript"):
        org_repo = REPRESENTATIVES[ecosystem]
        root = roots[ecosystem]
        snapshot = capture_repository_snapshot(require_listed(org_repo), root)
        curated = _readme_example(root, ecosystem)
        result = verify_local_product_example(snapshot, curated)
        controls[f"stale_{ecosystem}_readme_example"] = {
            "example_origin": "curated repository README",
            "example": curated.model_dump(mode="json"),
            "verification": result.model_dump(mode="json"),
        }

    return results, controls
