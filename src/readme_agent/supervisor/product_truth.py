"""Prepare one verified product-fact graph for a supervised local-POC run."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import README_PRESENTATION
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import README_DRAFTABLE_PRODUCT_FIELDS, ProductFactsV2
from readme_agent.llm import prompt_registry
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV1, ReadmePocStatusV2
from readme_agent.state.readme_poc_lifecycle import record_product_facts_outcome
from readme_agent.supervisor.local_poc_evidence import write_local_poc_product_facts

ResolutionSource = Literal["repository_and_policy", "agent_draft", "durable_revision_cache"]

_DRAFTABLE_ECOSYSTEMS = frozenset({"java", "net", "python", "typescript", "go", "cpp", "rust"})
_README_TRUTH_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "installation.verified_acquisition",
    "example.minimal",
    "product.license",
    "relationship.commercial_foss",
)
_CACHEABLE_LIFECYCLE_STATES = frozenset(
    {
        "FACTS_READY",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
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
)


class PreparedProductTruthV1(BaseModel):
    """Run-scoped fact graph plus the durable boundary it reached."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    facts: ProductFactsV2
    findings: list[dict] = Field(default_factory=list)
    proposed_product_truth: dict | None = None
    resolution_source: ResolutionSource
    lifecycle_status: ReadmePocStatusV2
    bundle_dir: str


def classify_product_truth(facts: ProductFactsV2) -> ReadmePocStatusV2:
    """Classify the current graph without trusting a persisted terminal label."""

    selected = [facts.selected_fact(field) for field in _README_TRUTH_FIELDS]
    if any(fact.verification_state == "conflicting" for fact in selected):
        return "BLOCKED_FACT_CONFLICT"
    if any(fact.verification_state not in {"verified", "policy_approved"} for fact in selected):
        return "BLOCKED_MISSING_EVIDENCE"
    return "FACTS_READY"


def _facts_need_drafting(facts: ProductFactsV2) -> bool:
    return any(
        facts.selected_fact(field).verification_state not in {"verified", "policy_approved"}
        or facts.selected_fact(field).has_unresolved_conflict
        for field in README_DRAFTABLE_PRODUCT_FIELDS
    )


def load_prepared_product_truth(
    org_repo: str,
    state_backend: StateBackend,
    source_revision: str,
) -> PreparedProductTruthV1 | None:
    """Load the exact supervisor-persisted graph without recollecting it."""
    state = state_backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if (
        lifecycle is None
        or isinstance(lifecycle, ReadmePocLifecycleStateV1)
        or lifecycle.source_revision != source_revision
        or lifecycle.facts_hash is None
        or lifecycle.status not in _CACHEABLE_LIFECYCLE_STATES
    ):
        return None

    org, repo = org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, source_revision)
    facts_path = bundle_dir / "facts" / "product-facts.json"
    findings_path = bundle_dir / "facts" / "findings.json"
    proposal_path = bundle_dir / "facts" / "proposed-product-truth.json"
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("local_verification_contract_hash") != local_verification_contract_hash():
        return None
    if not facts_path.is_file():
        raise RuntimeError(
            "durable product-facts evidence is missing for "
            f"{org_repo}@{source_revision}: {facts_path}"
        )
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    if facts.org_repo != org_repo:
        raise RuntimeError(
            "durable product-facts evidence belongs to a different repository: "
            f"expected {org_repo}, found {facts.org_repo}"
        )
    if facts.canonical_hash() != lifecycle.facts_hash:
        raise RuntimeError(
            "durable product-facts evidence hash does not match lifecycle state for "
            f"{org_repo}@{source_revision}"
        )
    identity_revision = facts.selected_fact("product.identity").source.source_revision
    if identity_revision is not None and identity_revision != source_revision:
        raise RuntimeError(
            "durable product-facts evidence revision does not match the repository snapshot: "
            f"expected {source_revision}, found {identity_revision}"
        )
    findings = (
        json.loads(findings_path.read_text(encoding="utf-8")) if findings_path.is_file() else []
    )
    proposed_product_truth = (
        json.loads(proposal_path.read_text(encoding="utf-8")) if proposal_path.is_file() else None
    )
    if proposed_product_truth is not None and lifecycle.prompt_hash != prompt_registry.prompt_hash(
        "draft_product_truth"
    ):
        return None
    return PreparedProductTruthV1(
        facts=facts,
        findings=findings,
        proposed_product_truth=proposed_product_truth,
        resolution_source="durable_revision_cache",
        lifecycle_status=lifecycle.status,
        bundle_dir=str(bundle_dir),
    )


