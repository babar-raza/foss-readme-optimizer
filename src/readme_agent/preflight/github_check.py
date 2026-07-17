"""Live GitHub read-check: GET /repos/{org}/{repo} and GET /user, GH_TOKEN > GITHUB_PAT.

The only call sites in this module are GET requests -- no write verb is ever
issued here, matching the rest of the codebase's read-only contract.
"""

from dataclasses import dataclass, field

import requests

API_ROOT = "https://api.github.com"


@dataclass
class GithubRepoCheck:
    org_repo: str
    http_status: int | None
    ok: bool
    default_branch: str | None = None
    license: str | None = None
    error: str | None = None


@dataclass
class GithubIdentity:
    ok: bool
    login: str | None = None
    scopes: list[str] = field(default_factory=list)
    error: str | None = None


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def check_identity(token: str, timeout: float = 15) -> GithubIdentity:
    try:
        resp = requests.get(f"{API_ROOT}/user", headers=_headers(token), timeout=timeout)
    except requests.RequestException as exc:
        return GithubIdentity(ok=False, error=f"network error: {exc}")
    if resp.status_code != 200:
        return GithubIdentity(ok=False, error=f"HTTP {resp.status_code} from GET /user")
    scopes_header = resp.headers.get("X-OAuth-Scopes", "")
    scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
    return GithubIdentity(ok=True, login=resp.json().get("login"), scopes=scopes)


def check_repo(org_repo: str, token: str, timeout: float = 15) -> GithubRepoCheck:
    try:
        resp = requests.get(
            f"{API_ROOT}/repos/{org_repo}", headers=_headers(token), timeout=timeout
        )
    except requests.RequestException as exc:
        return GithubRepoCheck(org_repo=org_repo, http_status=None, ok=False, error=str(exc))
    if resp.status_code != 200:
        return GithubRepoCheck(
            org_repo=org_repo,
            http_status=resp.status_code,
            ok=False,
            error=f"HTTP {resp.status_code}",
        )
    body = resp.json()
    license_info = body.get("license") or {}
    return GithubRepoCheck(
        org_repo=org_repo,
        http_status=200,
        ok=True,
        default_branch=body.get("default_branch"),
        license=license_info.get("spdx_id"),
    )
