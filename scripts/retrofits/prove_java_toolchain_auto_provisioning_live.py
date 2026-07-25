"""RPOC-041 live proof: real, unmocked evidence that Java product-fact
verification now auto-detects the JDK major version a repo's own pom.xml
REQUIRES and auto-provisions a matching Eclipse Temurin build, instead of
trying whatever `README_AGENT_JAVA_HOME`/ambient PATH happened to provide
and only discovering a version mismatch from Maven's error text after the
fact (`facts/local_verification.py::_java_toolchain_blocked`).

Runs the SAME real, imported (never reimplemented) production entry point
`facts/provider.py::collect_product_facts` the `get_product_facts`
capability itself calls, under a real `repository_snapshot_scope(...,
allow_local_fact_verification=True)` -- the exact condition the
`local_dry_run` execution profile sets (`supervisor/execution_profile.py`).
Nothing here is a bespoke bypass of `_verify_java`.

Two modes, selected by `sys.argv[1]`:
  * "cache" (default) -- run as-is against whatever `runs/toolchains/`
    already has. If a matching JDK is already cached from a prior session,
    this is a genuine cache-hit proof (no download).
  * "download" -- temporarily hides any already-cached Temurin JDK 21
    install (renames it out of `_cached_jdk_home()`'s `temurin-*` glob,
    never deletes anything) so `provision_jdk()` is forced through a real
    Adoptium network round-trip: metadata fetch, checksummed download,
    extraction -- then restores nothing (the freshly downloaded copy
    becomes the new cache; the hidden prior copy is left alongside it,
    untouched, for the operator to reconcile/delete by hand).

Kept after use as the executable record of this verification -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 5.
"""

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import env, paths  # noqa: E402
from readme_agent.facts import java_toolchain  # noqa: E402
from readme_agent.facts.provider import collect_product_facts  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.registry.loader import require_listed  # noqa: E402
from readme_agent.repository_snapshot import (  # noqa: E402
    capture_repository_snapshot,
    repository_snapshot_scope,
)

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
REQUIRED_MAJOR = 21  # confirmed from the repo's own real pom.xml (source/target=21)


def _hide_cached_jdk(major: int) -> Path | None:
    """Rename any already-cached matching JDK out of the `temurin-*` glob
    `_cached_jdk_home()` scans, forcing `provision_jdk()` down the real
    network path. Never deletes -- just prefixes the directory name so it
    stops matching."""
    cache_root = paths.toolchains_dir()
    existing = java_toolchain._cached_jdk_home(major)  # noqa: SLF001 -- live-proof introspection
    if existing is None:
        return None
    # existing is .../temurin-<version>/jdk-<version> -- hide the release
    # directory one level up so the whole release stops matching.
    release_dir = existing.parent
    hidden = cache_root / f"hidden-for-live-proof-{release_dir.name}-{int(time.time())}"
    release_dir.rename(hidden)
    return hidden


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "cache"
    print(f"Mode: {mode}")
    print(f"Repo: {ORG_REPO}")
    print(f"README_AGENT_JAVA_HOME set: {env.java_home() is not None} ({env.java_home()!r})")

    hidden_path = None
    if mode == "download":
        hidden_path = _hide_cached_jdk(REQUIRED_MAJOR)
        print(f"Hid pre-existing cached JDK {REQUIRED_MAJOR} at: {hidden_path}")
        still_cached = java_toolchain._cached_jdk_home(REQUIRED_MAJOR)  # noqa: SLF001
        print(f"Cache scan after hiding (must be None to force a real download): {still_cached}")

    entry = require_listed(ORG_REPO)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    snapshot = capture_repository_snapshot(entry, baseline_path)

    detected_major = java_toolchain.required_java_major_version(baseline_path / "pom.xml")
    print(f"\nrequired_java_major_version(baseline pom.xml) = {detected_major}")

    started = time.monotonic()
    with repository_snapshot_scope(snapshot, allow_local_fact_verification=True):
        result = collect_product_facts(ORG_REPO)
    elapsed = time.monotonic() - started

    local_verification = result.get("local_product_verification")
    print(f"\nWall time for collect_product_facts(): {elapsed:.1f}s")
    print("\n=== local_product_verification ===")
    print(json.dumps(local_verification, indent=2)[:4000])

    outcome = (local_verification or {}).get("outcome")
    detail = (local_verification or {}).get("detail")
    print("\n=== Verdict ===")
    print(f"detected required major version: {detected_major} (expected {REQUIRED_MAJOR})")
    print(f"outcome: {outcome}")
    print(f"detail: {detail}")
    resolved_home = java_toolchain.find_existing_jdk_home(REQUIRED_MAJOR)
    print(f"JDK home now satisfying major {REQUIRED_MAJOR}: {resolved_home}")
    if resolved_home is not None:
        print(f"  release file: {(resolved_home / 'release').read_text(encoding='utf-8').strip()}")

    success = detected_major == REQUIRED_MAJOR and outcome == "SOURCE_BUILD_VERIFIED"
    print(f"\nPASS: {success}")
    if hidden_path is not None:
        print(
            f"\nNote: pre-existing cache was hidden at {hidden_path} (not deleted) -- "
            "reconcile/remove by hand once this proof is reviewed."
        )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
