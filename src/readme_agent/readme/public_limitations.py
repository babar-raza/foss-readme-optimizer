"""Project accepted repository limitations into concise public README language."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from readme_agent.facts.limitation_rendering import limitation_phrases
from readme_agent.facts.public_constraint_text import is_public_constraint_sentence
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.public_vocabulary import (
    canonical_abbreviations_from_facts,
    canonicalize_abbreviations,
)

_ONLY_OUTPUT_RE = re.compile(
    r"^only\s+(?P<formats>.+?)\s+(?:save|output|export)\s+is\s+supported$",
    flags=re.IGNORECASE,
)
_ONLY_FILE_TARGET_RE = re.compile(
    r"^only\s+(?P<formats>.+?)\s+file\s+targets?\s+(?:are|is)\s+supported\s+"
    r"for\s+(?:save|output|export)(?:\s+operations?)?$",
    flags=re.IGNORECASE,
)
_UNSUPPORTED_FORMAT_OPTIONS_RE = re.compile(
    r"^unsupported\s+(?P<kind>format(?:\s*/\s*options?)?|options?)\s+arguments?"
    r"(?:\s*[:.-].*)?$",
    flags=re.IGNORECASE,
)
_PASSWORD_PROTECTED_RE = re.compile(
    r"^password[- ]protected\s+(?:documents?|files?|inputs?)\s+(?:are|is)\s+not\s+supported$",
    flags=re.IGNORECASE,
)
_FORMAT_SEPARATOR_RE = re.compile(r"\s*(?:,|&|\band\b|\bor\b)\s*", flags=re.IGNORECASE)
_UNSUPPORTED_THING_RE = re.compile(r"^unsupported\s+(?P<thing>.+)$", flags=re.IGNORECASE)
_REQUIRES_RE = re.compile(r"^(?P<subject>.+?)\s+requires\s+(?P<object>.+)$")
_DETERMINED_OBJECT_RE = re.compile(
    r"(?i)^(?:a|an|the|one|two|three|exactly|at\s+least|at\s+most|no|any|all)\b"
)


def _pluralized(noun_phrase: str) -> str:
    words = noun_phrase.split()
    if not words:
        return noun_phrase
    last = words[-1]
    lowered = last.casefold()
    if lowered.endswith(("s", "x", "z", "ch", "sh")):
        plural = last + "es"
    elif lowered.endswith("y") and len(lowered) > 1 and lowered[-2] not in "aeiou":
        plural = last[:-1] + "ies"
    else:
        plural = last + "s"
    return " ".join([*words[:-1], plural])


def _sentence_cased(text: str) -> str:
    return text[:1].upper() + text[1:] if text and text[:1].islower() else text


def _readable_requirement_object(value: str) -> str:
    normalized = " ".join(value.split())
    if re.fullmatch(r"(?i)one\s+input", normalized):
        return "exactly one input"
    if "," in normalized and " and " not in normalized.casefold():
        items = [item.strip() for item in normalized.split(",") if item.strip()]
        if len(items) >= 2:
            joined = _natural_join(items)
            return f"{joined} entries"
    last_word = normalized.split()[-1] if normalized.split() else ""
    if (
        not _DETERMINED_OBJECT_RE.match(normalized)
        and "," not in normalized
        and last_word.islower()
    ):
        article = "an" if normalized[:1].casefold() in "aeiou" else "a"
        return f"{article} {normalized}"
    return normalized


def _readable_limitation_sentence(normalized: str) -> str:
    unsupported = _UNSUPPORTED_THING_RE.fullmatch(normalized)
    if unsupported is not None and not re.search(
        r"\b(?:are|is|return|returns|treated)\b", normalized, flags=re.IGNORECASE
    ):
        thing = " ".join(unsupported.group("thing").split())
        return f"Unsupported {_pluralized(thing)} are rejected"
    requirement = _REQUIRES_RE.fullmatch(normalized)
    if requirement is not None:
        subject = " ".join(requirement.group("subject").split())
        subject_noun = subject.split()[-1] if subject.split() else ""
        if subject_noun.islower():
            return (
                f"{_sentence_cased(_pluralized(subject))} require "
                f"{_readable_requirement_object(requirement.group('object'))}"
            )
    return _sentence_cased(normalized)


@dataclass(frozen=True)
class _PublicLimitation:
    category: str
    text: str
    equivalence_key: str
    source_values: tuple[object, ...]


def _natural_join(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return " and ".join(values)
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def _output_formats(value: str, canonical_terms: tuple[str, ...]) -> list[str]:
    formats: list[str] = []
    for part in _FORMAT_SEPARATOR_RE.split(value):
        normalized = re.sub(r"(?i)\s+files?$", "", part.strip()).lstrip(".").strip()
        if not normalized:
            continue
        normalized = canonicalize_abbreviations(normalized, canonical_terms)
        if normalized.casefold() not in {item.casefold() for item in formats}:
            formats.append(normalized)
    return formats


def _public_limitation(
    phrase: str,
    canonical_terms: tuple[str, ...],
    source_value: object,
) -> _PublicLimitation:
    normalized = " ".join(re.sub(r"`{2,}", "`", phrase).strip().rstrip(". ").split())
    output_match = _ONLY_OUTPUT_RE.fullmatch(normalized) or _ONLY_FILE_TARGET_RE.fullmatch(
        normalized
    )
    if output_match is not None:
        formats = _output_formats(output_match.group("formats"), canonical_terms)
        if formats:
            format_names = _natural_join(formats)
            text = f"Output is limited to {format_names} files."
            key = "output:" + ",".join(sorted(item.casefold() for item in formats))
            return _PublicLimitation("output_restriction", text, key, (source_value,))
    if _PASSWORD_PROTECTED_RE.fullmatch(normalized):
        return _PublicLimitation(
            "input_restriction",
            "Password-protected documents are not supported as input.",
            "input:password-protected",
            (source_value,),
        )
    unsupported = _UNSUPPORTED_FORMAT_OPTIONS_RE.fullmatch(normalized)
    if unsupported is not None:
        kind = unsupported.group("kind").casefold().replace(" ", "")
        if "/" in kind:
            text = "Only documented output formats and save options are supported."
        elif kind.startswith("format"):
            text = "Only documented output formats are supported."
        else:
            text = "Only documented save options are supported."
        return _PublicLimitation(
            "generic_output_restriction",
            text,
            f"generic-output:{kind}",
            (source_value,),
        )
    readable = _readable_limitation_sentence(normalized)
    text = canonicalize_abbreviations(readable, canonical_terms).rstrip(". ") + "."
    equivalence_key = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    return _PublicLimitation("other", text, f"other:{equivalence_key}", (source_value,))


def _source_items(facts: ProductFactsV2) -> list[tuple[str, object]]:
    fact = facts.selected_fact("product.limitations")
    if not isinstance(fact.value, list):
        return []
    items: list[tuple[str, object]] = []
    for item in fact.value:
        phrase = (
            item
            if isinstance(item, str)
            else item.get("statement")
            if isinstance(item, dict)
            else None
        )
        if isinstance(phrase, str) and phrase.strip():
            items.append((phrase, item))
    return items


def _public_limitations(facts: ProductFactsV2) -> list[_PublicLimitation]:
    try:
        fact = facts.selected_fact("product.limitations")
    except KeyError:
        return []
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
    ):
        return []
    sources = _source_items(facts)
    safe_sources = [
        (phrases[0], value)
        for phrase, value in sources
        if (phrases := limitation_phrases([value]))
        if is_public_constraint_sentence(phrases[0])
        or _UNSUPPORTED_FORMAT_OPTIONS_RE.fullmatch(" ".join(phrases[0].split()))
    ]
    if not safe_sources:
        return []
    canonical_terms = canonical_abbreviations_from_facts(facts)
    limitations = [
        _public_limitation(
            phrase,
            canonical_terms,
            source_value,
        )
        for phrase, source_value in safe_sources
    ]
    if any(item.category == "output_restriction" for item in limitations):
        limitations = [
            item for item in limitations if item.category != "generic_output_restriction"
        ]
    deduplicated: list[_PublicLimitation] = []
    by_key: dict[str, int] = {}
    for item in limitations:
        prior = by_key.get(item.equivalence_key)
        if prior is None:
            by_key[item.equivalence_key] = len(deduplicated)
            deduplicated.append(item)
            continue
        existing = deduplicated[prior]
        deduplicated[prior] = _PublicLimitation(
            existing.category,
            existing.text,
            existing.equivalence_key,
            (*existing.source_values, *item.source_values),
        )
    return deduplicated


def public_limitation_phrases(facts: ProductFactsV2) -> list[str]:
    """Return deduplicated visitor copy for accepted repository limitation facts."""

    return [item.text for item in _public_limitations(facts)]


def public_limitation_fact_coordinates(
    text: str,
    fact_id: str,
    facts: ProductFactsV2,
) -> list[StructuredFactCoordinateV1]:
    """Bind public limitation prose to the exact source fact items it projects."""

    normalized = " ".join(re.sub(r"[`*_~]", "", text).casefold().split())
    coordinates: list[StructuredFactCoordinateV1] = []
    for limitation in _public_limitations(facts):
        phrase = " ".join(re.sub(r"[`*_~]", "", limitation.text).casefold().split())
        if phrase not in normalized:
            continue
        for value in limitation.source_values:
            payload = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            value_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            coordinates.append(
                StructuredFactCoordinateV1(
                    fact_id=fact_id,
                    field="product.limitations",
                    path=f"/items/{value_sha256[:16]}",
                    value_sha256=value_sha256,
                )
            )
    return sorted(set(coordinates), key=lambda item: (item.path, item.value_sha256))


__all__ = ["public_limitation_fact_coordinates", "public_limitation_phrases"]
