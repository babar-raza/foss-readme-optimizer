# Adapted from aspose.org: reports/repo-presenter/_scratch/fix_enterprise_links.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import re
import sys
from pathlib import Path

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_run as rr  # noqa: E402
import readme_refresh_checks as checks  # noqa: E402

rr.configure()

TARGETS = [
    "3d/python", "cells/go", "cells/python", "email/python", "html/python", "note/python",
    "page/python", "pdf/cpp", "pdf/go", "pdf/python", "tex/python", "words/net",
]

for fp in TARGETS:
    family, platform = fp.split("/")
    readme_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    text = readme_path.read_text(encoding="utf-8")
    el = rr._detect_enterprise_link(family, platform)
    verified_url = el["url"]
    assert verified_url, f"{fp}: no verified enterprise link -- cannot auto-fix"

    findings_before = checks.check_enterprise_edition_link_resolves(text, el)
    n_fixed = 0

    def _replace(match):
        global n_fixed
        anchor_text, href = match.group(1), match.group(2)
        if checks._ENTERPRISE_LINK_HOST_RE.search(href) and href.rstrip("/").lower() != verified_url.rstrip("/").lower():
            n_fixed += 1
            return f"[{anchor_text}]({verified_url})"
        return match.group(0)

    new_text = checks._MD_LINK_RE.sub(_replace, text)
    readme_path.write_text(new_text, encoding="utf-8")

    findings_after = checks.check_enterprise_edition_link_resolves(new_text, el)
    print(f"{fp}: fixed {n_fixed} link(s) -> {verified_url}  "
          f"(before: {len(findings_before)} findings, after: {len(findings_after)} findings)")
    if findings_after:
        print(f"   STILL FAILING: {findings_after}")
