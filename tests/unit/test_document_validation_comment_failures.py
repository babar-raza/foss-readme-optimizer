"""`_comment_failures` must not crash on a fenced code block with no info
string (e.g. a plain ``` ``` `` directory-tree diagram) -- `token.info.strip()
.split(maxsplit=1)[0]` raises IndexError on an empty split result, first
found live when PWD-060's verified Project Structure diagram (rendered as a
language-less fence, matching the maintainer's own source formatting) hit
this exact path."""

from __future__ import annotations

from readme_agent.readme.document_validation import _comment_failures


def test_language_less_fence_does_not_crash_and_is_not_a_comment_failure() -> None:
    candidate = (
        "# Product\n\n## Development and Testing\n\n### Project Structure\n\n"
        "```\n├── src/  # Public API\n└── docs/  # Documentation\n```\n"
    )

    assert _comment_failures(candidate) == []


def test_language_less_fence_with_a_real_comment_is_still_undetectable_by_language() -> None:
    # Without a declared language, `source_contains_comments` has nothing to
    # dispatch on -- this documents the boundary, not a gap this fix must close.
    candidate = "```\n# a shell-style comment\necho hi\n```\n"

    assert _comment_failures(candidate) == []


def test_labelled_fence_comment_detection_is_unaffected() -> None:
    candidate = "```python\n# a real comment\nprint('hi')\n```\n"

    assert _comment_failures(candidate) == [
        "README contains a source comment in the python fence at line 1"
    ]
