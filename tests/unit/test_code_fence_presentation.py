"""Verify visitor-facing code-fence normalization and validation."""

from readme_agent.readme.code_fence_presentation import (
    inspect_code_fences,
    normalize_code_snippet,
)


def test_normalization_preserves_code_and_collapses_only_repeated_blank_lines() -> None:
    code = "first()  \n\n\nsecond()\n"

    assert normalize_code_snippet(code) == "first()\n\nsecond()"


def test_language_and_repeated_blank_lines_fail_independently() -> None:
    issues = inspect_code_fences("```\nfirst()\n\n\nsecond()\n```\n")

    assert [issue.rule_id for issue in issues] == [
        "code_fence_language_missing",
        "code_fence_spacing",
    ]


def test_language_tagged_normalized_fence_passes() -> None:
    assert inspect_code_fences("```python\nfirst()\n\nsecond()\n```\n") == []
