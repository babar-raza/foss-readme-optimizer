"""Render verified capabilities as concise, scannable feature highlights."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_capability_seo import (
    capability_seo_context,
    seo_capability_title,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.capability_semantics import (
    capability_action_verb,
    normalize_capability_phrases,
)
from readme_agent.readme.presentation_similarity import semantically_repeats
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
    visitor_capability_phrase,
)
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding

_CAPABILITY_EXPLANATIONS = (
    (
        re.compile(r"(?i)\bworkbooks?\b.*\bworksheets?\b.*\b(?:save|modify)\b"),
        "Handle workbook and worksheet content through a complete create-to-save workflow",
    ),
    (
        re.compile(r"(?i)\bcells?\b.*\bvalues?\b.*\bstyles?\b"),
        "Read and update cell content while applying spreadsheet styles",
    ),
    (
        re.compile(r"(?i)\bfile format import and export\b"),
        "Exchange content across the listed supported file formats",
    ),
    (
        re.compile(r"(?i)\bprimitives?\b"),
        "Build reusable scene geometry from the listed primitive types",
    ),
    (
        re.compile(r"(?i)\banimations?\b.*\bkeyframes?\b"),
        "Animate scene properties with time-based keyframe data",
    ),
    (
        re.compile(r"(?i)\bcreate\b.*\bload\b.*\bsave\b.*\b(?:merge|inspect)\b"),
        "Load, save, merge, and inspect files throughout the document lifecycle",
    ),
    (
        re.compile(r"(?i)\bedit\b.*\btext\b.*\bimages?\b|\btext replacement\b|\bredaction\b"),
        "Replace or redact text and update visual page content",
    ),
    (
        re.compile(r"(?i)\bextract\b.*\b(?:text|images?)\b.*\battachments?\b"),
        "Retrieve text, embedded images, and file attachments",
    ),
    (
        re.compile(r"(?i)\bconcatenate\b.*\bpages?\b|\bappend\b.*\bpages?\b"),
        "Reorder pages or move selected pages between documents",
    ),
    (
        re.compile(r"(?i)\brender\b.*\b(?:png|tiff)\b"),
        "Produce PNG and TIFF image output from individual pages",
    ),
    (
        re.compile(r"(?i)\binteractive\b.*\bform fields?\b"),
        "Work with interactive data-entry controls and their values",
    ),
    (
        re.compile(r"(?i)\badd\b.*\bupdate\b.*\bremove\b.*\bannotations?\b"),
        "Manage annotations as document content changes",
    ),
    (
        re.compile(r"(?i)\bencrypt\b.*\bdecrypt\b.*\b(?:optimi[sz]e|compress)\b"),
        "Protect document content through encryption while controlling file size",
    ),
    (
        re.compile(r"(?i)\bpdf/a\b.*\bpdf/ua\b.*\bvalidat"),
        "Check archival and accessibility conformance profiles",
    ),
    (
        re.compile(r"(?i)\bresource\b.*\blimits?\b"),
        "Control resource-use limits during document processing",
    ),
    (
        re.compile(r"(?i)\bxmp\b.*\bmetadata\b.*\blow[- ]level\b.*\bobjects?\b"),
        "Parse and serialize metadata packets while inspecting low-level PDF objects",
    ),
    (
        re.compile(r"(?i)\bxmp\b.*\bmetadata\b"),
        "Parse and serialize document metadata packets",
    ),
    (
        re.compile(r"(?i)\bdigital signatures?\b"),
        "Support document-signing workflows",
    ),
    (re.compile(r"(?i)\btravers"), "Navigate document content and its child nodes"),
    (
        re.compile(r"(?i)\bpage\b.*\btitle\b|\btitle\b.*\bpage\b"),
        "Inspect page content together with its title information",
    ),
    (re.compile(r"(?i)\brich\s*text\b|\bformatting\b"), "Access text and its formatting data"),
    (
        re.compile(r"(?i)\bimage\b.*\battach|\battach.*\bimage\b"),
        "Retrieve embedded images and attached-file content",
    ),
    (re.compile(r"(?i)\btable\b|\brows?\b.*\bcells?\b"), "Traverse tables, rows, and cells"),
    (re.compile(r"(?i)\btags?\b"), "Inspect tags on content nodes"),
    (re.compile(r"(?i)\blists?\b|\boutline\b"), "Inspect numbered lists and outline structures"),
    (re.compile(r"(?i)\bexport\b"), "Produce files in the verified output formats"),
)


def _public_type_names(facts: ProductFactsV2) -> list[str]:
    try:
        fact = facts.selected_fact("api.public_surface")
    except KeyError:
        return []
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return []
    classes = fact.value.get("classes")
    if not isinstance(classes, list):
        return []
    return [
        str(item.get("name")).strip()
        for item in classes
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]


def _words(value: str) -> set[str]:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = {
        word.casefold().removesuffix("s")
        for word in re.findall(r"[A-Za-z0-9]+", expanded)
        if len(word) > 2
    }
    related = {
        "formatting": {"style"},
        "numbered": {"number"},
        "traversal": {"node", "visitor"},
    }
    return words | {word for source in words for word in related.get(source, set())}


def _related_types(capability: str, type_names: list[str]) -> list[str]:
    capability_words = _words(capability)
    if "xmp" in capability_words:
        by_name = {name.casefold(): name for name in type_names}
        preferred = [
            by_name[name] for name in ("xmppacket", "parse_xmp", "serialize_xmp") if name in by_name
        ]
        if {"low-level", "low", "object"}.intersection(capability_words):
            cos_extractor = by_name.get("cosextractor")
            if cos_extractor is not None:
                preferred.append(cos_extractor)
        if preferred:
            return preferred
    ranked: list[tuple[int, int, str]] = []
    for name in type_names:
        if name.endswith(("Error", "Exception")):
            continue
        type_words = _words(name)
        overlap = capability_words & type_words
        if overlap and type_words <= capability_words:
            ranked.append((-len(overlap), len(name), name))
    return [name for _overlap, _length, name in sorted(ranked)[:3]]


def _description(capability: str, source_capability: str, related_types: list[str]) -> str:
    exact_capability = capability.strip().rstrip(".")
    public_capability = exact_capability
    first_word = public_capability.split(maxsplit=1)[0]
    if (
        first_word
        and not any(character.isdigit() for character in first_word)
        and not (len(first_word) > 1 and first_word.isupper())
    ):
        public_capability = public_capability[:1].lower() + public_capability[1:]
    explanation = next(
        (
            text
            for pattern, text in _CAPABILITY_EXPLANATIONS
            if pattern.search(source_capability) or pattern.search(exact_capability)
        ),
        "",
    )
    if explanation:
        description = explanation + "."
        if related_types:
            rendered_items = [f"`{name}`" for name in related_types]
            if len(rendered_items) == 1:
                rendered = rendered_items[0]
            elif len(rendered_items) == 2:
                rendered = " and ".join(rendered_items)
            else:
                rendered = ", ".join(rendered_items[:-1]) + f", and {rendered_items[-1]}"
            noun = "API" if len(related_types) == 1 else "APIs"
            description += f" Available through the public {rendered} {noun}."
        return description
    if related_types:
        rendered_items = [f"`{name}`" for name in related_types]
        if len(rendered_items) == 1:
            rendered = rendered_items[0]
        elif len(rendered_items) == 2:
            rendered = " and ".join(rendered_items)
        else:
            rendered = ", ".join(rendered_items[:-1]) + f", and {rendered_items[-1]}"
        noun = "API" if len(related_types) == 1 else "APIs"
        return f"Available through the public {rendered} {noun} for {public_capability}."
    action = capability_action_verb(exact_capability)
    if action is not None:
        if action in {"create", "generate", "build"}:
            return "Build the corresponding content through the public object model."
        if action in {"read", "load", "import", "open", "extract"}:
            return "Bring supported content into application workflows."
        if action in {"save", "export", "write", "convert", "render"}:
            return "Produce verified output through the public API."
        if action in {"edit", "modify", "update", "replace", "remove", "add"}:
            return "Change supported content through the public object model."
        if action in {"inspect", "navigate", "traverse", "search"}:
            return "Navigate the relevant structures through the public object model."
        return "Apply the operation through the product's public API."
    return f"Supports {public_capability}."


def _richer_source_capability_exists(
    source_text: str,
    generated_markdown: str,
    generated_fact_ids: list[str],
    facts: ProductFactsV2,
) -> bool:
    """Prefer one fact-richer inherited capability over a narrower generated repeat."""

    capability_fact_id = facts.selected_fact_ids.get("product.capabilities")
    if capability_fact_id is None:
        return False
    source_bytes = source_text.encode("utf-8")
    generated_ids = set(generated_fact_ids)
    for claim in assess_material_claims(source_text):
        source_claim = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        if not semantically_repeats(source_claim, generated_markdown, threshold=0.6):
            continue
        binding = complete_source_claim_fact_binding(source_text, claim, facts)
        if (
            binding is not None
            and capability_fact_id in binding.fact_ids
            and bool(set(binding.fact_ids) - generated_ids)
        ):
            return True
    return False


def _richer_fact_bound_source_capability(
    source_text: str,
    capability: str,
    facts: ProductFactsV2,
) -> tuple[str, list[str]] | None:
    """Return one concise inherited capability that adds accepted repository detail."""

    capability_fact_id = facts.selected_fact_ids.get("product.capabilities")
    if capability_fact_id is None:
        return None
    source_bytes = source_text.encode("utf-8")
    candidates: list[tuple[int, int, str, list[str]]] = []
    for claim in assess_material_claims(source_text):
        source_claim = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        if "\n" in source_claim.strip():
            continue
        public_claim = re.sub(r"^\s*[-*+]\s+", "", source_claim.strip())
        public_claim = visitor_capability_phrase(public_claim)
        if (
            not public_claim
            or len(public_claim) > 160
            or capability_action_verb(public_claim) is None
            or not semantically_repeats(capability, public_claim, threshold=0.6)
        ):
            continue
        binding = complete_source_claim_fact_binding(source_text, claim, facts)
        if binding is None or capability_fact_id not in binding.fact_ids:
            continue
        added_words = _words(public_claim) - _words(capability)
        added_facts = set(binding.fact_ids) - {capability_fact_id}
        if not added_words and not added_facts:
            continue
        fact_ids = sorted(binding.fact_ids)
        candidates.append((len(fact_ids), len(_words(public_claim)), public_claim, fact_ids))
    if not candidates:
        return None
    _fact_count, _word_count, public_claim, fact_ids = max(
        candidates,
        key=lambda item: (item[0], item[1], item[2].casefold()),
    )
    return public_claim, fact_ids


def _capability_rows(
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
) -> list[tuple[str, list[str]]]:
    """Return exact public rows and the accepted facts that authorize each row."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    identity_view = visitor_fact_render_view(facts, "product.identity")
    type_names = _public_type_names(facts)
    seo_context = capability_seo_context(facts)
    problems_view = visitor_fact_render_view(facts, "product.problems_solved")
    api_fact_id: str | None = None
    try:
        api_fact = facts.selected_fact("api.public_surface")
    except KeyError:
        api_fact = None
    if (
        api_fact is not None
        and api_fact.verification_state in {"verified", "policy_approved"}
        and not api_fact.has_unresolved_conflict
    ):
        api_fact_id = api_fact.fact_id
    rows: list[tuple[str, list[str]]] = []
    retained_titles: list[str] = []
    retained_rows: list[str] = []
    for phrase in normalize_capability_phrases(view.phrases):
        inherited_fact_ids: list[str] = []
        if source_text is not None:
            inherited = _richer_fact_bound_source_capability(source_text, phrase, facts)
            if inherited is not None:
                phrase, inherited_fact_ids = inherited
        title = visitor_capability_phrase(phrase)
        if not title:
            continue
        if any(semantically_repeats(title, retained) for retained in retained_titles):
            continue
        seo_title = seo_capability_title(title, seo_context)
        related_types = _related_types(title, type_names)
        fact_ids = [*view.citation_fact_ids, *inherited_fact_ids]
        if (
            identity_view is not None
            and seo_context.product_name
            and seo_context.product_name.casefold() in seo_title.casefold()
        ):
            fact_ids.extend(identity_view.citation_fact_ids)
        if problems_view is not None and any(
            semantically_repeats(title, problem) for problem in problems_view.phrases
        ):
            fact_ids.extend(problems_view.citation_fact_ids)
        if related_types and api_fact_id is not None:
            fact_ids.append(api_fact_id)
        markdown = f"- **{seo_title}** - {_description(seo_title, phrase, related_types)}"
        if any(semantically_repeats(markdown, retained) for retained in retained_rows):
            continue
        fact_ids = sorted(set(fact_ids))
        if source_text is not None and _richer_source_capability_exists(
            source_text,
            markdown,
            fact_ids,
            facts,
        ):
            continue
        rows.append((markdown, fact_ids))
        retained_titles.append(title)
        retained_rows.append(markdown)
    return rows


def capability_highlights_markdown(
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
) -> str | None:
    """Return bold feature names followed by one fact-bounded explanation."""

    rows = _capability_rows(facts, source_text=source_text)
    return "\n".join(markdown for markdown, _fact_ids in rows) or None


def capability_claim_fact_ids(claim_text: str, facts: ProductFactsV2) -> list[str]:
    """Bind one exact canonical capability row to its accepted source facts."""

    normalized = claim_text.strip()
    canonical_terms = canonical_abbreviations_from_facts(facts)
    for markdown, fact_ids in _capability_rows(facts):
        if normalized in {
            markdown.strip(),
            canonicalize_public_markdown(markdown, canonical_terms).strip(),
        }:
            return fact_ids
    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is not None and any(
        semantically_repeats(normalized, phrase, threshold=0.6)
        for phrase in normalize_capability_phrases(view.phrases)
    ):
        return list(view.citation_fact_ids)
    return []


__all__ = ["capability_claim_fact_ids", "capability_highlights_markdown"]
