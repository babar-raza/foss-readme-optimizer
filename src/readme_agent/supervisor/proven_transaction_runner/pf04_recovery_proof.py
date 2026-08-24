"""Verify PF04's real canonical fact-recovery and preservation evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.evidence.writer import write_redacted_json
from readme_agent.facts.external_fact_block_adapters import ExternalFactResolutionDecisionV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.supervisor.proven_transaction_runner.contracts import canonical_sha256
from readme_agent.supervisor.proven_transaction_runner.pf04_case_evidence import (
    ExternalFactReplayCaseV1,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _verify_inventory(root: Path) -> str:
    inventory_path = root / "inventory.json"
    raw = _load_json(inventory_path)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"PF04 recovery inventory is empty or malformed: {inventory_path}")
    resolved_root = root.resolve()
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError(f"PF04 recovery inventory entry is malformed: {inventory_path}")
        evidence_path = Path(str(item["path"])).resolve()
        if not evidence_path.is_relative_to(resolved_root):
            raise ValueError(f"PF04 recovery inventory escapes its root: {evidence_path}")
        if not evidence_path.is_file() or _sha256(evidence_path) != item["sha256"]:
            raise ValueError(f"PF04 recovery inventory mismatch: {evidence_path}")
    return _sha256(inventory_path)


def _decisions(path: Path) -> tuple[ExternalFactResolutionDecisionV1, ...]:
    raw = _load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"PF04 recovery findings must be a list: {path}")
    return tuple(
        ExternalFactResolutionDecisionV1.model_validate(finding["external_fact_resolution"])
        for finding in raw
        if isinstance(finding, dict) and finding.get("external_fact_resolution") is not None
    )


def _fact_map(facts: ProductFactsV2) -> dict[str, dict]:
    return {fact.fact_id: fact.model_dump(mode="json") for fact in facts.facts}


def build_recovery_proof(
    cases: tuple[ExternalFactReplayCaseV1, ...],
    *,
    recovery_root: Path,
    current_runs_root: Path,
    preservation_witness: str,
    causally_related_fields: tuple[str, ...] = ("aspose.dependency_snapshot",),
) -> dict:
    """Prove canonical refresh, persisted decisions, and one preservation witness."""

    before_root = recovery_root / "before"
    after_root = recovery_root / "after"
    before_inventory_sha256 = _verify_inventory(before_root)
    after_inventory_sha256 = _verify_inventory(after_root)
    case_records: list[dict] = []
    witness_record: dict | None = None
    for case in cases:
        org, repo = case.org_repo.split("/", maxsplit=1)
        slug = f"{org}__{repo}"
        before_dir = before_root / slug
        after_dir = after_root / slug
        current_dir = current_runs_root / "readme-poc" / slug / case.source_revision
        before_snapshot = RepositorySnapshotV1.model_validate_json(
            (before_dir / "revision.json").read_text(encoding="utf-8-sig")
        )
        after_snapshot = RepositorySnapshotV1.model_validate_json(
            (after_dir / "revision.json").read_text(encoding="utf-8-sig")
        )
        before_facts = ProductFactsV2.model_validate_json(
            (before_dir / "facts" / "product-facts.json").read_text(encoding="utf-8-sig")
        )
        after_facts = ProductFactsV2.model_validate_json(
            (after_dir / "facts" / "product-facts.json").read_text(encoding="utf-8-sig")
        )
        before_manifest = _load_json(before_dir / "manifest.json")
        after_manifest = _load_json(after_dir / "manifest.json")
        if not isinstance(before_manifest, dict) or not isinstance(after_manifest, dict):
            raise ValueError(f"PF04 recovery manifests must be objects for {case.org_repo}")
        if (
            before_snapshot.org_repo != case.org_repo
            or after_snapshot.org_repo != case.org_repo
            or before_snapshot.source_revision != case.source_revision
            or after_snapshot.source_revision != case.source_revision
        ):
            raise ValueError(f"PF04 recovery snapshot identity mismatch for {case.org_repo}")
        if before_facts.selected_fact_ids != after_facts.selected_fact_ids:
            raise ValueError(f"PF04 canonical recovery changed fact selection for {case.org_repo}")
        if before_manifest.get("fact_acceptance_contract_hash") == after_manifest.get(
            "fact_acceptance_contract_hash"
        ):
            raise ValueError(f"PF04 recovery did not refresh the contract for {case.org_repo}")
        if before_manifest.get("completed_stages") != after_manifest.get("completed_stages"):
            raise ValueError(f"PF04 recovery discarded valid stages for {case.org_repo}")
        after_decisions = _decisions(after_dir / "facts" / "findings.json")
        actual_surfaces = tuple(sorted(item.block.fact_surface for item in after_decisions))
        if actual_surfaces != tuple(sorted(case.expected_surfaces)):
            raise ValueError(f"PF04 recovery decisions are incomplete for {case.org_repo}")
        current_hashes = {
            relative: _sha256(current_dir / relative)
            for relative in (
                "source/revision.json",
                "facts/product-facts.json",
                "facts/findings.json",
                "manifest.json",
            )
        }
        after_hashes = {
            "source/revision.json": _sha256(after_dir / "revision.json"),
            "facts/product-facts.json": _sha256(after_dir / "facts" / "product-facts.json"),
            "facts/findings.json": _sha256(after_dir / "facts" / "findings.json"),
            "manifest.json": _sha256(after_dir / "manifest.json"),
        }
        if current_hashes != after_hashes:
            raise ValueError(
                f"PF04 current receipt drifted from recovery proof for {case.org_repo}"
            )
        before_by_id = _fact_map(before_facts)
        after_by_id = _fact_map(after_facts)
        changed_fact_ids = sorted(
            fact_id
            for fact_id in before_by_id.keys() | after_by_id.keys()
            if before_by_id.get(fact_id) != after_by_id.get(fact_id)
        )
        record = {
            "org_repo": case.org_repo,
            "source_revision": case.source_revision,
            "before_contract_hash": before_manifest["fact_acceptance_contract_hash"],
            "after_contract_hash": after_manifest["fact_acceptance_contract_hash"],
            "completed_stages_preserved": before_manifest["completed_stages"],
            "selected_fact_ids_preserved": True,
            "persisted_decision_count": len(after_decisions),
            "persisted_decisions_sha256": canonical_sha256(
                [item.model_dump(mode="json") for item in after_decisions]
            ),
            "changed_fact_ids": changed_fact_ids,
            "current_receipt_hashes": current_hashes,
        }
        case_records.append(record)
        if case.org_repo == preservation_witness:
            permitted_refresh_fields = set(case.expected_surfaces) | set(causally_related_fields)
            preserved_fields = sorted(
                field
                for field, fact_id in before_facts.selected_fact_ids.items()
                if field not in permitted_refresh_fields
                and before_by_id[fact_id] == after_by_id[fact_id]
            )
            expected_preserved = sorted(
                set(before_facts.selected_fact_ids) - permitted_refresh_fields
            )
            if preserved_fields != expected_preserved:
                raise ValueError(
                    f"PF04 recovery changed an unrelated selected fact for {case.org_repo}"
                )
            witness_record = {
                "org_repo": case.org_repo,
                "targeted_surfaces": sorted(case.expected_surfaces),
                "causally_related_refresh_fields": sorted(causally_related_fields),
                "unrelated_selected_fields_preserved": preserved_fields,
                "preserved_selected_fact_count": len(preserved_fields),
            }
    if witness_record is None:
        raise ValueError("PF04 recovery preservation witness is absent from the case matrix")
    return {
        "schema_version": 1,
        "case_count": len(case_records),
        "before_inventory_sha256": before_inventory_sha256,
        "after_inventory_sha256": after_inventory_sha256,
        "cases": case_records,
        "preservation_witness": witness_record,
    }


def write_recovery_proof(path: Path, proof: dict) -> None:
    """Persist the verified proof through the shared redacted evidence writer."""

    write_redacted_json(path, proof)


__all__ = ["build_recovery_proof", "write_recovery_proof"]
