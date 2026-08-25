"""Regression tests for contextual verification of inherited C++ fragments."""

from __future__ import annotations

from types import SimpleNamespace

from readme_agent.facts.cpp_repository_fragments import verified_cpp_readme_fragments
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(tmp_path) -> RepositorySnapshotV1:
    package = tmp_path / "package"
    include = package / "include" / "aspose" / "sample"
    include.mkdir(parents=True)
    (package / "src").mkdir()
    (package / "CMakeLists.txt").write_text("project(sample)\n", encoding="utf-8")
    for name in ("FragmentType", "ReturnCollection", "Workbook", "Worksheet"):
        (include / f"{name}.h").write_text("#pragma once\n", encoding="utf-8")
    return RepositorySnapshotV1(
        org_repo="example/sample",
        source_revision="a" * 40,
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="b" * 64,
        captured_at="2026-08-25T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://github.com/example/sample.git",
            git_tree_sha256="b" * 64,
        ),
    )


def _base_example() -> MinimalExamplePolicy:
    return MinimalExamplePolicy(
        language="cpp",
        class_name="ReadmeExample",
        code=(
            '#include "aspose/sample/Workbook.h"\n'
            '#include "aspose/sample/Worksheet.h"\n\n'
            "using namespace Aspose::Sample;\n\n"
            "int main() {\n"
            "    Workbook workbook;\n"
            "    Worksheet& sheet = workbook.GetSheet();\n"
            "    return 0;\n"
            "}\n"
        ),
        evidence_paths=["README.md"],
    )


def test_verified_cpp_fragments_preserve_exact_source_after_harness_acceptance(tmp_path) -> None:
    calls = []

    def verify(example):
        calls.append(example)
        assert '#include "aspose/sample/FragmentType.h"' in example.code
        assert '#include "aspose/sample/Workbook.h"' in example.code
        assert '#include "aspose/sample/Worksheet.h"' in example.code
        assert "Workbook workbook;" in example.code
        assert "Worksheet& sheet = workbook.GetSheet();" in example.code
        return SimpleNamespace(
            truth_eligible=True,
            outcome="SOURCE_BUILD_VERIFIED",
            public_api_sha256="c" * 64,
            compiled_consumer=SimpleNamespace(example_sha256="d" * 64),
            example_compile=SimpleNamespace(stderr=""),
        )

    fragment = MinimalExamplePolicy(
        language="cpp",
        class_name="readme_example",
        code="sheet.Apply(FragmentType::Value);\n",
        evidence_paths=["README.md"],
    )
    result = verified_cpp_readme_fragments(
        _snapshot(tmp_path),
        [fragment],
        base_example=_base_example(),
        verify_example_fn=verify,
    )

    assert len(calls) == 1
    assert result[0]["code"] == fragment.code
    assert result[0]["static_api_verified"] is True
    assert result[0]["contextual_harness_sha256"]


def test_verified_cpp_fragments_add_forward_declared_headers_before_acceptance(tmp_path) -> None:
    calls = []

    def verify(example):
        calls.append(example)
        if len(calls) == 1:
            return SimpleNamespace(
                truth_eligible=False,
                outcome="BUILD_FAILED",
                compiled_consumer=None,
                example_compile=SimpleNamespace(
                    stderr="invalid use of incomplete type 'class Aspose::Sample::ReturnCollection'"
                ),
            )
        assert '#include "aspose/sample/ReturnCollection.h"' in example.code
        return SimpleNamespace(
            truth_eligible=True,
            outcome="SOURCE_BUILD_VERIFIED",
            public_api_sha256="c" * 64,
            compiled_consumer=SimpleNamespace(example_sha256="d" * 64),
            example_compile=SimpleNamespace(stderr=""),
        )

    fragment = MinimalExamplePolicy(
        language="cpp",
        class_name="readme_example",
        code="auto values = sheet.GetValues();\n",
        evidence_paths=["README.md"],
    )
    result = verified_cpp_readme_fragments(
        _snapshot(tmp_path),
        [fragment],
        base_example=_base_example(),
        verify_example_fn=verify,
    )

    assert len(calls) == 2
    assert len(result) == 1


def test_verified_cpp_fragments_fail_closed_without_harness_acceptance(tmp_path) -> None:
    def reject(_example):
        return SimpleNamespace(
            truth_eligible=False,
            outcome="BUILD_FAILED",
            compiled_consumer=None,
            example_compile=SimpleNamespace(stderr="syntax error"),
        )

    fragment = MinimalExamplePolicy(
        language="cpp",
        class_name="readme_example",
        code="sheet.Apply(FragmentType::Value);\n",
        evidence_paths=["README.md"],
    )

    assert (
        verified_cpp_readme_fragments(
            _snapshot(tmp_path),
            [fragment],
            base_example=_base_example(),
            verify_example_fn=reject,
        )
        == []
    )
