# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Repeatable clone/profile-latency diagnostic (decision #40/Part G) --
relocated from `scripts/retrofits/verify_profile_cache_against_aspose_page_
foss.py`, which was placed under the one-shot-transformation rule
(`GOVERNANCE.md` placement rule 5) but is actually a repeatable survey/
analysis tool (`investigations/tools/`, rule 6): it measures, it never
transforms the repo.

Generalized from a single hardcoded `aspose-page-foss` target to any
`--org-repo`, and from stdout-only output to an optional `--output` JSON
file, so `.github/workflows/measure-clone-latency.yml` can run this against
a real GitHub Actions runner and upload the result as an artifact --
answering the question this project's own local-machine numbers can't:
what does cold-clone latency actually look like in production CI
conditions, not on a developer's laptop.

Read-only throughout: git clone --depth 1 only (gitsafety.clone.
clone_baseline), never a work clone, never a push -- same posture as
survey_full_registry_ecosystem_detection.py. Uses an in-memory value pair
(prior_upstream_revision/prior_profile_result), not a real durable
StateBackend, so this never touches this project's own remote state ref.

Kept after use as the executable record of this measurement tool -- see
plans/GOVERNANCE.md, "Repository layout", placement rule 6.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.profile import cached  # noqa: E402
from readme_agent.registry.models import ProductEntry  # noqa: E402

DEFAULT_ORG_REPO = "aspose-page-foss/Aspose.Page-FOSS-for-Python"


def _force_rmtree(path: Path) -> None:
    def _on_error(func, target_path, exc_info):
        os.chmod(target_path, stat.S_IWRITE)
        func(target_path)

    if path.exists():
        shutil.rmtree(path, onerror=_on_error)


def _entry_for(org_repo: str) -> ProductEntry:
    org, repo_name = org_repo.split("/", 1)
    return ProductEntry(
        family="diagnostic",
        platform="unknown",
        repo_name=repo_name,
        repo_url=f"https://github.com/{org_repo}",
        clone_url=f"https://github.com/{org_repo}.git",
        active=True,
        discovered_via="manual",
        mode="disabled",
        ecosystem=None,
        policy_profile=None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-repo", default=DEFAULT_ORG_REPO)
    parser.add_argument(
        "--output", type=Path, default=None, help="write the result as JSON to this path"
    )
    args = parser.parse_args()

    entry = _entry_for(args.org_repo)
    clone_path = REPO_ROOT / "runs" / "investigation-clones" / "measure-profile-latency"

    result: dict = {
        "org_repo": args.org_repo,
        "timestamp": datetime.now(UTC).isoformat(),
        "github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
    }

    print(f"run 1 (cold, no cache) against {args.org_repo} ...")
    t0 = time.time()
    clone_baseline(entry, clone_path)
    t_cloned = time.time()
    profile1 = cached.build_profile(entry.org_repo, clone_path)
    t_profiled = time.time()
    result["clone_s"] = round(t_cloned - t0, 1)
    result["profile_s"] = round(t_profiled - t_cloned, 1)
    print(f"  clone_s={result['clone_s']} profile_s={result['profile_s']}")
    print(f"  detected_ecosystems={[e.ecosystem for e in profile1.detected_ecosystems]}")

    sha = cached.remote_head_sha(entry.clone_url)
    result["remote_head_sha"] = sha
    print(f"  remote_head_sha={sha}")

    if sha is None:
        print("\nremote_head_sha() returned None -- skipping the cache-hit proof this run.")
        result["cache_hit_elapsed_s"] = None
    else:
        print("\nrun 2 (via get_or_build_profile(), cache should hit -- zero clone) ...")
        t0 = time.time()
        profile2 = cached.get_or_build_profile(
            entry,
            prior_upstream_revision=sha,
            prior_profile_result=profile1.model_dump(mode="json"),
        )
        t1 = time.time()
        result["cache_hit_elapsed_s"] = round(t1 - t0, 2)
        print(f"  elapsed={result['cache_hit_elapsed_s']}s (should be near-zero, no clone)")
        assert profile2 == profile1, "cache hit must return the identical profile"
        print("  OK: cache hit returned the identical profile with no clone.")

    _force_rmtree(clone_path)
    print("\ncleaned up clone directory.")

    print(f"\nresult: {json.dumps(result, indent=2)}")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
