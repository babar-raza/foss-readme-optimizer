"""Validate compiled repository-presentation documents against the structural contract."""

from __future__ import annotations

import re
import unicodedata

from markdown_it import MarkdownIt

from readme_agent.links.terminology import find_enterprise_terminology_findings
from readme_agent.presentation.template_schema import (
    PresentationTemplateInputV1,
    RepositoryPresentationTemplateV1,
    load_repository_presentation_template,
)
from readme_agent.readme.capability_semantics import is_action_led_capability_title
from readme_agent.readme.document_structure import github_anchor, parse_headings
from readme_agent.readme.header_visual_layout import validate_capability_group_layout

_BADGE = re.compile(r"(?:!\[[^\]]+\]\([^)]+\)|\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\))")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_CODE_COMMENT = re.compile(r"(?m)^\s*(?:#(?!\s*\[)|//|/\*|\*|--)\s+\S")
_COPYRIGHT = re.compile(r"(?im)^\s*copyright(?:\s*©|\s+\(c\)|\s+\d{4})|©")
_MERMAID_NODE = re.compile(r'(?m)^\s{2}[A-Za-z][A-Za-z0-9_]*\(\["[^"]+"\]\)\s*$')
_ASPOSE_FOSS_PRODUCT = re.compile(r"\bAspose\.([A-Za-z0-9]+)\s+FOSS\b")
_INTERNAL_ASSURANCE_COMMENTARY = re.compile(
    r"(?i)(?:inventoried at the source revision|syntax and static public API checked|"
    r"not executed or syntax checked|checked but not executed|not executed by the evidence "
    r"collector|verification metadata|exact source revision|immutable repository revision|"
    r"network[- ]disabled verification|matching (?:pypi|registry) receipt|"
    r"verification environment)"
)


def _contains_emoji(text: str) -> bool:
    for character in text:
        codepoint = ord(character)
        if (
            0x1F000 <= codepoint <= 0x1FAFF
            or 0x2600 <= codepoint <= 0x27BF
            or unicodedata.category(character) == "So"
            and codepoint > 0x2300
        ):
            return True
    return False


