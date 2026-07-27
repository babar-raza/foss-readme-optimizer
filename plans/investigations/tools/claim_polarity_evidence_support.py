"""Build reproducible real-repository evidence for directional fact claims."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from readme_agent.facts.evidence_polarity import (
    EvidencePolarityAssessmentV1,
    ExpectedEvidencePolarity,
    assess_evidence_polarity,
)

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
SCENE_PATH = "src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs"
LIMITATIONS_PATH = "docs/release-26.2.0.md"


def _git(repository_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository_root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _assessment(
    *,
    repository_root: Path,
    source_revision: str,
    path: str,
    anchor: str,
    claim: str,
    expected: ExpectedEvidencePolarity,
    fact_id: str,
) -> EvidencePolarityAssessmentV1:
    result = assess_evidence_polarity(
        root=repository_root,
        evidence_paths=[path],
        anchor=anchor,
        fact_id=fact_id,
        claim_text=claim,
        expected_polarity=expected,
        source_revision=source_revision,
        observed_at=None,
    )
    if result is None:
        raise RuntimeError(f"real evidence anchor was not found: {path}: {anchor}")
    return result


def build_evidence(repository_root: Path, implementation_root: Path) -> dict[str, Any]:
    """Evaluate positive, constraint, and opposite-polarity real .NET controls."""

    source_revision = _git(repository_root, "rev-parse", "HEAD")
    implementation_revision = _git(implementation_root, "rev-parse", "HEAD")
    cases = {
        "render_stub_is_constraint": _assessment(
            repository_root=repository_root,
            source_revision=source_revision,
            path=SCENE_PATH,
            anchor="This feature is not available in the FOSS version.",
            claim="Scene.Render is not available in the FOSS version.",
            expected="explicit_constraint",
            fact_id="product.limitations:repository-evidence",
        ),
        "positive_render_symbol_cannot_prove_capability": _assessment(
            repository_root=repository_root,
            source_revision=source_revision,
            path=SCENE_PATH,
            anchor="public void Render(Entities.Camera camera, string fileName)",
            claim="Render scenes.",
            expected="positive_implementation",
            fact_id="product.capabilities:repository-evidence",
        ),
        "repository_limitations_statement_is_constraint": _assessment(
            repository_root=repository_root,
            source_revision=source_revision,
            path=LIMITATIONS_PATH,
            anchor=(
                "The `Scene.Render()` method throws `NotImplementedException` "
                "- use On-Premise for rendering functionality"
            ),
            claim="Scene.Render throws NotImplementedException.",
            expected="explicit_constraint",
            fact_id="product.limitations:repository-evidence",
        ),
        "scene_constructor_is_positive_implementation": _assessment(
            repository_root=repository_root,
            source_revision=source_revision,
            path=SCENE_PATH,
            anchor="public Scene() : base()",
            claim="Construct a Scene.",
            expected="positive_implementation",
            fact_id="product.capabilities:repository-evidence",
        ),
    }
    expected_acceptance = {
        "render_stub_is_constraint": True,
        "positive_render_symbol_cannot_prove_capability": False,
        "repository_limitations_statement_is_constraint": True,
        "scene_constructor_is_positive_implementation": True,
    }
    failures = [
        case_id
        for case_id, accepted in expected_acceptance.items()
        if cases[case_id].accepted is not accepted
    ]
    return {
        "schema_version": 1,
        "task_id": "L8-TRUTH-03-CLAIM-POLARITY",
        "repository": ORG_REPO,
        "source_revision": source_revision,
        "implementation_revision": implementation_revision,
        "repository_worktree_clean": _git(repository_root, "status", "--short") == "",
        "cases": {
            case_id: assessment.model_dump(mode="json")
            for case_id, assessment in sorted(cases.items())
        },
        "expected_acceptance": expected_acceptance,
        "failures": failures,
        "verdict": "VERIFIED" if not failures else "FAILED",
    }
