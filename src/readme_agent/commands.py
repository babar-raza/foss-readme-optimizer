"""CLI command handlers -- thin wrappers over orchestrator.py."""

import argparse


def cmd_preflight(args: argparse.Namespace) -> int:
    from readme_agent.preflight.runner import format_summary, run_preflight

    result = run_preflight()
    print(format_summary(result))
    return 0 if result.ok else 3


def cmd_inspect(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import inspect_repo

    facts = inspect_repo(args.repo, check_install=args.check_install)
    print(f"Inspected {args.repo}:")
    for key, value in facts.items():
        print(f"  {key}: {value}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import generate_repo

    result = generate_repo(args.repo, force_regenerate=args.force_regenerate)
    print(f"{args.repo}: {result.status}")
    print(
        f"  llm_called={result.llm_called}, llm_calls={result.llm_calls}, "
        f"gaps={result.gap_report.gaps}"
    )
    return 0 if result.status in ("COMPLIANT_NO_CHANGE", "GENERATED") else 1


def cmd_validate(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import validate_repo
    from readme_agent.validation import registry as validation_registry

    result = validate_repo(args.repo, check_links=args.check_links)
    passed = validation_registry.passed(result.validation_results)
    for rule_result in result.validation_results:
        marker = "OK" if rule_result.passed else rule_result.severity
        print(f"  [{marker}] {rule_result.rule_name}: {rule_result.message}")
    return 0 if passed else 1


def cmd_run(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import run_repo

    state_backend = _durable_state_backend(args)
    result = run_repo(
        args.repo,
        mode=args.mode,
        force_regenerate=args.force_regenerate,
        state_backend=state_backend,
    )
    print(
        f"{args.repo}: {result.status} (mode={args.mode}, push_block_ok={result.push_block_ok}, "
        f"committed={result.committed})"
    )
    return 0 if result.ok else 1


def _durable_state_backend(args: argparse.Namespace):
    """`--durable-state` is opt-in, matching `--check-install`/`--check-links`
    -- never a default, since it does a real network write to this
    project's own remote (`state/git_backend.py`)."""
    if not getattr(args, "durable_state", False):
        return None
    from readme_agent.state.git_backend import default_state_backend

    return default_state_backend()


def cmd_run_registry(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import run_registry

    only = args.only.split(",") if args.only else None
    state_backend = _durable_state_backend(args)
    results = run_registry(only=only, state_backend=state_backend)
    for result in results:
        print(f"  {result.org_repo}: {result.status}")
    # Exits nonzero only on an unhandled exception surfaced as an ERROR status
    # -- blocked/rejected outcomes for individual repos are correct, not failures.
    return 1 if any(r.status.startswith("ERROR") for r in results) else 0


def cmd_supervise(args: argparse.Namespace) -> int:
    from readme_agent.supervisor.loop import supervise_repo

    state_backend = _durable_state_backend(args)
    result = supervise_repo(args.repo, state_backend=state_backend)
    print(
        f"{args.repo}: {result.status}"
        + (f" ({result.blocked_reason})" if result.blocked_reason else "")
    )
    for d in result.decisions:
        print(f"  [{d.turn}] {d.kind}: {d.detail}")
    # CONVERGED_NO_TRACKED_CHANGE (Wave 6, decision #39): the registry-driven
    # specialist tier's own converged outcome -- a successful exit, exactly
    # like CONVERGED_NO_CHANGE, not a failure.
    converged_statuses = ("CONVERGED_NO_CHANGE", "CONVERGED_APPLIED", "CONVERGED_NO_TRACKED_CHANGE")
    return 0 if result.status in converged_statuses else 1


def cmd_report(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import report

    manifest = report(args.run_id)
    for key, value in manifest.items():
        print(f"  {key}: {value}")
    return 0
