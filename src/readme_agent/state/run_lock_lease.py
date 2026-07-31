"""Renew and fence one long-running supervisor lease."""

from __future__ import annotations

from threading import Event, Thread

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import Lock, StateBackend

DEFAULT_RUN_LOCK_RENEW_INTERVAL_SECONDS = 240.0


class RunLockLeaseGuard:
    """Keep one run lock alive and fail closed if durable ownership changes."""

    def __init__(
        self,
        backend: StateBackend,
        lock: Lock,
        *,
        renew_interval_seconds: float = DEFAULT_RUN_LOCK_RENEW_INTERVAL_SECONDS,
    ) -> None:
        if renew_interval_seconds <= 0:
            raise ValueError("run-lock renewal interval must be positive")
        self._backend = backend
        self._lock = lock
        self._renew_interval_seconds = renew_interval_seconds
        self._stop = Event()
        self._failure: str | None = None
        self._thread = Thread(
            target=self._renew_until_stopped,
            name=f"readme-agent-run-lock-{lock.org_repo.replace('/', '-')}",
            daemon=True,
        )

    @property
    def lock(self) -> Lock:
        return self._lock

    def __enter__(self) -> RunLockLeaseGuard:
        self._thread.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
        if self._thread.is_alive():
            self._failure = "run-lock renewal worker did not terminate"

    def assert_held(self) -> None:
        """Fence a lifecycle transition against the fresh durable holder."""

        if self._failure is not None:
            raise StateBackendError(self._failure)
        if not self._backend.run_lock_still_held(self._lock):
            raise StateBackendError("run-lock ownership was lost before a durable transition")

    def _renew_until_stopped(self) -> None:
        while not self._stop.wait(self._renew_interval_seconds):
            try:
                renewed = self._backend.renew_run_lock(self._lock)
            except Exception as exc:  # noqa: BLE001 - persisted failure must fence the run
                self._failure = f"run-lock renewal failed: {exc}"
                return
            if renewed is None:
                self._failure = "run-lock renewal lost durable ownership"
                return
            self._lock = renewed
