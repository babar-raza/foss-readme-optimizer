"""Current-contract safeguards for finalized README promotion."""

import hashlib
from types import SimpleNamespace

import pytest
from governance import promote_finalized_verified_readmes as promotion

from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2

ORG_REPO = "aspose-note-foss/Aspose.Note-FOSS-for-Python"
SOURCE_REVISION = "a" * 40
CANDIDATE_HASH = "b" * 64


class _Backend:
    def __init__(self, state: RunStateV2):
        self.state = state
        self.closed = False
        self.requested: list[str] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        self.closed = True

    def load_many(self, repositories: list[str]):
        self.requested = repositories
        return {
            repository: self.state if repository == ORG_REPO else None
            for repository in repositories
        }


def _no_op_state() -> RunStateV2:
    return RunStateV2(
        org_repo=ORG_REPO,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="NO_OP_PROVEN",
            source_revision=SOURCE_REVISION,
            candidate_hash=CANDIDATE_HASH,
        ),
    )


def test_default_state_source_reads_authoritative_backend(monkeypatch):
    state = _no_op_state()
    backend = _Backend(state)
    monkeypatch.setattr(promotion, "default_state_backend", lambda: backend)

    loaded = promotion._current_states(None, [ORG_REPO, "org/missing"])

    assert backend.requested == [ORG_REPO, "org/missing"]
    assert backend.closed is True
    assert loaded == {ORG_REPO: state.model_dump(mode="json")}


def test_explicit_state_snapshot_does_not_open_authoritative_backend(tmp_path, monkeypatch):
    monkeypatch.setattr(
        promotion,
        "_states_from_git_snapshot",
        lambda path: {ORG_REPO: {"snapshot": path.as_posix()}},
    )
    monkeypatch.setattr(
        promotion,
        "default_state_backend",
        lambda: pytest.fail("explicit snapshots must not open the live backend"),
    )

    loaded = promotion._current_states(tmp_path, [ORG_REPO])

    assert loaded == {ORG_REPO: {"snapshot": tmp_path.as_posix()}}


def test_state_source_record_does_not_persist_backend_or_external_path(monkeypatch, tmp_path):
    monkeypatch.delenv("README_AGENT_STATE_REMOTE", raising=False)
    assert promotion._state_source_record(None) == {
        "kind": "authoritative_durable_backend",
        "location": "origin",
    }

    monkeypatch.setenv("README_AGENT_STATE_REMOTE", "https://secret@example.invalid/state.git")
    assert promotion._state_source_record(None) == {
        "kind": "authoritative_durable_backend",
        "location": "environment_override",
    }
    assert promotion._state_source_record(tmp_path) == {
        "kind": "explicit_offline_git_snapshot",
        "location": "external_offline_snapshot",
    }


def test_manifest_reconciliation_removes_stale_campaign_acceptance(monkeypatch):
    manifest = {key: {"stale": True} for key in promotion.OBSOLETE_AGGREGATE_ACCEPTANCE_KEYS}
    manifest.update(
        {
            "template_sha256": "old-template",
            "reviewer_standard_sha256": "old-reviewer",
        }
    )
    monkeypatch.setattr(promotion, "document_template_hash", lambda: "current-template")
    monkeypatch.setattr(
        promotion,
        "separated_reviewer_standard_hash",
        lambda: "current-reviewer",
    )

    promotion._reconcile_current_manifest_metadata(manifest)

    assert not set(promotion.OBSOLETE_AGGREGATE_ACCEPTANCE_KEYS) & manifest.keys()
    assert manifest["template_sha256"] == "current-template"
    assert manifest["reviewer_standard_sha256"] == "current-reviewer"


def test_raw_no_op_is_rejected_when_current_acceptance_contract_is_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(
        promotion,
        "require_listed",
        lambda _repository: SimpleNamespace(
            policy_profile="aspose-note-foss-python",
            ecosystem="python",
            family="Note",
        ),
    )
    monkeypatch.setattr(
        promotion,
        "compute_control_plane_fingerprint",
        lambda _policy: "c" * 64,
    )
    monkeypatch.setattr(
        promotion,
        "evaluate_completed_local_poc_cache",
        lambda *_args, **_kwargs: SimpleNamespace(
            reusable=False,
            mismatch_reasons=[
                "fact_acceptance_recollection_component_changed",
                "manifest_local_verification_contract_hash_mismatch",
            ],
            cache_key="d" * 64,
        ),
    )

    with pytest.raises(
        promotion.StaleAcceptanceError,
        match="fact_acceptance_recollection_component_changed",
    ):
        promotion._validated_entry(
            ORG_REPO,
            _no_op_state().model_dump(mode="json"),
            tmp_path,
            "python",
        )


def test_superseded_entry_removes_only_checksum_bound_committed_artifacts(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    output_root = repo_root / "evidence"
    directory = output_root / "repositories/python/note"
    directory.mkdir(parents=True)
    readme = directory / "README.md"
    provenance = directory / "provenance.json"
    readme.write_bytes(b"# Candidate\n")
    provenance.write_bytes(b"{}\n")
    monkeypatch.setattr(promotion, "REPO_ROOT", repo_root)

    promotion._remove_committed_entry(
        {
            "repository": ORG_REPO,
            "platform": "python",
            "source_revision": SOURCE_REVISION,
            "candidate_sha256": hashlib.sha256(readme.read_bytes()).hexdigest(),
            "committed_readme": readme.relative_to(repo_root).as_posix(),
            "committed_artifacts": {
                "provenance.json": [
                    provenance.relative_to(repo_root).as_posix(),
                    hashlib.sha256(provenance.read_bytes()).hexdigest(),
                ]
            },
        },
        output_root,
    )

    assert not readme.exists()
    assert not provenance.exists()


def test_legacy_evidence_migration_is_bounded_to_exact_repository_directory(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    output_root = repo_root / "evidence"
    legacy = output_root / ORG_REPO.replace("/", "__")
    unrelated = output_root / "unrelated"
    legacy.mkdir(parents=True)
    unrelated.mkdir(parents=True)
    (legacy / "README.md").write_text("stale", encoding="utf-8")
    (unrelated / "keep.txt").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(promotion, "REPO_ROOT", repo_root)

    promotion._remove_legacy_evidence(ORG_REPO, output_root)

    assert not legacy.exists()
    assert (unrelated / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_durable_artifact_contract_contains_required_review_evidence():
    assert {
        "ORIGINAL-README.md",
        "README.patch",
        "product-facts.json",
        "provenance.json",
        "readme-document-plan.json",
        "claim-map.json",
        "deterministic-validation.json",
        "independent-agent-review.json",
        "final-verdict.json",
        "no-op-proof.json",
        "llm-call-ledger.jsonl",
        "runtime-manifest.json",
    } <= promotion.COMMITTED_ARTIFACTS.keys()
