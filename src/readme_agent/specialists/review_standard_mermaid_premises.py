"""Mechanically reconcile Mermaid review premises with the configured visual contract."""

from __future__ import annotations

import re


def _mermaid_source(candidate_text: str) -> str:
    blocks = re.findall(r"(?ms)^```mermaid[ \t]*\r?\n(.*?)^```[ \t]*$", candidate_text)
    return blocks[0] if len(blocks) == 1 else ""


def _mermaid_role_count(source: str, role: str) -> int:
    prefix = {"input": "I", "capability": "C", "output": "O"}[role]
    return len(
        re.findall(
            rf'(?m)^[ \t]*(?:{re.escape(role)}_\d+|{prefix}\d+)\["',
            source,
        )
    )


def _has_directional_connector(source: str) -> bool:
    return bool(re.search(r"(?:-->|<-->|==>|-.->)", source))


def _has_rendered_internal_capability_connector(source: str) -> bool:
    return bool(
        re.search(
            r"(?m)^\s*C\d+\s+(?:---|-->|<-->|==>|-.->)\s+C\d+\s*$",
            source,
        )
    )


def validate_mermaid_standard_premise(
    *, finding_id: str, premise: str, candidate_text: str, standard: dict
) -> list[str]:
    """Return contradictions decidable from the candidate Mermaid and its exact standard."""

    errors: list[str] = []
    mermaid = _mermaid_source(candidate_text)
    claims_configured_group_label_is_wrong = "core capabilities" in premise and any(
        phrase in premise
        for phrase in ("group label", "internal group", "rename 'core", 'rename "core')
    )
    configured_group_label = str(standard.get("capability_group_label") or "")
    if (
        claims_configured_group_label_is_wrong
        and configured_group_label
        and mermaid
        and re.search(
            rf'(?m)^\s*subgraph\s+CORE\["{re.escape(configured_group_label)}"\]\s*$', mermaid
        )
    ):
        errors.append(
            f"{finding_id}:Mermaid-group-label premise contradicts configured presentation"
        )
    claims_internal_direction_is_workflow = "direction tb" in premise and any(
        term in premise for term in ("workflow", "ordered", "remove")
    )
    if (
        claims_internal_direction_is_workflow
        and standard.get("internal_direction_directives") == "layout_only"
        and mermaid
        and re.search(r"(?m)^\s*direction\s+TB\s*$", mermaid)
    ):
        errors.append(
            f"{finding_id}:Mermaid-layout-direction premise contradicts configured presentation"
        )
    claims_styling_forbidden = any(
        term in premise
        for term in ("classdef", "style directive", "styling directive", "class directive")
    ) and any(
        term in premise
        for term in ("not permitted", "forbidden", "remove all", "not align", "may not align")
    )
    if (
        claims_styling_forbidden
        and standard.get("styling_directives") == "allowed"
        and mermaid
        and re.search(r"(?m)^\s*(?:classDef|class|style)\s+", mermaid)
    ):
        errors.append(f"{finding_id}:Mermaid-style premise contradicts configured presentation")
    claims_allowed_syntax_is_forbidden = (
        "html line break" in premise or "<br/>" in premise or "linkstyle" in premise
    ) and any(term in premise for term in ("not aligned", "not permitted", "remove", "replace"))
    if (
        claims_allowed_syntax_is_forbidden
        and standard.get("styling_directives") == "allowed"
        and mermaid
        and ("<br/>" in mermaid or re.search(r"(?m)^\s*linkStyle\s+", mermaid))
    ):
        errors.append(f"{finding_id}:Mermaid-syntax premise contradicts configured rendered visual")
    claims_directional = "directional arrow" in premise or "directional workflow" in premise
    if (
        claims_directional
        and standard.get("directional_workflow") is False
        and mermaid
        and not _has_directional_connector(mermaid)
    ):
        errors.append(f"{finding_id}:Mermaid-direction premise contradicts parsed connectors")
    if (
        claims_directional
        and standard.get("directional_workflow") is True
        and mermaid
        and _has_directional_connector(mermaid)
    ):
        errors.append(
            f"{finding_id}:Mermaid-direction premise contradicts configured outer workflow"
        )
    claims_product_core_edge_should_be_undirected = (
        "undirected connector" in premise and "product" in premise and "core" in premise
    )
    if (
        claims_product_core_edge_should_be_undirected
        and standard.get("directional_workflow") is True
        and standard.get("product_to_capabilities_edges") == 1
        and mermaid
        and re.search(r"(?m)^\s*PRODUCT\s+-->\s+CORE\s*$", mermaid)
    ):
        errors.append(
            f"{finding_id}:Mermaid product-to-capabilities premise contradicts configured topology"
        )
    claims_core_output_edge_should_be_undirected = (
        ("undirected connector" in premise or "~~~" in premise)
        and "core" in premise
        and "output" in premise
        and "individual output" not in premise
    )
    if (
        claims_core_output_edge_should_be_undirected
        and standard.get("directional_workflow") is True
        and standard.get("capabilities_to_outputs_edges") == 1
        and mermaid
        and re.search(r"(?m)^\s*CORE\s+-->\s+O1\s*$", mermaid)
    ):
        errors.append(
            f"{finding_id}:Mermaid capabilities-to-outputs premise contradicts configured topology"
        )
    claims_internal_capability_connectors = "capabilit" in premise and any(
        phrase in premise
        for phrase in ("internal capability", "bidirectional tilde", "tildes between")
    )
    if (
        claims_internal_capability_connectors
        and standard.get("rendered_internal_capability_connectors") == "none"
        and standard.get("invisible_layout_constraints") == "allowed"
        and not _has_rendered_internal_capability_connector(mermaid)
    ):
        errors.append(
            f"{finding_id}:internal-connector premise contradicts configured invisible layout "
            "constraints"
        )
    claims_target_outputs_are_required = bool(
        re.search(r"\btarget[_ -]?outputs\b", premise)
    ) and any(
        term in premise
        for term in (
            "requires",
            "required",
            "requirement",
            "expects",
            "expected",
            "noncompliant",
            "incomplete",
            "specifies",
            "missing",
        )
    )
    if (
        claims_target_outputs_are_required
        and standard.get("output_coverage") == "all_selected_verified"
        and _mermaid_role_count(mermaid, "output") >= int(standard.get("minimum_outputs", 1))
    ):
        errors.append(
            f"{finding_id}:Mermaid target-output premise contradicts verified-coverage contract"
        )
    claims_all_input_edges_are_required = "input arrow" in premise and any(
        term in premise for term in ("minimum_inputs", "missing", "required", "violat")
    )
    if (
        claims_all_input_edges_are_required
        and standard.get("input_to_product_edges") == 1
        and _mermaid_role_count(mermaid, "input") >= int(standard.get("minimum_inputs", 1))
        and mermaid
        and re.search(r"(?m)^\s*I1\s+-->\s+PRODUCT\s*$", mermaid)
    ):
        errors.append(
            f"{finding_id}:Mermaid input-edge premise contradicts configured grouped topology"
        )
    claims_group_output_edge_required = (
        "individual output" in premise
        and "output" in premise
        and any(term in premise for term in ("group", "topology", "connect"))
    ) or ("core --> o1" in premise and "outputs" in premise)
    if (
        claims_group_output_edge_required
        and standard.get("directional_workflow") is True
        and standard.get("capabilities_to_outputs_edges") == 1
        and mermaid
        and re.search(r"(?m)^\s*CORE\s+-->\s+O1\s*$", mermaid)
    ):
        errors.append(
            f"{finding_id}:Mermaid capabilities-to-outputs premise contradicts configured "
            "grouped topology"
        )
    claims_missing_roles = (
        any(phrase in premise for phrase in ("does not show", "fewer than"))
        and "capabilit" in premise
        and ("input" in premise or "output" in premise)
    )
    if mermaid and claims_missing_roles:
        role_counts_satisfy = (
            _mermaid_role_count(mermaid, "input") >= int(standard.get("minimum_inputs", 1))
            and _mermaid_role_count(mermaid, "capability")
            >= int(standard.get("minimum_capabilities", 1))
            and _mermaid_role_count(mermaid, "output") >= int(standard.get("minimum_outputs", 1))
        )
        if role_counts_satisfy:
            errors.append(f"{finding_id}:Mermaid-role-count premise contradicts parsed candidate")
    return errors


__all__ = ["validate_mermaid_standard_premise"]
