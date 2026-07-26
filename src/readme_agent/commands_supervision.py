"""Canonical repository-supervision CLI handlers."""

import argparse
import sys
import time
from pathlib import Path

from readme_agent import env
from readme_agent.commands_compatibility import _durable_state_backend
from readme_agent.evidence.redaction import redact
from readme_agent.state.lifecycle_schema import FailureClassificationV1, TriggerStatusV2

# Bound one invocation below common interactive/Actions cancellation windows;
# durable per-repository state makes the next invocation resume the portfolio.
_LOCAL_POC_EXECUTION_SLICE_SECONDS = 300.0


def _unhandled_runtime_failure_detail(exc: Exception) -> str:
    """Preserve the first failing boundary without leaking secrets or unbounded output."""

    message = redact(str(exc), env.secret_values()).replace("\r", " ").replace("\n", " ")
    prefix = f"unhandled_runtime_failure:{type(exc).__name__}:"
    return prefix + message[: max(0, 1024 - len(prefix))]


def cmd_supervise(args: argparse.Namespace) -> int:
    if getattr(args, "mission_task_graph", None):
        from readme_agent.supervisor.mission_command import run_mission_command

        return run_mission_command(args)

    if getattr(args, "registry", None):
        return _cmd_supervise_registry(args)

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
        if profile.name == "local_poc" and not getattr(args, "_portfolio_member", False):
            print(
                "error: --execution-profile local_poc requires --registry data/products.json",
                file=sys.stderr,
            )
            return 2
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
    state_backend = getattr(args, "_state_backend_override", None) or (
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
        from readme_agent.state.trigger_v2 import (
            normalize_github_trigger,
            normalize_trigger_envelope,
        )

        event_name = "cli_manual" if profile.name == "local_poc" else env.github_event_name()
        if event_name not in profile.allowed_triggers:
            print(
                f"error: trigger {event_name!r} is not allowed by execution profile "
                f"{profile.name!r}",
                file=sys.stderr,
            )
            return 2
        assert state_backend is not None
        resume_trigger_key = getattr(args, "resume_trigger_key", None)
        run_id = env.github_run_id() or generate_run_id()
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
        elif profile.name == "local_poc":
            envelope = normalize_trigger_envelope(
                args.repo,
                event_type="cli_manual",
                provider_event_id=run_id,
            )
        else:
            envelope = normalize_github_trigger(args.repo)
        acceptance = accept_trigger(state_backend, envelope)
        # Expose the exact accepted/resumed trigger to the portfolio fallback.
        # If setup or terminal evidence fails outside the guarded runtime
        # section, the portfolio can return this owned lease to retryable.
        args._active_trigger_key = envelope.dedup_key
        if not acceptance.should_execute:
            print(
                f"{args.repo}: DEDUPLICATED -- trigger {envelope.dedup_key!r} "
                "already reached a terminal state"
            )
            return 0
        lifecycle_recorder = LifecycleRecorder(
            state_backend,
            envelope,
            run_id,
            attempt=env.github_run_attempt(),
        )
        lifecycle_recorder.checkpoint(
            "trigger_accepted",
            inputs={"resumed": acceptance.resumed, "event_type": envelope.event_type},
        )
        lifecycle_recorder.start()
    elif getattr(args, "resume_trigger_key", None):
        print(
            "error: --resume-trigger-key requires a durable execution profile",
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
    dynamic_planning_required = profile is not None and profile.name == "local_poc"
    if getattr(args, "enable_dynamic_planning", False) or dynamic_planning_required:
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
                    verify_local_product_facts=profile.verify_local_product_facts,
                    track_readme_poc_lifecycle=profile.name == "local_poc",
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
                failure_detail=_unhandled_runtime_failure_detail(exc),
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

    lifecycle_status: TriggerStatusV2 | None = None
    if lifecycle_recorder is not None:
        assert state_backend is not None
        failure_classification: FailureClassificationV1 | None = None
        failure_detail: str | None = result.status
        if result.status == "BLOCKED":
            transient = bool(
                result.blocked_reason
                and (
                    result.blocked_reason.startswith("baseline_clone_failed:")
                    or result.blocked_reason.startswith("planner_llm_failure:")
                    or result.blocked_reason in {"lock_held", "run_lock_held"}
                )
            )
            failure_detail = result.blocked_reason
            if transient:
                lifecycle_status = "retryable"
                failure_classification = "transient"
            else:
                failure_classification = (
                    "unsupported"
                    if result.blocked_reason
                    and (
                        result.blocked_reason.startswith("unsupported_ecosystem:")
                        or result.blocked_reason == "not_onboarded"
                    )
                    else "validation_failed"
                )
                lifecycle_status = "blocked"
        else:
            lifecycle_status = "completed"

        from readme_agent.supervisor.evidence import (
            assert_evidence_complete,
            finalize_run_manifest_v3,
        )

        assert lifecycle_status is not None
        if lifecycle_status in {"blocked", "completed"}:
            lifecycle_recorder.checkpoint_final_acceptance(
                lifecycle_status,
                detail=failure_detail,
                failure_classification=failure_classification,
            )
        try:
            if result.evidence_dir is None:
                raise RuntimeError(
                    "GitHub execution profile did not produce a terminal evidence bundle"
                )
            finalize_run_manifest_v3(
                result.evidence_dir,
                lifecycle_recorder,
                lifecycle_status,
            )
            assert_evidence_complete(result.evidence_dir)
        except Exception as exc:
            transition_trigger(
                state_backend,
                args.repo,
                lifecycle_recorder.envelope.dedup_key,
                "retryable",
                failure_classification="validation_failed",
                failure_detail=f"terminal_evidence_failure:{type(exc).__name__}",
            )
            raise
        lifecycle_recorder.transition(
            lifecycle_status,
            detail=failure_detail,
            failure_classification=failure_classification,
        )
    print(
        f"{args.repo}: {result.status}"
        + (
            f" ({result.blocked_reason}; category={result.blocked_category})"
            if result.blocked_reason
            else ""
        )
    )
    for d in result.decisions:
        print(f"  [{d.turn}] {d.kind}: {d.detail}")
    from readme_agent.supervisor.status import terminal_exit_code

    exit_code = terminal_exit_code(result)
    # Private command-local handoff used only by `_cmd_supervise_registry()`
    # to derive an honest portfolio summary.  It is never persisted or used
    # to control execution; durable state and manifests remain authoritative.
    args._terminal_supervise_result = result
    return exit_code


def _cmd_supervise_registry(args: argparse.Namespace) -> int:
    """Fan the existing supervisor over one immutable registry snapshot.

    This is intentionally a thin command adapter, not a second controller:
    every repository goes through `cmd_supervise()` and therefore the same
    profile, state, lifecycle, evidence, registry, and terminal-classifier
    path as a single-repository invocation.  The source registry is loaded
    exactly once so a registry-discovery change cannot alter the denominator
    halfway through a proof pass.
    """
    if getattr(args, "execution_profile", None) != "local_poc":
        print(
            "error: --registry is only supported with --execution-profile local_poc",
            file=sys.stderr,
        )
        return 2
    if getattr(args, "domain", None) is not None:
        print(
            "error: --domain is not permitted under --execution-profile 'local_poc'",
            file=sys.stderr,
        )
        return 2
    if getattr(args, "resume_trigger_key", None):
        print(
            "error: --resume-trigger-key is not supported for a portfolio invocation",
            file=sys.stderr,
        )
        return 2

    from readme_agent import paths
    from readme_agent.registry.loader import load_products
    from readme_agent.state.recovery import recovery_sweep
    from readme_agent.supervisor.portfolio import (
        PortfolioPocSummaryV1,
        PortfolioRepositoryResultV1,
        completed_local_poc_status,
        mark_failed_member_retryable,
        recover_completed_local_poc_status,
        select_portfolio_trigger,
        write_portfolio_summary,
    )

    registry_path = Path(args.registry)
    entries = load_products(registry_path)
    # Resolve the one durable backend before the fan-out.  It is deliberately
    # shared by every member so the final summary can be derived from the
    # lifecycle state the canonical runs actually persisted, not their
    # console exit codes.
    state_backend = _force_durable_state_backend()
    results: list[PortfolioRepositoryResultV1] = []
    slice_started = time.monotonic()
    execution_slice_complete = True
    slice_budget = float(
        getattr(
            args,
            "portfolio_time_budget_seconds",
            _LOCAL_POC_EXECUTION_SLICE_SECONDS,
        )
    )
    for entry_index, entry in enumerate(entries):
        repository_args = argparse.Namespace(**vars(args))
        repository_args.repo = entry.org_repo
        repository_args.registry = None
        repository_args._portfolio_member = True
        repository_args._state_backend_override = state_backend
        # The source registry has already been frozen above.  A discovery
        # sweep during the pass would invalidate its dynamic denominator.
        repository_args.no_registry_heal = True
        try:
            persisted = state_backend.load(entry.org_repo)
            lifecycle = persisted.readme_poc_lifecycle if persisted is not None else None
            if lifecycle is not None and lifecycle.source_revision:
                org, repo = entry.org_repo.split("/", maxsplit=1)
                bundle_dir = paths.readme_poc_repository_dir(
                    org,
                    repo,
                    lifecycle.source_revision,
                )
                if complete_status := completed_local_poc_status(persisted, bundle_dir):
                    results.append(
                        PortfolioRepositoryResultV1(
                            org_repo=entry.org_repo,
                            status=complete_status,
                            exit_code=0,
                        )
                    )
                    continue
            # Recover only expired work. An explicitly retryable trigger can
            # resume immediately; an unexpired accepted/processing trigger is
            # still owned by another worker and must never be stolen.
            recovery_sweep(state_backend, [entry.org_repo])
            trigger_selection = select_portfolio_trigger(state_backend.load(entry.org_repo))
            if trigger_selection.active_trigger_key is not None:
                persisted = state_backend.load(entry.org_repo)
                lifecycle = persisted.readme_poc_lifecycle if persisted is not None else None
                results.append(
                    PortfolioRepositoryResultV1(
                        org_repo=entry.org_repo,
                        status=lifecycle.status if lifecycle is not None else "ACTIVE_TRIGGER",
                        exit_code=1,
                        blocked_reason=(
                            f"unexpired_active_trigger:{trigger_selection.active_trigger_key}"
                        ),
                        blocked_category="infra_external",
                    )
                )
                continue
            repository_args.resume_trigger_key = trigger_selection.resume_trigger_key
            exit_code = cmd_supervise(repository_args)
            terminal_result = getattr(repository_args, "_terminal_supervise_result", None)
            persisted = state_backend.load(entry.org_repo)
            lifecycle = persisted.readme_poc_lifecycle if persisted is not None else None
            results.append(
                PortfolioRepositoryResultV1(
                    org_repo=entry.org_repo,
                    status=(
                        lifecycle.status
                        if lifecycle is not None
                        else ("NO_POC_LIFECYCLE" if exit_code == 0 else "NON_SUCCESS_TERMINAL")
                    ),
                    exit_code=exit_code,
                    blocked_reason=(
                        terminal_result.blocked_reason if terminal_result is not None else None
                    ),
                    blocked_category=(
                        terminal_result.blocked_category if terminal_result is not None else None
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001 -- portfolio failure isolation is contractual
            print(f"{entry.org_repo}: SYSTEM_FAILURE: {type(exc).__name__}: {exc}", file=sys.stderr)
            failure_detail = f"portfolio_member_failure:{type(exc).__name__}:{exc}"
            try:
                recovered_status = recover_completed_local_poc_status(
                    state_backend,
                    entry.org_repo,
                )
            except Exception as recovery_check_exc:  # noqa: BLE001 -- preserve original failure
                recovered_status = None
                failure_detail += (
                    f"; completion_recovery_failed:{type(recovery_check_exc).__name__}:"
                    f"{recovery_check_exc}"
                )
            if recovered_status is not None:
                results.append(
                    PortfolioRepositoryResultV1(
                        org_repo=entry.org_repo,
                        status=recovered_status,
                        exit_code=0,
                    )
                )
                continue
            trigger_key = getattr(
                repository_args,
                "_active_trigger_key",
                repository_args.resume_trigger_key,
            )
            try:
                mark_failed_member_retryable(
                    state_backend,
                    entry.org_repo,
                    trigger_key,
                    failure_detail=failure_detail,
                )
            except Exception as recovery_exc:  # noqa: BLE001 -- retain the original failure
                print(
                    f"{entry.org_repo}: lifecycle recovery also failed: "
                    f"{type(recovery_exc).__name__}: {recovery_exc}",
                    file=sys.stderr,
                )
            results.append(
                PortfolioRepositoryResultV1(
                    org_repo=entry.org_repo,
                    status="SYSTEM_FAILURE",
                    exit_code=1,
                    blocked_reason=failure_detail,
                    blocked_category="agent_fixable",
                )
            )
        if entry_index + 1 < len(entries) and time.monotonic() - slice_started >= slice_budget:
            execution_slice_complete = False
            break

    summary = PortfolioPocSummaryV1(
        registry_path=str(registry_path),
        registry_count=len(entries),
        execution_slice_complete=execution_slice_complete,
        results=results,
    )
    write_portfolio_summary(paths.readme_poc_portfolio_summary_path(), summary)
    print(summary.summary_line())
    return 1 if not execution_slice_complete or any(result.exit_code for result in results) else 0


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
