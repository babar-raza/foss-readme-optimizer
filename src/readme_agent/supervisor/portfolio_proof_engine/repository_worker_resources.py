"""Concurrency gates for repository-worker resources."""

from __future__ import annotations

import threading
import time


class _ConcurrencyGate:
    """Bounded semaphore with an observed high-water mark. One instance per resource class."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self.limit = limit
        self._semaphore = threading.Semaphore(limit)
        self._lock = threading.Lock()
        self._active = 0
        self.observed_max = 0

    def reset_observed_max(self) -> None:
        with self._lock:
            self.observed_max = 0

    def acquire(self) -> float:
        """Blocks until a slot is free; returns the time spent waiting, in seconds."""

        started = time.monotonic()
        self._semaphore.acquire()
        waited = time.monotonic() - started
        with self._lock:
            self._active += 1
            self.observed_max = max(self.observed_max, self._active)
        return waited

    def release(self) -> None:
        with self._lock:
            self._active -= 1
        self._semaphore.release()
