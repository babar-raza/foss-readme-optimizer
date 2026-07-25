"""Run-local execution intent that must reach nested specialist graphs."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_PROPOSAL_ONLY: ContextVar[bool] = ContextVar(
    "readme_agent_proposal_only",
    default=False,
)


def proposal_only_active() -> bool:
    """Return whether effects must stop at an in-memory/local proposal."""
    return _PROPOSAL_ONLY.get()


@contextmanager
def proposal_only_scope(enabled: bool = True) -> Iterator[None]:
    """Propagate local-POC proposal-only intent through nested graph calls."""
    token = _PROPOSAL_ONLY.set(enabled)
    try:
        yield
    finally:
        _PROPOSAL_ONLY.reset(token)
