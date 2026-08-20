"""CLI handler for `readme-agent portfolio-proof` -- the five resumable portfolio proof engine
modes (preflight, facts-only, canaries, fleet, failed-only). Thin argument plumbing only: all
real logic lives in `supervisor/portfolio_proof_engine/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    for stage, count in sorted(by_stage.items()):
        print(f"  {stage}: {count}", flush=True)


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
            registry_path=registry_path, output_root=output_root, deadline=deadline
        )
    elif args.mode == "canaries":
        from readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes import (
            run_canaries,
        )

        result = run_canaries(
            registry_path=registry_path, output_root=output_root, deadline=deadline
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
        )
    elif args.mode == "failed-only":
        from readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes import (
            run_failed_only,
        )

        result = run_failed_only(
            registry_path=registry_path, output_root=output_root, deadline=deadline
        )
    else:  # pragma: no cover -- argparse `choices` already rejects this
        print(f"error: unknown mode {args.mode!r}", file=sys.stderr)
        return 2

    _print_result(result)
    return 0
