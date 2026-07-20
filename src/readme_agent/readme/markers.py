"""One owned span -- resources (file end).

Phase 21 (decision #9 as corrected): a second span, "callout", used to render
immediately after the H1 -- retired, because a promotional banner right under
the H1 is exactly what a product-first opening forbids, and because the
two-span design had a real, confirmed link-duplication bug (see renderer.py).
find_span/remove_span still work on any span name, including the retired
"callout", so orchestrator.py's one-time migration step can cleanly strip a
legacy callout span out of an existing work clone; upsert_span only ever
targets "resources" now.
"""

import re
from dataclasses import dataclass

SCHEMA_VERSION = "2"
SPAN_NAMES = ("resources",)


def _span_pattern(span_name: str) -> re.Pattern:
    return re.compile(
        rf'<!-- readme-agent:{span_name} hash="sha256:([0-9a-f]+)" schema="([^"]+)" -->\n'
        rf"(.*?)\n"
        rf"<!-- readme-agent:{span_name}:end -->\n?",
        re.DOTALL,
    )


@dataclass
class SpanMatch:
    start: int
    end: int
    facts_hash: str
    schema_version: str
    content: str


def find_span(text: str, span_name: str) -> SpanMatch | None:
    match = _span_pattern(span_name).search(text)
    if not match:
        return None
    return SpanMatch(
        start=match.start(),
        end=match.end(),
        facts_hash=match.group(1),
        schema_version=match.group(2),
        content=match.group(3),
    )


def render_span(span_name: str, content: str, facts_hash: str) -> str:
    return (
        f'<!-- readme-agent:{span_name} hash="sha256:{facts_hash}" schema="{SCHEMA_VERSION}" -->\n'
        f"{content}\n"
        f"<!-- readme-agent:{span_name}:end -->\n"
    )


def upsert_span(text: str, span_name: str, content: str, facts_hash: str) -> str:
    """Insert or replace the owned span. Never touches anything outside it.
    Only "resources" is a valid target since Phase 21 -- appended at end of
    file. Raises for any other name, including the retired "callout" (use
    remove_span for that -- see orchestrator.py's migration step)."""
    if span_name not in SPAN_NAMES:
        raise ValueError(f"unknown span {span_name!r}, expected one of {SPAN_NAMES}")

    rendered = render_span(span_name, content, facts_hash)
    existing = find_span(text, span_name)
    if existing:
        return text[: existing.start] + rendered + text[existing.end :]

    separator = "" if text.endswith("\n") else "\n"
    return text + separator + "\n" + rendered


def remove_span(text: str, span_name: str) -> str:
    """The exact inverse of upsert_span's insertion, including the blank-line
    separator(s) it adds -- callout gets one on each side (inserted
    mid-document), resources gets one only on the leading side (appended)."""
    existing = find_span(text, span_name)
    if not existing:
        return text
    start, end = existing.start, existing.end
    if start > 0 and text[start - 1] == "\n":
        start -= 1
    if span_name == "callout" and end < len(text) and text[end] == "\n":
        end += 1
    return text[:start] + text[end:]
