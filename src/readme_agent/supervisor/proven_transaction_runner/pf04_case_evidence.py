"""Validate and hash the current PF04 external-fact replay receipts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.external_fact_block_adapters import (
    ExternalFactResolutionDecisionV1,
    resolve_selected_external_fact_blocks,
)
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.supervisor.proven_transaction_runner.contracts import canonical_sha256


class ExternalFactReplayCaseV1(BaseModel):
    """One immutable real-repository receipt selected for PF04 replay."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    expected_surfaces: tuple[str, ...] = Field(min_length=1)


class LoadedExternalFactReplayCaseV1(BaseModel):
    """One current-contract bundle with persisted resolver decisions."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    case: ExternalFactReplayCaseV1
    bundle_dir: Path
    snapshot: RepositorySnapshotV1
    facts: ProductFactsV2
    manifest: dict
    persisted_decisions: tuple[ExternalFactResolutionDecisionV1, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_persisted_decisions(
    case: ExternalFactReplayCaseV1,
    findings_path: Path,
) -> tuple[ExternalFactResolutionDecisionV1, ...]:
    raw = json.loads(findings_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"PF04 findings must be a list for {case.org_repo}")
    decisions = tuple(
        ExternalFactResolutionDecisionV1.model_validate(finding["external_fact_resolution"])
        for finding in raw
        if isinstance(finding, dict) and finding.get("external_fact_resolution") is not None
    )
    actual = tuple(sorted(decision.block.fact_surface for decision in decisions))
    expected = tuple(sorted(case.expected_surfaces))
    if actual != expected:
        raise ValueError(
            f"PF04 persisted external decisions drifted for {case.org_repo}: "
            f"expected {expected}, found {actual}"
        )
    if any(
        decision.block.org_repo != case.org_repo
        or decision.block.source_revision != case.source_revision
        for decision in decisions
    ):
        raise ValueError(f"PF04 persisted decision identity mismatch for {case.org_repo}")
    return decisions


def require_current_fact_receipt(case: ExternalFactReplayCaseV1, manifest: dict) -> None:
    """Reject a fact receipt that is stale against any current acceptance dependency."""

    entry = require_listed(case.org_repo)
    contract = current_fact_acceptance_contract(
        entry.ecosystem,
        getattr(entry, "family", None),
    )
    required = {
        "org_repo": case.org_repo,
        "source_revision": case.source_revision,
        "fact_acceptance_contract_hash": contract.canonical_hash(),
        "fact_acceptance_component_hashes": contract.component_hashes,
        "local_verification_contract_hash": local_verification_contract_hash(entry.ecosystem),
        "lifecycle_status": "BLOCKED_MISSING_EVIDENCE",
    }
    mismatches = [key for key, value in required.items() if manifest.get(key) != value]
    if mismatches:
        raise ValueError(
            f"PF04 fact receipt is stale for {case.org_repo}: {', '.join(sorted(mismatches))}"
        )


def load_pf04_case(
    case: ExternalFactReplayCaseV1,
    runs_root: Path,
) -> LoadedExternalFactReplayCaseV1:
    """Load one real receipt only after its identity and contracts are current."""

    org, repo = case.org_repo.split("/", maxsplit=1)
    bundle = runs_root / "readme-poc" / f"{org}__{repo}" / case.source_revision
    snapshot_path = bundle / "source" / "revision.json"
    facts_path = bundle / "facts" / "product-facts.json"
    findings_path = bundle / "facts" / "findings.json"
    manifest_path = bundle / "manifest.json"
    required_paths = (snapshot_path, facts_path, findings_path, manifest_path)
    if any(not path.is_file() for path in required_paths):
        raise FileNotFoundError(f"PF04 source/fact evidence is missing for {case.org_repo}")
    snapshot = RepositorySnapshotV1.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"PF04 manifest must be an object for {case.org_repo}")
    if snapshot.org_repo != case.org_repo or facts.org_repo != case.org_repo:
        raise ValueError(f"PF04 evidence identity mismatch for {case.org_repo}")
    if snapshot.source_revision != case.source_revision:
        raise ValueError(f"PF04 evidence revision mismatch for {case.org_repo}")
    require_current_fact_receipt(case, manifest)
    return LoadedExternalFactReplayCaseV1(
        case=case,
        bundle_dir=bundle,
        snapshot=snapshot,
        facts=facts,
        manifest=manifest,
        persisted_decisions=_load_persisted_decisions(case, findings_path),
    )


def resolve_current_case(
    loaded: LoadedExternalFactReplayCaseV1,
) -> tuple[ExternalFactResolutionDecisionV1, ...]:
    """Recompute and match the resolver output against its persisted receipt."""

    entry = require_listed(loaded.case.org_repo)
    contract = current_fact_acceptance_contract(entry.ecosystem, getattr(entry, "family", None))
    for surface in loaded.case.expected_surfaces:
        if loaded.facts.selected_fact(surface).verification_state != "blocked":
            raise ValueError(
                f"PF04 expected a still-blocked selected fact for {loaded.case.org_repo}:{surface}"
            )
    decisions = resolve_selected_external_fact_blocks(
        loaded.facts,
        snapshot=loaded.snapshot,
        contract=contract,
    )
    actual = tuple(sorted(decision.block.fact_surface for decision in decisions))
    expected = tuple(sorted(loaded.case.expected_surfaces))
    if actual != expected:
        raise ValueError(
            f"PF04 external surfaces drifted for {loaded.case.org_repo}: "
            f"expected {expected}, found {actual}"
        )
    persisted = tuple(
        decision.model_dump(mode="json")
        for decision in sorted(loaded.persisted_decisions, key=lambda item: item.block.fact_surface)
    )
    recomputed = tuple(
        decision.model_dump(mode="json")
        for decision in sorted(decisions, key=lambda item: item.block.fact_surface)
    )
    if persisted != recomputed:
        raise ValueError(f"PF04 persisted external decisions are stale for {loaded.case.org_repo}")
    return decisions


def build_pf04_case_bindings(
    cases: tuple[ExternalFactReplayCaseV1, ...],
    *,
    runs_root: Path,
) -> dict[str, dict]:
    """Return inspectable hashes for every current external-fact replay receipt."""

    bindings: dict[str, dict] = {}
    for case in cases:
        loaded = load_pf04_case(case, runs_root)
        decisions = resolve_current_case(loaded)
        entry = require_listed(case.org_repo)
        contract = current_fact_acceptance_contract(
            entry.ecosystem,
            getattr(entry, "family", None),
        )
        bindings[case.org_repo] = {
            "source_revision": case.source_revision,
            "snapshot_sha256": _sha256(loaded.bundle_dir / "source" / "revision.json"),
            "product_facts_sha256": _sha256(loaded.bundle_dir / "facts" / "product-facts.json"),
            "findings_sha256": _sha256(loaded.bundle_dir / "facts" / "findings.json"),
            "manifest_sha256": _sha256(loaded.bundle_dir / "manifest.json"),
            "fact_acceptance_contract_hash": contract.canonical_hash(),
            "fact_acceptance_component_hashes_sha256": canonical_sha256(contract.component_hashes),
            "local_verification_contract_hash": local_verification_contract_hash(entry.ecosystem),
            "persisted_decisions_sha256": canonical_sha256(
                [
                    decision.model_dump(mode="json")
                    for decision in sorted(decisions, key=lambda item: item.block.fact_surface)
                ]
            ),
        }
    return bindings


__all__ = [
    "ExternalFactReplayCaseV1",
    "LoadedExternalFactReplayCaseV1",
    "build_pf04_case_bindings",
    "load_pf04_case",
    "require_current_fact_receipt",
    "resolve_current_case",
]
