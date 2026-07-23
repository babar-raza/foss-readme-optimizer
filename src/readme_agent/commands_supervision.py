"""Canonical repository-supervision CLI handlers."""

import argparse
import sys

from readme_agent.commands_compatibility import _durable_state_backend


def cmd_supervise(args: argparse.Namespace) -> int:
    if getattr(args, "mission_task_graph", None):
        from readme_agent.supervisor.mission_command import run_mission_command

        return run_mission_command(args)

    from readme_agent.preflight.runner import format_summary, run_preflight_for_repo
    from readme_agent.registry.self_heal import heal_registry_drift

    profile_name = getattr(args, "execution_profile", None)
    domain = getattr(args, "domain", None)

    # Wave 9.4 (execution profiles): a `github_*` profile must never let
    # `--domain` skip supervise_repo()'s own lock/evidence/verification path --
    # `_cmd_supervise_single_domain()`'s own docstring already says it
    # "deliberately bypasses the supervisor's own convergence/lock machinery",
    # which is fine for local, interactive diagnosis but never for an
    # unattended GitHub Actions run. Checked before anything else runs (no
    # registry heal, no preflight, no clone) -- a usage error, not a runtime
    # one, matching argparse's own exit-code-2 convention.
    if profile_name is not None:
        from readme_agent.supervisor.execution_profile import get_profile

        profile = get_profile(profile_name)
        if domain is not None and not profile.allows_domain_bypass:
            print(
                f"error: --domain is not permitted under --execution-profile {profile_name!r} -- "
                "a github_* profile must always go through supervise_repo()'s own lock/evidence/"
                "verification path, never a single-domain bypass.",
                file=sys.stderr,
            )
            return 2
    else:
        profile = None

    # CORE-034 (decision #47): registry drift self-heals before preflight and
    # before any allow-list gate, so a repo GitHub published after the last
    # weekly scan is already listed (as mode: "disabled") when
    # require_listed() runs below. Fail-open by contract -- whatever the heal
    # returns, supervision proceeds.
    heal_result = heal_registry_drift(enabled=not getattr(args, "no_registry_heal", False))
    print(heal_result.summary_line())

    # Wave 8.5 (`ORC-006`/D2): a single-repo preflight, checked before either
    # branch below -- the single-domain branch needs this even more than the
    # full path, since it bypasses more of supervise_repo()'s own
    # convergence/lock machinery per its own docstring. Exit code 3 matches
    # PreflightError.exit_code / errors.py's documented convention, same as
    # cmd_preflight()'s own return value.
    preflight_result = run_preflight_for_repo(args.repo)
    if not preflight_result.ok:
        print(format_summary(preflight_result))
        return 3

    # Wave 9.4: a profile that declares `requires_durable_state` gets a real
    # state backend regardless of whether `--durable-state` was also passed --
    # the profile is now the authoritative declaration, not an extra flag a
    # caller might forget. `--durable-state` alone (no profile) is unchanged.
    # `default_state_backend()` either returns a real backend or raises --
    # never a silent `None` -- so a `github_*` profile's `fail_closed_on_
    # state_failure` requirement is already satisfied by that existing
    # propagation (handled by `main()`'s own `ReadmeAgentError` catch), not
    # something this function needs to re-implement.
    needs_durable_state = getattr(args, "durable_state", False) or (
        profile is not None and profile.requires_durable_state
    )
    state_backend = (
        _durable_state_backend(args)
        if getattr(args, "durable_state", False)
        else (_force_durable_state_backend() if needs_durable_state else None)
    )

    # Wave 9.5 (`RUN-006`): trigger identity/dedup, only meaningful once a real
    # state backend exists to check/record against. GitHub Actions always sets
    # `GITHUB_RUN_ID` on a real runner; local CLI use has none, so `--domain`-
    # style ad hoc invocations are never deduplicated against each other --
    # correct, since there's no stable identity to dedup on outside Actions.
    if profile is not None and state_backend is not None:
        from readme_agent import env
        from readme_agent.state.schema import TriggerRecordV1
        from readme_agent.state.trigger import is_duplicate_trigger, record_trigger

        run_id = env.github_run_id()
        if run_id is not None:
            trigger = TriggerRecordV1(
                org_repo=args.repo,
                event_type=(
                    env.github_event_name() or "workflow_dispatch"  # type: ignore[arg-type]
                ),
                workflow_run_id=run_id,
            )
            if is_duplicate_trigger(state_backend, args.repo, trigger):
                print(
                    f"{args.repo}: DEDUPLICATED -- workflow run {run_id!r} already accepted, "
                    "not re-executing"
                )
                return 0
            record_trigger(state_backend, args.repo, trigger)

    if domain is not None:
        return _cmd_supervise_single_domain(args.repo, domain, state_backend)

    from readme_agent.supervisor.loop import supervise_repo

    allowed_permission_classes = (
        set(profile.allowed_permission_classes) if profile is not None else None
    )

    # Wave 12.2 (`ORC-003`/`AGT-008`): the confirmed real gap this phase
    # closes -- `enable_specialist_skip`/`specialist_selection_client`/
    # `repair_planner_client` have all defaulted `None`/`False` here since
    # Wave 8.6 shipped them (never a default, matching `--durable-state`'s
    # own convention), which meant the dynamic specialist-skip and
    # repair-alternative-selection mechanisms -- fully built and unit-tested
    # -- had zero effect in any shipped CLI/GitHub-Actions run. Opt-in only.
    dynamic_planning_kwargs: dict = {}
    if getattr(args, "enable_dynamic_planning", False):
        from readme_agent import env
        from readme_agent.llm.planner_client import LivePlannerClient

        base_url, api_key = env.llm_base_url(), env.llm_api_key()
        dynamic_planning_kwargs = {
            "enable_specialist_skip": True,
            "specialist_selection_client": LivePlannerClient(
                base_url, api_key, env.llm_model_for_job("specialist_selection")
            ),
            "repair_planner_client": LivePlannerClient(
                base_url, api_key, env.llm_model_for_job("repair_capability_selection")
            ),
        }

    result = supervise_repo(
        args.repo,
        state_backend=state_backend,
        allowed_permission_classes=allowed_permission_classes,
        **dynamic_planning_kwargs,
    )
    print(
        f"{args.repo}: {result.status}"
        + (f" ({result.blocked_reason})" if result.blocked_reason else "")
    )
    for d in result.decisions:
        print(f"  [{d.turn}] {d.kind}: {d.detail}")
    from readme_agent.supervisor.status import terminal_exit_code

    return terminal_exit_code(result)


