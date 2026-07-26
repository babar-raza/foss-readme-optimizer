"""Build the canonical live-like L8-027 accounting evidence bundle."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from readme_agent.capabilities.plan_readme_composition import execute as plan_composition
from readme_agent.capabilities.render_readme_candidate import execute as render_candidate
from readme_agent.evidence.manifest_v3 import RunManifestV3
from readme_agent.evidence.writer import (
    generate_run_id,
    refresh_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    current_llm_accounting_summary,
    current_llm_call_context,
    set_llm_stage,
    start_llm_call_accounting,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, repository_snapshot_scope
from readme_agent.specialists.independent_readme_review import (
    run_independent_readme_review,
)
from readme_agent.supervisor.portfolio import (
    PortfolioPocSummaryV1,
    PortfolioRepositoryResultV1,
)

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
REVISION = "8de5f467e93138b3605acdc46ca40e93f0364ee8"
SOURCE_BUNDLE = Path("runs") / "readme-poc" / "aspose-3d-foss__Aspose.3D-FOSS-for-Java" / REVISION
EVIDENCE_DIR = Path("plans/investigations/evidence/level8-llm-call-ledger")


def _load_json(relative: str) -> dict:
    value = json.loads((SOURCE_BUNDLE / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {SOURCE_BUNDLE / relative}")
    return value


def main() -> None:
    historical_manifest = _load_json("manifest.json")
    historical_status = historical_manifest.get("llm_accounting_status") or "UNKNOWN_LEGACY"
    if historical_status != "UNKNOWN_LEGACY":
        raise RuntimeError("historical 3D bundle unexpectedly claims exact LLM accounting")

    run_id = generate_run_id()
    start_llm_call_accounting(
        ORG_REPO,
        run_id,
        campaign_id="L8-TRUTH-01B-LLM-CALL-LEDGER",
        stage="AGENT_REVIEWING",
    )
    bind_llm_repository_revision(REVISION, stage="PLAN_READY")
    source_text = (SOURCE_BUNDLE / "source" / "README.md").read_text(encoding="utf-8")
    facts = _load_json("facts/product-facts.json")
    snapshot = RepositorySnapshotV1.model_validate(_load_json("source/revision.json"))
    with repository_snapshot_scope(snapshot, allow_local_fact_verification=False):
        composition_plan = plan_composition(ORG_REPO, product_facts_v2=facts)
        generated = render_candidate(
            ORG_REPO,
            product_facts_v2=facts,
            agentic_composition_plan=composition_plan,
        )
    generated_text = str(generated["final_text"])
    generated_hash = hashlib.sha256(generated_text.encode("utf-8")).hexdigest()
    historical_candidate_hash = str(historical_manifest["candidate_hash"])
    review = None
    if generated_hash == historical_candidate_hash:
        set_llm_stage("AGENT_REVIEWING")
        review = run_independent_readme_review(
            ORG_REPO,
            source_text,
            generated_text,
            _load_json("planning/presentation-plan.json"),
            _load_json("review/deterministic-validation.json"),
            product_facts_v2=facts,
        )
    summary = current_llm_accounting_summary()
    if summary.status != "EXACT" or not summary.provider_call_count:
        raise RuntimeError("representative live campaign produced no exact provider-call records")
    if summary.provider_call_count != len(summary.call_ids):
        raise RuntimeError("representative provider-call IDs do not reconcile")

    context = current_llm_call_context()
    assert context is not None
    source_ledger = Path(context.ledger_path)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_ledger, EVIDENCE_DIR / "representative-live-call-ledger.jsonl")

    write_redacted_json(
        EVIDENCE_DIR / "historical-3d-classification.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": REVISION,
            "source_manifest": str(SOURCE_BUNDLE / "manifest.json"),
            "classification": "UNKNOWN_LEGACY",
            "reason": (
                "The candidate predates transport-level call records. Its absent/default "
                "counter cannot establish zero provider calls."
            ),
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "representative-review-result.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": REVISION,
            "candidate_sha256": generated_hash,
            "historical_candidate_sha256": historical_candidate_hash,
            "byte_identical_to_historical_candidate": (generated_hash == historical_candidate_hash),
            "proof_scope": (
                "Transport-accounting proof only. This generated candidate predates full "
                "implementation of newer "
                "header, badge, visual, and contextual-link requirements and this verdict does "
                "not establish current Gate-A acceptance."
            ),
            "review": review,
        },
    )
    write_redacted_json(
        EVIDENCE_DIR / "representative-composition-plan.json",
        composition_plan,
    )
    write_redacted_text(
        EVIDENCE_DIR / "representative-generated-candidate.md",
        generated_text,
    )
    evidence_summary = summary.model_copy(
        update={"ledger_path": "representative-live-call-ledger.jsonl"}
    )
    write_redacted_json(EVIDENCE_DIR / "representative-call-summary.json", evidence_summary)
    manifest = RunManifestV3(
        run_id=run_id,
        org_repo=ORG_REPO,
        status="REPRESENTATIVE_REVIEW_COMPLETE",
        timestamp=datetime.now(UTC).isoformat(),
        upstream_revision=REVISION,
        llm_accounting_status="EXACT",
        llm_call_count=summary.provider_call_count,
        llm_calls=[job for job, count in summary.calls_by_job.items() for _ in range(count)],
        llm_call_ids=summary.call_ids,
        llm_calls_by_job=summary.calls_by_job,
        llm_fixture_call_count=summary.fixture_call_count,
        llm_cache_reuse_count=summary.cache_reuse_count,
        llm_prompt_tokens=summary.prompt_tokens,
        llm_completion_tokens=summary.completion_tokens,
        llm_total_tokens=summary.total_tokens,
        llm_ledger_path="representative-live-call-ledger.jsonl",
        llm_ledger_sha256=summary.ledger_sha256,
    )
    write_redacted_json(EVIDENCE_DIR / "representative-run-manifest.json", manifest)
    portfolio = PortfolioPocSummaryV1(
        registry_path="representative://L8-027",
        registry_count=1,
        results=[
            PortfolioRepositoryResultV1(
                org_repo=ORG_REPO,
                status="ACCOUNTING_PROOF_ONLY",
                exit_code=0,
                llm_accounting_status="EXACT",
                llm_call_count=summary.provider_call_count,
                llm_call_ids=summary.call_ids,
                llm_calls_by_job=summary.calls_by_job,
                llm_fixture_call_count=summary.fixture_call_count,
                llm_cache_reuse_count=summary.cache_reuse_count,
            )
        ],
    )
    write_redacted_json(EVIDENCE_DIR / "representative-portfolio-summary.json", portfolio)
    write_redacted_text(
        EVIDENCE_DIR / "reproduction.txt",
        (".venv/Scripts/python plans/investigations/tools/build_llm_call_ledger_evidence.py\n"),
    )
    refresh_sha256sums(EVIDENCE_DIR)


if __name__ == "__main__":
    main()
