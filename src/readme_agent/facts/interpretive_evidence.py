"""Deterministic groundedness/citation gate for free-text interpretive fields.

`product.audience` and `product.problems_solved` are the only two
`REQUIRED_PRODUCT_FIELDS` that are genuinely interpretive free text with no existing
mechanical check today -- unlike `product.capabilities`/`product.formats`/
`product.limitations`, which already have one via
`facts/policy_evidence.py::evidence_fact_candidate()` (source-code evidence paths and
required symbols). That check does not apply here: there is no file/symbol that proves an
audience or problem-statement claim. Instead, every drafted claim must cite other
already-established facts from the same `ProductFactsV2` object, and every significant
product word in the claim text must literally appear in at least one of its cited facts'
values. Audience claims receive only the fixed grammatical scaffold declared below;
that scaffold cannot introduce a product, feature, quality, use case, or outcome.
This is intentionally a crude, deterministic lexical-coverage check -- not a semantic one
-- so its pass/fail behavior stays simple and predictable rather than another model
grading its own homework.

Mirrors `facts/gating.py::validate_claim_citations()`'s citation-resolution shape (fact
exists, is the field's currently-selected fact, and is in a trustworthy verification
state) rather than reimplementing fact lookup from scratch.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.gating import _ACCEPTED_STATES
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InterpretiveClaimV1(_StrictModel):
    """One drafted free-text claim plus the already-established facts that ground it."""

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    supporting_fact_ids: list[str] = Field(default_factory=list)


_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A small, fixed set of common English function words. Deliberately not exhaustive or
# linguistically principled -- this whole gate is a crude lexical check by design, and an
# arbitrary-but-fixed stopword list keeps it deterministic rather than "smart".
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "as",
        "at",
        "by",
        "from",
        "into",
        "than",
        "then",
        "so",
        "such",
        "we",
        "you",
        "your",
        "our",
        "their",
        "they",
        "them",
        "he",
        "she",
        "his",
        "her",
        "not",
        "no",
        "yes",
        "do",
        "does",
        "did",
        "can",
        "could",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "must",
        "also",
        "very",
        "more",
        "most",
        "some",
        "any",
        "all",
        "each",
        "other",
        "which",
        "who",
        "whom",
        "what",
        "when",
        "where",
        "why",
        "how",
        "if",
        "up",
        "down",
        "out",
        "about",
        "over",
        "under",
        "again",
        "further",
        "just",
        "only",
        "own",
        "same",
        "too",
    }
)

# Audience claims need a minimal grammatical frame that repository facts do not
# mechanically contain. Keep this deliberately field-specific and tiny: it can
# describe who uses the evidenced product, but cannot introduce a product,
# feature, quality, use case, or outcome that the citations do not contain.
_FIELD_SCAFFOLD_TOKENS: dict[str, frozenset[str]] = {
    "product.audience": frozenset({"developers", "users", "using"}),
}


def _significant_tokens(text: str, field_name: str | None = None) -> list[str]:
    """Lowercase, tokenize, and drop stopwords/single characters -- deterministic, no NLP."""

    ignored = _STOPWORDS | _FIELD_SCAFFOLD_TOKENS.get(field_name or "", frozenset())
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if token not in ignored and len(token) > 1
    ]


def _value_text(value: object) -> str:
    if isinstance(value, str):
        return value.lower()
    return json.dumps(value, sort_keys=True, default=str).lower()


def _resolve_cited_fact(facts_so_far: ProductFactsV2, fact_id: str) -> FactRecordV2 | None:
    """Same shape as gating.py::validate_claim_citations(): must exist, be the field's
    currently-selected fact, and sit in a trustworthy verification state."""

    try:
        fact = facts_so_far.fact_by_id(fact_id)
    except KeyError:
        return None
    if facts_so_far.selected_fact_ids.get(fact.field) != fact_id:
        return None
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    return fact


def _audience_platform_values(facts: list[FactRecordV2]) -> set[str]:
    """Return literal platform identifiers that may complete the audience scaffold."""

    values: set[str] = set()
    for fact in facts:
        if fact.field == "product.platforms":
            rows = fact.value if isinstance(fact.value, list) else [fact.value]
            values.update(str(row).strip().casefold() for row in rows if str(row).strip())
        elif fact.field == "product.identity" and isinstance(fact.value, dict):
            for key in ("platform", "ecosystem"):
                value = str(fact.value.get(key) or "").strip()
                if value:
                    values.add(value.casefold())
    return values


def _audience_shape_failure(
    claim: InterpretiveClaimV1,
    cited_facts: list[FactRecordV2],
) -> str | None:
    """Require a complete audience label, never capability text forced into a fragment."""

    match = re.fullmatch(r"developers using (.+?)\.?", claim.text.strip(), flags=re.IGNORECASE)
    platforms = _audience_platform_values(cited_facts)
    if match is None or match.group(1).strip().casefold() not in platforms:
        return (
            f"{claim.claim_id}: audience must be exactly 'Developers using "
            "<cited literal platform or ecosystem>.'"
        )
    return None


def _claim_result(
    field_name: str,
    claim: InterpretiveClaimV1,
    facts_so_far: ProductFactsV2,
) -> tuple[bool, float, list[str]]:
    """Evaluate one claim against (a) non-empty citations, (b) citation resolution, and
    (c) full lexical coverage. Returns (passed, coverage_ratio, failure_reasons)."""

    if not claim.supporting_fact_ids:
        return False, 0.0, [f"{claim.claim_id}: rejected -- no supporting_fact_ids cited"]

    reasons: list[str] = []
    resolved_facts: list[FactRecordV2] = []
    for fact_id in claim.supporting_fact_ids:
        cited = _resolve_cited_fact(facts_so_far, fact_id)
        if cited is None:
            reasons.append(
                f"{claim.claim_id}: cited fact {fact_id!r} does not resolve to a "
                "currently-selected fact in a verified/policy_approved state"
            )
            continue
        resolved_facts.append(cited)
    if reasons:
        # (b) requires EVERY cited fact ID to resolve -- one bad citation fails the claim,
        # it does not just shrink the grounding pool.
        return False, 0.0, reasons

    if field_name == "product.audience":
        shape_failure = _audience_shape_failure(claim, resolved_facts)
        if shape_failure is not None:
            return False, 0.0, [shape_failure]

    resolved_values = [_value_text(fact.value) for fact in resolved_facts]
    tokens = _significant_tokens(claim.text, field_name)
    if not tokens:
        return False, 0.0, [f"{claim.claim_id}: claim text has no significant tokens to ground"]

    matched = [token for token in tokens if any(token in value for value in resolved_values)]
    coverage = len(matched) / len(tokens)
    if coverage < 1.0:
        unmatched = sorted(set(tokens) - set(matched))
        reasons.append(
            f"{claim.claim_id}: lexical coverage {coverage:.2f} -- unmatched tokens {unmatched}"
        )
        return False, coverage, reasons
    return True, coverage, reasons


def groundedness_fact_candidate(
    field_name: str,
    claims: list[InterpretiveClaimV1],
    facts_so_far: ProductFactsV2,
    source_revision: str | None,
    observed_at: str | None,
    *,
    allow_partial: bool = False,
) -> FactRecordV2:
    """Create one verified or narrowly blocked interpretive fact candidate.

    Default use remains all-or-nothing. Agentic drafting may explicitly
    retain only individually proved sibling problem claims. Every selected
    claim still requires complete citation resolution and 100% lexical
    coverage; audience selection remains all-or-nothing.
    """

    source = FactSourceV2(
        source_type="agent_drafted",
        location=f"agent-draft://{field_name}",
        source_revision=source_revision,
        retrieved_at=observed_at,
    )

    failures: list[str] = []
    coverages: list[float] = []
    accepted_claims: list[InterpretiveClaimV1] = []
    if not claims:
        failures.append(f"{field_name}: no claims were drafted for this field")

    for claim in claims:
        passed, coverage, reasons = _claim_result(field_name, claim, facts_so_far)
        if passed:
            coverages.append(coverage)
            accepted_claims.append(claim)
        else:
            failures.extend(reasons)

    selected_claims = claims
    selected_failures = failures
    if allow_partial and accepted_claims:
        selected_claims = accepted_claims
        selected_failures = []

    if selected_failures:
        return FactRecordV2(
            fact_id=descriptive_fact_id(field_name, "groundedness-blocked"),
            field=field_name,
            value={
                "claims": [claim.text for claim in claims],
                "groundedness_failures": selected_failures,
            },
            source=source,
            verification_state="blocked",
            authoritative_owner="repository-owner",
            confidence=0.0,
            affected_surfaces=SURFACE_DEPENDENCIES[field_name],
        )

    confidence = sum(coverages) / len(coverages)
    supporting_fact_ids = list(
        dict.fromkeys(fact_id for claim in selected_claims for fact_id in claim.supporting_fact_ids)
    )
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, "agent-drafted-grounded"),
        field=field_name,
        value=[claim.text for claim in selected_claims],
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=confidence,
        supporting_fact_ids=supporting_fact_ids,
        affected_surfaces=SURFACE_DEPENDENCIES[field_name],
    )
