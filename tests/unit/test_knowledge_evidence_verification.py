"""Item-level, polarity-aware evidence content verification -- the seam
`aspose_knowledge_selection.py` calls to decide whether a claim's cited
evidence actually supports or contradicts it, never merely whether the
cited file exists."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.knowledge_evidence_verification import evidence_content_signal


def test_evidence_content_signal_positive_implementation(tmp_path: Path):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n    def export(self):\n        return b'ok'\n", encoding="utf-8"
    )

    signal = evidence_content_signal(
        ({"file": "widget.py", "line": 2},), tmp_path, claim_kind="format_support"
    )

    assert signal == "positive"


def test_evidence_content_signal_negative_stub(tmp_path: Path):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n    def export(self):\n        raise NotImplementedError\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "widget.py", "line": 2},), tmp_path, claim_kind="format_support"
    )

    assert signal == "negative"


def test_evidence_content_signal_class_level_citation_all_stub_methods_is_negative(
    tmp_path: Path,
):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n"
        "    def export(self):\n"
        "        raise NotImplementedError\n\n"
        "    def export_to_stream(self):\n"
        "        raise NotImplementedError\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "widget.py", "line": 1},), tmp_path, claim_kind="format_support"
    )

    assert signal == "negative"


def test_evidence_content_signal_class_level_citation_all_real_methods_is_positive(
    tmp_path: Path,
):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n"
        "    def export(self):\n"
        "        return b'ok'\n\n"
        "    def export_to_stream(self, stream):\n"
        "        stream.write(b'ok')\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "widget.py", "line": 1},), tmp_path, claim_kind="format_support"
    )

    assert signal == "positive"


def test_evidence_content_signal_class_level_citation_mixed_methods_is_unresolved(
    tmp_path: Path,
):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n"
        "    def export(self):\n"
        "        return b'ok'\n\n"
        "    def export_to_stream(self):\n"
        "        raise NotImplementedError\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "widget.py", "line": 1},), tmp_path, claim_kind="format_support"
    )

    assert signal == "unresolved"


def test_evidence_content_signal_source_file_key_is_recognized(tmp_path: Path):
    (tmp_path / "README.md").write_text("This library supports Widget export.\n", encoding="utf-8")

    signal = evidence_content_signal(
        ({"source_file": "README.md", "snippet": "This library supports Widget export."},),
        tmp_path,
        claim_kind="feature",
    )

    assert signal == "positive"


def test_evidence_content_signal_limitation_kind_expects_negative_snippet(tmp_path: Path):
    (tmp_path / "README.md").write_text("Widget export is not supported.\n", encoding="utf-8")

    signal = evidence_content_signal(
        ({"source_file": "README.md", "snippet": "Widget export is not supported."},),
        tmp_path,
        claim_kind="limitation",
    )

    assert signal == "negative"


def test_evidence_content_signal_stale_snippet_is_unresolved(tmp_path: Path):
    (tmp_path / "README.md").write_text("Unrelated current content.\n", encoding="utf-8")

    signal = evidence_content_signal(
        ({"source_file": "README.md", "snippet": "A snippet that no longer exists."},),
        tmp_path,
        claim_kind="feature",
    )

    assert signal == "unresolved"


def test_evidence_content_signal_missing_file_is_unresolved(tmp_path: Path):
    signal = evidence_content_signal(
        ({"file": "does_not_exist.py", "line": 1},), tmp_path, claim_kind="format_support"
    )

    assert signal == "unresolved"


def test_evidence_content_signal_traversal_path_is_unresolved(tmp_path: Path):
    outside = tmp_path.parent / "outside_widget.py"
    outside.write_text("class Widget:\n    def export(self):\n        return 1\n", encoding="utf-8")
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()

    try:
        signal = evidence_content_signal(
            ({"file": "../outside_widget.py", "line": 2},), clone_cache, claim_kind="format_support"
        )
        assert signal == "unresolved"
    finally:
        outside.unlink()


def test_evidence_content_signal_absolute_path_escaping_root_is_unresolved(tmp_path: Path):
    absolute_elsewhere = tmp_path.parent / "elsewhere_widget.py"
    absolute_elsewhere.write_text("class Widget:\n    pass\n", encoding="utf-8")
    clone_cache = tmp_path / "clone"
    clone_cache.mkdir()

    try:
        signal = evidence_content_signal(
            ({"file": str(absolute_elsewhere), "line": 1},),
            clone_cache,
            claim_kind="format_support",
        )
        assert signal == "unresolved"
    finally:
        absolute_elsewhere.unlink()


def test_evidence_content_signal_bare_file_existence_without_line_or_snippet_is_unresolved(
    tmp_path: Path,
):
    """Mere file existence is never itself a signal -- an evidence item
    with a real, resolvable path but no `line` or `snippet` to check
    content against must stay unresolved."""

    (tmp_path / "widget.py").write_text(
        "class Widget:\n    def export(self):\n        return b'ok'\n", encoding="utf-8"
    )

    signal = evidence_content_signal(
        ({"file": "widget.py"},), tmp_path, claim_kind="format_support"
    )

    assert signal == "unresolved"


def test_evidence_content_signal_negative_outranks_positive_across_evidence_items(
    tmp_path: Path,
):
    """Negative-evidence supremacy: when one evidence item is positive and
    another is negative for the same claim, the negative (real stub/
    constraint) signal wins -- concrete implementation/exception evidence
    outranks weaker corroborating material, never the reverse."""

    (tmp_path / "positive.py").write_text(
        "class WidgetA:\n    def export(self):\n        return b'ok'\n", encoding="utf-8"
    )
    (tmp_path / "negative.py").write_text(
        "class WidgetB:\n    def export(self):\n        raise NotImplementedError\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        (
            {"file": "positive.py", "line": 2},
            {"file": "negative.py", "line": 2},
        ),
        tmp_path,
        claim_kind="format_support",
    )

    assert signal == "negative"


def test_evidence_content_signal_empty_evidence_is_unresolved(tmp_path: Path):
    assert evidence_content_signal((), tmp_path, claim_kind="format_support") == "unresolved"
