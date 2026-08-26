"""CLI handler for `readme-agent portfolio-proof` -- the five resumable portfolio proof engine
modes (preflight, facts-only, canaries, fleet, failed-only). Thin argument plumbing only: all
real logic lives in `supervisor/portfolio_proof_engine/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from readme_agent.evidence.writer import write_redacted_json
from readme_agent.supervisor.portfolio_proof_engine.dashboard import (
    PortfolioDashboardV1,
    build_dashboard,
)
from readme_agent.supervisor.portfolio_proof_engine.deadline import DeadlineBudget
from readme_agent.supervisor.portfolio_proof_engine.mode_shared import ModePassResultV1
from readme_agent.supervisor.portfolio_proof_engine.provider_concurrency import (
    DEFAULT_MAX_PROVIDER_CONCURRENCY,
)
from readme_agent.supervisor.portfolio_proof_engine.registry_cohort import (
    filter_entries,
    load_portfolio_entries,
    resolve_fleet_remaining,
    resolve_seven_canaries,
)

DASHBOARD_FILENAME = "portfolio-dashboard.json"


def _dry_run_cohort(args: argparse.Namespace) -> list[str]:
    registry_path = Path(args.registry) if args.registry else None
    entries = load_portfolio_entries(registry_path)
    only = [item.strip() for item in args.only.split(",")] if args.only else None
    if args.mode == "canaries":
        cohort = resolve_seven_canaries(entries)
    elif args.mode == "fleet":
        cohort = filter_entries(entries, only=only, platform=args.platform, family=args.family)
        cohort = resolve_fleet_remaining(cohort, set())
    else:
        cohort = filter_entries(entries, only=only, platform=args.platform, family=args.family)
    return [entry.org_repo for entry in cohort]


def _print_result(result: ModePassResultV1) -> None:
    by_stage: dict[str, int] = {}
    for receipt in result.receipts:
        by_stage[receipt.stage] = by_stage.get(receipt.stage, 0) + 1
    print(
        f"portfolio-proof {result.mode}: campaign={result.campaign_id[:16]} "
        f"output_root={result.output_root} receipts={len(result.receipts)} "
        f"deadline_expired={result.deadline_expired}",
        flush=True,
    )
    print(
        f"  targeted={result.targeted_count} completed={result.completed_count} "
        f"pending={result.pending_count} failed={result.failed_count}",
        flush=True,
    )
    for stage, count in sorted(by_stage.items()):
        print(f"  {stage}: {count}", flush=True)
    if result.pending_org_repos:
        resume_only = ",".join(result.pending_org_repos)
        print(
            f"  {len(result.pending_org_repos)} repositories not reached this pass -- resume with:",
            flush=True,
        )
        print(
            f"    readme-agent portfolio-proof --mode {result.mode} --only {resume_only}",
            flush=True,
        )


def _write_and_verify_dashboard(
    registry_path: Path | None, output_root: Path
) -> PortfolioDashboardV1 | None:
    """Build the dashboard from this mode's own output root and atomically write it -- never
    claimed to exist unless the file is actually present and re-parses as a valid
    `PortfolioDashboardV1` afterward. Returns `None` on any failure so the caller can fail the
    whole command with a nonzero exit code rather than silently reporting success."""

    try:
        dashboard = build_dashboard(registry_path=registry_path, output_root=output_root)
    except Exception as exc:  # noqa: BLE001 -- reported, never silently swallowed
        print(f"error: dashboard construction failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None

    dashboard_path = output_root / DASHBOARD_FILENAME
    write_redacted_json(dashboard_path, dashboard.model_dump(mode="json"))
    if not dashboard_path.is_file():
        print(f"error: dashboard write did not produce {dashboard_path}", file=sys.stderr)
        return None
    try:
        PortfolioDashboardV1.model_validate_json(dashboard_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 -- reported, never silently swallowed
        print(
            f"error: written dashboard at {dashboard_path} failed re-validation: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return None

    print(f"portfolio-proof dashboard written: {dashboard_path}", flush=True)
    summary = dashboard.summary
    print(
        f"  total={summary.total} terminal_skipped={summary.terminal_skipped} "
        f"processable={summary.processable} facts_ready={summary.facts_ready} "
        f"candidates_generated={summary.candidates_generated}",
        flush=True,
    )
    print(
        f"  accepted_30_of_30={summary.accepted_30_of_30} "
        f"candidate_rejected={summary.candidate_rejected} "
        f"blocked_facts={summary.blocked_facts} "
        f"candidate_incomplete={summary.candidate_incomplete}",
        flush=True,
    )
    return dashboard


def cmd_portfolio_proof(args: argparse.Namespace) -> int:
    max_provider_concurrency = getattr(
        args, "max_provider_concurrency", DEFAULT_MAX_PROVIDER_CONCURRENCY
    )
    if max_provider_concurrency < 1:
        print("error: --max-provider-concurrency must be at least 1", file=sys.stderr)
        return 2

    if getattr(args, "dry_run", False):
        cohort = _dry_run_cohort(args)
        print(
            f"portfolio-proof {args.mode} [dry-run]: {len(cohort)} repositories resolved, "
            "no intake/facts/candidate/provider call made",
            flush=True,
        )
        for org_repo in cohort:
            print(f"  {org_repo}", flush=True)
        return 0

    # Honest concurrency reporting (RUNTIME-TRUTH CLOSURE item F): dispatch is serial -- one
    # repository at a time -- through the real supervise machinery. `--max-provider-concurrency`
    # is accepted (and validated above) for the day real concurrent dispatch is separately
    # authorized (plans/master.md decision #95), but it is not yet connected to the actual
    # provider-call boundary, so this never claims a concurrency this run does not have.
    print(
        f"portfolio-proof: provider execution is serial (one repository at a time); "
        f"--max-provider-concurrency={max_provider_concurrency} is accepted but not yet enforced "
        "as real cross-repository concurrency",
        flush=True,
    )

    registry_path = Path(args.registry) if args.registry else None
    output_root = Path(args.output_root) if getattr(args, "output_root", None) else None
    deadline = (
        DeadlineBudget(
            total_seconds=args.deadline_seconds,
            per_stage_seconds=getattr(args, "per_stage_timeout_seconds", None),
        )
        if getattr(args, "deadline_seconds", None) is not None
        else None
    )

    only = [item.strip() for item in args.only.split(",")] if getattr(args, "only", None) else None
    retry_blocked = bool(getattr(args, "retry_blocked", False))

    if args.mode == "preflight":
        from readme_agent.supervisor.portfolio_proof_engine.modes import run_preflight

        result = run_preflight(
            registry_path=registry_path,
            output_root=output_root,
            max_deterministic_workers=getattr(args, "max_deterministic_workers", 1),
        )
    elif args.mode == "facts-only":
        from readme_agent.supervisor.portfolio_proof_engine.modes import run_facts_only

        result = run_facts_only(
            registry_path=registry_path,
            output_root=output_root,
            deadline=deadline,
            only=only,
            platform=getattr(args, "platform", None),
            family=getattr(args, "family", None),
        )
    elif args.mode == "canaries":
        from readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes import (
            run_canaries,
        )

        result = run_canaries(
            registry_path=registry_path,
            output_root=output_root,
            deadline=deadline,
            retry_blocked=retry_blocked,
        )
    elif args.mode == "fleet":
        from readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes import run_fleet

        result = run_fleet(
            registry_path=registry_path,
            output_root=output_root,
            deadline=deadline,
            platform=getattr(args, "platform", None),
            family=getattr(args, "family", None),
            only=only,
            retry_blocked=retry_blocked,
        )
    elif args.mode == "failed-only":
        from readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes import (
            run_failed_only,
        )

        result = run_failed_only(
            registry_path=registry_path,
            output_root=output_root,
            deadline=deadline,
            retry_blocked=retry_blocked,
        )
    else:  # pragma: no cover -- argparse `choices` already rejects this
        print(f"error: unknown mode {args.mode!r}", file=sys.stderr)
        return 2

    _print_result(result)

    dashboard = _write_and_verify_dashboard(registry_path, result.output_root)
    if dashboard is None:
        return 1
    return 0
