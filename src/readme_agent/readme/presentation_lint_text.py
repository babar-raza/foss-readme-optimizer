"""Shared text and stable-finding helpers for README presentation lint."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from readme_agent.readme.presentation_lint_models import (
    PresentationLintFindingV1,
    PresentationLintSpanV1,
)


@dataclass(frozen=True)
class VisibleLine:
    start: int
    end: int
    text: str


def visible_lines(text: str) -> list[VisibleLine]:
    """Return non-fenced lines with exact character offsets."""

    lines: list[VisibleLine] = []
    offset = 0
    fenced = False
    for raw in text.splitlines(keepends=True):
        content = raw.rstrip("\r\n")
        if content.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            lines.append(VisibleLine(offset, offset + len(content), content))
        offset += len(raw)
    return lines


def exact_span(text: str, start: int, end: int) -> PresentationLintSpanV1:
    return PresentationLintSpanV1(start=start, end=end, text=text[start:end])


def line_span(text: str, line: VisibleLine) -> PresentationLintSpanV1:
    leading = len(line.text) - len(line.text.lstrip())
    trailing = len(line.text.rstrip())
    return exact_span(text, line.start + leading, line.start + trailing)


def make_finding(
    rule_id: str,
    message: str,
    spans: list[PresentationLintSpanV1],
    *,
    severity: Literal["critical", "warning"] = "critical",
) -> PresentationLintFindingV1:
    ordered = sorted(spans, key=lambda span: (span.start, span.end, span.text))
    fingerprint = hashlib.sha256(
        (
            rule_id
            + "\0"
            + "\0".join(
                f"{span.start}\0{span.end}\0{span.text}\0{index}"
                for index, span in enumerate(ordered)
            )
        ).encode("utf-8")
    ).hexdigest()[:12]
    return PresentationLintFindingV1(
        finding_id=f"presentation.{rule_id}.{fingerprint}",
        rule_id=rule_id,
        severity=severity,
        message=message,
        spans=ordered,
    )
