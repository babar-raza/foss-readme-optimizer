"""Specialist registry (Wave 6, decision #39) -- mirrors
`capabilities/registry.py`'s dispatch-table pattern. Adding a specialist
(Wave 7+) is a new registration here, never a new call site in
`supervisor/loop.py`, which only ever calls `run_domain()`/`all_domains()`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from readme_agent.capabilities import domains
from readme_agent.errors import ConfigError
from readme_agent.specialists import (
    community_files_presentation,
    cross_surface_validation,
    github_generated_surface_audit,
    independent_verification,
    metadata_presentation,
    package_release_audit,
    presentation_benchmarking,
    readme_presentation,
    readme_reconciliation,
    visual_preparation,
)
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import DomainStateV1


@dataclass
class SpecialistManifest:
    domain: str
    name: str
    purpose: str
    run: Callable[[str, StateBackend | None, str | None], DomainStateV1]
    # Wave 7f: declares which other domains' recorded `DomainStateV1` this
    # specialist reads directly (e.g. `cross_surface_validation`'s own
    # `backend.load()` comparison) -- checked at build time, below, so
    # "registered last -> sees siblings' this-run state" (mechanically true
    # today from dict insertion order alone) becomes an enforced invariant
    # instead of an unstated assumption a future reordering could silently
    # break. Empty for every specialist that dispatches its own capability
    # and never reads a sibling's state.
    depends_on: tuple[str, ...] = ()


_SPECIALISTS: tuple[SpecialistManifest, ...] = (
    SpecialistManifest(
        domain=readme_reconciliation.DOMAIN,
        name="README reconciliation",
        purpose="Classify upstream README drift against the last accepted state for this domain.",
        run=readme_reconciliation.run,
    ),
    SpecialistManifest(
        domain=github_generated_surface_audit.DOMAIN,
        name="GitHub-generated-surface audit",
        purpose="Audit contributors/languages/stars/forks/watchers/open-issues -- class E, "
        "audit-only forever, no renderer or write path.",
        run=github_generated_surface_audit.run,
    ),
    SpecialistManifest(
        domain=package_release_audit.DOMAIN,
        name="Package/release audit",
        purpose="Audit GitHub Releases and live package-registry resolution -- class D, "
        "audit/handoff only, no renderer or write path.",
        run=package_release_audit.run,
    ),
    SpecialistManifest(
        domain=metadata_presentation.DOMAIN,
        name="Metadata presentation",
        purpose="Propose (never apply) description/homepage/topics improvements -- class B, "
        "dry-run only, no GitHub API PATCH ever attempted this wave.",
        run=metadata_presentation.run,
    ),
    SpecialistManifest(
        domain=community_files_presentation.DOMAIN,
        name="Community-files presentation",
        purpose="Audit LICENSE/CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/SUPPORT presence and "
        "GitHub Community Profile API recognition, plus proven-source candidate content for a "
        "missing CODE_OF_CONDUCT.md -- class 1, audit + prepare only, no write this wave.",
        run=community_files_presentation.run,
    ),
    SpecialistManifest(
        domain=cross_surface_validation.DOMAIN,
        name="Cross-surface validation",
        purpose="Read sibling domains' already-recorded state directly (no capability dispatch "
        "of its own) and flag two specialists independently disagreeing about the same fact -- "
        "today: README's license claim vs. the LICENSE file's own detected classification.",
        run=cross_surface_validation.run,
        depends_on=cross_surface_validation.DEPENDS_ON,
    ),
    SpecialistManifest(
        domain=readme_presentation.DOMAIN,
        name="README presentation",
        purpose="Render then commit the README candidate -- the one real mutating capability "
        "this project registers. Only writes/commits when a real durable backend is supplied; "
        "a real local git commit only ever happens when mode == 'full'.",
        run=readme_presentation.run,
    ),
    SpecialistManifest(
        domain=visual_preparation.DOMAIN,
        name="Visual preparation",
        purpose="Validate an existing image asset or prepare a real, freshly-generated candidate "
        "banner from product facts -- prepare-only, no embed-write into README.md this wave.",
        run=visual_preparation.run,
    ),
    SpecialistManifest(
        domain=presentation_benchmarking.DOMAIN,
        name="Presentation benchmarking",
        purpose="Compare the current README against docs/presentation-standard.md's codified "
        "rules via a structured LLM analysis call -- evidence, never a blocking gate (Wave 8.6).",
        run=presentation_benchmarking.run,
    ),
    SpecialistManifest(
        domain=independent_verification.DOMAIN,
        name="Independent verification",
        purpose="Post-hoc cross-domain audit -- evidence completeness across every other "
        "registered domain (Wave 8b); requirement mapping and adversarial cross-domain checks "
        "extend this in Wave 8c. The other VER-001 facet (the in-graph pre-apply gate) is wired "
        "directly into readme_presentation's own graph, not here.",
        run=independent_verification.run,
        depends_on=independent_verification.DEPENDS_ON,
    ),
)


def _build(
    specialists: tuple[SpecialistManifest, ...],
) -> dict[str, SpecialistManifest]:
    by_domain: dict[str, SpecialistManifest] = {}
    for specialist in specialists:
        if specialist.domain in by_domain:
            raise ConfigError(f"duplicate specialist domain {specialist.domain!r} in registry")
        if specialist.domain not in domains.KNOWN_DOMAINS:
            raise ConfigError(
                f"specialist domain {specialist.domain!r} is not registered in "
                f"capabilities/domains.py::KNOWN_DOMAINS"
            )
        # Wave 7f ordering gate: `all_domains()`/`supervisor/loop.py`'s
        # specialist-tier loop dispatch in registration (tuple/dict
        # insertion) order, nothing else -- a specialist declaring
        # `depends_on` is relying on its dependencies' `record` nodes having
        # already run and saved. Checked here, not just documented, so a
        # future reorder or mid-list insertion fails loudly at import time
        # instead of silently reading stale or absent sibling state.
        unregistered_deps = set(specialist.depends_on) - set(by_domain)
        if unregistered_deps:
            raise ConfigError(
                f"specialist domain {specialist.domain!r} declares depends_on "
                f"{sorted(unregistered_deps)} which are not yet registered earlier in "
                f"specialists/registry.py::_SPECIALISTS -- dependencies must be registered "
                f"before the specialist that reads their state"
            )
        by_domain[specialist.domain] = specialist

    # Wave 7 completeness gate: the existing checks above only ever caught
    # one direction (a specialist's domain must exist in KNOWN_DOMAINS). The
    # reverse -- a domain added to KNOWN_DOMAINS with no specialist ever
    # registered for it -- failed silently: that domain would just never
    # produce a DomainStateV1, discoverable only much later by absence,
    # unlike every other registration mistake in this codebase (duplicate
    # capability_id, unknown allowed_domains, missing idempotency_inputs),
    # which already fails loudly at import time. As domain registration
    # spreads across three files (domains.py, specialists/registry.py,
    # capabilities/registry.py) and grows from 1 to 8 domains across Wave 7,
    # a half-finished registration becomes more likely and deserves the same
    # fail-loud treatment as every other registry mistake here.
    orphaned_domains = domains.KNOWN_DOMAINS - set(by_domain)
    if orphaned_domains:
        raise ConfigError(
            f"domain(s) {sorted(orphaned_domains)} are registered in "
            f"capabilities/domains.py::KNOWN_DOMAINS but have no matching specialist in "
            f"specialists/registry.py::_SPECIALISTS"
        )
    return by_domain


_BY_DOMAIN = _build(_SPECIALISTS)


def all_domains() -> list[str]:
    return list(_BY_DOMAIN)


def run_domain(
    domain: str, org_repo: str, backend: StateBackend | None, current_revision: str | None = None
) -> DomainStateV1 | None:
    """`current_revision` (Wave 8.6, `ORC-003` reversal prerequisite):
    threaded through to the specialist's own `run()`, which threads it to
    its `_record_node()`'s `save_domain()`/`save_domain_with_failure_
    tracking()` call -- stamps `upstream_revision_at_accept` at the actual
    persistence point. `None` (every pre-Wave-8.6 caller) means "don't
    stamp," preserving today's behavior exactly."""
    specialist = _BY_DOMAIN.get(domain)
    if specialist is None:
        return None
    return specialist.run(org_repo, backend, current_revision)
