"""Persist and context-bind immutable registry revisions."""

from __future__ import annotations

from contextvars import ContextVar, Token
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.registry.revision import RegistryRevisionV1

_CURRENT_REGISTRY_REVISION: ContextVar[RegistryRevisionV1 | None] = ContextVar(
    "readme_agent_registry_revision",
    default=None,
)


def write_registry_revision(revision: RegistryRevisionV1) -> Path:
    """Write an immutable revision plus one atomic current pointer."""

    immutable = paths.registry_revision_path(revision.revision_id)
    immutable.parent.mkdir(parents=True, exist_ok=True)
    if immutable.exists():
        stored = RegistryRevisionV1.model_validate_json(immutable.read_text(encoding="utf-8"))
        if stored != revision:
            raise RuntimeError("registry revision identity collision")
    else:
        write_redacted_json(immutable, revision)
    write_redacted_json(paths.current_registry_revision_path(), revision)
    return immutable


def load_current_registry_revision() -> RegistryRevisionV1 | None:
    path = paths.current_registry_revision_path()
    if not path.is_file():
        return None
    return RegistryRevisionV1.model_validate_json(path.read_text(encoding="utf-8"))


def bind_registry_revision(revision: RegistryRevisionV1) -> Token[RegistryRevisionV1 | None]:
    """Bind the immutable portfolio denominator to every member manifest."""

    return _CURRENT_REGISTRY_REVISION.set(revision)


def reset_registry_revision(token: Token[RegistryRevisionV1 | None]) -> None:
    _CURRENT_REGISTRY_REVISION.reset(token)


def current_registry_revision() -> RegistryRevisionV1 | None:
    return _CURRENT_REGISTRY_REVISION.get()
