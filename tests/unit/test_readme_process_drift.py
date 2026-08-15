"""T3 -- drift test: docs/readme-process.md's stated facts must never
silently diverge from what the live check registry actually derives."""

from __future__ import annotations

import re
from pathlib import Path

from readme_agent.validation.aspose_checks import load_check_registry

_DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "readme-process.md"


def test_doc_exists_and_is_not_empty():
    assert _DOC_PATH.is_file()
    assert len(_DOC_PATH.read_text(encoding="utf-8")) > 100


def test_doc_stated_check_count_matches_the_live_derived_registry():
    """The doc states the count in one specific, greppable form
    ('**N**') precisely so this test can catch it drifting -- see
    resolution 7: the count is derived, never a binding constant, and
    that includes the DOCUMENTATION of the count, not just the code."""

    registry = load_check_registry()
    text = _DOC_PATH.read_text(encoding="utf-8")

    match = re.search(r"\*\*(\d+)\*\* checks", text)
    assert match is not None, "docs/readme-process.md must state the count as '**N** checks'"
    documented_count = int(match.group(1))

    assert documented_count == len(registry), (
        f"docs/readme-process.md claims {documented_count} checks, "
        f"the live registry derives {len(registry)} -- the doc has drifted"
    )


def test_doc_references_the_real_registry_module_path():
    text = _DOC_PATH.read_text(encoding="utf-8")

    assert "readme_agent.validation.aspose_checks" in text
    assert "load_check_registry" in text


def test_doc_references_the_real_fixture_coverage_test_module():
    """If this test file is ever renamed, the doc's claim about it becomes
    stale -- catch that here rather than let prose silently drift from
    what actually exists on disk."""

    text = _DOC_PATH.read_text(encoding="utf-8")
    referenced_test_file = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "unit"
        / "test_aspose_checks_fixture_coverage.py"
    )

    assert "test_aspose_checks_fixture_coverage.py" in text
    assert referenced_test_file.is_file()
