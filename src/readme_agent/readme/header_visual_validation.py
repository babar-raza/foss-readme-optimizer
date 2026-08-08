"""Validate factual badge provenance and the generated Mermaid grammar subset."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.diagram_role_semantics import selected_verified_capability_nodes
from readme_agent.readme.diagram_semantic_candidates import meaningful_diagram_tokens
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.header_badge_targets import normalized_badge_target
from readme_agent.readme.header_visual_layout import (
    capability_layout_edges,
    validate_capability_group_layout,
)
from readme_agent.readme.header_visual_models import (
    HeaderVisualValidationV1,
    ReadmeHeaderVisualV1,
    safe_mermaid_label,
)

_ACCEPTED_STATES = {"verified", "policy_approved"}
_ROOT_LINE = re.compile(r'^\s{2}(PRODUCT)\["([^"]+)"\]$')
_GROUP_LINE = re.compile(r'^\s{2}subgraph (Inputs|Capabilities|Outputs)\["([^"]+)"\]$')
_NODE_LINE = re.compile(r'^\s{4,6}([ICO]\d+)\["([^"]+)"\]$')
_EDGE_LINE = re.compile(r"^\s{2}([A-Za-z][A-Za-z0-9]*) --- ([A-Za-z][A-Za-z0-9]*)$")
_LAYOUT_EDGE_LINE = re.compile(r"^\s{4,6}(C\d+) ~~~ (C\d+)$")


def validate_readme_header_visual(
    visual: ReadmeHeaderVisualV1,
    facts: ProductFactsV2,
    *,
    candidate_text: str | None = None,
) -> HeaderVisualValidationV1:
    """Fail closed on unsupported badges, unsafe nodes, or malformed Mermaid."""

    checks: dict[str, bool] = {}
    errors: list[str] = []
    parsed = MarkdownIt("commonmark").parse(visual.mermaid_markdown)
    fences = [
        token for token in parsed if token.type == "fence" and token.info.strip() == "mermaid"
    ]
    checks["one_mermaid_fence"] = (
        len(fences) == 1 and fences[0].content.rstrip() == visual.mermaid_source
    )
    lines = visual.mermaid_source.splitlines()
    root_lines = [match for line in lines[1:] if (match := _ROOT_LINE.fullmatch(line)) is not None]
    group_lines = [
        match for line in lines[1:] if (match := _GROUP_LINE.fullmatch(line)) is not None
    ]
    node_lines = [
        match
        for line in lines[1:]
        if (match := _NODE_LINE.fullmatch(line)) is not None and match.group(1) != "product"
    ]
    edge_lines = [match for line in lines[1:] if (match := _EDGE_LINE.fullmatch(line)) is not None]
    layout_edge_lines = [
        match for line in lines[1:] if (match := _LAYOUT_EDGE_LINE.fullmatch(line)) is not None
    ]
    parsed_edges = {(match.group(1), match.group(2)) for match in edge_lines}
    input_ids = {node.node_id for node in visual.diagram_nodes if node.role == "input"}
    output_ids = {node.node_id for node in visual.diagram_nodes if node.role == "output"}
    capability_ids = [node.node_id for node in visual.diagram_nodes if node.role == "capability"]
    expected_layout_edges = capability_layout_edges(capability_ids)
    parsed_layout_edges = [(match.group(1), match.group(2)) for match in layout_edge_lines]
    expected_edges = {
        *((node_id, "PRODUCT") for node_id in input_ids),
        ("PRODUCT", "Capabilities"),
        *([("Capabilities", "Outputs")] if output_ids else []),
    }
    expected_groups = ["Inputs"] if input_ids else []
    expected_groups.append("Capabilities")
    if output_ids:
        expected_groups.append("Outputs")
    checks["mermaid_subset_parses"] = bool(
        lines
        and lines[0] == "flowchart LR"
        and len(root_lines) == 1
        and root_lines[0].group(1) == visual.diagram_nodes[0].node_id
        and root_lines[0].group(2) == visual.diagram_nodes[0].label
        and [match.group(1) for match in group_lines] == expected_groups
        and len(node_lines) == len(visual.diagram_nodes) - 1
        and parsed_edges == expected_edges
        and "-->" not in visual.mermaid_source
        and visual.mermaid_source.count("~~~") == len(expected_layout_edges)
    )
    adaptive_layout_valid = (
        validate_capability_group_layout(visual.mermaid_source, capability_ids)
        and parsed_layout_edges == expected_layout_edges
    )
    checks["capability_layout_adaptive"] = adaptive_layout_valid
    checks["capability_layout_vertical"] = adaptive_layout_valid
    checks["labels_safe"] = all(
        safe_mermaid_label(node.label) == node.label for node in visual.diagram_nodes
    )
    checks["diagram_specific"] = visual.diagram_nodes[0].role == "product" and any(
        node.role != "product" for node in visual.diagram_nodes
    )
    role_labels = [
        (node.role, " ".join(node.label.casefold().split())) for node in visual.diagram_nodes
    ]
    checks["diagram_role_labels_unique"] = len(role_labels) == len(set(role_labels))
    capability_tokens = {
        frozenset(meaningful_diagram_tokens(node.label))
        for node in visual.diagram_nodes
        if node.role == "capability"
    }
    checks["capabilities_not_duplicated_as_outputs"] = all(
        frozenset(meaningful_diagram_tokens(node.label)) not in capability_tokens
        for node in visual.diagram_nodes
        if node.role == "output"
    )
    expected_capabilities = {
        " ".join(node.label.casefold().split()): set(node.supporting_fact_ids)
        for node in selected_verified_capability_nodes(facts)
    }
    rendered_capabilities = {
        " ".join(node.label.casefold().split()): set(node.fact_ids)
        for node in visual.diagram_nodes
        if node.role == "capability"
    }
    checks["selected_capabilities_complete"] = all(
        label in rendered_capabilities and fact_ids <= rendered_capabilities[label]
        for label, fact_ids in expected_capabilities.items()
    )
    checks["maps_match_markdown"] = (
        f'  {visual.diagram_nodes[0].node_id}["{visual.diagram_nodes[0].label}"]'
        in visual.mermaid_source
        and all(
            re.search(
                rf'^\s{{4,6}}{re.escape(node.node_id)}\["{re.escape(node.label)}"\]$',
                visual.mermaid_source,
                re.MULTILINE,
            )
            is not None
            for node in visual.diagram_nodes[1:]
        )
        and all(badge.alt_text in visual.badge_markdown for badge in visual.badges)
    )
    citations = visual.all_fact_ids
    checks["citations_accepted"] = all(
        (
            (fact := facts.fact_by_id(fact_id)).verification_state in _ACCEPTED_STATES
            and not fact.has_unresolved_conflict
            and facts.selected_fact_ids.get(fact.field) == fact_id
        )
        for fact_id in citations
    )
    checks["badge_kinds_supported"] = all(
        badge.kind
        in {
            "version",
            "package",
            "download",
            "platform",
            "build",
            "source",
            "license",
            "contributors",
        }
        for badge in visual.badges
    )
    badge_targets = [
        target
        for badge in visual.badges
        if (target := normalized_badge_target(badge.target_url)) is not None
    ]
    checks["badge_targets_distinct"] = len(badge_targets) == len(set(badge_targets))
    registry_badges = [
        badge for badge in visual.badges if badge.kind in {"version", "package", "download"}
    ]
    acquisition = facts.selected_fact("installation.verified_acquisition")
    acquisition_value = acquisition.value if isinstance(acquisition.value, dict) else {}
    coordinate = acquisition_value.get("coordinate")
    registry_only_badges = [
        badge for badge in registry_badges if badge.kind in {"package", "download"}
    ]
    version_badges = [badge for badge in registry_badges if badge.kind == "version"]
    registry_verified = (
        acquisition.verification_state in _ACCEPTED_STATES
        and acquisition_value.get("outcome") == "REGISTRY_VERIFIED"
        and isinstance(coordinate, dict)
        and bool(coordinate)
    )
    source_version_verified = (
        acquisition.verification_state in _ACCEPTED_STATES
        and acquisition_value.get("outcome") == "SOURCE_BUILD_VERIFIED"
        and acquisition_value.get("truth_eligible") is True
        and isinstance(acquisition_value.get("source_build_receipt"), dict)
    )
    checks["registry_badges_verified"] = (not registry_only_badges or registry_verified) and (
        not version_badges or registry_verified or source_version_verified
    )
    source_badges = [badge for badge in visual.badges if badge.kind == "source"]
    identity = facts.selected_fact("product.identity")
    identity_value = identity.value if isinstance(identity.value, dict) else {}
    repository = str(identity_value.get("repository") or facts.org_repo).strip()
    checks["source_badges_verified"] = not source_badges or (
        identity.verification_state in _ACCEPTED_STATES
        and not identity.has_unresolved_conflict
        and len(repository.split("/")) == 2
    )
    license_badges = [badge for badge in visual.badges if badge.kind == "license"]
    license_fact = facts.selected_fact("product.license")
    checks["license_badge_verified"] = not license_badges or (
        license_fact.verification_state in _ACCEPTED_STATES
        and not license_fact.has_unresolved_conflict
    )
    checks["no_html_or_agent_metadata"] = not any(
        token in visual.badge_markdown + visual.mermaid_markdown
        for token in ("<!--", "readme-agent", "sha256:")
    )
    if candidate_text is not None:
        h1_titles = [
            heading.title for heading in parse_headings(candidate_text) if heading.level == 1
        ]
        before_first_h2 = re.split(r"(?m)^## ", candidate_text, maxsplit=1)[0]
        badge_lines = [
            line
            for line in before_first_h2.splitlines()
            if "shields.io/" in line or "actions/workflows/" in line
        ]
        checks["candidate_exact_title"] = h1_titles == [visual.title]
        checks["candidate_exact_badges"] = badge_lines == [visual.badge_markdown]
        checks["candidate_exact_mermaid"] = (
            candidate_text.count(visual.mermaid_markdown) == 1
            and candidate_text.count("```mermaid") == 1
        )
        checks["candidate_has_no_html_comments"] = "<!--" not in candidate_text
    for name, passed in checks.items():
        if not passed:
            errors.append(f"{name} failed")
    return HeaderVisualValidationV1(valid=not errors, checks=checks, errors=errors)
