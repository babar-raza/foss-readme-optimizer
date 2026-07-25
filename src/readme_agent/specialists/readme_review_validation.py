"""Dispatch and materialize deterministic README review gates."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent import paths
from readme_agent.capabilities.dispatcher import DispatchResult, dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.evidence.writer import write_readme_proposal_bundle
from readme_agent.registry.loader import require_listed

_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def dispatch_verify_readme_candidate(org_repo: str, render_result: dict) -> DispatchResult:
    """Run the independent deterministic candidate verifier."""

    return dispatch_tool_call(
        {
            "function": {
                "name": "verify_readme_candidate",
                "arguments": json.dumps(
                    {
                        "org_repo": org_repo,
                        "facts_hash": render_result["facts_hash"],
                        "fresh_fingerprint": render_result["fresh_fingerprint"],
                        "status": render_result["status"],
                        "needs_write": render_result["needs_write"],
                        "final_text": render_result["final_text"],
                    }
                ),
            }
        },
        _READ_ONLY_PERMISSIONS,
        caller_domain=INDEPENDENT_VERIFICATION,
        extra_kwargs={
            "agentic_composition_plan": render_result.get("agentic_composition_plan"),
        },
    )


def dispatch_build_presentation_plan(org_repo: str, render_result: dict) -> DispatchResult:
    """Build a source-bound plan from independently re-derived facts."""

    return dispatch_tool_call(
        {
            "function": {
                "name": "build_presentation_plan",
                "arguments": json.dumps({"org_repo": org_repo}),
            }
        },
        _READ_ONLY_PERMISSIONS,
        caller_domain=README_PRESENTATION,
        extra_kwargs={
            "original_text": render_result["original_text"],
            "source_text": render_result.get("source_text", render_result["original_text"]),
            "candidate_text": render_result["final_text"],
            "source_revision": render_result["source_revision"],
            "product_facts_v2": render_result.get("product_facts_v2"),
            "agentic_composition_plan": render_result.get("agentic_composition_plan"),
        },
    )


def presentation_plan_record(presentation_plan: dict) -> dict:
    """Remove the large raw patch from the durable plan record."""

    return {
        **presentation_plan,
        "git_patch_proof": {
            key: value
            for key, value in presentation_plan["git_patch_proof"].items()
            if key != "patch"
        },
    }


def materialize_and_verify_bundle(
    org_repo: str,
    render_result: dict,
    presentation_plan: dict,
    *,
    run_id: str,
) -> tuple[dict, Path]:
    """Write and independently reconstruct one proposal bundle."""

    entry = require_listed(org_repo)
    bundle_dir = paths.readme_proposal_bundle_dir(entry.org, entry.repo_name, run_id)
    write_readme_proposal_bundle(
        bundle_dir,
        original_readme=render_result["original_text"],
        candidate_readme=render_result["final_text"],
        patch_text=str(presentation_plan["git_patch_proof"].get("patch") or ""),
        product_facts_v2=render_result["product_facts_v2"],
        readme_assessment_v1=presentation_plan["readme_assessment"],
        agentic_composition_plan_v1=render_result.get("agentic_composition_plan"),
        readme_document_plan_v1=presentation_plan["readme_document_plan"],
        claim_map_v1=presentation_plan["claim_map"],
        repository_presentation_plan_v1=presentation_plan.get("presentation_plan") or {},
        document_validation=presentation_plan.get("document_validation") or {},
    )
    dispatch = dispatch_tool_call(
        {
            "function": {
                "name": "verify_readme_proposal_bundle",
                "arguments": json.dumps({"bundle_dir": str(bundle_dir)}),
            }
        },
        _READ_ONLY_PERMISSIONS,
        caller_domain=INDEPENDENT_VERIFICATION,
    )
    if dispatch.outcome != "executed" or dispatch.result is None:
        return (
            {
                "status": "dispatch_failed",
                "verified": False,
                "failures": [f"{dispatch.outcome}:{dispatch.error}"],
                "bundle_dir": str(bundle_dir),
            },
            bundle_dir,
        )
    return (
        {"status": "checked", "bundle_dir": str(bundle_dir), **dispatch.result},
        bundle_dir,
    )
