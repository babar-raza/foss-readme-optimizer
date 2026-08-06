"""Current-contract safeguards for finalized README promotion."""

import hashlib
from types import SimpleNamespace

import pytest
from governance import finalized_promotion_layout as layout
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


def _zero_cohort(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data = repo_root / "data"
    data.mkdir(parents=True)
    (data / "products.json").write_text(
        '[{"repo_url":"https://github.com/org/zero-python","platform":"python"}]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(promotion, "REPO_ROOT", repo_root)
    monkeypatch.setattr(promotion, "document_template_hash", lambda: "t" * 64)
    monkeypatch.setattr(promotion, "separated_reviewer_standard_hash", lambda: "r" * 64)
    monkeypatch.setattr(promotion, "_current_states", lambda _state_git, _repositories: {})
    return repo_root / "finalized"


def _file_bytes(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


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


def test_zero_candidate_clean_root_is_checksum_valid_and_byte_idempotent(tmp_path, monkeypatch):
    output_root = _zero_cohort(tmp_path, monkeypatch)

    first = promotion.promote(None, output_root, None)
    first_bytes = _file_bytes(output_root)
    (output_root / "repositories").rmdir()
    second = promotion.promote(None, output_root, None)
    stale = output_root / "repositories/python/stale-repository/revision/candidate"
    stale.mkdir(parents=True)
    for platform in ("java", "net"):
        (output_root / "repositories" / platform).mkdir()
    third = promotion.promote(None, output_root, None)

    assert first["promoted_verified_readmes"] == 0
    assert first["promoted_python_readmes"] == 0
    assert second == first
    assert third == first
    assert _file_bytes(output_root) == first_bytes
    assert promotion.verify_sha256sums(output_root) is True
    assert (output_root / "repositories").is_dir()
    assert list((output_root / "repositories").iterdir()) == []


def test_windows_cleanup_prunes_a_multilevel_stale_empty_tree(tmp_path):
    output_root = tmp_path / "finalized"
    repositories = output_root / "repositories"
    long_leaf = (
        repositories
        / "python"
        / ("repository-" + "x" * 100)
        / ("revision-" + "a" * 40)
        / ("candidate-" + "b" * 64)
    )
    assert len(str(long_leaf.resolve())) > 260
    layout.filesystem_path(long_leaf).mkdir(parents=True)
    (repositories / "java/repository/revision/candidate").mkdir(parents=True)

    layout.remove_obsolete_empty_directories(output_root)

    assert repositories.is_dir()
    assert list(repositories.iterdir()) == []


def test_cleanup_rejects_an_unowned_directory_disappearance(tmp_path, monkeypatch):
    output_root = tmp_path / "finalized"
    repositories = output_root / "repositories"
    leaf = repositories / "vanished"
    leaf.mkdir(parents=True)

    def disappear(_path):
        raise FileNotFoundError("simulated external removal after the fresh scan")

    monkeypatch.setattr(layout.os, "rmdir", disappear)

    with pytest.raises(FileNotFoundError, match="disappeared during cleanup"):
        layout.remove_obsolete_empty_directories(output_root)

    assert leaf.is_dir()


def test_zero_candidate_promotion_rejects_and_preserves_unrecognized_repository_data(
    tmp_path, monkeypatch
):
    output_root = _zero_cohort(tmp_path, monkeypatch)
    promotion.promote(None, output_root, None)
    unexpected = output_root / "repositories/python/unrecognized.txt"
    unexpected.parent.mkdir(parents=True)
    unexpected.write_text("preserve me\n", encoding="utf-8")
    promotion.refresh_sha256sums(output_root)

    with pytest.raises(ValueError, match="unrecognized or missing artifacts"):
        promotion.promote(None, output_root, None)

    assert unexpected.read_text(encoding="utf-8") == "preserve me\n"


def test_zero_candidate_promotion_rejects_unrecognized_root_data(tmp_path, monkeypatch):
    output_root = _zero_cohort(tmp_path, monkeypatch)
    promotion.promote(None, output_root, None)
    unexpected = output_root / "operator-notes.txt"
    unexpected.write_text("preserve me\n", encoding="utf-8")
    promotion.refresh_sha256sums(output_root)

    with pytest.raises(ValueError, match="unrecognized root entries"):
        promotion.promote(None, output_root, None)

    assert unexpected.read_text(encoding="utf-8") == "preserve me\n"


@pytest.mark.parametrize(
    "entry_name",
    ["README.md", "cohort-manifest.json", "sha256sums.txt", "repositories"],
)
def test_zero_candidate_promotion_rejects_and_preserves_canonical_root_symlinks(
    tmp_path, monkeypatch, entry_name
):
    output_root = _zero_cohort(tmp_path, monkeypatch)
    promotion.promote(None, output_root, None)
    entry = output_root / entry_name
    target = tmp_path / "targets" / entry_name
    target.parent.mkdir(parents=True, exist_ok=True)
    if entry_name == "repositories":
        entry.rmdir()
        target.mkdir()
        entry.symlink_to(target, target_is_directory=True)
    else:
        content = entry.read_bytes()
        entry.unlink()
        target.write_bytes(content)
        entry.symlink_to(target)

    with pytest.raises(ValueError, match="unsupported symlink"):
        promotion.promote(None, output_root, None)

    assert entry.is_symlink()
    assert target.exists()


def test_zero_candidate_promotion_rejects_and_preserves_nested_symlink(tmp_path, monkeypatch):
    output_root = _zero_cohort(tmp_path, monkeypatch)
    promotion.promote(None, output_root, None)
    nested = output_root / "repositories/python/inventory.txt"
    nested.parent.mkdir(parents=True)
    target = tmp_path / "inventory-target.txt"
    target.write_text("preserve me\n", encoding="utf-8")
    nested.symlink_to(target)

    with pytest.raises(ValueError, match="unsupported symlink"):
        promotion.promote(None, output_root, None)

    assert nested.is_symlink()
    assert target.read_text(encoding="utf-8") == "preserve me\n"


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
        "presentation-component-manifest.json",
        "readme-document-plan.json",
        "claim-map.json",
        "deterministic-validation.json",
        "independent-agent-review.json",
        "final-verdict.json",
        "no-op-proof.json",
        "llm-call-ledger.jsonl",
        "runtime-manifest.json",
    } <= promotion.COMMITTED_ARTIFACTS.keys()
