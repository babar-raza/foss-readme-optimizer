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
    from readme_agent.preflight.runner import format_summary, run_preflight_for_repo
    from readme_agent.registry.self_heal import heal_registry_drift

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

    state_backend = _durable_state_backend(args)

    domain = getattr(args, "domain", None)
    if domain is not None:
        return _cmd_supervise_single_domain(args.repo, domain, state_backend)

    from readme_agent.supervisor.loop import supervise_repo

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
