"""Refresh data/products.json by scanning the GitHub orgs listed in data/families.json.

Usage:
    python scripts/update_products_registry.py [--dry-run] [--token TOKEN]
    python scripts/update_products_registry.py --org aspose-3d-foss,aspose-pdf-foss

Safety contract (do not weaken without a plans/master.md decision edit):
    - Read-only against GitHub: only GET requests are ever issued.
    - data/products.json is the allow-list (docs/safety-model.md). This script MUST NOT be the
      thing that makes a repo operable: newly discovered (family, platform) pairs are always
      written with mode="disabled", ecosystem=None, policy_profile=None. Enabling a repo remains
      a manual edit per docs/policy-authoring.md.
    - Existing entries never have mode/ecosystem/policy_profile/overrides touched by this script,
      regardless of what GitHub reports -- only the upstream-shaped fields (repo_name, repo_url,
      clone_url, active, discovered_via) are refreshed.
    - No entry is ever deleted, even if the repo disappears from GitHub -- a human decides that.

Output: data/products.json, written atomically (tmp file + os.replace).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
FAMILIES_PATH = REPO_ROOT / "data" / "families.json"
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"

_GITHUB_API = "https://api.github.com"
_RATE_SLEEP = 1.0

# Aspose.{Family}-FOSS-for-{Platform} (e.g. Aspose.3D-FOSS-for-Java)
_REPO_PATTERN_FOSS = re.compile(r"^Aspose\.([A-Za-z0-9]+)-FOSS-for-([A-Za-z0-9.]+)$")
# aspose-{family}-foss-for-{platform} (e.g. aspose-pdf-foss-for-go)
_REPO_PATTERN_FOSS_LOWER = re.compile(r"^aspose-([a-z0-9]+)-foss-for-([a-z0-9]+)$")

_PLATFORM_MAP = {
    "python": "python",
    "java": "java",
    ".net": "net",
    "net": "net",
    "cpp": "cpp",
    "typescript": "typescript",
    "javascript": "javascript",
    "nodejs": "nodejs",
    "go": "go",
}


def classify_repo_name(repo_name: str) -> tuple[str, str] | None:
    """Return (family, platform) for a repo name, or None when it matches neither FOSS naming
    convention observed across the registry (see data/products.json's real repo_name values)."""
    m = _REPO_PATTERN_FOSS.match(repo_name)
    if m:
        family = m.group(1).lower()
        platform_raw = m.group(2).lower()
        return family, _PLATFORM_MAP.get(platform_raw, platform_raw)

    m = _REPO_PATTERN_FOSS_LOWER.match(repo_name.lower())
    if m:
        platform_raw = m.group(2)
        return m.group(1), _PLATFORM_MAP.get(platform_raw, platform_raw)

    return None


def load_families(path: Path = FAMILIES_PATH) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} must be a JSON array")
    return raw


# ---------------------------------------------------------------------------
# GitHub org scanning (read-only: GET requests only)
# ---------------------------------------------------------------------------


