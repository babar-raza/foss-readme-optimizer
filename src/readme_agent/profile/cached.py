"""Shared read path for profile_repository/get_product_facts (decision
#40/Part B): both capabilities need an identical RepositoryProfile from a
fresh clone_baseline() + build_profile() every call today, even when
nothing changed upstream (measured ~258s on a real ~1GB registry repo).
get_or_build_profile() adds a pre-clone remote_head_sha() freshness check
in front of that -- a cache hit skips the clone entirely.
"""

import sys

from readme_agent.errors import StateBackendError
from readme_agent.gitsafety.clone import clone_baseline, remote_head_sha
from readme_agent.paths import baseline_dir
from readme_agent.profile.detector import build_profile
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.registry.models import ProductEntry
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import ProfileCacheV1, RunStateV1


def _load_cached_profile(
    backend: StateBackend | None, org_repo: str, current_revision: str | None
) -> RepositoryProfile | None:
    if backend is None or current_revision is None:
        return None
    try:
        state = backend.load(org_repo)
    except StateBackendError:
        return None
    cache = state.profile_cache if state else None
    if cache is None or cache.upstream_revision != current_revision:
        return None
    return RepositoryProfile.model_validate(cache.profile_result)


def _record_profile_cache(
    backend: StateBackend, org_repo: str, upstream_revision: str, profile: RepositoryProfile
) -> None:
    """Best-effort CAS write-back, mirrors
    `supervisor/loop.py::_record_supervisor_state` -- never able to fail the
    caller by itself; a "stale" CAS outcome just means some other write beat
    this one, resolved fresh again on the next call either way."""
    try:
        current = backend.load(org_repo)
        expected_version = current.state_version if current else None
        cache = ProfileCacheV1(
            upstream_revision=upstream_revision,
            profile_result=profile.model_dump(mode="json"),
        )
        new_state = (current or RunStateV1(org_repo=org_repo)).model_copy(
            update={"profile_cache": cache}
        )
        backend.save(org_repo, new_state, expected_version)
    except StateBackendError as exc:
        print(
            f"warning: durable state write-back failed, continuing without it: {exc}",
            file=sys.stderr,
        )


def get_or_build_profile(
    entry: ProductEntry, state_backend: StateBackend | None = None
) -> RepositoryProfile:
    """Called by both profile_repository.execute() and
    get_product_facts.execute() in place of their previously-duplicated
    inline clone_baseline() + build_profile() pair. remote_head_sha() is a
    tiny git ls-remote, not a clone -- a match against the cached revision
    returns the cached profile with zero clone; anything else (mismatch, no
    backend, probe failure) falls back to a real clone + profile, then
    best-effort records the new cache entry."""
    current_revision = remote_head_sha(entry.clone_url)
    cached = _load_cached_profile(state_backend, entry.org_repo, current_revision)
    if cached is not None:
        return cached

    path = baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, path)
    profile = build_profile(entry.org_repo, path)

    if state_backend is not None and current_revision is not None:
        _record_profile_cache(state_backend, entry.org_repo, current_revision, profile)

    return profile
