"""Normalize and inspect visitor-facing Markdown code fences."""

from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class CodeFenceIssue:
    rule_id: str
    line_start: int
    line_end: int
    message: str


def normalize_code_snippet(code: str) -> str:
    """Remove trailing whitespace and collapse repeated blank lines without changing tokens."""

    rendered: list[str] = []
    previous_blank = False
    for raw in code.strip("\r\n").splitlines():
        line = raw.rstrip()
        blank = not line
        if blank and previous_blank:
            continue
        rendered.append(line)
        previous_blank = blank
    return "\n".join(rendered).strip("\n")


def inspect_code_fences(markdown: str) -> list[CodeFenceIssue]:
    """Return language and repeated-blank-line defects for CommonMark fences."""

    issues: list[CodeFenceIssue] = []
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type != "fence" or token.map is None:
            continue
        start, end = token.map
        language = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ""
        if not language:
            issues.append(
                CodeFenceIssue(
                    rule_id="code_fence_language_missing",
                    line_start=start,
                    line_end=max(start + 1, end),
                    message="Every visitor-facing code fence must declare its language.",
                )
            )
        if normalize_code_snippet(token.content) != token.content.rstrip("\r\n"):
            issues.append(
                CodeFenceIssue(
                    rule_id="code_fence_spacing",
                    line_start=start,
                    line_end=max(start + 1, end),
                    message=(
                        "Code fences must not contain trailing whitespace or repeated blank lines."
                    ),
                )
            )
    return issues