def _unsupported_drafting_finding(org_repo: str, ecosystem: str | None) -> dict:
    return {
        "finding_id": "product-truth-drafting-ecosystem-unsupported",
        "classification": "BLOCKED_MISSING_EVIDENCE",
        "blocked_category": "agent_fixable",
        "org_repo": org_repo,
        "ecosystem": ecosystem,
        "detail": (
            "The typed minimal-example drafting contract does not yet support this ecosystem; "
            "verified mechanical facts remain available, but dependent README claims stay blocked."
        ),
        "required_action": (
            "Add a typed minimal-example contract and isolated verifier for this ecosystem, then "
            "rerun product-truth preparation."
        ),
    }


def prepare_local_product_truth(
    org_repo: str,
    snapshot: RepositorySnapshotV1,
    state_backend: StateBackend,
    *,
    client=None,
) -> PreparedProductTruthV1:
    """Resolve, optionally draft, persist, and durably classify one fact graph."""
    cached = load_prepared_product_truth(
        org_repo,
        state_backend,
        snapshot.source_revision,
    )
    if cached is not None:
        return cached

    base_result = collect_product_facts(org_repo)
    facts = ProductFactsV2.model_validate(base_result["product_facts_v2"])
    entry = require_listed(org_repo)

    findings: list[dict] = []
    proposed_product_truth: dict | None = None
    resolution_source: ResolutionSource = "repository_and_policy"
    prompt_hash: str | None = None

    if _facts_need_drafting(facts):
        if entry.ecosystem not in _DRAFTABLE_ECOSYSTEMS:
            findings.append(_unsupported_drafting_finding(org_repo, entry.ecosystem))
        else:
            dispatch = dispatch_tool_call(
                {
                    "id": f"product-truth:{org_repo}",
                    "function": {
                        "name": "draft_product_truth",
                        "arguments": json.dumps({"org_repo": org_repo}),
                    },
                },
                {"read_only_local", "read_only_network"},
                caller_domain=README_PRESENTATION,
                extra_kwargs={
                    "client": client,
                    "repository_snapshot": snapshot,
                    "base_facts": facts,
                },
                state_backend=state_backend,
            )
            if dispatch.outcome != "executed" or dispatch.result is None:
                raise RuntimeError(
                    "draft_product_truth dispatch failed: "
                    f"{dispatch.outcome}: {dispatch.error or dispatch.gap}"
                )
            facts = ProductFactsV2.model_validate(dispatch.result["product_facts_v2"])
            findings.extend(dispatch.result.get("findings", []))
            proposed_product_truth = dispatch.result["proposed_product_truth"]
            resolution_source = "agent_draft"
            prompt_hash = prompt_registry.prompt_hash("draft_product_truth")

    lifecycle_status = classify_product_truth(facts)
    bundle_dir = write_local_poc_product_facts(
        snapshot,
        facts,
        findings=findings,
        resolution_source=resolution_source,
        proposed_product_truth=proposed_product_truth,
        lifecycle_status=lifecycle_status,
        prompt_hash=prompt_hash,
        local_verification_contract_hash=local_verification_contract_hash(),
    )
    record_product_facts_outcome(
        state_backend,
        org_repo,
        source_revision=snapshot.source_revision,
        facts_hash=facts.canonical_hash(),
        outcome=lifecycle_status,
        evidence_refs=[
            str(bundle_dir / "facts" / "product-facts.json"),
            str(bundle_dir / "facts" / "provenance.json"),
            str(bundle_dir / "facts" / "conflicts.json"),
        ],
        prompt_hash=prompt_hash,
    )
    return PreparedProductTruthV1(
        facts=facts,
        findings=findings,
        proposed_product_truth=proposed_product_truth,
        resolution_source=resolution_source,
        lifecycle_status=lifecycle_status,
        bundle_dir=str(bundle_dir),
    )
