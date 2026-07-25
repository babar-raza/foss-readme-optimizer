"""Bind one verified ProductFactsV2 graph to every consumer in a logical run."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from readme_agent.facts.schema_v2 import ProductFactsV2

_ACTIVE_PRODUCT_FACTS: ContextVar[ProductFactsV2 | None] = ContextVar(
    "readme_agent_active_product_facts",
    default=None,
)


def current_product_facts(org_repo: str | None = None) -> ProductFactsV2 | None:
    """Return the run-scoped verified graph, optionally enforcing repository identity."""
    facts = _ACTIVE_PRODUCT_FACTS.get()
    if facts is not None and org_repo is not None and facts.org_repo != org_repo:
        raise RuntimeError(
            f"active product facts belong to {facts.org_repo!r}, not requested {org_repo!r}"
        )
    return facts


@contextmanager
def product_facts_scope(facts: ProductFactsV2) -> Iterator[ProductFactsV2]:
    """Make one immutable graph authoritative for nested fact consumers."""
    token = _ACTIVE_PRODUCT_FACTS.set(facts)
    try:
        yield facts
    finally:
        _ACTIVE_PRODUCT_FACTS.reset(token)
