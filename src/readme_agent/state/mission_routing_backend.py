"""Route mission authority and repository lifecycle records to their owning backends."""

from __future__ import annotations

from readme_agent.state.backend import Lock, SaveResult, StateBackend
from readme_agent.state.schema import ModelRouteStatusV1, RunStateV1, RunStateV2


class MissionRoutingBackend:
    """Keep mission writes central while reading repository lifecycle from its runtime store."""

    def __init__(self, mission_backend: StateBackend, lifecycle_backend: StateBackend) -> None:
        self._mission = mission_backend
        self._lifecycle = lifecycle_backend

    @property
    def mission_backend(self) -> StateBackend:
        return self._mission

    @property
    def lifecycle_backend(self) -> StateBackend:
        return self._lifecycle

    @staticmethod
    def _is_mission_key(org_repo: str) -> bool:
        return org_repo.startswith("mission/")

    def _backend_for_key(self, org_repo: str) -> StateBackend:
        return self._mission if self._is_mission_key(org_repo) else self._lifecycle

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self._backend_for_key(org_repo).load(org_repo)

    def load_many(self, org_repos: list[str]) -> dict[str, RunStateV2 | None]:
        mission_keys = [item for item in org_repos if self._is_mission_key(item)]
        lifecycle_keys = [item for item in org_repos if not self._is_mission_key(item)]
        loaded: dict[str, RunStateV2 | None] = {}
        for backend, keys in (
            (self._mission, mission_keys),
            (self._lifecycle, lifecycle_keys),
        ):
            bulk = getattr(backend, "load_many", None)
            if callable(bulk):
                loaded.update(bulk(keys))
            else:
                loaded.update({key: backend.load(key) for key in keys})
        return {key: loaded.get(key) for key in org_repos}

    def save(
        self,
        org_repo: str,
        state: RunStateV1 | RunStateV2,
        expected_version: int | None,
    ) -> SaveResult:
        return self._backend_for_key(org_repo).save(org_repo, state, expected_version)

    def acquire_lock(self, org_repo: str) -> Lock | None:
        return self._backend_for_key(org_repo).acquire_lock(org_repo)

    def release_lock(self, lock: Lock) -> None:
        self._backend_for_key(lock.org_repo).release_lock(lock)

    def lock_still_held(self, lock: Lock) -> bool:
        return self._backend_for_key(lock.org_repo).lock_still_held(lock)

    def acquire_run_lock(self, org_repo: str) -> Lock | None:
        return self._backend_for_key(org_repo).acquire_run_lock(org_repo)

    def renew_run_lock(self, lock: Lock) -> Lock | None:
        return self._backend_for_key(lock.org_repo).renew_run_lock(lock)

    def run_lock_still_held(self, lock: Lock) -> bool:
        return self._backend_for_key(lock.org_repo).run_lock_still_held(lock)

    def release_run_lock(self, lock: Lock) -> None:
        self._backend_for_key(lock.org_repo).release_run_lock(lock)

    def load_model_route_status(self, job: str) -> ModelRouteStatusV1 | None:
        return self._mission.load_model_route_status(job)

    def save_model_route_status(self, status: ModelRouteStatusV1) -> None:
        self._mission.save_model_route_status(status)

    def close(self) -> None:
        for backend in (self._mission, self._lifecycle):
            close = getattr(backend, "close", None)
            if callable(close):
                close()
