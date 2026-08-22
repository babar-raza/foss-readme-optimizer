"""Select bounded fact clusters for canonical README prose authoring."""

from __future__ import annotations

import re
from collections.abc import Iterable

from readme_agent.facts.format_vocabulary import canonical_document_format
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.llm.section_authoring_prompts import SectionAuthoringTaskFamily
from readme_agent.specialists.section_authoring_document import SectionAuthoringSpecV1

_SECTION_FIELDS: tuple[tuple[str, SectionAuthoringTaskFamily, str, tuple[str, ...]], ...] = (
    (
        "summary",
        "opening_summary",
        "Introduce the complete product identity, intended audience, and concrete purpose.",
        (
            "product.identity",
            "product.audience",
            "product.problems_solved",
            "product.capabilities",
        ),
    ),
    (
        "key_capabilities",
        "capability_entry_cluster",
        "Describe concrete visitor-facing capabilities without installation or verification prose.",
        (
            "product.capabilities",
            "aspose.feature_claims",
        ),
    ),
    (
        "installation",
        "installation_framing",
        "Briefly frame the supported acquisition path; exact commands are supplied separately.",
        (
            "installation.verified_acquisition",
            "product.compatibility",
            "aspose.install_claims",
        ),
    ),
    (
        "quick_start",
        "verified_example_framing",
        "Explain what the introductory example demonstrates; exact code is supplied separately.",
        ("example.minimal",),
    ),
    (
        "scope_and_limitations",
        "scope_and_limitations",
        "State practical scope and limitations without internal assurance narration.",
        ("product.limitations",),
    ),
)


def _accepted_selected_fact(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    if fact.has_unresolved_conflict:
        return None
    return fact


def _public_terms(values: Iterable[object], *, limit: int = 12) -> tuple[str, ...]:
    terms: list[str] = []
    for value in values:
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            text = str(candidate).strip()
            if text and len(text) <= 80 and text not in terms:
                terms.append(text)
            if len(terms) == limit:
                return tuple(terms)
    return tuple(terms)


def _contains_format_token(value: str) -> bool:
    return any(
        canonical_document_format(token.lstrip(".")) is not None
        for token in re.findall(r"(?<![A-Za-z0-9])\.?[A-Za-z0-9][A-Za-z0-9.+_-]{1,}", value)
    )


def build_canonical_section_authoring_specs(
    facts: ProductFactsV2,
) -> tuple[SectionAuthoringSpecV1, ...]:
    """Return the same platform-neutral prose jobs for every verified repository."""

    seo_facts = [
        _accepted_selected_fact(facts, field)
        for field in ("product.identity", "product.capabilities", "product.formats")
    ]
    format_fact = _accepted_selected_fact(facts, "product.formats")
    seo_vocabulary = tuple(
        term
        for term in _public_terms(fact.value for fact in seo_facts if fact is not None)
        if format_fact is None or not _contains_format_token(term)
    )
    specs: list[SectionAuthoringSpecV1] = []
    for section_id, task_family, objective, fields in _SECTION_FIELDS:
        accepted = [
            fact for field in fields if (fact := _accepted_selected_fact(facts, field)) is not None
        ]
        if not accepted:
            continue
        specs.append(
            SectionAuthoringSpecV1(
                section_id=section_id,
                task_family=task_family,
                section_objective=objective,
                accepted_fact_ids=tuple(fact.fact_id for fact in accepted),
                do_not_claim_fact_ids=(
                    (format_fact.fact_id,)
                    if section_id in {"summary", "key_capabilities", "scope_and_limitations"}
                    and format_fact is not None
                    else ()
                ),
                max_facts_per_cluster=4,
                seo_vocabulary=(
                    seo_vocabulary
                    if task_family
                    in {"opening_summary", "capability_entry_cluster", "scope_and_limitations"}
                    else ()
                ),
            )
        )
    return tuple(specs)


__all__ = ["build_canonical_section_authoring_specs"]
