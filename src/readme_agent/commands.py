"""CLI command handlers -- thin wrappers over orchestrator.py."""

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
    # CONVERGED_NO_TRACKED_CHANGE (Wave 6, decision #39): the registry-driven
    # specialist tier's own converged outcome -- a successful exit, exactly
    # like CONVERGED_NO_CHANGE, not a failure.
    converged_statuses = ("CONVERGED_NO_CHANGE", "CONVERGED_APPLIED", "CONVERGED_NO_TRACKED_CHANGE")
    return 0 if result.status in converged_statuses else 1


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


def cmd_report(args: argparse.Namespace) -> int:
    from readme_agent.orchestrator import report

    manifest = report(args.run_id)
    for key, value in manifest.items():
        print(f"  {key}: {value}")
    return 0


def cmd_authorization_validate(args: argparse.Namespace) -> int:
    """Wave 13.2 (`AUTH-001`-`006`): a diagnostic, read-only check of
    whether `config/authorization/<org>__<repo>.yml` exists, is
    schema-valid, and which `EffectClass` values it currently covers --
    never itself grants or infers authority (that stays a human-authored
    config file, reviewed asynchronously per the Execution Readiness
    model). Reports "no record filed" honestly for a repo with none, which
    is the correct, expected state for every repo today (this mechanism is
    new -- no real authorization record exists yet for any of the 3
    current pilots)."""
    from typing import get_args

    from readme_agent.authorization import registry as auth_registry
    from readme_agent.authorization.schema import EffectClass
    from readme_agent.errors import ConfigError

    try:
        # `auth_registry.AUTHORIZATION_DIR` read as a module attribute here
        # (not relied on as `load_authorization_record()`'s own bound
        # default), so a test can monkeypatch it and have this call site
        # actually observe the override.
        record = auth_registry.load_authorization_record(args.repo, auth_registry.AUTHORIZATION_DIR)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if record is None:
        print(f"{args.repo}: no authorization record filed -- no autonomous write authority.")
        return 0

    from datetime import UTC, datetime

    expired = record.expiration is not None and datetime.fromisoformat(
        record.expiration
    ) <= datetime.now(UTC)
    print(f"{args.repo}: authorization record found (approved by {record.approving_identity!r})")
    print(f"  effect_classes: {record.effect_classes}")
    print(f"  branch_pattern: {record.branch_pattern}")
    print(f"  expiration: {record.expiration!r} ({'EXPIRED' if expired else 'not expired'})")
    for effect_class in get_args(EffectClass):
        covered = effect_class in record.effect_classes and not expired
        print(f"  {effect_class}: {'AUTHORIZED' if covered else 'not authorized'}")
    return 0


def cmd_golden_set_run(args: argparse.Namespace) -> int:
    """Wave 13.5 (`OPS-011`/`OPS-012`): a real, live golden-set run against
    `args.job`'s own currently-routed model. Structurally non-mutating in
    itself (`golden_set/harness.py::run_golden_set()` never dispatches a
    real capability, only compares the planner's chosen capability NAME) --
    but this command's own follow-up auto-disable check durably records a
    `disabled` `ModelRouteStatusV1` when this run's pass rate crosses the
    documented floor (`golden_set/auto_disable.py`), never a silent
    substitution. Exit code reflects whether this run just disabled a route
    -- a real CI signal (a failed workflow run), not something a human has
    to notice by reading log output."""
    from readme_agent import env
    from readme_agent.golden_set import auto_disable
    from readme_agent.golden_set.harness import run_golden_set, summarize
    from readme_agent.llm.planner_client import LivePlannerClient
    from readme_agent.state.git_backend import default_state_backend

    base_url, api_key = env.llm_base_url(), env.llm_api_key()
    client = LivePlannerClient(base_url, api_key, env.llm_model_for_job(args.job))

    results = run_golden_set(client)
    summary = summarize(results)
    print(
        f"{args.job}: {summary['passed']}/{summary['total']} passed "
        f"(pass_rate={summary['pass_rate']})"
    )
    for category, counts in summary["by_category"].items():
        print(f"  {category}: {counts['passed']}/{counts['total']}")
    for result in results:
        if not result.passed:
            print(f"  FAIL {result.scenario_id}: {result.detail}")

    backend = default_state_backend()
    disabled = auto_disable.evaluate_and_disable(args.job, results, backend)
    if disabled is not None:
        print(f"AUTO-DISABLED model_route {args.job!r}: {disabled.reason}", file=sys.stderr)
        return 1
    return 0


