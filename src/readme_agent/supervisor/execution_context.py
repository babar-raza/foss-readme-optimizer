"""Run-local execution intent that must reach nested specialist graphs."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from readme_agent.supervisor.stage_limit import ReadmePocStageLimitV1

_PROPOSAL_ONLY: ContextVar[bool] = ContextVar(
    "readme_agent_proposal_only",
    default=False,
)
_README_POC_STAGE_LIMIT: ContextVar[ReadmePocStageLimitV1 | None] = ContextVar(
    "readme_agent_readme_poc_stage_limit",
    default=None,
)


def proposal_only_active() -> bool:
    """Return whether effects must stop at an in-memory/local proposal."""
    return _PROPOSAL_ONLY.get()


def readme_poc_stage_limit_active() -> ReadmePocStageLimitV1 | None:
    """Return the typed local boundary nested specialist graphs must honor."""

    return _README_POC_STAGE_LIMIT.get()


@contextmanager
def proposal_only_scope(enabled: bool = True) -> Iterator[None]:
    """Propagate local-POC proposal-only intent through nested graph calls."""
    token = _PROPOSAL_ONLY.set(enabled)
    try:
        yield
    finally:
        _PROPOSAL_ONLY.reset(token)


@contextmanager
def readme_poc_stage_limit_scope(
    stage: ReadmePocStageLimitV1 | None,
) -> Iterator[None]:
    """Propagate one stage ceiling without turning it into a process global."""

    token = _README_POC_STAGE_LIMIT.set(stage)
    try:
        yield
    finally:
        _README_POC_STAGE_LIMIT.reset(token)
