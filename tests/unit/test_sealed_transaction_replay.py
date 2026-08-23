"""Attest that a sealed replay transaction reused the first and did nothing new.

No real PF-03 bundle pair (a completed transaction plus its immediate no-op replay) exists in
this repository yet -- the PF-02 bundle stops at DETERMINISTIC_VALIDATED and the only
NO_OP_PROVEN example predates stage_receipts/the LLM call ledger. Every fixture here is
synthetic but structurally faithful to the real on-disk bundle shape. Attesting a real captured
pair remains an integration-time test once L8-PF-03-SEALED-CANDIDATE-NO-OP produces one.
"""

from __future__ import annotations

import ast
import json
import os
import re
import socket
import subprocess
import types
from pathlib import Path
from typing import Any

import pydantic
import pytest

from readme_agent.evidence.writer import sha256_file, verify_sha256sums
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.verification import sealed_transaction_replay as attestor
from readme_agent.verification.sealed_transaction_replay import (
    CompleteTransactionNoOpProofV1,
    DeclaredArtifactV1,
    IdentityBindingSpecV1,
    LedgerDeclarationSpecV1,
    ProductEffectExpectationV1,
    ProviderProofContractV1,
    ReplayAttestationContractV1,
    attest_complete_transaction_noop,
    canonical_json_sha256,
    canonical_proof_hash,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sealed_transaction_replay"

ORG_REPO = "example-foss/Example-FOSS-for-Python"
SOURCE_REVISION = "a1b2c3d4" * 5
REVIEWER_STANDARD_HASH = "9e" * 32
CHECK_IMPLEMENTATION_HASH = "7c" * 32
PROMPT_REGISTRY_HASH = "5a" * 32

SOURCE_README = (FIXTURES / "source-README.md").read_bytes()
CANDIDATE_README = (FIXTURES / "candidate-README.md").read_bytes()
CANDIDATE_PATCH = (FIXTURES / "candidate-README.patch").read_bytes()
# A CRLF checkout would silently change the raw candidate hash; fail loudly instead of producing
# 29 confusing mismatches.
assert b"\r\n" not in CANDIDATE_README
assert b"\r\n" not in SOURCE_README
assert b"\r\n" not in CANDIDATE_PATCH


# ---- golden ledger ----

_AUTHOR_JOB = "section_cluster_authoring"
_FACTUAL_JOB = "factual_readme_plan_review"
_VISITOR_JOB = "blind_readme_quality_review"
_REPAIR_JOB = "repair_capability_selection"


def _ledger_record(
    *,
    call_id: str,
    job: str,
    disposition: str,
    run_id: str,
    prompt_sha256: str = "b" * 64,
    model: str = "qwen3-next",
    request_sha256: str = "c" * 64,
    started_at: str = "2026-08-23T00:00:00+00:00",
    finished_at: str = "2026-08-23T00:00:01+00:00",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "call_id": call_id,
        "logical_call_id": call_id,
        "org_repo": ORG_REPO,
        "source_revision": SOURCE_REVISION,
        "run_id": run_id,
        "campaign_id": "camp-1",
        "stage": "AUTHORING",
        "job": job,
        "prompt_id": f"{job}_prompt",
        "prompt_sha256": prompt_sha256,
        "provider": "cache" if disposition == "cache_reuse" else "configured_gateway",
        "model": model,
        "attempt": 1,
        "disposition": disposition,
        "started_at": started_at,
        "finished_at": finished_at,
        "latency_ms": 0 if disposition == "cache_reuse" else 500,
        "outcome": "cache_reuse" if disposition == "cache_reuse" else "success",
        "request_sha256": request_sha256,
        "cost_unavailable_reason": "not_a_provider_call"
        if disposition == "cache_reuse"
        else "pricing_not_configured",
        "pricing_source": "unconfigured",
        "pricing_version": "unconfigured",
    }


def _golden_ledger_first() -> list[dict[str, Any]]:
    return [
        _ledger_record(
            call_id="call-author-1",
            job=_AUTHOR_JOB,
            disposition="provider_call",
            run_id="first-run",
        ),
        _ledger_record(
            call_id="call-factual-1",
            job=_FACTUAL_JOB,
            disposition="provider_call",
            run_id="first-run",
        ),
        _ledger_record(
            call_id="call-visitor-1",
            job=_VISITOR_JOB,
            disposition="provider_call",
            run_id="first-run",
        ),
    ]


def _golden_ledger_replay() -> list[dict[str, Any]]:
    return _golden_ledger_first() + [
        _ledger_record(
            call_id="call-author-1-reuse",
            job=_AUTHOR_JOB,
            disposition="cache_reuse",
            run_id="replay-run",
            started_at="2026-08-23T01:00:00+00:00",
            finished_at="2026-08-23T01:00:00+00:00",
        ),
        _ledger_record(
            call_id="call-factual-1-reuse",
            job=_FACTUAL_JOB,
            disposition="cache_reuse",
            run_id="replay-run",
            started_at="2026-08-23T01:00:00+00:00",
            finished_at="2026-08-23T01:00:00+00:00",
        ),
        _ledger_record(
            call_id="call-visitor-1-reuse",
            job=_VISITOR_JOB,
            disposition="cache_reuse",
            run_id="replay-run",
            started_at="2026-08-23T01:00:00+00:00",
            finished_at="2026-08-23T01:00:00+00:00",
        ),
    ]


# ---- golden tree ----


def _golden_tree(role: str) -> dict[str, Any]:
    facts = {"product": {"name": "Example FOSS for Python", "language": "python"}}
    return {
        "manifest.json": {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "lifecycle_status": "NO_OP_PROVEN" if role == "replay" else "AGENT_APPROVED",
            "prompt_registry_hash": PROMPT_REGISTRY_HASH,
            "prompt_dependency_hashes": {
                "FACTS_COLLECTING": "aa" * 32,
                "CANDIDATE_GENERATED": "bb" * 32,
                "AGENT_REVIEWING": "cc" * 32,
            },
            "check_implementation_hash": CHECK_IMPLEMENTATION_HASH,
            "reviewer_standard_hash": REVIEWER_STANDARD_HASH,
            "llm_accounting_status": "EXACT",
            "llm_call_count": 3,
            "patch_created": False,
            "duplicate_bundle_created": False,
        },
        "source/revision.json": {
            "source_revision": SOURCE_REVISION,
            "readme_sha256": sha256_hex(SOURCE_README),
            "inventory_sha256": "d" * 64,
            "snapshot_root": f"/tmp/snapshot-{role}",
            "captured_at": "2026-08-23T00:00:00+00:00"
            if role == "first"
            else "2026-08-23T01:00:00+00:00",
        },
        "source/README.md": SOURCE_README,
        "facts/product-facts.json": facts,
        "candidate/README.md": CANDIDATE_README,
        "candidate/README.patch": CANDIDATE_PATCH,
        "candidate/candidate-hash.txt": None,  # derived in _seal
        "planning/readme-document-plan.json": {
            "schema_version": 1,
            "org_repo": ORG_REPO,
            "operations": [{"operation": "insert_section", "section": "Architecture"}],
        },
        "review/deterministic-validation.json": {
            "schema_version": 1,
            "valid": True,
            "checks": {"word_count": True, "link_whitelist": True},
            "errors": [],
        },
        "review/factual-plan-review.json": {
            "schema_version": 1,
            "verdict": "ACCEPT",
            "reasoning": "all claims verified against source",
            "failed_criteria": [],
        },
        "review/blind-quality-review.json": {
            "schema_version": 1,
            "verdict": "ACCEPT",
            "reasoning": "clear and product-specific",
            "failed_criteria": [],
        },
        "review/final-verdict.json": {
            "verdict": "AGENT_APPROVED",
            "agent_approved": True,
            "deterministic_validation_passed": True,
            "repair_attempts": 0,
        },
        "review/rubric-evaluation.json": {
            "schema_version": 1,
            "rubric_version": "RUBRIC_30/2026-08-20",
            "awarded_points": 30,
            "max_points": 30,
            "hard_disqualifiers": [],
        },
        "review/repair-history.json": {"schema_version": 1, "attempts": []},
        "receipts/CANDIDATE_GENERATED.json": {"stage": "CANDIDATE_GENERATED", "promoted_at": "t0"},
        "receipts/AGENT_APPROVED.json": {"stage": "AGENT_APPROVED", "promoted_at": "t1"},
        "llm-call-ledger.jsonl": _golden_ledger_replay()
        if role == "replay"
        else _golden_ledger_first(),
    }


def _add_replay_only_artifacts(tree: dict[str, Any]) -> None:
    tree["receipts/NO_OP_PROVEN.json"] = {"stage": "NO_OP_PROVEN", "promoted_at": "t2"}
    tree["review/no-op-proof.json"] = {
        "verdict": "NO_OP_PROVEN",
        "patch_created": False,
        "duplicate_bundle_created": False,
        "agentic_review_reused": True,
        "llm_accounting_status": "EXACT",
        "new_provider_call_count": 0,
    }
    tree["effects/product-effect-ledger.json"] = {
        "schema_version": 1,
        "paths_written": [],
        "commits_created": 0,
        "branches_created": 0,
        "push_attempts": 0,
        "pull_requests_opened": 0,
        "published": False,
        "work_clone_tree_sha256_before": "e" * 64,
        "work_clone_tree_sha256_after": "e" * 64,
    }


# ---- sealing (derive hashes, write files, write sha256sums.txt) ----


def _seal(root: Path, tree: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    candidate_bytes = tree["candidate/README.md"]
    candidate_hash = sha256_hex(candidate_bytes)
    tree["candidate/candidate-hash.txt"] = (candidate_hash + "\n").encode("utf-8")
    tree["manifest.json"]["candidate_hash"] = candidate_hash
    tree["manifest.json"]["facts_hash"] = canonical_json_sha256(tree["facts/product-facts.json"])
    tree["manifest.json"]["candidate_stage_dependency_key"] = canonical_json_sha256(
        {"candidate_hash": candidate_hash, "plan": tree["planning/readme-document-plan.json"]}
    )

    deterministic_hash = canonical_json_sha256(tree["review/deterministic-validation.json"])
    tree["manifest.json"]["deterministic_validation_hash"] = deterministic_hash
    binding = {
        "candidate_hash": candidate_hash,
        "deterministic_validation_hash": deterministic_hash,
        "reviewer_standard_hash": tree["manifest.json"]["reviewer_standard_hash"],
    }
    for key in (
        "review/factual-plan-review.json",
        "review/blind-quality-review.json",
        "review/final-verdict.json",
        "review/rubric-evaluation.json",
    ):
        tree[key]["acceptance_binding"] = binding
    if "review/no-op-proof.json" in tree:
        tree["review/no-op-proof.json"]["candidate_hash"] = candidate_hash
        tree["review/no-op-proof.json"]["acceptance_binding"] = binding

    for relpath, value in list(tree.items()):
        target = root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        if relpath.endswith(".jsonl"):
            lines = "\n".join(
                json.dumps(record, sort_keys=True, separators=(",", ":")) for record in value
            )
            target.write_text(lines + "\n", encoding="utf-8", newline="\n")
        elif isinstance(value, bytes):
            target.write_bytes(value)
        else:
            target.write_text(
                json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )

    ledger_path = root / "llm-call-ledger.jsonl"
    ledger_digest = sha256_file(ledger_path)[0]
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["ledger_digest"] = ledger_digest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    _write_inventory(root)


def _write_inventory(root: Path) -> None:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "sha256sums.txt":
            digest, _ = sha256_file(path)
            entries.append(f"{digest}  {path.relative_to(root).as_posix()}")
    (root / "sha256sums.txt").write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


# ---- contract ----


def _golden_contract() -> ReplayAttestationContractV1:
    def artifact(
        artifact_id: str,
        relative_path: str,
        hash_mode: str,
        kind: str,
        level: str,
        stage: str,
        scope: str = "both",
        compare_for_delta: bool = True,
    ) -> DeclaredArtifactV1:
        return DeclaredArtifactV1(
            artifact_id=artifact_id,
            relative_path=relative_path,
            hash_mode=hash_mode,  # type: ignore[arg-type]
            kind=kind,  # type: ignore[arg-type]
            level=level,  # type: ignore[arg-type]
            stage=stage,  # type: ignore[arg-type]
            scope=scope,  # type: ignore[arg-type]
            compare_for_delta=compare_for_delta,
        )

    artifacts = (
        artifact(
            "manifest",
            "manifest.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "SOURCE",
            compare_for_delta=False,
        ),
        artifact(
            "source_revision",
            "source/revision.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "SOURCE",
        ),
        artifact("source_readme", "source/README.md", "raw_sha256", "text", "REQUIRED", "SOURCE"),
        artifact(
            "facts",
            "facts/product-facts.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "KNOWLEDGE",
        ),
        artifact("candidate", "candidate/README.md", "raw_sha256", "text", "REQUIRED", "CANDIDATE"),
        artifact(
            "candidate_patch",
            "candidate/README.patch",
            "crlf_normalized_sha256",
            "text",
            "REQUIRED",
            "CANDIDATE",
        ),
        artifact(
            "candidate_hash_file",
            "candidate/candidate-hash.txt",
            "raw_sha256",
            "text",
            "REQUIRED",
            "CANDIDATE",
        ),
        artifact(
            "document_plan",
            "planning/readme-document-plan.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "CANDIDATE",
        ),
        artifact(
            "deterministic_validation",
            "review/deterministic-validation.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "VALIDATION",
        ),
        artifact(
            "factual_review",
            "review/factual-plan-review.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "REVIEW",
        ),
        artifact(
            "visitor_review",
            "review/blind-quality-review.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "REVIEW",
        ),
        artifact(
            "final_verdict",
            "review/final-verdict.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "ACCEPTANCE",
        ),
        artifact(
            "rubric",
            "review/rubric-evaluation.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "ACCEPTANCE",
        ),
        artifact(
            "repair_history",
            "review/repair-history.json",
            "canonical_json_sha256",
            "json_object",
            "OPTIONAL",
            "REVIEW",
        ),
        artifact(
            "receipt_candidate",
            "receipts/CANDIDATE_GENERATED.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "CANDIDATE",
            compare_for_delta=False,
        ),
        artifact(
            "receipt_approved",
            "receipts/AGENT_APPROVED.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "ACCEPTANCE",
            compare_for_delta=False,
        ),
        artifact(
            "receipt_noop",
            "receipts/NO_OP_PROVEN.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "ACCEPTANCE",
            scope="replay_only",
        ),
        artifact(
            "no_op_proof",
            "review/no-op-proof.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "ACCEPTANCE",
            scope="replay_only",
        ),
        artifact(
            "effects_ledger",
            "effects/product-effect-ledger.json",
            "canonical_json_sha256",
            "json_object",
            "REQUIRED",
            "EFFECTS",
            scope="replay_only",
        ),
        artifact(
            "ledger",
            "llm-call-ledger.jsonl",
            "crlf_normalized_sha256",
            "jsonl_llm_ledger",
            "REQUIRED",
            "SEALING",
            compare_for_delta=False,
        ),
    )

    identity_bindings = (
        IdentityBindingSpecV1(
            component="repository_identity",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/org_repo",
        ),
        IdentityBindingSpecV1(
            component="source_revision",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/source_revision",
        ),
        IdentityBindingSpecV1(
            component="facts_hash",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/facts_hash",
        ),
        IdentityBindingSpecV1(
            component="candidate_hash",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/candidate_hash",
        ),
        IdentityBindingSpecV1(
            component="prompt_registry_hash",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/prompt_registry_hash",
        ),
        IdentityBindingSpecV1(
            component="prompt_dependency_hashes",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/prompt_dependency_hashes",
        ),
        IdentityBindingSpecV1(
            component="check_implementation_hash",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/check_implementation_hash",
        ),
        IdentityBindingSpecV1(
            component="reviewer_standard_hash",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/reviewer_standard_hash",
        ),
        IdentityBindingSpecV1(
            component="deterministic_validation_hash",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/deterministic_validation_hash",
        ),
        IdentityBindingSpecV1(
            component="candidate_stage_dependency_key",
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer="/candidate_stage_dependency_key",
        ),
    )

    product_effects = (
        ProductEffectExpectationV1(
            effect="readme_write",
            level="REQUIRED",
            artifact_id="source_revision",
            json_pointer="/readme_sha256",
            comparison="equal_across_bundles",
        ),
        ProductEffectExpectationV1(
            effect="target_tree_change",
            level="REQUIRED",
            artifact_id="source_revision",
            json_pointer="/inventory_sha256",
            comparison="equal_across_bundles",
        ),
        ProductEffectExpectationV1(
            effect="commit",
            level="REQUIRED",
            artifact_id="no_op_proof",
            json_pointer="/patch_created",
            comparison="equals_expected",
            expected_value=False,
        ),
        ProductEffectExpectationV1(
            effect="duplicate_lifecycle_effect",
            level="REQUIRED",
            artifact_id="no_op_proof",
            json_pointer="/duplicate_bundle_created",
            comparison="equals_expected",
            expected_value=False,
        ),
        ProductEffectExpectationV1(
            effect="branch",
            level="REQUIRED",
            artifact_id="effects_ledger",
            json_pointer="/branches_created",
            comparison="equals_expected",
            expected_value=0,
        ),
        ProductEffectExpectationV1(
            effect="push",
            level="REQUIRED",
            artifact_id="effects_ledger",
            json_pointer="/push_attempts",
            comparison="equals_expected",
            expected_value=0,
        ),
        ProductEffectExpectationV1(
            effect="pull_request",
            level="REQUIRED",
            artifact_id="effects_ledger",
            json_pointer="/pull_requests_opened",
            comparison="equals_expected",
            expected_value=0,
        ),
        ProductEffectExpectationV1(
            effect="publication",
            level="REQUIRED",
            artifact_id="effects_ledger",
            json_pointer="/published",
            comparison="equals_expected",
            expected_value=False,
        ),
    )

    return ReplayAttestationContractV1(
        contract_id="golden-fixture-v1",
        org_repo=ORG_REPO,
        expected_source_revision=SOURCE_REVISION,
        artifacts=artifacts,
        identity_bindings=identity_bindings,
        output_equivalence_artifact_ids=(
            "candidate",
            "candidate_patch",
            "candidate_hash_file",
            "document_plan",
            "deterministic_validation",
            "factual_review",
            "visitor_review",
            "final_verdict",
            "rubric",
        ),
        provider_proof=ProviderProofContractV1(
            first_ledger_artifact_id="ledger",
            replay_ledger_artifact_id="ledger",
            first_declaration=LedgerDeclarationSpecV1(artifact_id="manifest"),
            replay_declaration=LedgerDeclarationSpecV1(artifact_id="manifest"),
        ),
        product_effects=product_effects,
        lifecycle_effect_directories=("superseded",),
    )


Mutate = Any


class Pair:
    def __init__(
        self, root: Path, first_dir: Path, replay_dir: Path, contract: ReplayAttestationContractV1
    ) -> None:
        self.root = root
        self.first_dir = first_dir
        self.replay_dir = replay_dir
        self.contract = contract

    def attest(self) -> CompleteTransactionNoOpProofV1:
        return attest_complete_transaction_noop(
            first_bundle_root=self.first_dir,
            replay_bundle_root=self.replay_dir,
            expected_contract=self.contract,
        )


def build_pair(
    tmp_path: Path,
    *,
    first: Mutate = None,
    replay: Mutate = None,
    contract: Mutate = None,
    raw_first: Mutate = None,
    raw_replay: Mutate = None,
    reseal_after_raw: bool = False,
) -> Pair:
    first_tree = _golden_tree("first")
    replay_tree = _golden_tree("replay")
    _add_replay_only_artifacts(replay_tree)
    if first is not None:
        first(first_tree)
    if replay is not None:
        replay(replay_tree)

    first_dir = tmp_path / "t1"
    replay_dir = tmp_path / "t2"
    _seal(first_dir, first_tree)
    _seal(replay_dir, replay_tree)

    for target_dir, mutator in ((first_dir, raw_first), (replay_dir, raw_replay)):
        if mutator is not None:
            mutator(target_dir)
            if reseal_after_raw:
                _write_inventory(target_dir)

    built_contract = _golden_contract()
    if contract is not None:
        built_contract = contract(built_contract)

    return Pair(tmp_path, first_dir, replay_dir, built_contract)


# ---- assertion helpers ----


def assert_passed(proof: CompleteTransactionNoOpProofV1) -> None:
    assert proof.passed is True, (proof.failures, [f.code for f in proof.findings])


def assert_failed(proof: CompleteTransactionNoOpProofV1, code_substring: str) -> None:
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert any(code_substring in code for code in codes), codes


def _tree_snapshot(root: Path) -> dict[str, tuple[int, str]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest, size = sha256_file(path)
            snapshot[str(path.relative_to(root))] = (size, digest)
    return snapshot


# ==== 1: happy path ====


def test_01_valid_first_and_replay_pair_passes(tmp_path: Path) -> None:
    pair = build_pair(tmp_path)
    assert verify_sha256sums(pair.first_dir) is True
    assert verify_sha256sums(pair.replay_dir) is True

    proof = pair.attest()
    assert_passed(proof)
    assert proof.earliest_affected_stage is None
    assert proof.provider_delta.accounting_certain is True
    assert proof.provider_delta.replay_authoring_calls == 0
    assert proof.provider_delta.replay_factual_review_calls == 0
    assert proof.provider_delta.replay_visitor_review_calls == 0
    assert proof.provider_delta.replay_repair_calls == 0
    assert proof.provider_delta.replay_new_cache_reuse_count == 3
    assert proof.artifact_delta.changed_artifact_ids == ()
    assert proof.effect_delta.violated == ()
    assert proof.effect_delta.unproven == ()
    assert re.fullmatch(r"[0-9a-f]{64}", proof.proof_hash)


# ==== 2-5: per-role provider-call budget ====


def _append_provider_call(job: str, call_id: str) -> Mutate:
    def mutate(tree: dict[str, Any]) -> None:
        record = _ledger_record(
            call_id=call_id,
            job=job,
            disposition="provider_call",
            run_id="replay-run",
            started_at="2026-08-23T02:00:00+00:00",
            finished_at="2026-08-23T02:00:01+00:00",
        )
        tree["llm-call-ledger.jsonl"].append(record)
        tree["manifest.json"]["llm_call_count"] = 4

    return mutate


def test_02_one_author_call_fails(tmp_path: Path) -> None:
    pair = build_pair(tmp_path, replay=_append_provider_call(_AUTHOR_JOB, "call-author-new"))
    proof = pair.attest()
    assert_failed(proof, "new_provider_call:authoring")
    assert proof.provider_delta.replay_authoring_calls == 1
    assert proof.provider_delta.replay_factual_review_calls == 0
    assert proof.earliest_affected_stage == "AUTHORING"


def test_02b_unmapped_job_fails(tmp_path: Path) -> None:
    pair = build_pair(
        tmp_path, replay=_append_provider_call("totally_unmapped_job", "call-unknown-new")
    )
    proof = pair.attest()
    assert_failed(proof, "unmapped_job")
    assert "totally_unmapped_job" in proof.provider_delta.replay_unclassified_jobs


def test_03_one_factual_review_call_fails(tmp_path: Path) -> None:
    pair = build_pair(tmp_path, replay=_append_provider_call(_FACTUAL_JOB, "call-factual-new"))
    proof = pair.attest()
    assert_failed(proof, "new_provider_call:factual_review")
    assert proof.provider_delta.replay_factual_review_calls == 1
    assert proof.earliest_affected_stage == "REVIEW"


def test_04_one_visitor_review_call_fails(tmp_path: Path) -> None:
    pair = build_pair(tmp_path, replay=_append_provider_call(_VISITOR_JOB, "call-visitor-new"))
    proof = pair.attest()
    assert_failed(proof, "new_provider_call:visitor_review")
    assert proof.provider_delta.replay_visitor_review_calls == 1
    assert proof.earliest_affected_stage == "REVIEW"


def test_05_one_repair_call_fails(tmp_path: Path) -> None:
    pair = build_pair(tmp_path, replay=_append_provider_call(_REPAIR_JOB, "call-repair-new"))
    proof = pair.attest()
    assert_failed(proof, "new_provider_call:repair")
    assert proof.provider_delta.replay_repair_calls == 1


# ==== 6-7: ledger presence and accounting status ====


def test_06_missing_ledger_fails(tmp_path: Path) -> None:
    def unlink_ledger(root: Path) -> None:
        (root / "llm-call-ledger.jsonl").unlink()

    pair = build_pair(tmp_path, raw_replay=unlink_ledger, reseal_after_raw=True)
    proof = pair.attest()
    assert proof.passed is False
    assert proof.provider_delta.accounting_certain is False
    assert proof.provider_delta.replay_provider_call_count is None
    assert proof.provider_delta.first_provider_call_count is None


def test_07_non_exact_ledger_accounting_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["manifest.json"]["llm_accounting_status"] = "UNKNOWN_LEGACY"

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert proof.provider_delta.accounting_certain is False
    assert proof.provider_delta.replay_declared_status == "UNKNOWN_LEGACY"


# ==== 8-11: semantic equality and the closed allowlist ====


def test_08_identical_candidate_with_changed_review_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["review/blind-quality-review.json"]["reasoning"] = "one blocking finding"
        tree["review/blind-quality-review.json"]["failed_criteria"] = ["clarity"]

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert "visitor_review" in proof.artifact_delta.changed_artifact_ids
    assert "candidate" not in proof.artifact_delta.changed_artifact_ids


def test_09_identical_candidate_and_review_with_changed_rubric_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["review/rubric-evaluation.json"]["rubric_version"] = "RUBRIC_30/2026-09-01"

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert "rubric" in proof.artifact_delta.changed_artifact_ids
    assert proof.earliest_affected_stage == "ACCEPTANCE"


def test_10_explicit_timestamp_and_run_id_differences_pass(tmp_path: Path) -> None:
    # The golden pair already carries different, but allowed, captured_at/snapshot_root values
    # between first and replay (a legitimate local re-capture) -- test 1's happy path already
    # proves that passes. This test drives the same two fields to a THIRD pair of values, proving
    # the allowlist tolerates arbitrary values there, not just the golden fixture's specific ones.
    def mutate(tree: dict[str, Any]) -> None:
        tree["source/revision.json"]["captured_at"] = "2026-08-23T09:00:00+00:00"
        tree["source/revision.json"]["snapshot_root"] = "/some/other/local/path"

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert_passed(proof)
    assert "source_revision#/captured_at" in proof.artifact_delta.allowed_differences_observed
    assert "source_revision#/snapshot_root" in proof.artifact_delta.allowed_differences_observed
    assert proof.artifact_delta.changed_artifact_ids == ()


def test_11_undeclared_semantic_difference_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["review/deterministic-validation.json"]["checks"]["word_count"] = False
        tree["review/deterministic-validation.json"]["valid"] = False

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert "deterministic_validation" in proof.artifact_delta.changed_artifact_ids


# ==== 12-18: drift classification ====


def test_12_prompt_drift_is_classified(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["manifest.json"]["prompt_registry_hash"] = "f" * 64

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert "identity_drift:prompt_registry_hash" in codes
    assert proof.earliest_affected_stage == "CONFIGURATION"


def test_13_model_drift_is_classified(tmp_path: Path) -> None:
    # Mutate the SHARED call_id (call-author-1), not the separate "-reuse" cache record: only a
    # call_id present in both bundles is checked for reused-record drift by the ledger superset
    # comparison. The "-reuse" records are new cache_reuse entries with their own call_ids and are
    # never matched back against a first-bundle record.
    def mutate(tree: dict[str, Any]) -> None:
        for record in tree["llm-call-ledger.jsonl"]:
            if record["call_id"] == "call-author-1":
                record["model"] = "qwen3-next-2510"

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert "model_drift:authoring" in codes
    assert "sampling_drift:authoring" not in codes
    assert "identity_drift:prompt_registry_hash" not in codes


def test_14_sampling_drift_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        for record in tree["llm-call-ledger.jsonl"]:
            if record["call_id"] == "call-author-1":
                record["request_sha256"] = "d" * 64

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert "sampling_drift:authoring" in codes
    assert "model_drift:authoring" not in codes


def test_15_source_drift_is_classified(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        extra = tree["source/README.md"] + b"\nExtra paragraph.\n"
        tree["source/README.md"] = extra
        tree["source/revision.json"]["readme_sha256"] = sha256_hex(extra)

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert proof.earliest_affected_stage == "SOURCE"


def test_16_facts_drift_is_classified(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["facts/product-facts.json"]["product"]["language"] = "python3"

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert "identity_drift:facts_hash" in codes
    assert proof.earliest_affected_stage == "KNOWLEDGE"


def test_17_check_drift_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["manifest.json"]["check_implementation_hash"] = "1" * 64

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert "identity_drift:check_implementation_hash" in codes
    assert proof.earliest_affected_stage == "CONFIGURATION"


def test_18_reviewer_standard_drift_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["manifest.json"]["reviewer_standard_hash"] = "2" * 64
        # acceptance_binding chain re-derived from this same field in _seal, so it propagates
        # consistently -- only the cross-bundle comparison should catch the drift.

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    codes = [f.code for f in proof.findings]
    assert "identity_drift:reviewer_standard_hash" in codes


# ==== 19-22: bundle integrity and declaration hygiene ====


def test_19_corruption_hash_mismatch_fails(tmp_path: Path) -> None:
    def tamper(root: Path) -> None:
        path = root / "candidate" / "README.md"
        path.write_bytes(path.read_bytes() + b"\n<!-- tampered -->\n")

    pair = build_pair(tmp_path, raw_replay=tamper, reseal_after_raw=False)
    assert verify_sha256sums(pair.replay_dir) is False
    proof = pair.attest()
    assert proof.passed is False


def test_19b_stale_inventory_digest_fails(tmp_path: Path) -> None:
    def tamper(root: Path) -> None:
        sums = root / "sha256sums.txt"
        lines = sums.read_text(encoding="utf-8").splitlines()
        lines = [
            line.replace(line.split("  ")[0], "0" * 64) if line.endswith("manifest.json") else line
            for line in lines
        ]
        sums.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    pair = build_pair(tmp_path, raw_replay=tamper, reseal_after_raw=False)
    proof = pair.attest()
    assert proof.passed is False
    assert "manifest.json" in proof.replay_inventory.hash_declaration_mismatches


# ==== 20: missing required artifact fails ====


@pytest.mark.parametrize(
    "relative_path",
    [
        "review/factual-plan-review.json",
        "receipts/AGENT_APPROVED.json",
        "planning/readme-document-plan.json",
    ],
)
def test_20_missing_required_artifact_fails(tmp_path: Path, relative_path: str) -> None:
    def unlink(root: Path) -> None:
        (root / relative_path).unlink()

    pair = build_pair(tmp_path, raw_replay=unlink, reseal_after_raw=True)
    proof = pair.attest()
    assert proof.passed is False
    assert proof.replay_inventory.missing_required != ()


def test_20b_missing_optional_artifact_passes(tmp_path: Path) -> None:
    def unlink(root: Path) -> None:
        (root / "review" / "repair-history.json").unlink()

    pair = build_pair(tmp_path, raw_replay=unlink, reseal_after_raw=True)
    proof = pair.attest()
    assert_passed(proof)


# ==== 21: extra semantic artifact fails ====


def test_21_extra_semantic_artifact_fails(tmp_path: Path) -> None:
    def add_extra(root: Path) -> None:
        (root / "candidate" / "README.alt.md").write_text(
            "# Alternate\n", encoding="utf-8", newline="\n"
        )

    pair = build_pair(tmp_path, raw_replay=add_extra, reseal_after_raw=True)
    proof = pair.attest()
    assert proof.passed is False
    assert "candidate/README.alt.md" in proof.replay_inventory.undeclared_semantic_paths


def test_21b_non_semantic_extra_file_passes(tmp_path: Path) -> None:
    def add_extra(root: Path) -> None:
        (root / "sha256sums.txt.tmp").write_text("scratch", encoding="utf-8", newline="\n")

    pair = build_pair(tmp_path, raw_replay=add_extra, reseal_after_raw=True)
    proof = pair.attest()
    assert_passed(proof)


# ==== 22: duplicate declaration fails ====


def test_22_duplicate_declaration_in_contract_raises() -> None:
    base = _golden_contract()
    payload = base.model_dump(mode="json")
    duplicate_artifact = dict(payload["artifacts"][0])
    duplicate_artifact["artifact_id"] = payload["artifacts"][1]["artifact_id"]
    payload["artifacts"].append(duplicate_artifact)
    with pytest.raises(pydantic.ValidationError):
        ReplayAttestationContractV1.model_validate(payload)


def test_22b_duplicate_declaration_in_bundle_fails(tmp_path: Path) -> None:
    def duplicate_line(root: Path) -> None:
        sums = root / "sha256sums.txt"
        lines = sums.read_text(encoding="utf-8").splitlines()
        manifest_line = next(line for line in lines if line.endswith("manifest.json"))
        lines.append(manifest_line.replace(manifest_line.split("  ")[0], "1" * 64))
        sums.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    pair = build_pair(tmp_path, raw_replay=duplicate_line, reseal_after_raw=False)
    proof = pair.attest()
    assert proof.passed is False
    assert proof.replay_inventory.duplicate_declared_paths != ()


# ==== 23-24: product effect ====


def test_23_product_effect_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["review/no-op-proof.json"]["patch_created"] = True

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert "commit" in proof.effect_delta.violated


def test_23b_duplicate_bundle_effect_fails(tmp_path: Path) -> None:
    def mutate(tree: dict[str, Any]) -> None:
        tree["review/no-op-proof.json"]["duplicate_bundle_created"] = True

    pair = build_pair(tmp_path, replay=mutate)
    proof = pair.attest()
    assert proof.passed is False
    assert "duplicate_lifecycle_effect" in proof.effect_delta.violated


def test_24_missing_effect_evidence_fails(tmp_path: Path) -> None:
    def strip_fields(tree: dict[str, Any]) -> None:
        del tree["review/no-op-proof.json"]["patch_created"]

    pair = build_pair(tmp_path, replay=strip_fields)
    proof = pair.attest()
    assert proof.passed is False
    assert "commit" in proof.effect_delta.unproven
    assert "commit" not in proof.effect_delta.proven_absent


# ==== 25-26: containment ====


def test_25_traversal_fails(tmp_path: Path) -> None:
    def traverse(root: Path) -> None:
        sums = root / "sha256sums.txt"
        lines = sums.read_text(encoding="utf-8").splitlines()
        lines.append(f"{'0' * 64}  ../t1/manifest.json")
        sums.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    pair = build_pair(tmp_path, raw_replay=traverse, reseal_after_raw=False)
    proof = pair.attest()
    assert proof.passed is False


def test_25b_traversal_in_contract_path_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        DeclaredArtifactV1(
            artifact_id="evil",
            relative_path="../t1/manifest.json",
            hash_mode="raw_sha256",
            kind="text",
            level="REQUIRED",
            stage="SOURCE",
        )


def test_26_escaping_symlink_containment_logic() -> None:
    # Leg 1: the containment predicate itself, exercised directly -- always available regardless
    # of platform symlink privileges.
    resolved = attestor._resolve_declared_path(Path("/does/not/exist"), "a/b.json")
    assert resolved is None


def test_26b_escaping_symlink_fails(tmp_path: Path) -> None:
    pair = build_pair(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    forged = outside / "final-verdict.json"
    forged.write_text(json.dumps({"verdict": "AGENT_APPROVED"}), encoding="utf-8", newline="\n")
    forged_before = forged.read_bytes()

    target = pair.replay_dir / "review" / "final-verdict.json"
    target.unlink()
    try:
        target.symlink_to(forged)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not available in this environment")

    _write_inventory(pair.replay_dir)
    proof = pair.attest()
    assert proof.passed is False
    assert forged.read_bytes() == forged_before


# ==== 27-28: determinism ====


def test_27_reordered_manifest_remains_deterministic(tmp_path: Path) -> None:
    ordered = build_pair(tmp_path / "a")

    def reorder(root: Path) -> None:
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        reversed_manifest = dict(reversed(list(manifest.items())))
        manifest_path.write_text(
            json.dumps(reversed_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    reordered = build_pair(tmp_path / "b", raw_replay=reorder, reseal_after_raw=True)

    ordered_bytes = (ordered.replay_dir / "manifest.json").read_bytes()
    reordered_bytes = (reordered.replay_dir / "manifest.json").read_bytes()
    assert ordered_bytes != reordered_bytes
    assert verify_sha256sums(reordered.replay_dir) is True

    p1 = ordered.attest()
    p2 = reordered.attest()
    assert_passed(p1)
    assert_passed(p2)
    assert p1.proof_hash == p2.proof_hash


def test_28_canonical_proof_hash_is_stable(tmp_path: Path) -> None:
    pair = build_pair(tmp_path)
    proof_a = pair.attest()
    proof_b = pair.attest()
    assert proof_a.proof_hash == proof_b.proof_hash
    assert proof_a.proof_hash == canonical_proof_hash(proof_a)

    def shuffle_contract(contract: ReplayAttestationContractV1) -> ReplayAttestationContractV1:
        return contract.model_copy(
            update={
                "artifacts": tuple(reversed(contract.artifacts)),
                "identity_bindings": tuple(reversed(contract.identity_bindings)),
                "product_effects": tuple(reversed(contract.product_effects)),
            }
        )

    shuffled_pair = build_pair(tmp_path / "shuffled", contract=shuffle_contract)
    proof_shuffled = shuffled_pair.attest()
    assert proof_shuffled.proof_hash == proof_a.proof_hash

    drifted_pair = build_pair(
        tmp_path / "drifted",
        replay=lambda tree: tree["facts/product-facts.json"]["product"].update(
            {"language": "rust"}
        ),
    )
    proof_drifted = drifted_pair.attest()
    assert proof_drifted.proof_hash != proof_a.proof_hash
    assert re.fullmatch(r"[0-9a-f]{64}", proof_drifted.proof_hash)


# ==== 29: no provider/pipeline/cache/product operation ====

_FORBIDDEN_STDLIB = {
    "subprocess",
    "socket",
    "ssl",
    "http",
    "urllib",
    "urllib3",
    "ftplib",
    "smtplib",
    "telnetlib",
    "multiprocessing",
    "shutil",
    "tempfile",
    "webbrowser",
    "pickle",
}
_FORBIDDEN_THIRD_PARTY = {
    "requests",
    "httpx",
    "aiohttp",
    "git",
    "github",
    "langchain_core",
    "langgraph",
}
_FORBIDDEN_FIRST_PARTY_PREFIXES = (
    "readme_agent.llm.",
    "readme_agent.capabilities.",
    "readme_agent.supervisor.",
    "readme_agent.gitsafety.",
    "readme_agent.state.",
    "readme_agent.specialists.",
    "readme_agent.orchestrator",
    "readme_agent.registry.",
)
_ALLOWED_FIRST_PARTY = {
    "readme_agent.evidence.file_inventory",
    "readme_agent.evidence.redaction",
    "readme_agent.evidence.writer",
    "readme_agent.llm.call_ledger",
    "readme_agent.llm.call_schema",
    "readme_agent.readme.document_hashing",
}


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


def test_29a_static_import_allowlist() -> None:
    module_path = Path(attestor.__file__)
    imports = _module_imports(module_path)
    forbidden_hits = {name for name in imports if name.split(".")[0] in _FORBIDDEN_STDLIB}
    assert not forbidden_hits, forbidden_hits
    third_party_hits = {name for name in imports if name.split(".")[0] in _FORBIDDEN_THIRD_PARTY}
    assert not third_party_hits, third_party_hits

    first_party = {name for name in imports if name.startswith("readme_agent.")}
    for name in first_party:
        if name in _ALLOWED_FIRST_PARTY:
            continue
        assert not name.startswith(_FORBIDDEN_FIRST_PARTY_PREFIXES), name

    source = module_path.read_text(encoding="utf-8")
    assert not re.search(r"\bopen\([^)]*['\"][wax]", source)
    assert ".write_text(" not in source
    assert ".write_bytes(" not in source
    assert "os.system(" not in source
    assert "subprocess" not in source


def test_29b_no_side_effects_at_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pair = build_pair(tmp_path)
    target_repo = tmp_path / "target-repo"
    target_repo.mkdir()
    (target_repo / "README.md").write_text("original\n", encoding="utf-8", newline="\n")

    before_first = _tree_snapshot(pair.first_dir)
    before_replay = _tree_snapshot(pair.replay_dir)
    before_target = _tree_snapshot(target_repo)
    cwd_before = Path.cwd()

    def boom(name: str):
        def _raise(*_args: object, **_kwargs: object) -> Any:
            raise AssertionError(f"attestor performed a forbidden operation: {name}")

        return _raise

    monkeypatch.setattr(socket, "socket", boom("socket.socket"))
    monkeypatch.setattr(socket, "create_connection", boom("socket.create_connection"))
    monkeypatch.setattr(subprocess, "run", boom("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", boom("subprocess.Popen"))
    monkeypatch.setattr(os, "system", boom("os.system"))
    real_open = Path.open

    def guarded_open(self: Path, mode: str = "r", *args: object, **kwargs: object) -> Any:
        if any(ch in mode for ch in "wax+"):
            raise AssertionError(f"attestor opened {self} for writing")
        return real_open(self, mode, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(Path, "write_text", boom("Path.write_text"))
    monkeypatch.setattr(Path, "write_bytes", boom("Path.write_bytes"))
    monkeypatch.setattr(Path, "unlink", boom("Path.unlink"))
    monkeypatch.setattr(os, "replace", boom("os.replace"))
    monkeypatch.setattr(os, "remove", boom("os.remove"))

    proof = pair.attest()
    assert_passed(proof)

    assert _tree_snapshot(pair.first_dir) == before_first
    assert _tree_snapshot(pair.replay_dir) == before_replay
    assert _tree_snapshot(target_repo) == before_target
    assert Path.cwd() == cwd_before


def test_29c_no_forbidden_module_objects_bound() -> None:
    bad = [
        name
        for name, value in vars(attestor).items()
        if isinstance(value, types.ModuleType)
        and (
            value.__name__.split(".")[0] in _FORBIDDEN_STDLIB
            or value.__name__.split(".")[0] in _FORBIDDEN_THIRD_PARTY
            or value.__name__.startswith(_FORBIDDEN_FIRST_PARTY_PREFIXES)
        )
    ]
    assert bad == []
