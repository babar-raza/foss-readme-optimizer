"""Backend-independent durable-state interface (`MEM-003`): the chosen
backend (`state/git_backend.py`) can be evaluated and swapped without
changing callers. `SaveResult`/`Lock` are internal return values, not
serialized contracts -- plain dataclasses, mirroring `validation/result.py`'s
`RuleResult` (contrast `schema.py`'s pydantic `RunStateV1`, which *is*
serialized).
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from readme_agent.state.schema import RunStateV1

SaveOutcome = Literal["saved", "stale", "lock_held"]


@dataclass
class SaveResult:
    outcome: SaveOutcome
    new_version: int | None


@dataclass
class Lock:
    org_repo: str
    holder_id: str
    leased_until: str


class StateBackend(Protocol):
    def load(self, org_repo: str) -> RunStateV1 | None: ...

    def save(self, org_repo: str, state: RunStateV1, expected_version: int | None) -> SaveResult:
        """CAS: rejected with `outcome="stale"` if the backend's current
        `state_version` no longer matches `expected_version`.
        `expected_version=None` is only valid for the first-ever write to a
        new `org_repo`."""
        ...

    def acquire_lock(self, org_repo: str) -> Lock | None:
        """Per-repository lease (`MEM-002`). `None` means another holder has
        an unexpired lease -- callers must not proceed as if they hold it."""
        ...

    def release_lock(self, lock: Lock) -> None: ...
