"""Validate and normalize evidence-bounded README diagram roles."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import AgenticDiagramNodeV1
from readme_agent.readme.diagram_semantic_candidates import (
    bounded_diagram_label,
    diagram_role_identity,
    input_node_candidates,
    label_has_forbidden_role_semantics,
    meaningful_diagram_tokens,
    output_node_candidates,
    selected_verified_capability_nodes,
)

_ROLE_FACT_FIELDS = {
    "input": frozenset({"product.formats", "product.capabilities"}),
    "capability": frozenset({"product.capabilities", "product.problems_solved", "product.formats"}),
    "output": frozenset({"product.formats", "product.capabilities"}),
}


def _node_has_literal_fact_grounding(node: AgenticDiagramNodeV1, facts: ProductFactsV2) -> bool:
    label_tokens = meaningful_diagram_tokens(node.label)
    normalized_label = " ".join(node.label.casefold().split()).strip(" .,:;-")
    fact_tokens: set[str] = set()
    normalized_phrases: set[str] = set()
    for fact_id in node.supporting_fact_ids:
        field = facts.fact_by_id(fact_id).field
        view = visitor_fact_render_view(facts, field)
        if view is not None:
            for phrase in view.phrases:
                fact_tokens.update(meaningful_diagram_tokens(phrase))
                normalized_phrases.add(" ".join(phrase.casefold().split()).strip(" .,:;-"))
    if not label_tokens:
        # Generic endpoint nouns (for example, "document files") intentionally
        # have no semantic identity tokens. Accept them only when the complete
        # visitor label occurs verbatim in the cited accepted fact, never by a
        # fuzzy match that could invent an input or output role.
        return normalized_label in normalized_phrases
    return label_tokens <= fact_tokens


def _allowed_role_candidates(
    role: str,
    facts: ProductFactsV2,
) -> list[AgenticDiagramNodeV1]:
    if role == "input":
        return input_node_candidates(facts)
    if role == "output":
        return output_node_candidates(facts)
    return selected_verified_capability_nodes(facts)


def _node_semantic_error(node: AgenticDiagramNodeV1, facts: ProductFactsV2) -> str | None:
    try:
        cited_fields = sorted(
            {facts.fact_by_id(fact_id).field for fact_id in node.supporting_fact_ids}
        )
    except KeyError:
        return f"{node.role}:{node.label!r} cites an unknown fact"
    disallowed = [field for field in cited_fields if field not in _ROLE_FACT_FIELDS[node.role]]
    if disallowed:
        return f"{node.role}:{node.label!r} cites {disallowed}"
    if label_has_forbidden_role_semantics(node.label):
        return f"{node.role}:{node.label!r} describes infrastructure instead of product behavior"
    if node.role in {"input", "output"}:
        allowed = {
            diagram_role_identity(candidate.role, candidate.label)
            for candidate in _allowed_role_candidates(node.role, facts)
        }
        if diagram_role_identity(node.role, node.label) not in allowed:
            return (
                f"{node.role}:{node.label!r} is not an explicitly verified "
                f"{'consumed input' if node.role == 'input' else 'emitted result'}"
            )
    if not _node_has_literal_fact_grounding(node, facts):
        return f"{node.role}:{node.label!r} is not grounded in its cited fact text"
    return None


def _fallback_capability_nodes(facts: ProductFactsV2) -> list[AgenticDiagramNodeV1]:
    """Use one accepted action statement when capability facts are unavailable."""

    for field in ("product.problems_solved", "product.formats"):
        view = visitor_fact_render_view(facts, field)
        if view is None:
            continue
        for phrase in view.phrases:
            if phrase.strip() and not label_has_forbidden_role_semantics(phrase):
                return [
                    AgenticDiagramNodeV1(
                        role="capability",
                        label=bounded_diagram_label(phrase),
                        supporting_fact_ids=view.citation_fact_ids,
                    )
                ]
    return []


def _cross_role_errors(nodes: Iterable[AgenticDiagramNodeV1]) -> list[str]:
    """Reject capability labels reused as output artifacts."""

    capabilities = {
        frozenset(meaningful_diagram_tokens(node.label)): node.label
        for node in nodes
        if node.role == "capability"
    }
    errors: list[str] = []
    for output in (node for node in nodes if node.role == "output"):
        identity = frozenset(meaningful_diagram_tokens(output.label))
        if identity and identity in capabilities:
            errors.append(
                f"capability {capabilities[identity]!r} is duplicated as output {output.label!r}"
            )
    return errors


def evidence_scaled_role_minimums(
    facts: ProductFactsV2,
    base: dict[str, int],
) -> dict[str, int]:
    """Require input/output roles only when accepted evidence can populate them.

    Working-condition presentation: repositories without derivable endpoints
    ship a capabilities-only landscape instead of failing composition.
    """

    scaled = dict(base)
    if not input_node_candidates(facts):
        scaled["input"] = 0
    if not output_node_candidates(facts):
        scaled["output"] = 0
    if not selected_verified_capability_nodes(facts) and not _fallback_capability_nodes(facts):
        scaled["capability"] = 0
    return scaled


def normalize_diagram_role_nodes(
    nodes: Iterable[AgenticDiagramNodeV1],
    facts: ProductFactsV2,
    required_counts: dict[str, int],
    target_counts: dict[str, int] | None = None,
) -> list[AgenticDiagramNodeV1]:
    """Build stable roles from accepted evidence; accept only complete safe reorderings."""

    proposed = list(nodes)
    authoritative = [
        *input_node_candidates(facts),
        *(selected_verified_capability_nodes(facts) or _fallback_capability_nodes(facts)),
        *output_node_candidates(facts),
    ]
    normalized: list[AgenticDiagramNodeV1] = []
    for role in ("input", "capability", "output"):
        role_nodes = [node for node in authoritative if node.role == role]
        authoritative_by_identity = {
            diagram_role_identity(node.role, node.label): node for node in role_nodes
        }
        proposed_identities = [
            diagram_role_identity(node.role, node.label)
            for node in proposed
            if node.role == role
            and diagram_role_identity(node.role, node.label) in authoritative_by_identity
        ]
        if len(proposed_identities) == len(authoritative_by_identity) and len(
            set(proposed_identities)
        ) == len(authoritative_by_identity):
            role_nodes = [authoritative_by_identity[identity] for identity in proposed_identities]
        target = (target_counts or {}).get(role)
        if role != "capability" and target is not None and len(role_nodes) > target:
            # Presentation economy: inputs/outputs beyond the configured target
            # stay in the text sections; selected capabilities are never
            # trimmed because the header validator requires them complete.
            role_nodes = role_nodes[:target]
        normalized.extend(role_nodes)
        minimum = required_counts.get(role, 0)
        if len(role_nodes) < minimum:
            raise LLMError(
                f"verified diagram has {len(role_nodes)} {role} node(s); requires {minimum}"
            )
    cross_role = _cross_role_errors(normalized)
    if cross_role:
        raise LLMError("diagram semantic roles overlap: " + "; ".join(cross_role))
    return normalized


def diagram_role_phrase_guidance(facts: ProductFactsV2) -> dict[str, list[str]]:
    """Return exact role-approved vocabulary for optional editorial ordering."""

    return {
        "input": [node.label for node in input_node_candidates(facts)],
        "capability": [node.label for node in selected_verified_capability_nodes(facts)],
        "output": [node.label for node in output_node_candidates(facts)],
    }


def validate_diagram_role_fact_semantics(
    nodes: Iterable[AgenticDiagramNodeV1],
    facts: ProductFactsV2,
) -> None:
    """Reject role assignments that are not reproducible from accepted evidence."""

    materialized = list(nodes)
    invalid = [
        error for node in materialized if (error := _node_semantic_error(node, facts)) is not None
    ]
    invalid.extend(_cross_role_errors(materialized))
    if invalid:
        raise LLMError(
            "composition diagram assigns unsupported semantic roles: " + "; ".join(invalid)
        )


def diagram_semantic_contract_hash(facts: ProductFactsV2) -> str:
    """Return a stable hash of the authoritative semantic diagram vocabulary."""

    payload = {
        role: [node.model_dump(mode="json") for node in nodes]
        for role, nodes in (
            ("input", input_node_candidates(facts)),
            ("capability", selected_verified_capability_nodes(facts)),
            ("output", output_node_candidates(facts)),
        )
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
