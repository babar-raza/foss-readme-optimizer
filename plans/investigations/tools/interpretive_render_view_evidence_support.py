"""Build representative controls for interpretive visitor render views."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from readme_agent.facts.interpretive_evidence import (
    InterpretiveClaimV1,
    groundedness_fact_candidate,
)
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2


def _facts(representative_root: Path, ecosystem: str) -> ProductFactsV2:
    path = representative_root / ecosystem / "bundle/product-facts-v2.json"
    return ProductFactsV2.model_validate_json(path.read_text(encoding="utf-8"))


def _replace_selected(facts: ProductFactsV2, replacement: FactRecordV2) -> ProductFactsV2:
    records = [fact for fact in facts.facts if fact.field != replacement.field]
    records.append(replacement)
    selections = dict(facts.selected_fact_ids)
    selections[replacement.field] = replacement.fact_id
    return ProductFactsV2(
        org_repo=facts.org_repo,
        facts=records,
        selected_fact_ids=selections,
        package_root_roles=facts.package_root_roles,
    )


def build_interpretive_controls(representative_root: Path) -> dict[str, Any]:
    """Exercise real Java/TypeScript facts and hostile internal-value controls."""
    java = _facts(representative_root, "java")
    java_identity = visitor_fact_render_view(java, "product.identity")
    if java_identity is None:
        raise RuntimeError("Java identity has no visitor render view")

    typescript = _facts(representative_root, "typescript")
    identity = typescript.selected_fact("product.identity")
    audience = groundedness_fact_candidate(
        "product.audience",
        [
            InterpretiveClaimV1(
                claim_id="typescript-audience",
                text="Developers using TypeScript.",
                supporting_fact_ids=[identity.fact_id],
            )
        ],
        typescript,
        source_revision=identity.source.source_revision,
        observed_at=None,
    )
    typescript = _replace_selected(typescript, audience)
    audience_view = visitor_fact_render_view(typescript, "product.audience")

    formats = typescript.selected_fact("product.formats")
    format_values = formats.value if isinstance(formats.value, list) else []
    problem = groundedness_fact_candidate(
        "product.problems_solved",
        [
            InterpretiveClaimV1(
                claim_id="typescript-problem",
                text=str(format_values[0]),
                supporting_fact_ids=[formats.fact_id],
            )
        ],
        typescript,
        source_revision=formats.source.source_revision,
        observed_at=None,
    )
    typescript = _replace_selected(typescript, problem)
    problem_view = visitor_fact_render_view(typescript, "product.problems_solved")

    capabilities = java.selected_fact("product.capabilities")
    unsafe_capabilities = capabilities.model_copy(
        update={"value": ["scene_graph", "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"]}
    )
    unsafe_java = java.model_copy(
        update={
            "facts": [
                unsafe_capabilities if fact.fact_id == capabilities.fact_id else fact
                for fact in java.facts
            ]
        }
    )
    problems = java.selected_fact("product.problems_solved")
    nested_problems = problems.model_copy(
        update={"value": {"manifest_key": {"nested_value": "internal"}}}
    )
    nested_java = java.model_copy(
        update={
            "facts": [
                nested_problems if fact.fact_id == problems.fact_id else fact for fact in java.facts
            ]
        }
    )
    return {
        "java_identity": {
            "source_value": java.selected_fact("product.identity").value,
            "render_view": java_identity.model_dump(mode="json"),
        },
        "typescript_audience": {
            "grounded_fact": audience.model_dump(mode="json"),
            "render_view": audience_view.model_dump(mode="json") if audience_view else None,
        },
        "typescript_problem": {
            "grounded_fact": problem.model_dump(mode="json"),
            "render_view": problem_view.model_dump(mode="json") if problem_view else None,
        },
        "negative_controls": {
            "internal_tokens_have_no_view": (
                visitor_fact_render_view(unsafe_java, "product.capabilities") is None
            ),
            "nested_values_are_not_flattened": (
                visitor_fact_render_view(nested_java, "product.problems_solved") is None
            ),
            "identity_omits_repository_slug": (
                "aspose-cells-foss" not in " ".join(java_identity.phrases).casefold()
            ),
            "identity_omits_manifest_keys": (
                "manifest_names" not in " ".join(java_identity.phrases)
            ),
        },
    }
