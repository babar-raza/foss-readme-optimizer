"""Render verified capabilities as concise, scannable feature highlights."""

from __future__ import annotations

import re
from dataclasses import dataclass

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
from readme_agent.readme.claim_accountability_api_coordinates import (
    api_class_fact_coordinates,
    api_mcp_server_fact_coordinates,
)
from readme_agent.readme.claim_accountability_coordinates import (
    structured_list_item_coordinate,
)
from readme_agent.readme.claim_accountability_implementation_coordinates import (
    implementation_component_coordinates,
)
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.presentation_similarity import (
    capability_discriminators,
    semantically_repeats,
)
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
    visitor_capability_phrase,
)
from readme_agent.readme.source_claim_fact_binding import (
    CompleteSourceClaimFactBindingV1,
    complete_source_claim_fact_binding,
)

SourceCapabilityBinding = tuple[str, CompleteSourceClaimFactBindingV1]
CapabilityCoordinateKey = tuple[str, str, str]
IndexedSourceBinding = tuple[set[str], set[StructuredFactCoordinateV1]]


@dataclass(frozen=True)
class CapabilityPresentationPlanV1:
    """Transaction-local capability rows with complete fact provenance."""

    rows: tuple[
        tuple[str, tuple[str, ...], tuple[StructuredFactCoordinateV1, ...]],
        ...,
    ]


