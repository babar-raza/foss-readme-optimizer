"""One-shot correction of the 22 policy profiles a concurrent session generated
by pattern-substitution (2026-07-22) before their `products_com_link.url`
values had been checked against the real site.

`scripts/data-refresh/verify_policy_profile_facts.py` (built the same session)
live-verified every field these profiles assert:
  - `detected_license`: MIT confirmed for all 25 non-disabled registry entries
    -- 19 via GitHub's own license classifier, the remaining 6
    (3d/typescript, cells/{cpp,net,python}, words/python; cells/java's pilot
    profile already documents this same pattern) via an explicit "MIT" /
    "licensed under the MIT License" statement in the real README, matching
    the ground-truth-from-README precedent the aspose-cells-foss.yml pilot
    profile already established. No correction needed.
  - `products_org_link.url` (family and platform depth): all 200 for all 25
    entries. No correction needed -- the guessed pattern happened to hold,
    and is now genuinely verified rather than merely asserted.
  - `products_com_link.url` (platform depth): 9 of 22 templated URLs 404'd
    for real. Aspose's own site uses a `-net`/`-cpp` combined-binding slug
    for some Python platforms, and has no platform-specific page at all for
    two TypeScript-only families -- this script corrects exactly those 9,
    each mapped to a live-reverified URL (see PLATFORM_URL_CORRECTIONS).
    Every other templated com URL was already correct; left untouched.

Kept after use as the reviewable record of this correction (GOVERNANCE
placement rule 5), matching this project's own "kept, not deleted"
retrofit-script precedent.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_DIR = REPO_ROOT / "config" / "policies"

# (yaml filename, wrong url substring, corrected url) -- substring replace,
# not a YAML rewrite, so every other line (family_url, label, block, etc.)
# is preserved byte-for-byte.
PLATFORM_URL_CORRECTIONS = [
    (
        "aspose-3d-foss-python.yml",
        "url: https://products.aspose.com/3d/python/",
        "url: https://products.aspose.com/3d/python-net/",
    ),
    (
        # No TypeScript-specific page exists on products.aspose.com for 3d --
        # fall back to the family-level page (itself verified 200).
        "aspose-3d-foss-typescript.yml",
        "url: https://products.aspose.com/3d/typescript/",
        "url: https://products.aspose.com/3d/",
    ),
    (
        # Same fallback: cells/typescript has no dedicated com platform page.
        "aspose-cells-foss-typescript.yml",
        "url: https://products.aspose.com/cells/typescript/",
        "url: https://products.aspose.com/cells/",
    ),
    (
        "aspose-email-foss-python.yml",
        "url: https://products.aspose.com/email/python/",
        "url: https://products.aspose.com/email/python-net/",
    ),
    (
        "aspose-font-foss-python.yml",
        "url: https://products.aspose.com/font/python/",
        "url: https://products.aspose.com/font/",
    ),
    (
        "aspose-note-foss-python.yml",
        "url: https://products.aspose.com/note/python/",
        "url: https://products.aspose.com/note/",
    ),
    (
        "aspose-page-foss-python.yml",
        "url: https://products.aspose.com/page/python/",
        "url: https://products.aspose.com/page/python-net/",
    ),
    (
        "aspose-pdf-foss-go.yml",
        "url: https://products.aspose.com/pdf/go/",
        "url: https://products.aspose.com/pdf/go-cpp/",
    ),
    (
        "aspose-tex-foss-python.yml",
        "url: https://products.aspose.com/tex/python/",
        "url: https://products.aspose.com/tex/python-net/",
    ),
]


def main() -> int:
    changed = 0
    for filename, old, new in PLATFORM_URL_CORRECTIONS:
        path = POLICIES_DIR / filename
        text = path.read_text(encoding="utf-8")
        if old not in text:
            print(
                f"SKIP {filename}: expected substring not found (already fixed?)", file=sys.stderr
            )
            continue
        if text.count(old) != 1:
            print(
                f"ABORT {filename}: substring appears {text.count(old)} times, expected 1",
                file=sys.stderr,
            )
            return 1
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
        print(f"OK {filename}: {old.split('url: ')[1]} -> {new.split('url: ')[1]}")
        changed += 1

    print(f"\n{changed}/{len(PLATFORM_URL_CORRECTIONS)} profiles corrected.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
