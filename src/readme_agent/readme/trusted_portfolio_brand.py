"""Validate the shared visible-brand contract for trusted README candidates."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.links.catalog import normalize_target_url
from readme_agent.readme.presentation_contract import (
    PRESENTATION_CONTRACT_VERSION,
    PRESENTATION_EMOJI_POLICY,
    PRESENTATION_ENTERPRISE_LINK_SECTION,
    PRESENTATION_MERMAID_GRAMMAR,
    PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
    PRESENTATION_MERMAID_MAX_NODES,
)
from readme_agent.readme.public_text import title_case_heading

TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION = PRESENTATION_CONTRACT_VERSION

_URL = re.compile(r"https?://[^\s<>)\"']+")
_MARKDOWN_LINK = re.compile(r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)")
_H1 = re.compile(r"(?m)^# (.+?)\s*$")
_H2 = re.compile(r"(?m)^## (.+?)\s*$")
_EMOJI = re.compile("[\u2600-\u27bf\U0001f000-\U0001faff]")
_HEADING = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")
_MERMAID_FENCE = re.compile(r"(?ms)^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$")
_INLINE_NODE = re.compile(
    r"(?<![A-Za-z0-9_.-])([A-Za-z][A-Za-z0-9_.-]*)[ \t]*"
    r'\[[ \t]*"?([^"\]\r\n]+)"?[ \t]*\]'
)
_NODE = re.compile(r'(?m)^[ \t]*(I\d+|PRODUCT|C\d+|O\d+)\["([^"\r\n]+)"\][ \t]*$')
_EDGE = re.compile(
    r"(?m)^[ \t]*(I\d+|PRODUCT|C\d+|O\d+)[ \t]*-->[ \t]*(I\d+|PRODUCT|C\d+|O\d+)[ \t]*$"
)
_INLINE_EDGE = re.compile(
    r"(?<![A-Za-z0-9_.-])([A-Za-z][A-Za-z0-9_.-]*)[ \t]*-->[ \t]*"
    r"([A-Za-z][A-Za-z0-9_.-]*)(?![A-Za-z0-9_.-])"
)
_BADGE_LINK = re.compile(r"\[!\[(?P<label>[^\]]+)\]\((?P<image>[^)]+)\)\]\((?P<target>[^)]+)\)")
_ANY_BADGE = re.compile(
    r"\[!\[(?P<link_label>[^\]]+)\]\((?P<link_image>[^)]+)\)\]\((?P<target>[^)]+)\)"
    r"|!\[(?P<image_label>[^\]]+)\]\((?P<image_url>[^)]+)\)"
)
_HEADING_WORD = re.compile(r"[A-Za-z][A-Za-z0-9.+#/-]*")
_HEADING_PROPER_WORDS = frozenset(
    {
        "Aspose",
        "GitHub",
        "Java",
        "JavaScript",
        "NuGet",
        "OneNote",
        "PyPI",
        "Python",
        "TypeScript",
    }
)
_CAPABILITY_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "conversion",
        "convert",
        "for",
        "in",
        "integrate",
        "integration",
        "python",
        "the",
        "to",
        "tools",
        "through",
        "workflow",
        "workflows",
    }
)


def validate_trusted_portfolio_brand(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> None:
    """Fail closed when a runtime-bound trusted brand contract is not met."""

    standards = {item.standard_id: item for item in graph.configured_standards}
    header = standards.get("readme.header")
    if (
        header is None
        or header.parameters.get("brand_contract_version")
        != TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION
    ):
        return
    _validate_header_and_sections(candidate, standards)
    _validate_mermaid(candidate, standards)
    _validate_enterprise_link(candidate, standards)


def normalize_trusted_portfolio_headings(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Apply configured heading style without changing section prose."""

    header = next(
        (
            standard
            for standard in graph.configured_standards
            if standard.standard_id == "readme.header"
        ),
        None,
    )
    if (
        header is None
        or header.parameters.get("brand_contract_version")
        != TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION
    ):
        return candidate

    def replace(match: re.Match[str]) -> str:
        title = _EMOJI.sub("", match.group(2)).replace("\ufe0f", "")
        title = " ".join(title.split()).strip()
        aliases = {
            str(key).casefold(): str(value)
            for key, value in header.parameters.get("heading_aliases", {}).items()
        }
        suffix_aliases = {
            str(key).casefold(): str(value)
            for key, value in header.parameters.get("heading_suffix_aliases", {}).items()
        }
        prefix_aliases = {
            str(key).casefold(): str(value)
            for key, value in header.parameters.get("heading_prefix_aliases", {}).items()
        }
        title = aliases.get(
            title.casefold(),
            next(
                (
                    replacement
                    for source, replacement in aliases.items()
                    if title.casefold().endswith(f" {source}")
                ),
                title,
            ),
        )
        title = next(
            (
                replacement
                for suffix, replacement in suffix_aliases.items()
                if title.casefold() == suffix or title.casefold().endswith(f" {suffix}")
            ),
            title,
        )
        title = next(
            (
                replacement
                for prefix, replacement in prefix_aliases.items()
                if title.casefold().startswith(prefix)
            ),
            title,
        )
        if len(match.group(1)) > 1:
            title = (
                title_case_heading(title)
                if header.parameters.get("heading_style") == "title_case_without_emoji"
                else _sentence_case_heading(title)
            )
        return f"{match.group(1)} {title}"

    return _HEADING.sub(replace, candidate)


