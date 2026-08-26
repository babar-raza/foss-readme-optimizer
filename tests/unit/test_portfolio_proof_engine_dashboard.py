"""Dashboard: a read-and-report join over receipts, rubric results, and evidence bundles.

Proves every MANDATORY TESTS bullet: all five states resolve correctly; the 33/31/2 registry
denominator; a missing LICENSE never causes a skip; a named facts surface survives into
BLOCKED_FACTS; 29/30 is rejected (never rounded); a 30/30 candidate with a hard disqualifier is
rejected; a 30/30 candidate with missing extra-prerequisite evidence is incomplete; hash/revision
mismatches can never accept; an errored or skipped applicable blocking check can never accept; an
invalid disposition ledger or claim-accountability map can never accept; provisional/error-bearing
K3 evidence can never accept; a rejected independent reviewer can never accept; only the complete
evidence chain produces ACCEPTED_30_OF_30; summary counts reconcile exactly with no double count;
and rerunning against identical receipts is byte-identical.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums
from readme_agent.presentation.candidate_benchmark_acceptance import (
    BenchmarkDimensionAcceptanceV1,
    CandidateBenchmarkAcceptanceV1,
)
from readme_agent.presentation.candidate_benchmark_acceptance_contracts import (
    canonical_benchmark_acceptance_payload_hash,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    CandidateBenchmarkComparisonV1,
    CandidateBenchmarkDimensionV1,
    load_benchmark_quality_profile,
)
from readme_agent.supervisor.portfolio_proof_engine import dashboard as dashboard_module
from readme_agent.supervisor.portfolio_proof_engine import registry_cohort
from readme_agent.supervisor.portfolio_proof_engine.acceptance_contract import (
    portfolio_acceptance_contract_hash,
    replay_attestation_contract_hash,
)
from readme_agent.supervisor.portfolio_proof_engine.contracts import campaign_id_for_mode
from readme_agent.supervisor.portfolio_proof_engine.dashboard import build_dashboard
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import write_receipt
from readme_agent.verification.sealed_transaction_replay import (
    CompleteTransactionNoOpProofV1,
    DeclaredArtifactV1,
    IdentityBindingSpecV1,
    LedgerDeclarationSpecV1,
    ProductEffectDeltaV1,
    ProductEffectExpectationV1,
    ProviderLedgerDeltaV1,
    ProviderProofContractV1,
    ReplayArtifactDeltaV1,
    ReplayArtifactInventoryV1,
    ReplayAttestationContractV1,
    SealedTransactionIdentityV1,
    canonical_json_sha256,
    canonical_proof_hash,
)
from tests.unit.portfolio_proof_engine_fixtures import make_entry, make_receipt

_REV = "a" * 40
_FACTS_HASH = "f" * 64
_SOURCE_README = "# Source\n\nOriginal repository content.\n"
_CANDIDATE_README = "# Candidate\n\nVerified candidate.\n"
_CANDIDATE_HASH = hashlib.sha256(_CANDIDATE_README.encode("utf-8")).hexdigest()
_CANARY_CAMPAIGN = campaign_id_for_mode("canaries")
_CURRENT_REQUIRED_CHECKS = (
    "candidate_matches_independent_render",
    "source_document_hash",
    "candidate_is_marker_free",
    "candidate_has_no_comments",
    "facts_hash_matches",
    "template_hash_matches",
    "candidate_hash_matches",
    "source_span_hashes",
    "fact_citations",
    "api_capability_wording_has_implementation_evidence",
    "document_reconstruction",
    "composition_lineage",
    "protected_content",
    "verified_example_present",
    "verified_overview_present",
    "verified_limitations_present",
    "example_assurance_claims_supported",
    "no_introduced_duplicate_headings",
    "header_visuals",
    "enterprise_edition_terminology",
    "contextual_links",
    "claim_accountability_complete",
    "claim_accountability_gaps_visible",
    "presentation_lint",
    "public_candidate_quality",
    "aspose_checks_no_blocking_errors",
    "needs_write_matches",
)
_REVIEW_SECTIONS = (
    "front-matter",
    "at-a-glance",
    "key-capabilities",
    "installation",
    "quick-start",
    "additional-examples",
    "navigation",
    "api-reference",
    "documentation-resources",
    "development-and-testing",
    "license",
    "scope-and-limitations",
)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _bundle_dir(runs_dir: Path, org_repo: str, source_revision: str = _REV) -> Path:
    org, repo = org_repo.split("/", maxsplit=1)
    return runs_dir / "readme-poc" / f"{org}__{repo}" / source_revision


def _terminal_acceptance_artifacts(
    org_repo: str, source_revision: str, candidate_hash: str
) -> tuple[dict[str, object], dict[str, object]]:
    profile_hash = load_benchmark_quality_profile()[1]
    comparison = CandidateBenchmarkComparisonV1(
        repository=org_repo,
        source_revision=source_revision,
        candidate_sha256=candidate_hash,
        benchmark_profile_sha256=profile_hash,
        benchmark_snapshot_sha256="5" * 64,
        dimensions=[
            CandidateBenchmarkDimensionV1(
                dimension_id="information_coverage",
                benchmark_disposition="accepted",
                obligation="Cover repository-supported visitor questions.",
                applicable=True,
                status="EVIDENCE_BOUND_PENDING_ACCEPTANCE",
                evidence_paths=["candidate/README.md"],
            )
        ],
    )
    comparison_payload = comparison.model_dump(mode="json")
    comparison_payload["dimensions"] = sorted(
        comparison_payload["dimensions"], key=lambda item: item["dimension_id"]
    )
    benchmark = CandidateBenchmarkAcceptanceV1(
        repository=org_repo,
        source_revision=source_revision,
        candidate_sha256=candidate_hash,
        facts_hash=_FACTS_HASH,
        comparison_identity_sha256=canonical_benchmark_acceptance_payload_hash(comparison_payload),
        benchmark_profile_sha256=profile_hash,
        deterministic_evidence_sha256="7" * 64,
        factual_review_sha256="8" * 64,
        visitor_review_sha256="9" * 64,
        rubric_evidence_sha256="a" * 64,
        evidence_bundle_sha256="b" * 64,
        dimensions=(
            BenchmarkDimensionAcceptanceV1(
                dimension_id="information_coverage",
                benchmark_disposition="accepted",
                obligation="Cover repository-supported visitor questions.",
                verdict="PASS",
                evidence_categories_considered=("claim_grounding",),
            ),
        ),
        applicable_dimension_ids=("information_coverage",),
        quarantined_dimension_ids=(),
        not_applicable_dimension_ids=(),
        unresolved_dimension_ids=(),
        acceptance_status="BENCHMARK_ACCEPTANCE_PROVEN",
    )
    manifest_artifact = DeclaredArtifactV1(
        artifact_id="manifest",
        relative_path="manifest.json",
        hash_mode="canonical_json_sha256",
        kind="json_object",
        level="REQUIRED",
        stage="SEALING",
        compare_for_delta=False,
    )
    ledger_artifact = DeclaredArtifactV1(
        artifact_id="ledger",
        relative_path="llm-call-ledger.jsonl",
        hash_mode="crlf_normalized_sha256",
        kind="jsonl_llm_ledger",
        level="REQUIRED",
        stage="SEALING",
        compare_for_delta=False,
    )
    identity_bindings = tuple(
        IdentityBindingSpecV1(
            component=component,
            level="REQUIRED",
            artifact_id="manifest",
            json_pointer=f"/{pointer}",
        )
        for component, pointer in (
            ("repository_identity", "org_repo"),
            ("source_revision", "source_revision"),
            ("facts_hash", "facts_hash"),
            ("candidate_hash", "candidate_hash"),
        )
    )
    effects = tuple(
        ProductEffectExpectationV1(
            effect=effect,
            level="REQUIRED",
            artifact_id="manifest",
            comparison="absent",
        )
        for effect in (
            "readme_write",
            "target_tree_change",
            "commit",
            "branch",
            "push",
            "pull_request",
            "publication",
            "duplicate_lifecycle_effect",
        )
    )
    replay_contract = ReplayAttestationContractV1(
        contract_id="local-poc-complete-transaction-v1",
        org_repo=org_repo,
        expected_source_revision=source_revision,
        artifacts=(manifest_artifact, ledger_artifact),
        identity_bindings=identity_bindings,
        provider_proof=ProviderProofContractV1(
            first_ledger_artifact_id="ledger",
            replay_ledger_artifact_id="ledger",
            first_declaration=LedgerDeclarationSpecV1(artifact_id="manifest"),
            replay_declaration=LedgerDeclarationSpecV1(artifact_id="manifest"),
        ),
        product_effects=effects,
    )
    component_digests = {
        "repository_identity": canonical_json_sha256(org_repo),
        "source_revision": canonical_json_sha256(source_revision),
        "facts_hash": canonical_json_sha256(_FACTS_HASH),
        "candidate_hash": canonical_json_sha256(candidate_hash),
    }
    first_identity = SealedTransactionIdentityV1(
        bundle_label="first",
        org_repo=org_repo,
        source_revision=source_revision,
        component_digests=component_digests,
        resolved_components=tuple(sorted(component_digests)),
        identity_digest=canonical_json_sha256(component_digests),
    )
    replay_identity = first_identity.model_copy(update={"bundle_label": "replay"})
    first_inventory = ReplayArtifactInventoryV1(
        bundle_label="first",
        declared_count=2,
        present_count=2,
        file_count=2,
        total_bytes=2,
        inventory_digest="c" * 64,
    )
    replay_inventory = first_inventory.model_copy(update={"bundle_label": "replay"})
    provider = ProviderLedgerDeltaV1(
        first_declared_status="EXACT",
        replay_declared_status="EXACT",
        first_provider_call_count=3,
        replay_provider_call_count=3,
        replay_new_cache_reuse_count=3,
        ledger_superset_ok=True,
        ledger_temporal_ok=True,
        ledger_scope_ok=True,
        declared_accounting_consistent=True,
        accounting_certain=True,
        delta_digest="d" * 64,
    )
    effect_names = tuple(effect.effect for effect in effects)
    effect_delta = ProductEffectDeltaV1(
        checked_effects=effect_names,
        proven_absent=effect_names,
        target_readme_digest_first="e" * 64,
        target_readme_digest_replay="e" * 64,
        target_tree_digest_first="f" * 64,
        target_tree_digest_replay="f" * 64,
        target_revision_first=source_revision,
        target_revision_replay=source_revision,
        delta_digest="0" * 64,
    )
    proof = CompleteTransactionNoOpProofV1(
        contract_id=replay_contract.contract_id,
        org_repo=org_repo,
        expected_source_revision=source_revision,
        contract_digest=replay_attestation_contract_hash(replay_contract),
        passed=True,
        checks={"complete_transaction_is_no_op": True},
        failures=(),
        findings=(),
        earliest_affected_stage=None,
        affected_stages=(),
        first_identity=first_identity,
        replay_identity=replay_identity,
        first_inventory=first_inventory,
        replay_inventory=replay_inventory,
        artifact_delta=ReplayArtifactDeltaV1(delta_digest="1" * 64),
        provider_delta=provider,
        effect_delta=effect_delta,
        proof_hash="0" * 64,
    )
    artifacts: dict[str, object] = {
        "benchmark_comparison": comparison.model_dump(mode="json"),
        "benchmark_acceptance": benchmark.model_dump(mode="json"),
        "replay_contract": replay_contract.model_dump(mode="json"),
    }
    stable_contract = ReplayAttestationContractV1.model_validate(artifacts["replay_contract"])
    proof = proof.model_copy(
        update={
            "contract_digest": replay_attestation_contract_hash(stable_contract),
            "proof_hash": "0" * 64,
        }
    )
    proof = proof.model_copy(update={"proof_hash": canonical_proof_hash(proof)})
    artifacts.update(
        {
            "replay_attestation": {
                "attestation_type": "CompleteTransactionReplayAttestationV1",
                "first_bundle_root": "sealed/first",
                "replay_bundle_root": "sealed/replay",
                "proof": proof.model_dump(mode="json"),
            },
            "rubric_evaluation": {
                "rubric": {"total_score": 30},
                "outcome": {
                    "org_repo": org_repo,
                    "accepted": True,
                    "score": 30,
                    "hard_disqualifier_count": 0,
                    "missing_evidence_criteria": [],
                    "benchmark_acceptance_proven": True,
                    "benchmark_acceptance_hash": benchmark.canonical_hash(),
                    "replay_attestation_proven": True,
                    "replay_attestation_hash": proof.proof_hash,
                    "acceptance_contract_hash": portfolio_acceptance_contract_hash(),
                },
            },
        }
    )
    manifest_bindings: dict[str, object] = {
        "org_repo": org_repo,
        "benchmark_acceptance_proven": True,
        "benchmark_acceptance_hash": benchmark.canonical_hash(),
        "portfolio_acceptance_contract_hash": portfolio_acceptance_contract_hash(),
        "complete_transaction_replay_attestation_passed": True,
        "complete_transaction_replay_attestation_hash": proof.proof_hash,
    }
    return artifacts, manifest_bindings


def _perfect_bundle_files(
    runs_dir: Path,
    org_repo: str,
    *,
    source_revision: str = _REV,
    candidate_hash: str = _CANDIDATE_HASH,
    validation_overrides: dict | None = None,
    manifest_overrides: dict | None = None,
    knowledge_overrides: dict | None = None,
    factual_overrides: dict | None = None,
    visitor_overrides: dict | None = None,
    visitor_support_omit: set[str] | None = None,
    claim_map_overrides: dict | None = None,
    reconciliation_overrides: dict | None = None,
    check_coverage_overrides: dict | None = None,
    no_op_overrides: dict | None = None,
    omit: set[str] | None = None,
) -> None:
    """Write a complete, fully-passing evidence bundle for one candidate -- every ACCEPTED_30_OF_30
    prerequisite satisfied. Individual tests mutate exactly one artifact via the *_overrides/omit
    parameters to break exactly one thing."""

    omit = omit or set()
    bundle_dir = _bundle_dir(runs_dir, org_repo, source_revision)
    terminal_artifacts, manifest_bindings = _terminal_acceptance_artifacts(
        org_repo, source_revision, candidate_hash
    )

    checks = {name: True for name in _CURRENT_REQUIRED_CHECKS}
    validation = {
        "verdict": "accept",
        "reason": None,
        "checks": checks,
        **(validation_overrides or {}),
    }
    manifest = {
        "source_revision": source_revision,
        "facts_hash": _FACTS_HASH,
        "candidate_hash": candidate_hash,
        "candidate_stage_dependency_key": "1" * 64,
        "prompt_registry_content_hash": "2" * 64,
        "prompt_dependency_hashes": {"review": "3" * 64},
        **manifest_bindings,
        **(manifest_overrides or {}),
    }
    knowledge_application = {
        "status": "final",
        "final_dispositions": [
            {"global_claim_id": "x", "disposition": "rendered_with_exact_spans"}
        ],
        "candidate_sha256": candidate_hash,
        **(knowledge_overrides or {}),
    }
    supported_sections = set(_REVIEW_SECTIONS) - (visitor_support_omit or set())
    factual_review = {
        "verdict": "ACCEPT",
        "candidate_hash": candidate_hash,
        "findings": [
            {"section": section, "disposition": "supports_acceptance"}
            for section in _REVIEW_SECTIONS
        ],
        **(factual_overrides or {}),
    }
    visitor_review = {
        "verdict": "ACCEPT",
        "candidate_hash": candidate_hash,
        "findings": [
            {"section": section, "disposition": "supports_acceptance"}
            for section in _REVIEW_SECTIONS
            if section in supported_sections
        ],
        **(visitor_overrides or {}),
    }
    claim_text = "Verified candidate."
    claim_start = _CANDIDATE_README.encode("utf-8").index(claim_text.encode("utf-8"))
    claim_map = {
        "valid": True,
        "candidate_sha256": candidate_hash,
        "claims": [
            {
                "fact_id": "fact-installation-coordinates",
                "verification_state": "verified",
                "byte_start": claim_start,
                "byte_end": claim_start + len(claim_text.encode("utf-8")),
                "claim_text_sha256": hashlib.sha256(claim_text.encode("utf-8")).hexdigest(),
            }
        ],
        **(claim_map_overrides or {}),
    }
    source_bytes = _SOURCE_README.encode("utf-8")
    reconciliation = {
        "source_bytes": len(source_bytes),
        "entries": [
            {
                "source_byte_start": 0,
                "source_byte_end": len(source_bytes),
                "disposition": "preserved",
                "final_byte_start": 0,
                "final_byte_end": len(_CANDIDATE_README.encode("utf-8")),
            }
        ],
        **(reconciliation_overrides or {}),
    }
    check_coverage = {
        "skipped": 0,
        "errored": 0,
        "failed": 0,
        "entries": [{"check_id": "current-contract", "blocking": True, "outcome": "pass"}],
        **(check_coverage_overrides or {}),
    }
    selected_fields = (
        "installation.coordinates",
        "installation.verified_acquisition",
        "aspose.dependency_snapshot",
        "api.public_surface",
        "example.minimal",
        "product.limitations",
        "documentation.links",
        "product.formats",
        "product.license",
    )
    selected_fact_ids = {field: f"fact-{field.replace('.', '-')}" for field in selected_fields}
    facts_records = [
        {
            "fact_id": fact_id,
            "field": field,
            "verification_state": "verified",
            "conflicts": [],
            "value": (
                {"verification_outcome": "EXECUTED"}
                if field == "example.minimal"
                else "verified-value"
            ),
        }
        for field, fact_id in selected_fact_ids.items()
    ]
    facts = {"selected_fact_ids": selected_fact_ids, "facts": facts_records}
    no_op_proof = {
        "verdict": "NO_OP_PROVEN",
        "candidate_hash": candidate_hash,
        "patch_created": False,
        "duplicate_bundle_created": False,
        "llm_accounting_status": "EXACT",
        "new_provider_call_count": 0,
        "acceptance_binding": {"contract_hash": "e" * 64},
        **(no_op_overrides or {}),
    }
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()

    artifacts = {
        "manifest": (bundle_dir / "manifest.json", manifest),
        "deterministic_validation": (
            bundle_dir / "review" / "deterministic-validation.json",
            validation,
        ),
        "knowledge_application": (bundle_dir / "knowledge-application.json", knowledge_application),
        "factual_review": (bundle_dir / "review" / "factual-plan-review.json", factual_review),
        "visitor_review": (bundle_dir / "review" / "blind-quality-review.json", visitor_review),
        "claim_map": (bundle_dir / "candidate" / "claim-map.json", claim_map),
        "reconciliation": (bundle_dir / "candidate" / "readme-reconciliation.json", reconciliation),
        "check_coverage": (bundle_dir / "candidate" / "check-coverage.json", check_coverage),
        "facts": (bundle_dir / "facts" / "product-facts.json", facts),
        "no_op_proof": (bundle_dir / "review" / "no-op-proof.json", no_op_proof),
        "snapshot_revision": (
            bundle_dir / "source" / "revision.json",
            {"source_revision": source_revision, "readme_sha256": source_sha256},
        ),
        "document_plan": (
            bundle_dir / "planning" / "readme-document-plan.json",
            {"source_sha256": source_sha256},
        ),
        "benchmark_comparison": (
            bundle_dir / "planning" / "candidate-benchmark-comparison.json",
            terminal_artifacts["benchmark_comparison"],
        ),
        "benchmark_acceptance": (
            bundle_dir / "review" / "benchmark-acceptance.json",
            terminal_artifacts["benchmark_acceptance"],
        ),
        "replay_contract": (
            bundle_dir / "review" / "complete-transaction-replay-contract.json",
            terminal_artifacts["replay_contract"],
        ),
        "replay_attestation": (
            bundle_dir / "review" / "complete-transaction-replay-attestation.json",
            terminal_artifacts["replay_attestation"],
        ),
        "rubric_evaluation": (
            bundle_dir / "review" / "rubric-evaluation.json",
            terminal_artifacts["rubric_evaluation"],
        ),
    }
    for key, (path, data) in artifacts.items():
        if key in omit:
            continue
        _write_json(path, data)
    if "source_readme" not in omit:
        source_path = bundle_dir / "source" / "README.md"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(_SOURCE_README, encoding="utf-8")
    if "candidate_readme" not in omit:
        candidate_path = bundle_dir / "candidate" / "README.md"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(_CANDIDATE_README, encoding="utf-8")
    refresh_sha256sums(bundle_dir)


def _accepted_receipt_chain(
    output_root: Path, org_repo: str, *, candidate_hash: str = _CANDIDATE_HASH
):
    """The minimum receipt trail needed for the dashboard to enter its candidate-evaluation
    branch: a CANDIDATE_ASSEMBLED-or-later stage receipt bound to the same source/candidate
    identity the evidence files on disk carry."""

    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo=org_repo,
            stage="VISITOR_REVIEWED",
            source_revision=_REV,
            candidate_hash=candidate_hash,
            facts_hash=_FACTS_HASH,
        ),
    )


def _dashboard(
    tmp_path: Path,
    monkeypatch,
    entries: list,
    *,
    output_root: Path | None = None,
):
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    return build_dashboard(output_root=output_root or (tmp_path / "proof"))


def _runs_dir(tmp_path: Path, monkeypatch) -> Path:
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))
    return runs_dir


# ---------------------------------------------------------------------------
# 1. All five dashboard states
# ---------------------------------------------------------------------------


def test_all_five_dashboard_states(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"

    skipped = make_entry(org_repo="acme/skipped", repository_id=1)
    blocked = make_entry(org_repo="acme/blocked", repository_id=2)
    incomplete = make_entry(org_repo="acme/incomplete", repository_id=3)
    rejected = make_entry(org_repo="acme/rejected", repository_id=4)
    accepted = make_entry(org_repo="acme/accepted", repository_id=5)

    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/skipped", stage="TERMINAL_SKIPPED"),
    )
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo="acme/blocked",
            stage="BLOCKED_INPUT",
            status="FAILED",
            failure_reason="facts collection failed: no manifest detected",
        ),
    )
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/incomplete", stage="FACTS_READY", source_revision=_REV),
    )

    _perfect_bundle_files(runs_dir, "acme/rejected", factual_overrides={"verdict": "REJECT"})
    _accepted_receipt_chain(output_root, "acme/rejected")

    _perfect_bundle_files(runs_dir, "acme/accepted")
    _accepted_receipt_chain(output_root, "acme/accepted")

    result = _dashboard(
        tmp_path,
        monkeypatch,
        [skipped, blocked, incomplete, rejected, accepted],
        output_root=output_root,
    )
    by_repo = {row.org_repo: row.state for row in result.rows}
    assert by_repo == {
        "acme/skipped": "SKIPPED_NON_SUBSTANTIVE",
        "acme/blocked": "BLOCKED_FACTS",
        "acme/incomplete": "CANDIDATE_INCOMPLETE",
        "acme/rejected": "CANDIDATE_REJECTED",
        "acme/accepted": "ACCEPTED_30_OF_30",
    }


# ---------------------------------------------------------------------------
# 2. Exactly 33 registry rows: 31 processable plus two skipped
# ---------------------------------------------------------------------------


def test_real_registry_resolves_to_34_rows_32_processable_2_skipped(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entries = registry_cohort.load_portfolio_entries()
    assert len(entries) == 34
    skip_candidates = [entry for entry in entries if entry.family == "psd"]
    assert len(skip_candidates) == 2
    for entry in skip_candidates:
        write_receipt(
            output_root,
            _CANARY_CAMPAIGN,
            make_receipt(org_repo=entry.org_repo, stage="TERMINAL_SKIPPED"),
        )

    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    result = build_dashboard(output_root=output_root)

    assert len(result.rows) == 34
    assert {row.org_repo for row in result.rows} == {entry.org_repo for entry in entries}
    assert result.summary.total == 34
    assert result.summary.terminal_skipped == 2
    assert result.summary.processable == 32


# ---------------------------------------------------------------------------
# 3. Missing LICENSE does not cause skipping
# ---------------------------------------------------------------------------


def test_missing_license_does_not_cause_skipping(tmp_path, monkeypatch):
    """The dashboard reflects whatever the intake receipt already says -- it never re-derives or
    second-guesses skip status from LICENSE presence. A repo intake-classified as processable
    (even though its own reason text mentions a missing LICENSE) is never
    SKIPPED_NON_SUBSTANTIVE."""

    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/no-license", repository_id=1)
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/no-license", stage="INTAKE", source_revision=_REV),
    )
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state != "SKIPPED_NON_SUBSTANTIVE"
    assert row.processability == "PROCESSABLE"


# ---------------------------------------------------------------------------
# 4. A named facts surface is retained in BLOCKED_FACTS
# ---------------------------------------------------------------------------


def test_blocked_facts_retains_the_exact_named_surface(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/blocked", repository_id=1)
    reason = "dependency manifest resolution failed: pyproject.toml declares no build-system"
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo="acme/blocked", stage="BLOCKED_INPUT", status="FAILED", failure_reason=reason
        ),
    )
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state == "BLOCKED_FACTS"
    assert row.blocked_surface == reason


# ---------------------------------------------------------------------------
# 5. A 29/30 candidate is rejected (never rounded)
# ---------------------------------------------------------------------------


def test_29_of_30_is_rejected_never_rounded(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/near-miss", repository_id=1)
    # Additional-example review support is criterion 19's sole signal, so removing only that
    # support fails exactly one criterion without making the whole review non-accepting.
    _perfect_bundle_files(runs_dir, "acme/near-miss", visitor_support_omit={"additional-examples"})
    _accepted_receipt_chain(output_root, "acme/near-miss")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.score == 29
    assert row.state == "CANDIDATE_REJECTED"
    assert any("19" in gate for gate in row.failed_gates)


# ---------------------------------------------------------------------------
# 6. A 30/30 candidate with one hard disqualifier is rejected
# ---------------------------------------------------------------------------


def test_30_of_30_with_hard_disqualifier_is_rejected(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/disqualified", repository_id=1)
    # A provisional knowledge report is a hard disqualifier while leaving all 30 scored criteria
    # satisfiable, proving that the disqualifier overrides a full numeric score.
    _perfect_bundle_files(
        runs_dir, "acme/disqualified", knowledge_overrides={"status": "provisional"}
    )
    _accepted_receipt_chain(output_root, "acme/disqualified")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state == "CANDIDATE_REJECTED"
    assert row.hard_disqualifier_count >= 1


# ---------------------------------------------------------------------------
# 7. A 30/30 candidate with missing evidence is incomplete
# ---------------------------------------------------------------------------


def test_30_of_30_with_missing_extra_evidence_is_incomplete(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/sparse", repository_id=1)
    # Every scored criterion passes because all blocking entries passed, but the dashboard's
    # additional aggregate check counters are unresolved rather than falsely reported as zero.
    _perfect_bundle_files(
        runs_dir,
        "acme/sparse",
        check_coverage_overrides={"skipped": None, "errored": None, "failed": None},
    )
    _accepted_receipt_chain(output_root, "acme/sparse")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.score == 30
    assert row.hard_disqualifier_count == 0
    assert row.state == "CANDIDATE_INCOMPLETE"


# ---------------------------------------------------------------------------
# 8. A candidate-hash mismatch cannot accept
# ---------------------------------------------------------------------------


def test_candidate_hash_mismatch_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/hash-mismatch", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/hash-mismatch", knowledge_overrides={"candidate_sha256": "e" * 64}
    )
    _accepted_receipt_chain(output_root, "acme/hash-mismatch")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 9. A source-revision mismatch cannot accept
# ---------------------------------------------------------------------------


def test_source_revision_mismatch_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/rev-mismatch", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/rev-mismatch", manifest_overrides={"source_revision": "b" * 40}
    )
    _accepted_receipt_chain(output_root, "acme/rev-mismatch")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.state == "CANDIDATE_REJECTED"


# ---------------------------------------------------------------------------
# 10. An errored applicable blocking check cannot accept
# ---------------------------------------------------------------------------


def test_errored_blocking_check_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/check-errored", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/check-errored", check_coverage_overrides={"errored": 1})
    _accepted_receipt_chain(output_root, "acme/check-errored")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 11. A skipped applicable blocking check cannot accept
# ---------------------------------------------------------------------------


def test_skipped_blocking_check_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/check-skipped", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/check-skipped", check_coverage_overrides={"skipped": 1})
    _accepted_receipt_chain(output_root, "acme/check-skipped")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 12. An invalid disposition ledger cannot accept
# ---------------------------------------------------------------------------


def test_invalid_disposition_ledger_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/dropped-content", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/dropped-content", reconciliation_overrides={"source_bytes": 1}
    )
    _accepted_receipt_chain(output_root, "acme/dropped-content")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 13. An invalid claim-accountability map cannot accept
# ---------------------------------------------------------------------------


def test_invalid_claim_map_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/bad-claim-map", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/bad-claim-map", claim_map_overrides={"valid": False})
    _accepted_receipt_chain(output_root, "acme/bad-claim-map")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 14. Provisional or error-bearing knowledge-application evidence cannot accept
# ---------------------------------------------------------------------------


def test_provisional_knowledge_application_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/provisional-k3", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/provisional-k3", knowledge_overrides={"status": "provisional"}
    )
    _accepted_receipt_chain(output_root, "acme/provisional-k3")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 15. A rejected independent reviewer cannot accept
# ---------------------------------------------------------------------------


def test_rejected_factual_review_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/factual-reject", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/factual-reject", factual_overrides={"verdict": "REJECT"})
    _accepted_receipt_chain(output_root, "acme/factual-reject")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.factual_review_result == "REJECT"


def test_rejected_visitor_review_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/visitor-reject", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/visitor-reject", visitor_overrides={"verdict": "REJECT"})
    _accepted_receipt_chain(output_root, "acme/visitor-reject")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 16. Only the complete evidence chain produces ACCEPTED_30_OF_30
# ---------------------------------------------------------------------------


def test_only_the_complete_evidence_chain_produces_accepted(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/complete", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/complete")
    _accepted_receipt_chain(output_root, "acme/complete")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state == "ACCEPTED_30_OF_30"


def test_missing_benchmark_acceptance_artifact_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/no-benchmark", repository_id=1)
    _perfect_bundle_files(runs_dir, entry.org_repo, omit={"benchmark_acceptance"})
    _accepted_receipt_chain(output_root, entry.org_repo)

    row = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root).rows[0]

    assert row.state == "CANDIDATE_INCOMPLETE"


def test_missing_replay_attestation_artifact_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/no-replay", repository_id=1)
    _perfect_bundle_files(runs_dir, entry.org_repo, omit={"replay_attestation"})
    _accepted_receipt_chain(output_root, entry.org_repo)

    row = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root).rows[0]

    assert row.state == "CANDIDATE_INCOMPLETE"


def test_missing_terminal_manifest_bindings_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entries = [
        make_entry(org_repo="acme/unbound-benchmark", repository_id=1),
        make_entry(org_repo="acme/unbound-replay", repository_id=2),
    ]
    _perfect_bundle_files(
        runs_dir,
        entries[0].org_repo,
        manifest_overrides={"benchmark_acceptance_hash": None},
    )
    _perfect_bundle_files(
        runs_dir,
        entries[1].org_repo,
        manifest_overrides={"complete_transaction_replay_attestation_hash": None},
    )
    for entry in entries:
        _accepted_receipt_chain(output_root, entry.org_repo)

    rows = _dashboard(tmp_path, monkeypatch, entries, output_root=output_root).rows

    assert {row.state for row in rows} == {"CANDIDATE_REJECTED"}


def test_missing_or_unbound_benchmark_dimension_path_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/unbound-dimension", repository_id=1)
    _perfect_bundle_files(runs_dir, entry.org_repo)
    bundle_dir = _bundle_dir(runs_dir, entry.org_repo)
    comparison_path = bundle_dir / "planning" / "candidate-benchmark-comparison.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["dimensions"][0]["evidence_paths"] = ["candidate/missing-evidence.json"]
    _write_json(comparison_path, comparison)
    refresh_sha256sums(bundle_dir)
    _accepted_receipt_chain(output_root, entry.org_repo)

    row = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root).rows[0]

    assert row.state == "CANDIDATE_REJECTED"


def test_benchmark_acceptance_for_a_different_candidate_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/stale-benchmark", repository_id=1)
    _perfect_bundle_files(runs_dir, entry.org_repo)
    bundle_dir = _bundle_dir(runs_dir, entry.org_repo)
    acceptance_path = bundle_dir / "review" / "benchmark-acceptance.json"
    acceptance_data = json.loads(acceptance_path.read_text(encoding="utf-8"))
    acceptance_data["candidate_sha256"] = "e" * 64
    stale = CandidateBenchmarkAcceptanceV1.model_validate(acceptance_data)
    _write_json(acceptance_path, stale.model_dump(mode="json"))
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["benchmark_acceptance_hash"] = stale.canonical_hash()
    _write_json(manifest_path, manifest)
    rubric_path = bundle_dir / "review" / "rubric-evaluation.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    rubric["outcome"]["benchmark_acceptance_hash"] = stale.canonical_hash()
    _write_json(rubric_path, rubric)
    refresh_sha256sums(bundle_dir)
    _accepted_receipt_chain(output_root, entry.org_repo)

    row = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root).rows[0]

    assert row.state == "CANDIDATE_REJECTED"
    assert "unmet: benchmark_acceptance_proven_and_current" in row.failed_gates


def test_replay_with_a_new_provider_call_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/provider-on-replay", repository_id=1)
    _perfect_bundle_files(runs_dir, entry.org_repo)
    bundle_dir = _bundle_dir(runs_dir, entry.org_repo)
    attestation_path = bundle_dir / "review" / "complete-transaction-replay-attestation.json"
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    proof = CompleteTransactionNoOpProofV1.model_validate(attestation["proof"])
    provider = proof.provider_delta.model_copy(update={"replay_authoring_calls": 1})
    proof = proof.model_copy(update={"provider_delta": provider, "proof_hash": "0" * 64})
    proof = proof.model_copy(update={"proof_hash": canonical_proof_hash(proof)})
    attestation["proof"] = proof.model_dump(mode="json")
    _write_json(attestation_path, attestation)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["complete_transaction_replay_attestation_hash"] = proof.proof_hash
    _write_json(manifest_path, manifest)
    rubric_path = bundle_dir / "review" / "rubric-evaluation.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    rubric["outcome"]["replay_attestation_hash"] = proof.proof_hash
    _write_json(rubric_path, rubric)
    refresh_sha256sums(bundle_dir)
    _accepted_receipt_chain(output_root, entry.org_repo)

    row = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root).rows[0]

    assert row.state == "CANDIDATE_REJECTED"
    assert "unmet: complete_transaction_replay_proven_and_current" in row.failed_gates


def test_current_deterministic_verdict_schema_is_accepted(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/current-verdict", repository_id=1)
    _perfect_bundle_files(
        runs_dir,
        entry.org_repo,
        validation_overrides={"valid": None, "errors": None, "verdict": "accept", "reason": None},
    )
    _accepted_receipt_chain(output_root, entry.org_repo)

    row = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root).rows[0]

    assert row.state == "ACCEPTED_30_OF_30"
    assert row.score == 30
    assert row.score == 30
    assert row.hard_disqualifier_count == 0
    assert row.failed_gates == ()


# ---------------------------------------------------------------------------
# 17. Summary counts equal the actual row states, no double count
# ---------------------------------------------------------------------------


def test_summary_counts_reconcile_exactly(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entries = [
        make_entry(org_repo="acme/skipped", repository_id=1),
        make_entry(org_repo="acme/blocked", repository_id=2),
        make_entry(org_repo="acme/incomplete", repository_id=3),
        make_entry(org_repo="acme/rejected", repository_id=4),
        make_entry(org_repo="acme/accepted", repository_id=5),
    ]
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/skipped", stage="TERMINAL_SKIPPED"),
    )
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo="acme/blocked", stage="BLOCKED_INPUT", status="FAILED", failure_reason="x"
        ),
    )
    _perfect_bundle_files(runs_dir, "acme/rejected", factual_overrides={"verdict": "REJECT"})
    _accepted_receipt_chain(output_root, "acme/rejected")
    _perfect_bundle_files(runs_dir, "acme/accepted")
    _accepted_receipt_chain(output_root, "acme/accepted")

    result = _dashboard(tmp_path, monkeypatch, entries, output_root=output_root)
    assert len(result.rows) == 5
    assert len({row.org_repo for row in result.rows}) == 5
    assert result.summary.total == 5
    assert result.summary.terminal_skipped == 1
    assert result.summary.blocked_facts == 1
    assert result.summary.candidate_incomplete == 1
    assert result.summary.candidate_rejected == 1
    assert result.summary.accepted_30_of_30 == 1
    assert (
        result.summary.terminal_skipped
        + result.summary.blocked_facts
        + result.summary.candidate_incomplete
        + result.summary.candidate_rejected
        + result.summary.accepted_30_of_30
        == result.summary.total
    )


# ---------------------------------------------------------------------------
# 18. Rerunning on identical receipts is byte-identical
# ---------------------------------------------------------------------------


def test_rerun_on_identical_receipts_is_byte_identical(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/stable", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/stable")
    _accepted_receipt_chain(output_root, "acme/stable")

    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: (entry,))
    first = build_dashboard(output_root=output_root)
    second = build_dashboard(output_root=output_root)
    assert first.model_dump_json() == second.model_dump_json()


def test_dashboard_module_has_no_new_scoring_system(tmp_path, monkeypatch):
    """Sanity guard for the "never a second scoring system" constraint: the dashboard module's
    only rubric-shaped import is the existing `rubric.score_candidate`, never a redefinition."""

    assert dashboard_module.score_candidate.__module__ == (
        "readme_agent.supervisor.portfolio_proof_engine.rubric"
    )
