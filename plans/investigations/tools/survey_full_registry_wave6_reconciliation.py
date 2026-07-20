# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Full-registry (all 25 real repos, regardless of mode) survey of Wave 6's
new read-only building blocks -- decision #38's compute_tracked_content_hash
(the fix for the durable-skip drift-blindness gap) and decision #39's
readme.reconciliation.classify() (the drift classifier), plus a re-check of
Wave 3's profile.detector.build_profile() as a shared input. Only the 3
enabled pilots have a policy_profile, so the get_product_facts capability's
policy-dependent half cannot be exercised for the other 22 -- this survey
covers exactly what's real and shared across the whole registry, not a
substitute for that.

Read-only throughout: git clone --depth 1 only (gitsafety.clone.clone_baseline,
the same primitive orchestrator.inspect_repo() uses), never a work clone,
never a push -- identical safety posture to
survey_full_registry_ecosystem_detection.py (Wave 3), which this script
mirrors structurally rather than reinventing (decision #30/GOV-015). Decision
24/PIL-011: research/development tasks cover every data/products.json entry
with equal precedence regardless of mode -- via the read-only clone primitive
directly, not the capability layer's allow-list-gated execute() path (which
correctly stays mode-gated for real capability execution).
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
from readme_agent.inspection import file_inventory  # noqa: E402
from readme_agent.profile.detector import build_profile  # noqa: E402
from readme_agent.readme.facts import compute_tracked_content_hash  # noqa: E402
from readme_agent.readme.reconciliation import classify  # noqa: E402
from readme_agent.registry.loader import load_products  # noqa: E402

OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "full-registry-wave6-survey"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CLONE_DIR = REPO_ROOT / "runs" / "investigation-clones"


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

        inventory = file_inventory.scan(clone_path)
        readme_text = (
            inventory.readme_path.read_text(encoding="utf-8", errors="replace")
            if inventory.readme_path
            else ""
        )

        fingerprint = compute_tracked_content_hash(clone_path)
        drift = classify(
            current_readme_text=readme_text,
            prior_stripped_text_hash=None,
            prior_owned_span_present=False,
        )
        t_before_profile = time.time()
        profile = build_profile(org_repo, clone_path)
        t_profiled = time.time()

        dt = t_profiled - t0
        # Split so a slow repo's cost can be attributed to network transfer
        # (clone_s) vs. the manifest walk (profile_s) vs. this script's own
        # extra reconciliation/fingerprint steps (other_s) -- see decision
        # #40/Part B: the combined latency_s alone can't tell which side to
        # optimize.
        clone_s = round(t_cloned - t0, 1)
        other_s = round(t_before_profile - t_cloned, 1)
        profile_s = round(t_profiled - t_before_profile, 1)
        record.update(
            {
                "ok": True,
                "latency_s": round(dt, 1),
                "clone_s": clone_s,
                "other_s": other_s,
                "profile_s": profile_s,
                "has_readme": inventory.readme_path is not None,
                "readme_length_chars": len(readme_text),
                "has_license_file": inventory.license_path is not None,
                "community_files": sorted(inventory.community_paths),
                "tracked_content_fingerprint": fingerprint,
                "drift_classification": drift.classification,
                "owned_span_present_now": drift.owned_span_present_now,
                "detected_ecosystems": [d.ecosystem for d in profile.detected_ecosystems],
                "unresolved_manifests": profile.unresolved_manifests,
            }
        )
        print(
            f"[{i}/{len(entries)}] ok {org_repo} ({entry.platform}, mode={entry.mode}): "
            f"readme={record['has_readme']} license={record['has_license_file']} "
            f"community={record['community_files']} drift={drift.classification} "
            f"span_present={drift.owned_span_present_now} "
            f"{dt:.1f}s (clone={clone_s:.1f}s, other={other_s:.1f}s, profile={profile_s:.1f}s)"
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
print(f"\n{ok_count}/{len(results)} repos surveyed without a crash")
no_readme = [r["org_repo"] for r in results if r.get("ok") and not r.get("has_readme")]
if no_readme:
    print(f"no README detected for {len(no_readme)} repos: {no_readme}")
non_first_observation = [
    r["org_repo"]
    for r in results
    if r.get("ok") and r.get("drift_classification") != "FIRST_OBSERVATION"
]
if non_first_observation:
    print(
        f"UNEXPECTED: non-FIRST_OBSERVATION classification with no prior state for "
        f"{len(non_first_observation)} repos: {non_first_observation}"
    )
