"""Version the complete deterministic contract that accepts cached product truth."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
VISITOR_RENDER_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
)

_COMPONENT_FILES: dict[str, tuple[str, ...]] = {
    "classification_semantics": ("acceptance_contract.py",),
    "fact_schema": ("schema_v2.py",),
    "fact_eligibility": ("gating.py",),
    "evidence_polarity": ("policy_evidence.py", "interpretive_evidence.py"),
    "visitor_render_eligibility": ("render_views.py",),
}


class FactAcceptanceContractV1(BaseModel):
    """Hashable acceptance boundary for persisted facts and dependent lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    required_fields: tuple[str, ...]
    accepted_verification_states: tuple[str, ...]
    blocking_conflict_statuses: tuple[str, ...]
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
        digest.update((root / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_fact_acceptance_contract() -> FactAcceptanceContractV1:
    """Build the current contract from explicit rules and their implementation files."""

    root = Path(__file__).parent
    return FactAcceptanceContractV1(
        required_fields=README_TRUTH_FIELDS,
        accepted_verification_states=ACCEPTED_VERIFICATION_STATES,
        blocking_conflict_statuses=BLOCKING_CONFLICT_STATUSES,
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
    selected = [facts.selected_fact(field) for field in active_contract.required_fields]
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
    if any(
        (view := visitor_fact_render_view(facts, field)) is None or not view.phrases
        for field in active_contract.visitor_render_fields
    ):
        return "BLOCKED_MISSING_EVIDENCE"
    return "FACTS_READY"
