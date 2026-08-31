"""Reject visitor-facing format directions contradicted by accepted facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.format_role_truth import FormatRole, unsupported_format_directions
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import exact_span, make_finding

RULE_IDS = ("format_direction_contradiction",)

_INPUT_VERB = re.compile(r"(?i)\b(?:import|load|open|read)s?(?:ing)?\b")
_OUTPUT_VERB = re.compile(r"(?i)\b(?:export|save|write)s?(?:ing)?\b")
_DIRECTION_BOUNDARY = re.compile(
    r"(?i)\b(?:and\s+)?(?:import|load|open|read|export|save|write)s?(?:ing)?\b"
    # "converts to"/"converted into"/etc: a conversion clause names its *target* format
    # after "to"/"into", not its source. Without its own boundary, that target format
    # gets swept into whatever fragment the sentence's earlier load/read/import verb
    # started -- e.g. "a loaded `.md` file converts to DOCX or PDF" wrongly attributed
    # PDF to the *input* role, since "loaded" was the only boundary match on the line
    # and its fragment ran to the end of the sentence. Anchoring a new boundary at
    # "to"/"into" itself starts a fresh, correctly-classified output fragment there.
    r"|\bconverts?(?:ed|ing)?\b[^.\n]{0,40}?\b(?:to|into)\b"
)
_NEGATED_DIRECTION = re.compile(
    r"(?i)\b(?:not|cannot|can't|doesn't|does not|isn't|is not|unavailable|unsupported|"
    r"limited(?:\s+to)?)\b"
)
_INPUT_NOUN = re.compile(r"(?i)\b(?:importer|input|load options?)\b")
_OUTPUT_NOUN = re.compile(r"(?i)\b(?:exporter|output|save options?)\b")
# "like any other input/output": a generic hedge comparing this format to every other one
# a reader would already expect, not a claim about a *specific* format's direction. Without
# this guard, the bare noun "input"/"output" makes the whole-line noun fallback below sweep
# in every format the line happens to mention -- observed live: "a loaded `.md` file
# converts to DOCX or PDF like any other input" wrongly claimed PDF as an *input* format
# purely because the sentence ends with the unrelated word "input".
_GENERIC_DIRECTION_HEDGE = re.compile(r"(?i)\blike any other (?:input|output)\b")


def directional_fragments(line: str) -> list[tuple[FormatRole, str, int, int]]:
    matches = list(_DIRECTION_BOUNDARY.finditer(line))
    fragments: list[tuple[FormatRole, str, int, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
        fragment = line[start:end]
        if _NEGATED_DIRECTION.search(fragment):
            continue
        role: FormatRole = "input" if _INPUT_VERB.search(match.group(0)) else "output"
        fragments.append((role, fragment, start, end))
    return fragments


def lint_format_directions(
    text: str,
    facts: ProductFactsV2 | None,
) -> list[PresentationLintFindingV1]:
    """Find explicit prose or Mermaid roles that oppose authoritative format roles."""

    if facts is None:
        return []
    findings: list[PresentationLintFindingV1] = []
    offset = 0
    fence = None
    mermaid_role: FormatRole | None = None
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            if fence is None:
                fence = stripped[3:].strip().casefold()
            else:
                fence = None
                mermaid_role = None
            offset += len(raw_line)
            continue
        fragments: list[tuple[FormatRole, str, int, int]] = []
        if fence == "mermaid":
            subgraph = re.match(r'(?i)^\s*subgraph\s+\w+\["?(?P<label>[^\]"]+)', line)
            if subgraph is not None:
                label = subgraph.group("label").casefold()
                mermaid_role = (
                    "input" if "input" in label else "output" if "output" in label else None
                )
            elif stripped == "end":
                mermaid_role = None
            elif mermaid_role is not None:
                fragments.append((mermaid_role, line, 0, len(line)))
        elif fence is None:
            fragments.extend(directional_fragments(line))
            if not _NEGATED_DIRECTION.search(line) and not _GENERIC_DIRECTION_HEDGE.search(line):
                if _INPUT_NOUN.search(line):
                    fragments.append(("input", line, 0, len(line)))
                if _OUTPUT_NOUN.search(line):
                    fragments.append(("output", line, 0, len(line)))
        for role, fragment, start, end in fragments:
            conflicts = sorted(unsupported_format_directions(fragment, facts, role))
            if not conflicts:
                continue
            findings.append(
                make_finding(
                    "format_direction_contradiction",
                    f"Accepted product facts do not authorize {role} role for "
                    f"{', '.join(conflicts)}.",
                    [exact_span(text, offset + start, offset + end)],
                )
            )
        offset += len(raw_line)
    return findings


__all__ = ["RULE_IDS", "directional_fragments", "lint_format_directions"]
