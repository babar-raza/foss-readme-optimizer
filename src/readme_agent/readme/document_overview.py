"""Render a concise, non-duplicative fact-backed README overview."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import Heading, github_anchor
from readme_agent.readme.document_templates import (
    accepted_fact,
    load_template,
    mapping_value,
    visitor_text,
)
from readme_agent.readme.presentation_similarity import summaries_overlap

_OMIT_LINE = "__README_AGENT_OMIT_LINE__"


def _without_redundant_problem(selected: dict[str, str]) -> dict[str, str]:
    problem = selected.get("product.problems_solved")
    capabilities = selected.get("product.capabilities")
    if problem and capabilities and summaries_overlap(problem, capabilities):
        return {**selected, "product.problems_solved": _OMIT_LINE}
    return selected


def _render(selected: dict[str, str], navigation: str, mermaid_markdown: str | None) -> str:
    values = _without_redundant_problem(selected)
    rendered = (
        load_template("product-overview-and-navigation.md")
        .format(
            audience=values.get("product.audience", _OMIT_LINE),
            problem=values.get("product.problems_solved", _OMIT_LINE),
            capabilities=values.get("product.capabilities", _OMIT_LINE),
            formats=values.get("product.formats", _OMIT_LINE),
            minimum_runtime=values.get("product.compatibility", _OMIT_LINE),
            limitations=values.get("product.limitations", _OMIT_LINE),
            mermaid=mermaid_markdown or _OMIT_LINE,
            navigation=navigation or "- Continue with the repository guidance below.",
        )
        .strip()
    )
    return "\n".join(line for line in rendered.splitlines() if _OMIT_LINE not in line).strip()


def overview_text(
    facts: ProductFactsV2,
    headings: list[Heading],
    agentic_overview_sentences: list[dict] | None = None,
    mermaid_markdown: str | None = None,
    omitted_fields: frozenset[str] = frozenset(),
) -> str:
    """Render navigation and accepted fact views without repeated inventories."""

    navigation = "\n".join(
        f"- [{heading.title}](#{github_anchor(heading.title)})"
        for heading in headings
        if heading.level == 2
        and heading.title.strip().lower() not in {"at a glance", "in this readme"}
    )
    selected: dict[str, str] = {}
    if agentic_overview_sentences:
        for sentence in agentic_overview_sentences:
            text = str(sentence["text"]).strip()
            for fact_id in sentence.get("supporting_fact_ids", []):
                try:
                    field = facts.fact_by_id(str(fact_id)).field
                except KeyError:
                    continue
                if field not in omitted_fields:
                    selected.setdefault(field, text)
    else:
        compatibility = accepted_fact(facts, "product.compatibility")
        compatibility_value = mapping_value(compatibility.value) if compatibility else {}
        for field in (
            "product.audience",
            "product.problems_solved",
            "product.capabilities",
            "product.formats",
        ):
            visitor_phrase = visitor_text(facts, field)
            if visitor_phrase and field not in omitted_fields:
                selected[field] = visitor_phrase
        minimum_runtime = compatibility_value.get("minimum_runtime")
        if minimum_runtime and "product.compatibility" not in omitted_fields:
            selected["product.compatibility"] = str(minimum_runtime)
        limitations = visitor_text(facts, "product.limitations")
        if limitations and "product.limitations" not in omitted_fields:
            selected["product.limitations"] = limitations
    return _render(selected, navigation, mermaid_markdown)
