"""Capability registry -- dispatch-table pattern, mirrors
ecosystems/registry.py's `_PARSERS` shape: new capabilities are new entries,
not new call sites.

Repository-profile compatibility filtering (`CAP-002`) is Wave 3's extension
point once RepositoryProfile exists to filter against -- filter_by() only
supports the keyword criteria already meaningful today.

Build-time gates (Decision #33/#26 addendum, `CAP-006`/`EFF-001`): three
additive checks run once, at import time, alongside the existing duplicate-
`capability_id` guard -- domain-membership validation, a fail-closed sunset
on the "unscoped by default" domain grant, and the `EFF-001` idempotency-
declaration gate for mutating capabilities. All three are no-ops today
(`domains.KNOWN_DOMAINS` is empty, no capability declares `local_write`+),
by design -- see `domains.py` and `schema.py`'s `allowed_domains` docstring.

Reconciliation-check resolution (Wave 7, `EFF-001`'s remaining gap): a module
MAY optionally define a module-level `reconciliation_check(arguments: dict)
-> dict | None` callable, resolved the same way `execute` already is --
by attribute name, not a manifest field (avoids putting a bare `Callable` in
the pydantic contract). `effect_ledger.py::dispatch_gated_effect` looks this
up, if present, before concluding a stale `pending` record is unrecoverable.
"""

from collections.abc import Callable
from types import ModuleType
from typing import get_args

from readme_agent.authorization.schema import EffectClass
from readme_agent.capabilities import (
    audit_community_files,
    audit_github_generated_surfaces,
    audit_package_release_surfaces,
    build_presentation_plan,
    check_install_path,
    classify_upstream_change,
    commit_readme_write,
    compare_against_presentation_standard,
    compare_reference_repositories,
    detect_readme_gaps,
    domains,
    get_domain_findings,
    get_product_facts,
    get_template_clone_findings,
    inspect_repository,
    open_presentation_pr,
    prepare_visual_asset,
    profile_repository,
    propose_metadata_changes,
    render_readme_candidate,
    review_visual_asset_accuracy,
    stop,
    verify_package_acquisition,
    verify_prose_quality,
    verify_readme_candidate,
)
from readme_agent.capabilities.compatibility import (
    is_compatible,
    validate_compatibility_declarations,
)
from readme_agent.capabilities.contracts import materialize_contract_models
from readme_agent.capabilities.schema import CapabilityManifest, ExecutionType, PermissionClass
from readme_agent.errors import ConfigError
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.validation.registry import registered_rule_ids

_MODULES = (
    inspect_repository,
    detect_readme_gaps,
    check_install_path,
    profile_repository,
    get_product_facts,
    build_presentation_plan,
    classify_upstream_change,
    render_readme_candidate,
    audit_github_generated_surfaces,
    audit_package_release_surfaces,
    propose_metadata_changes,
    audit_community_files,
    commit_readme_write,
    open_presentation_pr,
    prepare_visual_asset,
    verify_readme_candidate,
    get_domain_findings,
    verify_prose_quality,
    compare_against_presentation_standard,
    compare_reference_repositories,
    review_visual_asset_accuracy,
    get_template_clone_findings,
    verify_package_acquisition,
    stop,
)

# side_effect_class values at or above this index are mutating -- the
# threshold both the fail-closed domain sunset and the EFF-001 gate key off,
# matching PermissionClass's own declared ordering (schema.py).
_MUTATING_PERMISSION_CLASSES = ("local_write", "remote_write")

ReconciliationCheck = Callable[[dict], "dict | None"]
# Wave 8 (`EFF-002` ordering fix, production-reliability pass): a module MAY
# optionally define a module-level `precheck(arguments: dict) -> str | None`,
# resolved the exact same attribute-based way `reconciliation_check` already
# is. A non-`None` return is a cheap, side-effect-free rejection reason --
# `effect_ledger.py::dispatch_gated_effect()` calls it *before* acquiring the
# lock or writing any pending entry, so a caller-side mistake (an
# unacceptable `verification_verdict`, or any other capability-declared
# precondition) fails cheaply instead of leaving a permanently stuck pending
# record behind (the exact latent defect found by direct trace: every one of
# `dispatch_tool_call()`'s own cheap checks -- unknown capability, permission
# denied, domain denied, missing argument -- already ran *after* the pending
# write, not just this new one).
PrecheckFn = Callable[[dict], "str | None"]


