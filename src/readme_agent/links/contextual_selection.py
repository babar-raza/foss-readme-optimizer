"""Select only verified article links with strong adjacent-content evidence."""

from __future__ import annotations

from collections import Counter

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.links.allocation import ResolvedLinkBudgetV1, resolve_link_budget
from readme_agent.links.catalog import normalize_target_url, query_linkable_targets
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1, AsposeLinkRecordV2
from readme_agent.links.contextual_matching import rank_contextual_articles
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
    pre_link_url_counts: dict[str, int],
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
        pre_link_url_counts=pre_link_url_counts,
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
    pre_link_url_counts = dict(
        sorted(
            Counter(
                occurrence.normalized_url
                for occurrence in find_aspose_link_occurrences(pre_link_markdown)
            ).items()
        )
    )
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
            pre_link_url_counts=pre_link_url_counts,
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
            pre_link_url_counts=pre_link_url_counts,
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
    ranked = rank_contextual_articles(
        exact_platform,
        code=code,
        example_value=value,
    )
    considered = [match.record.record_id for match in ranked]
    if not ranked:
        return _decision(
            family=family,
            platform=platform,
            enterprise_product_name=enterprise_product_name,
            catalogs=catalogs,
            budget=budget,
            counts=counts,
            pre_link_url_counts=pre_link_url_counts,
            considered_record_ids=[],
            bindings=[],
            omission_reason="no_strong_context_match",
        )
    existing = {
        occurrence.normalized_url for occurrence in find_aspose_link_occurrences(pre_link_markdown)
    }
    for match in ranked:
        record = match.record
        matched = match.matched_terms
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
            pre_link_url_counts=pre_link_url_counts,
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
        if all(normalize_target_url(match.record.url) in existing for match in ranked)
        else "budget_exhausted"
    )
    return _decision(
        family=family,
        platform=platform,
        enterprise_product_name=enterprise_product_name,
        catalogs=catalogs,
        budget=budget,
        counts=counts,
        pre_link_url_counts=pre_link_url_counts,
        considered_record_ids=considered,
        bindings=[],
        omission_reason=omission,
    )
