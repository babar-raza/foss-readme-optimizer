"""Current candidate LLM accounting is distinct from revision history."""

from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    record_non_provider_call,
    reset_llm_call_accounting,
    start_llm_call_accounting,
)
from readme_agent.supervisor.candidate_llm_accounting import (
    write_candidate_transaction_llm_accounting,
)


def test_current_candidate_accounting_records_exact_cache_reuse(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    repository = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    revision = "a" * 40
    start_llm_call_accounting(repository, "candidate-run", stage="README_PROCESSING")
    bind_llm_repository_revision(revision, stage="README_PROCESSING")
    try:
        record_non_provider_call(
            job="section_cluster_authoring",
            prompt_id="section_cluster_authoring",
            prompt_sha256="b" * 64,
            model="qwen3-next",
            disposition="cache_reuse",
            request={"packet_hash": "c" * 64},
        )
        fields = write_candidate_transaction_llm_accounting(tmp_path / "bundle")
    finally:
        reset_llm_call_accounting()

    assert fields == {
        "candidate_llm_accounting_status": "EXACT",
        "candidate_llm_run_id": "candidate-run",
        "candidate_llm_provider_call_count": 0,
        "candidate_llm_cache_reuse_count": 1,
        "candidate_llm_calls_by_job": {},
        "candidate_llm_ledger_sha256": fields["candidate_llm_ledger_sha256"],
    }
    ledger = tmp_path / "bundle" / "candidate" / "current-transaction-llm-call-ledger.jsonl"
    summary = tmp_path / "bundle" / "candidate" / "current-transaction-llm-accounting.json"
    assert ledger.is_file() and ledger.read_text(encoding="utf-8").count("\n") == 1
    assert summary.is_file()


def test_candidate_accounting_without_run_context_is_explicit(tmp_path):
    reset_llm_call_accounting()

    assert write_candidate_transaction_llm_accounting(tmp_path / "bundle") == {
        "candidate_llm_accounting_status": "UNAVAILABLE_NO_RUN_CONTEXT"
    }
    assert not (tmp_path / "bundle").exists()
