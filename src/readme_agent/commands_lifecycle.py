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

    from readme_agent.state.git_backend import default_state_backend
    from readme_agent.state.health import build_health_report

    repositories = _selected_repositories(getattr(args, "only", None))
    report = build_health_report(
        default_state_backend(),
        repositories,
        expected_schedule_interval=timedelta(hours=args.expected_interval_hours),
        backlog_sla=timedelta(minutes=args.backlog_sla_minutes),
        repeated_failure_threshold=args.repeated_failure_threshold,
    )
    _emit_json(report.model_dump(mode="json"), getattr(args, "output", None))
    return 1 if args.fail_unhealthy and not report.healthy else 0
