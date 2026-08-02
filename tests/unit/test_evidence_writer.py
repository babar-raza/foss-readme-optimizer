import json
import re
from types import SimpleNamespace

import pytest

from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.evidence.writer import (
    generate_run_id,
    refresh_sha256sums,
    sha256_file,
    unified_diff,
    verify_sha256sums,
    write_evidence,
    write_run_manifest_v2,
)
from readme_agent.state.schema import SurfaceFreshnessContractV1


def _repository_snapshot(org_repo: str, source_revision: str, snapshot_root: str):
    from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1

    return RepositorySnapshotV1(
        org_repo=org_repo,
        source_revision=source_revision,
        snapshot_root=snapshot_root,
        inventory_sha256="b" * 64,
        captured_at="2026-08-02T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url=f"https://example.invalid/{org_repo}.git",
            git_tree_sha256="b" * 64,
        ),
    )


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


class TestChecksumInventory:
    def test_exact_inventory_passes_and_corruption_fails(self, tmp_path):
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        artifact = evidence_dir / "artifact.json"
        artifact.write_text('{"status":"accepted"}\n', encoding="utf-8")

        refresh_sha256sums(evidence_dir)

        assert verify_sha256sums(evidence_dir) is True
        artifact.write_text('{"status":"corrupted"}\n', encoding="utf-8")
        assert verify_sha256sums(evidence_dir) is False


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


class TestFactsStageEvidence:
    def test_loads_only_the_snapshot_bound_to_durable_lifecycle(self, tmp_path, monkeypatch):
        import readme_agent.paths as paths_module
        from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
        from readme_agent.supervisor.facts_stage_evidence import load_facts_stage_snapshot

        source_revision = "a" * 40
        snapshot = _repository_snapshot("org/repo", source_revision, str(tmp_path.resolve()))
        monkeypatch.setattr(paths_module, "readme_poc_root", lambda: tmp_path / "readme-poc")
        revision_path = (
            paths_module.readme_poc_repository_dir("org", "repo", source_revision)
            / "source"
            / "revision.json"
        )
        revision_path.parent.mkdir(parents=True)
        revision_path.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
        lifecycle = ReadmePocLifecycleStateV2(
            status="FACTS_READY",
            source_revision=source_revision,
        )

        loaded = load_facts_stage_snapshot("org/repo", lifecycle)

        assert loaded == snapshot

    @pytest.mark.parametrize("failure", ["missing", "repository_mismatch", "revision_mismatch"])
    def test_fails_closed_when_snapshot_does_not_match_lifecycle(
        self, tmp_path, monkeypatch, failure
    ):
        import readme_agent.paths as paths_module
        from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
        from readme_agent.supervisor.facts_stage_evidence import load_facts_stage_snapshot

        source_revision = "a" * 40
        monkeypatch.setattr(paths_module, "readme_poc_root", lambda: tmp_path / "readme-poc")
        revision_path = (
            paths_module.readme_poc_repository_dir("org", "repo", source_revision)
            / "source"
            / "revision.json"
        )
        if failure != "missing":
            snapshot = _repository_snapshot(
                "other/repo" if failure == "repository_mismatch" else "org/repo",
                "c" * 40 if failure == "revision_mismatch" else source_revision,
                str(tmp_path.resolve()),
            )
            revision_path.parent.mkdir(parents=True)
            revision_path.write_text(
                snapshot.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
        lifecycle = ReadmePocLifecycleStateV2(
            status="FACTS_READY",
            source_revision=source_revision,
        )

        with pytest.raises(RuntimeError, match="facts-stage snapshot"):
            load_facts_stage_snapshot("org/repo", lifecycle)

    def test_manifest_binds_trigger_to_the_same_upstream_revision(self, tmp_path, monkeypatch):
        import readme_agent.supervisor.evidence as evidence_module
        from readme_agent.state.lifecycle_schema import TriggerEnvelopeV2
        from readme_agent.supervisor.task import TaskGraph

        source_revision = "a" * 40
        trigger = TriggerEnvelopeV2(
            provider_event_id="event-1",
            event_type="cli_manual",
            repository_scope="org/repo",
            dedup_key="dedup-1",
        )
        monkeypatch.setattr(
            evidence_module,
            "current_lifecycle_recorder",
            lambda: SimpleNamespace(envelope=trigger, checkpoints=lambda: []),
        )

        evidence_module.write_supervise_evidence(
            tmp_path,
            "run-1",
            "org/repo",
            "STAGE_COMPLETE",
            TaskGraph(),
            [],
            upstream_revision=source_revision,
        )

        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["upstream_revision"] == source_revision
        assert manifest["trigger"]["source_revision"] == source_revision

    def test_manifest_rejects_a_conflicting_trigger_revision(self, tmp_path, monkeypatch):
        import readme_agent.supervisor.evidence as evidence_module
        from readme_agent.state.lifecycle_schema import TriggerEnvelopeV2
        from readme_agent.supervisor.task import TaskGraph

        trigger = TriggerEnvelopeV2(
            provider_event_id="event-1",
            event_type="cli_manual",
            repository_scope="org/repo",
            source_revision="b" * 40,
            dedup_key="dedup-1",
        )
        monkeypatch.setattr(
            evidence_module,
            "current_lifecycle_recorder",
            lambda: SimpleNamespace(envelope=trigger, checkpoints=lambda: []),
        )

        with pytest.raises(RuntimeError, match="conflicts with the trigger envelope"):
            evidence_module.write_supervise_evidence(
                tmp_path,
                "run-1",
                "org/repo",
                "STAGE_COMPLETE",
                TaskGraph(),
                [],
                upstream_revision="a" * 40,
            )
