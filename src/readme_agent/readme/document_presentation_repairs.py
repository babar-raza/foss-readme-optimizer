"""Plan bounded deterministic repairs for known visitor-facing presentation defects."""

from __future__ import annotations

import re

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import (
    ReadmeDocumentOperationV1,
)
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.presentation_lint_text import (
    emoji_decoration_spans,
    strip_emoji_decorations,
    strip_fenced_code_comments,
)
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
    public_text_corrections,
    title_case_heading,
)

_VAGUE_FUTURE_BULLET = re.compile(
    r"(?im)^[ \t]*[-*+][ \t]+more[^\r\n]*coming soon(?:[.!…]+)?[ \t]*(?:\r?\n|$)"
)
_RAW_OPTION_BULLET = re.compile(
    r"(?m)^(?P<prefix>[ \t]*[-*+][ \t]+)"
    r"`(?P<token>[a-z][a-z0-9_]*_[a-z0-9_]+)`"
    r"[ \t]+[-–—:][ \t]+(?P<description>[^\r\n]+)(?P<newline>\r?\n|$)"
)
_COMMERCIAL_HEADING = re.compile(r"(?i)(?:enterprise edition|aspose\.com)")
_OTHER_PLATFORMS_HEADING = re.compile(r"(?i)\bother platforms(?:\s+\(official [^)]+\))?$")
_COMMERCIAL_CTA = re.compile(r"(?i)\b(?:buy|free trial|download|upgrade now)\b")
_COMMERCIAL_DIRECTORY = re.compile(
    r"(?i)(?:products\.aspose\.com|full-featured Aspose product|official libraries)"
)
_MOJIBAKE_REPLACEMENTS = {
    "鈥?": "—",
    "â€¢": "-",
    "â€”": "—",
    "â€“": "–",
    "â€™": "’",
    "â€¦": "…",
    "Â©": "©",
}
_CANONICAL_H2 = {
    "currently available features": "Key Capabilities",
    "in this readme": "Navigation",
    "features": "Key Capabilities",
    "quick start": "Quick Start",
    "limitations": "Scope and Limitations",
    "known limitations": "Scope and Limitations",
    "current limitations": "Scope and Limitations",
    "project scope and limitations": "Scope and Limitations",
}


def _overlaps(
    start: int,
    end: int,
    operations: list[ReadmeDocumentOperationV1],
) -> bool:
    return any(
        operation.source_byte_start < end and start < operation.source_byte_end
        for operation in operations
    )


def _friendly_option_name(token: str) -> str:
    return token.replace("_", " ").strip().capitalize()


