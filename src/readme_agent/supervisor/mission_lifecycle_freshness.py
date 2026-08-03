"""Evaluate persisted fact boundaries against current truth contracts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.acceptance_contract import (
    FactAcceptanceContractV1,
    classify_product_truth,
    current_fact_acceptance_contract,
    fact_contract_change_requires_recollection,
)
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm import prompt_registry
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.mission_goal_schema import MissionLifecycleBoundary
from readme_agent.state.schema import RunStateV1

REACHED_STATUSES: dict[MissionLifecycleBoundary, frozenset[str]] = {
    "FACTS_READY": frozenset(
        {
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATION_FAILED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "REPAIRING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "CANDIDATE_GENERATED": frozenset(
        {
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATION_FAILED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "REPAIRING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "DETERMINISTIC_VALIDATED": frozenset(
        {
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "AGENT_APPROVED": frozenset(
        {
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "NO_OP_PROVEN": frozenset(
        {
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        }
    ),
    "HUMAN_ACCEPTED": frozenset({"HUMAN_ACCEPTED", "PR_ELIGIBLE", "PR_PROOF_COMPLETE"}),
    "MISSION_CLOSED": frozenset(),
}
ORDERED_BOUNDARIES: tuple[MissionLifecycleBoundary, ...] = (
    "FACTS_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
    "HUMAN_ACCEPTED",
)
ACCEPTANCE_BOUNDARIES: tuple[MissionLifecycleBoundary, ...] = (
    "AGENT_APPROVED",
    "NO_OP_PROVEN",
    "HUMAN_ACCEPTED",
)
TRUSTED_REACHED_STATUSES: dict[str, frozenset[str]] = {
    "trusted_facts_extracted": frozenset(
        {
            "TRUSTED_FACTS_EXTRACTED",
            "TRUSTED_PLAN_READY",
            "TRUSTED_CANDIDATE_GENERATED",
            "TRUSTED_DETERMINISTIC_VALIDATED",
            "TRUSTED_REVIEWING",
            "TRUSTED_REVIEW_REJECTED",
            "TRUSTED_REPAIRING",
            "TRUSTED_TRANSFORM_APPROVED",
            "TRUSTED_NO_OP_PROVEN",
            "TRUSTED_PR_ELIGIBLE",
            "TRUSTED_PR_OPEN",
        }
    ),
    "trusted_candidate_generated": frozenset(
        {
            "TRUSTED_CANDIDATE_GENERATED",
            "TRUSTED_DETERMINISTIC_VALIDATED",
            "TRUSTED_REVIEWING",
            "TRUSTED_REVIEW_REJECTED",
            "TRUSTED_REPAIRING",
            "TRUSTED_TRANSFORM_APPROVED",
            "TRUSTED_NO_OP_PROVEN",
            "TRUSTED_PR_ELIGIBLE",
            "TRUSTED_PR_OPEN",
        }
    ),
    "trusted_transform_approved": frozenset(
        {
            "TRUSTED_TRANSFORM_APPROVED",
            "TRUSTED_NO_OP_PROVEN",
            "TRUSTED_PR_ELIGIBLE",
            "TRUSTED_PR_OPEN",
        }
    ),
    "trusted_no_op_proven": frozenset(
        {"TRUSTED_NO_OP_PROVEN", "TRUSTED_PR_ELIGIBLE", "TRUSTED_PR_OPEN"}
    ),
    "trusted_pr_open": frozenset({"TRUSTED_PR_OPEN"}),
}


class LifecycleFactFreshnessDecisionV1(BaseModel):
    """Read-only decision proving whether a fact boundary remains current."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reusable: bool
    mismatch_reasons: list[str] = Field(default_factory=list)


def _load_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def evaluate_lifecycle_fact_freshness(
    state: RunStateV1 | None,
    bundle_dir: Path,
    *,
    current_contract: FactAcceptanceContractV1 | None = None,
    current_local_verification_hash: str | None = None,
    ecosystem: str | None = None,
    family: str | None = None,
) -> LifecycleFactFreshnessDecisionV1:
    """Fail closed unless persisted facts still satisfy the public truth contract."""

    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        return LifecycleFactFreshnessDecisionV1(
            reusable=False,
            mismatch_reasons=["repository_verified_v2_lifecycle_missing"],
        )

    reasons: list[str] = []
    if lifecycle.content_assurance != "repository_verified":
        reasons.append("content_assurance_not_repository_verified")
    if lifecycle.source_revision is None:
        reasons.append("source_revision_missing")
    if lifecycle.facts_hash is None:
        reasons.append("facts_hash_missing")

    contract = current_contract or current_fact_acceptance_contract(ecosystem, family)
    contract_hash = contract.canonical_hash()
    verification_hash = current_local_verification_hash or local_verification_contract_hash(
        ecosystem
    )
    contract_is_current = (
        lifecycle.fact_acceptance_contract_hash == contract_hash
        and lifecycle.fact_acceptance_component_hashes == contract.component_hashes
    )
    if not contract_is_current and fact_contract_change_requires_recollection(
        lifecycle.fact_acceptance_component_hashes,
        contract,
    ):
        reasons.append("fact_acceptance_recollection_component_changed")

    manifest = _load_json(bundle_dir / "manifest.json")
    if manifest is None:
        reasons.append("manifest_missing_or_invalid")
    else:
        expected_manifest = {
            "org_repo": state.org_repo if state is not None else None,
            "source_revision": lifecycle.source_revision,
            "facts_hash": lifecycle.facts_hash,
            "content_assurance": "repository_verified",
            "fact_acceptance_contract_hash": contract_hash,
            "fact_acceptance_component_hashes": contract.component_hashes,
            "local_verification_contract_hash": verification_hash,
        }
        for field, expected in expected_manifest.items():
            if field in {"fact_acceptance_contract_hash", "fact_acceptance_component_hashes"}:
                continue
            actual = manifest.get(field)
            if actual != expected:
                reasons.append(f"manifest_{field}_mismatch")

    if (bundle_dir / "facts" / "proposed-product-truth.json").is_file() and (
        lifecycle.prompt_hash != prompt_registry.prompt_hash("draft_product_truth")
    ):
        reasons.append("draft_product_truth_prompt_hash_changed")

    facts_payload = _load_json(bundle_dir / "facts" / "product-facts.json")
    if facts_payload is None:
        reasons.append("product_truth_missing_or_invalid")
    else:
        try:
            facts = ProductFactsV2.model_validate(facts_payload)
        except ValueError:
            reasons.append("product_truth_missing_or_invalid")
        else:
            if state is not None and facts.org_repo != state.org_repo:
                reasons.append("product_truth_repository_mismatch")
            if lifecycle.facts_hash is not None and facts.canonical_hash() != lifecycle.facts_hash:
                reasons.append("product_truth_hash_mismatch")
            if classify_product_truth(facts, contract) != "FACTS_READY":
                reasons.append("product_truth_not_facts_ready")
            try:
                identity_revision = facts.selected_fact("product.identity").source.source_revision
            except KeyError:
                identity_revision = None
            if (
                identity_revision is not None
                and lifecycle.source_revision is not None
                and identity_revision != lifecycle.source_revision
            ):
                reasons.append("product_truth_source_revision_mismatch")

    mismatch_reasons = sorted(set(reasons))
    return LifecycleFactFreshnessDecisionV1(
        reusable=not mismatch_reasons,
        mismatch_reasons=mismatch_reasons,
    )
