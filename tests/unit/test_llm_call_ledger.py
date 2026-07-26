import ast
import json
from pathlib import Path

import pytest
import requests
from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.llm import call_transport, live_client
from readme_agent.llm.bundle_accounting import local_bundle_llm_accounting_fields
from readme_agent.llm.call_ledger import (
    append_llm_call_record,
    bind_llm_repository_revision,
    current_llm_accounting_summary,
    load_llm_call_records,
    record_non_provider_call,
    start_llm_call_accounting,
)
from readme_agent.llm.call_schema import LlmCallRecordV1
from readme_agent.llm.fixture_client import FixtureLLMClient
from readme_agent.llm.live_client import LiveLLMClient
from readme_agent.supervisor.local_poc_review_evidence import (
    write_local_poc_no_op_evidence,
)

_REVISION = "a" * 40
_VALID_CONTENT = json.dumps(
    {
        "relationship_paragraph": "This is the free FOSS edition.",
        "talking_points_covered": ["open_source_scope"],
        "claims": {
            "license_name": "MIT",
            "commercial_link_url": "https://products.aspose.com/3d/java/",
        },
    }
)


class _Response:
    def __init__(self, status_code: int, body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body else "")
        self.content = self.text.encode()

    def json(self):
        return self._body


@pytest.fixture
def accounting(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    start_llm_call_accounting("aspose-3d-foss/Aspose.3D-FOSS-for-Java", "run-1")
    bind_llm_repository_revision(_REVISION, stage="FACTS_COLLECTING")
    return tmp_path / "runs" / "llm-calls" / ("aspose-3d-foss__Aspose.3D-FOSS-for-Java/run-1.jsonl")


def test_retry_attempts_and_tokens_reconcile(accounting, monkeypatch):
    calls = 0
    success = {
        "id": "provider-2",
        "model": "gpt-oss",
        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
        "choices": [{"message": {"content": _VALID_CONTENT}}],
    }

    def fake_post(url, json, headers, timeout):
        nonlocal calls
        calls += 1
        return _Response(503, text="retry") if calls == 1 else _Response(200, success)

    monkeypatch.setattr(live_client.requests, "post", fake_post)
    monkeypatch.setattr(live_client.time, "sleep", lambda _: None)
    LiveLLMClient("https://gateway.example/v1?token=must-not-leak", "secret", "gpt-oss").generate(
        [{"role": "user", "content": "private prompt"}]
    )

    records = load_llm_call_records(accounting)
    assert [record.attempt for record in records] == [1, 2]
    assert [record.outcome for record in records] == ["http_error", "success"]
    assert len({record.call_id for record in records}) == 2
    assert len({record.logical_call_id for record in records}) == 1
    summary = current_llm_accounting_summary()
    assert summary.provider_call_count == 2
    assert summary.calls_by_job == {"relationship_explained": 2}
    assert summary.total_tokens is None
    ledger_text = accounting.read_text(encoding="utf-8")
    assert "private prompt" not in ledger_text
    assert "must-not-leak" not in ledger_text
    assert "secret" not in ledger_text


def test_schema_failure_is_a_counted_provider_call(accounting, monkeypatch):
    body = {"choices": [{"message": {"content": '{"wrong": true}'}}]}
    monkeypatch.setattr(live_client.requests, "post", lambda *args, **kwargs: _Response(200, body))

    with pytest.raises(LLMError):
        LiveLLMClient("https://gateway.example/v1", None, "gpt-oss").generate([])

    records = load_llm_call_records(accounting)
    assert len(records) == 1
    assert records[0].outcome == "response_invalid"


def test_timeout_retries_are_each_counted(accounting, monkeypatch):
    monkeypatch.setattr(
        call_transport.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("late")),
    )
    monkeypatch.setattr(live_client.time, "sleep", lambda _: None)
    with pytest.raises(LLMError):
        LiveLLMClient("https://gateway.example/v1", None, "gpt-oss").generate([])
    records = load_llm_call_records(accounting)
    assert len(records) == 3
    assert {record.outcome for record in records} == {"timeout"}