def _canonicalize_h2_text(markdown: str) -> str:
    def replace(match: re.Match[str]) -> str:
        title = match.group("title").strip()
        canonical = _CANONICAL_H2.get(title.casefold())
        return match.group(0) if canonical is None else f"## {canonical}"

    normalized = re.sub(r"(?m)^##[ \t]+(?P<title>[^\r\n]+?)[ \t]*$", replace, markdown)
    for source, target in _CANONICAL_H2.items():
        normalized = re.sub(
            rf"\[{re.escape(source)}\]\(#{re.escape(source.replace(' ', '-'))}\)",
            f"[{target}](#{target.casefold().replace(' ', '-')})",
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


def commercial_directory_spans(context: DocumentRenderContext) -> list[tuple[int, int]]:
    """Return byte spans for standalone commercial directories."""

    spans: list[tuple[int, int]] = []
    for heading in context.headings:
        if heading.level not in {2, 3} or not (
            _COMMERCIAL_HEADING.search(heading.title)
            or _OTHER_PLATFORMS_HEADING.search(heading.title.strip())
        ):
            continue
        section = context.inner_text[heading.start : heading.section_end]
        if _COMMERCIAL_CTA.search(section) or _COMMERCIAL_DIRECTORY.search(section):
            spans.append(
                (
                    context.byte_offset(heading.start),
                    context.byte_offset(heading.section_end),
                )
            )
    return spans


def canonicalize_operation_decorations(
    operations: list[ReadmeDocumentOperationV1],
    *,
    canonical_terms: tuple[str, ...] | None = None,
) -> list[ReadmeDocumentOperationV1]:
    """Apply the no-emoji contract inside already-owned replacement spans."""

    normalized: list[ReadmeDocumentOperationV1] = []
    for operation in operations:
        replacement = _canonicalize_h2_text(
            strip_fenced_code_comments(strip_emoji_decorations(operation.replacement_text))
        )
        replacement = (
            canonicalize_public_markdown(replacement, canonical_terms)
            if canonical_terms is not None
            else canonicalize_public_markdown(replacement)
        )
        if replacement == operation.replacement_text:
            normalized.append(operation)
            continue
        normalized.append(
            operation.model_copy(
                update={
                    "replacement_text": replacement,
                    "replacement_sha256": sha256_hex(replacement),
                    "rationale": (
                        operation.rationale
                        + " Apply the portfolio-wide no-comment and no-emoji presentation "
                        "contract."
                    ),
                }
            )
        )
    return normalized


def build_presentation_policy_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Repair only exact, source-local defects with lossless or policy-owned transforms."""

    operations: list[ReadmeDocumentOperationV1] = []
    occupied = [*existing_operations]

    # Whole-section policy dispositions own their source span before cosmetic
    # heading repairs.  Otherwise a smaller title-case or emoji operation can
    # occupy the heading bytes and silently prevent removal of the commercial
    # directory that contains them.
    for start, end in commercial_directory_spans(context):
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.remove-commercial-directory:{start}",
            operation="remove",
            source=context.source,
            start=start,
            end=end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Remove a standalone commercial call-to-action directory; verified Enterprise "
                "Edition context remains eligible only where it naturally supports reader prose."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    for heading in context.headings:
        canonical = (
            _CANONICAL_H2.get(heading.title.strip().casefold()) if heading.level == 2 else None
        ) or title_case_heading(
            heading.title.strip(), canonical_abbreviations_from_facts(context.facts)
        )
        if canonical is None or heading.title == canonical:
            continue
        start = context.byte_offset(heading.start)
        end = context.byte_offset(heading.heading_end)
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.canonical-heading:{start}",
            operation="replace",
            source=context.source,
            start=start,
            end=end,
            replacement=f"{'#' * heading.level} {canonical}\n",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Apply the accepted repository-presentation heading contract without changing "
                "the section body."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    navigation = context.h2("navigation", "in this readme")
    if navigation is not None:
        body = context.inner_text[navigation.heading_end : navigation.section_end]
        for source_title, target_title in _CANONICAL_H2.items():
            pattern = re.compile(
                rf"\[{re.escape(source_title)}\]\(#{re.escape(source_title.replace(' ', '-'))}\)",
                re.IGNORECASE,
            )
            for match in pattern.finditer(body):
                replacement = f"[{target_title}](#{target_title.casefold().replace(' ', '-')})"
                if match.group(0) == replacement:
                    continue
                character_start = navigation.heading_end + match.start()
                character_end = navigation.heading_end + match.end()
                start = context.byte_offset(character_start)
                end = context.byte_offset(character_end)
                if _overlaps(start, end, occupied):
                    continue
                operation = build_operation(
                    operation_id=f"readme.presentation.canonical-navigation:{start}",
                    operation="replace",
                    source=context.source,
                    start=start,
                    end=end,
                    replacement=replacement,
                    fact_ids=[],
                    treatment="presentation_policy_correction",
                    rationale=(
                        "Keep the Navigation label and anchor aligned with the canonical "
                        "section heading."
                    ),
                )
                operations.append(operation)
                occupied.append(operation)

    canonical_terms = canonical_abbreviations_from_facts(context.facts)
    for correction in public_text_corrections(context.inner_text, canonical_terms):
        if correction.standard_id != "readme.technical_abbreviation_case":
            continue
        start = context.byte_offset(correction.character_start)
        end = context.byte_offset(correction.character_end)
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.canonical-abbreviation:{start}",
            operation="replace",
            source=context.source,
            start=start,
            end=end,
            replacement=correction.replacement,
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=correction.rationale,
        )
        operations.append(operation)
        occupied.append(operation)

    for match in _VAGUE_FUTURE_BULLET.finditer(context.inner_text):
        start = context.byte_offset(match.start())
        end = context.byte_offset(match.end())
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.remove-vague-future:{start}",
            operation="remove",
            source=context.source,
            start=start,
            end=end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Remove an unbounded future-format placeholder that has no verified release scope."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    for match in _RAW_OPTION_BULLET.finditer(context.inner_text):
        start = context.byte_offset(match.start())
        end = context.byte_offset(match.end())
        if _overlaps(start, end, occupied):
            continue
        token = match.group("token")
        replacement = (
            f"{match.group('prefix')}**{_friendly_option_name(token)}** "
            f"(`{token}`) — {match.group('description')}{match.group('newline')}"
        )
        operation = build_operation(
            operation_id=f"readme.presentation.explain-option:{start}",
            operation="replace",
            source=context.source,
            start=start,
            end=end,
            replacement=replacement,
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Retain the exact maintainer-authored option and description while adding a "
                "visitor-readable task label."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    for broken, corrected in _MOJIBAKE_REPLACEMENTS.items():
        cursor = 0
        while (position := context.inner_text.find(broken, cursor)) >= 0:
            start = context.byte_offset(position)
            end = context.byte_offset(position + len(broken))
            cursor = position + len(broken)
            if _overlaps(start, end, occupied):
                continue
            operation = build_operation(
                operation_id=f"readme.presentation.repair-encoding:{start}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=corrected,
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    "Replace a known broken punctuation sequence with its unambiguous UTF-8 "
                    "character without changing the surrounding maintainer-authored claim."
                ),
            )
            operations.append(operation)
            occupied.append(operation)

    for character_start, character_end in emoji_decoration_spans(context.inner_text):
        start = context.byte_offset(character_start)
        end = context.byte_offset(character_end)
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.remove-emoji:{start}",
            operation="remove",
            source=context.source,
            start=start,
            end=end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Apply the portfolio-wide no-emoji presentation contract without changing "
                "technical text or protected code."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    return operations
