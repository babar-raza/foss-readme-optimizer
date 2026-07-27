"""Live Docker proof for Java, .NET, C++, and Go public README consumers."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from readme_agent.facts import (
    cpp_example_verifier,
    dotnet_example_verifier,
    go_example_verifier,
    java_example_verifier,
)
from readme_agent.facts.repository_examples import repository_readme_example_candidates
from readme_agent.registry.loader import load_products
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import capture_repository_snapshot

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is unavailable"),
]

BASELINE_ROOT = Path("runs/baseline")


def _failure_detail(result) -> str:
    execution = result.isolated_execution
    if execution is None:
        return result.detail
    return (
        f"{result.detail}\n"
        f"return_code={execution.return_code}\n"
        f"stdout_tail={execution.stdout[-2000:]}\n"
        f"stderr_tail={execution.stderr[-4000:]}"
    )


def _entry(org_repo: str):
    return next(entry for entry in load_products() if entry.org_repo == org_repo)


def _snapshot(org_repo: str):
    entry = _entry(org_repo)
    root = BASELINE_ROOT / org_repo.replace("/", "__")
    return capture_repository_snapshot(entry, root)


@pytest.mark.parametrize(
    ("org_repo", "language", "verifier"),
    [
        (
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
            "java",
            java_example_verifier.verify,
        ),
        (
            "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
            "dotnet",
            dotnet_example_verifier.verify,
        ),
        (
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
            "cpp",
            cpp_example_verifier.verify,
        ),
    ],
)
def test_repository_readme_consumer_compiles_in_network_denied_container(
    org_repo, language, verifier
):
    snapshot = _snapshot(org_repo)
    candidates = repository_readme_example_candidates(snapshot.root_path, language)
    assert candidates

    result = verifier(snapshot, candidates[0])

    assert result.truth_eligible, _failure_detail(result)
    assert result.outcome == "SOURCE_BUILD_VERIFIED"
    assert result.compiled_consumer is not None
    assert result.compiled_consumer.accepted
    assert result.verified_public_symbols
    assert result.isolated_execution is not None
    assert result.isolated_execution.policy.network_mode == "none"
    assert result.isolated_execution.cleanup.complete
    assert result.isolated_execution.environment_names
    assert not any(
        marker in name.upper()
        for name in result.isolated_execution.environment_names
        for marker in ("TOKEN", "SECRET", "PASSWORD", "AUTH", "KEY")
    )


def test_repository_owned_go_example_compiles_in_network_denied_container():
    org_repo = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go"
    snapshot = _snapshot(org_repo)
    source_path = "_examples/text_extraction/main.go"
    code = (snapshot.root_path / source_path).read_text(encoding="utf-8")
    example = MinimalExamplePolicy(
        language="go",
        class_name="readme_example",
        code=code,
        evidence_paths=[source_path],
        required_symbols=['pdf.Open("testdata/binder1.pdf")'],
    )

    result = go_example_verifier.verify(snapshot, example)

    assert result.truth_eligible, _failure_detail(result)
    assert result.outcome == "SOURCE_BUILD_VERIFIED"
    assert result.compiled_consumer is not None
    assert result.compiled_consumer.accepted
    assert result.verified_public_symbols
    assert result.isolated_execution is not None
    assert result.isolated_execution.policy.network_mode == "none"
    assert result.isolated_execution.cleanup.complete
