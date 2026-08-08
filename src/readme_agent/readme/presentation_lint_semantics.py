"""Detect internal tokens, duplication, leakage, injection, and visible fragments."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.presentation_lint_models import PresentationLintFindingV1
from readme_agent.readme.presentation_lint_text import (
    VisibleLine,
    emoji_decoration_spans,
    exact_span,
    line_span,
    make_finding,
    visible_lines,
)
from readme_agent.readme.presentation_similarity import (
    capability_discriminators,
    semantically_repeats,
    summaries_overlap,
)

RULE_IDS = (
    "cross_product_leakage",
    "emoji_decoration",
    "prompt_injection_residue",
    "raw_internal_token",
    "semantic_duplicate",
    "visitor_fragment",
)

_RAW_SNAKE_BULLET = re.compile(r"^\s*[-*+]\s+`(?P<token>[a-z][a-z0-9]*_[a-z0-9_]+)`")
_SNAKE_IDENTIFIER = re.compile(r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b")
_ENUM_LIST = re.compile(r"\b[A-Z][A-Z0-9_]{1,}(?:\s*,\s*[A-Z][A-Z0-9_]{1,})+\b")
_PROMPT_INJECTION = re.compile(
    r"(?i)(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)"
    r"\s+(?:instructions?|prompts?)|report\b.*\bapproved\b.*\bmissing\b"
)
_VISITOR_FRAGMENT = re.compile(r"\ufffd|鈥\?|â€”|â€“|â€")
_ASPOSE_FOSS_PRODUCT = re.compile(r"\bAspose\.([A-Za-z0-9]+)\s+FOSS\b")
_BULLET_PREFIX = re.compile(r"^\s*[-*+]\s+")
_CAPABILITY_ROW = re.compile(r"^\s*[-*+]\s+\*\*(?P<title>[^*]+)\*\*\s+-\s+.+$")
_MARKUP = re.compile(r"[`*_.,:;!?()\[\]{}]")
_LABEL = re.compile(r"^\s*[-*+]\s+\*\*([^*]+):\*\*\s*(.+)$")
_API_SIGNATURE_BULLET = re.compile(
    r"^\s*[-*+]\s+`[^`\n]+`(?:\s*(?:,\s*|and\s+)`[^`\n]+`)*\s*$",
    flags=re.IGNORECASE,
)


def _normalized_bullet(line: str) -> str:
    capability_row = _CAPABILITY_ROW.match(line)
    value = capability_row.group("title") if capability_row is not None else line
    value = _BULLET_PREFIX.sub("", value)
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


def _verified_repository_identifiers(facts: ProductFactsV2 | None) -> set[str]:
    """Return code identifiers independently bound to accepted implementation evidence."""

    if facts is None:
        return set()
    identifiers: set[str] = set()
    for fact in facts.facts:
        if fact.verification_state != "verified":
            continue
        if fact.field == "api.public_surface" and isinstance(fact.value, dict):
            for module in fact.value.get("modules", []):
                if not isinstance(module, dict):
                    continue
                for exported in module.get("exports", []):
                    if isinstance(exported, str) and _SNAKE_IDENTIFIER.fullmatch(exported):
                        identifiers.add(exported)
            for public_class in fact.value.get("classes", []):
                if not isinstance(public_class, dict):
                    continue
                for member in public_class.get("members", []):
                    if not isinstance(member, dict):
                        continue
                    name = member.get("name")
                    if isinstance(name, str) and _SNAKE_IDENTIFIER.fullmatch(name):
                        identifiers.add(name)
        for assessment in fact.evidence_assessments or []:
            if not assessment.accepted or assessment.observed_polarity != "positive_implementation":
                continue
            for evidence_text in (
                assessment.anchor,
                assessment.exact_excerpt,
                assessment.context_excerpt,
            ):
                identifiers.update(_SNAKE_IDENTIFIER.findall(evidence_text))
    return identifiers


def lint_semantics(
    text: str,
    facts: ProductFactsV2 | None,
) -> list[PresentationLintFindingV1]:
    findings: list[PresentationLintFindingV1] = []
    lines = visible_lines(text)
    verified_identifiers = _verified_repository_identifiers(facts)

    emoji_spans = [exact_span(text, start, end) for start, end in emoji_decoration_spans(text)]
    if emoji_spans:
        findings.append(
            make_finding(
                "emoji_decoration",
                "Visitor-facing emoji decoration violates the portfolio presentation contract.",
                emoji_spans,
            )
        )

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
        snake_bullet = _RAW_SNAKE_BULLET.match(line.text)
        if snake_bullet is not None and snake_bullet.group("token") not in verified_identifiers:
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
        if _BULLET_PREFIX.match(line.text) and not _API_SIGNATURE_BULLET.fullmatch(line.text):
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

    capability_sections = {
        heading.start: heading
        for heading in h2_sections
        if any(
            marker in heading.title.casefold() for marker in ("capabilit", "feature", "why aspose")
        )
    }
    cross_section_duplicates: list[VisibleLine] = []
    capability_bullets = [
        (section_start, normalized, line)
        for (section_start, normalized), section_lines in bullets.items()
        if section_start in capability_sections
        for line in section_lines
    ]
    for index, (_left_section, left, left_line) in enumerate(capability_bullets):
        for right_section, right, right_line in capability_bullets[index + 1 :]:
            if _left_section == right_section:
                left_discriminators = capability_discriminators(left)
                right_discriminators = capability_discriminators(right)
                if (
                    left_discriminators
                    and right_discriminators
                    and left_discriminators != right_discriminators
                ):
                    continue
            if not semantically_repeats(left, right):
                continue
            cross_section_duplicates.extend((left_line, right_line))
    if cross_section_duplicates:
        unique_lines = {(line.start, line.end): line for line in cross_section_duplicates}
        findings.append(
            make_finding(
                "semantic_duplicate",
                "Capability information is repeated across competing visitor sections.",
                [line_span(text, line) for line in unique_lines.values()],
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
