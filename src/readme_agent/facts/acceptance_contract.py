"""Version the complete deterministic contract that accepts cached product truth."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.gating import SurfaceFactRequirementV1, evaluate_surface_facts
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2

ProductTruthOutcome = Literal[
    "FACTS_READY",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
]

README_TRUTH_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "installation.verified_acquisition",
    "example.minimal",
    "product.license",
    "relationship.commercial_foss",
)
ACCEPTED_VERIFICATION_STATES = ("policy_approved", "verified")
BLOCKING_CONFLICT_STATUSES = ("unresolved",)
RECOLLECT_ON_COMPONENT_CHANGE = (
    "fact_schema",
    "fact_eligibility",
    "acquisition_truth",
    "drafting_and_example_selection",
    "evidence_polarity",
    "root_role_selection",
)
VISITOR_RENDER_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
)

_COMPONENT_FILES: dict[str, tuple[str, ...]] = {
    "acquisition_truth": (
        "acquisition.py",
        "acquisition_pins.py",
        "acquisition_schema.py",
        "example_verification_schema.py",
        "compiled_consumer.py",
        "compiled_consumer_schema.py",
        "java_example_verifier.py",
        "dotnet_example_verifier.py",
        "cpp_example_verifier.py",
        "go_example_verifier.py",
        "python_example_verifier.py",
        "typescript_example_verifier.py",
        "rust_example_verifier.py",
        "../ecosystems/foss_coordinate.py",
        "../ecosystems/registry_request.py",
        "../ecosystems/resolver.py",
    ),
    "classification_semantics": ("acceptance_contract.py",),
    "conflict_semantics": ("acceptance_contract.py", "resolution.py", "schema_v2.py"),
    "drafting_and_example_selection": (
        "../capabilities/draft_product_truth.py",
        "agentic_drafting.py",
        "example_quality.py",
        "problem_grounding.py",
        "repository_examples.py",
    ),
    "fact_schema": ("schema_v2.py",),
    "fact_eligibility": ("gating.py",),
    "evidence_polarity": (
        "evidence_polarity.py",
        "policy_evidence.py",
        "interpretive_evidence.py",
    ),
    "root_role_selection": (
        "root_role_schema.py",
        "root_role_evidence.py",
        "root_roles.py",
        "manifest_facts.py",
        "repository_ingestion.py",
    ),
    "visitor_render_eligibility": ("render_views.py",),
}


class FactAcceptanceContractV1(BaseModel):
    """Hashable acceptance boundary for persisted facts and dependent lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    required_fields: tuple[str, ...]
    accepted_verification_states: tuple[str, ...]
    blocking_conflict_statuses: tuple[str, ...]
    recollect_on_component_change: tuple[str, ...]
    visitor_render_fields: tuple[str, ...]
    component_hashes: dict[str, str]

    def canonical_hash(self) -> str:
        """Return the exact hash stored beside every accepted cached fact graph."""

        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _component_hash(root: Path, relative_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_path in relative_paths:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        with (root / relative_path).open("r", encoding="utf-8", newline=None) as source:
            normalized_source = source.read()
        digest.update(normalized_source.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def current_fact_acceptance_contract() -> FactAcceptanceContractV1:
    """Build the current contract from explicit rules and their implementation files."""

    root = Path(__file__).parent
    return FactAcceptanceContractV1(
        required_fields=README_TRUTH_FIELDS,
        accepted_verification_states=ACCEPTED_VERIFICATION_STATES,
        blocking_conflict_statuses=BLOCKING_CONFLICT_STATUSES,
        recollect_on_component_change=RECOLLECT_ON_COMPONENT_CHANGE,
        visitor_render_fields=VISITOR_RENDER_FIELDS,
        component_hashes={
            name: _component_hash(root, relative_paths)
            for name, relative_paths in sorted(_COMPONENT_FILES.items())
        },
    )


def classify_product_truth(
    facts: ProductFactsV2,
    contract: FactAcceptanceContractV1 | None = None,
) -> ProductTruthOutcome:
    """Classify the current graph without trusting a persisted terminal label."""

    active_contract = contract or current_fact_acceptance_contract()
    try:
        selected = [facts.selected_fact(field) for field in active_contract.required_fields]
    except KeyError:
        return "BLOCKED_MISSING_EVIDENCE"
    if any(
        fact.verification_state == "conflicting"
        or any(
            conflict.status in active_contract.blocking_conflict_statuses
            for conflict in fact.conflicts
        )
        for fact in selected
    ):
        return "BLOCKED_FACT_CONFLICT"
    if any(
        fact.verification_state not in active_contract.accepted_verification_states
        for fact in selected
    ):
        return "BLOCKED_MISSING_EVIDENCE"
    eligibility = evaluate_surface_facts(
        facts,
        [
            SurfaceFactRequirementV1(
                surface_id="readme",
                required_fields=list(active_contract.required_fields),
            )
        ],
    )[0]
    if not eligibility.eligible:
        return "BLOCKED_MISSING_EVIDENCE"
    if any(
        (view := visitor_fact_render_view(facts, field)) is None or not view.phrases
        for field in active_contract.visitor_render_fields
    ):
        return "BLOCKED_MISSING_EVIDENCE"
    return "FACTS_READY"
