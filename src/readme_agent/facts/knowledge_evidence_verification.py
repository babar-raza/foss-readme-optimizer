"""Item-level, polarity-aware content verification for one imported
knowledge claim's cited evidence.

`aspose_knowledge_selection.py`'s corroboration pass calls
`evidence_content_signal()` to decide whether a claim's cited evidence
actually supports or contradicts that claim -- never merely whether the
cited file exists. A real 3D claim asserting "export support for Fbx via
FbxExporter" and a real Barcode claim asserting "export support for Pdf via
PdfRenderer" both cite a file that genuinely exists; both cited methods
genuinely raise `NotImplementedError`. File existence alone cannot tell
those two claims apart from a real, working exporter -- only inspecting the
cited code region's actual content can.

Extensible by construction: each evidence shape (a Python source line, a
prose/markdown snippet, ...) is handled by one small verifier function below;
adding a new evidence shape means adding one function and wiring it into
`_evidence_item_signal`, never branching on product family or repository.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

from readme_agent.facts.knowledge_source_polarity import (
    TreeSitterEvidenceCache,
    source_line_signal,
)
from readme_agent.facts.python_evidence_polarity import function_node_is_unimplemented

EvidenceContentSignal = Literal["positive", "negative", "unresolved"]

# Evidence dicts in the imported corpus cite a path under one of two keys
# (scout claims use `file`, LLM-enriched claims use `source_file`) -- both
# are recognized, `source_file` preferred when both resolve since it is the
# more specific citation the enrichment pass actually inspected.
_PATH_KEYS: tuple[str, ...] = ("source_file", "file")

# Owner review (2026-08-20), correction 6: aspose.org's own scout/LLM-
# enrichment pipeline writes its own intermediate digest to a file it names
# `verified_facts.txt` -- confirmed live, dozens of real `llm_enriched`
# claims across the imported corpus (e.g. 3d/python's DracoFormat claim)
# cite it as their sole evidence, with snippets like "Class: DracoFormat\n
# Docstring: Google Draco format": the pipeline's own notes about itself,
# never genuine product documentation or source. Even if a file with this
# exact name also happens to exist inside the pinned repository clone, it
# must never be treated as corroborating evidence -- doing so would let the
# pipeline's own self-description authorize a claim without ever inspecting
# real content, the same circular-authority risk this whole module exists
# to prevent for "cited file merely exists" signals.
_SYNTHETIC_EVIDENCE_FILENAMES = frozenset({"verified_facts.txt"})


class EvidenceContentCache:
    """Per-immutable-snapshot file, source, and AST cache for claim corroboration."""

    def __init__(self, clone_cache: Path) -> None:
        self.root = clone_cache.resolve()
        self.resolved: dict[str, Path | None] = {}
        self.texts: dict[Path, str | None] = {}
        self.trees: dict[Path, ast.Module | None] = {}
        self.python_line_signals: dict[tuple[Path, int], EvidenceContentSignal] = {}
        self.tree_sitter = TreeSitterEvidenceCache(self.root)

    def resolve(self, reference: str) -> Path | None:
        if reference in self.resolved:
            return self.resolved[reference]
        resolved = _safe_resolve(self.root, reference)
        self.resolved[reference] = resolved
        return resolved

    def text(self, path: Path) -> str | None:
        if path not in self.texts:
            self.texts[path] = _read_text(path)
        return self.texts[path]

    def source_and_tree(self, path: Path) -> tuple[str | None, ast.Module | None]:
        source = self.text(path)
        if path not in self.trees:
            try:
                self.trees[path] = ast.parse(source) if source is not None else None
            except SyntaxError:
                self.trees[path] = None
        return source, self.trees[path]


def _is_synthetic_evidence_reference(reference: str) -> bool:
    return Path(reference).name in _SYNTHETIC_EVIDENCE_FILENAMES


def _safe_resolve(clone_cache: Path, reference: str) -> Path | None:
    """Resolve `reference` to a real file strictly inside `clone_cache`.

    Rejects traversal, an absolute path escaping the clone root, a missing
    file, an unreadable path, and a known-synthetic pipeline artifact name
    (see `_SYNTHETIC_EVIDENCE_FILENAMES`) -- a corroboration signal only
    ever comes from a real, genuine file inside the pinned repository
    clone, never from mere path syntax or the pipeline's own output about
    itself."""

    if not isinstance(reference, str) or not reference:
        return None
    if _is_synthetic_evidence_reference(reference):
        return None
    root = clone_cache.resolve()
    try:
        candidate = (root / reference).resolve()
    except OSError:
        return None
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _class_wide_signal(tree: ast.Module, source: str, line: int) -> EvidenceContentSignal:
    """Fallback for evidence cited at a class-declaration line rather than
    inside one of its methods -- the common scout-extractor convention for
    "X support ... via ClassName" claims, which cite the class line, not a
    specific method. Classifies by the class's own public methods (dunder
    and private helpers excluded), never by class/file existence alone: a
    class whose every public method is a stub is negative evidence, a class
    whose every public method is real is positive evidence, and a class with
    a genuine mix at a class-level citation is unresolved rather than
    guessed."""

    classes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    if not classes:
        return "unresolved"
    target = min(classes, key=lambda node: (node.end_lineno or node.lineno) - node.lineno)
    public_methods = [
        member
        for member in target.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not member.name.startswith("_")
    ]
    if not public_methods:
        return "unresolved"
    stub_flags = [function_node_is_unimplemented(source, member) for member in public_methods]
    if all(stub_flags):
        return "negative"
    if not any(stub_flags):
        return "positive"
    return "unresolved"


def _python_line_signal(
    evidence_item: dict,
    resolved_path: Path,
    cache: EvidenceContentCache,
) -> EvidenceContentSignal:
    """Verifier: a cited Python source line. Prefers the innermost function
    containing the line (the common case -- a limitation claim citing the
    exact `raise` line, or a method-level citation); falls back to the
    enclosing class's own public-method survey when the line lands on a
    class declaration instead."""

    line = evidence_item.get("line")
    if resolved_path.suffix != ".py" or not isinstance(line, int) or line < 1:
        return "unresolved"
    key = (resolved_path, line)
    if key in cache.python_line_signals:
        return cache.python_line_signals[key]
    signal = _uncached_python_line_signal(resolved_path, line, cache)
    cache.python_line_signals[key] = signal
    return signal


def _uncached_python_line_signal(
    resolved_path: Path,
    line: int,
    cache: EvidenceContentCache,
) -> EvidenceContentSignal:
    source, tree = cache.source_and_tree(resolved_path)
    if source is None or tree is None:
        return "unresolved"
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.lineno <= line <= (node.end_lineno or node.lineno)
    ]
    if functions:
        innermost = min(functions, key=lambda node: (node.end_lineno or node.lineno) - node.lineno)
        return "negative" if function_node_is_unimplemented(source, innermost) else "positive"
    return _class_wide_signal(tree, source, line)


def _snippet_freshness_signal(
    evidence_item: dict,
    resolved_path: Path,
    *,
    claim_kind: str,
    cache: EvidenceContentCache,
) -> EvidenceContentSignal:
    """Verifier: a cited prose/markdown snippet (LLM-enriched claims). The
    snippet was captured, by construction, as support for this exact claim;
    a fresh (still verbatim, whitespace-normalized) match corroborates the
    claim's own stated polarity. A stale or mismatched snippet -- captured
    from a since-refreshed README, or otherwise no longer reproducible --
    never corroborates, regardless of how the original claim reads."""

    snippet = evidence_item.get("snippet")
    if not isinstance(snippet, str) or not snippet.strip():
        return "unresolved"
    content = cache.text(resolved_path)
    if content is None:
        return "unresolved"
    if _normalize_whitespace(snippet) not in _normalize_whitespace(content):
        return "unresolved"
    return "negative" if claim_kind == "limitation" else "positive"


def _evidence_item_signal(
    evidence_item: object,
    clone_cache: Path,
    *,
    claim_kind: str,
    cache: EvidenceContentCache,
) -> EvidenceContentSignal:
    if not isinstance(evidence_item, dict):
        return "unresolved"
    resolved: Path | None = None
    for key in _PATH_KEYS:
        reference = evidence_item.get(key)
        if isinstance(reference, str) and reference:
            resolved = cache.resolve(reference)
            if resolved is not None:
                break
    if resolved is None:
        return "unresolved"
    line_signal = _python_line_signal(evidence_item, resolved, cache)
    if line_signal != "unresolved":
        return line_signal
    line = evidence_item.get("line")
    if isinstance(line, int):
        source_signal = source_line_signal(resolved, line, cache=cache.tree_sitter)
        if source_signal != "unresolved":
            return source_signal
    return _snippet_freshness_signal(
        evidence_item,
        resolved,
        claim_kind=claim_kind,
        cache=cache,
    )


def evidence_content_signal(
    evidence: tuple[dict, ...],
    clone_cache: Path,
    *,
    claim_kind: str,
    cache: EvidenceContentCache | None = None,
) -> EvidenceContentSignal:
    """Combine every cited evidence item's resolved content signal for one
    claim. Negative (stub/constraint) evidence always outranks a merely
    positive-looking signal found elsewhere in the same claim's evidence --
    concrete implementation/exception evidence outranks weaker corroborating
    material, never the reverse. `"unresolved"` only when no cited item
    yields a definite signal -- the mere existence of a cited file is never
    itself a signal."""

    active_cache = cache or EvidenceContentCache(clone_cache)
    if active_cache.root != clone_cache.resolve():
        raise ValueError("evidence cache belongs to another immutable snapshot")
    signals = [
        _evidence_item_signal(
            item,
            clone_cache,
            claim_kind=claim_kind,
            cache=active_cache,
        )
        for item in evidence
    ]
    if "negative" in signals:
        return "negative"
    if "positive" in signals:
        return "positive"
    return "unresolved"


__all__ = ["EvidenceContentCache", "EvidenceContentSignal", "evidence_content_signal"]
