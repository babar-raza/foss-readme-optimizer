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
"""

from collections.abc import Callable
from types import ModuleType

from readme_agent.capabilities import (
    check_install_path,
    classify_upstream_change,
    detect_readme_gaps,
    domains,
    get_product_facts,
    inspect_repository,
    profile_repository,
)
from readme_agent.capabilities.schema import CapabilityManifest, ExecutionType, PermissionClass
from readme_agent.errors import ConfigError

_MODULES = (
    inspect_repository,
    detect_readme_gaps,
    check_install_path,
    profile_repository,
    get_product_facts,
    classify_upstream_change,
)

# side_effect_class values at or above this index are mutating -- the
# threshold both the fail-closed domain sunset and the EFF-001 gate key off,
# matching PermissionClass's own declared ordering (schema.py).
_MUTATING_PERMISSION_CLASSES = ("local_write", "remote_write")


def _build(
    modules: tuple[ModuleType, ...],
) -> tuple[dict[str, CapabilityManifest], dict[str, Callable[..., dict]]]:
    manifests: dict[str, CapabilityManifest] = {}
    executors: dict[str, Callable[..., dict]] = {}
    for module in modules:
        manifest = module.MANIFEST
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
    return manifests, executors


_MANIFESTS, _EXECUTORS = _build(_MODULES)


def get(capability_id: str) -> CapabilityManifest | None:
    return _MANIFESTS.get(capability_id)


def get_executor(capability_id: str) -> Callable[..., dict] | None:
    return _EXECUTORS.get(capability_id)


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


def all_tool_schemas() -> list[dict]:
    """OpenAI-style tool schemas for every registered capability -- what a
    planner is offered (L6: native tool-calling, proven reliable in Wave 1)."""
    return [m.to_tool_schema() for m in list_all()]
