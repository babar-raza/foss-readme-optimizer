"""Authorization, evaluation, and policy-governance CLI handlers."""

import argparse
import sys


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
