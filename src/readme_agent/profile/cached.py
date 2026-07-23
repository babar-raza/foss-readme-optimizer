"""Shared read path for profile_repository/get_product_facts (decision
#40/Part B; refactored to the stateless convention below in the follow-up
plan's Part E). Both capabilities need an identical RepositoryProfile from a
fresh clone_baseline() + build_profile() every call, even when nothing
changed upstream (measured ~258s on a real registry repo). get_or_build_
profile() adds a pre-clone remote_head_sha() freshness check in front of
that -- a cache hit skips the clone entirely.

Stateless by design (decision #26(b), matching render_readme_candidate.py's
own established convention exactly): this function takes and returns plain
values only, never a live StateBackend. Loading prior state before the call
and persisting the result after it is deterministic wiring code's job
(orchestrator.py::profile_repo_with_cache()), not this helper's -- it was
originally built accepting a state_backend directly (decision #40/Part B),
before that convention was this explicit; corrected here rather than left
as a one-off inconsistency.
"""

import tempfile
from pathlib import Path

import requests

from readme_agent import env
from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.github_api import client as github_api_client
from readme_agent.gitsafety.clone import clone_baseline, remote_head_sha
from readme_agent.inspection.tree_paths import (
    find_all_manifest_roots_from_tree,
    find_manifest_paths_from_tree,
)
from readme_agent.paths import baseline_dir
from readme_agent.profile.detector import build_profile, resolve_unresolved_manifests
from readme_agent.profile.schema import DetectedEcosystem, PackageRoot, RepositoryProfile
from readme_agent.registry.models import ProductEntry
from readme_agent.state.lifecycle import current_lifecycle_recorder


def _checkpoint_profile(profile: RepositoryProfile, source: str) -> RepositoryProfile:
    recorder = current_lifecycle_recorder()
    if recorder is not None:
        recorder.checkpoint(
            "profile_completed",
            action=source,
            outputs=profile.model_dump(mode="json"),
        )
    return profile


def _build_profile_via_api(
    entry: ProductEntry, current_revision: str, token: str
) -> RepositoryProfile | None:
    """`SCL-004` (decision #40/Part F): git-tree-API-based profiling, no
    clone. Returns `None` (never raises) on anything that means "can't use
    this path" -- a truncated tree listing, or any HTTP/network failure --
    so `get_or_build_profile()` falls back to the proven
    `clone_baseline()`+`build_profile()` path unconditionally. Pure
    optimization layered in front of an already-working path: must never
    make a cold call worse than before this existed, only sometimes faster."""
    try:
        tree_response = github_api_client.get_tree(entry.org_repo, current_revision, token)
    except requests.RequestException:
        return None
    if tree_response.get("truncated"):
        return None

    tree_entries = tree_response.get("tree", [])
    manifest_paths = find_manifest_paths_from_tree(tree_entries)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            for path in manifest_paths.values():
                content = github_api_client.get_file_content(entry.org_repo, path, token)
                dest = temp_root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)

            detected: list[DetectedEcosystem] = []
            for ecosystem, path in manifest_paths.items():
                facts = parse_manifest(ecosystem, temp_root)
                filename = path.rsplit("/", 1)[-1]
                detected.append(
                    DetectedEcosystem(
                        ecosystem=ecosystem,
                        manifest_path=path,
                        confidence=1.0 if facts else 0.5,
                        evidence=(
                            f"found {filename}; parsed {len(facts)} field(s)"
                            if facts
                            else f"found {filename}; nothing parsed"
                        ),
                    )
                )
    except requests.RequestException:
        return None

    matched_filenames = {path.rsplit("/", 1)[-1] for path in manifest_paths.values()}
    root_candidates = [
        tree_entry["path"]
        for tree_entry in tree_entries
        if tree_entry.get("type") == "blob" and "/" not in tree_entry["path"]
    ]
    unresolved = resolve_unresolved_manifests(root_candidates, matched_filenames)

    package_roots = [
        PackageRoot(
            path=path.rsplit("/", 1)[0] if "/" in path else ".",
            ecosystem=ecosystem,
            manifest_path=path,
            confidence=1.0,
            evidence=f"found {path.rsplit('/', 1)[-1]} (via tree API)",
        )
        for ecosystem, path in find_all_manifest_roots_from_tree(tree_entries)
    ]

    return RepositoryProfile(
        org_repo=entry.org_repo,
        detected_ecosystems=detected,
        unresolved_manifests=unresolved,
        package_roots=package_roots,
    )


def get_or_build_profile(
    entry: ProductEntry,
    *,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
) -> RepositoryProfile:
    """Called by both profile_repository.execute() and
    get_product_facts.execute() in place of their previously-duplicated
    inline clone_baseline() + build_profile() pair. remote_head_sha() is a
    tiny git ls-remote, not a clone -- a match between it and
    prior_upstream_revision returns prior_profile_result (deserialized) with
    zero clone; anything else (mismatch, no prior value supplied, probe
    failure) tries the git-tree-API path next (when a GitHub token is
    available -- `SCL-004`, decision #40/Part F), then falls back to a real
    clone + profile. Never persists anything itself -- the caller owns
    reading prior_* from durable state and writing the fresh result back
    (mirrors orchestrator.py's own record_accepted_readme_state()
    write-back pattern, one level up)."""
    current_revision = remote_head_sha(entry.clone_url)
    if (
        current_revision is not None
        and prior_upstream_revision is not None
        and current_revision == prior_upstream_revision
        and prior_profile_result is not None
    ):
        return _checkpoint_profile(
            RepositoryProfile.model_validate(prior_profile_result),
            "durable_profile_cache",
        )

    token = env.gh_token()
    if current_revision is not None and token:
        api_profile = _build_profile_via_api(entry, current_revision, token)
        if api_profile is not None:
            return _checkpoint_profile(api_profile, "github_tree_api")

    path = baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, path)
    return _checkpoint_profile(build_profile(entry.org_repo, path), "baseline_clone")
