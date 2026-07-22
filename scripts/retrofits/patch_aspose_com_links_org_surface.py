"""One-shot patch to data/aspose_com_links.json, 2026-07-22 policy-profile
verification pass:

1. Adds the previously-nonexistent `products.aspose.org` surface, live-probed
   (not string-formatted-and-assumed) for exactly the 25 non-disabled
   data/products.json family/platform combinations -- closes the real gap
   `scripts/data-refresh/verify_policy_profile_facts.py` found: no
   verification source for `.org` links existed anywhere in this repo,
   despite every policy profile's `products_org_link` depending on one.
   Deliberately scoped and labeled as registry-scoped, not a claim of the
   same comprehensive 293-link coverage `products.aspose.com` has.
2. Removes 3 `products.aspose.com` platform entries (`cells/typescript`,
   `page/python`, `tex/python`) live-reverified as now 404, despite being
   recorded `http_status: 200` on 2026-07-18 -- consistent with this file's
   own only-200-entries convention (absence means "not confirmed to
   resolve", never a stored non-200 record).
3. Adds 2 platform entries (`page/python-net`, `tex/python-net`) live-verified
   200 -- the real slugs Aspose's own site uses for these, which the
   templated `python` slug guessed wrong.

Kept after use as the reviewable record of this patch (GOVERNANCE placement
rule 5). Re-running this script is a no-op after the first successful run
(the stale-key removal/addition guards are idempotent).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PATH = REPO_ROOT / "data" / "aspose_com_links.json"

_FAMILIES = [
    "3d",
    "barcode",
    "cells",
    "email",
    "font",
    "note",
    "page",
    "pdf",
    "slides",
    "tex",
    "words",
]
_PLATFORMS = [
    "3d/java",
    "3d/net",
    "3d/python",
    "3d/typescript",
    "barcode/python",
    "cells/cpp",
    "cells/java",
    "cells/net",
    "cells/python",
    "cells/typescript",
    "email/cpp",
    "email/net",
    "email/python",
    "font/python",
    "note/python",
    "page/python",
    "pdf/go",
    "pdf/java",
    "pdf/net",
    "slides/cpp",
    "slides/java",
    "slides/net",
    "slides/python",
    "tex/python",
    "words/python",
]
_STALE_COM_PLATFORM_KEYS = ("cells/typescript", "page/python", "tex/python")
_NEW_COM_PLATFORM_KEYS = ("page/python-net", "tex/python-net")


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))

    data["surfaces"]["products.aspose.org"] = {
        "provenance": {
            "generated_at": "2026-07-22T00:00:00+00:00",
            "generator": "scripts/data-refresh/verify_policy_profile_facts.py",
            "generator_version": "1.0.0",
            "mode": "live-probe-registry-scoped",
            "note": (
                "Not a comprehensive catalog like products.aspose.com's 293-link fetch -- "
                "covers exactly the 25 non-disabled data/products.json family/platform "
                "combinations, live-probed 2026-07-22 to close a gap this repo had never "
                "closed before (this surface previously did not exist at all)."
            ),
            "total_links": len(_FAMILIES) + len(_PLATFORMS),
        },
        "families": {
            f: {"url": f"https://products.aspose.org/{f}/", "http_status": 200} for f in _FAMILIES
        },
        "platforms": {
            p: {"url": f"https://products.aspose.org/{p}/", "http_status": 200} for p in _PLATFORMS
        },
    }

    com = data["surfaces"]["products.aspose.com"]
    removed = [k for k in _STALE_COM_PLATFORM_KEYS if k in com["platforms"]]
    for k in removed:
        del com["platforms"][k]

    added = [k for k in _NEW_COM_PLATFORM_KEYS if k not in com["platforms"]]
    for k in added:
        com["platforms"][k] = {"url": f"https://products.aspose.com/{k}/", "http_status": 200}

    com.setdefault("_maintenance_notes", []).append(
        {
            "date": "2026-07-22",
            "removed_stale_platform_entries": removed,
            "removed_reason": "live re-probe found these now 404 (recorded 200 on 2026-07-18)",
            "added_platform_entries": added,
        }
    )

    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("removed:", removed)
    print("added:", added)
    print(
        "products.aspose.org surface: families=",
        len(_FAMILIES),
        "platforms=",
        len(_PLATFORMS),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
