"""Reconcile run-scoped LLM records into revision-addressed README bundles."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.llm.call_ledger import (
    current_llm_call_context,
    load_llm_call_records,
    summarize_llm_call_records,
)
from readme_agent.llm.call_schema import LlmCallRecordV1

_LEDGER_NAME = "llm-call-ledger.jsonl"


def _append_missing(path: Path, incoming: list[LlmCallRecordV1]) -> None:
    existing = load_llm_call_records(path)
    by_id = {record.call_id: record for record in existing}
    additions: list[LlmCallRecordV1] = []
    for record in incoming:
        prior = by_id.get(record.call_id)
        if prior is not None and prior != record:
            raise RuntimeError(
                f"README bundle LLM ledger has conflicting call ID: {record.call_id}"
            )
        if prior is None:
            by_id[record.call_id] = record
            additions.append(record)
    if not additions:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        for record in additions:
            stream.write(
                json.dumps(
                    record.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
        stream.flush()


def local_bundle_llm_accounting_fields(
    bundle_dir: Path,
    prior_manifest: dict,
) -> dict:
    """Return fail-closed cumulative accounting fields for one README revision."""

    bundle_ledger = bundle_dir / _LEDGER_NAME
    context = current_llm_call_context()
    if context is not None:
        run_ledger = Path(context.ledger_path)
        incoming = [
            record
            for record in load_llm_call_records(run_ledger)
            if record.org_repo == context.org_repo
            and record.source_revision == context.source_revision
        ]
        _append_missing(bundle_ledger, incoming)

    legacy_unknown = (
        bool(prior_manifest)
        and "llm_accounting_status" not in prior_manifest
        and not bundle_ledger.is_file()
    )
    if legacy_unknown:
        return {
            "llm_accounting_status": "UNKNOWN_LEGACY",
            "llm_call_count": None,
            "llm_call_ids": [],
            "llm_calls_by_job": {},
            "llm_fixture_call_count": None,
            "llm_cache_reuse_count": None,
            "llm_total_tokens": None,
            "llm_ledger_sha256": None,
        }

    summary = summarize_llm_call_records(
        load_llm_call_records(bundle_ledger),
        ledger_path=bundle_ledger,
    )
    return {
        "llm_accounting_status": summary.status,
        "llm_call_count": summary.provider_call_count,
        "llm_call_ids": summary.call_ids,
        "llm_calls_by_job": summary.calls_by_job,
        "llm_fixture_call_count": summary.fixture_call_count,
        "llm_cache_reuse_count": summary.cache_reuse_count,
        "llm_prompt_tokens": summary.prompt_tokens,
        "llm_completion_tokens": summary.completion_tokens,
        "llm_total_tokens": summary.total_tokens,
        "llm_ledger_sha256": summary.ledger_sha256,
    }
