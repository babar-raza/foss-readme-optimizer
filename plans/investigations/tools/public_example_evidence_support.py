"""Build seven real public-example cases and curated-content dispositions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.repository_examples import repository_readme_example_candidates
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, capture_repository_snapshot

ExampleOrigin = Literal["curated_readme", "repository_source", "evidence_backed_correction"]

REPRESENTATIVES = {
    "java": "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "dotnet": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
    "cpp": "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
    "go": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
    "python": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    "typescript": "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    "rust": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
}


@dataclass(frozen=True)
class PublicExampleCase:
    """One exact example plus its reuse/correction origin."""

    ecosystem: str
    snapshot: RepositorySnapshotV1
    example: MinimalExamplePolicy
    origin: ExampleOrigin
    disposition: str


def _snapshot(repository_root: Path, ecosystem: str) -> RepositorySnapshotV1:
    org_repo = REPRESENTATIVES[ecosystem]
    root = repository_root / "runs/baseline" / org_repo.replace("/", "__")
    return capture_repository_snapshot(require_listed(org_repo), root)


def _readme_case(repository_root: Path, ecosystem: str) -> PublicExampleCase:
    snapshot = _snapshot(repository_root, ecosystem)
    candidates = repository_readme_example_candidates(snapshot.root_path, ecosystem)
    if not candidates:
        raise ValueError(f"{ecosystem} representative has no curated README example")
    return PublicExampleCase(
        ecosystem=ecosystem,
        snapshot=snapshot,
        example=candidates[0],
        origin="curated_readme",
        disposition="reuse_unchanged_after_public_api_and_compiler_acceptance",
    )


def _go_case(repository_root: Path) -> PublicExampleCase:
    snapshot = _snapshot(repository_root, "go")
    source_path = "_examples/text_extraction/main.go"
    code = (snapshot.root_path / source_path).read_text(encoding="utf-8")
    return PublicExampleCase(
        ecosystem="go",
        snapshot=snapshot,
        example=MinimalExamplePolicy(
            language="go",
            class_name="readme_example",
            code=code,
            evidence_paths=[source_path],
            required_symbols=['pdf.Open("testdata/binder1.pdf")'],
        ),
        origin="repository_source",
        disposition=(
            "curated_readme_fragments_are_incomplete_programs; reuse_repository_owned_complete_"
            "example_after_compilation"
        ),
    )


def _python_case(repository_root: Path) -> PublicExampleCase:
    snapshot = _snapshot(repository_root, "python")
    return PublicExampleCase(
        ecosystem="python",
        snapshot=snapshot,
        example=MinimalExamplePolicy(
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
        ),
        origin="evidence_backed_correction",
        disposition=(
            "curated_readme_example_rejected_because_installed_package_cannot_import_"
            "aspose.threed.formats.collada; use_source_and_installed_package_verified_symbols"
        ),
    )


def _typescript_case(repository_root: Path) -> PublicExampleCase:
    snapshot = _snapshot(repository_root, "typescript")
    return PublicExampleCase(
        ecosystem="typescript",
        snapshot=snapshot,
        example=MinimalExamplePolicy(
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
        ),
        origin="evidence_backed_correction",
        disposition=(
            "curated_readme_root_and_format_imports_are_not_compiler_resolved; "
            "use_the_built_package_canonical_import"
        ),
    )


def public_example_cases(repository_root: Path) -> list[PublicExampleCase]:
    """Return deterministic representative cases in ecosystem order."""

    return [
        _readme_case(repository_root, "java"),
        _readme_case(repository_root, "dotnet"),
        _python_case(repository_root),
        _typescript_case(repository_root),
        _readme_case(repository_root, "cpp"),
        _go_case(repository_root),
        _readme_case(repository_root, "rust"),
    ]


def curated_rejection_controls(repository_root: Path) -> dict[str, LocalProductVerificationV1]:
    """Execute stale curated Python/TypeScript examples and retain typed rejections."""

    controls: dict[str, LocalProductVerificationV1] = {}
    for ecosystem in ("python", "typescript"):
        snapshot = _snapshot(repository_root, ecosystem)
        candidate = repository_readme_example_candidates(snapshot.root_path, ecosystem)[0]
        controls[ecosystem] = verify_local_product_example(snapshot, candidate)
    return controls


def run_public_example_cases(
    repository_root: Path,
) -> tuple[list[PublicExampleCase], dict[str, LocalProductVerificationV1]]:
    """Run every selected example through the canonical isolated verifier."""

    cases = public_example_cases(repository_root)
    return cases, {
        case.ecosystem: verify_local_product_example(case.snapshot, case.example) for case in cases
    }


def case_record(
    case: PublicExampleCase,
    result: LocalProductVerificationV1,
) -> dict[str, object]:
    """Build a compact provenance record while retaining full result separately."""

    execution = result.isolated_execution
    return {
        "ecosystem": case.ecosystem,
        "org_repo": case.snapshot.org_repo,
        "source_revision": case.snapshot.source_revision,
        "origin": case.origin,
        "disposition": case.disposition,
        "example_sha256": hashlib.sha256(case.example.code.encode("utf-8")).hexdigest(),
        "evidence_paths": case.example.evidence_paths,
        "required_symbols": case.example.required_symbols,
        "outcome": result.outcome,
        "truth_eligible": result.truth_eligible,
        "verified_public_symbols": result.verified_public_symbols,
        "immutable_image": execution.policy.immutable_image if execution else None,
        "network_mode": execution.policy.network_mode if execution else None,
        "command": execution.argv if execution else None,
        "return_code": execution.return_code if execution else None,
        "stdout_classification": "nonempty" if execution and execution.stdout else "empty",
        "stderr_classification": (
            "nonempty_success_diagnostics"
            if execution and execution.return_code == 0 and execution.stderr
            else "empty"
            if not execution or not execution.stderr
            else "failure_diagnostics"
        ),
        "dependency_inputs": result.acquisition_dependency_pins,
        "cleanup_complete": execution.cleanup.complete if execution else False,
    }