def test_cancellation_is_recorded_before_propagation(accounting, monkeypatch):
    monkeypatch.setattr(
        call_transport.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        LiveLLMClient("https://gateway.example/v1", None, "gpt-oss").generate([])
    records = load_llm_call_records(accounting)
    assert len(records) == 1
    assert records[0].outcome == "cancelled"


def test_fixture_and_cache_are_visible_but_not_provider_calls(accounting, tmp_path):
    fixture = tmp_path / "response.json"
    fixture.write_text(_VALID_CONTENT, encoding="utf-8")
    FixtureLLMClient(fixture).generate([{"role": "user", "content": "fixture"}])
    record_non_provider_call(
        job="plan_readme_composition",
        prompt_id="plan_readme_composition",
        prompt_sha256=None,
        model="cached",
        disposition="cache_reuse",
        request={"fingerprint": "f" * 64},
    )
    summary = current_llm_accounting_summary()
    assert summary.provider_call_count == 0
    assert summary.fixture_call_count == 1
    assert summary.cache_reuse_count == 1


def test_duplicate_call_id_with_conflicting_content_is_rejected(accounting):
    base = {
        "call_id": "same",
        "logical_call_id": "logical",
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "source_revision": _REVISION,
        "run_id": "run-1",
        "campaign_id": "run-1",
        "stage": "FACTS_COLLECTING",
        "job": "draft_product_truth",
        "prompt_id": "draft_product_truth",
        "provider": "gateway",
        "model": "model",
        "attempt": 1,
        "disposition": "provider_call",
        "started_at": "2026-07-26T00:00:00+00:00",
        "finished_at": "2026-07-26T00:00:01+00:00",
        "latency_ms": 1,
        "outcome": "success",
        "request_sha256": "a" * 64,
    }
    append_llm_call_record(LlmCallRecordV1.model_validate(base))
    append_llm_call_record(LlmCallRecordV1.model_validate(base))
    with pytest.raises(RuntimeError, match="conflicting"):
        append_llm_call_record(LlmCallRecordV1.model_validate({**base, "request_sha256": "b" * 64}))


def test_provider_call_requires_versioned_cost_disposition():
    with pytest.raises(ValidationError, match="pricing source and version"):
        LlmCallRecordV1(
            call_id="call",
            logical_call_id="logical",
            org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
            source_revision=_REVISION,
            run_id="run-1",
            campaign_id="run-1",
            stage="FACTS_COLLECTING",
            job="draft_product_truth",
            prompt_id="draft_product_truth",
            provider="gateway",
            model="model",
            attempt=1,
            disposition="provider_call",
            started_at="2026-07-26T00:00:00+00:00",
            finished_at="2026-07-26T00:00:01+00:00",
            latency_ms=1,
            outcome="success",
            request_sha256="a" * 64,
            pricing_source=None,
            pricing_version=None,
        )


def test_manifest_rejects_inconsistent_exact_totals():
    with pytest.raises(ValidationError, match="must equal"):
        RunManifestV2(
            run_id="r",
            org_repo="o/r",
            status="FAILED",
            timestamp="t",
            llm_accounting_status="EXACT",
            llm_call_count=1,
            llm_call_ids=[],
            llm_calls_by_job={"job": 1},
        )


def test_historical_bundle_without_transport_evidence_is_unknown_legacy(accounting, tmp_path):
    bundle = tmp_path / "bundle"
    fields = local_bundle_llm_accounting_fields(
        bundle,
        {"candidate_hash": "historical", "llm_call_count": 0},
    )
    assert fields["llm_accounting_status"] == "UNKNOWN_LEGACY"
    assert fields["llm_call_count"] is None


def test_new_bundle_reconciles_current_provider_record(accounting, monkeypatch, tmp_path):
    body = {"choices": [{"message": {"content": _VALID_CONTENT}}]}
    monkeypatch.setattr(live_client.requests, "post", lambda *args, **kwargs: _Response(200, body))
    LiveLLMClient("https://gateway.example/v1", None, "gpt-oss").generate([])
    fields = local_bundle_llm_accounting_fields(tmp_path / "new-bundle", {})
    assert fields["llm_accounting_status"] == "EXACT"
    assert fields["llm_call_count"] == 1
    assert len(fields["llm_call_ids"]) == 1


def test_no_op_proof_rejects_a_new_provider_call(accounting, monkeypatch, tmp_path):
    body = {"choices": [{"message": {"content": _VALID_CONTENT}}]}
    monkeypatch.setattr(live_client.requests, "post", lambda *args, **kwargs: _Response(200, body))
    LiveLLMClient("https://gateway.example/v1", None, "gpt-oss").generate([])
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text(
        json.dumps({"candidate_hash": "c", "completed_stages": []}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="unchanged README no-op"):
        write_local_poc_no_op_evidence(
            bundle,
            candidate_hash="c",
            agentic_review_reused=True,
        )


def test_all_llm_provider_posts_are_centralized():
    root = Path("src/readme_agent/llm")
    call_sites: list[str] = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "requests"
                and node.func.attr == "post"
            ):
                call_sites.append(path.name)
    assert call_sites == ["call_transport.py"]
