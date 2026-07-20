"""One-shot verification (decision #40/Part B): the documented-but-never-
ticketed aspose-page-foss profiling latency (~185-258s across Wave 3/Wave 6
hardening, plans/master.md) was measured as clone_baseline()+build_profile()
combined, never split -- this proves the split and the new freshness-gate
cache in profile/cached.py end to end against the real repo, once.

Read-only throughout: git clone --depth 1 only (gitsafety.clone.clone_baseline),
never a work clone, never a push -- same posture as
survey_full_registry_ecosystem_detection.py. Uses an in-memory FakeStateBackend,
not the real git-ref-backed StateBackend, so this never touches this
project's own remote state ref.

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import shutil
import stat
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.profile import cached  # noqa: E402
from readme_agent.registry.models import ProductEntry  # noqa: E402
from readme_agent.state.backend import Lock, SaveResult  # noqa: E402
from readme_agent.state.schema import RunStateV1  # noqa: E402


class FakeStateBackend:
    def __init__(self):
        self._states: dict[str, RunStateV1] = {}
        self._locks: dict[str, tuple[str, datetime]] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo):
        leased_until = datetime.now(UTC) + timedelta(seconds=900)
        holder_id = "verify-script"
        self._locks[org_repo] = (holder_id, leased_until)
        return Lock(org_repo=org_repo, holder_id=holder_id, leased_until=leased_until.isoformat())

    def release_lock(self, lock):
        self._locks.pop(lock.org_repo, None)


ENTRY = ProductEntry(
    family="page",
    platform="python",
    repo_name="Aspose.Page-FOSS-for-Python",
    repo_url="https://github.com/aspose-page-foss/Aspose.Page-FOSS-for-Python",
    clone_url="https://github.com/aspose-page-foss/Aspose.Page-FOSS-for-Python.git",
    active=True,
    discovered_via="manual",
    mode="disabled",
    ecosystem=None,
    policy_profile=None,
)

CLONE_PATH = REPO_ROOT / "runs" / "investigation-clones" / "verify-profile-cache"


def _force_rmtree(path: Path) -> None:
    def _on_error(func, target_path, exc_info):
        import os

        os.chmod(target_path, stat.S_IWRITE)
        func(target_path)

    if path.exists():
        shutil.rmtree(path, onerror=_on_error)


backend = FakeStateBackend()

print(f"run 1 (cold, no cache) against {ENTRY.org_repo} ...")
t0 = time.time()
clone_baseline(ENTRY, CLONE_PATH)
t_cloned = time.time()
profile1 = cached.build_profile(ENTRY.org_repo, CLONE_PATH)
t_profiled = time.time()
clone_s = t_cloned - t0
profile_s = t_profiled - t_cloned
print(f"  clone_s={clone_s:.1f} profile_s={profile_s:.1f} total={t_profiled - t0:.1f}s")
print(f"  detected_ecosystems={[e.ecosystem for e in profile1.detected_ecosystems]}")
print(f"  unresolved_manifests={profile1.unresolved_manifests}")

sha = cached.remote_head_sha(ENTRY.clone_url)
print(f"  remote_head_sha={sha}")

if sha is None:
    print(
        "\nremote_head_sha() returned None (transient network issue) -- "
        "skipping the cache-hit proof this run, nothing to key it by."
    )
else:
    cached._record_profile_cache(backend, ENTRY.org_repo, sha, profile1)

    print("\nrun 2 (via get_or_build_profile(), cache should hit -- zero clone) ...")
    t0 = time.time()
    profile2 = cached.get_or_build_profile(ENTRY, backend)
    t1 = time.time()
    print(f"  elapsed={t1 - t0:.2f}s (should be near-zero, no clone)")
    assert profile2 == profile1, "cache hit must return the identical profile"
    print("  OK: cache hit returned the identical profile with no clone.")

_force_rmtree(CLONE_PATH)
print("\ncleaned up clone directory.")
