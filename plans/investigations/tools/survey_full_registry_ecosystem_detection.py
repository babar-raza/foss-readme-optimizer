# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Full-registry (all 26 real repos, regardless of mode) ecosystem-detection
survey -- Wave 3 hardening. Clones each real repo's baseline and runs
profile.detector.build_profile() against it, exercising all six
ecosystems/*.py parsers against real, previously-unseen data (5 of 6
platforms had only synthetic-fixture coverage after Wave 3 shipped).

Read-only throughout: git clone --depth 1 only (gitsafety.clone.clone_baseline,
the same primitive orchestrator.inspect_repo() uses), never a work clone,
never a push. Decision 24/PIL-011: research/development tasks cover every
data/products.json entry with equal precedence regardless of mode -- this is
exactly that, via the read-only clone primitive directly, not the capability
layer's allow-list-gated execute() path (which correctly stays mode-gated for
real capability execution -- see plans/master.md Wave 3 Changelog entry on
why the live capability test targets an enabled pilot, not a disabled one).

This is a distinct survey from survey_full_registry.py (API-only, no clone,
gap_detector against fetched READMEs) -- that script cannot see manifest
files at all, so it cannot exercise the ecosystems/*.py parsers this wave
added. Not a duplicate: different data source, different subject.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.profile.detector import build_profile  # noqa: E402
from readme_agent.registry.loader import load_products  # noqa: E402

OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "full-registry-ecosystem-survey"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CLONE_DIR = REPO_ROOT / "runs" / "investigation-clones"

# What we expect to detect per declared platform -- not enforced, just
# reported, since a real repo can legitimately have zero, one, or multiple
# manifests (a platform label is not a manifest-presence guarantee).
EXPECTED_ECOSYSTEM_BY_PLATFORM = {
    "java": "java",
    "net": "net",
    "python": "python",
    "typescript": "typescript",
    "go": "go",
    "cpp": "cpp",
}


def _force_rmtree(path: Path) -> None:
    def _on_error(func, target_path, exc_info):
        os.chmod(target_path, stat.S_IWRITE)
        func(target_path)

    if path.exists():
        shutil.rmtree(path, onerror=_on_error)


results: list[dict] = []
entries = load_products()
print(f"surveying {len(entries)} registry entries (all modes)...\n")

for i, entry in enumerate(entries, start=1):
    org_repo = entry.org_repo
    clone_path = CLONE_DIR / f"{entry.org}__{entry.repo_name}"
    record: dict = {"org_repo": org_repo, "platform": entry.platform, "mode": entry.mode}
    t0 = time.time()
    try:
        clone_baseline(entry, clone_path)
        t_cloned = time.time()
        profile = build_profile(org_repo, clone_path)
        dt = time.time() - t0
        clone_s = round(t_cloned - t0, 1)
        profile_s = round(dt - (t_cloned - t0), 1)
        detected = [d.model_dump() for d in profile.detected_ecosystems]
        expected = EXPECTED_ECOSYSTEM_BY_PLATFORM.get(entry.platform)
        found_expected = any(d["ecosystem"] == expected for d in detected) if expected else None
        record.update(
            {
                "ok": True,
                "latency_s": round(dt, 1),
                "clone_s": clone_s,
                "profile_s": profile_s,
                "detected_ecosystems": detected,
                "unresolved_manifests": profile.unresolved_manifests,
                "expected_platform_detected": found_expected,
            }
        )
        print(
            f"[{i}/{len(entries)}] ok {org_repo} ({entry.platform}): "
            f"detected={[d['ecosystem'] for d in detected]} "
            f"expected_found={found_expected} "
            f"unresolved={profile.unresolved_manifests} "
            f"{dt:.1f}s (clone={clone_s:.1f}s, profile={profile_s:.1f}s)"
        )
    except Exception as e:  # noqa: BLE001 -- survey every repo, one failure must not abort the rest
        dt = time.time() - t0
        record.update(
            {
                "ok": False,
                "latency_s": round(dt, 1),
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }
        )
        print(f"[{i}/{len(entries)}] FAIL {org_repo} ({entry.platform}): {type(e).__name__}: {e}")
    results.append(record)

(OUT_DIR / "survey-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nwrote: {(OUT_DIR / 'survey-results.json').relative_to(REPO_ROOT)}")

ok_count = sum(1 for r in results if r["ok"])
print(f"\n{ok_count}/{len(results)} repos profiled without a crash")
mismatches = [
    r["org_repo"] for r in results if r["ok"] and r["expected_platform_detected"] is False
]
if mismatches:
    print(f"expected-platform NOT detected for {len(mismatches)} repos: {mismatches}")
unresolved_any = [r["org_repo"] for r in results if r.get("ok") and r.get("unresolved_manifests")]
if unresolved_any:
    print(f"unresolved manifests recorded for {len(unresolved_any)} repos: {unresolved_any}")
