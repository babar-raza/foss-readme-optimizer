# Adapted from aspose.org: reports/repo-presenter/_scratch/fix_banner_links.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
sys.path.insert(0, str(REPO_ROOT / "scripts" / "pipeline" / "commands" / "foss"))
import readme_refresh_run as rr  # noqa: E402
import readme_refresh_checks as checks  # noqa: E402

rr.configure()

BARE_RE = checks._BANNER_LINE_RE

products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
excl = json.loads((REPO_ROOT / "data" / "registry_exclusions.json").read_text(encoding="utf-8"))
excl_keys = {(e.get("family"), e.get("platform")) for e in excl} if isinstance(excl, list) else set()
active = sorted(
    (p["family"], p["platform"]) for p in products
    if p.get("active") and (p["family"], p["platform"]) not in excl_keys
)

fixed, already_ok, skipped = [], [], []

for family, platform in active:
    readme_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    if not readme_path.is_file():
        skipped.append((family, platform, "no readme.md"))
        continue
    homepage = rr._detect_homepage_link(family, platform)
    if not homepage["verified"]:
        skipped.append((family, platform, "homepage not verified"))
        continue

    text = readme_path.read_text(encoding="utf-8")
    idx, line = checks._find_banner_line(text)
    if idx is None:
        skipped.append((family, platform, "no banner line found"))
        continue

    if checks._LINKED_BANNER_LINE_RE.match(line):
        already_ok.append((family, platform))
        continue

    match = BARE_RE.match(line)
    if not match:
        skipped.append((family, platform, f"banner line malformed: {line!r}"))
        continue

    linked_line = f"[{line}]({homepage['url']})"
    lines = text.splitlines()
    assert lines[idx].strip() == line
    # Preserve original leading/trailing whitespace on the line (should be none, but be exact).
    lines[idx] = linked_line
    new_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    readme_path.write_text(new_text, encoding="utf-8")
    fixed.append((family, platform))

print(f"Fixed: {len(fixed)}")
for f, p in fixed:
    print(f"  {f}/{p}")
print(f"Already OK: {len(already_ok)}")
for f, p in already_ok:
    print(f"  {f}/{p}")
print(f"Skipped: {len(skipped)}")
for f, p, reason in skipped:
    print(f"  {f}/{p}: {reason}")
