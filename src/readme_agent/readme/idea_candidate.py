"""Prepare an idea-faithful README candidate from one immutable repository view."""

from __future__ import annotations

from contextlib import nullcontext

from readme_agent import paths
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.gitsafety.hooks import install_pre_push_hook
from readme_agent.gitsafety.neuter import neuter_push
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.inspection.file_inventory import scan
from readme_agent.orchestrator import require_permitted
from readme_agent.readme.candidate_workspace import ensure_work_clone
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.facts import compute_tracked_content_hash
from readme_agent.repository_snapshot import (
    capture_repository_snapshot,
    current_repository_snapshot,
    repository_snapshot_scope,
    verify_repository_snapshot,
)


def prepare_idea_fidelity_candidate(org_repo: str) -> dict:
    """Build a deterministic proposal; never write its candidate to the work clone."""

    entry = require_permitted(org_repo)
    snapshot = current_repository_snapshot(org_repo)
    owns_snapshot = snapshot is None
    if snapshot is None:
        baseline = paths.baseline_dir(entry.org, entry.repo_name)
        clone_baseline(entry, baseline)
        snapshot = capture_repository_snapshot(entry, baseline)
    scope = (
        repository_snapshot_scope(snapshot, allow_local_fact_verification=True)
        if owns_snapshot
        else nullcontext(snapshot)
    )
    with scope:
        verify_repository_snapshot(snapshot)
        facts_result = collect_product_facts(org_repo)
        facts = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
        source_readme = (
            snapshot.root_path / snapshot.readme_path
            if snapshot.readme_path is not None
            else snapshot.root_path / "README.md"
        )
        source_text = source_readme.read_text(encoding="utf-8") if source_readme.exists() else ""
        fresh_fingerprint = compute_tracked_content_hash(snapshot.root_path)

        work_path = paths.work_dir(entry.org, entry.repo_name)
        ensure_work_clone(
            entry,
            snapshot.root_path,
            work_path,
            fresh_fingerprint=fresh_fingerprint,
        )
        neuter_push(work_path)
        install_pre_push_hook(work_path)
        proof = verify_push_blocked(work_path)
        if not proof.ok:
            raise RuntimeError(f"push-block verification failed, aborting: {proof.detail}")
        inventory = scan(work_path)
        work_readme = inventory.readme_path or (work_path / "README.md")
        original_text = work_readme.read_text(encoding="utf-8") if work_readme.exists() else ""

        final_text, document_plan = build_readme_document_candidate(
            org_repo,
            source_text,
            facts,
            base_revision=snapshot.source_revision,
        )
        needs_write = final_text != original_text
        return {
            "facts_hash": facts.canonical_hash(),
            "source_revision": snapshot.source_revision,
            "fresh_fingerprint": fresh_fingerprint,
            "skip_regeneration": not needs_write,
            "needs_write": needs_write,
            "original_text": original_text,
            "source_text": source_text,
            "final_text": final_text,
            "status": "GENERATED" if needs_write else "COMPLIANT_NO_CHANGE",
            "llm_called": False,
            "llm_calls": [],
            "readme_document_plan": document_plan.model_dump(mode="json"),
        }
