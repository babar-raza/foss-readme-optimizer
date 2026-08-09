"""Draft fact-bound content for the governed repository-presentation template."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.presentation.template_schema import (
    FactFieldTemplateContentV1,
    ProductFactsTemplateDraftV1,
    RepositoryPresentationTemplateV1,
    load_repository_presentation_template,
)
from readme_agent.presentation.verified_template_api_reference import api_reference_markdown
from readme_agent.presentation.verified_template_capabilities import (
    CapabilityPresentationPlanV1,
    capability_highlights_markdown,
)
from readme_agent.presentation.verified_template_documentation import (
    documentation_resources_markdown,
)
from readme_agent.presentation.verified_template_sections import (
    additional_examples_markdown,
    contributing_markdown,
    dependency_markdown,
    development_markdown,
    package_status_markdown,
    repository_documents_markdown,
    scenario_dependency_markdown,
    security_markdown,
    third_party_notices_markdown,
)
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_links import (
    render_contextual_example_markdown,
    render_contextual_relationship_markdown,
)
from readme_agent.readme.document_structure import heading_identity, parse_headings
from readme_agent.readme.document_templates import example_text, installation_text
from readme_agent.readme.header_badges import render_brand_banner
from readme_agent.readme.header_visual import render_readme_header_visual
from readme_agent.readme.license_location import repository_license_path
from readme_agent.readme.public_limitations import public_limitation_phrases
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding


def _included(
    markdown: str,
    *fields: str,
    standards: tuple[str, ...] = (),
) -> FactFieldTemplateContentV1:
    return FactFieldTemplateContentV1(
        disposition="include",
        markdown=markdown,
        fact_fields=list(fields),
        standard_ids=list(standards),
    )


def _omitted(reason: str) -> FactFieldTemplateContentV1:
    return FactFieldTemplateContentV1(disposition="omit", omission_reason=reason)


def _phrases(facts: ProductFactsV2, field: str) -> list[str]:
    view = visitor_fact_render_view(facts, field)
    return list(view.phrases) if view is not None else []


def _fields_for_fact_ids(facts: ProductFactsV2, fact_ids: list[str]) -> list[str]:
    return sorted({facts.fact_by_id(fact_id).field for fact_id in fact_ids})


def _accepted_fields(facts: ProductFactsV2, *fields: str) -> tuple[str, ...]:
    accepted: list[str] = []
    for field in fields:
        try:
            fact = facts.selected_fact(field)
        except KeyError:
            continue
        if (
            fact.verification_state in {"verified", "policy_approved"}
            and not fact.has_unresolved_conflict
        ):
            accepted.append(field)
    return tuple(accepted)


def _source_owned_optional_slots(
    source_text: str,
    facts: ProductFactsV2,
    contract: RepositoryPresentationTemplateV1,
) -> set[str]:
    """Return optional H2 roles whose complete material content is fact-authorized."""

    headings = [heading for heading in parse_headings(source_text) if heading.level == 2]
    claims = assess_material_claims(source_text)
    owned: set[str] = set()
    for slot in contract.section_order:
        if slot in contract.required_slots:
            continue
        matches = [
            heading
            for heading in headings
            if heading_identity(heading.title) == heading_identity(contract.headings[slot])
        ]
        if len(matches) != 1:
            continue
        heading = matches[0]
        start = len(source_text[: heading.start].encode("utf-8"))
        end = len(source_text[: heading.section_end].encode("utf-8"))
        section_claims = [
            claim
            for claim in claims
            if start <= claim.source_byte_start and claim.source_byte_end <= end
        ]
        if section_claims and all(
            complete_source_claim_fact_binding(source_text, claim, facts) is not None
            for claim in section_claims
        ):
            owned.add(slot)
    return owned


def _source_opening_summary(
    source_text: str,
    facts: ProductFactsV2,
    title: str,
) -> tuple[str, list[str]] | None:
    """Reuse one fully fact-bound, product-named public opening without duplicating it."""

    first_h2 = next(
        (heading for heading in parse_headings(source_text) if heading.level == 2), None
    )
    opening_end = (
        len(source_text[: first_h2.start].encode("utf-8"))
        if first_h2 is not None
        else len(source_text.encode("utf-8"))
    )
    source_bytes = source_text.encode("utf-8")
    for claim in assess_material_claims(source_text):
        if claim.source_byte_end > opening_end:
            continue
        text = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8").strip()
        if not text.casefold().startswith(title.casefold()) or "open-source" not in text.casefold():
            continue
        binding = complete_source_claim_fact_binding(source_text, claim, facts)
        if binding is None:
            continue
        fields = sorted({facts.fact_by_id(fact_id).field for fact_id in binding.fact_ids})
        if {"product.identity", "product.audience", "product.capabilities"}.issubset(fields):
            return text, fields
    return None


_SCOPE_TOPIC_RULES = (
    (re.compile(r"(?i)\bcolou?r\b"), "color-space"),
    (re.compile(r"(?i)\bfunctions?\b"), "function"),
    (re.compile(r"(?i)\bfonts?\b"), "embedded-font"),
)
_SPELLED_COUNTS = (
    "Zero",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
    "Twenty",
)
_CONVERSION_WORKFLOW = re.compile(r"(?i)\bto\b.+\bconversion\b|\bconvert\b")


def _scope_limitations_brief(facts: ProductFactsV2, limitations: list[str]) -> str:
    topics: list[str] = []
    for phrase in limitations:
        for pattern, topic in _SCOPE_TOPIC_RULES:
            if pattern.search(phrase) and topic not in topics:
                topics.append(topic)
    capability_phrases = _phrases(facts, "product.capabilities")
    workflows = (
        "conversion workflows"
        if any(_CONVERSION_WORKFLOW.search(item) for item in capability_phrases)
        else "workflows"
    )
    opening = f"The library targets the {workflows} listed above"
    if topics:
        joined = (
            ", ".join(topics[:-1]) + f", and {topics[-1]}"
            if len(topics) > 2
            else " and ".join(topics)
        )
        opening += f"; {joined} support has documented boundaries"
    count = len(limitations)
    spelled = _SPELLED_COUNTS[count] if count < len(_SPELLED_COUNTS) else str(count)
    noun = "constraint is" if count == 1 else "constraints are"
    return f"{opening}. {spelled} specific {noun} listed below."


def _scope_text(
    facts: ProductFactsV2,
    contextual_links: ContextualLinkPlanV1 | None,
) -> tuple[str, list[str], tuple[str, ...]]:
    limitations = public_limitation_phrases(facts)
    paragraphs = (
        [
            _scope_limitations_brief(facts, limitations),
            "\n".join(
                [
                    "<details>",
                    "<summary>View specific limitations</summary>",
                    "",
                    *(f"- {item}" for item in limitations),
                    "",
                    "</details>",
                ]
            ),
        ]
        if limitations
        else []
    )
    fields = ["product.limitations"] if limitations else []
    package_status = package_status_markdown(facts)
    if package_status:
        paragraphs.append(package_status)
        fields.append("python.distribution")
    repository_documents = repository_documents_markdown(facts)
    if repository_documents:
        paragraphs.append(repository_documents)
        fields.append("repository.documentation_assets")
    standards = ["readme.enterprise_edition_terminology"]
    if contextual_links is not None:
        relationship_markdown, relationship_fact_ids = render_contextual_relationship_markdown(
            contextual_links
        )
        if relationship_markdown:
            paragraphs.append(relationship_markdown)
            fields.extend(_fields_for_fact_ids(facts, relationship_fact_ids))
            standards.append("readme.contextual_links")
    if not paragraphs:
        scope_items = [
            *_phrases(facts, "product.capabilities")[:3],
            *_phrases(facts, "product.formats")[:3],
            *_phrases(facts, "product.compatibility")[:1],
        ]
        paragraphs.append(
            "Verified scope: " + "; ".join(item.rstrip(". ") for item in scope_items) + "."
        )
        fields.extend(["product.capabilities", "product.formats"])
        fields.extend(_accepted_fields(facts, "product.compatibility"))
    return "\n\n".join(paragraphs), fields, tuple(standards)


def _license_text(facts: ProductFactsV2) -> str:
    license_fact = facts.selected_fact("product.license")
    name = str(license_fact.value).strip()
    path = repository_license_path(license_fact)
    normalized = name.casefold().replace("license", "").strip(" -")
    if normalized == "mit":
        return (
            f"This project is available under the [MIT License]({path}). It permits use, "
            "modification, distribution, and commercial use when the license and copyright "
            "notice are retained."
        )
    return (
        f"This project is available under the [{name}]({path}). The license describes the "
        "permissions and conditions for use, modification, and distribution."
    )


def build_verified_template_draft(
    facts: ProductFactsV2,
    source_text: str,
    source_revision: str,
    agentic_plan: ReadmeAgenticCompositionPlanV1,
    contextual_links: ContextualLinkPlanV1 | None = None,
    documentation_link_limit: int | None = None,
    capability_plan: CapabilityPresentationPlanV1 | None = None,
) -> ProductFactsTemplateDraftV1:
    """Bind verified facts and the validated agentic plan to reusable slots."""

    visual = render_readme_header_visual(facts, agentic_plan)
    title = visual.title
    capabilities = _phrases(facts, "product.capabilities")
    problems = _phrases(facts, "product.problems_solved")
    source_summary = _source_opening_summary(source_text, facts, title)
    if source_summary is not None:
        summary, summary_fields = source_summary
    elif agentic_plan.opening_summary is not None:
        summary = agentic_plan.opening_summary.text.strip().rstrip(".") + "."
        summary_fact_ids = set(agentic_plan.opening_summary.supporting_fact_ids)
        summary_fields = sorted({facts.fact_by_id(fact_id).field for fact_id in summary_fact_ids})
    else:
        overview = []
        summary_fact_ids = set()
        for sentence in agentic_plan.overview_sentences:
            sentence_fields = {
                facts.fact_by_id(fact_id).field for fact_id in sentence.supporting_fact_ids
            }
            text = sentence.text.strip().rstrip(".")
            if sentence_fields & {"product.audience", "product.problems_solved"} and text:
                overview.append(text + ".")
                summary_fact_ids.update(sentence.supporting_fact_ids)
        if overview:
            summary = " ".join(overview)
            summary_fields = sorted(
                {facts.fact_by_id(fact_id).field for fact_id in summary_fact_ids}
            )
        else:
            summary = f"{title} provides " + ", ".join(capabilities[:3] or problems[:3]) + "."
            summary_fields = ["product.identity", "product.capabilities"]
    capability_text = capability_highlights_markdown(
        facts,
        source_text=source_text,
        presentation_plan=capability_plan,
    )
    at_a_glance = visual.mermaid_markdown
    installation = installation_text(facts, facts.org_repo, source_revision)
    scenario_dependencies = scenario_dependency_markdown(facts, source_text=source_text)
    if installation is not None and scenario_dependencies:
        installation += "\n\n" + scenario_dependencies
    dependencies = dependency_markdown(facts)
    if installation is not None and dependencies:
        installation += "\n\n" + dependencies
    example = example_text(facts, source_revision)
    example_standards = ["readme.primary_example"]
    example_fields = ["example.minimal"]
    if contextual_links is not None:
        contextual_example, contextual_fact_ids = render_contextual_example_markdown(
            contextual_links
        )
        if contextual_example:
            example += "\n\n" + contextual_example
            example_fields.extend(_fields_for_fact_ids(facts, contextual_fact_ids))
            example_standards.append("readme.contextual_links")
    if not capability_text or not installation or not example:
        raise ValueError(
            "verified template lacks required capability, acquisition, or example facts"
        )
    scope, scope_fields, scope_standards = _scope_text(facts, contextual_links)
    badge_block = visual.badge_markdown
    banner = render_brand_banner(facts, product_name=title)
    if banner is not None:
        badge_block += "\n\n" + banner
    badge_fields = sorted(
        {facts.fact_by_id(fact_id).field for badge in visual.badges for fact_id in badge.fact_ids}
    )
    visual_fields = sorted(
        {
            facts.fact_by_id(fact_id).field
            for node in visual.diagram_nodes
            for fact_id in node.fact_ids
        }
    )
    contract = load_repository_presentation_template()
    source_owned_optional_slots = _source_owned_optional_slots(source_text, facts, contract)
    optional: dict = {
        slot: _omitted(
            "Current source owns this canonical optional H2; exact source preservation "
            "reconciles it against verified facts."
            if slot in source_owned_optional_slots
            else "No separately verified repository content is bound to this slot."
        )
        for slot in contract.section_order
        if slot
        not in {
            "navigation",
            "at_a_glance",
            "key_capabilities",
            "installation",
            "quick_start",
            "scope_and_limitations",
            "license",
        }
    }
    development = development_markdown(facts)
    contributing = contributing_markdown(facts)
    security = security_markdown(facts)
    optional_sections = {
        "additional_examples": (
            (
                examples_markdown := additional_examples_markdown(
                    facts, reserved_heading_titles=(title,), source_text=source_text
                )
            ),
            (
                ("repository.examples", *_accepted_fields(facts, "api.public_surface"))
                if examples_markdown and "### Host the MCP Server" in examples_markdown
                else ("repository.examples",)
            ),
            ("readme.additional_examples",),
        ),
        "api_reference": (
            api_reference_markdown(facts),
            ("api.public_surface",),
            ("readme.api_reference",),
        ),
        "documentation_resources": (
            documentation_resources_markdown(facts, link_limit=documentation_link_limit),
            ("documentation.links", "product.identity"),
            ("readme.documentation_resources",),
        ),
        "development_and_testing": (
            development,
            _accepted_fields(
                facts,
                "development.assets",
                "development.commands",
                "development.golden_workflow",
            ),
            ("readme.development_and_testing",),
        ),
        "contributing": (
            contributing,
            _accepted_fields(facts, "repository.contribution_guidance"),
            ("readme.contributing",),
        ),
        "security": (
            security,
            _accepted_fields(facts, "repository.security_guidance"),
            ("readme.security",),
        ),
        "third_party_notices": (
            third_party_notices_markdown(facts),
            ("repository.third_party_notices",),
            ("readme.third_party_notices",),
        ),
    }
    for slot, (markdown, fields, standards) in optional_sections.items():
        if markdown and slot not in source_owned_optional_slots:
            optional[slot] = _included(markdown, *fields, standards=standards)
    return ProductFactsTemplateDraftV1(
        source_revision=source_revision,
        source_line_count=len(source_text.splitlines()),
        title=_included(title, "product.identity", standards=("readme.header",)),
        badges=_included(badge_block, *badge_fields, standards=("readme.badges",)),
        summary=_included(
            summary,
            *summary_fields,
            standards=("readme.agentic_opening_summary",),
        ),
        sections={
            "at_a_glance": _included(
                at_a_glance,
                *visual_fields,
                standards=("readme.at_a_glance_mermaid",),
            ),
            "key_capabilities": _included(
                capability_text,
                "product.capabilities",
                *_accepted_fields(
                    facts,
                    "product.identity",
                    "product.platforms",
                    "product.formats",
                    "api.public_surface",
                ),
            ),
            "installation": _included(
                installation,
                "installation.verified_acquisition",
                "installation.coordinates",
                *_accepted_fields(facts, "product.compatibility"),
                *(
                    _accepted_fields(
                        facts,
                        "installation.optional_extras",
                        "installation.capability_dependencies",
                    )
                    if scenario_dependencies
                    else []
                ),
                *_accepted_fields(
                    facts,
                    *(("python.distribution",) if dependencies else ()),
                ),
                standards=("readme.verified_acquisition",),
            ),
            "quick_start": _included(
                example,
                *example_fields,
                standards=tuple(example_standards),
            ),
            "scope_and_limitations": _included(scope, *scope_fields, standards=scope_standards),
            "license": _included(
                _license_text(facts), "product.license", standards=("readme.license",)
            ),
            **optional,
        },
    )
