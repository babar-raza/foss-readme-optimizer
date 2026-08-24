"""Derive a replay-attestation contract from two real local-POC bundle views."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal, cast

from readme_agent.verification.sealed_transaction_replay import (
    DeclaredArtifactV1,
    IdentityBindingSpecV1,
    LedgerDeclarationSpecV1,
    ProductEffectExpectationV1,
    ProviderProofContractV1,
    ReplayAttestationContractV1,
)

_SAFE_ID = re.compile(r"[^a-z0-9_]+")
_MIN_ARTIFACT_LIMIT = 8_388_608
_MAX_ARTIFACT_LIMIT = 33_554_432


def _artifact_id(relative_path: str) -> str:
    stem = _SAFE_ID.sub("_", relative_path.casefold()).strip("_")[:90]
    suffix = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:12]
    return f"{stem}_{suffix}"


def _artifact_limit(*paths: Path) -> int:
    """Return bounded headroom for the largest sealed copy of an artifact."""

    largest = max(path.stat().st_size for path in paths)
    required = max(_MIN_ARTIFACT_LIMIT, largest)
    rounded = 1 << (required - 1).bit_length()
    return min(rounded, _MAX_ARTIFACT_LIMIT)


def _kind(
    path: Path,
) -> tuple[
    Literal["json_object", "json_array", "jsonl_llm_ledger", "text", "binary"],
    Literal["raw_sha256", "crlf_normalized_sha256", "canonical_json_sha256"],
]:
    if path.name == "llm-call-ledger.jsonl":
        return "jsonl_llm_ledger", "crlf_normalized_sha256"
    if path.suffix.casefold() == ".json":
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return (
            ("json_object" if isinstance(loaded, dict) else "json_array"),
            "raw_sha256",
        )
    try:
        path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return "binary", "raw_sha256"
    return "text", "raw_sha256"


def _stage(
    relative_path: str,
) -> Literal[
    "SOURCE",
    "KNOWLEDGE",
    "CONFIGURATION",
    "AUTHORING",
    "CANDIDATE",
    "VALIDATION",
    "REVIEW",
    "ACCEPTANCE",
    "EFFECTS",
    "SEALING",
]:
    prefix = relative_path.split("/", 1)[0]
    return cast(
        Literal[
            "SOURCE",
            "KNOWLEDGE",
            "CONFIGURATION",
            "AUTHORING",
            "CANDIDATE",
            "VALIDATION",
            "REVIEW",
            "ACCEPTANCE",
            "EFFECTS",
            "SEALING",
        ],
        {
            "source": "SOURCE",
            "facts": "KNOWLEDGE",
            "knowledge-application.json": "KNOWLEDGE",
            "assurance": "AUTHORING",
            "assessment": "AUTHORING",
            "planning": "AUTHORING",
            "candidate": "CANDIDATE",
            "review": "REVIEW",
            "intake": "SOURCE",
            "receipts": "SEALING",
            "llm-call-ledger.jsonl": "SEALING",
            "manifest.json": "SEALING",
        }.get(prefix, "SEALING"),
    )


def _files(root: Path) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file() and path.name != "sha256sums.txt"
    }


def derive_local_poc_replay_contract(
    *,
    first_root: Path,
    replay_root: Path,
) -> ReplayAttestationContractV1:
    """Declare every semantic file in the actual pair and bind stable transaction identities."""

    first = _files(first_root)
    replay = _files(replay_root)
    relative_paths = sorted(set(first) | set(replay))
    artifacts: list[DeclaredArtifactV1] = []
    ids: dict[str, str] = {}
    outputs: list[str] = []
    for relative in relative_paths:
        ids[relative] = artifact_id = _artifact_id(relative)
        path = first.get(relative) or replay[relative]
        kind, hash_mode = _kind(path)
        scope = cast(
            Literal["both", "first_only", "replay_only"],
            "both"
            if relative in first and relative in replay
            else ("first_only" if relative in first else "replay_only"),
        )
        mutable_bookkeeping = relative in {"manifest.json", "llm-call-ledger.jsonl"}
        artifacts.append(
            DeclaredArtifactV1(
                artifact_id=artifact_id,
                relative_path=relative,
                hash_mode=hash_mode,
                kind=kind,
                level="REQUIRED",
                stage=_stage(relative),
                scope=scope,
                compare_for_delta=scope == "both" and not mutable_bookkeeping,
                max_bytes=_artifact_limit(
                    *(
                        candidate
                        for candidate in (first.get(relative), replay.get(relative))
                        if candidate
                    )
                ),
            )
        )
        if scope == "both" and not mutable_bookkeeping:
            outputs.append(artifact_id)

    manifest_id = ids["manifest.json"]
    ledger_id = ids["llm-call-ledger.jsonl"]
    preflight_id = ids["intake/preflight.json"]
    source_id = ids["source/revision.json"]
    no_op_id = ids["review/no-op-proof.json"]
    manifest = json.loads((replay_root / "manifest.json").read_text(encoding="utf-8"))
    return ReplayAttestationContractV1(
        contract_id="local-poc-complete-transaction-v1",
        org_repo=str(manifest["org_repo"]),
        expected_source_revision=str(manifest["source_revision"]),
        artifacts=tuple(artifacts),
        identity_bindings=(
            IdentityBindingSpecV1(
                component="repository_identity",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/org_repo",
            ),
            IdentityBindingSpecV1(
                component="source_revision",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/source_revision",
            ),
            IdentityBindingSpecV1(
                component="facts_hash",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/facts_hash",
            ),
            IdentityBindingSpecV1(
                component="candidate_hash",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/candidate_hash",
            ),
            IdentityBindingSpecV1(
                component="candidate_stage_dependency_key",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/candidate_stage_dependency_key",
            ),
            IdentityBindingSpecV1(
                component="prompt_registry_hash",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/prompt_registry_content_hash",
            ),
            IdentityBindingSpecV1(
                component="reviewer_standard_hash",
                level="REQUIRED",
                artifact_id=manifest_id,
                json_pointer="/reviewer_standard_hash",
            ),
            IdentityBindingSpecV1(
                component="source_readme_digest",
                level="REQUIRED",
                artifact_id=source_id,
                json_pointer="/readme_sha256",
            ),
            IdentityBindingSpecV1(
                component="source_tree_inventory_digest",
                level="REQUIRED",
                artifact_id=source_id,
                json_pointer="/inventory_sha256",
            ),
        ),
        output_equivalence_artifact_ids=tuple(sorted(outputs)),
        provider_proof=ProviderProofContractV1(
            first_ledger_artifact_id=ledger_id,
            replay_ledger_artifact_id=ledger_id,
            first_declaration=LedgerDeclarationSpecV1(artifact_id=manifest_id),
            replay_declaration=LedgerDeclarationSpecV1(artifact_id=manifest_id),
        ),
        product_effects=(
            ProductEffectExpectationV1(
                effect="readme_write",
                level="REQUIRED",
                artifact_id=source_id,
                json_pointer="/readme_sha256",
                comparison="equal_across_bundles",
            ),
            ProductEffectExpectationV1(
                effect="target_tree_change",
                level="REQUIRED",
                artifact_id=source_id,
                json_pointer="/inventory_sha256",
                comparison="equal_across_bundles",
            ),
            *(
                ProductEffectExpectationV1(
                    effect=effect,
                    level="REQUIRED",
                    artifact_id=preflight_id,
                    json_pointer="/target_remote_effects_allowed",
                    comparison="equals_expected",
                    expected_value=False,
                )
                for effect in ("commit", "branch", "push", "pull_request", "publication")
            ),
            ProductEffectExpectationV1(
                effect="duplicate_lifecycle_effect",
                level="REQUIRED",
                artifact_id=no_op_id,
                json_pointer="/duplicate_bundle_created",
                comparison="equals_expected",
                expected_value=False,
            ),
        ),
    )


__all__ = ["derive_local_poc_replay_contract"]
