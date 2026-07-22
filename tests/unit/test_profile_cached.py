"""profile/cached.py::get_or_build_profile() -- decision #40/Part B's
pre-clone freshness gate, refactored to the stateless convention (decision
#26(b), Part E1), plus the git-tree-API-first path (`SCL-004`, Part F).
No real clone/network: clone_baseline(), build_profile(), remote_head_sha(),
env.gh_token(), and github_api_client.get_tree()/get_file_content() are all
monkeypatched.

Every clone-fallback test below explicitly mocks env.gh_token() to return
None -- without that, a real GH_TOKEN/GITHUB_PAT present in the ambient
shell environment (ordinary for a dev machine) would make these "offline"
unit tests attempt real GitHub API calls. Write-back behavior belongs to
orchestrator.py::profile_repo_with_cache() -- see test_orchestrator.py."""

from types import SimpleNamespace

from readme_agent.profile import cached
from readme_agent.profile.schema import RepositoryProfile

ORG_REPO = "acme/widget"


def _fake_entry() -> SimpleNamespace:
    return SimpleNamespace(
        org="acme",
        repo_name="widget",
        org_repo=ORG_REPO,
        clone_url="https://example.invalid/acme/widget.git",
    )


def _fail_if_called(*args, **kwargs):
    raise AssertionError("clone_baseline/build_profile must not run on a cache hit")


class TestGetOrBuildProfileCacheHit:
    def test_cache_hit_returns_prior_profile_without_cloning(self, monkeypatch):
        entry = _fake_entry()
        prior_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["stray.toml"]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "deadbeef")
        monkeypatch.setattr(cached, "clone_baseline", _fail_if_called)
        monkeypatch.setattr(cached, "build_profile", _fail_if_called)

        result = cached.get_or_build_profile(
            entry,
            prior_upstream_revision="deadbeef",
            prior_profile_result=prior_profile.model_dump(mode="json"),
        )

        assert result == prior_profile

    def test_sha_mismatch_clones_fresh(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        stale_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["old.toml"]
        )
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["new.toml"]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "new-sha")
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(
            entry,
            prior_upstream_revision="old-sha",
            prior_profile_result=stale_profile.model_dump(mode="json"),
        )

        assert result == fresh_profile

    def test_no_prior_value_always_clones_fresh(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "some-sha")
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry)

        assert result == fresh_profile

    def test_prior_revision_without_prior_result_clones_fresh(self, monkeypatch, tmp_path):
        """A prior_upstream_revision with no matching prior_profile_result
        (e.g. a caller bug, or a durable record predating this field) must
        never be treated as a usable cache hit -- there's nothing to return."""
        entry = _fake_entry()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "deadbeef")
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(
            entry, prior_upstream_revision="deadbeef", prior_profile_result=None
        )

        assert result == fresh_profile

    def test_remote_head_sha_failure_falls_back_to_clone(self, monkeypatch, tmp_path):
        """remote_head_sha() returning None (unreachable remote, timeout,
        etc.) must never be treated as a cache-invalidation error -- just
        clone as if no prior value had been supplied at all."""
        entry = _fake_entry()
        prior_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["old.toml"]
        )
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: None)
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(
            entry,
            prior_upstream_revision="old-sha",
            prior_profile_result=prior_profile.model_dump(mode="json"),
        )

        assert result == fresh_profile


class TestGetOrBuildProfileApiPath:
    """SCL-004 (decision #40/Part F): the git-tree-API-first path, tried
    before falling back to a real clone, only when a token is available."""

    def test_no_token_skips_api_path_entirely(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "new-sha")
        monkeypatch.setattr(cached.env, "gh_token", lambda: None)
        monkeypatch.setattr(cached.github_api_client, "get_tree", _fail_if_called)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry)

        assert result == fresh_profile

    def test_api_path_used_when_token_available_no_clone(self, monkeypatch):
        entry = _fake_entry()
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "new-sha")
        monkeypatch.setattr(cached.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(cached, "clone_baseline", _fail_if_called)
        monkeypatch.setattr(cached, "build_profile", _fail_if_called)
        monkeypatch.setattr(
            cached.github_api_client,
            "get_tree",
            lambda org_repo, sha, token: {
                "truncated": False,
                "tree": [{"path": "pyproject.toml", "type": "blob"}],
            },
        )
        monkeypatch.setattr(
            cached.github_api_client,
            "get_file_content",
            lambda org_repo, path, token: b"[project]\nname = 'widget'\n",
        )

        result = cached.get_or_build_profile(entry)

        assert result.org_repo == ORG_REPO
        assert [d.ecosystem for d in result.detected_ecosystems] == ["python"]
        assert result.detected_ecosystems[0].manifest_path == "pyproject.toml"

    def test_truncated_tree_falls_back_to_clone(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "new-sha")
        monkeypatch.setattr(cached.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            cached.github_api_client,
            "get_tree",
            lambda org_repo, sha, token: {"truncated": True, "tree": []},
        )
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry)

        assert result == fresh_profile

    def test_api_failure_falls_back_to_clone(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )

        def _raise_http_error(org_repo, sha, token):
            import requests

            raise requests.HTTPError("simulated 500")

        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "new-sha")
        monkeypatch.setattr(cached.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(cached.github_api_client, "get_tree", _raise_http_error)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry)

        assert result == fresh_profile
