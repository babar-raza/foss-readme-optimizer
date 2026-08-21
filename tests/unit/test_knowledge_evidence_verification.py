"""Item-level, polarity-aware evidence content verification -- the seam
`aspose_knowledge_selection.py` calls to decide whether a claim's cited
evidence actually supports or contradicts it, never merely whether the
cited file exists."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.knowledge_evidence_verification import (
    EvidenceContentCache,
    evidence_content_signal,
)


def test_csharp_limitation_line_is_verified_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "Scene.cs").write_text(
        "public class Scene\n"
        "{\n"
        "    public void Render()\n"
        "    {\n"
        '        throw new NotImplementedException("Unavailable in FOSS");\n'
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "Scene.cs", "line": 5},), tmp_path, claim_kind="limitation"
    )

    assert signal == "negative"


def test_csharp_implemented_method_is_positive_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "Scene.cs").write_text(
        "public class Scene\n{\n    public int Count()\n    {\n        return 1;\n    }\n}\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "Scene.cs", "line": 5},), tmp_path, claim_kind="feature"
    )

    assert signal == "positive"


def test_csharp_class_level_mixed_implementation_is_unresolved(tmp_path: Path):
    (tmp_path / "Scene.cs").write_text(
        "public class Scene\n"
        "{\n"
        "    public int Count() { return 1; }\n"
        "    public void Render() { throw new NotImplementedException(); }\n"
        "}\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "Scene.cs", "line": 1},), tmp_path, claim_kind="feature"
    )

    assert signal == "unresolved"


def test_java_limitation_line_is_verified_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "Scene.java").write_text(
        "public class Scene {\n"
        "  public void render() {\n"
        '    throw new UnsupportedOperationException("not implemented");\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "Scene.java", "line": 3},), tmp_path, claim_kind="limitation"
    )

    assert signal == "negative"


def test_typescript_implemented_method_is_positive_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "scene.ts").write_text(
        "export class Scene {\n  render(): number {\n    return 1;\n  }\n}\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "scene.ts", "line": 3},), tmp_path, claim_kind="feature"
    )

    assert signal == "positive"


def test_cpp_limitation_line_is_verified_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "scene.cpp").write_text(
        'void render() {\n    throw std::runtime_error("not implemented");\n}\n',
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "scene.cpp", "line": 2},), tmp_path, claim_kind="limitation"
    )

    assert signal == "negative"


def test_rust_limitation_line_is_verified_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "scene.rs").write_text(
        'pub fn render() {\n    unimplemented!("not implemented");\n}\n',
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "scene.rs", "line": 2},), tmp_path, claim_kind="limitation"
    )

    assert signal == "negative"


def test_go_implemented_function_is_positive_from_the_syntax_tree(tmp_path: Path):
    (tmp_path / "scene.go").write_text(
        "package scene\nfunc Render() int {\n    return 1\n}\n",
        encoding="utf-8",
    )

    signal = evidence_content_signal(
        ({"file": "scene.go", "line": 3},), tmp_path, claim_kind="feature"
    )

    assert signal == "positive"


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


def test_evidence_content_signal_verified_facts_txt_is_never_authorizing(tmp_path: Path):
    """Owner review (2026-08-20), mandatory correction 6: `verified_facts.txt`
    is a real filename dozens of `llm_enriched` claims across the imported
    corpus cite as their sole evidence (e.g. 3d/python's DracoFormat claim:
    `{"source_file": "verified_facts.txt", "snippet": "Class: DracoFormat\\n
    Docstring: Google Draco format"}`) -- aspose.org's own pipeline digest
    about itself, not genuine product documentation. Even when a file with
    that exact name is present inside the pinned clone and its content
    verbatim-matches the cited snippet (the ordinary positive-signal path,
    proven working one test above for README.md), it must still resolve
    `unresolved`, never `positive` -- synthetic self-description can never
    substitute for real corroboration, regardless of what it contains."""

    (tmp_path / "verified_facts.txt").write_text(
        "Class: DracoFormat\n  Docstring: Google Draco format\n", encoding="utf-8"
    )

    signal = evidence_content_signal(
        (
            {
                "source_file": "verified_facts.txt",
                "snippet": "Class: DracoFormat\n  Docstring: Google Draco format",
            },
        ),
        tmp_path,
        claim_kind="api",
    )

    assert signal == "unresolved"


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


def test_evidence_cache_parses_one_immutable_file_once_across_claims(tmp_path: Path):
    (tmp_path / "widget.py").write_text(
        "class Widget:\n    def export(self):\n        return b'ok'\n", encoding="utf-8"
    )
    cache = EvidenceContentCache(tmp_path)
    evidence = ({"file": "widget.py", "line": 2},)

    first = evidence_content_signal(evidence, tmp_path, claim_kind="format_support", cache=cache)
    source_path = cache.resolve("widget.py")
    assert source_path is not None
    cache.trees[source_path] = None
    second = evidence_content_signal(evidence, tmp_path, claim_kind="format_support", cache=cache)

    assert first == second == "positive"
    assert len(cache.texts) == 1
    assert len(cache.trees) == 1
    assert cache.python_line_signals == {(source_path, 2): "positive"}


def test_evidence_cache_classifies_one_non_python_source_line_once(tmp_path: Path):
    (tmp_path / "Scene.cs").write_text(
        "public class Scene\n{\n    public int Count() { return 1; }\n}\n",
        encoding="utf-8",
    )
    cache = EvidenceContentCache(tmp_path)
    evidence = ({"file": "Scene.cs", "line": 3},)

    first = evidence_content_signal(evidence, tmp_path, claim_kind="feature", cache=cache)
    source_path = cache.resolve("Scene.cs")
    assert source_path is not None
    cache.tree_sitter.trees[source_path] = None
    second = evidence_content_signal(evidence, tmp_path, claim_kind="feature", cache=cache)

    assert first == second == "positive"
    assert cache.tree_sitter.line_signals == {(source_path, 3): "positive"}
