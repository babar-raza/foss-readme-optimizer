"""Read-only compatibility and diagnostic CLI handlers."""

import argparse
import sys


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
    from readme_agent.supervisor.loop import supervise_repo
    from readme_agent.supervisor.status import terminal_exit_code

    result = supervise_repo(
        args.repo,
        allowed_permission_classes={"read_only_local", "read_only_network"},
    )
    print(
        f"{args.repo}: {result.status} "
        "(generate compatibility command; canonical supervisor, read-only effects)"
    )
    return terminal_exit_code(result)


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
    from readme_agent.supervisor.loop import supervise_repo
    from readme_agent.supervisor.status import terminal_exit_code

    state_backend = _durable_state_backend(args)
    result = supervise_repo(
        args.repo,
        state_backend=state_backend,
        allowed_permission_classes={"read_only_local", "read_only_network"},
    )
    print(
        f"{args.repo}: {result.status} "
        f"(run compatibility command; requested_mode={args.mode}, committed=False)"
    )
    return terminal_exit_code(result)


def _durable_state_backend(args: argparse.Namespace):
    """`--durable-state` is opt-in, matching `--check-install`/`--check-links`
    -- never a default, since it does a real network write to this
    project's own remote (`state/git_backend.py`)."""
    if not getattr(args, "durable_state", False):
        return None
    from readme_agent.state.git_backend import default_state_backend

    return default_state_backend()


def cmd_run_registry(args: argparse.Namespace) -> int:
    from readme_agent.registry.loader import enabled_entries
    from readme_agent.supervisor.loop import supervise_repo
    from readme_agent.supervisor.status import terminal_exit_code

    only = args.only.split(",") if args.only else None
    state_backend = _durable_state_backend(args)
    results = []
    for entry in enabled_entries():
        if only and entry.org_repo not in only:
            continue
        try:
            results.append(
                supervise_repo(
                    entry.org_repo,
                    state_backend=state_backend,
                    allowed_permission_classes={"read_only_local", "read_only_network"},
                )
            )
        except Exception as exc:  # noqa: BLE001 -- preserve portfolio failure isolation
            print(f"  {entry.org_repo}: ERROR: {exc}", file=sys.stderr)
            return 1
    for result in results:
        print(f"  {result.org_repo}: {result.status}")
    return 1 if any(terminal_exit_code(result) for result in results) else 0


def cmd_profile_registry(args: argparse.Namespace) -> int:
    """Decision #40, Part E: the actual invokable entry point for
    `run_registry_profiling_sweep()` -- profiles every registry entry
    (regardless of mode, unlike `run-registry`'s enabled-only sweep;
    read-only, so decision #40's mode-gate reasoning applies here too),
    with the SHA-freshness cache engaged whenever `--durable-state` is
    given. Mirrors `cmd_run_registry()`'s shape exactly."""
    from readme_agent.orchestrator import run_registry_profiling_sweep

    only = args.only.split(",") if args.only else None
    state_backend = _durable_state_backend(args)
    profiles = run_registry_profiling_sweep(state_backend=state_backend, only=only)
    for profile in profiles:
        ecosystems = [d.ecosystem for d in profile.detected_ecosystems]
        print(
            f"  {profile.org_repo}: detected={ecosystems} unresolved={profile.unresolved_manifests}"
        )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import report

    manifest = report(args.run_id)
    for key, value in manifest.items():
        print(f"  {key}: {value}")
    return 0
