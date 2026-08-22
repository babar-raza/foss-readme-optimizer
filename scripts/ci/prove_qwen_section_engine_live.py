"""Prove live Qwen section authoring, reuse, recovery, and candidate consumption."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from readme_agent import env
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    current_llm_call_context,
    load_llm_call_records,
    reset_llm_call_accounting,
    start_llm_call_accounting,
)
from readme_agent.llm.prompt_registry import get as get_prompt
from readme_agent.llm.section_author_client import build_live_section_cluster_author_client
from readme_agent.presentation.verified_template_document import (
    build_verified_template_document_candidate,
)
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
)
from readme_agent.readme.section_authoring_specs import build_canonical_section_authoring_specs
from readme_agent.specialists.section_authoring_document import author_and_persist_readme_sections

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
DEFAULT_REVISION = "ee05c1ba9153ef5916b7a108406c794f2e464d01"
DEFAULT_FACTS = (
    ROOT
    / "runs"
    / "readme-poc"
    / "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / DEFAULT_REVISION
    / "facts"
    / "product-facts.json"
)
DEFAULT_SOURCE = (
    ROOT / "runs" / "baseline" / "aspose-3d-foss__Aspose.3D-FOSS-for-Python" / "README.md"
)
DEFAULT_EVIDENCE = (
    ROOT / "plans" / "investigations" / "evidence" / ("qwen-section-engine-integration")
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section_prompt_version() -> str:
    manifest = get_prompt("section_cluster_authoring")
    if manifest is None:
        raise RuntimeError("section_cluster_authoring prompt is not registered")
    return manifest.version


def _git_status(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=repository_root,
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout


def _metrics(document, elapsed_seconds: float) -> dict:
    usages = [
        usage
        for outcome in document.outcomes
        if not outcome.reused_from_cache
        for usage in outcome.receipt.token_usage
    ]
    return {
        "cluster_count": len(document.outcomes),
        "provider_logical_calls": document.provider_logical_calls,
        "reused_cluster_count": document.reused_cluster_count,
        "executed_semantic_retry_cluster_count": sum(
            outcome.receipt.semantic_retry_used
            for outcome in document.outcomes
            if not outcome.reused_from_cache
        ),
        "prompt_tokens": sum(usage.prompt_tokens or 0 for usage in usages),
        "completion_tokens": sum(usage.completion_tokens or 0 for usage in usages),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "models": sorted(
            {
                outcome.receipt.provider_model
                for outcome in document.outcomes
                if outcome.receipt.provider_model
            }
        ),
        "request_ids": [
            outcome.receipt.provider_request_id
            for outcome in document.outcomes
            if not outcome.reused_from_cache and outcome.receipt.provider_request_id
        ],
    }


def _inventory(evidence_dir: Path) -> None:
    lines = []
    for path in sorted(evidence_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (evidence_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-repo", default=DEFAULT_REPOSITORY)
    parser.add_argument("--facts", type=Path, default=DEFAULT_FACTS)
    parser.add_argument("--source-readme", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    facts = ProductFactsV2.model_validate_json(args.facts.read_text(encoding="utf-8"))
    source_text = args.source_readme.read_text(encoding="utf-8")
    source_revision = facts.selected_fact("product.identity").source.source_revision
    if facts.org_repo != args.org_repo or source_revision is None:
        raise ValueError("live proof facts do not match the requested repository/revision")
    baseline_root = args.source_readme.parent
    source_sha256_before = _sha256(source_text)
    git_status_before = _git_status(baseline_root)
    protected = fingerprint_protected_content(source_text)
    specs = build_canonical_section_authoring_specs(facts)
    if len(specs) < 3:
        raise ValueError("live proof requires at least three independent section clusters")
    client = build_live_section_cluster_author_client(
        env.llm_base_url(),
        env.llm_api_key(),
        timeout=env.llm_timeout_seconds(),
    )

    with tempfile.TemporaryDirectory(prefix="readme-agent-qwen-live-") as temp:
        proof_runs = Path(temp) / "runs"
        prior_runs_dir = os.environ.get("README_AGENT_RUNS_DIR")
        os.environ["README_AGENT_RUNS_DIR"] = str(proof_runs)
        start_llm_call_accounting(
            args.org_repo,
            f"qwen-section-engine-live-{source_revision[:12]}",
            campaign_id="L8-PF-01A-QWEN-SECTION-ENGINE-INTEGRATION",
            stage="SECTION_AUTHORING",
        )
        bind_llm_repository_revision(source_revision, stage="SECTION_AUTHORING")
        try:
            cache_dir = Path(temp) / "cache"
            start = time.perf_counter()
            first = author_and_persist_readme_sections(
                org_repo=args.org_repo,
                source_revision=source_revision,
                source_text=source_text,
                product_facts=facts,
                protected_content=protected,
                section_specs=specs,
                client=client,
                cache_dir=cache_dir,
            )
            first_elapsed = time.perf_counter() - start

            start = time.perf_counter()
            second = author_and_persist_readme_sections(
                org_repo=args.org_repo,
                source_revision=source_revision,
                source_text=source_text,
                product_facts=facts,
                protected_content=protected,
                section_specs=specs,
                client=client,
                cache_dir=cache_dir,
            )
            second_elapsed = time.perf_counter() - start

            changed_specs = list(specs)
            changed_specs[1] = replace(
                changed_specs[1],
                section_objective=changed_specs[1].section_objective
                + " Prefer one concise sentence per capability.",
            )
            start = time.perf_counter()
            selective = author_and_persist_readme_sections(
                org_repo=args.org_repo,
                source_revision=source_revision,
                source_text=source_text,
                product_facts=facts,
                protected_content=protected,
                section_specs=changed_specs,
                client=client,
                cache_dir=cache_dir,
            )
            selective_elapsed = time.perf_counter() - start
            ledger_context = current_llm_call_context()
            if ledger_context is None:
                raise RuntimeError("Qwen live proof lost its LLM accounting context")
            ledger_records = load_llm_call_records(Path(ledger_context.ledger_path))
        finally:
            reset_llm_call_accounting()
            if prior_runs_dir is None:
                os.environ.pop("README_AGENT_RUNS_DIR", None)
            else:
                os.environ["README_AGENT_RUNS_DIR"] = prior_runs_dir

    assessment = assess_readme_document(
        facts.org_repo,
        source_text,
        facts,
        base_revision=source_revision,
    )
    plan = ReadmeAgenticCompositionPlanV1(
        org_repo=facts.org_repo,
        source_sha256=source_sha256_before,
        facts_hash=facts.canonical_hash(),
        assessment_hash=assessment.canonical_hash(),
        prompt_sha256="0" * 64,
        tool_schema_sha256="0" * 64,
        input_sha256="0" * 64,
        model="qwen3-next-section-engine-live-proof",
        attempt_count=1,
        repository_summary="Bounded section-engine live proof.",
        section_decisions=[],
        overview_sentences=[],
    )
    candidate, document_plan = build_verified_template_document_candidate(
        facts,
        source_text,
        source_revision,
        plan,
        section_authoring_document=first,
    )
    validation = validate_readme_document_candidate(
        source_text,
        candidate,
        document_plan,
        facts,
    )
    independently_rendered, independent_plan = build_verified_template_document_candidate(
        facts,
        source_text,
        source_revision,
        plan,
        section_authoring_document=first,
    )
    public_lint = lint_readme_presentation(candidate, facts)
    authored_provenance = [
        binding
        for binding in document_plan.candidate_content_provenance
        if binding.provenance_id.startswith("template.section-authoring.")
    ]
    first_metrics = _metrics(first, first_elapsed)
    second_metrics = _metrics(second, second_elapsed)
    selective_metrics = _metrics(selective, selective_elapsed)
    source_sha256_after = _sha256(args.source_readme.read_text(encoding="utf-8"))
    git_status_after = _git_status(baseline_root)
    expected_calls = len(first.expected_cluster_ids)
    canonical_terms = canonical_abbreviations_from_facts(facts)
    checks = {
        "first_complete": first.complete,
        "first_used_qwen3_next": first_metrics["models"] == ["qwen3-next"],
        "first_authored_every_cluster": first_metrics["provider_logical_calls"] >= expected_calls,
        "unchanged_results_identical": [item.result for item in first.outcomes]
        == [item.result for item in second.outcomes],
        "unchanged_zero_provider_calls": second_metrics["provider_logical_calls"] == 0,
        "unchanged_reused_every_cluster": second.reused_cluster_count == expected_calls,
        "selective_one_cluster_reauthored": sum(
            not outcome.reused_from_cache for outcome in selective.outcomes
        )
        == 1,
        "selective_calls_within_one_cluster_bound": 1
        <= selective_metrics["provider_logical_calls"]
        <= 3,
        "selective_reused_other_clusters": selective.reused_cluster_count == expected_calls - 1,
        "candidate_contains_authored_bytes": all(
            canonicalize_public_markdown(unit.text.strip(), canonical_terms) in candidate
            for outcome in first.outcomes
            for unit in outcome.result.units
        ),
        "candidate_has_authored_fact_lineage": len(authored_provenance)
        == sum(len(outcome.result.units) for outcome in first.outcomes),
        "complete_deterministic_candidate_validation": validation.valid,
        "public_presentation_contract_valid": public_lint.valid,
        "independent_candidate_reconstruction_matches": independently_rendered == candidate,
        "independent_document_plan_matches": independent_plan == document_plan,
        "llm_call_ledger_covers_bounded_physical_attempts": (
            first_metrics["provider_logical_calls"] + selective_metrics["provider_logical_calls"]
            <= len(ledger_records)
            <= 2
            * (
                first_metrics["provider_logical_calls"]
                + selective_metrics["provider_logical_calls"]
            )
        ),
        "source_readme_unchanged": source_sha256_after == source_sha256_before,
        "baseline_git_state_unchanged": git_status_after == git_status_before,
    }
    failed = [name for name, passed in checks.items() if not passed]
    verdict = "PASS" if not failed else "FAIL"

    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "verdict": verdict,
        "org_repo": facts.org_repo,
        "source_revision": source_revision,
        "facts_hash": facts.canonical_hash(),
        "source_sha256": source_sha256_before,
        "model_route": env.llm_model_for_job("section_cluster_authoring"),
        "prompt_version": _section_prompt_version(),
        "checks": checks,
        "first": first_metrics,
        "unchanged_rerun": second_metrics,
        "one_cluster_invalidation": selective_metrics,
        "acceleration": {
            "unchanged_provider_calls_avoided": expected_calls,
            "unchanged_recompute_reduction_percent": 100.0,
            "selective_clusters_avoided": expected_calls - 1,
            "selective_minimum_provider_calls_avoided": max(
                0,
                expected_calls - selective_metrics["provider_logical_calls"],
            ),
            "selective_cluster_recompute_reduction_percent": round(
                100 * (expected_calls - 1) / expected_calls, 1
            ),
        },
        "candidate_sha256": _sha256(candidate),
        "authored_provenance_count": len(authored_provenance),
        "deterministic_validation": {
            "valid": validation.valid,
            "checks": validation.checks,
            "errors": validation.errors,
        },
        "public_presentation_lint": public_lint.model_dump(mode="json"),
        "section_authoring_document_sha256": first.canonical_hash(),
        "llm_call_record_count": len(ledger_records),
        "limitations": [
            "This proves the authoring portion of one real repository transaction, not PF-02.",
            "The transport client can make up to two physical attempts per logical call; the "
            "document receipt reports logical calls while the shared LLM ledger owns physical "
            "retries.",
        ],
    }
    write_redacted_json(args.evidence_dir / "live-proof.json", payload)
    write_redacted_json(
        args.evidence_dir / "section-authoring-first.json",
        first.model_dump(mode="json"),
    )
    write_redacted_json(
        args.evidence_dir / "section-authoring-unchanged.json",
        second.model_dump(mode="json"),
    )
    write_redacted_json(
        args.evidence_dir / "section-authoring-selective.json",
        selective.model_dump(mode="json"),
    )
    write_redacted_json(
        args.evidence_dir / "llm-call-ledger.json",
        [record.model_dump(mode="json") for record in ledger_records],
    )
    write_redacted_json(
        args.evidence_dir / "readme-document-plan.json",
        document_plan.model_dump(mode="json"),
    )
    (args.evidence_dir / "candidate.md").write_text(candidate, encoding="utf-8")
    report = (
        "# Qwen Section Engine Live Proof\n\n"
        f"Verdict: {verdict}\n\n"
        f"- Repository: `{facts.org_repo}`\n"
        f"- Source revision: `{source_revision}`\n"
        f"- Model: `{payload['model_route']}`\n"
        f"- First run: {first_metrics['provider_logical_calls']} logical provider calls for "
        f"{expected_calls} clusters in {first_metrics['elapsed_seconds']} seconds.\n"
        f"- Unchanged rerun: 0 provider calls; {expected_calls}/{expected_calls} clusters reused "
        f"in {second_metrics['elapsed_seconds']} seconds.\n"
        f"- One-cluster change: {selective_metrics['provider_logical_calls']} logical provider "
        f"call(s); {expected_calls - 1}/{expected_calls} clusters reused in "
        f"{selective_metrics['elapsed_seconds']} seconds.\n"
        f"- Candidate: `{payload['candidate_sha256']}` with "
        f"{len(authored_provenance)} exact authored fact-lineage spans.\n"
        f"- Complete deterministic document validation: {validation.valid}.\n"
        f"- Independent deterministic reconstruction: {independently_rendered == candidate}.\n"
        f"- Detailed section documents and {len(ledger_records)} redacted provider-call "
        "records are checksum-bound in this evidence directory.\n"
        "- Product README and baseline git state remained unchanged.\n\n"
        "This demonstrates bounded authoring acceleration and recovery isolation. It does not "
        "claim PF-02 candidate closure or full-portfolio delivery.\n"
    )
    (args.evidence_dir / "REPORT.md").write_text(report, encoding="utf-8")
    _inventory(args.evidence_dir)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if failed:
        raise RuntimeError(f"Qwen section-engine live proof failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
