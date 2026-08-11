"""Normalize verified capability phrases for consistent public presentation."""

from __future__ import annotations

import re
from collections.abc import Iterable

from readme_agent.readme.presentation_similarity import (
    semantic_content_words,
    semantically_repeats,
)

_DOMAIN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("validation", re.compile(r"(?i)\b(?:pdf/a|pdf/ua|validat)")),
    (
        "document_lifecycle",
        re.compile(
            r"(?i)\bdocument lifecycle\b|\b(?:create|load|save|merge|inspect)\b.*\bdocuments?\b"
        ),
    ),
    (
        "editing",
        re.compile(r"(?i)\bedit(?:ing)?\b|\breplac(?:e|ement)\b|\bredact(?:ion)?\b"),
    ),
    ("rendering", re.compile(r"(?i)\brender\b|\braster")),
    ("forms", re.compile(r"(?i)\bforms?\b|\bfields?\b")),
    ("annotations", re.compile(r"(?i)\bannotations?\b")),
    ("security", re.compile(r"(?i)\bencrypt|\bdecrypt|\bcompress|\boptimi[sz]")),
    ("metadata", re.compile(r"(?i)\bxmp\b|\bmetadata\b")),
    ("signatures", re.compile(r"(?i)\bsignatures?\b")),
    ("resource_limits", re.compile(r"(?i)\bresource\b.*\blimits?\b")),
    ("pages", re.compile(r"(?i)\bpages?\b")),
    ("extraction", re.compile(r"(?i)\bextract")),
    ("text_images", re.compile(r"(?i)\btext\b.*\bimages?\b|\bimages?\b.*\btext\b")),
)
# Domains whose pattern matches an operation verb (what is being done), as opposed to an
# object/content-type noun (what is being acted on, e.g. "metadata" or "text_images"). Only
# an operation domain is strong enough evidence, alone, to fold a generic restatement into a
# more specific phrase that also names it -- a shared object noun alone is not (two phrases
# extracting different unrelated things can each mention "metadata" without being one capability).
_OPERATION_DOMAINS = frozenset(
    {"document_lifecycle", "editing", "rendering", "security", "extraction", "validation"}
)
_GENERIC_NOUNS = re.compile(
    r"(?i)\b(?:configuration|handling|lifecycle management|operations|support|validation)\b"
)
_ACTION_VERBS = re.compile(
    r"(?i)\b(?:access|add|analy[sz]e|append|apply|build|compress|concatenate|configure|"
    r"convert|create|decode|decrypt|delete|detect|edit|encode|encrypt|export|extract|"
    r"generate|host|import|insert|inspect|load|manage|merge|modify|navigate|open|optimi[sz]e|"
    r"parse|process|read|remove|render|replace|run|save|search|sign|transform|traverse|"
    r"update|validate|verify|work|write)\b"
)
_DISCRIMINATOR_TOKEN = re.compile(r"\b(?:[A-Z]{2,}[A-Z0-9.+-]*|[A-Za-z]*\d[A-Za-z0-9.+-]*)\b")
_READ_DIRECTION = re.compile(
    r"(?i)\b(?:read(?:s|ing)?|load(?:s|ing)?|import(?:s|ing)?|open(?:s|ing)?|pars(?:e|es|ing))\b"
)
_WRITE_DIRECTION = re.compile(
    r"(?i)\b(?:writ(?:e|es|ing)|sav(?:e|es|ing)|export(?:s|ing)?|generat(?:e|es|ing))\b"
)


def capability_domains(value: str) -> frozenset[str]:
    """Return stable semantic domains used to compare capability granularity."""

    return frozenset(name for name, pattern in _DOMAIN_PATTERNS if pattern.search(value))


def _specificity(value: str) -> tuple[int, int, int, int]:
    words = semantic_content_words(value)
    return (
        len(_ACTION_VERBS.findall(value)),
        0 if _GENERIC_NOUNS.search(value) else 1,
        len(words),
        len(value),
    )


