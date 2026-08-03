"""Validate factual badge provenance and the generated Mermaid grammar subset."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.header_visual_models import (
    HeaderVisualValidationV1,
    ReadmeHeaderVisualV1,
    safe_mermaid_label,
)

_ACCEPTED_STATES = {"verified", "policy_approved"}
_NODE_LINE = re.compile(r'^\s{2,4}([a-z][a-z0-9_]*)\["([^"]+)"\]$')
_EDGE_LINE = re.compile(r"^\s{2}([a-z][a-z0-9_]*) --- ([a-z][a-z0-9_]*)$")


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
    node_lines = [match for line in lines[1:] if (match := _NODE_LINE.fullmatch(line)) is not None]
    edge_lines = [match for line in lines[1:] if (match := _EDGE_LINE.fullmatch(line)) is not None]
    checks["mermaid_subset_parses"] = bool(
        lines
        and lines[0] == "flowchart LR"
        and len(node_lines) == len(visual.diagram_nodes)
        and edge_lines
        and len(edge_lines) >= len(visual.diagram_nodes) - 1
    )
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
    checks["maps_match_markdown"] = all(
        f'  {node.node_id}["{node.label}"]' in visual.mermaid_source
        for node in visual.diagram_nodes
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
