"""CLI handlers for the durable production matrix, recovery, and health surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from readme_agent.registry.loader import load_products, require_listed


def _selected_repositories(only: str | None) -> list[str]:
    entries = load_products()
    if not only:
        return sorted(entry.org_repo for entry in entries if entry.active)
    selected = sorted({item.strip() for item in only.split(",") if item.strip()})
    for org_repo in selected:
        require_listed(org_repo)
    return selected


def _emit_json(payload: object, output: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def cmd_runtime_matrix(args: argparse.Namespace) -> int:
    """Emit the single authoritative active-repository Actions matrix."""

    selected = set(_selected_repositories(getattr(args, "only", None)))
    entries = [
        {
            "repo": entry.org_repo,
            "owner": entry.org,
            "name": entry.repo_name,
            "mode": entry.mode,
            "ecosystem": entry.ecosystem or "unknown",
        }
        for entry in load_products()
        if entry.active and entry.org_repo in selected
    ]
    _emit_json({"include": entries}, getattr(args, "output", None))
    return 0


def cmd_registry_preflight(args: argparse.Namespace) -> int:
    """Reconcile discovery and intake before a workflow freezes its matrix."""

    from readme_agent.state.git_backend import default_state_backend
    from readme_agent.supervisor.registry_revision_preflight import prepare_registry_revision

    result = prepare_registry_revision(
        Path(args.registry),
        default_state_backend(),
        heal_enabled=not args.no_refresh,
        force_refresh=args.force_refresh,
        act_fixture_inventory=args.act_fixture_inventory,
    )
    _emit_json(result.model_dump(mode="json"), getattr(args, "output", None))
    return 0 if result.gate.eligible else 1


def cmd_qualified_cohort_matrix(args: argparse.Namespace) -> int:
    """Emit a checksum- and contract-validated frozen trusted cohort matrix."""

    from readme_agent.supervisor.trusted_cohort_runtime import (
        load_runtime_trusted_cohort,
        runtime_trusted_cohort_matrix,
    )

    cohort = load_runtime_trusted_cohort(Path(args.manifest))
    _emit_json(runtime_trusted_cohort_matrix(cohort), getattr(args, "output", None))
    return 0


def cmd_restore_qualified_cohort(args: argparse.Namespace) -> int:
    """Restore exact ACT proof inputs into isolated local runtime/state paths."""

    from readme_agent.supervisor.trusted_cohort_restore import (
        restore_trusted_cohort_act_inputs,
    )
    from readme_agent.supervisor.trusted_cohort_runtime import load_runtime_trusted_cohort

    cohort = load_runtime_trusted_cohort(Path(args.manifest))
    result = restore_trusted_cohort_act_inputs(
        cohort,
        input_manifest_path=Path(args.input_manifest),
        runtime_root=Path(args.runtime_root),
        state_remote=Path(args.state_remote),
    )
    _emit_json(result, getattr(args, "output", None))
    return 0


def cmd_recovery_sweep(args: argparse.Namespace) -> int:
    """Mark expired unfinished lifecycle records retryable and report them."""

    from readme_agent.state.git_backend import default_state_backend
    from readme_agent.state.recovery import recovery_sweep

    repositories = _selected_repositories(getattr(args, "only", None))
    candidates = recovery_sweep(
        default_state_backend(),
        repositories,
        stale_after_seconds=args.stale_after_seconds,
    )
    _emit_json(
        {
            "repositories_checked": len(repositories),
            "recovery_candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        },
        getattr(args, "output", None),
    )
    return 0


def cmd_health_report(args: argparse.Namespace) -> int:
    """Render HealthReportV1 from durable state without hiding read failures."""

    from datetime import timedelta

    from readme_agent.registry.revision_gate import evaluate_registry_revision
    from readme_agent.registry.revision_store import load_current_registry_revision
    from readme_agent.state.git_backend import default_state_backend
    from readme_agent.state.health import build_health_report

    revision = load_current_registry_revision()
    if revision is None:
        registry_health = {
            "eligible": False,
            "reasons": ["registry_revision_missing"],
        }
    else:
        products = json.loads(Path("data/products.json").read_text(encoding="utf-8"))
        registry_health = evaluate_registry_revision(revision, products).model_dump(mode="json")

    repositories = _selected_repositories(getattr(args, "only", None))
    workflow_failures: list[dict[str, str]] = []
    for item in getattr(args, "upstream_job_result", []):
        job, separator, result = item.partition("=")
        if not separator or not job or not result:
            raise ValueError("--upstream-job-result must use JOB=RESULT")
        if result in {"failure", "cancelled"}:
            workflow_failures.append({"job": job, "result": result})
    report = build_health_report(
        default_state_backend(),
        repositories,
        expected_schedule_interval=timedelta(hours=args.expected_interval_hours),
        backlog_sla=timedelta(minutes=args.backlog_sla_minutes),
        repeated_failure_threshold=args.repeated_failure_threshold,
        registry_revision_health=registry_health,
        workflow_failures=workflow_failures,
    )
    _emit_json(report.model_dump(mode="json"), getattr(args, "output", None))
    return 1 if args.fail_unhealthy and not report.healthy else 0
