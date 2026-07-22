"""GitHub org discovery + additive merge for data/products.json.

Shared core of the registry-refresh machinery. Two callers, one safety
contract: the scheduled/manual CLI (scripts/data-refresh/update_products_registry.py)
and the supervise-time runtime self-heal (registry/self_heal.py). This module
holds the logic once (plans/GOVERNANCE.md placement rule 2); the callers stay
thin wrappers.

Safety contract (do not weaken without a plans/master.md decision edit):
    - Read-only against GitHub: only GET requests are ever issued.
    - data/products.json is the allow-list (docs/safety-model.md). Discovery MUST NOT be
      the thing that makes a repo operable: newly discovered (family, platform) pairs are
      always written with mode="disabled", ecosystem=None, policy_profile=None. Enabling a
      repo remains a manual edit per docs/policy-authoring.md.
    - Existing entries never have mode/ecosystem/policy_profile/overrides touched by
      discovery, regardless of what GitHub reports -- only the upstream-shaped fields
      (repo_name, repo_url, clone_url, active, discovered_via) are refreshed.
    - No entry is ever deleted, even if the repo disappears from GitHub -- a human
      decides that.

Writes here are NOT capability effects: data/products.json is this project's own
config-as-data, not a target repo surface, so nothing in this module goes through
capability dispatch or the effect ledger. The safety envelope is the merge()
invariants above plus write_atomic().
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import requests

# Deliberately cwd-relative, matching registry/loader.py's PRODUCTS_PATH (local
# dev and CI runners both execute from the repo root).
FAMILIES_PATH = Path("data/families.json")
PRODUCTS_PATH = Path("data/products.json")

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


class RegistryScanRateLimited(Exception):
    """A GitHub 403 rate limit asked us to wait longer than the caller's cap.

    The CLI passes no cap and sleeps out any wait (a cron job can afford an
    hour); the runtime self-heal caps the wait so a rate-limited scan degrades
    to a visible skip instead of silently blocking supervision.
    """

    def __init__(self, wait_seconds: int, max_wait_seconds: float):
        self.wait_seconds = wait_seconds
        self.max_wait_seconds = max_wait_seconds
        super().__init__(
            f"GitHub rate limit requires a {wait_seconds}s wait, "
            f"over the caller's {max_wait_seconds}s cap"
        )


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


def _paginate(
    url: str,
    params: dict,
    token: str | None,
    *,
    max_rate_limit_wait_seconds: float | None = None,
) -> Iterator[dict]:
    # Mypy hygiene fix (found pre-existing, unrelated to this pass -- fixed
    # in passing per "prove it in production, don't leave a known-broken
    # check unfixed"): `url`'s own parameter type is `str` (every real
    # caller always passes a genuine URL), but the loop's own "no next page"
    # signal is `None` -- a separate, correctly-`str | None`-typed local
    # carries that loop-control state instead of reassigning the parameter
    # to a value its own declared type doesn't allow.
    next_url: str | None = url
    while next_url:
        resp = requests.get(next_url, params=params, headers=_headers(token), timeout=30)
        if resp.status_code == 403:
            wait = _rate_limit_wait_seconds(resp)
            if max_rate_limit_wait_seconds is not None and wait > max_rate_limit_wait_seconds:
                raise RegistryScanRateLimited(wait, max_rate_limit_wait_seconds)
            time.sleep(wait)
            resp = requests.get(next_url, params=params, headers=_headers(token), timeout=30)
        resp.raise_for_status()
        yield from resp.json()
        link = resp.headers.get("Link", "")
        next_url = None
        for part in link.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        params = {}
        if next_url:
            time.sleep(_RATE_SLEEP)


def scan_org(
    org: str,
    *,
    token: str | None = None,
    max_rate_limit_wait_seconds: float | None = None,
) -> list[dict]:
    """List public repos for one GitHub org. Read-only GET, paginated."""
    url = f"{_GITHUB_API}/orgs/{org}/repos"
    params = {"type": "public", "per_page": 100, "sort": "pushed"}
    repos = []
    for raw in _paginate(
        url, params, token, max_rate_limit_wait_seconds=max_rate_limit_wait_seconds
    ):
        repos.append(
            {
                "name": raw["name"],
                "html_url": raw["html_url"],
                "clone_url": raw["clone_url"],
                "archived": bool(raw.get("archived")),
            }
        )
    return repos


def discover(
    families: list[dict],
    *,
    token: str | None = None,
    max_rate_limit_wait_seconds: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Scan every org in *families*; return (classified entries, org failures).

    Failures come back as data ([{"org": ..., "error": ...}]) instead of being
    printed here, so the CLI can warn on stderr and the self-heal can record
    them in evidence -- one bad org never loses the others either way.
    """
    discovered = []
    org_failures = []
    for fam in families:
        org = fam["github_org"]
        try:
            repos = scan_org(
                org, token=token, max_rate_limit_wait_seconds=max_rate_limit_wait_seconds
            )
        except Exception as exc:  # noqa: BLE001 -- one bad org must not lose the others
            org_failures.append({"org": org, "error": str(exc)})
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
    return discovered, org_failures


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
