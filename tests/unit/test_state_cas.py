"""Bounded compare-and-swap state update behavior."""

from readme_agent.state.backend import SaveResult
from readme_agent.state.cas import save_state_patch
from readme_agent.state.schema import RunStateV2


class _Backend:
    def __init__(self, state: RunStateV2 | None = None):
        self.state = state
        self.save_calls = 0

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.state

    def save(self, org_repo: str, state: RunStateV2, expected_version: int | None) -> SaveResult:
        self.save_calls += 1
        current_version = self.state.state_version if self.state is not None else None
        if expected_version != current_version:
            return SaveResult("stale", current_version)
        next_version = (current_version or 0) + 1
        self.state = state.model_copy(update={"state_version": next_version})
        return SaveResult("saved", next_version)


class _StaleOnceBackend(_Backend):
    def save(self, org_repo: str, state: RunStateV2, expected_version: int | None) -> SaveResult:
        if self.save_calls == 0:
            self.save_calls += 1
            assert self.state is not None
            self.state = self.state.model_copy(
                update={"state_version": self.state.state_version + 1, "last_run_id": "concurrent"}
            )
            return SaveResult("stale", self.state.state_version)
        return super().save(org_repo, state, expected_version)


def test_existing_exact_no_op_does_not_save_or_advance_version():
    original = RunStateV2(org_repo="acme/widget", state_version=7)
    backend = _Backend(original)

    result = save_state_patch(backend, "acme/widget", lambda state: state)

    assert result is original
    assert result.state_version == 7
    assert backend.state is original
    assert backend.save_calls == 0


def test_equal_copy_is_an_exact_no_op_without_save():
    original = RunStateV2(org_repo="acme/widget", state_version=3)
    backend = _Backend(original)

    result = save_state_patch(backend, "acme/widget", lambda state: state.model_copy())

    assert result == original
    assert result.state_version == 3
    assert backend.save_calls == 0


def test_new_record_is_saved_even_when_patch_returns_default_base():
    backend = _Backend()

    result = save_state_patch(backend, "acme/widget", lambda state: state)

    assert backend.save_calls == 1
    assert result.state_version == 1
    assert backend.state == result


def test_material_change_still_uses_cas_save():
    original = RunStateV2(org_repo="acme/widget", state_version=4)
    backend = _Backend(original)

    result = save_state_patch(
        backend,
        "acme/widget",
        lambda state: state.model_copy(update={"last_run_id": "run-1"}),
    )

    assert backend.save_calls == 1
    assert result.state_version == 5
    assert result.last_run_id == "run-1"


def test_material_patch_is_recomputed_and_saved_after_stale_cas():
    original = RunStateV2(org_repo="acme/widget", state_version=4)
    backend = _StaleOnceBackend(original)

    result = save_state_patch(
        backend,
        "acme/widget",
        lambda state: state.model_copy(update={"last_run_id": "run-1"}),
        max_retries=2,
    )

    assert backend.save_calls == 2
    assert result.state_version == 6
    assert result.last_run_id == "run-1"