def identifier_discriminators(value: str) -> frozenset[str]:
    """Return acronym- or digit-bearing identifier tokens (e.g. "PDF", "128", "A4").

    These distinguish otherwise near-identical statements about different concrete
    things -- a format name, a version, a symbology number -- that generic word-overlap
    similarity would otherwise conflate (e.g. "Code 128" vs "Code 39").
    """

    return frozenset(item.upper() for item in _DISCRIMINATOR_TOKEN.findall(value))


def same_public_capability(left: str, right: str) -> bool:
    """Return whether two phrases represent one public capability."""

    left_actions = {item.casefold() for item in _ACTION_VERBS.findall(left)}
    right_actions = {item.casefold() for item in _ACTION_VERBS.findall(right)}
    if left_actions and right_actions and left_actions.isdisjoint(right_actions):
        return False
    left_discriminators = identifier_discriminators(left)
    right_discriminators = identifier_discriminators(right)
    if left_discriminators and right_discriminators and left_discriminators != right_discriminators:
        return False
    left_reads = _READ_DIRECTION.search(left) is not None
    left_writes = _WRITE_DIRECTION.search(left) is not None
    right_reads = _READ_DIRECTION.search(right) is not None
    right_writes = _WRITE_DIRECTION.search(right) is not None
    if (left_reads and not left_writes and right_writes and not right_reads) or (
        left_writes and not left_reads and right_reads and not right_writes
    ):
        # Opposite data directions are distinct public capabilities even when
        # every other token repeats (for example MSG reading vs MSG writing).
        return False
    left_domains = capability_domains(left)
    right_domains = capability_domains(right)
    if (
        left_domains
        and right_domains
        and left_domains.isdisjoint(right_domains)
        and "document lifecycle management" not in (left + "\n" + right).casefold()
    ):
        # Shared action words such as "create" and "inspect" do not make
        # document lifecycle and digital-signature work the same capability.
        return False
    if semantically_repeats(left, right, threshold=0.6):
        return True
    if re.search(r"(?i)\bdocument lifecycle management\b", left + "\n" + right):
        concrete = right if "lifecycle management" in left.casefold() else left
        if re.search(r"(?i)\bdocuments?\b", concrete) and len(_ACTION_VERBS.findall(concrete)) >= 2:
            return True
    if left_domains <= right_domains:
        narrower = left_domains
    elif right_domains <= left_domains:
        narrower = right_domains
    else:
        narrower = None
    comparable_domains = left_domains == right_domains or (
        narrower is not None and bool(narrower & _OPERATION_DOMAINS)
    )
    return bool(
        left_domains
        and right_domains
        and comparable_domains
        and (_GENERIC_NOUNS.search(left) or _GENERIC_NOUNS.search(right))
    )


def normalize_capability_phrases(values: Iterable[str]) -> list[str]:
    """Keep one most-specific phrase for each repeated public capability.

    Ordering follows the first occurrence. A later phrase replaces an earlier generic
    label only when it expresses the same semantic domain with greater specificity.
    """

    retained: list[str] = []
    for value in values:
        phrase = " ".join(value.strip().rstrip(".").split())
        if not phrase:
            continue
        match_index = next(
            (
                index
                for index, existing in enumerate(retained)
                if same_public_capability(existing, phrase)
            ),
            None,
        )
        if match_index is None:
            retained.append(phrase)
        elif _specificity(phrase) > _specificity(retained[match_index]):
            retained[match_index] = phrase
    return retained


def capability_action_verb(value: str) -> str | None:
    """Return the normalized leading public action verb, when present."""

    match = _ACTION_VERBS.match(value.strip())
    return match.group(0).casefold() if match and match.start() == 0 else None


def is_action_led_capability_title(value: str) -> bool:
    """Return whether a public capability title starts with an approved action verb."""

    return capability_action_verb(value) is not None


__all__ = [
    "capability_action_verb",
    "capability_domains",
    "identifier_discriminators",
    "is_action_led_capability_title",
    "normalize_capability_phrases",
    "same_public_capability",
]
