"""Bind complete source claims to accepted literal or structured repository facts."""

from __future__ import annotations

import ast
import hashlib
import io
import re
import tokenize
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_coordinates import (
    literal_list_fact_coordinates,
    structured_fact_coordinates,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.fact_grounding import literal_fact_ids
from readme_agent.readme.source_claim_conversion_binding import (
    conversion_source_claim_fact_coordinates,
)
from readme_agent.readme.source_claim_structured_matching import (
    structured_source_claim_fact_ids,
    verified_issue_route_fact_ids,
)

_MARKDOWN = re.compile(r"[`*_>#\[\]()]|^\s*[-+]\s*", re.MULTILINE)
_FACT_PREFIX = re.compile(r"^(?:input|output)\s+format\s*:\s*", re.IGNORECASE)
_ACCEPTED_STATES = {"verified", "policy_approved"}
_FENCE = re.compile(
    r"^\s*```(?P<language>python|py)\s*\r?\n(?P<code>.*)\r?\n```\s*$",
    re.DOTALL | re.IGNORECASE,
)
_EXACT_VALUE_FIELDS = {
    "product.audience",
    "product.capabilities",
    "product.formats",
    "product.identity",
    "product.license",
    "product.limitations",
    "product.problems_solved",
    "repository.public_guidance",
}
_STRUCTURED_ONLY_FIELDS = {
    "api.public_surface",
    "installation.coordinates",
    "installation.optional_extras",
    "installation.verified_acquisition",
}
_FACT_VARIANT_CACHE_MAX_GRAPHS = 16
_FACT_VARIANT_CACHE: OrderedDict[
    int,
    tuple[weakref.ReferenceType[ProductFactsV2], dict[str, frozenset[str]]],
] = OrderedDict()
_FACT_VARIANT_CACHE_LOCK = RLock()
_CLAIM_BINDING_CACHE_MAX_DOCUMENTS = 32
_CLAIM_BINDING_CACHE: OrderedDict[
    tuple[int, int],
    tuple[
        weakref.ReferenceType[ProductFactsV2],
        str,
        dict[
            tuple[str, int, int, str],
            CompleteSourceClaimFactBindingV1 | None,
        ],
    ],
] = OrderedDict()
_CLAIM_BINDING_CACHE_LOCK = RLock()


@dataclass(frozen=True)
class CompleteSourceClaimFactBindingV1:
    """Accepted facts and exact coordinates covering one complete material claim."""

    fact_ids: frozenset[str]
    fact_coordinates: tuple[StructuredFactCoordinateV1, ...]


def _normalized(value: str) -> str:
    return " ".join(_MARKDOWN.sub("", value).casefold().split()).strip(" .")


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for value_item in value for item in _strings(value_item)]
    if isinstance(value, dict):
        return [item for value_item in value.values() for item in _strings(value_item)]
    return []


def _python_code(value: str) -> str | None:
    match = _FENCE.fullmatch(value)
    return match.group("code") + "\n" if match is not None else None


def _python_ast(value: str) -> str | None:
    try:
        return ast.dump(ast.parse(value), include_attributes=False)
    except SyntaxError:
        return None


def _comment_free_python(value: str) -> str | None:
    try:
        tokens = tokenize.generate_tokens(io.StringIO(value).readline)
        cleaned = tokenize.untokenize(token for token in tokens if token.type != tokenize.COMMENT)
    except (IndentationError, tokenize.TokenError):
        return None
    return cleaned.rstrip() + "\n"


def verified_comment_free_python_example(claim_text: str, verified_code: str) -> str | None:
    """Remove Python comments only when the verified executable AST stays exact."""

    source_code = _python_code(claim_text)
    expected_ast = _python_ast(verified_code)
    if source_code is None or expected_ast is None or _python_ast(source_code) != expected_ast:
        return None
    cleaned = _comment_free_python(source_code)
    if cleaned is None or _python_ast(cleaned) != expected_ast:
        return None
    language = _FENCE.fullmatch(claim_text).group("language")  # type: ignore[union-attr]
    return f"```{language}\n{cleaned}```"


def verified_example_code(value: object) -> str | None:
    """Return one nonempty verified example payload."""

    if not isinstance(value, dict):
        return None
    code = value.get("code")
    return code if isinstance(code, str) and code.strip() else None


