"""Two owned spans -- callout (immediately after H1) and resources (file end).

Evidence-grounded, not the single-block design from the first pass: the
working 3d template has a short prominent pointer right under the H1 *and* a
fuller structured section further down, and pdf/Go's one buried link (line
1890 of 1890) showed presence without prominence doesn't serve the actual
goal. One documented strategy per span, not a pluggable framework.
"""

import re
from dataclasses import dataclass

SCHEMA_VERSION = "2"
SPAN_NAMES = ("callout", "resources")


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


def _h1_end_index(text: str) -> int:
    """Index right after the H1 heading line (+ its newline), or 0 if none."""
    match = re.search(r"^#[^#].*$", text, re.MULTILINE)
    if not match:
        return 0
    idx = match.end()
    if idx < len(text) and text[idx] == "\n":
        idx += 1
    return idx


def upsert_span(text: str, span_name: str, content: str, facts_hash: str) -> str:
    """Insert or replace the owned span. Never touches anything outside it."""
    if span_name not in SPAN_NAMES:
        raise ValueError(f"unknown span {span_name!r}, expected one of {SPAN_NAMES}")

    rendered = render_span(span_name, content, facts_hash)
    existing = find_span(text, span_name)
    if existing:
        return text[: existing.start] + rendered + text[existing.end :]

    if span_name == "callout":
        insert_at = _h1_end_index(text)
        return text[:insert_at] + "\n" + rendered + "\n" + text[insert_at:]

    # resources: append at end of file
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