def _force_durable_state_backend():
    """Wave 9.4: same backend `--durable-state` resolves to, but invoked because an
    `ExecutionProfileV1` requires durable state, not because the flag was passed."""
    from readme_agent.state.git_backend import default_state_backend

    return default_state_backend()


def _cmd_supervise_single_domain(repo: str, domain: str, state_backend) -> int:
    """Wave 7: `specialists/registry.py::run_domain()` already lets one
    domain run in isolation at the Python level -- this is the CLI-facing
    version of that, bypassing the full specialist-tier sweep and planner
    loop entirely. Deliberately does not go through `supervise_repo()`'s own
    convergence/lock machinery: a single-domain run is meant to be cheap and
    direct, matching `run_domain()`'s own (org_repo, backend) -> DomainStateV1
    contract exactly."""
    from readme_agent.specialists import registry as specialists_registry

    known = specialists_registry.all_domains()
    if domain not in known:
        print(f"unknown domain {domain!r} -- registered domains: {known}")
        return 2

    result = specialists_registry.run_domain(domain, repo, state_backend)
    if result is None:
        print(f"unknown domain {domain!r} -- registered domains: {known}")
        return 2

    print(f"{repo} [{domain}]: {result.accepted_status}")
    if result.details:
        for key, value in result.details.items():
            print(f"  {key}: {value}")
    return 0 if not (result.accepted_status or "").startswith("ERROR") else 1
