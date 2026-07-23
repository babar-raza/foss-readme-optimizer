import json
import re

from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.evidence.writer import (
    generate_run_id,
    sha256_file,
    unified_diff,
    write_evidence,
    write_run_manifest_v2,
)
from readme_agent.state.schema import SurfaceFreshnessContractV1


class TestGenerateRunId:
    def test_matches_the_documented_format(self):
        run_id = generate_run_id()
        assert re.match(r"^\d{8}-\d{6}-[0-9a-f]{4}$", run_id)

    def test_two_calls_produce_different_ids(self):
        assert generate_run_id() != generate_run_id()


class TestSha256File:
    def test_crlf_and_lf_files_hash_identically(self, tmp_path):
        lf_file = tmp_path / "lf.txt"
        crlf_file = tmp_path / "crlf.txt"
        lf_file.write_bytes(b"line1\nline2\n")
        crlf_file.write_bytes(b"line1\r\nline2\r\n")

        digest_lf, _ = sha256_file(lf_file)
        digest_crlf, _ = sha256_file(crlf_file)

        assert digest_lf == digest_crlf


class TestUnifiedDiff:
    def test_no_changes_produces_empty_diff(self):
        assert unified_diff("same\n", "same\n") == ""

    def test_changes_are_reflected(self):
        diff = unified_diff("line1\nline2\n", "line1\nline2\nline3\n")
        assert "+line3" in diff


class TestWriteEvidence:
    def test_writes_expected_files_and_manifest(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        evidence_dir = tmp_path / "evidence" / "run1"

        write_evidence(
            evidence_dir,
            run_id="run1",
            org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
            mode="full",
            status="GENERATED",
            facts={"org_repo": "x"},
            facts_hash="abc123",
            llm_mode="fixture",
            llm_calls=["relationship_explained"],
            llm_request=[{"role": "user", "content": "hi"}],
            llm_response={"relationship_paragraph": "hello"},
            baseline_readme="# Title\n",
            work_readme="# Title\n\nmore\n",
            rendered_spans={"callout": "some callout"},
            validation_results=[],
            push_block_detail="push_url='DISABLED'",
        )

        assert (evidence_dir / "manifest.json").exists()
        assert (evidence_dir / "facts.json").exists()
        assert (evidence_dir / "llm_request.json").exists()
        assert (evidence_dir / "llm_response.json").exists()
        assert (evidence_dir / "block.md").exists()
        assert (evidence_dir / "diff.patch").exists()
        assert (evidence_dir / "validation_report.json").exists()
        assert (evidence_dir / "sha256sums.txt").exists()

        manifest = json.loads((evidence_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["run_id"] == "run1"
        assert manifest["status"] == "GENERATED"
        # LLM-015: usage must be visible in evidence, not just minimized.
        assert manifest["llm_call_count"] == 1
        assert manifest["llm_calls"] == ["relationship_explained"]

    def test_secret_like_values_are_redacted_in_written_files(self, tmp_path):
        evidence_dir = tmp_path / "evidence" / "run2"

        write_evidence(
            evidence_dir,
            run_id="run2",
            org_repo="x/y",
            mode="dry_run",
            status="GENERATED",
            facts={"note": "leaked key: sk-abcdefghij1234567890"},
            facts_hash="abc123",
            llm_mode="fixture",
            llm_calls=[],
            llm_request=None,
            llm_response=None,
            baseline_readme="# Title\n",
            work_readme="# Title\n",
            rendered_spans={},
            validation_results=[],
            push_block_detail=None,
        )

        facts_text = (evidence_dir / "facts.json").read_text(encoding="utf-8")
        assert "sk-abcdefghij1234567890" not in facts_text
        assert "[REDACTED]" in facts_text


class TestWriteRunManifestV2:
    """Wave 13.1 (`EVID-001`): the single, canonical `manifest.json` writer
    for `supervisor/loop.py::supervise_repo()`'s evidence bundle."""

    def test_writes_a_valid_json_manifest(self, tmp_path):
        manifest = RunManifestV2(
            run_id="run1",
            org_repo="acme/widget",
            status="CONVERGED_APPLIED",
            timestamp="2026-07-23T00:00:00+00:00",
            control_plane_fingerprint="fp1",
            upstream_revision="abc123",
            domain_coverage_complete=True,
            surface_freshness={
                "metadata_presentation": SurfaceFreshnessContractV1(
                    surface_id="metadata_presentation",
                    authoritative_source="github_api",
                    ttl_seconds=3600,
                )
            },
        )

        write_run_manifest_v2(tmp_path, manifest)

        written = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert written["run_id"] == "run1"
        assert written["control_plane_fingerprint"] == "fp1"
        assert written["upstream_revision"] == "abc123"
        assert written["domain_coverage_complete"] is True
        assert written["surface_freshness"]["metadata_presentation"]["ttl_seconds"] == 3600
        # Not yet populated by anything -- explicit null, not omitted or faked.
        assert written["authorization_record_id"] is None
        assert written["trigger_dedup_key"] is None

    def test_secret_like_values_in_the_manifest_are_redacted(self, tmp_path):
        manifest = RunManifestV2(
            run_id="run1",
            org_repo="acme/widget",
            status="BLOCKED",
            timestamp="t",
            upstream_revision="sk-abcdefghij1234567890",
        )

        write_run_manifest_v2(tmp_path, manifest)

        manifest_text = (tmp_path / "manifest.json").read_text(encoding="utf-8")
        assert "sk-abcdefghij1234567890" not in manifest_text
        assert "[REDACTED]" in manifest_text

    def test_atomic_write_leaves_no_tmp_file_behind(self, tmp_path):
        manifest = RunManifestV2(
            run_id="run1", org_repo="acme/widget", status="CONVERGED_NO_CHANGE", timestamp="t"
        )
        write_run_manifest_v2(tmp_path, manifest)
        assert not (tmp_path / "manifest.json.tmp").exists()