def verified_repository_example_code(
    claim_text: str,
    facts: ProductFactsV2,
) -> tuple[str, str] | None:
    """Return the selected fact and exact statically verified repository example."""

    fact_id = facts.selected_fact_ids.get("repository.examples")
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    code = _python_code(claim_text)
    if (
        code is None
        or fact.verification_state not in _ACCEPTED_STATES
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return None
    inline = fact.value.get("inline_examples")
    if not isinstance(inline, list):
        return None
    exact = [
        item
        for item in inline
        if isinstance(item, dict)
        and item.get("static_api_verified") is True
        and isinstance(item.get("code"), str)
        and item["code"].rstrip() + "\n" == code
    ]
    return (fact_id, code) if len(exact) == 1 else None


def _build_fact_variants(facts: ProductFactsV2, fact_id: str) -> frozenset[str]:
    fact = facts.fact_by_id(fact_id)
    view = visitor_fact_render_view(facts, fact.field)
    values: list[str] = []
    if view is not None and view.fact_id == fact_id:
        values.extend(view.phrases)
    if fact.field in _EXACT_VALUE_FIELDS:
        values.extend(_strings(fact.value))
    return frozenset(
        normalized
        for raw in values
        if (normalized := _normalized(_FACT_PREFIX.sub("", raw))) and len(normalized) >= 2
    )


def _fact_variants(facts: ProductFactsV2, fact_id: str) -> frozenset[str]:
    """Reuse normalized variants for one immutable product-fact graph."""

    graph_key = id(facts)
    with _FACT_VARIANT_CACHE_LOCK:
        cached = _FACT_VARIANT_CACHE.get(graph_key)
        if cached is not None and cached[0]() is facts:
            variants = cached[1].get(fact_id)
            if variants is not None:
                _FACT_VARIANT_CACHE.move_to_end(graph_key)
                return variants
        elif cached is not None:
            del _FACT_VARIANT_CACHE[graph_key]

    variants = _build_fact_variants(facts, fact_id)
    with _FACT_VARIANT_CACHE_LOCK:
        cached = _FACT_VARIANT_CACHE.get(graph_key)
        if cached is None or cached[0]() is not facts:
            cached = (weakref.ref(facts), {})
            _FACT_VARIANT_CACHE[graph_key] = cached
        cached[1][fact_id] = variants
        _FACT_VARIANT_CACHE.move_to_end(graph_key)
        while len(_FACT_VARIANT_CACHE) > _FACT_VARIANT_CACHE_MAX_GRAPHS:
            _FACT_VARIANT_CACHE.popitem(last=False)
    return variants


def _clear_fact_variant_cache() -> None:
    """Clear the bounded cache for deterministic test isolation."""

    with _FACT_VARIANT_CACHE_LOCK:
        _FACT_VARIANT_CACHE.clear()
    with _CLAIM_BINDING_CACHE_LOCK:
        _CLAIM_BINDING_CACHE.clear()


def _covered_by_fact_variants(
    claim: str,
    variants_by_fact: dict[str, frozenset[str]],
) -> set[str]:
    covered = bytearray(len(claim))
    used: set[str] = set()
    ordered = sorted(
        (
            (fact_id, variant)
            for fact_id, variants in variants_by_fact.items()
            for variant in variants
            if variant
        ),
        key=lambda item: len(item[1]),
        reverse=True,
    )
    for fact_id, variant in ordered:
        cursor = 0
        while (start := claim.find(variant, cursor)) >= 0:
            covered[start : start + len(variant)] = b"\x01" * len(variant)
            used.add(fact_id)
            cursor = start + len(variant)
    remainder = "".join(character for index, character in enumerate(claim) if not covered[index])
    return used if not re.sub(r"[^a-z0-9]+", "", remainder) else set()


def accepted_source_claim_fact_ids(claim_text: str, facts: ProductFactsV2) -> set[str]:
    """Return selected accepted literal facts covering the complete source claim."""

    literal_ids = set(literal_fact_ids(claim_text, facts, list(facts.selected_fact_ids.values())))
    result: set[str] = set()
    if repository_example := verified_repository_example_code(claim_text, facts):
        result.add(repository_example[0])
    variants_by_fact: dict[str, frozenset[str]] = {}
    normalized_claim = _normalized(claim_text)
    for fact_id in facts.selected_fact_ids.values():
        fact = facts.fact_by_id(fact_id)
        if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
            continue
        if fact.field == "example.minimal":
            code = verified_example_code(fact.value)
            if code is not None and verified_comment_free_python_example(claim_text, code):
                result.add(fact_id)
            continue
        if fact.field in _STRUCTURED_ONLY_FIELDS:
            continue
        if fact_id in literal_ids or fact.field in _EXACT_VALUE_FIELDS:
            variants_by_fact[fact_id] = _fact_variants(facts, fact_id)
    result.update(_covered_by_fact_variants(normalized_claim, variants_by_fact))
    result.update(verified_issue_route_fact_ids(claim_text, facts))
    return result


def _build_complete_source_claim_fact_binding(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
) -> CompleteSourceClaimFactBindingV1 | None:
    """Build one hash-current claim binding from accepted evidence."""

    document_bytes = document.encode("utf-8")
    if claim.source_byte_end > len(document_bytes):
        raise ValueError("source claim exceeds immutable document bytes")
    claim_bytes = document_bytes[claim.source_byte_start : claim.source_byte_end]
    if hashlib.sha256(claim_bytes).hexdigest() != claim.content_sha256:
        raise ValueError("source claim hash does not match immutable document bytes")
    text = claim_bytes.decode("utf-8")
    literal_ids = accepted_source_claim_fact_ids(text, facts)
    coordinates = list(structured_fact_coordinates(document, claim, facts))
    coordinates.extend(conversion_source_claim_fact_coordinates(text, facts))
    structured_ids = structured_source_claim_fact_ids(document, claim, text, facts)
    fact_ids = frozenset({*literal_ids, *structured_ids, *(item.fact_id for item in coordinates)})
    if not fact_ids:
        return None
    for fact_id in fact_ids:
        fact = facts.fact_by_id(fact_id)
        if fact.field in {
            "product.capabilities",
            "product.compatibility",
            "product.formats",
            "product.limitations",
            "product.problems_solved",
        }:
            coordinates.extend(literal_list_fact_coordinates(text, fact_id, fact.field, fact.value))
    coordinates = sorted(
        set(coordinates),
        key=lambda item: (item.fact_id, item.path, item.value_sha256),
    )
    return CompleteSourceClaimFactBindingV1(
        fact_ids=fact_ids,
        fact_coordinates=tuple(coordinates),
    )


def complete_source_claim_fact_binding(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
) -> CompleteSourceClaimFactBindingV1 | None:
    """Bind one immutable claim once per facts/document pair."""

    document_key = (id(facts), id(document))
    claim_key = (
        claim.claim_id,
        claim.source_byte_start,
        claim.source_byte_end,
        claim.content_sha256,
    )
    with _CLAIM_BINDING_CACHE_LOCK:
        cached = _CLAIM_BINDING_CACHE.get(document_key)
        if cached is not None and cached[0]() is facts and cached[1] is document:
            if claim_key in cached[2]:
                _CLAIM_BINDING_CACHE.move_to_end(document_key)
                return cached[2][claim_key]
        elif cached is not None:
            del _CLAIM_BINDING_CACHE[document_key]

    binding = _build_complete_source_claim_fact_binding(document, claim, facts)
    with _CLAIM_BINDING_CACHE_LOCK:
        cached = _CLAIM_BINDING_CACHE.get(document_key)
        if cached is None or cached[0]() is not facts or cached[1] is not document:
            cached = (weakref.ref(facts), document, {})
            _CLAIM_BINDING_CACHE[document_key] = cached
        cached[2][claim_key] = binding
        _CLAIM_BINDING_CACHE.move_to_end(document_key)
        while len(_CLAIM_BINDING_CACHE) > _CLAIM_BINDING_CACHE_MAX_DOCUMENTS:
            _CLAIM_BINDING_CACHE.popitem(last=False)
    return binding


def python_claim_has_comments(claim_text: str) -> bool:
    """Return whether one exact Python fence includes comment tokens."""

    return tokenize.COMMENT in {
        token.type
        for token in tokenize.generate_tokens(io.StringIO(_python_code(claim_text) or "").readline)
    }


__all__ = [
    "CompleteSourceClaimFactBindingV1",
    "accepted_source_claim_fact_ids",
    "complete_source_claim_fact_binding",
    "python_claim_has_comments",
    "verified_comment_free_python_example",
    "verified_example_code",
    "verified_repository_example_code",
]