def _build(
    modules: tuple[ModuleType, ...],
) -> tuple[
    dict[str, CapabilityManifest],
    dict[str, Callable[..., dict]],
    dict[str, ReconciliationCheck],
    dict[str, PrecheckFn],
]:
    manifests: dict[str, CapabilityManifest] = {}
    executors: dict[str, Callable[..., dict]] = {}
    reconciliation_checks: dict[str, ReconciliationCheck] = {}
    prechecks: dict[str, PrecheckFn] = {}
    for module in modules:
        manifest = materialize_contract_models(module.MANIFEST)
        validate_compatibility_declarations(manifest)
        if manifest.capability_id in manifests:
            # GOVERNANCE.md "Capability and agentic-component lifecycle", rule 2: no silent
            # duplicates -- caught at build time, not left to surface as a runtime surprise.
            raise ConfigError(f"duplicate capability_id {manifest.capability_id!r} in registry")

        unknown_domains = set(manifest.allowed_domains) - domains.KNOWN_DOMAINS
        if unknown_domains:
            raise ConfigError(
                f"{manifest.capability_id!r} declares allowed_domains {sorted(unknown_domains)} "
                f"not registered in domains.KNOWN_DOMAINS"
            )

        # Wave 13.3 (`AUTH-004`): the same build-time membership check as
        # allowed_domains above, for the new, separate effect_classes axis --
        # a typo or stale value here would otherwise surface only as a
        # confusing runtime KeyError-shaped miss deep inside authorized_for().
        unknown_effect_classes = set(manifest.effect_classes) - set(get_args(EffectClass))
        if unknown_effect_classes:
            raise ConfigError(
                f"{manifest.capability_id!r} declares effect_classes "
                f"{sorted(unknown_effect_classes)} not in authorization.schema.EffectClass"
            )

        required_permissions = set(manifest.required_permissions)
        if not required_permissions or manifest.side_effect_class not in required_permissions:
            raise ConfigError(
                f"{manifest.capability_id!r} must declare its side_effect_class "
                f"{manifest.side_effect_class!r} in non-empty required_permissions"
            )

        unknown_validators = set(manifest.validators) - registered_rule_ids()
        if unknown_validators:
            raise ConfigError(
                f"{manifest.capability_id!r} declares unknown validators "
                f"{sorted(unknown_validators)}"
            )

        unknown_evidence_outputs = set(manifest.evidence_outputs) - set(manifest.produced_outputs)
        if unknown_evidence_outputs:
            raise ConfigError(
                f"{manifest.capability_id!r} declares evidence_outputs not present in its "
                f"output contract: {sorted(unknown_evidence_outputs)}"
            )
        if (
            manifest.side_effect_class in _MUTATING_PERMISSION_CLASSES
            and not manifest.evidence_outputs
        ):
            raise ConfigError(
                f"{manifest.capability_id!r} is mutating but declares no evidence_outputs"
            )

        # Fail-closed sunset (Decision #33): once more than one domain is
        # registered, "unscoped" stops meaning "no restriction expressed
        # yet" and starts meaning "explicitly unrestricted across multiple
        # real callers" -- GOVERNANCE.md rule 5 ("explicit and minimal,
        # nothing defaults to a broader class") then applies to this axis
        # too, for any capability dangerous enough to matter.
        if (
            len(domains.KNOWN_DOMAINS) > 1
            and manifest.side_effect_class in _MUTATING_PERMISSION_CLASSES
            and not manifest.allowed_domains
        ):
            raise ConfigError(
                f"{manifest.capability_id!r} is {manifest.side_effect_class!r} but declares no "
                f"allowed_domains -- multiple domains are registered, so an unscoped mutating "
                f"capability is no longer permitted by default"
            )

        # EFF-001 registration gate (Decision #26 addendum): a mutating
        # capability with no idempotency story is exactly the "GitHub
        # Actions re-run duplicates a remote effect" failure mode --
        # rejected here, before it can ever be registered, rather than
        # discovered live.
        if manifest.side_effect_class in _MUTATING_PERMISSION_CLASSES and (
            not manifest.idempotency_inputs or manifest.retry_policy is None
        ):
            raise ConfigError(
                f"{manifest.capability_id!r} is {manifest.side_effect_class!r} but declares no "
                f"idempotency_inputs/retry_policy -- EFF-001 requires both before a mutating "
                f"capability may be registered"
            )

        manifests[manifest.capability_id] = manifest
        executors[manifest.capability_id] = module.execute
        reconciliation_check = getattr(module, "reconciliation_check", None)
        if reconciliation_check is not None:
            reconciliation_checks[manifest.capability_id] = reconciliation_check
        precheck = getattr(module, "precheck", None)
        if precheck is not None:
            prechecks[manifest.capability_id] = precheck
    return manifests, executors, reconciliation_checks, prechecks


