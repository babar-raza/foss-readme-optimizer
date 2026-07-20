"""Specialist registry (Wave 6, decision #39) -- mirrors
`capabilities/registry.py`'s dispatch-table pattern. Adding a specialist
(Wave 7+) is a new registration here, never a new call site in
`supervisor/loop.py`, which only ever calls `run_domain()`/`all_domains()`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from readme_agent.capabilities import domains
from readme_agent.errors import ConfigError
from readme_agent.specialists import readme_reconciliation
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import DomainStateV1


@dataclass
class SpecialistManifest:
    domain: str
    name: str
    purpose: str
    run: Callable[[str, StateBackend | None], DomainStateV1]


_SPECIALISTS: tuple[SpecialistManifest, ...] = (
    SpecialistManifest(
        domain=readme_reconciliation.DOMAIN,
        name="README reconciliation",
        purpose="Classify upstream README drift against the last accepted state for this domain.",
        run=readme_reconciliation.run,
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
        by_domain[specialist.domain] = specialist
    return by_domain


_BY_DOMAIN = _build(_SPECIALISTS)


def all_domains() -> list[str]:
    return list(_BY_DOMAIN)


def run_domain(domain: str, org_repo: str, backend: StateBackend | None) -> DomainStateV1 | None:
    specialist = _BY_DOMAIN.get(domain)
    if specialist is None:
        return None
    return specialist.run(org_repo, backend)