def cmd_model_route_enable(args: argparse.Namespace) -> int:
    """Wave 8.6 (`OPS-011` extension): the only way a disabled LLM job
    route ever becomes enabled again -- always an explicit, human-authored
    action with a recorded reason, never automatic."""
    from datetime import UTC, datetime

    from readme_agent.state.git_backend import default_state_backend
    from readme_agent.state.schema import ModelRouteStatusV1

    backend = default_state_backend()
    backend.save_model_route_status(
        ModelRouteStatusV1(
            job=args.job,
            status="enabled",
            reason=args.reason,
            re_enabled_by="cli",
            re_enabled_at=datetime.now(UTC).isoformat(),
        )
    )
    print(f"{args.job}: enabled ({args.reason})")
    return 0


_SCAFFOLD_SECONDARY_LINKS = [
    "docs.aspose.org",
    "docs.aspose.com",
    "reference.aspose.com",
    "releases.aspose.com",
    "blog.aspose.org",
    "kb.aspose.org",
    "forum.aspose.com",
]
_SCAFFOLD_PROHIBITED_TERMS = ["guarantee", "100%", "best in the world", "free forever", "no bugs"]
_SCAFFOLD_LINK_WHITELIST_DOMAINS = [
    "products.aspose.com",
    "docs.aspose.com",
    "reference.aspose.com",
    "releases.aspose.com",
    "products.aspose.org",
    "docs.aspose.org",
    "kb.aspose.org",
    "forum.aspose.com",
]


def _build_scaffold_profile(
    *,
    policy_profile: str,
    license_value: str,
    org_url: str,
    org_family_url: str,
    org_label: str,
    com_url: str,
    com_family_url: str,
    com_label: str,
) -> dict:
    """A dict, dumped via `yaml.safe_dump` -- not a hand-written string
    template. A string template broke live the first time a TODO
    placeholder (which legitimately contains a colon) was substituted in
    unquoted: YAML read the colon as a nested-mapping separator and failed
    to parse its own generated file. `yaml.safe_dump` quotes any scalar
    that needs it, so this class of bug can't recur regardless of what
    text ends up in a value."""
    return {
        "schema_version": 2,
        "policy_profile": policy_profile,
        "required_elements": {
            "license_mentioned": {"detected_license": license_value},
            "products_org_link": {"url": org_url, "family_url": org_family_url, "label": org_label},
            "products_com_link": {
                "url": com_url,
                "family_url": com_family_url,
                "label": com_label,
                "utm": {
                    "utm_source": "github",
                    "utm_medium": "readme",
                    "utm_campaign": "foss-readme-optimizer",
                },
            },
            "relationship_explained": {
                "min_sentences": 2,
                "talking_points": ["open_source_scope", "commercial_upgrade_path"],
            },
        },
        "secondary_links": list(_SCAFFOLD_SECONDARY_LINKS),
        "block": {
            "word_limit": {"min": 20, "max": 120},
            "prohibited_terms": list(_SCAFFOLD_PROHIBITED_TERMS),
            "link_whitelist_domains": list(_SCAFFOLD_LINK_WHITELIST_DOMAINS),
        },
    }