def _headers(token: str | None) -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _rate_limit_wait_seconds(resp) -> int:
    """GitHub signals two different rate limits on a 403: the primary/core limit
    (X-RateLimit-Reset, an epoch timestamp) and the secondary/abuse-detection limit
    (Retry-After, a relative second count) -- the latter can fire with quota still
    remaining, so it must be checked first, not folded into the same branch."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after is not None:
        return int(retry_after) + 2
    reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
    return max(1, reset - int(time.time())) + 2


def _paginate(url: str, params: dict, token: str | None) -> Iterator[dict]:
    while url:
        resp = requests.get(url, params=params, headers=_headers(token), timeout=30)
        if resp.status_code == 403:
            time.sleep(_rate_limit_wait_seconds(resp))
            resp = requests.get(url, params=params, headers=_headers(token), timeout=30)
        resp.raise_for_status()
        yield from resp.json()
        link = resp.headers.get("Link", "")
        url = None
        for part in link.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
        params = {}
        if url:
            time.sleep(_RATE_SLEEP)


def scan_org(org: str, *, token: str | None = None) -> list[dict]:
    """List public repos for one GitHub org. Read-only GET, paginated."""
    url = f"{_GITHUB_API}/orgs/{org}/repos"
    params = {"type": "public", "per_page": 100, "sort": "pushed"}
    repos = []
    for raw in _paginate(url, params, token):
        repos.append(
            {
                "name": raw["name"],
                "html_url": raw["html_url"],
                "clone_url": raw["clone_url"],
                "archived": bool(raw.get("archived")),
            }
        )
    return repos


def discover(families: list[dict], *, token: str | None = None) -> list[dict]:
    """Scan every org in *families* and return classified product entries."""
    discovered = []
    for fam in families:
        org = fam["github_org"]
        try:
            repos = scan_org(org, token=token)
        except Exception as exc:  # noqa: BLE001 -- one bad org must not lose the others
            print(f"WARN: could not scan {org}: {exc}", file=sys.stderr)
            continue
        for repo in repos:
            pair = classify_repo_name(repo["name"])
            if pair is None:
                continue
            family, platform = pair
            discovered.append(
                {
                    "family": family,
                    "platform": platform,
                    "repo_name": repo["name"],
                    "repo_url": repo["html_url"],
                    "clone_url": repo["clone_url"],
                    "active": not repo["archived"],
                    "discovered_via": "github",
                }
            )
    return discovered


# ---------------------------------------------------------------------------
# Merge -- see the safety contract in the module docstring
# ---------------------------------------------------------------------------

_UPSTREAM_FIELDS = ("repo_name", "repo_url", "clone_url", "active", "discovered_via")
_OWNED_FIELDS = ("mode", "ecosystem", "policy_profile")


def merge(existing: list[dict], discovered: list[dict]) -> list[dict]:
    registry = {(e["family"], e["platform"]): dict(e) for e in existing}

    for entry in discovered:
        key = (entry["family"], entry["platform"])
        if key not in registry:
            registry[key] = {
                **entry,
                "mode": "disabled",
                "ecosystem": None,
                "policy_profile": None,
            }
        else:
            for field in _UPSTREAM_FIELDS:
                registry[key][field] = entry[field]
            # _OWNED_FIELDS are deliberately never written here.

    return sorted(registry.values(), key=lambda e: (e["family"], e["platform"]))


def write_atomic(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        Path(tmp_path).replace(path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", help="GitHub token (falls back to GH_TOKEN / GITHUB_PAT env)")
    parser.add_argument(
        "--org", help="Comma-separated GitHub orgs to scan (default: every org in families.json)"
    )
    parser.add_argument(
        "--families", type=Path, default=FAMILIES_PATH, help="Path to data/families.json"
    )
    parser.add_argument(
        "--products", type=Path, default=PRODUCTS_PATH, help="Path to data/products.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the diff; do not write data/products.json"
    )
    args = parser.parse_args(argv)

    if requests is None:
        print("ERROR: requests is required (pip install -e .)", file=sys.stderr)
        return 2

    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT")

    families = load_families(args.families)
    if args.org:
        wanted = {o.strip() for o in args.org.split(",") if o.strip()}
        families = [f for f in families if f["github_org"] in wanted]

    org_names = [f["github_org"] for f in families]
    print(f"Scanning {len(families)} org(s): {org_names}", file=sys.stderr)
    discovered = discover(families, token=token)
    matched_msg = f"  matched {len(discovered)} repo(s) against the FOSS naming convention"
    print(matched_msg, file=sys.stderr)

    existing: list[dict] = []
    if args.products.is_file():
        existing = json.loads(args.products.read_text(encoding="utf-8"))

    merged = merge(existing, discovered)
    new_count = len(merged) - len(existing)

    if args.dry_run:
        print(f"{'family':<12} {'platform':<12} {'repo_name':<40} {'mode':<10} {'active'}")
        print("-" * 90)
        for e in merged:
            print(
                f"{e['family']:<12} {e['platform']:<12} {e['repo_name']:<40} "
                f"{e['mode']:<10} {e.get('active', False)}"
            )
        print(f"\nTotal: {len(merged)}  new={new_count}")
        print("DRY-RUN: data/products.json was NOT modified.")
        return 0

    write_atomic(args.products, merged)
    print(f"OK  wrote {len(merged)} entries to {args.products} (new={new_count})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
