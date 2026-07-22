"""Write-verb GitHub REST API calls (TC-08, `PRL-*`) -- deliberately
separate from `client.py`, which is read-only by design and by convention
(its own module docstring's explicit invariant, `docs/safety-model.md`:
"No write verb is ever issued from this module"). Every function here
issues a real `POST` against a real repo -- gated end to end by
`capabilities/open_presentation_pr.py`'s own `remote_write` side_effect_class,
domain scoping, and the effect ledger, exactly like `commit_readme_write`
gates its one `local_write` call. No function here is ever imported by a
read-only audit capability.
"""

import time

import requests

from readme_agent.github_api.client import API_ROOT, _headers, _rate_limit_wait_seconds


def find_open_pr(
    org_repo: str, branch_name: str, token: str | None, *, timeout: float = 15
) -> dict | None:
    """`GET /repos/{org}/{repo}/pulls?head=...` -- a read, but colocated
    here rather than in `client.py` since it exists solely to support this
    module's own dedup logic (`PRL-001`): before ever pushing a branch or
    creating a PR, `capabilities/open_presentation_pr.py` checks whether one
    already exists for this exact head branch. Returns the first open PR
    for that branch, or `None` if none exists."""
    owner = org_repo.split("/")[0]
    url = f"{API_ROOT}/repos/{org_repo}/pulls"
    params = {"head": f"{owner}:{branch_name}", "state": "open"}
    resp = requests.get(url, params=params, headers=_headers(token), timeout=timeout)
    if resp.status_code == 403:
        time.sleep(_rate_limit_wait_seconds(resp))
        resp = requests.get(url, params=params, headers=_headers(token), timeout=timeout)
    resp.raise_for_status()
    results = resp.json()
    return results[0] if results else None


def create_pull_request(
    org_repo: str,
    *,
    head: str,
    base: str,
    title: str,
    body: str,
    token: str | None,
    timeout: float = 15,
) -> dict:
    """`POST /repos/{org}/{repo}/pulls` -- the one real PR-creation call
    this project makes. Never merges, never approves, never even comments
    on the result -- the human reviewing it on GitHub is the sole approval
    authority (`PR-merge-as-approval`, decision #46)."""
    url = f"{API_ROOT}/repos/{org_repo}/pulls"
    payload = {"head": head, "base": base, "title": title, "body": body}
    resp = requests.post(url, json=payload, headers=_headers(token), timeout=timeout)
    if resp.status_code == 403:
        time.sleep(_rate_limit_wait_seconds(resp))
        resp = requests.post(url, json=payload, headers=_headers(token), timeout=timeout)
    resp.raise_for_status()
    return resp.json()
