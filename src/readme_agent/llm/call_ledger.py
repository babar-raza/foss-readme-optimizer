"""Store and reconcile redacted append-only LLM call records."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.llm.call_schema import LlmAccountingSummaryV1, LlmCallRecordV1


class LlmCallContextV1(BaseModel):
    """Repository/run identity injected once, then refined after snapshot capture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    source_revision: str = "PRE_SNAPSHOT"
    run_id: str
    campaign_id: str
    stage: str
    ledger_path: str


_CONTEXT: ContextVar[LlmCallContextV1 | None] = ContextVar("llm_call_context", default=None)
_WRITE_LOCK = threading.Lock()


def start_llm_call_accounting(
    org_repo: str,
    run_id: str,
    *,
    campaign_id: str | None = None,
    stage: str = "PREFLIGHT",
) -> None:
    """Start or replace the accounting context for one canonical repository run."""

    safe_repo = org_repo.replace("/", "__")
    ledger_path = paths.runs_dir() / "llm-calls" / safe_repo / f"{run_id}.jsonl"
    _CONTEXT.set(
        LlmCallContextV1(
            org_repo=org_repo,
            run_id=run_id,
            campaign_id=campaign_id or run_id,
            stage=stage,
            ledger_path=str(ledger_path),
        )
    )


def bind_llm_repository_revision(source_revision: str, *, stage: str = "SUPERVISING") -> None:
    """Bind subsequent calls to the immutable revision discovered by supervision."""

    context = _CONTEXT.get()
    if context is not None:
        _CONTEXT.set(
            context.model_copy(update={"source_revision": source_revision, "stage": stage})
        )


def set_llm_stage(stage: str) -> None:
    context = _CONTEXT.get()
    if context is not None:
        _CONTEXT.set(context.model_copy(update={"stage": stage}))


def current_llm_call_context() -> LlmCallContextV1 | None:
    return _CONTEXT.get()


def canonical_call_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def known_prompt_hash(prompt_id: str) -> str | None:
    """Resolve a governed prompt hash without inventing one for transport-only jobs."""

    from readme_agent.llm import prompt_registry

    return prompt_registry.prompt_hash(prompt_id) if prompt_registry.get(prompt_id) else None


def append_llm_call_record(record: LlmCallRecordV1) -> None:
    """Append one validated record, rejecting conflicting or duplicate call IDs."""

    context = _CONTEXT.get()
    if context is None:
        return
    path = Path(context.ledger_path)
    line = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    with _WRITE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            for existing in load_llm_call_records(path):
                if existing.call_id == record.call_id:
                    if existing != record:
                        raise RuntimeError(
                            "LLM call ledger duplicate ID has conflicting content: "
                            f"{record.call_id}"
                        )
                    return
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")
            stream.flush()


def record_non_provider_call(
    *,
    job: str,
    prompt_id: str,
    prompt_sha256: str | None,
    model: str,
    disposition: Literal["fixture", "cache_reuse"],
    request: Any,
) -> None:
    """Record fixture use or an explicit cache reuse without inflating provider totals."""

    context = _CONTEXT.get()
    if context is None:
        return
    now = datetime.now(UTC).isoformat()
    call_id = str(uuid.uuid4())
    append_llm_call_record(
        LlmCallRecordV1(
            call_id=call_id,
            logical_call_id=call_id,
            org_repo=context.org_repo,
            source_revision=context.source_revision,
            run_id=context.run_id,
            campaign_id=context.campaign_id,
            stage=context.stage,
            job=job,
            prompt_id=prompt_id,
            prompt_sha256=prompt_sha256,
            provider="fixture" if disposition == "fixture" else "cache",
            model=model,
            attempt=0,
            disposition=disposition,
            started_at=now,
            finished_at=now,
            latency_ms=0,
            outcome=disposition,
            request_sha256=canonical_call_hash(request),
            cost_unavailable_reason="not_a_provider_call",
        )
    )


def load_llm_call_records(path: Path) -> list[LlmCallRecordV1]:
    if not path.is_file():
        return []
    records: list[LlmCallRecordV1] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = LlmCallRecordV1.model_validate_json(line)
        if record.call_id in seen:
            raise RuntimeError(f"duplicate LLM call ID at {path}:{line_number}: {record.call_id}")
        seen.add(record.call_id)
        records.append(record)
    return records


def summarize_llm_call_records(
    records: list[LlmCallRecordV1],
    *,
    ledger_path: Path | None = None,
) -> LlmAccountingSummaryV1:
    provider = [record for record in records if record.disposition == "provider_call"]
    fixture = [record for record in records if record.disposition == "fixture"]
    cache = [record for record in records if record.disposition == "cache_reuse"]
    by_job: dict[str, int] = {}
    for record in provider:
        by_job[record.job] = by_job.get(record.job, 0) + 1
    token_known = all(record.total_tokens is not None for record in provider)
    digest = (
        hashlib.sha256(ledger_path.read_bytes()).hexdigest()
        if ledger_path is not None and ledger_path.is_file()
        else None
    )
    return LlmAccountingSummaryV1(
        status="EXACT",
        provider_call_count=len(provider),
        fixture_call_count=len(fixture),
        cache_reuse_count=len(cache),
        call_ids=sorted(record.call_id for record in provider),
        calls_by_job=dict(sorted(by_job.items())),
        prompt_tokens=(
            sum(record.prompt_tokens or 0 for record in provider) if token_known else None
        ),
        completion_tokens=(
            sum(record.completion_tokens or 0 for record in provider) if token_known else None
        ),
        total_tokens=sum(record.total_tokens or 0 for record in provider) if token_known else None,
        ledger_path=str(ledger_path) if ledger_path is not None else None,
        ledger_sha256=digest,
    )


def current_llm_accounting_summary() -> LlmAccountingSummaryV1:
    context = _CONTEXT.get()
    if context is None:
        return LlmAccountingSummaryV1(status="UNKNOWN_LEGACY")
    path = Path(context.ledger_path)
    return summarize_llm_call_records(load_llm_call_records(path), ledger_path=path)