def validate_repository_presentation(
    candidate: str,
    template_input: PresentationTemplateInputV1,
    *,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> list[str]:
    """Return deterministic contract violations; an empty list is acceptance."""

    contract = template or load_repository_presentation_template()
    errors: list[str] = []
    headings = parse_headings(candidate)
    h1s = [heading.title for heading in headings if heading.level == 1]
    h2s = [heading for heading in headings if heading.level == 2]
    title = " ".join(template_input.title.markdown.split())
    if h1s != [title]:
        errors.append("candidate must contain exactly one full-product-name H1")

    opening = candidate[: h2s[0].start] if h2s else candidate
    badge_lines = [
        line
        for line in opening.splitlines()
        if _BADGE.search(line) and "products.aspose.org/media/" not in line
    ]
    if len(badge_lines) != contract.invariants.badge_rows:
        errors.append("candidate must contain exactly one opening badge row")
    banner_lines = [line for line in opening.splitlines() if "products.aspose.org/media/" in line]
    if len(banner_lines) > 1 or any(
        re.fullmatch(
            rf"!\[{re.escape(title)}\]\(https://products\.aspose\.org/media/[a-z0-9./_-]+\)",
            line,
        )
        is None
        for line in banner_lines
    ):
        errors.append("candidate brand banner must be one exact portfolio media image")
    elif len(_BADGE.findall(badge_lines[0])) < contract.invariants.minimum_badges:
        errors.append("candidate badge row has no applicable badge")
    elif badge_lines[0] != template_input.badges.markdown.strip().splitlines()[0]:
        errors.append("candidate badge row differs from the bound applicable badge set")

    navigation = next(
        (heading for heading in h2s if heading.title.casefold() == "navigation"),
        None,
    )
    if navigation is None:
        errors.append("candidate is missing list navigation")
    else:
        body = candidate[navigation.heading_end : navigation.section_end]
        expected = {
            github_anchor(heading.title)
            for heading in h2s
            if heading.title.casefold() != "navigation"
        }
        linked = set(re.findall(r"(?m)^- \[[^\]]+\]\(#([^)]+)\)$", body))
        if linked != expected:
            errors.append("navigation must be a complete H2 link list")

    api_reference = next(
        (heading for heading in h2s if heading.title.casefold() == "api reference"),
        None,
    )
    if api_reference is not None:
        api_body = candidate[api_reference.heading_end : api_reference.section_end]
        namespace_tables = re.findall(
            r"(?ms)^### [^\r\n]+ Namespace \(`[^`]+`\)\s+\| Type \| Description \|\s+"
            r"\| --- \| --- \|",
            api_body,
        )
        namespace_headings = re.findall(r"(?m)^### [^\r\n]+ Namespace \(`[^`]+`\)\s*$", api_body)
        api_rows = re.findall(r"(?m)^\| `([^`]+)` \| ([^|]+) \|$", api_body)
        descriptions = [" ".join(description.split()).casefold() for _name, description in api_rows]
        if (
            "<details>" not in api_body
            or "<summary>View public API by namespace</summary>" not in api_body
            or "</details>" not in api_body
            or not namespace_headings
            or len(namespace_tables) != len(namespace_headings)
            or re.search(r"(?m)^- `", api_body) is not None
        ):
            errors.append(
                "API reference must contain one collapsed Type/Description table per namespace"
            )
        if any(
            len(description.rstrip(".")) < 24
            or description
            in {
                "public exception type.",
                "public enumeration exported by this namespace.",
                "public export provided by this namespace.",
            }
            for description in descriptions
        ):
            errors.append("API reference contains an incomplete generic description")
        if len(descriptions) != len(set(descriptions)):
            errors.append("API reference contains duplicated descriptions")

    capabilities = next(
        (heading for heading in h2s if heading.title.casefold() == "key capabilities"),
        None,
    )
    if capabilities is not None:
        body = candidate[capabilities.heading_end : capabilities.section_end].strip()
        lines = [
            line
            for line in body.splitlines()
            if line.strip()
            and line.strip() not in {"<details>", "</details>"}
            and not line.strip().startswith("<summary>")
        ]
        if not lines or any(
            re.fullmatch(r"- \*\*[^*\n]+\*\* - \S.+\.", line) is None for line in lines
        ):
            errors.append(
                "Key capabilities must use bold feature names with same-line explanations"
            )
        titles = re.findall(r"(?m)^- \*\*([^*]+)\*\* - ", body)
        if titles and any(not is_action_led_capability_title(title) for title in titles):
            errors.append("Key capability titles must be action-led search phrases")

    additional_examples = next(
        (heading for heading in h2s if heading.title.casefold() == "additional examples"),
        None,
    )
    if additional_examples is not None:
        body = candidate[additional_examples.heading_end : additional_examples.section_end].strip()
        introduction = body.partition("<details>")[0].strip()
        if (
            not introduction.startswith("Expand this section to ")
            or "<summary>View additional examples and results</summary>" not in body
            or re.search(r"(?m)^### .+ \(\d+\)$", body) is not None
        ):
            errors.append(
                "Additional examples must preview named workflows and use meaningful headings"
            )

    tokens = MarkdownIt("commonmark").parse(candidate)
    mermaid = [
        token.content for token in tokens if token.type == "fence" and token.info == "mermaid"
    ]
    if len(mermaid) != 1:
        errors.append("candidate must contain exactly one Mermaid diagram")
    else:
        source = mermaid[0]
        if title not in source:
            errors.append("Mermaid must use the complete product name")
        if not source.startswith("flowchart LR\n"):
            errors.append("Mermaid must use the configured capability landscape")
        for node_prefix, group_id, label, minimum in (
            ("I", "Inputs", "Inputs", contract.invariants.minimum_mermaid_inputs),
            (
                "C",
                "Capabilities",
                "Capabilities",
                contract.invariants.minimum_mermaid_capabilities,
            ),
            ("O", "Outputs", "Outputs", contract.invariants.minimum_mermaid_outputs),
        ):
            if minimum > 0 and source.count(f"subgraph {group_id}") != 1:
                errors.append(f"Mermaid requires one {label.casefold()} subgraph")
            count = (
                len(re.findall(r'C\d+\["', source))
                if node_prefix == "C"
                else len(re.findall(rf'(?m)^\s{{4}}{node_prefix}\d+\["', source))
            )
            if count < minimum:
                errors.append(f"Mermaid requires at least {minimum} {label.casefold()} nodes")
        if not re.search(r"(?m)^\s{2}I\d+ --- PRODUCT$", source):
            errors.append("Mermaid inputs must connect to the product")
        capability_ids = re.findall(r'(C\d+)\["', source)
        if not validate_capability_group_layout(source, capability_ids):
            errors.append("Mermaid capability nodes must use the adaptive column layout")
        if len(re.findall(r"(?m)^\s{2}PRODUCT --- Capabilities$", source)) != 1:
            errors.append("Mermaid product must have one connection to Core capabilities")
        output_count = len(re.findall(r'(?m)^\s{4}O\d+\["', source))
        capability_output_edges = len(re.findall(r"(?m)^\s{2}Capabilities --- Outputs$", source))
        if output_count and capability_output_edges != 1:
            errors.append("Mermaid Core capabilities must have one connection to Outputs")
        if not output_count and capability_output_edges:
            errors.append("Mermaid cannot connect to an empty Outputs group")
        if "-->" in source:
            errors.append("Mermaid overview must use only visible undirected relationships")

    if _HTML_COMMENT.search(candidate) or any(
        _CODE_COMMENT.search(token.content)
        for token in tokens
        if token.type in {"fence", "code_block"} and token.info != "mermaid"
    ):
        errors.append("candidate contains a visible or code comment")
    if _INTERNAL_ASSURANCE_COMMENTARY.search(candidate):
        errors.append("candidate exposes internal verification commentary")
    if _contains_emoji(candidate):
        errors.append("candidate contains emoji")
    if _COPYRIGHT.search(candidate):
        errors.append("candidate contains a default copyright declaration")
    own_families = {match.group(1).casefold() for match in _ASPOSE_FOSS_PRODUCT.finditer(title)}
    candidate_families = {
        match.group(1).casefold() for match in _ASPOSE_FOSS_PRODUCT.finditer(candidate)
    }
    if own_families and candidate_families - own_families:
        errors.append("candidate contains cross-product Aspose FOSS identity leakage")
    if find_enterprise_terminology_findings(candidate):
        errors.append("candidate contains noncanonical Aspose Enterprise Edition terminology")

    license_heading = next(
        (heading for heading in h2s if heading.title.casefold() == "license"),
        None,
    )
    license_body = (
        candidate[license_heading.heading_end : license_heading.section_end]
        if license_heading
        else ""
    )
    if not license_heading or not re.search(
        r"\[[^\]]*license[^\]]*\]\([^)]+\)",
        license_body,
        re.I,
    ):
        errors.append("License must be prose with a license link")
    if "permit" not in license_body.casefold():
        errors.append("License prose must summarize practical permission benefits")

    notices = next(
        (heading for heading in h2s if heading.title.casefold() == "third-party notices"),
        None,
    )
    if notices is not None:
        body = candidate[notices.heading_end : notices.section_end]
        if not re.search(r"\[[^\]]+\]\((?!https?://)[^)]+\)", body):
            errors.append("Third-party notices must link a repository-relative notice file")
        if re.search(r"\[`[^`]+`\]\((?!https?://)[^)]+\)", body):
            errors.append("Third-party notices link text must use normal link styling")
    return errors
