"""Typed retry policies shared by external-operation boundaries."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, TypeVar

import requests
from pydantic import BaseModel, Field
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt
from tenacity.wait import wait_random_exponential

OperationClass = Literal[
    "github_read",
    "llm_call",
    "state_cas",
    "clone",
    "package_registry",
    "github_write",
]
T = TypeVar("T")


class RetryPolicyV1(BaseModel):
    operation_class: OperationClass
    max_attempts: int = Field(ge=1, le=10)
    initial_seconds: float = Field(ge=0)
    maximum_seconds: float = Field(ge=0)
    jitter: bool = True


RETRY_POLICIES: dict[OperationClass, RetryPolicyV1] = {
    "github_read": RetryPolicyV1(
        operation_class="github_read",
        max_attempts=4,
        initial_seconds=1,
        maximum_seconds=60,
    ),
    "llm_call": RetryPolicyV1(
        operation_class="llm_call",
        max_attempts=3,
        initial_seconds=1,
        maximum_seconds=20,
    ),
    "state_cas": RetryPolicyV1(
        operation_class="state_cas",
        max_attempts=5,
        initial_seconds=0.05,
        maximum_seconds=2,
    ),
    "clone": RetryPolicyV1(
        operation_class="clone",
        max_attempts=3,
        initial_seconds=2,
        maximum_seconds=30,
    ),
    "package_registry": RetryPolicyV1(
        operation_class="package_registry",
        max_attempts=3,
        initial_seconds=1,
        maximum_seconds=20,
    ),
    "github_write": RetryPolicyV1(
        operation_class="github_write",
        max_attempts=3,
        initial_seconds=2,
        maximum_seconds=60,
    ),
}


class RetryableOperationError(Exception):
    """An explicitly retryable boundary failure with optional server delay."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class _WaitPolicy:
    def __init__(self, policy: RetryPolicyV1):
        self._fallback = wait_random_exponential(
            multiplier=policy.initial_seconds,
            max=policy.maximum_seconds,
        )
        self._maximum = policy.maximum_seconds

    def __call__(self, retry_state) -> float:
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        retry_after = getattr(exception, "retry_after_seconds", None)
        if retry_after is not None:
            return min(max(float(retry_after), 0.0), self._maximum)
        return float(self._fallback(retry_state))


def run_with_retry(
    operation_class: OperationClass,
    operation: Callable[[], T],
    *,
    sleep: Callable[[float], None] | None = None,
    max_attempts: int | None = None,
) -> T:
    """Run only explicitly retryable failures under the named bounded policy."""

    policy = RETRY_POLICIES[operation_class]
    kwargs: dict[str, Any] = {}
    if sleep is not None:
        kwargs["sleep"] = sleep
    retrying = Retrying(
        stop=stop_after_attempt(max_attempts or policy.max_attempts),
        wait=_WaitPolicy(policy),
        retry=retry_if_exception_type(RetryableOperationError),
        reraise=True,
        **kwargs,
    )
    return retrying(operation)


def github_retry_after_seconds(
    status_code: int,
    headers: dict[str, str],
    *,
    now: datetime | None = None,
) -> float | None:
    """Honor GitHub Retry-After/reset headers for 403/429 responses."""

    if status_code not in {403, 429}:
        return None
    normalized = {key.lower(): value for key, value in headers.items()}
    retry_after = normalized.get("retry-after")
    if retry_after is not None:
        try:
            return max(float(retry_after), 0.0)
        except ValueError:
            return None
    if normalized.get("x-ratelimit-remaining") != "0":
        return 60.0 if status_code == 429 else None
    reset = normalized.get("x-ratelimit-reset")
    if reset is None:
        return 60.0
    try:
        reset_at = datetime.fromtimestamp(float(reset), tz=UTC)
    except ValueError:
        return 60.0
    return max((reset_at - (now or datetime.now(UTC))).total_seconds(), 0.0)


def run_http_with_retry(
    operation_class: OperationClass,
    operation: Callable[[], requests.Response],
    *,
    retryable_statuses: set[int],
    honor_github_rate_limit: bool = False,
    sleep: Callable[[float], None] | None = None,
) -> requests.Response:
    """Apply one typed policy to retryable transport and HTTP failures."""

    def attempt() -> requests.Response:
        try:
            response = operation()
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise RetryableOperationError(f"network error: {exc}") from exc
        if response.status_code in retryable_statuses:
            retry_after = (
                github_retry_after_seconds(
                    response.status_code,
                    dict(getattr(response, "headers", {})),
                )
                if honor_github_rate_limit
                else None
            )
            if honor_github_rate_limit and response.status_code == 403 and retry_after is None:
                # A permission/auth 403 is permanent for this credential.
                # Replaying it would hide configuration errors behind minutes
                # of backoff; only explicit rate-limit headers make it retryable.
                return response
            raise RetryableOperationError(
                f"HTTP {response.status_code}",
                retry_after_seconds=retry_after,
            )
        return response

    return run_with_retry(operation_class, attempt, sleep=sleep)
