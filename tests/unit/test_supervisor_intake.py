"""The supervisor intake seam is revision-bound, idempotent, and read-only."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1
from readme_agent.supervisor.intake import run_readonly_intake_preflight
from readme_agent.supervisor.intake_cache import completed_intake_binding
from tests.unit.test_readme_poc_intake import IntakeBackend


def _entry() -> ProductEntry:
    return ProductEntry(
        registry_schema_version=2,
        provider_identity={
            "provider": "github",
            "repository_id": 123,
            "node_id": "R_test",
        },
        family="example",
        platform="python",
        repo_name="Example",
        repo_url="https://github.com/example-org/Example",
        clone_url="https://github.com/example-org/Example.git",
        active=True,
        discovered_via="test",
        mode="disabled",
        ecosystem="python",
        policy_profile="example-python",
    )


def test_second_observation_reuses_one_receipt_and_does_not_reclone(
    monkeypatch,
    tmp_path,
):
    import readme_agent.paths as path_module
    import readme_agent.supervisor.intake as intake_module

    readme = "# Example\n\nA valuable short maintainer README.\n"
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    revision = "a" * 40
    snapshot = RepositorySnapshotV1(
        org_repo="example-org/Example",
        source_revision=revision,
        snapshot_root=str(tmp_path.resolve()),
        readme_path="README.md",
        readme_sha256=hashlib.sha256(readme.encode("utf-8")).hexdigest(),
        inventory_sha256="b" * 64,
        captured_at="2026-07-29T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://github.com/example-org/Example.git",
            git_tree_sha256="b" * 64,
        ),
    )
    clone_calls: list[str] = []
    monkeypatch.setattr(path_module, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        intake_module,
        "remote_head_sha",
        lambda clone_url: (_ for _ in ()).throw(
            AssertionError("a portfolio-resolved revision must not be probed twice")
        ),
    )
    monkeypatch.setattr(
        intake_module,
        "verified_baseline_at_revision",
        lambda entry, baseline, **kwargs: clone_calls.append(entry.org_repo),
    )
    monkeypatch.setattr(
        intake_module,
        "capture_repository_snapshot",
        lambda entry, baseline: snapshot,
    )
    backend = IntakeBackend()

    first = run_readonly_intake_preflight(_entry(), backend, source_revision=revision)
    second = run_readonly_intake_preflight(_entry(), backend, source_revision=revision)

    assert first.executed is True
    assert second.executed is False
    assert first.binding == second.binding
    assert first.binding.outcome == "READY_FULL_PIPELINE"
    assert clone_calls == ["example-org/Example"]
    evidence = tmp_path / "runs" / "readme-poc" / "example-org__Example" / revision
    assert (evidence / "intake" / "preflight.json").is_file()
    assert (evidence / "sha256sums.txt").is_file()
    assert (
        completed_intake_binding(
            backend.states["example-org/Example"],
            _entry(),
            current_source_revision=revision,
        )
        == first.binding
    )

    receipt = Path(first.binding.evidence_refs[0])
    receipt.write_text("{}", encoding="utf-8")
    assert (
        completed_intake_binding(
            backend.states["example-org/Example"],
            _entry(),
            current_source_revision=revision,
        )
        is None
    )


def test_unreachable_repository_is_a_visible_access_block_without_clone(
    monkeypatch,
    tmp_path,
):
    import readme_agent.paths as path_module
    import readme_agent.supervisor.intake as intake_module

    monkeypatch.setattr(path_module, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(intake_module, "remote_head_sha", lambda clone_url: None)
    monkeypatch.setattr(
        intake_module,
        "verified_baseline_at_revision",
        lambda entry, baseline, **kwargs: (_ for _ in ()).throw(
            AssertionError("an unresolved revision must not clone")
        ),
    )

    result = run_readonly_intake_preflight(_entry(), IntakeBackend())

    assert result.binding.outcome == "BLOCKED_ACCESS"
    assert result.executed is True
