"""Prove CMake development commands come only from real manifest evidence."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.curated_cmake_development import repository_cmake_development_commands
from readme_agent.facts.curated_repository_guidance import repository_development_commands

_TEST_PROJECT = """
cmake_minimum_required(VERSION 3.16)
project(Aspose.Cells.Foss.Cpp.Tests LANGUAGES CXX)

enable_testing()

option(ASPOSE_CELLS_FOSS_TESTS_USE_SYSTEM_GTEST
    "Use an installed GTest package instead of FetchContent" OFF)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip)
FetchContent_MakeAvailable(googletest)

add_executable(aspose_cells_foss_cpp_tests tests/WorkbookPortingTests.cpp)
add_test(NAME unit COMMAND aspose_cells_foss_cpp_tests)
"""

_SAMPLES_PROJECT = """
cmake_minimum_required(VERSION 3.16)
project(Aspose.Cells.Foss.Cpp.Samples LANGUAGES CXX)

file(GLOB_RECURSE SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")
add_executable(${PROJECT_NAME} ${SOURCE})
target_link_libraries(${PROJECT_NAME} PRIVATE aspose_cells_foss)
"""

_LIBRARY_PROJECT = """
cmake_minimum_required(VERSION 3.16)
project(Aspose.Cells.Foss.Cpp LANGUAGES CXX)

add_library(aspose_cells_foss src/Workbook.cpp)
"""


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_test_project_yields_ctest_command_with_pinned_dependency(tmp_path: Path) -> None:
    _write(tmp_path, "Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt", _TEST_PROJECT)

    value, locations = repository_cmake_development_commands(tmp_path)
    entry = value["entries"][0]

    assert entry["kind"] == "cmake_test_project"
    assert entry["working_directory"] == "Aspose.Cells.Foss.Cpp.Tests"
    assert entry["commands"] == [
        "cmake -S . -B build",
        "cmake --build build",
        "ctest --test-dir build --output-on-failure",
    ]
    assert entry["cmake_minimum_version"] == "3.16"
    assert entry["executables"] == ["aspose_cells_foss_cpp_tests"]
    assert entry["fetched_dependencies"] == [
        {
            "name": "googletest",
            "version": "v1.14.0",
            "url": "https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip",
        }
    ]
    assert entry["options"] == ["ASPOSE_CELLS_FOSS_TESTS_USE_SYSTEM_GTEST"]
    # Nothing is executed to derive these commands.
    assert entry["execution_verified"] is False
    assert entry["evidence_kind"] == "source_derived"
    assert locations == ["Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt"]


def test_executable_named_by_project_variable_is_resolved(tmp_path: Path) -> None:
    _write(tmp_path, "samples/CMakeLists.txt", _SAMPLES_PROJECT)

    value, _locations = repository_cmake_development_commands(tmp_path)
    entry = value["entries"][0]

    assert entry["kind"] == "cmake_build_project"
    assert entry["executables"] == ["Aspose.Cells.Foss.Cpp.Samples"]
    # A project with no registered test never gets a ctest command.
    assert entry["commands"] == ["cmake -S . -B build", "cmake --build build"]


def test_library_only_project_is_not_a_development_entry_point(tmp_path: Path) -> None:
    _write(tmp_path, "Aspose.Cells.Foss.Cpp/CMakeLists.txt", _LIBRARY_PROJECT)

    assert repository_cmake_development_commands(tmp_path) is None


def test_enable_testing_without_a_registered_test_yields_no_ctest(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "harness/CMakeLists.txt",
        "cmake_minimum_required(VERSION 3.16)\n"
        "project(Harness LANGUAGES CXX)\n"
        "enable_testing()\n"
        "add_executable(harness main.cpp)\n",
    )

    value, _locations = repository_cmake_development_commands(tmp_path)
    entry = value["entries"][0]

    assert entry["kind"] == "cmake_build_project"
    assert "ctest --test-dir build --output-on-failure" not in entry["commands"]


def test_unpinned_fetchcontent_dependency_is_not_reported(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "tests/CMakeLists.txt",
        "cmake_minimum_required(VERSION 3.16)\n"
        "project(T LANGUAGES CXX)\n"
        "enable_testing()\n"
        "include(FetchContent)\n"
        "FetchContent_Declare(dep GIT_REPOSITORY https://example.invalid/dep.git)\n"
        "add_executable(t main.cpp)\n"
        "add_test(NAME t COMMAND t)\n",
    )

    value, _locations = repository_cmake_development_commands(tmp_path)

    assert "fetched_dependencies" not in value["entries"][0]


def test_deeply_nested_vendored_project_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "third_party/vendor/gtest/CMakeLists.txt", _TEST_PROJECT)

    assert repository_cmake_development_commands(tmp_path) is None


def test_repository_without_any_build_manifest_has_no_commands(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Product\n", encoding="utf-8")

    assert repository_development_commands(tmp_path) is None


def test_guidance_seam_falls_back_to_cmake_for_a_non_python_repository(tmp_path: Path) -> None:
    _write(tmp_path, "Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt", _TEST_PROJECT)

    result = repository_development_commands(tmp_path)

    assert result is not None
    value, _locations = result
    assert value["entries"][0]["kind"] == "cmake_test_project"


def test_guidance_seam_still_prefers_an_existing_python_layout(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.0"\n', encoding="utf-8"
    )
    package = tmp_path / "src/demo"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    _write(tmp_path, "Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt", _TEST_PROJECT)

    result = repository_development_commands(tmp_path)

    assert result is not None
    value, _locations = result
    kinds = {entry["kind"] for entry in value["entries"]}
    assert "cmake_test_project" not in kinds
    assert "editable_install" in kinds


def test_command_is_a_complete_runnable_sequence(tmp_path: Path) -> None:
    """The rendered `command` is emitted verbatim as one shell block, so it
    must include the working directory and configure step -- a bare
    `ctest --test-dir build` does not work from the repository root."""

    _write(tmp_path, "Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt", _TEST_PROJECT)

    value, _locations = repository_cmake_development_commands(tmp_path)

    assert value["entries"][0]["command"] == (
        "cd Aspose.Cells.Foss.Cpp.Tests\n"
        "cmake -S . -B build\n"
        "cmake --build build\n"
        "ctest --test-dir build --output-on-failure"
    )


def test_root_level_project_needs_no_directory_change(tmp_path: Path) -> None:
    _write(tmp_path, "CMakeLists.txt", _TEST_PROJECT)

    value, _locations = repository_cmake_development_commands(tmp_path)
    entry = value["entries"][0]

    assert entry["working_directory"] == "."
    assert not entry["command"].startswith("cd ")


def test_command_collectors_dispatch_by_declared_ecosystem(tmp_path: Path) -> None:
    """CORE-035: each build-system collector must be reachable only from the
    ecosystem that owns it, so registering it in the fact-acceptance contract
    keeps its edits from invalidating every other ecosystem's cached facts."""

    _write(tmp_path, "Aspose.Cells.Foss.Cpp.Tests/CMakeLists.txt", _TEST_PROJECT)

    assert repository_development_commands(tmp_path, ecosystem="cpp") is not None
    for foreign in ("java", "rust", "go", "typescript", "net", "python"):
        assert repository_development_commands(tmp_path, ecosystem=foreign) is None


def test_cmake_collector_is_scoped_out_of_foreign_ecosystem_contracts() -> None:
    from readme_agent.facts import acceptance_contract as contract

    owning = [
        name
        for name, files in contract._COMPONENT_FILES.items()
        if "curated_cmake_development.py" in files
    ]
    assert owning, "the CMake collector must stay registered in the fact contract"
    for component in owning:
        cpp = contract._scoped_component_files(component, "cpp", "cells")
        java = contract._scoped_component_files(component, "java", "cells")
        assert "curated_cmake_development.py" in cpp
        assert "curated_cmake_development.py" not in java
