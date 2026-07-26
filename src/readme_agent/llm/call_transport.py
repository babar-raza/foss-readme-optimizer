"""Instrument the physical HTTP boundary for LLM provider attempts."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import requests

from readme_agent.llm.call_ledger import (
    append_llm_call_record,
    canonical_call_hash,
    current_llm_call_context,
)
from readme_agent.llm.call_schema import CallOutcome, LlmCallRecordV1


def _response_metadata(response: requests.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        body = {}
    usage = body.get("usage") if isinstance(body, dict) else {}
    usage = usage if isinstance(usage, dict) else {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    if (
        total_tokens is None
        and isinstance(prompt_tokens, int)
        and isinstance(completion_tokens, int)
    ):
        total_tokens = prompt_tokens + completion_tokens
    return {
        "provider_request_id": body.get("id") if isinstance(body, dict) else None,
        "prompt_tokens": prompt_tokens if isinstance(prompt_tokens, int) else None,
        "completion_tokens": (completion_tokens if isinstance(completion_tokens, int) else None),
        "total_tokens": total_tokens if isinstance(total_tokens, int) else None,
    }


class ProviderCallSession:
    """Group transport retries and semantic retries under one logical call ID."""

    def __init__(
        self,
        *,
        job: str,
        prompt_id: str,
        prompt_sha256: str | None,
        provider: str,
        model: str,
    ):
        self.logical_call_id = str(uuid.uuid4())
        self.job = job
        self.prompt_id = prompt_id
        self.prompt_sha256 = prompt_sha256
        self.provider = provider
        self.model = model
        self._attempt = 0
        self._pending: dict[int, tuple[str, str, str, float]] = {}

    def post(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> requests.Response:
        """Perform and account one physical provider attempt without storing content."""

        self._attempt += 1
        call_id = str(uuid.uuid4())
        request_sha256 = canonical_call_hash(payload)
        started_at = datetime.now(UTC).isoformat()
        started = time.monotonic()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        except requests.Timeout:
            self._record(
                call_id, request_sha256, started_at, started, "timeout", error_class="Timeout"
            )
            raise
        except requests.ConnectionError:
            self._record(
                call_id,
                request_sha256,
                started_at,
                started,
                "connection_error",
                error_class="ConnectionError",
            )
            raise
        except (KeyboardInterrupt, SystemExit) as exc:
            self._record(
                call_id,
                request_sha256,
                started_at,
                started,
                "cancelled",
                error_class=type(exc).__name__,
            )
            raise
        if response.status_code != 200:
            self._record(
                call_id,
                request_sha256,
                started_at,
                started,
                "http_error",
                response=response,
            )
        else:
            self._pending[id(response)] = (call_id, request_sha256, started_at, started)
        return response

    def finalize(
        self,
        response: requests.Response,
        outcome: Literal["success", "response_invalid"],
    ) -> None:
        pending = self._pending.pop(id(response), None)
        if pending is None:
            return
        call_id, request_sha256, started_at, started = pending
        self._record(
            call_id,
            request_sha256,
            started_at,
            started,
            outcome,
            response=response,
        )

    def _record(
        self,
        call_id: str,
        request_sha256: str,
        started_at: str,
        started: float,
        outcome: CallOutcome,
        *,
        response: requests.Response | None = None,
        error_class: str | None = None,
    ) -> None:
        context = current_llm_call_context()
        if context is None:
            return
        content = (
            getattr(response, "content", str(getattr(response, "text", "")).encode("utf-8"))
            if response is not None
            else b""
        )
        metadata = _response_metadata(response) if response is not None else {}
        append_llm_call_record(
            LlmCallRecordV1(
                call_id=call_id,
                logical_call_id=self.logical_call_id,
                org_repo=context.org_repo,
                source_revision=context.source_revision,
                run_id=context.run_id,
                campaign_id=context.campaign_id,
                stage=context.stage,
                job=self.job,
                prompt_id=self.prompt_id,
                prompt_sha256=self.prompt_sha256,
                provider=self.provider,
                model=self.model,
                attempt=self._attempt,
                disposition="provider_call",
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
                latency_ms=max(0, round((time.monotonic() - started) * 1000)),
                outcome=outcome,
                http_status=response.status_code if response is not None else None,
                request_sha256=request_sha256,
                response_sha256=(
                    hashlib.sha256(content).hexdigest() if response is not None else None
                ),
                error_class=error_class,
                **metadata,
            )
        )
