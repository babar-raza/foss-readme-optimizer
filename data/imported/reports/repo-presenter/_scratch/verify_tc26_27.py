# Adapted from aspose.org: reports/repo-presenter/_scratch/verify_tc26_27.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import json
import sys
from pathlib import Path

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_run as rr  # noqa: E402

rr.configure()

PRODUCTS = [("barcode", "python"), ("cells", "cpp"), ("3d", "typescript")]


def run_one(family, platform, readme_path, label):
    text = readme_path.read_text(encoding="utf-8")
    clone_cache = rr._product_clone_cache(family, platform)
    result = rr._run_deterministic_checks(family, platform, text, clone_cache)
    hard_fails = {k: v["findings"] for k, v in result.items() if v.get("hard_gate") and v.get("findings")}
    print(f"=== {label} ({family}/{platform}) ===")
    homepage = rr._detect_homepage_link(family, platform)
    print(f"  homepage: {homepage}")
    lic = rr._detect_license_file(clone_cache)
    print(f"  license_file: {lic}")
    print(f"  license_section_matches_template findings: {result['license_section_matches_template']['findings']}")
    print(f"  banner_links_to_homepage findings: {result['banner_links_to_homepage']['findings']}")
    if hard_fails:
        print(f"  HARD GATE FAILURES ({len(hard_fails)}):")
        for k, v in hard_fails.items():
            print(f"    - {k}: {len(v)} finding(s)")
            for f in v[:2]:
                print(f"        {f}")
    else:
        print("  ALL HARD GATES CLEAN")
    print()


for family, platform in PRODUCTS:
    live_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    if live_path.is_file():
        run_one(family, platform, live_path, "LIVE")

    reproof_path = (
        REPO_ROOT / "reports" / "repo-presenter-regen-reproof" / "repo-presenter"
        / family / platform / "readme.md"
    )
    if reproof_path.is_file():
        run_one(family, platform, reproof_path, "REPROOF")