def cmd_scaffold_policy(args: argparse.Namespace) -> int:
    """ONB-004: pre-fill config/policies/<profile>.yml for a registry entry.

    Never invents a business fact (decision #4): every URL and the license
    are live-verified via `registry/policy_facts.py` (GitHub's own license
    classifier + a README text fallback for the license; a real HTTP GET,
    never a string-formatted guess, for every URL). Anything that fails to
    verify is written as an explicit `TODO(human): ...` value rather than a
    plausible-looking guess -- found live 2026-07-22 that guessing here is
    exactly how 9 of 22 policy profiles ended up with a wrong `.com` URL.

    Deliberately does not touch data/products.json: wiring a new profile's
    name into `ecosystem`/`policy_profile` stays a separate, deliberate
    human step per docs/policy-authoring.md -- this command only removes
    the blank-page cost of authoring the YAML itself.
    """
    from pathlib import Path

    from readme_agent import env
    from readme_agent.registry import policy_facts
    from readme_agent.registry.loader import POLICIES_DIR, find_entry

    entry = find_entry(args.repo)
    if entry is None:
        print(f"error: {args.repo} is not in data/products.json -- add it first.", file=sys.stderr)
        return 2

    slug = f"aspose-{entry.family}-foss-{entry.platform}"
    out_path = Path(POLICIES_DIR) / f"{slug}.yml"
    if out_path.exists() and not args.force:
        print(f"error: {out_path} already exists (pass --force to overwrite).", file=sys.stderr)
        return 2

    print(f"Verifying real facts for {args.repo} ({entry.family}/{entry.platform})...")
    facts = policy_facts.verify_repo_facts(args.repo, entry.family, entry.platform, env.gh_token())

    todo = "TODO(human): could not verify automatically -- confirm manually before enabling"
    license_value = facts["license"] or todo
    org_url = (
        facts["org_platform_url"]
        if facts["org_platform_status"] == 200
        else (facts["org_family_url"] if facts["org_family_status"] == 200 else todo)
    )
    com_url = (
        facts["com_platform_url"]
        if facts["com_platform_status"] == 200
        else (facts["com_family_url"] if facts["com_family_status"] == 200 else todo)
    )
    org_family_url = facts["org_family_url"] if facts["org_family_status"] == 200 else todo
    com_family_url = facts["com_family_url"] if facts["com_family_status"] == 200 else todo

    # Matches the exact label convention already used across the 25 existing
    # profiles (net -> .NET, cpp -> Cpp, not a generic .upper()/.capitalize()
    # guess -- found live: a naive length<=3 heuristic wrongly produced "NET"
    # instead of ".NET" for aspose-words-foss-net.yml).
    _PLATFORM_LABELS = {
        "net": ".NET",
        "python": "Python",
        "java": "Java",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "cpp": "Cpp",
        "go": "Go",
        "nodejs": "NodeJS",
    }
    label_platform = _PLATFORM_LABELS.get(entry.platform, entry.platform.capitalize())
    family_title = entry.family.upper() if len(entry.family) <= 3 else entry.family.capitalize()

    import yaml

    profile = _build_scaffold_profile(
        policy_profile=slug,
        license_value=license_value,
        org_url=org_url,
        org_family_url=org_family_url,
        org_label=f"Aspose.{family_title} FOSS for {label_platform}",
        com_url=com_url,
        com_family_url=com_family_url,
        com_label=f"Aspose.{family_title} for {label_platform}",
    )
    content = yaml.safe_dump(profile, sort_keys=False, default_flow_style=False, allow_unicode=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8", newline="\n")

    _checked = [("license", license_value), ("org URL", org_url), ("com URL", com_url)]
    unverified = [k for k, v in _checked if v == todo]
    print(f"Wrote {out_path}")
    if unverified:
        print(f"  UNVERIFIED, needs manual review before enabling: {', '.join(unverified)}")
    print(
        "Not yet wired in: edit data/products.json's entry to set "
        f'"ecosystem": "{entry.platform}", "policy_profile": "{slug}" once reviewed.'
    )
    return 0
