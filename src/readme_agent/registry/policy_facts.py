"""Verify the real, checkable business facts a policy profile asserts.

A policy profile's `detected_license` and `products_org_link`/
`products_com_link` fields are business facts this codebase MUST NEVER
invent (decision #4, docs/policy-authoring.md) -- data/README.md's own rule
says never construct a link by string-formatting a family/platform name,
since only a verified, resolving URL confirms it's real. Found live,
2026-07-22: a session did exactly the forbidden thing for 22 policy
profiles, and 9 of the 22 guessed `.com` platform URLs turned out to be
genuinely wrong. This module is the fix: the one place that actually
fetches/probes these facts instead of guessing them, shared by
`scripts/data-refresh/verify_policy_profile_facts.py` (bulk audit CLI) and
`readme-agent scaffold-policy` (new-profile authoring, `ONB-004`).

Read-only: one GitHub API GET per repo (license + README text), plus one
HTTP GET per org/com URL at family and platform depth.
"""

from __future__ import annotations

import requests

from readme_agent.github_api.client import repo_summary

_BROWSER_LIKE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# README phrasings actually observed across the real registry's repos
# (2026-07-22 verification pass) when GitHub's own license classifier
# returns null -- matches the ground-truth-from-README precedent the
# aspose-cells-foss.yml pilot profile already established.
_LICENSE_README_MARKERS = (
    "mit license",
    "apache license",
    "bsd license",
    "gpl",
    "license: mit",
    "licensed under",
    "## license\n\nmit",
    "## license\n\nmit.",
)


def _http_status(url: str) -> int | None:
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True, headers=_BROWSER_LIKE_HEADERS)
        if resp.status_code in (405, 403):
            resp = requests.get(
                url, timeout=10, allow_redirects=True, headers=_BROWSER_LIKE_HEADERS
            )
        return resp.status_code
    except requests.RequestException:
        return None


def _readme_states_license(org_repo: str) -> str | None:
    """Best-effort text scan of the real README for an explicit license
    statement, when GitHub's classifier itself returns null. Returns a
    human-readable label (e.g. "MIT") or None if nothing is found -- never
    a guess."""
    for ref in ("HEAD", "main", "master"):
        url = f"https://raw.githubusercontent.com/{org_repo}/{ref}/README.md"
        try:
            resp = requests.get(url, timeout=10)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        lowered = resp.text.lower()
        for marker in _LICENSE_README_MARKERS:
            idx = lowered.find(marker)
            if idx == -1:
                continue
            nearby = lowered[max(0, idx - 20) : idx + 60]
            if "mit" in marker or "mit" in nearby:
                return "MIT"
            return marker.split()[0].upper()
        return None
    return None


def verify_repo_facts(org_repo: str, family: str, platform: str, token: str | None) -> dict:
    """Live-verify everything a policy profile would otherwise have to
    guess. Never raises -- a lookup failure just means that field comes
    back None/unresolved, for the caller to flag rather than invent."""
    license_spdx = None
    try:
        summary = repo_summary(org_repo, token)
        license_spdx = (summary.get("license") or {}).get("spdx_id")
    except requests.HTTPError:
        pass
    if license_spdx in (None, "NOASSERTION"):
        license_spdx = _readme_states_license(org_repo)

    org_family_url = f"https://products.aspose.org/{family}/"
    org_platform_url = f"https://products.aspose.org/{family}/{platform}/"
    com_family_url = f"https://products.aspose.com/{family}/"
    com_platform_url = f"https://products.aspose.com/{family}/{platform}/"

    org_platform_status = _http_status(org_platform_url)
    com_platform_status = _http_status(com_platform_url)

    return {
        "org_repo": org_repo,
        "family": family,
        "platform": platform,
        "license": license_spdx,
        "org_family_url": org_family_url,
        "org_family_status": _http_status(org_family_url),
        "org_platform_url": org_platform_url,
        "org_platform_status": org_platform_status,
        "com_family_url": com_family_url,
        "com_family_status": _http_status(com_family_url),
        "com_platform_url": com_platform_url,
        "com_platform_status": com_platform_status,
    }
