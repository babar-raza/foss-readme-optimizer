"""Build representative controls for interpretive visitor render views."""

from __future__ import annotations

import hashlib
import json
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_live_python_regression_control(
    bundle_root: Path,
    supervisor_manifest_path: Path,
) -> dict[str, Any]:
    """Prove the repaired live run reaches FACTS_READY with grounded visitor views."""
    facts_path = bundle_root / "facts/product-facts.json"
    bundle_manifest_path = bundle_root / "manifest.json"
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    supervisor_manifest = json.loads(supervisor_manifest_path.read_text(encoding="utf-8"))

    audience = facts.selected_fact("product.audience")
    problem = facts.selected_fact("product.problems_solved")
    audience_support = [facts.fact_by_id(fact_id) for fact_id in audience.supporting_fact_ids]
    problem_support = [facts.fact_by_id(fact_id) for fact_id in problem.supporting_fact_ids]
    audience_view = visitor_fact_render_view(facts, "product.audience")
    problem_view = visitor_fact_render_view(facts, "product.problems_solved")
    checkpoints = supervisor_manifest.get("checkpoints", [])
    latest_run_id = supervisor_manifest.get("run_id")
    latest_checkpoints = [
        checkpoint for checkpoint in checkpoints if checkpoint.get("run_id") == latest_run_id
    ]
    latest_stages = [checkpoint.get("stage") for checkpoint in latest_checkpoints]

    checks = {
        "product_facts_v2_valid": True,
        "bundle_reaches_facts_ready": bundle_manifest.get("lifecycle_status") == "FACTS_READY",
        "audience_verified_with_eligible_support": (
            audience.verification_state == "verified"
            and bool(audience.supporting_fact_ids)
            and all(
                supporting is not None and supporting.verification_state == "verified"
                for supporting in audience_support
            )
        ),
        "problem_verified_with_eligible_support": (
            problem.verification_state == "verified"
            and bool(problem.supporting_fact_ids)
            and all(
                supporting is not None and supporting.verification_state == "verified"
                for supporting in problem_support
            )
        ),
        "visitor_views_are_nonempty": (
            audience_view is not None
            and bool(audience_view.phrases)
            and problem_view is not None
            and bool(problem_view.phrases)
        ),
        "stage_ceiling_preserved": (
            bundle_manifest.get("completed_stages") == ["SNAPSHOTTED", "PROFILED", "FACTS_READY"]
            and "final_acceptance" in latest_stages
            and not {
                "candidate_generated",
                "deterministic_validated",
                "agent_reviewing",
                "effect_requested",
            }.intersection(latest_stages)
        ),
        "verifier_and_effects_not_run": (
            supervisor_manifest.get("verifier", {}).get("status") == "not_run"
            and supervisor_manifest.get("effects") == []
        ),
        "exact_two_call_accounting": (
            bundle_manifest.get("llm_accounting_status") == "EXACT"
            and supervisor_manifest.get("llm_accounting_status") == "EXACT"
            and supervisor_manifest.get("llm_call_count") == 2
            and supervisor_manifest.get("llm_calls_by_job") == {"draft_product_truth": 2}
        ),
    }
    return {
        "repository": facts.org_repo,
        "source_revision": bundle_manifest.get("source_revision"),
        "lifecycle_status": bundle_manifest.get("lifecycle_status"),
        "facts_sha256": _sha256(facts_path),
        "bundle_manifest_sha256": _sha256(bundle_manifest_path),
        "supervisor_manifest_sha256": _sha256(supervisor_manifest_path),
        "audience": {
            "fact_id": audience.fact_id,
            "verification_state": audience.verification_state,
            "supporting_fact_ids": audience.supporting_fact_ids,
            "render_view": audience_view.model_dump(mode="json") if audience_view else None,
        },
        "problem": {
            "fact_id": problem.fact_id,
            "verification_state": problem.verification_state,
            "supporting_fact_ids": problem.supporting_fact_ids,
            "render_view": problem_view.model_dump(mode="json") if problem_view else None,
        },
        "latest_checkpoint_stages": latest_stages,
        "checks": checks,
    }
