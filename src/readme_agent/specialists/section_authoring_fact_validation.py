"""Reject section prose that contradicts deterministic fact coordinates."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from readme_agent.readme.presentation_similarity import semantic_content_words
from readme_agent.specialists.section_authoring_contracts import (
    SectionAuthoringFactV1,
    SectionAuthoringPacketV1,
    SectionClusterUnitV1,
)

_REGISTRY_NAME = re.compile(
    r"(?i)\b(?:pypi|nuget|maven central|npm(?:js)?|crates\.io|go (?:module )?proxy|"
    r"(?:public )?(?:python )?package registr(?:y|ies))\b"
)
_CLOSED_WORLD_DENIAL = re.compile(
    r"(?i)\b(?:does not|doesn't|do not|don't|cannot|can't)\s+support\b[^.\n]{0,140}"
    r"\b(?:other|beyond|except|outside|only)\b|\bonly supports?\b"
)
_UNSUPPORTED_POSITIONING = re.compile(
    r"(?i)\b(?:complete|comprehensive|effortless|ensur(?:e|es|ing)|powerful|rapid|reliable|"
    r"robust|seamless|production[- ]ready|fully implemented|(?:smallest|simplest) possible|"
    r"only supported|"
    r"requiring only)\b|"
    r"\bwithout (?:any )?external [a-z][a-z-]*\b"
)
_SIBLING_GENERIC_WORDS = frozenset(
    {"3d", "and", "file", "format", "includ", "operation", "support", "system"}
)


def _structured_values(value: object, keys: set[str]) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, (str, int, float)):
                rendered = str(item).strip()
                if rendered:
                    yield key, rendered
            yield from _structured_values(item, keys)
    elif isinstance(value, list):
        for item in value:
            yield from _structured_values(item, keys)


def _contains_literal(text: str, literal: str) -> bool:
    if len(literal) < 2:
        return False
    if re.fullmatch(r"[A-Za-z0-9_.+-]+", literal):
        return (
            re.search(
                rf"(?<![A-Za-z0-9_.+-]){re.escape(literal)}(?![A-Za-z0-9_.+-])",
                text,
                flags=re.IGNORECASE,
            )
            is not None
        )
    return literal.casefold() in text.casefold()


def _deterministic_literal_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
) -> list[str]:
    errors: list[str] = []
    owned_keys_by_field = {
        "installation.verified_acquisition": {"name", "version", "source_revision"},
        "installation.coordinates": {"name", "version", "manifest_path"},
        "example.minimal": {"code", "command", "module", "class", "function"},
        "api.public_surface": {"module", "name", "export", "signature"},
    }
    for fact in cited_facts:
        keys = owned_keys_by_field.get(fact.field)
        if keys is None:
            continue
        for key, literal in sorted(set(_structured_values(fact.value, keys))):
            if _contains_literal(unit.text, literal):
                errors.append(f"{fact.field} {key!r} literal belongs to deterministic rendering")
    return errors


def _example_operation_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
) -> list[str]:
    errors: list[str] = []
    operation_tokens = {
        "save": (r"\b(?:save|saves|saved|saving)\b", (".save", "save(")),
        "export": (r"\b(?:export|exports|exported|exporting)\b", (".export", "export(")),
        "write": (r"\b(?:write|writes|wrote|written|writing)\b", (".write", "write(")),
        "add": (
            r"\b(?:add|adds|added|adding)\b",
            (".add", "add(", ".append", "append(", ".insert", "insert("),
        ),
    }
    prose = unit.text.casefold()
    for fact in cited_facts:
        if fact.field != "example.minimal" or not isinstance(fact.value, dict):
            continue
        code = str(fact.value.get("code") or "").casefold()
        for operation, (pattern, tokens) in operation_tokens.items():
            if re.search(pattern, prose, flags=re.IGNORECASE) and not any(
                token in code for token in tokens
            ):
                errors.append(
                    f"example.minimal does not execute the claimed {operation!r} operation"
                )
    return errors


def _sibling_item_conflation_errors(
    unit: SectionClusterUnitV1,
    cited_facts: Iterable[SectionAuthoringFactV1],
) -> list[str]:
    errors: list[str] = []
    unit_words = semantic_content_words(unit.heading + " " + unit.text)
    for fact in cited_facts:
        if not isinstance(fact.value, list):
            continue
        items = [item for item in fact.value if isinstance(item, str) and item.strip()]
        if len(items) < 2:
            continue
        word_sets = [semantic_content_words(item) - _SIBLING_GENERIC_WORDS for item in items]
        exclusive_sets = [
            words - set().union(*(other for index, other in enumerate(word_sets) if index != item))
            for item, words in enumerate(word_sets)
        ]
        matched_items = [words & unit_words for words in exclusive_sets if words & unit_words]
        if len(matched_items) > 1:
            errors.append(
                f"{fact.field} unit combines {len(matched_items)} independent sibling items"
            )
    return errors


def section_authoring_fact_errors(
    packet: SectionAuthoringPacketV1,
    unit: SectionClusterUnitV1,
) -> list[str]:
    """Return contradictions and deterministic-literal ownership violations.

    Fact IDs establish provenance, but they do not make arbitrary prose true. This validator
    handles the structured coordinates for which a false rewrite is both high-risk and
    mechanically decidable. Broader natural-language factuality remains independently checked
    after complete candidate assembly.
    """

    facts_by_id = {fact.fact_id: fact for fact in packet.accepted_facts}
    cited_facts = [facts_by_id[fact_id] for fact_id in unit.fact_ids if fact_id in facts_by_id]
    errors = _deterministic_literal_errors(unit, cited_facts)
    errors.extend(_example_operation_errors(unit, cited_facts))
    if re.search(r"(?i)\baspose[.\w-]+", unit.text):
        if packet.public_product_name not in unit.text:
            errors.append(
                f"product identity must preserve exact public name {packet.public_product_name!r}"
            )
    if _CLOSED_WORLD_DENIAL.search(unit.text):
        errors.append("positive capability inventories cannot authorize closed-world denials")
    # Capability entries promise one scannable concept per unit, so fusing independent list
    # items changes their meaning (for example, animation becomes an export format). An opening
    # summary intentionally synthesizes several verified purposes/capabilities and must not be
    # forced into one sentence per list item.
    if packet.task_family == "capability_entry_cluster":
        errors.extend(_sibling_item_conflation_errors(unit, cited_facts))
    cited_values = json.dumps(
        [fact.value for fact in cited_facts],
        sort_keys=True,
        default=str,
    ).casefold()
    unsupported_positioning = sorted(
        {
            match.group(0).casefold()
            for match in _UNSUPPORTED_POSITIONING.finditer(unit.text)
            if match.group(0).casefold() not in cited_values
        }
    )
    if unsupported_positioning:
        errors.append(
            "unsupported quality, completeness, guarantee, or dependency wording: "
            f"{unsupported_positioning}"
        )
    acquisitions = [
        fact
        for fact in packet.accepted_facts
        if fact.field == "installation.verified_acquisition" and isinstance(fact.value, dict)
    ]
    for acquisition in acquisitions:
        value = acquisition.value
        assert isinstance(value, dict)
        source_only = value.get("method") == "source_build" or value.get("outcome") == (
            "SOURCE_BUILD_VERIFIED"
        )
        if not source_only:
            continue
        registry_publication = _REGISTRY_NAME.search(unit.text)
        if registry_publication:
            errors.append(
                "source-build acquisition cannot authorize a package-registry publication "
                "or installation claim"
            )
    return errors


__all__ = ["section_authoring_fact_errors"]
