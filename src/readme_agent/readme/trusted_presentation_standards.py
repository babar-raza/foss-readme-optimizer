"""Bind governed presentation additions to README-inherited trusted facts."""

from __future__ import annotations

import json
import re
from urllib.parse import quote

from readme_agent.facts.trusted_readme_extraction import (
    bind_configured_standards,
    configured_standard_addition,
)
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.links.allocation import resolve_link_budget
from readme_agent.links.catalog import lookup_verified_target
from readme_agent.links.runtime_context import load_runtime_link_inputs
from readme_agent.registry.loader import load_policy, require_listed

_URL = re.compile(r"https?://[^\s<>()\]]+", re.IGNORECASE)


def bind_trusted_presentation_standards(
    org_repo: str,
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
) -> TrustedReadmeFactGraphV1:
    """Attach only separately-attributed, policy-backed README standards."""

    entry = require_listed(org_repo)
    if entry.policy_profile is None:
        raise ValueError(f"{org_repo!r} has no policy_profile for trusted presentation")
    policy = load_policy(entry.policy_profile)
    config_source = f"config/policies/{entry.policy_profile}.yml"
    config_bytes = json.dumps(
        policy.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    license_name = policy.required_elements.license_mentioned.detected_license
    license_badge = (
        "![License: "
        f"{license_name}](https://img.shields.io/badge/License-"
        f"{quote(license_name, safe='')}-blue.svg)"
    )
    catalogs, allocation_policy = load_runtime_link_inputs(org_repo)
    if catalogs is None or allocation_policy is None:
        allowed_urls: list[str] = []
        surface_by_url: dict[str, str] = {}
    else:
        configured_targets = {
            policy.required_elements.products_org_link.url,
            policy.required_elements.products_org_link.family_url,
            policy.required_elements.products_com_link.url,
            policy.required_elements.products_com_link.family_url,
        }
        source_targets = set(_URL.findall(source_text))
        records = [
            record
            for url in sorted(configured_targets | source_targets)
            if (record := lookup_verified_target(catalogs, url)) is not None
        ]
        allowed_urls = sorted({record.url for record in records})
        surface_by_url = {record.url: record.surface for record in records}
    budget = resolve_link_budget(policy.link_allocation, source_text)
    additions = [
        configured_standard_addition(
            "readme.header",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={
                "repository_name": entry.repo_name,
                "family": entry.family,
                "platform": entry.platform,
            },
        ),
        configured_standard_addition(
            "readme.badges",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={"required_fragments": [license_badge]},
        ),
        configured_standard_addition(
            "readme.navigation",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={"required_labels": ["At a glance"]},
        ),
        configured_standard_addition(
            "readme.at_a_glance_mermaid",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={"heading": "At a glance", "diagram_kind": "flowchart"},
        ),
        configured_standard_addition(
            "readme.no_comments",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={
                "remove_html_comments": True,
                "remove_code_comments_and_docstrings": True,
            },
        ),
        configured_standard_addition(
            "readme.enterprise_edition_terminology",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={"required_term": "Enterprise Edition"},
        ),
        configured_standard_addition(
            "readme.contextual_links",
            configuration_source=config_source,
            configuration_bytes=config_bytes,
            parameters={
                "allowed_urls": allowed_urls,
                "max_total": budget.max_total,
                "domain_maxima": budget.domain_maxima,
                "surface_maxima": budget.surface_maxima,
                "surface_by_url": surface_by_url,
                "priority_hosts": ["products.aspose.org", "products.aspose.com"],
                "forbidden_sections": ["navigation", "at a glance"],
                "forbid_blockquotes": True,
            },
        ),
    ]
    return bind_configured_standards(graph, additions)
