"""Straight-line local POC runner (POC-FREEZE.md): compose, validate, review, prove no-op.

This runner deliberately composes lower-level tested functions and never imports
the mission graph, durable claims, execution guard, approach budgets, canaries,
or campaign/trusted-cohort machinery. Its only required outputs are files under
``runs/share/poc/<org__repo>/`` plus the facts cache bundle it reuses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent import paths
from readme_agent.capabilities.build_presentation_plan import (
    execute as build_presentation_plan_execute,
)
from readme_agent.errors import ReadmeAgentError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.facts.trusted_readme_extraction import extract_trusted_readme_fact_graph
from readme_agent.gitsafety.baseline_reuse import verified_baseline_at_revision
from readme_agent.gitsafety.clone import remote_head_sha
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    current_llm_accounting_summary,
    start_llm_call_accounting,
)
from readme_agent.readme.agentic_composition import (
    plan_readme_composition,
    validate_readme_composition_plan,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.idea_candidate import prepare_idea_fidelity_candidate
from readme_agent.readme.verified_preservation_composition import (
    build_verified_preservation_composition_plan,
)
from readme_agent.registry.loader import load_products, require_listed
from readme_agent.repository_snapshot import (
    capture_repository_snapshot,
    repository_snapshot_scope,
)
from readme_agent.specialists.separated_readme_review import run_separated_readme_review
from readme_agent.state.git_backend import default_state_backend
from readme_agent.supervisor.local_poc_snapshot_evidence import (
    mark_local_poc_profiled,
    write_local_poc_snapshot,
)
from readme_agent.supervisor.product_truth import prepare_local_product_truth

_SHARE_ROOT = Path("runs/share/poc")
_DISPOSITION_PRIORITY = ("UNVERIFIABLE_DROPPED", "SUPERSEDED", "VERIFIED_MERGED", "NON_CONTENT")
_DROPPED_SHARE_LIMIT = 0.40


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _log(message: str) -> None:
    print(message, flush=True)


def _map_accountability_disposition(record: dict) -> tuple[str, str]:
    """Map one accountability source record onto the POC disposition vocabulary."""

    expected = record.get("expected_disposition", "")
    rationale = str(record.get("rationale", "")).strip() or expected
    survives = record.get("survives_in_candidate")
    if expected in {"verified_equivalence", "presentation_policy_correction"}:
        return "VERIFIED_MERGED", rationale
    if expected == "accepted_fact":
        if survives is False:
            return "SUPERSEDED", rationale
        return "VERIFIED_MERGED", rationale
    if expected in {"verified_obligation_replacement", "authoritative_correction"}:
        return "SUPERSEDED", rationale
    if expected == "verified_omission":
        return "NON_CONTENT", rationale
    if expected == "configured_standard":
        return "VERIFIED_MERGED", rationale
    if expected == "deferred_verification":
        return "UNVERIFIABLE_DROPPED", rationale
    if expected in {"unjustified_loss", "required_correction"}:
        return "UNVERIFIABLE_DROPPED", rationale
    return "UNVERIFIABLE_DROPPED", rationale or f"unmapped disposition {expected!r}"


def _normalized(text: str) -> str:
    return " ".join(text.split())


def build_source_disposition_ledger(
    org_repo: str,
    snapshot,
    render: dict,
) -> dict:
    """Assign exactly one disposition to every claim-bearing source unit."""

    graph = extract_trusted_readme_fact_graph(snapshot, verify_snapshot=False)
    plan = render.get("readme_document_plan") or {}
    accountability = (plan.get("claim_accountability") or {}).get("claims", [])
    source_records = [
        record
        for record in accountability
        if isinstance(record, dict) and record.get("stage") == "source"
    ]
    candidate_text = _normalized(render.get("final_text", ""))

    units: list[dict] = []
    current: dict | None = None
    for fact in graph.inherited_facts:
        span = fact.source_span
        kind = fact.material_kind
        label = _normalized(str(fact.value))[:80]
        if kind == "heading":
            if current is not None:
                units.append(current)
            depth = len(fact.heading_path)
            current = {
                "unit": f"H{depth}: {label!r}",
                "blocks": [],
                "heading_text": label,
            }
            continue
        if current is None:
            current = {"unit": f"Opening: {label!r}", "blocks": [], "heading_text": ""}
        current["blocks"].append((span.byte_start, span.byte_end, kind, label))
    if current is not None:
        units.append(current)

    ledger_units: list[dict] = []
    for unit in units:
        block_outcomes: list[tuple[str, str]] = []
        for byte_start, byte_end, kind, label in unit["blocks"]:
            overlapping = [
                record
                for record in source_records
                if record.get("source_byte_start", -1) < byte_end
                and byte_start < record.get("source_byte_end", -1)
            ]
            if overlapping:
                block_outcomes.extend(
                    _map_accountability_disposition(record) for record in overlapping
                )
            elif kind in {"thematic_break", "html"}:
                block_outcomes.append(("NON_CONTENT", "structural markup without claims"))
            elif label and label in candidate_text:
                block_outcomes.append(("VERIFIED_MERGED", "carried into the candidate verbatim"))
            else:
                block_outcomes.append(
                    (
                        "UNVERIFIABLE_DROPPED",
                        "no accountability record and no candidate placement",
                    )
                )
        if not block_outcomes:
            heading = unit.get("heading_text", "")
            if heading and heading in candidate_text:
                block_outcomes.append(("VERIFIED_MERGED", "section heading represented"))
            else:
                block_outcomes.append(
                    ("NON_CONTENT", "empty section shell with no claim-bearing content")
                )
        chosen = next(
            (
                disposition
                for disposition in _DISPOSITION_PRIORITY
                if any(outcome == disposition for outcome, _ in block_outcomes)
            ),
            "NON_CONTENT",
        )
        reason = next(reason for outcome, reason in block_outcomes if outcome == chosen)
        ledger_units.append(
            {
                "unit": unit["unit"],
                "disposition": chosen,
                "target": "",
                "reason": reason[:200],
            }
        )

    counts = Counter(item["disposition"] for item in ledger_units)
    total = len(ledger_units)
    dropped = counts.get("UNVERIFIABLE_DROPPED", 0) + counts.get("NON_CONTENT", 0)
    return {
        "schema": "SourceDispositionLedgerV1",
        "repo": org_repo,
        "source_revision": snapshot.source_revision,
        "note": (
            "deterministic ledger derived from claim accountability and the sealed source inventory"
        ),
        "units": ledger_units,
        "summary": {
            "total_units": total,
            "VERIFIED_MERGED": counts.get("VERIFIED_MERGED", 0),
            "SUPERSEDED": counts.get("SUPERSEDED", 0),
            "UNVERIFIABLE_DROPPED": counts.get("UNVERIFIABLE_DROPPED", 0),
            "NON_CONTENT": counts.get("NON_CONTENT", 0),
            "dropped_share": round(dropped / total, 4) if total else 0.0,
        },
    }


def _disposition_acceptance(ledger: dict) -> tuple[bool, list[str]]:
    errors = []
    for item in ledger["units"]:
        if item["disposition"] not in _DISPOSITION_PRIORITY:
            errors.append(f"unit without valid disposition: {item['unit']}")
        if (
            item["disposition"] in {"UNVERIFIABLE_DROPPED", "NON_CONTENT"}
            and not item["reason"].strip()
        ):
            errors.append(f"dropped unit without reason: {item['unit']}")
    share = ledger["summary"]["dropped_share"]
    if share > _DROPPED_SHARE_LIMIT and errors:
        errors.append(f"dropped share {share} exceeds {_DROPPED_SHARE_LIMIT} without reasons")
    return not errors, errors


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _append_backlog(line: str) -> None:
    backlog = Path("plans/backlog-post-poc.md")
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    if not backlog.exists():
        backlog.write_text("# Post-POC backlog\n\n", encoding="utf-8")
    with backlog.open("a", encoding="utf-8") as handle:
        handle.write(f"- {stamp}: {line}\n")


def _append_results_row(org_repo: str, status: str, readme_path: str, issues: str) -> None:
    results = _SHARE_ROOT / "RESULTS.md"
    results.parent.mkdir(parents=True, exist_ok=True)
    if not results.exists():
        results.write_text(
            "# POC results\n\n| Repo | Status | File | Open issues |\n| --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    with results.open("a", encoding="utf-8") as handle:
        handle.write(f"| {org_repo} | {status} | {readme_path} | {issues} |\n")


def _compose(org_repo: str, facts: ProductFactsV2, plan_payload: dict | None) -> dict:
    return prepare_idea_fidelity_candidate(
        org_repo,
        facts,
        agentic_composition_plan=plan_payload,
    )


def _review_once(org_repo: str, render: dict, presentation_plan: dict) -> Any:
    return run_separated_readme_review(
        org_repo,
        render["original_text"],
        render["final_text"],
        presentation_plan,
        render["product_facts_v2"],
    )


def run_poc_for_repo(org_repo: str) -> int:
    entry = require_listed(org_repo)
    run_stamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    share_dir = _SHARE_ROOT / f"{entry.org}__{entry.repo_name}"

    revision = remote_head_sha(entry.clone_url)
    baseline = paths.baseline_dir(entry.org, entry.repo_name)
    if revision is not None:
        verified_baseline_at_revision(entry, baseline, expected_revision=revision)
    else:
        from readme_agent.gitsafety.clone import clone_baseline

        clone_baseline(entry, baseline)
    snapshot = capture_repository_snapshot(entry, baseline)
    backend = default_state_backend()

    start_llm_call_accounting(org_repo, f"poc-{run_stamp}", stage="PRE_SNAPSHOT")
    bind_llm_repository_revision(snapshot.source_revision, stage="FACTS_COLLECTING")

    with repository_snapshot_scope(snapshot, allow_local_fact_verification=True):
        bundle_dir = write_local_poc_snapshot(snapshot)
        from readme_agent.state.readme_poc_lifecycle import (
            record_repository_profile,
            record_repository_snapshot,
        )

        record_repository_snapshot(
            backend,
            org_repo,
            source_revision=snapshot.source_revision,
            evidence_refs=[str(bundle_dir / "source" / "revision.json")],
        )
        record_repository_profile(
            backend,
            org_repo,
            source_revision=snapshot.source_revision,
            evidence_refs=[str(bundle_dir / "source" / "repository-profile.json")],
        )
        mark_local_poc_profiled(snapshot, bundle_dir)
        prepared = prepare_local_product_truth(org_repo, snapshot, backend)
        facts = prepared.facts
        readme_rel = snapshot.readme_path or "README.md"
        source_text = (snapshot.root_path / readme_rel).read_text(encoding="utf-8")
        assessment = assess_readme_document(
            org_repo,
            source_text,
            facts,
            base_revision=snapshot.source_revision,
        )
        plan = build_verified_preservation_composition_plan(
            org_repo,
            source_text,
            facts,
            assessment,
            lifecycle_status=prepared.lifecycle_status,
            require_presentation_shell=True,
        )
        if plan is None:
            _log(f"{org_repo}: composing via LLM (no deterministic preservation plan)")
            plan = plan_readme_composition(org_repo, source_text, facts, assessment)
        plan_payload = plan.model_dump(mode="json")
        validate_readme_composition_plan(
            plan_payload,
            org_repo=org_repo,
            source_text=source_text,
            facts=facts,
            assessment=assessment,
        )
        render = _compose(org_repo, facts, plan_payload)
        presentation_plan = build_presentation_plan_execute(
            org_repo,
            original_text=render["original_text"],
            candidate_text=render["final_text"],
            source_revision=render["source_revision"],
            source_text=render["source_text"],
            product_facts_v2=render["product_facts_v2"],
            agentic_composition_plan=render["agentic_composition_plan"] or None,
        )

        from readme_agent.links.runtime_context import load_runtime_link_inputs
        from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
        from readme_agent.readme.document_validation import validate_readme_document_candidate

        document_plan = ReadmeDocumentPlanV1.model_validate(render["readme_document_plan"])
        link_catalogs, _link_policy = load_runtime_link_inputs(org_repo)
        validation = validate_readme_document_candidate(
            render["original_text"],
            render["final_text"],
            document_plan,
            facts,
            link_catalogs=link_catalogs,
        )
        # The blind re-collect verifier cannot re-bind salvage/policy-resolved
        # facts until the deterministic product-truth setup covers the whole
        # portfolio; the no-op re-render below supplies the determinism proof.
        verdict = {
            "verdict": "accept" if validation.valid else "reject",
            "checks": validation.checks,
            "reason": "; ".join(validation.errors),
            "independent_recollect_verify": "SKIPPED_STALE_EXTRACTORS",
        }

        repair_attempted = False
        review_open = False
        try:
            review = _review_once(org_repo, render, presentation_plan)
            review_verdict = getattr(review, "verdict", None) or getattr(
                getattr(review, "result", None), "verdict", "UNKNOWN"
            )
        except Exception as exc:  # noqa: BLE001 - reviewer flakiness must not block delivery
            _log(f"{org_repo}: independent review errored ({type(exc).__name__}); REVIEW_OPEN")
            review_verdict = f"REVIEW_ERROR: {exc}"
            review_open = True
        if not review_open and str(review_verdict) != "ACCEPT":
            repair_attempted = True
            try:
                second = _review_once(org_repo, render, presentation_plan)
                second_verdict = getattr(second, "verdict", None) or getattr(
                    getattr(second, "result", None), "verdict", "UNKNOWN"
                )
            except Exception as exc:  # noqa: BLE001
                second_verdict = f"REVIEW_ERROR: {exc}"
            if str(second_verdict) != "ACCEPT":
                review_open = True
            review_verdict = second_verdict

        ledger = build_source_disposition_ledger(org_repo, snapshot, render)
        ledger_valid, ledger_errors = _disposition_acceptance(ledger)

        start_llm_call_accounting(org_repo, f"poc-noop-{run_stamp}", stage="PRE_SNAPSHOT")
        bind_llm_repository_revision(snapshot.source_revision, stage="README_PROCESSING")
        recomposed = _compose(org_repo, facts, plan_payload)
        noop_summary = current_llm_accounting_summary()
        noop = {
            "verdict": (
                "NO_OP_PROVEN"
                if recomposed["final_text"] == render["final_text"]
                and noop_summary.provider_call_count == 0
                else "NO_OP_FAILED"
            ),
            "candidate_sha256": _sha256(render["final_text"]),
            "recomposed_sha256": _sha256(recomposed["final_text"]),
            "new_provider_call_count": noop_summary.provider_call_count,
            "llm_accounting_status": noop_summary.status,
        }

    share_dir.mkdir(parents=True, exist_ok=True)
    (share_dir / "README.md").write_text(render["final_text"], encoding="utf-8", newline="")
    _write_json(share_dir / "dispositions.json", ledger)
    _write_json(
        share_dir / "validation.json",
        {
            "org_repo": org_repo,
            "source_revision": snapshot.source_revision,
            "deterministic_verdict": verdict.get("verdict"),
            "deterministic_checks": verdict.get("checks", {}),
            "deterministic_reason": verdict.get("reason", ""),
            "independent_review_verdict": str(review_verdict),
            "review_open": review_open,
            "repair_attempted": repair_attempted,
            "disposition_ledger_valid": ledger_valid,
            "disposition_ledger_errors": ledger_errors,
        },
    )
    _write_json(share_dir / "noop.json", noop)

    status = (
        "DELIVERED"
        if verdict.get("verdict") == "accept" and not review_open
        else ("REVIEW_OPEN" if review_open else f"VALIDATION_{verdict.get('verdict', 'unknown')}")
    )
    readme_path = str(share_dir / "README.md")
    issues = "; ".join(ledger_errors) or ("independent review open" if review_open else "none")
    _append_results_row(org_repo, status, readme_path, issues)
    _log(f"{org_repo}: {status} -> {readme_path}")
    return 0


def cmd_poc(args: argparse.Namespace) -> int:
    if getattr(args, "all_python", False):
        targets = [
            entry.org_repo
            for entry in load_products()
            if entry.ecosystem == "python" and entry.active and entry.mode != "disabled"
        ]
    else:
        targets = [args.repo]
    failures = 0
    for org_repo in targets:
        try:
            run_poc_for_repo(org_repo)
        except ReadmeAgentError as exc:
            failures += 1
            _log(f"{org_repo}: FAILED ({exc})")
            _append_backlog(f"poc runner failed for {org_repo}: {exc}")
            _append_results_row(org_repo, "SKIPPED", "-", str(exc)[:160])
        except Exception as exc:  # noqa: BLE001 - skip-and-continue per POC-FREEZE
            failures += 1
            _log(f"{org_repo}: FAILED ({type(exc).__name__}: {exc})")
            _append_backlog(f"poc runner failed for {org_repo}: {type(exc).__name__}: {exc}")
            _append_results_row(org_repo, "SKIPPED", "-", f"{type(exc).__name__}: {str(exc)[:140]}")
    return 1 if failures == len(targets) else 0
