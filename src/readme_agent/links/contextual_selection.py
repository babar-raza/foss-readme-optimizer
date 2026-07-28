"""Select only verified article links with strong adjacent-content evidence."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.links.allocation import ResolvedLinkBudgetV1, resolve_link_budget
from readme_agent.links.catalog import normalize_target_url, query_linkable_targets
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1, AsposeLinkRecordV2
from readme_agent.links.contextual_models import (
    ContextualLinkBindingV1,
    ContextualLinkOmissionReason,
    ContextualLinkPlanV1,
)
from readme_agent.links.occurrences import (
    AsposeLinkOccurrenceCountsV1,
    count_aspose_link_occurrences,
    find_aspose_link_occurrences,
)
from readme_agent.links.terminology import enterprise_product_name_from_facts
from readme_agent.readme.document_structure import parse_headings
from readme_agent.registry.models import LinkAllocationPolicyV1

_CODE_TERM = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_STOP_TERMS = {
    "auto",
    "class",
    "const",
    "false",
    "from",
    "import",
    "int",
    "let",
    "main",
    "new",
    "none",
    "null",
    "package",
    "print",
    "println",
    "public",
    "return",
    "static",
    "str",
    "string",
    "true",
    "use",
    "using",
    "var",
    "void",
}


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact = facts.selected_fact(field)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _identity_scope(facts: ProductFactsV2) -> tuple[str, str, FactRecordV2]:
    identity = _accepted(facts, "product.identity")
    value = identity.value if identity is not None and isinstance(identity.value, dict) else {}
    family = str(value.get("family") or "").casefold()
    platform = str(value.get("platform") or value.get("ecosystem") or "").casefold()
    if not family or not platform or identity is None:
        raise ValueError("contextual link selection requires accepted family/platform identity")
    return family, platform, identity


def _example_terms(code: str) -> tuple[set[str], set[str]]:
    all_terms: set[str] = set()
    strong_terms: set[str] = set()
    for raw in _CODE_TERM.findall(code):
        folded = raw.casefold().rstrip(".")
        parts = [part for part in folded.split(".") if len(part) >= 3]
        all_terms.update(parts)
        all_terms.add(folded)
        if "." in raw or raw[:1].isupper() or "_" in raw:
            strong_terms.add(folded)
            strong_terms.update(parts)
    all_terms.difference_update(_STOP_TERMS)
    strong_terms.difference_update(_STOP_TERMS)
    return all_terms, strong_terms


def _matched_terms(
    record: AsposeLinkRecordV2,
    *,
    all_terms: set[str],
    strong_terms: set[str],
) -> tuple[list[str], list[str]]:
    subjects = {term.casefold().rstrip(".") for term in record.subject_terms}
    matched = sorted(subjects & all_terms)
    strong = sorted(subjects & strong_terms)
    return matched, strong


def _example_section(markdown: str, code: str) -> str | None:
    position = markdown.find(code.rstrip())
    if position < 0:
        return None
    headings = [
        heading
        for heading in parse_headings(markdown)
        if heading.level == 2 and heading.heading_end <= position < heading.section_end
    ]
    return headings[-1].title if headings else None


def _within_budget(
    record: AsposeLinkRecordV2,
    *,
    plan_budget: ResolvedLinkBudgetV1,
    counts: AsposeLinkOccurrenceCountsV1,
) -> bool:
    return bool(
        counts.total < plan_budget.max_total
        and counts.by_parent_domain[record.parent_domain]
        < plan_budget.domain_maxima[record.parent_domain]
        and counts.by_surface[record.surface] < plan_budget.surface_maxima[record.surface]
    )


def _decision(
    *,
    family: str,
    platform: str,
    enterprise_product_name: str,
    catalogs: AsposeLinkCatalogSetV1,
    budget: ResolvedLinkBudgetV1,
    counts: AsposeLinkOccurrenceCountsV1,
    considered_record_ids: list[str],
    bindings: list[ContextualLinkBindingV1],
    omission_reason: ContextualLinkOmissionReason,
) -> ContextualLinkPlanV1:
    return ContextualLinkPlanV1(
        family=family,
        platform=platform,
        enterprise_product_name=enterprise_product_name,
        aspose_org_catalog_hash=catalogs.aspose_org.provenance.output_hash,
        aspose_com_catalog_hash=catalogs.aspose_com.provenance.output_hash,
        budget=budget,
        pre_link_occurrences=counts,
        considered_record_ids=considered_record_ids,
        bindings=bindings,
        omission_reason=omission_reason,
    )


def select_contextual_links(
    facts: ProductFactsV2,
    pre_link_markdown: str,
    catalogs: AsposeLinkCatalogSetV1,
    policy: LinkAllocationPolicyV1,
    *,
    verified_code_sha256s: set[str] | None = None,
) -> ContextualLinkPlanV1:
    """Return at most one strongly matched article for the accepted minimal example."""

    family, platform, identity = _identity_scope(facts)
    enterprise_product_name = enterprise_product_name_from_facts(facts)
    budget = resolve_link_budget(
        policy,
        pre_link_markdown,
        verified_code_sha256s=verified_code_sha256s,
    )
    counts = count_aspose_link_occurrences(pre_link_markdown)
    example = _accepted(facts, "example.minimal")
    value = example.value if example is not None and isinstance(example.value, dict) else {}
    code = str(value.get("code") or "").strip()
    if example is None or not code:
        return _decision(
            family=family,
            platform=platform,
            enterprise_product_name=enterprise_product_name,
            catalogs=catalogs,
            budget=budget,
            counts=counts,
            considered_record_ids=[],
            bindings=[],
            omission_reason="no_accepted_example",
        )
    section = _example_section(pre_link_markdown, code)
    if section is None:
        return _decision(
            family=family,
            platform=platform,
            enterprise_product_name=enterprise_product_name,
            catalogs=catalogs,
            budget=budget,
            counts=counts,
            considered_record_ids=[],
            bindings=[],
            omission_reason="no_example_section",
        )
    candidates = query_linkable_targets(
        catalogs,
        family=family,
        platform=platform,
        surfaces={"docs", "kb", "reference"},
    )
    exact_platform = [record for record in candidates if platform in record.platforms]
    all_terms, strong_terms = _example_terms(code)
    ranked: list[tuple[tuple, AsposeLinkRecordV2, list[str]]] = []
    for record in exact_platform:
        matched, strong = _matched_terms(
            record,
            all_terms=all_terms,
            strong_terms=strong_terms,
        )
        dotted = [term for term in matched if "." in term]
        if not strong and len(matched) < 2:
            continue
        surface_rank = {"docs": 0, "kb": 1, "reference": 2}
        ranked.append(
            (
                (
                    -len(dotted),
                    -len(strong),
                    -len(matched),
                    surface_rank[record.surface],
                    len(record.url),
                    record.record_id,
                ),
                record,
                matched,
            )
        )
    considered = [record.record_id for _, record, _ in sorted(ranked)]
    if not ranked:
        return _decision(
            family=family,
            platform=platform,
            enterprise_product_name=enterprise_product_name,
            catalogs=catalogs,
            budget=budget,
            counts=counts,
            considered_record_ids=[],
            bindings=[],
            omission_reason="no_strong_context_match",
        )
    existing = {
        occurrence.normalized_url for occurrence in find_aspose_link_occurrences(pre_link_markdown)
    }
    for _, record, matched in sorted(ranked):
        if normalize_target_url(record.url) in existing:
            continue
        if not _within_budget(record, plan_budget=budget, counts=counts):
            continue
        return _decision(
            family=family,
            platform=platform,
            enterprise_product_name=enterprise_product_name,
            catalogs=catalogs,
            budget=budget,
            counts=counts,
            considered_record_ids=considered,
            bindings=[
                ContextualLinkBindingV1(
                    binding_id=f"readme.example:{record.record_id}",
                    context_kind="code_example",
                    section_heading=section,
                    context_id=example.fact_id,
                    target_record_id=record.record_id,
                    target_url=record.url,
                    target_title=record.title,
                    parent_domain=record.parent_domain,
                    surface=record.surface,
                    support_rationale=(
                        f"Verified {record.surface} article matches accepted example terms: "
                        + ", ".join(matched)
                    ),
                    placement="after_verified_example",
                    accepted_fact_ids=[identity.fact_id, example.fact_id],
                    matched_subject_terms=matched,
                )
            ],
            omission_reason="none",
        )
    omission: ContextualLinkOmissionReason = (
        "target_already_present"
        if all(normalize_target_url(record.url) in existing for _, record, _ in ranked)
        else "budget_exhausted"
    )
    return _decision(
        family=family,
        platform=platform,
        enterprise_product_name=enterprise_product_name,
        catalogs=catalogs,
        budget=budget,
        counts=counts,
        considered_record_ids=considered,
        bindings=[],
        omission_reason=omission,
    )
