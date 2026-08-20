"""Enforced ceiling on concurrent provider (LLM) calls -- default 2, per EXECUTION BOUNDS.

Dispatch to repositories in this engine stays serial through the existing, already-serial
`commands_supervision._cmd_supervise_registry` call (a deliberate design decision -- see the
plan's "Real concurrent multi-repository execution is not authorized..." note): this gate exists
so the ceiling is real and enforced *now*, and is ready the moment true concurrent multi-repository
dispatch is separately authorized (`plans/master.md` decision #95). Deterministic, read-only
classification work may still use a small bounded local thread pool (`run_deterministic_fanout`):
that carries none of the coordination risk real provider concurrency would, since it touches no
shared mutable state.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import TypeVar

DEFAULT_MAX_PROVIDER_CONCURRENCY = 2

T = TypeVar("T")
R = TypeVar("R")


class ProviderConcurrencyGate:
    """A bounded semaphore with an assertable, currently-observed concurrency high-water mark."""

    def __init__(self, max_concurrent: int = DEFAULT_MAX_PROVIDER_CONCURRENCY) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._lock = threading.Lock()
        self._active = 0
        self.observed_max_concurrent = 0

    @contextmanager
    def acquire(self) -> Iterator[None]:
        self._semaphore.acquire()
        try:
            with self._lock:
                self._active += 1
                self.observed_max_concurrent = max(self.observed_max_concurrent, self._active)
            yield
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()


def run_deterministic_fanout(
    items: Iterable[T],
    worker: Callable[[T], R],
    *,
    max_workers: int,
) -> list[R]:
    """Bounded local parallelism for read-only, non-provider classification work only."""

    materialized = list(items)
    if not materialized:
        return []
    if max_workers <= 1:
        return [worker(item) for item in materialized]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(worker, materialized))
