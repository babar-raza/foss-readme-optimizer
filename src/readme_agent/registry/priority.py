"""Load and apply the governed portfolio ecosystem execution priority."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from readme_agent.errors import ConfigError
from readme_agent.registry.models import ProductEntry

PLATFORM_PRIORITIES_PATH = Path("data/platform_priorities.json")
SupportedEcosystem = Literal["python", "net", "java", "cpp", "typescript", "rust", "go"]
_SUPPORTED_ECOSYSTEMS = {"python", "net", "java", "cpp", "typescript", "rust", "go"}


class PlatformPriorityV1(BaseModel):
    """Complete ordered execution policy for the supported ecosystems."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    execution_order: list[SupportedEcosystem]

    @field_validator("execution_order")
    @classmethod
    def _is_complete_without_duplicates(
        cls,
        value: list[SupportedEcosystem],
    ) -> list[SupportedEcosystem]:
        if len(value) != len(set(value)):
            raise ValueError("execution_order contains duplicate ecosystems")
        if set(value) != _SUPPORTED_ECOSYSTEMS:
            missing = sorted(_SUPPORTED_ECOSYSTEMS - set(value))
            extra = sorted(set(value) - _SUPPORTED_ECOSYSTEMS)
            raise ValueError(
                f"execution_order must cover every supported ecosystem; "
                f"missing={missing}, extra={extra}"
            )
        return value


def load_platform_priority(
    path: Path = PLATFORM_PRIORITIES_PATH,
) -> PlatformPriorityV1:
    """Load the user-governed ecosystem order and fail closed on drift."""

    if not path.exists():
        raise ConfigError(f"{path} not found (run from the repo root?)")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    try:
        return PlatformPriorityV1.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{path} is malformed: {exc}") from exc


def order_entries_by_platform_priority(
    entries: tuple[ProductEntry, ...],
    *,
    policy: PlatformPriorityV1 | None = None,
) -> tuple[ProductEntry, ...]:
    """Order known ecosystems by policy while preserving registry order within each."""

    selected_policy = policy or load_platform_priority()
    rank: dict[str, int] = {
        ecosystem: position for position, ecosystem in enumerate(selected_policy.execution_order)
    }

    def _sort_key(indexed: tuple[int, ProductEntry]) -> tuple[int, int]:
        index, entry = indexed
        ecosystem = getattr(entry, "ecosystem", None)
        ecosystem_rank = rank.get(ecosystem, len(rank)) if isinstance(ecosystem, str) else len(rank)
        return ecosystem_rank, index

    return tuple(entry for _index, entry in sorted(enumerate(entries), key=_sort_key))