_CAPABILITY_EXPLANATIONS = (
    (
        re.compile(r"(?i)\bword 97-2003\b.*\bdoc\b.*\bolefile\b"),
        "Parse legacy Word binary files through the repository's olefile-backed reader",
    ),
    (
        re.compile(r"(?i)\b(?:read|write)\b.*\bpython standard-library components\b"),
        "Process this format through the repository's pure-Python reader and writer",
    ),
    (
        re.compile(r"(?i)\bwrite\b.*\bpdf\b"),
        "Render document content as a portable PDF file",
    ),
    (
        re.compile(r"(?i)\b(?:document\s+)?loading\b.*\bfile path\b"),
        "Load supported documents directly from filesystem paths",
    ),
    (
        re.compile(r"(?i)\bsaveformat\b.*\boutput formats?\b"),
        "Select the requested output format when saving a document",
    ),
    (
        re.compile(r"(?i)\bloadoptions\b.*\binput format\b"),
        "Choose or detect the source format before loading a document",
    ),
    (
        re.compile(r"(?i)\bworkbooks?\b.*\bworksheets?\b.*\b(?:save|modify)\b"),
        "Handle workbook and worksheet content through a complete create-to-save workflow",
    ),
    (
        re.compile(r"(?i)\badd\b.*\bremove\b.*\brename\b.*\bworksheets?\b"),
        "Organize workbook sheets by adding, removing, and renaming worksheet entries",
    ),
    (
        re.compile(r"(?i)\bcreate\b.*\bmodify\b.*\bcharts?\b"),
        "Build chart objects from worksheet data and update their presentation",
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
        re.compile(r"(?i)\bencrypt\b.*\bdecrypt\b"),
        "Protect PDF content with RC4 or AES encryption",
    ),
    (
        re.compile(r"(?i)\boptimi[sz]e\b.*\bstreams?\b.*\bimages?\b.*\bfonts?\b"),
        "Compress streams and consolidate unused image, font, and object resources",
    ),
    (
        re.compile(r"(?i)\bheuristic\b.*\bpdf/a\b.*\bpdf/ua\b.*\bvalidat"),
        "Run heuristic checks for archival and accessibility conformance profiles",
    ),
    (
        re.compile(r"(?i)\bpdf/a\b.*\bpdf/ua\b.*\b(?:validat|checks?|conversions?)"),
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
    (re.compile(r"(?i)\bexport\b"), "Create files in the listed output formats"),
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
    catalog = fact.value.get("coordinate_catalog")
    catalog_classes = catalog.get("classes") if isinstance(catalog, dict) else None
    names = [
        str(item.get("name")).strip()
        for source_list in (classes, catalog_classes)
        if isinstance(source_list, list)
        for item in source_list
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    mcp_server = fact.value.get("mcp_server")
    if isinstance(mcp_server, dict):
        names.extend(
            str(mcp_server.get(key)).strip()
            for key in ("factory", "runner")
            if str(mcp_server.get(key) or "").strip()
        )
        tools = mcp_server.get("tools")
        if isinstance(tools, list):
            names.extend(str(tool).strip() for tool in tools if str(tool).strip())
    return list(dict.fromkeys(names))


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


def _format_subject(value: str) -> str:
    """Return the factual format token without a generic content suffix."""

    without_direction = re.sub(
        r"(?i)^(?:(?:reads?|writes?|inputs?|outputs?)\s+|"
        r"(?:input|output)\s+format\s*:\s*)",
        "",
        value,
    ).strip()
    return re.sub(
        r"(?i)\s+(?:files|documents|content)$",
        "",
        without_direction,
    ).strip()


def _same_capability_presentation(left: str, right: str) -> bool:
    """Compare capability prose without collapsing distinct format directions."""

    left_discriminators = capability_discriminators(left)
    right_discriminators = capability_discriminators(right)
    if left_discriminators and right_discriminators and left_discriminators != right_discriminators:
        return False
    return semantically_repeats(left, right)


def _related_types(capability: str, type_names: list[str]) -> list[str]:
    capability_words = _words(capability)
    capability_discriminator_set = capability_discriminators(capability)
    if "IMAGE" in capability_discriminator_set:
        capability_words.add("image")
    by_name = {name.casefold(): name for name in type_names}
    if "mcp" in capability_words:
        preferred = [by_name[name] for name in ("create_server", "run") if name in by_name]
        if preferred:
            return preferred
    if "eps" in capability_words and "metadata" in capability_words:
        eps_metadata = by_name.get("eps_metadata")
        if eps_metadata is not None:
            return [eps_metadata]
    if "xmp" in capability_words:
        preferred = [
            by_name[name] for name in ("xmppacket", "parse_xmp", "serialize_xmp") if name in by_name
        ]
        if {"low-level", "low", "object"}.intersection(capability_words):
            cos_extractor = by_name.get("cosextractor")
            if cos_extractor is not None:
                preferred.append(cos_extractor)
        if preferred:
            return preferred
    conversion = re.search(r"(?i)^convert\s+(?P<inputs>.+?)\s+(?:files\s+)?to\s+", capability)
    input_tokens = _words(conversion.group("inputs")) if conversion is not None else set()
    ranked: list[tuple[int, int, str]] = []
    for name in type_names:
        if name.endswith(("Error", "Exception")):
            continue
        reverse_target = re.search(r"_to_([a-z0-9]+)$", name)
        if reverse_target is not None and reverse_target.group(1).removesuffix("s") in input_tokens:
            # A helper converting INTO the capability's input format runs the
            # opposite direction and must not be attributed to this row.
            continue
        name_discriminators = capability_discriminators(name.replace("_", " "))
        if (
            capability_discriminator_set
            and name_discriminators
            and not name_discriminators.issubset(capability_discriminator_set)
        ):
            continue
        type_words = _words(name)
        overlap = capability_words & type_words
        if overlap and type_words <= capability_words:
            ranked.append((-len(overlap), len(name), name))
    return [name for _overlap, _length, name in sorted(ranked)[:3]]


def _public_api_reference(related_types: list[str]) -> str:
    rendered_items = [f"`{name}`" for name in related_types]
    if len(rendered_items) == 1:
        rendered = rendered_items[0]
    elif len(rendered_items) == 2:
        rendered = " and ".join(rendered_items)
    else:
        rendered = ", ".join(rendered_items[:-1]) + f", and {rendered_items[-1]}"
    noun = "API" if len(related_types) == 1 else "APIs"
    return f"the public {rendered} {noun}"


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
            description += f" Available through {_public_api_reference(related_types)}."
        return description
    directional = re.fullmatch(
        r"(?i)convert\s+(.+?)\s+to\s+(.+?)(?:\s+in\s+[A-Za-z0-9.+#-]+)?$",
        exact_capability,
    )
    if directional is not None:
        output = directional.group(2)
        output_discriminators = capability_discriminators(output)
        description = (
            "Render the supported source content as raster image data."
            if "IMAGE" in output_discriminators or output.casefold() == "images"
            else f"Serialize the supported source content as {output} output."
        )
        if related_types:
            description += f" Available through {_public_api_reference(related_types)}."
        return description
    if re.search(r"(?i)\bmcp\b.*\bserver", exact_capability):
        api_reference = _public_api_reference(related_types) if related_types else "public APIs"
        return f"Create and run the MCP server through {api_reference}."
    if re.search(r"(?i)\beps\b.*\bmetadata", exact_capability):
        api_reference = _public_api_reference(related_types) if related_types else "the public API"
        return f"Read EPS metadata through {api_reference}."
    subject = re.sub(r"(?i)^work with\s+", "", public_capability)
    if related_types:
        api_reference = _public_api_reference(related_types)
        action = capability_action_verb(exact_capability)
        if action in {"read", "load", "parse", "import", "open", "extract"}:
            return f"Build in-memory document structures through {api_reference}."
        if action in {
            "edit",
            "inspect",
            "modify",
            "navigate",
            "search",
            "traverse",
            "update",
        }:
            return f"Work directly with the public object model through {api_reference}."
        if action in {"save", "export", "write", "convert", "render"}:
            return f"Produce supported output through {api_reference}."
        return f"Use {api_reference} in application workflows."
    action = capability_action_verb(exact_capability)
    if action is not None:
        if action in {"create", "generate", "build"}:
            return "Build the corresponding content through the public object model."
        if action in {"read", "load", "import", "open", "extract"}:
            return "Bring supported content into application workflows."
        if action in {"save", "export", "write", "convert", "render"}:
            return "Produce supported output through the public API."
        if action in {"edit", "modify", "update", "replace", "remove", "add"}:
            return "Change supported content through the public object model."
        if action in {"inspect", "navigate", "traverse", "search"}:
            return "Navigate the relevant structures through the public object model."
        return f"Apply {subject} through the product's public object model."
    return f"Supports {public_capability}."


def _richer_source_capability_exists(
    source_bindings: list[SourceCapabilityBinding],
    generated_markdown: str,
    generated_fact_ids: list[str],
    facts: ProductFactsV2,
) -> bool:
    """Prefer one fact-richer inherited capability over a narrower generated repeat."""

    capability_fact_id = facts.selected_fact_ids.get("product.capabilities")
    if capability_fact_id is None:
        return False
    generated_ids = set(generated_fact_ids)
    generated_discriminator_set = capability_discriminators(generated_markdown)
    for source_claim, binding in source_bindings:
        source_discriminator_set = capability_discriminators(source_claim)
        if (
            generated_discriminator_set
            and source_discriminator_set
            and generated_discriminator_set != source_discriminator_set
        ):
            continue
        if not semantically_repeats(source_claim, generated_markdown, threshold=0.6):
            continue
        if capability_fact_id in binding.fact_ids and bool(set(binding.fact_ids) - generated_ids):
            return True
    return False


def _richer_fact_bound_source_capability(
    source_bindings: list[SourceCapabilityBinding],
    capability: str,
    facts: ProductFactsV2,
) -> tuple[str, list[str], list[StructuredFactCoordinateV1]] | None:
    """Return one concise inherited capability that adds accepted repository detail."""

    capability_fact_id = facts.selected_fact_ids.get("product.capabilities")
    if capability_fact_id is None:
        return None
    capability_discriminator_set = capability_discriminators(capability)
    candidates: list[tuple[int, int, str, list[str], list[StructuredFactCoordinateV1]]] = []
    for source_claim, binding in source_bindings:
        if "\n" in source_claim.strip():
            continue
        public_claim = re.sub(r"^\s*[-*+]\s+", "", source_claim.strip())
        public_claim = visitor_capability_phrase(public_claim)
        source_discriminator_set = capability_discriminators(public_claim)
        if (
            not public_claim
            or len(public_claim) > 160
            or capability_action_verb(public_claim) is None
            or (
                capability_discriminator_set
                and source_discriminator_set
                and capability_discriminator_set != source_discriminator_set
            )
            or not semantically_repeats(capability, public_claim, threshold=0.6)
        ):
            continue
        if capability_fact_id not in binding.fact_ids:
            continue
        added_words = _words(public_claim) - _words(capability)
        added_facts = set(binding.fact_ids) - {capability_fact_id}
        if not added_words and not added_facts:
            continue
        fact_ids = sorted(binding.fact_ids)
        candidates.append(
            (
                len(fact_ids),
                len(_words(public_claim)),
                public_claim,
                fact_ids,
                list(binding.fact_coordinates),
            )
        )
    if not candidates:
        return None
    _fact_count, _word_count, public_claim, fact_ids, coordinates = max(
        candidates,
        key=lambda item: (item[0], item[1], item[2].casefold()),
    )
    return public_claim, fact_ids, coordinates


def _list_coordinates_for_capability_row(
    facts: ProductFactsV2,
    fact_id: str,
    source_phrase: str,
    rendered_title: str,
) -> list[StructuredFactCoordinateV1]:
    fact = facts.fact_by_id(fact_id)
    if not isinstance(fact.value, list):
        return []
    coordinates: list[StructuredFactCoordinateV1] = []
    for item in fact.value:
        if not isinstance(item, str):
            continue
        matches = False
        if fact.field == "product.capabilities":
            matches = source_phrase.casefold() in {
                phrase.casefold() for phrase in normalize_capability_phrases([item])
            }
        elif fact.field == "product.formats":
            subject = _format_subject(item)
            matches = bool(
                subject
                and re.search(
                    rf"(?i)(?<![A-Za-z0-9]){re.escape(subject)}(?![A-Za-z0-9])",
                    rendered_title,
                )
            )
        elif fact.field == "product.problems_solved":
            matches = semantically_repeats(source_phrase, item, threshold=0.6)
        if matches:
            coordinates.append(structured_list_item_coordinate(fact_id, fact.field, item))
    return coordinates


def _source_capability_bindings(
    source_text: str,
    facts: ProductFactsV2,
) -> list[SourceCapabilityBinding]:
    """Parse and fact-bind each source claim once for capability rendering."""

    source_bytes = source_text.encode("utf-8")
    bindings: list[SourceCapabilityBinding] = []
    for claim in assess_material_claims(source_text):
        binding = complete_source_claim_fact_binding(source_text, claim, facts)
        if binding is None:
            continue
        source_claim = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        bindings.append((source_claim, binding))
    return bindings


def _source_capability_coordinate_index(
    source_bindings: list[SourceCapabilityBinding],
) -> dict[frozenset[CapabilityCoordinateKey], list[IndexedSourceBinding]]:
    """Index exact source evidence once by structured capability item."""

    index: dict[frozenset[CapabilityCoordinateKey], list[IndexedSourceBinding]] = {}
    for _source_claim, binding in source_bindings:
        capability_keys = frozenset(
            (coordinate.fact_id, coordinate.path, coordinate.value_sha256)
            for coordinate in binding.fact_coordinates
            if coordinate.field in {"product.capabilities", "repository.implementation_components"}
        )
        if not capability_keys:
            continue
        index.setdefault(capability_keys, []).append(
            (set(binding.fact_ids), set(binding.fact_coordinates))
        )
    return index


def _source_coordinates_for_capability_row(
    source_index: dict[frozenset[CapabilityCoordinateKey], list[IndexedSourceBinding]],
    row_coordinates: list[StructuredFactCoordinateV1],
) -> tuple[list[str], list[StructuredFactCoordinateV1]]:
    """Return indexed source evidence for the row's exact capability items."""

    row_keys = {
        (coordinate.fact_id, coordinate.path, coordinate.value_sha256)
        for coordinate in row_coordinates
        if coordinate.field in {"product.capabilities", "repository.implementation_components"}
    }
    fact_ids: set[str] = set()
    coordinates: set[StructuredFactCoordinateV1] = set()
    for capability_keys, source_bindings in source_index.items():
        if not capability_keys.issubset(row_keys):
            continue
        if len(source_bindings) == 1:
            fact_ids.update(source_bindings[0][0])
            coordinates.update(source_bindings[0][1])
            continue
        common_coordinates = set.intersection(*(binding[1] for binding in source_bindings))
        coordinates.update(common_coordinates)
        fact_ids.update(coordinate.fact_id for coordinate in common_coordinates)
    return sorted(fact_ids), sorted(
        coordinates,
        key=lambda item: (item.fact_id, item.path, item.value_sha256),
    )


def _capability_rows(
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
) -> list[tuple[str, list[str], list[StructuredFactCoordinateV1]]]:
    """Return exact public rows and the accepted facts that authorize each row."""

    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is None:
        return []
    identity_view = visitor_fact_render_view(facts, "product.identity")
    formats_view = visitor_fact_render_view(facts, "product.formats")
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
    try:
        implementation_fact = facts.selected_fact("repository.implementation_components")
    except KeyError:
        implementation_fact = None
    if implementation_fact is not None and (
        implementation_fact.verification_state not in {"verified", "policy_approved"}
        or implementation_fact.has_unresolved_conflict
    ):
        implementation_fact = None
    rows: list[tuple[str, list[str], list[StructuredFactCoordinateV1]]] = []
    source_bindings = (
        _source_capability_bindings(source_text, facts) if source_text is not None else []
    )
    source_coordinate_index = (
        _source_capability_coordinate_index(source_bindings) if source_text is not None else {}
    )
    retained_titles: list[str] = []
    retained_seo_titles: set[str] = set()
    retained_rows: list[str] = []
    for phrase in normalize_capability_phrases(view.phrases):
        inherited_fact_ids: list[str] = []
        inherited_coordinates: list[StructuredFactCoordinateV1] = []
        source_phrase = phrase
        if source_bindings:
            inherited = _richer_fact_bound_source_capability(source_bindings, phrase, facts)
            if inherited is not None:
                phrase, inherited_fact_ids, inherited_coordinates = inherited
        title = visitor_capability_phrase(phrase)
        if not title:
            continue
        if any(_same_capability_presentation(title, retained) for retained in retained_titles):
            continue
        seo_title = seo_capability_title(title, seo_context)
        normalized_seo_title = seo_title.casefold()
        if normalized_seo_title in retained_seo_titles:
            continue
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
        if formats_view is not None and any(
            re.search(
                rf"(?i)(?<![A-Za-z0-9]){re.escape(_format_subject(format_phrase))}"
                r"(?![A-Za-z0-9])",
                seo_title,
            )
            for format_phrase in formats_view.phrases
            if _format_subject(format_phrase)
        ):
            fact_ids.extend(formats_view.citation_fact_ids)
        if related_types and api_fact_id is not None:
            fact_ids.append(api_fact_id)
        markdown = f"- **{seo_title}** - {_description(seo_title, phrase, related_types)}"
        if any(_same_capability_presentation(markdown, retained) for retained in retained_rows):
            continue
        fact_ids = sorted(set(fact_ids))
        coordinates = list(inherited_coordinates)
        for fact_id in fact_ids:
            field = facts.fact_by_id(fact_id).field
            if field in {
                "product.capabilities",
                "product.formats",
                "product.problems_solved",
            }:
                coordinates.extend(
                    _list_coordinates_for_capability_row(
                        facts,
                        fact_id,
                        source_phrase,
                        seo_title,
                    )
                )
        if implementation_fact is not None:
            implementation_coordinates = implementation_component_coordinates(
                markdown,
                implementation_fact.fact_id,
                implementation_fact.value,
                known_non_dependency_names=set(related_types),
            )
            if implementation_coordinates:
                coordinates.extend(implementation_coordinates)
                fact_ids.append(implementation_fact.fact_id)
        if source_coordinate_index:
            source_fact_ids, source_coordinates = _source_coordinates_for_capability_row(
                source_coordinate_index,
                coordinates,
            )
            fact_ids.extend(source_fact_ids)
            coordinates.extend(source_coordinates)
        if related_types and api_fact is not None:
            coordinates.extend(
                api_class_fact_coordinates(api_fact.fact_id, api_fact.value, related_types)
            )
        if api_fact is not None and "`create_server`" in markdown and "`run`" in markdown:
            coordinates.extend(
                api_mcp_server_fact_coordinates(
                    api_fact.fact_id,
                    api_fact.value,
                    include_factory=True,
                    include_runner=True,
                )
            )
        coordinates = sorted(
            set(coordinates),
            key=lambda item: (item.fact_id, item.path, item.value_sha256),
        )
        fact_ids = sorted({*fact_ids, *(coordinate.fact_id for coordinate in coordinates)})
        # Verify-then-merge (Tweak 4): richer inherited capabilities are merged
        # into the generated row above, never preferred over it as a competing
        # preserved block.
        rows.append((markdown, fact_ids, coordinates))
        retained_titles.append(title)
        retained_seo_titles.add(normalized_seo_title)
        retained_rows.append(markdown)
    return rows


def build_capability_presentation_plan(
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
) -> CapabilityPresentationPlanV1:
    """Build one reusable capability rendering and provenance plan."""

    return CapabilityPresentationPlanV1(
        rows=tuple(
            (markdown, tuple(fact_ids), tuple(coordinates))
            for markdown, fact_ids, coordinates in _capability_rows(
                facts,
                source_text=source_text,
            )
        )
    )


def capability_highlights_markdown(
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
    presentation_plan: CapabilityPresentationPlanV1 | None = None,
) -> str | None:
    """Return bold feature names followed by one fact-bounded explanation."""

    rows = (
        presentation_plan.rows
        if presentation_plan is not None
        else build_capability_presentation_plan(facts, source_text=source_text).rows
    )
    bullets = [markdown for markdown, _fact_ids, _coordinates in rows]
    if not bullets:
        return None
    return "\n".join(bullets)


def _identity_claim_fact_ids(claim_text: str, facts: ProductFactsV2) -> list[str]:
    view = visitor_fact_render_view(facts, "product.identity")
    try:
        identity = facts.selected_fact("product.identity")
    except KeyError:
        return []
    if view is None or not isinstance(identity.value, dict):
        return []
    identity_terms = [
        str(identity.value.get(field) or "").strip() for field in ("product_name", "platform")
    ]
    if any(
        term and re.search(rf"(?i)(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", claim_text)
        for term in identity_terms
    ):
        return list(view.citation_fact_ids)
    return []


def capability_claim_fact_ids(
    claim_text: str,
    facts: ProductFactsV2,
    *,
    presentation_plan: CapabilityPresentationPlanV1 | None = None,
) -> list[str]:
    """Bind one exact canonical capability row to its accepted source facts."""

    normalized = claim_text.strip()
    canonical_terms = canonical_abbreviations_from_facts(facts)
    rows = (
        presentation_plan.rows
        if presentation_plan is not None
        else build_capability_presentation_plan(facts).rows
    )
    for markdown, fact_ids, _coordinates in rows:
        if normalized in {
            markdown.strip(),
            canonicalize_public_markdown(markdown, canonical_terms).strip(),
        }:
            return sorted({*fact_ids, *_identity_claim_fact_ids(normalized, facts)})
    view = visitor_fact_render_view(facts, "product.capabilities")
    if view is not None and any(
        semantically_repeats(normalized, phrase, threshold=0.6)
        for phrase in normalize_capability_phrases(view.phrases)
    ):
        return sorted(
            {
                *view.citation_fact_ids,
                *_identity_claim_fact_ids(normalized, facts),
            }
        )
    return []


def capability_claim_fact_coordinates(
    claim_text: str,
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
    presentation_plan: CapabilityPresentationPlanV1 | None = None,
) -> list[StructuredFactCoordinateV1]:
    """Bind one exact canonical capability row to exact structured coordinates."""

    normalized = claim_text.strip()
    canonical_terms = canonical_abbreviations_from_facts(facts)
    rows = (
        presentation_plan.rows
        if presentation_plan is not None
        else build_capability_presentation_plan(facts, source_text=source_text).rows
    )
    for markdown, _fact_ids, coordinates in rows:
        if normalized in {
            markdown.strip(),
            canonicalize_public_markdown(markdown, canonical_terms).strip(),
        }:
            return list(coordinates)
    return []


__all__ = [
    "CapabilityPresentationPlanV1",
    "build_capability_presentation_plan",
    "capability_claim_fact_coordinates",
    "capability_claim_fact_ids",
    "capability_highlights_markdown",
]
