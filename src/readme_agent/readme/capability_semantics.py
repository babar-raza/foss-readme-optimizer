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


def _same_public_capability(left: str, right: str) -> bool:
    left_actions = {item.casefold() for item in _ACTION_VERBS.findall(left)}
    right_actions = {item.casefold() for item in _ACTION_VERBS.findall(right)}
    if left_actions and right_actions and left_actions.isdisjoint(right_actions):
        return False
    left_discriminators = {item.upper() for item in _DISCRIMINATOR_TOKEN.findall(left)}
    right_discriminators = {item.upper() for item in _DISCRIMINATOR_TOKEN.findall(right)}
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
    if semantically_repeats(left, right, threshold=0.6):
        return True
    left_domains = capability_domains(left)
    right_domains = capability_domains(right)
    if re.search(r"(?i)\bdocument lifecycle management\b", left + "\n" + right):
        concrete = right if "lifecycle management" in left.casefold() else left
        if re.search(r"(?i)\bdocuments?\b", concrete) and len(_ACTION_VERBS.findall(concrete)) >= 2:
            return True
    comparable_domains = left_domains <= right_domains or right_domains <= left_domains
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
                if _same_public_capability(existing, phrase)
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
    "is_action_led_capability_title",
    "normalize_capability_phrases",
]
