"""Wave 8.6 (item I, `LLM-017`/`VAL-016`/`RDM-020`): pure-function tests for
`scripts/data-refresh/detect_template_clones.py`'s similarity computation --
loaded via `importlib` since `scripts/data-refresh/` is a subdirectory, not
itself on `pythonpath` (unlike `scripts/` directly, per `pyproject.toml`)."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = REPO_ROOT / "scripts" / "data-refresh" / "detect_template_clones.py"

_spec = importlib.util.spec_from_file_location("detect_template_clones", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
detect_template_clones = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(detect_template_clones)


class TestCosineSimilarity:
    def test_identical_vectors_are_similarity_one(self):
        assert detect_template_clones._cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0

    def test_orthogonal_vectors_are_similarity_zero(self):
        assert detect_template_clones._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_zero_vector_never_divides_by_zero(self):
        assert detect_template_clones._cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestStripOwnedSpans:
    def test_removes_the_resources_span(self):
        from readme_agent.readme.markers import render_span

        text = "# Title\n\nSome prose.\n\n" + render_span("resources", "Link stuff.", "abc123")
        stripped = detect_template_clones._strip_owned_spans(text)
        assert "Link stuff." not in stripped
        assert "Some prose." in stripped


class TestFindFlaggedPairs:
    def test_similar_pair_above_threshold_is_flagged(self):
        embeddings = {
            "org/a": [1.0, 0.0],
            "org/b": [0.99, 0.01],
            "org/c": [0.0, 1.0],
        }
        flagged = detect_template_clones.find_flagged_pairs(embeddings, threshold=0.9)
        pairs = {(f["repo_a"], f["repo_b"]) for f in flagged}
        assert ("org/a", "org/b") in pairs
        assert not any("org/c" in pair for pair in pairs)

    def test_failed_embeddings_are_excluded_not_crashed_on(self):
        embeddings = {"org/a": [1.0, 0.0], "org/b": None}
        flagged = detect_template_clones.find_flagged_pairs(embeddings, threshold=0.9)
        assert flagged == []

    def test_no_pairs_above_threshold_returns_empty(self):
        embeddings = {"org/a": [1.0, 0.0], "org/b": [0.0, 1.0]}
        assert detect_template_clones.find_flagged_pairs(embeddings, threshold=0.9) == []
