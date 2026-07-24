# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: authoritative package-acquisition ground-truth matrix for the whole registry
"""Verify every data/products.json entry's FOSS package against its AUTHORITATIVE registry.

The "aspose {family} foss" rule (verified live 2026-07-24): the published FOSS package is derived
from family+ecosystem, NEVER the manifest's self-declared name and NEVER the commercial package:

  java   -> Maven repo1.maven.org metadata for org.aspose:aspose-{f}-foss
            (NOT search.maven.org, which does not index the org.aspose group)
  python -> PyPI    aspose-{f}-foss
  net    -> NuGet   aspose.{f}.foss
  cpp    -> NuGet   aspose.{f}.cpp.foss                (C++ ships on NuGet, not Conan/vcpkg)
  typescript -> npm aspose-{f}-foss                    (no FOSS npm package today -> honest 404)
  go     -> Go proxy github.com/{org}/{repo-lower}/@v/list

200 => published, 404 => not published (honest source-build fallback). This is the
regression baseline the corrected resolver must match. Read-only network only.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTS = REPO_ROOT / "data" / "products.json"


def _get(url: str, timeout: float = 12.0) -> int:
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code in (429, 502, 503, 504) and attempt < 2:
                time.sleep(1.5)
                continue
            return resp.status_code
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1.5)
                continue
            return -1
    return -1


def _coordinate(entry: dict) -> tuple[str | None, str | None]:
    """Return (canonical FOSS coordinate label, existence-check URL) or (None, None)."""
    fam = entry["family"].lower()
    eco = entry.get("ecosystem")
    org = entry["repo_url"].split("/")[-2]
    repo = entry["repo_name"]
    if eco == "java":
        return (
            f"org.aspose:aspose-{fam}-foss",
            f"https://repo1.maven.org/maven2/org/aspose/aspose-{fam}-foss/maven-metadata.xml",
        )
    if eco == "python":
        return (
            f"aspose-{fam}-foss (PyPI)",
            f"https://pypi.org/pypi/aspose-{fam}-foss/json",
        )
    if eco == "net":
        return (
            f"Aspose.{fam}.FOSS (NuGet)",
            f"https://api.nuget.org/v3-flatcontainer/aspose.{fam}.foss/index.json",
        )
    if eco == "cpp":
        return (
            f"Aspose.{fam}.Cpp.FOSS (NuGet)",
            f"https://api.nuget.org/v3-flatcontainer/aspose.{fam}.cpp.foss/index.json",
        )
    if eco == "typescript":
        return (
            f"aspose-{fam}-foss (npm)",
            f"https://registry.npmjs.org/{quote(f'aspose-{fam}-foss', safe='')}",
        )
    if eco == "go":
        return (
            f"github.com/{org}/{repo.lower()} (Go proxy)",
            f"https://proxy.golang.org/github.com/{org}/{repo.lower()}/@v/list",
        )
    return (None, None)


def main() -> int:
    entries = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for entry in entries:
        org_repo = f"{entry['repo_url'].split('/')[-2]}/{entry['repo_name']}"
        eco = entry.get("ecosystem")
        if eco is None:
            rows.append(
                {
                    "org_repo": org_repo,
                    "family": entry["family"],
                    "platform": entry["platform"],
                    "ecosystem": None,
                    "mode": entry["mode"],
                    "coordinate": None,
                    "url": None,
                    "http_status": None,
                    "published": None,
                    "note": "disabled entry (no ecosystem) -- excluded",
                }
            )
            continue
        coordinate, url = _coordinate(entry)
        status = _get(url) if url else None
        published = status == 200 if isinstance(status, int) and status in (200, 404) else None
        rows.append(
            {
                "org_repo": org_repo,
                "family": entry["family"],
                "platform": entry["platform"],
                "ecosystem": eco,
                "mode": entry["mode"],
                "coordinate": coordinate,
                "url": url,
                "http_status": status,
                "published": published,
            }
        )
        verdict = "PUBLISHED" if published else ("NOT_PUBLISHED" if published is False else "?")
        print(f"  {org_repo:52} {eco:11} {str(coordinate):40} HTTP {status} -> {verdict}")

    matrix = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "rule": "aspose {family} foss against the authoritative registry per ecosystem; "
        "Maven uses repo1.maven.org (not search.maven.org); cpp uses NuGet; "
        "never the manifest name, never the commercial package",
        "entry_count": len(entries),
        "published_count": sum(1 for r in rows if r["published"] is True),
        "not_published_count": sum(1 for r in rows if r["published"] is False),
        "excluded_count": sum(1 for r in rows if r["ecosystem"] is None),
        "rows": rows,
    }
    out = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else REPO_ROOT / "package-acquisition-ground-truth.json"
    )
    out.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        f"\npublished={matrix['published_count']} not_published={matrix['not_published_count']} "
        f"excluded={matrix['excluded_count']} -> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
