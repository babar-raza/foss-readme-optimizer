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
    split_capability_columns,
    validate_capability_group_layout,
)
from readme_agent.readme.header_visual_mermaid import (
    capability_mermaid_label,
    compact_diagram_node_label,
    endpoint_mermaid_label,
    product_mermaid_label,
    raster_output_formats_label,
    render_capability_landscape,
)
from readme_agent.readme.header_visual_models import (
    HeaderVisualValidationV1,
    ReadmeHeaderVisualV1,
    safe_mermaid_label,
)
from readme_agent.readme.presentation_contract import (
    PRESENTATION_MERMAID_MAX_BLOCK_LINES,
    PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS,
)

_ACCEPTED_STATES = {"verified", "policy_approved"}


def validate_readme_header_visual(
    visual: ReadmeHeaderVisualV1,
    facts: ProductFactsV2,
    *,
    candidate_text: str | None = None,
) -> HeaderVisualValidationV1:
    """Fail closed on unsupported badges, unsafe nodes, or malformed Mermaid."""

    checks: dict[str, bool] = {}
    errors: list[str] = []
    diagramless = visual.mermaid_markdown == "" and len(visual.diagram_nodes) <= 1
    parsed = MarkdownIt("commonmark").parse(visual.mermaid_markdown)
    fences = [
        token for token in parsed if token.type == "fence" and token.info.strip() == "mermaid"
    ]
    checks["one_mermaid_fence"] = (
        visual.mermaid_source == ""
        if diagramless
        else len(fences) == 1 and fences[0].content.rstrip() == visual.mermaid_source
    )
    lines = visual.mermaid_source.splitlines()
    capability_ids = [node.node_id for node in visual.diagram_nodes if node.role == "capability"]
    checks["mermaid_subset_parses"] = diagramless or (
        bool(lines)
        and lines[0] == "flowchart LR"
        and visual.mermaid_source == render_capability_landscape(visual.diagram_nodes)
    )
    adaptive_layout_valid = diagramless or validate_capability_group_layout(
        visual.mermaid_source, capability_ids
    )
    checks["capability_layout_adaptive"] = adaptive_layout_valid
    checks["capability_layout_vertical"] = adaptive_layout_valid
    checks["mermaid_block_compact"] = len(lines) <= PRESENTATION_MERMAID_MAX_BLOCK_LINES
    capability_columns = split_capability_columns(capability_ids)
    checks["capability_columns_balanced"] = (
        len(capability_columns) == (1 if len(capability_ids) <= 5 else 2)
        and max(map(len, capability_columns)) - min(map(len, capability_columns)) <= 1
    )
    checks["labels_compact"] = all(
        len(node.label) <= PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS
        for node in visual.diagram_nodes
        if node.role != "product"
    )
    checks["labels_safe"] = all(
        safe_mermaid_label(node.label) == node.label for node in visual.diagram_nodes
    )
    checks["diagram_specific"] = (
        bool(visual.diagram_nodes)
        and visual.diagram_nodes[0].role == "product"
        and (diagramless or any(node.role != "product" for node in visual.diagram_nodes))
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
    raster_formats = raster_output_formats_label(facts)
    expected_capabilities = {
        " ".join(
            compact_diagram_node_label(
                node.label,
                "capability",
                raster_output_formats=raster_formats,
                product_name=visual.diagram_nodes[0].label,
            )
            .casefold()
            .split()
        ): set(node.supporting_fact_ids)
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
        diagramless
        or (
            f"  {visual.diagram_nodes[0].node_id}"
            f'["{product_mermaid_label(visual.diagram_nodes[0].label)}"]'
            in visual.mermaid_source
            and all(
                (
                    f'{node.node_id}["{endpoint_mermaid_label(node.label)}"]'
                    if node.role in {"input", "output"}
                    else f'{node.node_id}["{capability_mermaid_label(node.label)}"]'
                )
                in visual.mermaid_source
                for node in visual.diagram_nodes[1:]
            )
        )
    ) and all(badge.alt_text in visual.badge_markdown for badge in visual.badges)
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
        header_lines = before_first_h2.splitlines()
        banner_indexes = [
            index
            for index, line in enumerate(header_lines)
            if line.startswith("![") and "products.aspose.org" in line
        ]
        badge_indexes = [index for index, line in enumerate(header_lines) if line in badge_lines]
        checks["candidate_banner_wellformed"] = len(banner_indexes) <= 1 and all(
            re.fullmatch(
                rf"!\[{re.escape(visual.title)}\]"
                r"\(https://products\.aspose\.org/media/[a-z0-9./_-]+\)",
                header_lines[index],
            )
            is not None
            and badge_indexes
            and index > badge_indexes[0]
            for index in banner_indexes
        )
        checks["candidate_exact_mermaid"] = (
            candidate_text.count("```mermaid") == 0
            if diagramless
            else (
                candidate_text.count(visual.mermaid_markdown) == 1
                and candidate_text.count("```mermaid") == 1
            )
        )
        checks["candidate_has_no_html_comments"] = "<!--" not in candidate_text
    for name, passed in checks.items():
        if not passed:
            errors.append(f"{name} failed")
    return HeaderVisualValidationV1(valid=not errors, checks=checks, errors=errors)
