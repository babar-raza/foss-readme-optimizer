"""profile/cached.py::get_or_build_profile() -- decision #40/Part B's
pre-clone freshness gate. No real clone/network: clone_baseline(),
build_profile(), and remote_head_sha() are all monkeypatched, mirroring
test_capabilities.py's style for the two callers of this shared helper."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from readme_agent.profile import cached
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.schema import ProfileCacheV1, RunStateV1

ORG_REPO = "acme/widget"


class FakeStateBackend:
    """In-memory `StateBackend`, mirrors `test_state_backend.py`'s fake."""

    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, tuple[str, datetime]] = {}

    def load(self, org_repo: str) -> RunStateV1 | None:
        return self._states.get(org_repo)

    def save(self, org_repo: str, state: RunStateV1, expected_version: int | None) -> SaveResult:
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo: str):
        existing = self._locks.get(org_repo)
        if existing is not None and existing[1] > datetime.now(UTC):
            return None
        leased_until = datetime.now(UTC) + timedelta(seconds=900)
        holder_id = f"fake-holder-{len(self._locks)}"
        self._locks[org_repo] = (holder_id, leased_until)
        return Lock(org_repo=org_repo, holder_id=holder_id, leased_until=leased_until.isoformat())

    def release_lock(self, lock) -> None:
        self._locks.pop(lock.org_repo, None)


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
    def test_cache_hit_returns_cached_profile_without_cloning(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        backend = FakeStateBackend()
        cached_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["stray.toml"]
        )
        backend.save(
            ORG_REPO,
            RunStateV1(
                org_repo=ORG_REPO,
                profile_cache=ProfileCacheV1(
                    upstream_revision="deadbeef",
                    profile_result=cached_profile.model_dump(mode="json"),
                ),
            ),
            expected_version=None,
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "deadbeef")
        monkeypatch.setattr(cached, "clone_baseline", _fail_if_called)
        monkeypatch.setattr(cached, "build_profile", _fail_if_called)

        result = cached.get_or_build_profile(entry, backend)

        assert result == cached_profile

    def test_sha_mismatch_clones_fresh_and_updates_cache(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        backend = FakeStateBackend()
        stale_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["old.toml"]
        )
        backend.save(
            ORG_REPO,
            RunStateV1(
                org_repo=ORG_REPO,
                profile_cache=ProfileCacheV1(
                    upstream_revision="old-sha",
                    profile_result=stale_profile.model_dump(mode="json"),
                ),
            ),
            expected_version=None,
        )
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=["new.toml"]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "new-sha")
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry, backend)

        assert result == fresh_profile
        updated = backend.load(ORG_REPO)
        assert updated.profile_cache.upstream_revision == "new-sha"
        assert updated.profile_cache.profile_result == fresh_profile.model_dump(mode="json")

    def test_no_backend_always_clones_fresh(self, monkeypatch, tmp_path):
        entry = _fake_entry()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: "some-sha")
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry, state_backend=None)

        assert result == fresh_profile

    def test_remote_head_sha_failure_falls_back_to_clone_without_caching(
        self, monkeypatch, tmp_path
    ):
        """remote_head_sha() returning None (unreachable remote, timeout,
        etc.) must never be treated as a cache-invalidation error -- just
        clone as if there were no backend at all, and skip the write-back
        since there's no revision to key it by."""
        entry = _fake_entry()
        backend = FakeStateBackend()
        fresh_profile = RepositoryProfile(
            org_repo=ORG_REPO, detected_ecosystems=[], unresolved_manifests=[]
        )
        monkeypatch.setattr(cached, "remote_head_sha", lambda clone_url: None)
        monkeypatch.setattr(cached, "baseline_dir", lambda org, repo: tmp_path)
        monkeypatch.setattr(cached, "clone_baseline", lambda entry, path: None)
        monkeypatch.setattr(cached, "build_profile", lambda org_repo, path: fresh_profile)

        result = cached.get_or_build_profile(entry, backend)

        assert result == fresh_profile
        assert backend.load(ORG_REPO) is None