_MANIFESTS, _EXECUTORS, _RECONCILIATION_CHECKS, _PRECHECKS = _build(_MODULES)


def get(capability_id: str) -> CapabilityManifest | None:
    return _MANIFESTS.get(capability_id)


def get_executor(capability_id: str) -> Callable[..., dict] | None:
    return _EXECUTORS.get(capability_id)


def get_reconciliation_check(capability_id: str) -> ReconciliationCheck | None:
    return _RECONCILIATION_CHECKS.get(capability_id)


def get_precheck(capability_id: str) -> PrecheckFn | None:
    return _PRECHECKS.get(capability_id)


def list_all() -> list[CapabilityManifest]:
    return list(_MANIFESTS.values())


def filter_by(
    execution_type: ExecutionType | None = None,
    side_effect_class: PermissionClass | None = None,
    category: str | None = None,
) -> list[CapabilityManifest]:
    results = list_all()
    if execution_type is not None:
        results = [m for m in results if m.execution_type == execution_type]
    if side_effect_class is not None:
        results = [m for m in results if m.side_effect_class == side_effect_class]
    if category is not None:
        results = [m for m in results if m.category == category]
    return results


def filter_compatible(profile: RepositoryProfile) -> list[CapabilityManifest]:
    """Return registered capabilities whose declared axes match a repository profile."""

    return [manifest for manifest in list_all() if is_compatible(manifest, profile)]


def all_tool_schemas(caller_domain: str | None = None) -> list[dict]:
    """OpenAI-style tool schemas for every capability a caller with
    `caller_domain` may actually invoke (L6: native tool-calling, proven
    reliable in Wave 1).

    Wave 7 fix (root cause: confirmed by reading the code, not assumed --
    this function used to return every registered capability unconditionally,
    and `supervisor/loop.py`'s general planner, itself unscoped
    (`caller_domain=None`), handed the whole list to the LLM with no domain
    awareness at all). A domain-scoped capability offered to a planner that
    can never legally call it is a guaranteed `rejected_domain_denied` the
    moment the LLM tries -- burning a planning turn nondeterministically,
    since *whether* the LLM tries it is sampling-dependent. That is a
    concrete mechanism by which two runs against the identical, unchanged
    repo state converge in a different number of turns. Latent with the one
    scoped capability that existed before Wave 7 (`classify_upstream_change`,
    which nothing had reason to try); real once Wave 7 registers several
    more, including the one real mutating capability. Filtering here, at the
    single source every caller of this function shares, is cheaper and more
    reliable than trusting every future caller to filter its own copy."""
    return [
        m.to_tool_schema()
        for m in list_all()
        if not m.allowed_domains or caller_domain in m.allowed_domains
    ]
