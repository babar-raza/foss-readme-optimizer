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

    # Resolve and prove durable state before preflight can make an LLM
    # connectivity call. A GitHub profile may never degrade to ephemeral
    # execution when intake state is uncertain.
    needs_durable_state = getattr(args, "durable_state", False) or (
        profile is not None and profile.requires_durable_state
    )
    state_backend = (
        _durable_state_backend(args)
        if getattr(args, "durable_state", False)
        else (_force_durable_state_backend() if needs_durable_state else None)
    )

    lifecycle_recorder = None
    if profile is not None and profile.requires_durable_state:
        from readme_agent import env
        from readme_agent.errors import StateBackendError
        from readme_agent.evidence.writer import generate_run_id
        from readme_agent.state.lifecycle import LifecycleRecorder, accept_trigger
        from readme_agent.state.trigger_v2 import normalize_github_trigger

        event_name = env.github_event_name()
        if event_name not in profile.allowed_triggers:
            print(
                f"error: trigger {event_name!r} is not allowed by execution profile "
                f"{profile.name!r}",
                file=sys.stderr,
            )
            return 2
        assert state_backend is not None
        resume_trigger_key = getattr(args, "resume_trigger_key", None)
        if resume_trigger_key:
            assert state_backend is not None
            recovery_state = state_backend.load(args.repo)
            if recovery_state is None:
                raise StateBackendError(
                    f"cannot resume trigger {resume_trigger_key!r}: no durable state "
                    f"exists for {args.repo!r}"
                )
            lifecycle = recovery_state.trigger_lifecycles.get(resume_trigger_key)
            if lifecycle is None:
                raise StateBackendError(
                    f"cannot resume unknown trigger {resume_trigger_key!r} for {args.repo!r}"
                )
            envelope = lifecycle.envelope
        else:
            envelope = normalize_github_trigger(args.repo)
        acceptance = accept_trigger(state_backend, envelope)
        if not acceptance.should_execute:
            print(
                f"{args.repo}: DEDUPLICATED -- trigger {envelope.dedup_key!r} "
                "already reached a terminal state"
            )
            return 0
        lifecycle_recorder = LifecycleRecorder(
            state_backend,
            envelope,
            env.github_run_id() or generate_run_id(),
            attempt=env.github_run_attempt(),
        )
        lifecycle_recorder.checkpoint(
            "trigger_accepted",
            inputs={"resumed": acceptance.resumed, "event_type": envelope.event_type},
        )
        lifecycle_recorder.start()
    elif getattr(args, "resume_trigger_key", None):
        print(
            "error: --resume-trigger-key requires a github_* execution profile",
            file=sys.stderr,
        )
        return 2

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
        if lifecycle_recorder is not None:
            from readme_agent.state.lifecycle import transition_trigger

            assert state_backend is not None
            transition_trigger(
                state_backend,
                args.repo,
                lifecycle_recorder.envelope.dedup_key,
                "retryable",
                failure_classification="transient",
                failure_detail="preflight_failed",
            )
        print(format_summary(preflight_result))
        return 3

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

    from readme_agent.state.lifecycle import activate_lifecycle, transition_trigger

    try:
        with activate_lifecycle(lifecycle_recorder):
            if profile is None:
                result = supervise_repo(
                    args.repo,
                    state_backend=state_backend,
                    allowed_permission_classes=allowed_permission_classes,
                    **dynamic_planning_kwargs,
                )
            else:
                result = supervise_repo(
                    args.repo,
                    state_backend=state_backend,
                    allowed_permission_classes=allowed_permission_classes,
                    fail_closed_on_state_failure=profile.fail_closed_on_state_failure,
                    require_evidence_bundle=profile.require_evidence_bundle,
                    require_independent_verification=profile.require_independent_verification,
                    **dynamic_planning_kwargs,
                )
    except Exception as exc:
        if lifecycle_recorder is not None:
            assert state_backend is not None
            transition_trigger(
                state_backend,
                args.repo,
                lifecycle_recorder.envelope.dedup_key,
                "retryable",
                failure_classification="transient",
                failure_detail=f"unhandled_runtime_failure:{type(exc).__name__}",
            )
        raise
    if profile is not None and profile.require_evidence_bundle and result.evidence_dir is None:
        from readme_agent import paths
        from readme_agent.evidence.writer import generate_run_id
        from readme_agent.supervisor.evidence import (
            assert_evidence_complete,
            write_supervise_evidence,
        )

        fallback_run_id = (
            lifecycle_recorder.run_id if lifecycle_recorder is not None else generate_run_id()
        )
        result.evidence_dir = paths.evidence_dir(fallback_run_id)
        with activate_lifecycle(lifecycle_recorder):
            write_supervise_evidence(
                result.evidence_dir,
                fallback_run_id,
                args.repo,
                result.status,
                result.task_graph,
                result.decisions,
            )
        assert_evidence_complete(result.evidence_dir)

    lifecycle_status = None
    if lifecycle_recorder is not None:
        assert state_backend is not None
        if result.status == "BLOCKED":
            transient = bool(
                result.blocked_reason
                and (
                    result.blocked_reason.startswith("baseline_clone_failed:")
                    or result.blocked_reason.startswith("planner_llm_failure:")
                    or result.blocked_reason in {"lock_held", "run_lock_held"}
                )
            )
            if transient:
                transition_trigger(
                    state_backend,
                    args.repo,
                    lifecycle_recorder.envelope.dedup_key,
                    "retryable",
                    failure_classification="transient",
                    failure_detail=result.blocked_reason,
                )
                lifecycle_status = "retryable"
            else:
                lifecycle_recorder.finish(
                    "blocked",
                    detail=result.blocked_reason,
                    failure_classification=(
                        "unsupported"
                        if result.blocked_reason
                        and (
                            result.blocked_reason.startswith("unsupported_ecosystem:")
                            or result.blocked_reason == "not_onboarded"
                        )
                        else "validation_failed"
                    ),
                )
                lifecycle_status = "blocked"
        else:
            lifecycle_recorder.finish("completed", detail=result.status)
            lifecycle_status = "completed"
        if result.evidence_dir is not None:
            from readme_agent.supervisor.evidence import (
                assert_evidence_complete,
                finalize_run_manifest_v3,
            )

            assert lifecycle_status is not None
            finalize_run_manifest_v3(
                result.evidence_dir,
                lifecycle_recorder,
                lifecycle_status,
            )
            assert_evidence_complete(result.evidence_dir)
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
