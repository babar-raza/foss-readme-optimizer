"""Shared, read-only GitHub REST API client (Wave 7, decision #41 addendum)
-- consolidates the pagination/rate-limit pattern that already existed
independently in `registry/discovery.py::_paginate()` (formerly
`scripts/update_products_registry.py`)
(live-proven against all 26 real orgs) and `preflight/github_check.py`
(a one-off environment check). Four Wave 7 audit specialists (7b-7e) each
need substantially more GitHub API surface (contributors, languages,
stargazers/forks/watchers, releases, packages, Community Profile API,
description/homepage/topics) than either predecessor exposed -- one shared
module, per `GOV-015`/rule 8, rather than a fifth independent
reimplementation of the same pagination/rate-limit handling.

Read-only by design and by convention: every function here issues only GET
requests, matching every other GitHub API caller in this codebase
(`docs/safety-model.md`). No write verb is ever issued from this module.
"""

import base64
import time
from collections.abc import Iterator
from typing import Any

import requests

API_ROOT = "https://api.github.com"
_RATE_SLEEP = 1.0


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _rate_limit_wait_seconds(resp: requests.Response) -> int:
    """Mirrors `registry/discovery.py`'s own fix: GitHub
    signals two different rate limits on a 403 -- the secondary/abuse-
    detection limit (`Retry-After`, relative seconds) can fire with primary/
    core quota still remaining, so it is checked first, never folded into
    the same branch as `X-RateLimit-Reset` (an epoch timestamp)."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after is not None:
        return int(retry_after) + 2
    reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
    return max(1, reset - int(time.time())) + 2


def get_json(
    path: str, token: str | None, *, params: dict | None = None, timeout: float = 15
) -> Any:
    """One GET against `api.github.com/{path}`, with the same bounded
    403-retry `registry/discovery.py` already proved live.
    Raises `requests.HTTPError` on any other non-2xx response -- callers
    decide how to degrade, this function never silently swallows a real
    failure."""
    url = f"{API_ROOT}/{path.lstrip('/')}"
    resp = requests.get(url, params=params, headers=_headers(token), timeout=timeout)
    if resp.status_code == 403:
        time.sleep(_rate_limit_wait_seconds(resp))
        resp = requests.get(url, params=params, headers=_headers(token), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def paginate(
    path: str, token: str | None, *, params: dict | None = None, timeout: float = 15
) -> Iterator[dict]:
    """Follows GitHub's `Link: rel="next"` header -- identical mechanics to
    `registry/discovery.py::_paginate()`, live-proven against
    all 26 real orgs, promoted here as the shared, reusable implementation."""
    url: str | None = f"{API_ROOT}/{path.lstrip('/')}"
    query = dict(params or {})
    while url:
        resp = requests.get(url, params=query, headers=_headers(token), timeout=timeout)
        if resp.status_code == 403:
            time.sleep(_rate_limit_wait_seconds(resp))
            resp = requests.get(url, params=query, headers=_headers(token), timeout=timeout)
        resp.raise_for_status()
        yield from resp.json()
        link = resp.headers.get("Link", "")
        url = None
        for part in link.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
        query = {}
        if url:
            time.sleep(_RATE_SLEEP)


def repo_summary(org_repo: str, token: str | None) -> dict:
    """`GET /repos/{org}/{repo}` -- backs the stargazers/forks/watchers/
    primary-language fields the GitHub-generated-surface auditor (7b)
    needs."""
    return get_json(f"repos/{org_repo}", token)


def list_contributors(org_repo: str, token: str | None) -> list[dict]:
    """`GET /repos/{org}/{repo}/contributors`, paginated. Returns `[]` for a
    repo GitHub reports as having none classifiable (e.g. too large to
    compute) rather than raising -- callers treat that as a real, observable
    audit finding, not a transport failure."""
    try:
        return list(paginate(f"repos/{org_repo}/contributors", token, params={"per_page": 100}))
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in (204, 404):
            return []
        raise


def list_languages(org_repo: str, token: str | None) -> dict[str, int]:
    """`GET /repos/{org}/{repo}/languages` -- byte counts per Linguist-detected
    language, GitHub's own source of truth for the "Languages" bar."""
    return get_json(f"repos/{org_repo}/languages", token)


def list_releases(org_repo: str, token: str | None) -> list[dict]:
    """`GET /repos/{org}/{repo}/releases`, paginated -- backs the
    package/release auditor (7c). An empty list is a legitimate, common
    result (many real FOSS repos never cut a GitHub Release), not an error."""
    return list(paginate(f"repos/{org_repo}/releases", token, params={"per_page": 100}))


def get_tree(org_repo: str, sha: str, token: str | None, *, recursive: bool = True) -> dict:
    """`GET /repos/{org}/{repo}/git/trees/{sha}` -- backs `SCL-004`'s
    no-checkout manifest detection (decision #40/Part F): every path in the
    repo at `sha` in one call, no clone. `sha` is expected to come from
    `gitsafety.clone.remote_head_sha()` (a `git ls-remote`, already proven
    live and already the cheapest way to resolve it) -- this function never
    re-resolves a ref itself. Returns the raw response
    (`{"tree": [{"path", "type", ...}, ...], "truncated": bool, ...}`);
    callers MUST check `truncated` themselves -- GitHub silently caps this
    endpoint (~100k entries/7MB) rather than paginating it, so a `True` value
    means "this listing is incomplete," never "this repo has few files"."""
    params = {"recursive": "1"} if recursive else None
    return get_json(f"repos/{org_repo}/git/trees/{sha}", token, params=params)


def get_file_content(org_repo: str, path: str, token: str | None) -> bytes:
    """`GET /repos/{org}/{repo}/contents/{path}` -- the handful of matched
    manifest files `SCL-004`'s tree-based path needs the actual bytes of,
    never the whole tree. Raises if `path` names a directory (no `content`
    key) or is missing -- callers already know `path` exists from a prior
    `get_tree()` call, so either is a real error, not a case to degrade."""
    body = get_json(f"repos/{org_repo}/contents/{path}", token)
    return base64.b64decode(body["content"])


def get_community_profile(org_repo: str, token: str | None) -> dict:
    """`GET /repos/{org}/{repo}/community/profile` -- backs the community-
    files auditor (7e). `files` (verified live against `n8n-io/n8n` and
    `apache/pdfbox`, 2026-07-20) reports recognition for exactly `readme`,
    `license`, `code_of_conduct`, `contributing`, `issue_template`,
    `pull_request_template` -- GitHub does NOT report `security` or `support`
    recognition through this endpoint, confirmed by direct inspection of a
    real response, not assumed from the docs table alone. Callers must not
    treat a missing `security`/`support` key as "not recognized" the way a
    `null` value for a tracked key means that -- there is no recognition
    signal for those two files at all."""
    return get_json(f"repos/{org_repo}/community/profile", token)
