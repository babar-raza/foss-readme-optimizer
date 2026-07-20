"""Tests for the readme_reconciliation specialist (Wave 6, decision #39) and
the specialist registry -- real local git repos, real capability dispatch
through classify_upstream_change (proving decision #34's domain enforcement
end to end, not mocked), a fake in-memory StateBackend. No network."""

import json

from readme_agent.gitsafety._git import run_git
from readme_agent.specialists import readme_reconciliation, registry
from readme_agent.state.backend import SaveResult
from readme_agent.state.schema import RunStateV1

ORG_REPO = "example-foss/Example-Widget"


def _init_source_repo(path, readme_text: str):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text(readme_text, encoding="utf-8")
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


def _setup_project_root(tmp_path, source_clone_url: str):
    (tmp_path / "data").mkdir()
    products = [
        {
            "family": "widget",
            "platform": "java",
            "repo_name": "Example-Widget",
            "repo_url": "https://github.com/example-foss/Example-Widget",
            "clone_url": source_clone_url,
            "active": True,
            "discovered_via": "manual",
            "mode": "full",
            "ecosystem": "java",
            "policy_profile": "test-profile",
        }
    ]
    (tmp_path / "data" / "products.json").write_text(json.dumps(products), encoding="utf-8")


class _FakeStateBackend:
    """Mirrors test_orchestrator.py's own fake backend -- lock is a no-op
    (always granted), full CAS/lock contract is proven elsewhere
    (test_state_backend.py)."""

    def __init__(self):
        self._states: dict[str, RunStateV1] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": new_version})
        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo):
        return object()

    def release_lock(self, lock):
        pass


class TestSpecialistsRegistry:
    def test_all_domains_includes_readme_reconciliation(self):
        assert registry.all_domains() == ["readme_reconciliation"]

    def test_run_domain_unknown_domain_returns_none(self):
        assert registry.run_domain("nonexistent_domain", "acme/widget", None) is None

    def test_run_domain_dispatches_to_the_real_specialist(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)

        result = registry.run_domain("readme_reconciliation", ORG_REPO, None)

        assert result is not None
        assert result.accepted_status == "FIRST_OBSERVATION"


class TestReadmeReconciliationSpecialist:
    def test_first_run_is_first_observation_and_records_state(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        result = readme_reconciliation.run(ORG_REPO, backend)

        assert result.accepted_status == "FIRST_OBSERVATION"
        assert result.domain == "readme_reconciliation"
        stored = backend.load(ORG_REPO)
        assert stored is not None
        assert stored.domain_states["readme_reconciliation"].accepted_status == "FIRST_OBSERVATION"

    def test_second_run_with_unchanged_content_is_no_change(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        first = readme_reconciliation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        second = readme_reconciliation.run(ORG_REPO, backend)
        assert second.accepted_status == "NO_CHANGE"

    def test_upstream_edit_between_runs_is_upstream_changed(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)
        backend = _FakeStateBackend()

        first = readme_reconciliation.run(ORG_REPO, backend)
        assert first.accepted_status == "FIRST_OBSERVATION"

        (source / "README.md").write_text(
            "# Widget\n\nA widget library.\n\nNew section a maintainer added.\n", encoding="utf-8"
        )
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "docs: update"], cwd=source)

        second = readme_reconciliation.run(ORG_REPO, backend)
        assert second.accepted_status == "UPSTREAM_CHANGED"

    def test_run_without_a_backend_still_works(self, tmp_path, monkeypatch):
        source = _init_source_repo(tmp_path / "source", "# Widget\n\nA widget library.\n")
        _setup_project_root(tmp_path, str(source))
        monkeypatch.chdir(tmp_path)

        result = readme_reconciliation.run(ORG_REPO, None)

        assert result.accepted_status == "FIRST_OBSERVATION"
