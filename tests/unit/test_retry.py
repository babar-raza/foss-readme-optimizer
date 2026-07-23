"""Typed retry policies, jitter, and GitHub rate-limit delay tests."""

from datetime import UTC, datetime

import pytest
import requests

from readme_agent.retry import (
    RETRY_POLICIES,
    RetryableOperationError,
    github_retry_after_seconds,
    run_http_with_retry,
    run_with_retry,
)


def test_every_external_operation_has_a_bounded_policy():
    assert set(RETRY_POLICIES) == {
        "github_read",
        "llm_call",
        "state_cas",
        "clone",
        "package_registry",
        "github_write",
    }
    assert all(policy.max_attempts <= 5 for policy in RETRY_POLICIES.values())


def test_only_explicitly_retryable_failures_are_retried():
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RetryableOperationError("transient")
        return "ok"

    assert run_with_retry("state_cas", operation, sleep=lambda _seconds: None) == "ok"
    assert calls == 3


def test_caller_may_tighten_the_policy_attempt_bound():
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        raise RetryableOperationError("still transient")

    with pytest.raises(RetryableOperationError):
        run_with_retry(
            "state_cas",
            operation,
            sleep=lambda _seconds: None,
            max_attempts=2,
        )
    assert calls == 2


def test_non_retryable_failure_is_not_replayed():
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError):
        run_with_retry("github_write", operation, sleep=lambda _seconds: None)
    assert calls == 1


def test_retry_after_header_wins():
    assert github_retry_after_seconds(429, {"Retry-After": "17"}) == 17


def test_primary_limit_uses_reset_epoch():
    now = datetime(2026, 7, 23, tzinfo=UTC)
    reset = int(now.timestamp()) + 30
    assert (
        github_retry_after_seconds(
            403,
            {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(reset)},
            now=now,
        )
        == 30
    )


def test_429_without_headers_waits_one_minute():
    assert github_retry_after_seconds(429, {}) == 60


def test_unmarked_403_is_not_misclassified_as_rate_limiting():
    assert github_retry_after_seconds(403, {}) is None


def test_unmarked_github_403_is_returned_without_replay():
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        response = requests.Response()
        response.status_code = 403
        return response

    response = run_http_with_retry(
        "github_read",
        operation,
        retryable_statuses={403, 429, 502, 503, 504},
        honor_github_rate_limit=True,
        sleep=lambda _seconds: None,
    )
    assert response.status_code == 403
    assert calls == 1
