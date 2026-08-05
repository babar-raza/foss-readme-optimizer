"""Authorize exact source claims from accepted facts before verified preservation."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.fact_grounding import literal_fact_ids

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
}


@dataclass(frozen=True)
class SourceClaimAssurance:
    preserve_ranges: list[tuple[int, int]]
    correction_ranges: list[tuple[int, int]]


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


def _verified_example_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    code = value.get("code")
    return code if isinstance(code, str) and code.strip() else None


def _fact_variants(facts: ProductFactsV2, fact_id: str) -> set[str]:
    fact = facts.fact_by_id(fact_id)
    view = visitor_fact_render_view(facts, fact.field)
    values: list[str] = []
    if view is not None and view.fact_id == fact_id:
        values.extend(view.phrases)
    if fact.field in _EXACT_VALUE_FIELDS:
        values.extend(_strings(fact.value))
    return {
        normalized
        for raw in values
        if (normalized := _normalized(_FACT_PREFIX.sub("", raw))) and len(normalized) >= 2
    }


def _covered_by_fact_variants(claim: str, variants_by_fact: dict[str, set[str]]) -> set[str]:
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
    """Return selected accepted facts exactly represented by one source claim."""

    literal_ids = set(literal_fact_ids(claim_text, facts, list(facts.selected_fact_ids.values())))
    result: set[str] = set()
    variants_by_fact: dict[str, set[str]] = {}
    normalized_claim = _normalized(claim_text)
    for fact_id in facts.selected_fact_ids.values():
        fact = facts.fact_by_id(fact_id)
        if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
            continue
        if fact.field == "example.minimal":
            verified_code = _verified_example_code(fact.value)
            if verified_code is not None and verified_comment_free_python_example(
                claim_text, verified_code
            ):
                result.add(fact_id)
            continue
        if fact.field in {"installation.coordinates", "installation.verified_acquisition"}:
            if fact_id in literal_ids:
                result.add(fact_id)
            continue
        if fact_id in literal_ids:
            variants_by_fact[fact_id] = _fact_variants(facts, fact_id)
    result.update(_covered_by_fact_variants(normalized_claim, variants_by_fact))
    return result


def build_source_claim_assurance(
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
) -> SourceClaimAssurance:
    """Separate fact-authorized preservation from unsupported correction candidates."""

    source = source_text.encode("utf-8")
    preserve: list[tuple[int, int]] = []
    correction: list[tuple[int, int]] = []
    for claim in assessment.material_claims:
        coordinates = (claim.source_byte_start, claim.source_byte_end)
        if claim.disposition != "preserve":
            continue
        text = source[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        accepted = accepted_source_claim_fact_ids(text, facts)
        verified_example = facts.selected_fact("example.minimal")
        verified_code = _verified_example_code(verified_example.value)
        comment_correction = bool(
            verified_code
            and verified_comment_free_python_example(text, verified_code)
            and tokenize.COMMENT
            in {
                token.type
                for token in tokenize.generate_tokens(
                    io.StringIO(_python_code(text) or "").readline
                )
            }
        )
        target = preserve if accepted and not comment_correction else correction
        target.append(coordinates)
    return SourceClaimAssurance(
        preserve_ranges=sorted(preserve),
        correction_ranges=sorted(correction),
    )
