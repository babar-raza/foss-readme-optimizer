"""Detect internal tokens, duplication, leakage, injection, and visible fragments."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import line_span, make_finding, visible_lines
from readme_agent.readme.presentation_similarity import summaries_overlap

RULE_IDS = (
    "cross_product_leakage",
    "prompt_injection_residue",
    "raw_internal_token",
    "semantic_duplicate",
    "visitor_fragment",
)

_RAW_SNAKE_BULLET = re.compile(r"^\s*[-*+]\s+`[a-z][a-z0-9]*_[a-z0-9_]+`")
_ENUM_LIST = re.compile(r"\b[A-Z][A-Z0-9_]{1,}(?:\s*,\s*[A-Z][A-Z0-9_]{1,})+\b")
_PROMPT_INJECTION = re.compile(
    r"(?i)(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)"
    r"\s+(?:instructions?|prompts?)|report\b.*\bapproved\b.*\bmissing\b"
)
_VISITOR_FRAGMENT = re.compile(r"\ufffd|鈥\?|â€”|â€“|â€")
_ASPOSE_FOSS_PRODUCT = re.compile(r"\bAspose\.([A-Za-z0-9]+)\s+FOSS\b")
_BULLET_PREFIX = re.compile(r"^\s*[-*+]\s+")
_MARKUP = re.compile(r"[`*_.,:;!?()\[\]{}]")
_LABEL = re.compile(r"^\s*[-*+]\s+\*\*([^*]+):\*\*\s*(.+)$")


def _normalized_bullet(line: str) -> str:
    value = _BULLET_PREFIX.sub("", line)
    value = _MARKUP.sub(" ", value).casefold()
    return " ".join(value.split())


def _own_aspose_family(facts: ProductFactsV2 | None) -> str | None:
    if facts is None:
        return None
    identity = facts.selected_fact("product.identity").value
    if not isinstance(identity, dict):
        return None
    family = str(identity.get("family") or "").strip().casefold()
    return family or None


def lint_semantics(
    text: str,
    facts: ProductFactsV2 | None,
) -> list[PresentationLintFindingV1]:
    findings: list[PresentationLintFindingV1] = []
    lines = visible_lines(text)

    for line in lines:
        if _PROMPT_INJECTION.search(line.text):
            findings.append(
                make_finding(
                    "prompt_injection_residue",
                    "Untrusted repository instructions survived into the candidate.",
                    [line_span(text, line)],
                )
            )
        for match in _VISITOR_FRAGMENT.finditer(line.text):
            start = line.start + match.start()
            findings.append(
                make_finding(
                    "visitor_fragment",
                    "A broken encoding fragment is visible to README visitors.",
                    [
                        line_span(text, line).model_copy(
                            update={
                                "start": start,
                                "end": start + len(match.group(0)),
                                "text": match.group(0),
                            }
                        )
                    ],
                )
            )
        if _RAW_SNAKE_BULLET.match(line.text):
            findings.append(
                make_finding(
                    "raw_internal_token",
                    "An internal snake-case token is exposed as visitor prose.",
                    [line_span(text, line)],
                )
            )
        if "**Verified formats:**" in line.text and _ENUM_LIST.search(line.text):
            findings.append(
                make_finding(
                    "raw_internal_token",
                    "Internal format enum values are exposed in the visitor summary.",
                    [line_span(text, line)],
                )
            )

    h2_sections = [heading for heading in parse_headings(text) if heading.level == 2]
    bullets: dict[tuple[int, str], list] = {}
    for line in lines:
        if _BULLET_PREFIX.match(line.text):
            normalized = _normalized_bullet(line.text)
            if normalized:
                section_start = next(
                    (
                        heading.start
                        for heading in h2_sections
                        if heading.heading_end <= line.start < heading.section_end
                    ),
                    -1,
                )
                bullets.setdefault((section_start, normalized), []).append(line)
    for repeated in bullets.values():
        if len(repeated) > 1:
            findings.append(
                make_finding(
                    "semantic_duplicate",
                    "The same visitor-facing bullet is repeated.",
                    [line_span(text, line) for line in repeated],
                )
            )

    labeled = []
    for line in lines:
        label_match = _LABEL.match(line.text)
        if label_match:
            labeled.append((label_match.group(1).casefold(), label_match.group(2), line))
    problems = [item for item in labeled if item[0] == "problem solved"]
    capabilities = [item for item in labeled if item[0] == "verified capabilities"]
    for _, problem, problem_line in problems:
        for _, capability, capability_line in capabilities:
            if summaries_overlap(problem, capability):
                findings.append(
                    make_finding(
                        "semantic_duplicate",
                        "Problem and capability summaries repeat the same inventory.",
                        [line_span(text, problem_line), line_span(text, capability_line)],
                    )
                )

    own_family = _own_aspose_family(facts)
    if own_family:
        foreign_lines = []
        for line in lines:
            families = {
                match.group(1).casefold() for match in _ASPOSE_FOSS_PRODUCT.finditer(line.text)
            }
            if any(family != own_family for family in families):
                foreign_lines.append(line_span(text, line))
        if foreign_lines:
            findings.append(
                make_finding(
                    "cross_product_leakage",
                    "The candidate introduces a different product family than its "
                    "fact-bound identity.",
                    foreign_lines,
                )
            )
    return findings