def normalize_trusted_portfolio_emojis(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Remove every emoji from a candidate governed by the portfolio contract."""

    header = next(
        (
            standard
            for standard in graph.configured_standards
            if standard.standard_id == "readme.header"
        ),
        None,
    )
    if (
        header is None
        or header.parameters.get("brand_contract_version")
        != TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION
        or header.parameters.get("emoji_policy") != PRESENTATION_EMOJI_POLICY
    ):
        return candidate
    return strip_readme_emojis(candidate)


def strip_readme_emojis(markdown: str) -> str:
    """Remove emoji code points while preserving the surrounding README content."""

    normalized = _EMOJI.sub("", markdown).replace("\ufe0f", "").replace("\u200d", "")
    normalized = re.sub(r"(?m)^([ \t]*[-*+][ \t]+)[ \t]+", r"\1", normalized)
    normalized = re.sub(r"(?<!!)\[[ \t]+", "[", normalized)
    normalized = re.sub(r"(?m)^[ \t]+(?=[*_])", "", normalized)
    return normalized


def normalize_trusted_portfolio_header_assets(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Place inherited project badges and quick links after the shared core row."""

    standards = {item.standard_id: item for item in graph.configured_standards}
    header = standards.get("readme.header")
    badges = standards.get("readme.badges")
    if (
        header is None
        or badges is None
        or header.parameters.get("brand_contract_version")
        != TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION
    ):
        return candidate
    required_core_row = str(badges.parameters.get("required_core_row", ""))
    normalized = candidate
    if required_core_row:
        normalized = re.sub(
            rf"\A(# [^\r\n]+)\r?\n(?:[ \t]*\r?\n)+(?={re.escape(required_core_row)})",
            r"\1\n\n",
            normalized,
            count=1,
        )
    inherited_badges: list[str] = []
    quick_links: list[str] = []
    removable: list[str] = []
    for fact in graph.inherited_facts:
        badge_matches = list(_BADGE_LINK.finditer(fact.value))
        if badge_matches:
            removable.append(fact.value)
            inherited_badges.extend(
                match.group(0)
                for match in badge_matches
                if "license" not in match.group("label").casefold()
            )
        if fact.value.lstrip().casefold().startswith("quick links:"):
            removable.append(fact.value)
            quick_links.append(fact.value.strip())
    if not inherited_badges and not quick_links:
        return _normalize_header_badge_lines(normalized)
    for value in dict.fromkeys(removable):
        normalized = normalized.replace(value, "")
    core_offset = normalized.find(required_core_row)
    if core_offset < 0:
        return candidate
    insert_at = core_offset + len(required_core_row)
    assets = []
    if inherited_badges:
        assets.append(" ".join(dict.fromkeys(inherited_badges)))
    assets.extend(dict.fromkeys(quick_links))
    normalized = normalized[:insert_at] + "\n\n" + "\n\n".join(assets) + normalized[insert_at:]
    return _normalize_header_badge_lines(normalized)


def _normalize_header_badge_lines(candidate: str) -> str:
    """Remove model-control leakage and duplicate badge labels from the header."""

    first_h2 = re.search(r"(?m)^##[ \t]+", candidate)
    header_end = len(candidate) if first_h2 is None else first_h2.start()
    lines = candidate[:header_end].splitlines(keepends=True)
    seen_labels: set[str] = set()
    seen_quick_links: set[str] = set()
    normalized: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "required_core_row":
            continue
        if stripped.casefold().startswith("quick links:"):
            identity = " ".join(strip_readme_emojis(stripped).split()).casefold()
            if identity in seen_quick_links:
                continue
            seen_quick_links.add(identity)
        matches = list(_ANY_BADGE.finditer(line))
        if not matches or _ANY_BADGE.sub("", line).strip():
            normalized.append(line)
            continue
        kept: list[str] = []
        for match in matches:
            label = str(match.group("link_label") or match.group("image_label")).strip().casefold()
            if label in seen_labels:
                continue
            seen_labels.add(label)
            kept.append(match.group(0))
        if kept:
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            normalized.append(" ".join(kept) + ending)
    header = re.sub(r"(?:\r?\n){3,}", "\n\n", "".join(normalized))
    return header + candidate[header_end:]


def normalize_trusted_key_capabilities(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Carry complete inherited capability lists into the common capability section."""

    header = next(
        (item for item in graph.configured_standards if item.standard_id == "readme.header"),
        None,
    )
    if (
        header is None
        or header.parameters.get("brand_contract_version")
        != TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION
    ):
        return candidate
    primary_facts = [
        fact
        for fact in graph.inherited_facts
        if fact.material_kind in {"unordered_list", "ordered_list"}
        and any(
            _plain_heading(part) in {"features", "key capabilities", "capabilities"}
            or _plain_heading(part).endswith(" features")
            for part in fact.heading_path
        )
    ]
    supplementary_facts = [
        fact
        for fact in graph.inherited_facts
        if fact.material_kind in {"unordered_list", "ordered_list"}
        and any(_plain_heading(part).startswith("why ") for part in fact.heading_path)
    ]
    if not primary_facts and not supplementary_facts:
        return candidate
    key_span = _h2_section_span(candidate, "Key capabilities")
    if key_span is None:
        return candidate
    complete_lines = [
        line for fact in primary_facts for line in fact.value.strip().splitlines() if line.strip()
    ]
    signatures = {
        signature for line in complete_lines if (signature := _capability_signature(line))
    }
    for fact in supplementary_facts:
        for line in fact.value.strip().splitlines():
            signature = _capability_signature(line)
            if not signature or signature in signatures:
                continue
            complete_lines.append(line)
            signatures.add(signature)
    complete_body = "\n".join(complete_lines)
    key_heading_end = candidate.find("\n", key_span[0])
    if key_heading_end < 0:
        return candidate
    normalized = (
        candidate[: key_heading_end + 1] + "\n" + complete_body + "\n\n" + candidate[key_span[1] :]
    )
    feature_span = next(
        (
            span
            for title in ("Features",)
            if (span := _h2_section_span(normalized, title)) is not None
        ),
        None,
    )
    if feature_span is not None:
        normalized = normalized[: feature_span[0]] + normalized[feature_span[1] :]
    return normalized


def normalize_trusted_portfolio_mermaid(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Canonicalize model-selected diagram labels into the shared grammar."""

    standards = {item.standard_id: item for item in graph.configured_standards}
    mermaid = standards.get("readme.at_a_glance_mermaid")
    if mermaid is None or mermaid.parameters.get("visual_grammar") != PRESENTATION_MERMAID_GRAMMAR:
        return candidate
    heading = re.search(r"^## At a Glance[ \t]*$", candidate, re.MULTILINE | re.IGNORECASE)
    if heading is None:
        return candidate
    next_h2 = re.search(r"(?m)^## ", candidate[heading.end() :])
    section_end = len(candidate) if next_h2 is None else heading.end() + next_h2.start()
    fence = _MERMAID_FENCE.search(candidate, heading.end(), section_end)
    if fence is None:
        return candidate
    selected_by_id: dict[str, str] = {}
    for node_id, label in _INLINE_NODE.findall(fence.group(1)):
        selected_by_id.setdefault(node_id, label.strip())
    selected = list(selected_by_id.items())
    input_nodes = [(node_id, label) for node_id, label in selected if node_id.startswith("I")]
    capability_nodes = [
        (node_id, label) for node_id, label in selected if node_id.startswith(("C", "F"))
    ]
    output_nodes = [(node_id, label) for node_id, label in selected if node_id.startswith("O")]
    product_nodes = [
        (node_id, label)
        for node_id, label in selected
        if not node_id.startswith(("I", "C", "F", "O"))
    ]
    if not product_nodes and re.search(r"\bPRODUCT\b", fence.group(1)):
        title = _H1.search(candidate)
        if title is not None:
            product_label = title.group(1).split(":", maxsplit=1)[0].strip()
            if product_label:
                product_nodes = [("PRODUCT", product_label)]
    inputs = [label for _, label in input_nodes]
    capabilities = [label for _, label in capability_nodes]
    outputs = [label for _, label in output_nodes]
    products = [label for _, label in product_nodes]
    maximum_nodes = int(mermaid.parameters.get("max_nodes", PRESENTATION_MERMAID_MAX_NODES))
    maximum_label = int(
        mermaid.parameters.get(
            "max_label_characters",
            PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
        )
    )
    if (
        not inputs
        or len(capabilities) < 2
        or not outputs
        or len(products) != 1
        or len(inputs) + len(capabilities) + len(outputs) + 1 > maximum_nodes
        or any(
            len(label) > maximum_label for label in [*inputs, *products, *capabilities, *outputs]
        )
    ):
        return candidate
    lines = ["flowchart LR", "  subgraph Inputs"]
    lines.extend(f'    I{index}["{label}"]' for index, label in enumerate(inputs, start=1))
    lines.extend(["  end", f'  PRODUCT["{products[0]}"]', "  subgraph Capabilities"])
    lines.extend(f'    C{index}["{label}"]' for index, label in enumerate(capabilities, start=1))
    lines.extend(["  end", "  subgraph Outputs"])
    lines.extend(f'    O{index}["{label}"]' for index, label in enumerate(outputs, start=1))
    lines.append("  end")
    node_map = {
        **{node_id: f"I{index}" for index, (node_id, _) in enumerate(input_nodes, start=1)},
        **{node_id: f"C{index}" for index, (node_id, _) in enumerate(capability_nodes, start=1)},
        **{node_id: f"O{index}" for index, (node_id, _) in enumerate(output_nodes, start=1)},
        product_nodes[0][0]: "PRODUCT",
    }
    edge_source = _INLINE_NODE.sub(lambda match: match.group(1), fence.group(1))
    selected_edges = {
        (node_map[left], node_map[right])
        for left, right in _INLINE_EDGE.findall(edge_source)
        if left in node_map and right in node_map
    }
    permitted_edges = {
        (left, right)
        for left, right in selected_edges
        if (left.startswith("I") and right == "PRODUCT")
        or (left == "PRODUCT" and right.startswith("C"))
        or (left.startswith("C") and right.startswith("O"))
    }
    complete_edges = (
        all((f"I{index}", "PRODUCT") in permitted_edges for index in range(1, len(inputs) + 1))
        and all(
            ("PRODUCT", f"C{index}") in permitted_edges for index in range(1, len(capabilities) + 1)
        )
        and all(
            any(left.startswith("C") and right == f"O{index}" for left, right in permitted_edges)
            for index in range(1, len(outputs) + 1)
        )
    )
    if complete_edges:
        lines.extend(
            f"  {left} --> {right}" for left, right in sorted(permitted_edges, key=_edge_sort_key)
        )
    else:
        lines.extend(f"  I{index} --> PRODUCT" for index in range(1, len(inputs) + 1))
        lines.extend(f"  PRODUCT --> C{index}" for index in range(1, len(capabilities) + 1))
        lines.extend(
            f"  C{((index - 1) % len(capabilities)) + 1} --> O{index}"
            for index in range(1, len(outputs) + 1)
        )
    replacement = "\n".join(lines)
    return candidate[: fence.start(1)] + replacement + "\n" + candidate[fence.end(1) :]


def _edge_sort_key(edge: tuple[str, str]) -> tuple[int, int, int]:
    """Keep canonical edge groups and numeric node order stable."""

    left, right = edge
    group = 0 if left.startswith("I") else 1 if left == "PRODUCT" else 2
    left_number = int(re.sub(r"\D", "", left) or "0")
    right_number = int(re.sub(r"\D", "", right) or "0")
    return group, left_number, right_number


def restore_trusted_at_a_glance(
    candidate: str,
    accepted_candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Preserve validated header, visual, and navigation shells during content repair."""

    standards = {item.standard_id: item for item in graph.configured_standards}
    header = standards.get("readme.header")
    if (
        header is None
        or header.parameters.get("brand_contract_version")
        != TRUSTED_PORTFOLIO_BRAND_CONTRACT_VERSION
    ):
        return candidate
    prior_h1 = _H1.search(accepted_candidate)
    candidate_h1 = _H1.search(candidate)
    badges = standards.get("readme.badges")
    required_core_row = (
        "" if badges is None else str(badges.parameters.get("required_core_row", ""))
    )
    if prior_h1 is not None and candidate_h1 is None:
        candidate = f"# {prior_h1.group(1)}\n\n{required_core_row}\n\n" + candidate.lstrip()
    elif prior_h1 is not None and candidate_h1 is not None:
        candidate = (
            candidate[: candidate_h1.start()]
            + f"# {prior_h1.group(1)}"
            + candidate[candidate_h1.end() :]
        )
        candidate_h1 = _H1.search(candidate)
        assert candidate_h1 is not None
        after_h1 = candidate[candidate_h1.end() :].lstrip("\r\n ")
        first_line = after_h1.splitlines()[0].strip() if after_h1 else ""
        if required_core_row and first_line != required_core_row:
            candidate = (
                candidate[: candidate_h1.end()]
                + f"\n\n{required_core_row}\n"
                + candidate[candidate_h1.end() :]
            )
    accepted_span = _h2_section_span(accepted_candidate, "At a glance")
    if accepted_span is None:
        return candidate
    accepted_section = accepted_candidate[accepted_span[0] : accepted_span[1]]
    candidate_span = _h2_section_span(candidate, "At a glance")
    if candidate_span is not None:
        candidate = (
            candidate[: candidate_span[0]] + accepted_section + candidate[candidate_span[1] :]
        )
    else:
        navigation = re.search(r"(?m)^## Navigation[ \t]*$", candidate)
        insertion = navigation.start() if navigation is not None else _first_h2_offset(candidate)
        candidate = candidate[:insertion] + accepted_section + candidate[insertion:]
    if _h2_section_span(candidate, "Navigation") is None:
        prior_navigation = _h2_section_span(accepted_candidate, "Navigation")
        current_glance = _h2_section_span(candidate, "At a glance")
        if prior_navigation is not None and current_glance is not None:
            navigation_section = accepted_candidate[prior_navigation[0] : prior_navigation[1]]
            candidate = (
                candidate[: current_glance[1]] + navigation_section + candidate[current_glance[1] :]
            )
    return candidate


def normalize_trusted_enterprise_product_links(
    candidate: str,
    graph: TrustedReadmeFactGraphV1,
) -> str:
    """Keep the one configured Enterprise Edition target without adding prose."""

    standard = next(
        (
            item
            for item in graph.configured_standards
            if item.standard_id == "readme.contextual_links"
        ),
        None,
    )
    if standard is None:
        return candidate
    required = str(standard.parameters.get("required_enterprise_url", ""))
    if not required:
        return candidate
    product_name = str(
        standard.parameters.get("enterprise_product_name", "Enterprise Edition")
    ).strip()
    if not product_name.endswith("Enterprise Edition"):
        product_name += " Enterprise Edition"
    links = list(
        re.finditer(
            r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)",
            candidate,
        )
    )
    raw_urls = list(_URL.finditer(candidate))
    keep_range: tuple[int, int] | None = None
    eligible = [
        match
        for match in links
        if (
            urlsplit(match.group(2).rstrip(".,;:")).netloc.casefold() == "products.aspose.com"
            and normalize_target_url(match.group(2).rstrip(".,;:"))
            == normalize_target_url(required)
        )
    ]
    scope_span = _h2_section_span(candidate, PRESENTATION_ENTERPRISE_LINK_SECTION)
    preferred = next(
        (
            match
            for match in eligible
            if scope_span is not None and scope_span[0] <= match.start() < scope_span[1]
        ),
        None,
    )
    if preferred is not None:
        keep_range = (preferred.start(), preferred.end())
    edits: dict[tuple[int, int], str] = {}
    for match in links:
        if urlsplit(match.group(2).rstrip(".,;:")).netloc.casefold() != "products.aspose.com":
            continue
        if keep_range == (match.start(), match.end()):
            if match.group(1).strip() != product_name:
                edits[(match.start(), match.end())] = f"[{product_name}]({match.group(2)})"
            continue
        edits[(match.start(), match.end())] = match.group(1)
    for match in raw_urls:
        if urlsplit(match.group(0).rstrip(".,;:")).netloc.casefold() != "products.aspose.com":
            continue
        if any(start <= match.start() and match.end() <= end for start, end in edits):
            continue
        if (
            keep_range is not None
            and keep_range[0] <= match.start()
            and match.end() <= keep_range[1]
        ):
            continue
        edits[(match.start(), match.end())] = ""
    normalized = candidate
    for (start, end), replacement in sorted(edits.items(), reverse=True):
        normalized = normalized[:start] + replacement + normalized[end:]
    if normalize_target_url(required) not in {
        normalize_target_url(match.group(0).rstrip(".,;:")) for match in _URL.finditer(normalized)
    }:
        sentence = (
            "For requirements outside this repository's documented scope, "
            f"[{product_name}]({required}) is the related product."
        )
        scope = _h2_section_span(normalized, PRESENTATION_ENTERPRISE_LINK_SECTION)
        if scope is None:
            normalized = normalized.rstrip() + (
                f"\n\n## {PRESENTATION_ENTERPRISE_LINK_SECTION}\n\n" + sentence + "\n"
            )
        else:
            insertion = scope[1]
            normalized = (
                normalized[:insertion].rstrip()
                + "\n\n"
                + sentence
                + "\n\n"
                + normalized[insertion:].lstrip()
            )
    return normalized


def validate_trusted_portfolio_cohort(
    candidates: dict[str, tuple[str, TrustedReadmeFactGraphV1]],
) -> None:
    """Compare candidates so individually valid portfolio drift cannot pass."""

    if not candidates:
        raise LLMError("trusted portfolio cohort is empty")
    section_prefixes: set[tuple[str, ...]] = set()
    diagram_sources: set[str] = set()
    for candidate, graph in candidates.values():
        validate_trusted_portfolio_brand(candidate, graph)
        standards = {item.standard_id: item for item in graph.configured_standards}
        header = standards["readme.header"].parameters
        expected = tuple(str(item) for item in header.get("required_h2_prefix", []))
        actual = tuple(match.group(1).strip() for match in _H2.finditer(candidate))
        section_prefixes.add(actual[: len(expected)])
        diagram_sources.add(_at_a_glance_mermaid(candidate))
    if len(section_prefixes) != 1:
        raise LLMError("trusted cohort candidates do not share one macro-section prefix")
    if len(candidates) > 1 and len(diagram_sources) != len(candidates):
        raise LLMError("trusted cohort reused a generic At a glance diagram")


def _validate_header_and_sections(candidate: str, standards: dict) -> None:
    h1s = list(_H1.finditer(candidate))
    if len(h1s) != 1:
        raise LLMError("portfolio brand contract requires exactly one H1")
    first_content = candidate.lstrip("\ufeff\r\n ")
    if not first_content.startswith("# "):
        raise LLMError("portfolio brand contract requires the H1 to be first")
    if _EMOJI.search(candidate) or "\ufe0f" in candidate or "\u200d" in candidate:
        raise LLMError("portfolio brand contract prohibits emojis anywhere in the README")

    badges = standards.get("readme.badges")
    required_row = "" if badges is None else str(badges.parameters.get("required_core_row", ""))
    after_h1 = candidate[h1s[0].end() :].lstrip("\r\n ")
    first_line = after_h1.splitlines()[0].strip() if after_h1 else ""
    if not required_row or first_line != required_row:
        raise LLMError("portfolio brand contract requires the configured core badge row after H1")

    expected_prefix = tuple(
        str(item) for item in standards["readme.header"].parameters.get("required_h2_prefix", [])
    )
    actual = tuple(match.group(1).strip() for match in _H2.finditer(candidate))
    if not expected_prefix or actual[: len(expected_prefix)] != expected_prefix:
        raise LLMError(
            "portfolio brand contract requires the common At a glance, Navigation, "
            "Key capabilities, Installation, and Quick start section order"
        )


def _h2_section_span(markdown: str, title: str) -> tuple[int, int] | None:
    heading = re.search(rf"(?mi)^##[ \t]+{re.escape(title)}[ \t]*$", markdown)
    if heading is None:
        return None
    next_h2 = re.search(r"(?m)^##[ \t]+", markdown[heading.end() :])
    end = len(markdown) if next_h2 is None else heading.end() + next_h2.start()
    return heading.start(), end


def _first_h2_offset(markdown: str) -> int:
    heading = re.search(r"(?m)^##[ \t]+", markdown)
    return len(markdown) if heading is None else heading.start()


def _plain_heading(value: str) -> str:
    return " ".join(_EMOJI.sub("", value).replace("\ufe0f", "").split()).casefold()


def _sentence_case_heading(title: str) -> str:
    """Lower generic title-case words while retaining technical and product spelling."""

    seen_word = False

    def replace(match: re.Match[str]) -> str:
        nonlocal seen_word
        word = match.group(0)
        if not seen_word:
            seen_word = True
            return word
        if (
            word in _HEADING_PROPER_WORDS
            or word.isupper()
            or any(character.isdigit() for character in word)
            or any(character in ".+#/" for character in word)
            or not (word[:1].isupper() and word[1:].islower())
        ):
            return word
        return word.casefold()

    return _HEADING_WORD.sub(replace, title)


def _capability_signature(line: str) -> frozenset[str]:
    """Identify equivalent capability bullets without depending on their prose order."""

    words = {
        word
        for word in re.findall(r"[a-z0-9]+", line.casefold())
        if word not in _CAPABILITY_STOP_WORDS
    }
    return frozenset(words)


def find_trusted_capability_list_representation(
    source_list: str,
    candidate: str,
) -> str | None:
    """Return one exact candidate list that semantically covers every source capability."""

    source_signatures = {
        signature for line in source_list.splitlines() if (signature := _capability_signature(line))
    }
    if not source_signatures:
        return None
    for match in re.finditer(r"(?m)(?:^[-*+][ \t]+.+(?:\r?\n|$))+", candidate):
        candidate_signatures = {
            signature
            for line in match.group(0).splitlines()
            if (signature := _capability_signature(line))
        }
        if source_signatures <= candidate_signatures:
            return match.group(0).rstrip("\r\n")
    return None


def _validate_mermaid(candidate: str, standards: dict) -> None:
    mermaid = standards.get("readme.at_a_glance_mermaid")
    if mermaid is None or mermaid.parameters.get("visual_grammar") != PRESENTATION_MERMAID_GRAMMAR:
        raise LLMError("portfolio brand contract is missing its Mermaid visual grammar")
    source = _at_a_glance_mermaid(candidate)
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not lines or lines[0] != "flowchart LR":
        raise LLMError("At a glance must use the shared left-to-right flowchart")
    if (
        lines.count("subgraph Inputs") != 1
        or lines.count("subgraph Capabilities") != 1
        or lines.count("subgraph Outputs") != 1
    ):
        raise LLMError("At a glance must contain Inputs, Capabilities, and Outputs zones")
    if any(re.match(r"^(?:style|classDef|class|click)\b", line) for line in lines):
        raise LLMError("At a glance contains presentation noise outside the shared grammar")

    nodes = _NODE.findall(source)
    node_ids = [node_id for node_id, _ in nodes]
    maximum_nodes = int(mermaid.parameters.get("max_nodes", PRESENTATION_MERMAID_MAX_NODES))
    maximum_label = int(
        mermaid.parameters.get(
            "max_label_characters",
            PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
        )
    )
    if not 3 <= len(nodes) <= maximum_nodes or node_ids.count("PRODUCT") != 1:
        raise LLMError("At a glance must contain one product and bounded input/outcome nodes")
    if not any(node_id.startswith("I") for node_id in node_ids) or not any(
        node_id.startswith("O") for node_id in node_ids
    ):
        raise LLMError("At a glance must contain at least one input and one outcome")
    if len([node_id for node_id in node_ids if node_id.startswith("C")]) < 2:
        raise LLMError("At a glance must contain at least two product-specific capabilities")
    if any(len(label.strip()) > maximum_label for _, label in nodes):
        raise LLMError("At a glance node labels must remain scannable")

    edges = set(_EDGE.findall(source))
    permitted = {
        (left, right)
        for left, right in edges
        if (left.startswith("I") and right == "PRODUCT")
        or (left == "PRODUCT" and right.startswith("C"))
        or (left.startswith("C") and right.startswith("O"))
    }
    if edges != permitted:
        raise LLMError(
            "At a glance edges must flow only from Inputs to Product to Capabilities to Outputs"
        )
    for node_id in node_ids:
        if node_id.startswith("I") and (node_id, "PRODUCT") not in edges:
            raise LLMError("At a glance contains an unconnected input")
        if node_id.startswith("C") and ("PRODUCT", node_id) not in edges:
            raise LLMError("At a glance contains an unconnected capability")
        if node_id.startswith("O") and not any(
            left.startswith("C") and right == node_id for left, right in edges
        ):
            raise LLMError("At a glance contains an unconnected outcome")


def _validate_enterprise_link(candidate: str, standards: dict) -> None:
    contextual = standards.get("readme.contextual_links")
    if contextual is None:
        raise LLMError("portfolio brand contract is missing contextual-link configuration")
    required = str(contextual.parameters.get("required_enterprise_url", ""))
    matches = [
        match
        for match in _URL.finditer(candidate)
        if urlsplit(match.group(0).rstrip(".,;:")).netloc.casefold() == "products.aspose.com"
    ]
    expected_count = int(contextual.parameters.get("required_aspose_com_occurrences", 1))
    if len(matches) != expected_count:
        raise LLMError("portfolio brand contract requires exactly one products.aspose.com link")
    actual = normalize_target_url(matches[0].group(0).rstrip(".,;:"))
    if not required or actual != normalize_target_url(required):
        raise LLMError(
            "portfolio brand contract requires the configured catalog-verified product link"
        )
    product_name = str(
        contextual.parameters.get("enterprise_product_name", "Enterprise Edition")
    ).strip()
    markdown_link = next(
        (
            link
            for link in _MARKDOWN_LINK.finditer(candidate)
            if normalize_target_url(link.group("url").rstrip(".,;:")) == actual
        ),
        None,
    )
    if markdown_link is None or markdown_link.group("label").strip() != product_name:
        raise LLMError("Enterprise Edition link requires the configured descriptive product label")
    paragraph_start = max(candidate.rfind("\n\n", 0, matches[0].start()), 0)
    paragraph_end = candidate.find("\n\n", matches[0].end())
    paragraph_end = len(candidate) if paragraph_end < 0 else paragraph_end
    paragraph = candidate[paragraph_start:paragraph_end]
    if "Enterprise Edition" not in paragraph:
        raise LLMError("contextual products.aspose.com prose must name the Enterprise Edition")
    visible_words = re.findall(r"\b[\w.-]+\b", re.sub(r"[`*_#\[\]()>-]", " ", paragraph))
    if len(visible_words) < 10:
        raise LLMError("Enterprise Edition link must be embedded in useful contextual prose")
    prior_sections = list(_H2.finditer(candidate[: matches[0].start()]))
    section = prior_sections[-1].group(1).strip() if prior_sections else ""
    if section.casefold() != PRESENTATION_ENTERPRISE_LINK_SECTION.casefold():
        raise LLMError(
            f"Enterprise Edition link must appear in {PRESENTATION_ENTERPRISE_LINK_SECTION} context"
        )
    if re.search(
        r"(?i)\b(?:for commercial use|please see|learn more|upgrade|buy now)\b", paragraph
    ):
        raise LLMError("Enterprise Edition link reads as a promotional call to action")


def _at_a_glance_mermaid(candidate: str) -> str:
    heading = re.search(r"^## At a Glance[ \t]*$", candidate, re.MULTILINE | re.IGNORECASE)
    if heading is None:
        raise LLMError("portfolio brand contract requires an At a glance section")
    next_h2 = re.search(r"(?m)^## ", candidate[heading.end() :])
    end = len(candidate) if next_h2 is None else heading.end() + next_h2.start()
    section = candidate[heading.end() : end]
    fences = list(_MERMAID_FENCE.finditer(section))
    if len(fences) != 1:
        raise LLMError("At a glance must contain exactly one Mermaid diagram")
    return fences[0].group(1).strip()
