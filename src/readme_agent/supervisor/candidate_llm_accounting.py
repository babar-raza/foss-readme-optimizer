"""Bind candidate evidence to the exact LLM activity of its current transaction."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import sha256_file, write_redacted_json, write_redacted_text
from readme_agent.llm.call_ledger import (
    current_llm_call_context,
    load_llm_call_records,
    summarize_llm_call_records,
)


def write_candidate_transaction_llm_accounting(bundle_dir: Path) -> dict:
    """Write the redacted current-run ledger and return manifest accounting fields."""

    context = current_llm_call_context()
    if context is None:
        return {"candidate_llm_accounting_status": "UNAVAILABLE_NO_RUN_CONTEXT"}
    records = [
        record
        for record in load_llm_call_records(Path(context.ledger_path))
        if record.org_repo == context.org_repo
        and record.source_revision == context.source_revision
        and record.run_id == context.run_id
    ]
    ledger_path = bundle_dir / "candidate" / "current-transaction-llm-call-ledger.jsonl"
    write_redacted_text(
        ledger_path,
        "".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
    )
    summary = summarize_llm_call_records(records, ledger_path=ledger_path)
    summary_payload = {
        "schema_version": 1,
        "scope": "current_candidate_transaction",
        "org_repo": context.org_repo,
        "source_revision": context.source_revision,
        "run_id": context.run_id,
        "campaign_id": context.campaign_id,
        "stage": context.stage,
        "summary": summary.model_dump(mode="json"),
    }
    write_redacted_json(
        bundle_dir / "candidate" / "current-transaction-llm-accounting.json",
        summary_payload,
    )
    return {
        "candidate_llm_accounting_status": summary.status,
        "candidate_llm_run_id": context.run_id,
        "candidate_llm_provider_call_count": summary.provider_call_count,
        "candidate_llm_cache_reuse_count": summary.cache_reuse_count,
        "candidate_llm_calls_by_job": summary.calls_by_job,
        "candidate_llm_ledger_sha256": sha256_file(ledger_path)[0],
    }


__all__ = ["write_candidate_transaction_llm_accounting"]
