"""Select and verify seven ecosystem examples for public-example evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from readme_agent.facts.example_quality import strip_source_comments
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.repository_examples import (
    repository_readme_example_candidates,
    repository_source_example_candidates,
)
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.registry.priority import load_platform_priority
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
_PRIORITY_TO_REPRESENTATIVE = {"net": "dotnet"}

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


def ordered_representative_ecosystems() -> list[str]:
    """Return the governed platform order restricted to this seven-repository proof."""

    return [
        representative
        for ecosystem in load_platform_priority().execution_order
        if (representative := _PRIORITY_TO_REPRESENTATIVE.get(ecosystem, ecosystem))
        in REPRESENTATIVES
    ]


def _readme_example(root: Path, ecosystem: str) -> MinimalExamplePolicy:
    candidates = repository_readme_example_candidates(root, ecosystem)
    if not candidates:
        raise RuntimeError(f"{ecosystem} representative has no README example candidate")
    return candidates[0]


def _selected_example(root: Path, ecosystem: str) -> tuple[MinimalExamplePolicy, str, str]:
    if ecosystem == "python":
        return (
            _PYTHON_EXAMPLE,
            "repository-source-backed correction of stale README example",
            (
                "reject curated README import because the installed package cannot load "
                "aspose.threed.formats.collada; reuse only source-and-package-verified symbols"
            ),
        )
    if ecosystem == "typescript":
        return (
            _TYPESCRIPT_EXAMPLE,
            "repository-source-backed correction of stale README import",
            (
                "reject curated README package roots because the compiler cannot resolve them; "
                "use the compiler-resolved built-package import"
            ),
        )
    if ecosystem == "go":
        candidates = repository_source_example_candidates(root, "go")
        if not candidates:
            raise RuntimeError("Go representative has no complete repository source example")
        return (
            candidates[0],
            "repository-owned example source",
            (
                "curated README fragments are not complete programs; reuse the repository-owned "
                "complete comment-free example only after source and consumer compilation"
            ),
        )
    curated = _readme_example(root, ecosystem)
    comment_free = curated.model_copy(
        update={"code": strip_source_comments(ecosystem, curated.code)}
    )
    return (
        comment_free,
        "curated repository README",
        (
            "reuse validated code after removing comments; preserve all executable bytes "
            "subject to public-symbol and compiler acceptance"
        ),
    )


def verify_representatives(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the canonical verifier for one real example in every ecosystem."""

    results: dict[str, Any] = {}
    controls: dict[str, Any] = {}
    roots = representative_roots(repo_root)
    for ecosystem in ordered_representative_ecosystems():
        org_repo = REPRESENTATIVES[ecosystem]
        root = roots[ecosystem]
        snapshot = capture_repository_snapshot(require_listed(org_repo), root)
        example, origin, disposition = _selected_example(root, ecosystem)
        result = verify_local_product_example(snapshot, example)
        results[ecosystem] = {
            "example_origin": origin,
            "curated_content_disposition": disposition,
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
            "curated_content_disposition": "reject as stale and require evidence-backed correction",
            "example": curated.model_dump(mode="json"),
            "verification": result.model_dump(mode="json"),
        }

    return results, controls


def example_summary(results: dict[str, Any]) -> dict[str, Any]:
    """Project large typed records into an inspectable portfolio index."""

    summary: dict[str, Any] = {}
    for ecosystem in ordered_representative_ecosystems():
        item = results[ecosystem]
        verification = item["verification"]
        execution = verification["isolated_execution"]
        summary[ecosystem] = {
            "org_repo": verification["org_repo"],
            "source_revision": verification["source_revision"],
            "example_origin": item["example_origin"],
            "curated_content_disposition": item["curated_content_disposition"],
            "outcome": verification["outcome"],
            "truth_eligible": verification["truth_eligible"],
            "verified_public_symbols": verification["verified_public_symbols"],
            "immutable_image": execution["policy"]["immutable_image"],
            "dependency_inputs": verification["acquisition_dependency_pins"],
            "network_mode": execution["policy"]["network_mode"],
            "cleanup_complete": all(execution["cleanup"].values()),
        }
    return summary


def remove_obsolete_combined_evidence(evidence_dir: Path) -> None:
    """Remove only the superseded large-file layout before writing split records."""

    for name in ("example-verifications.json", "example-verifications.json.tmp"):
        path = evidence_dir / name
        if path.is_file():
            path.unlink()
