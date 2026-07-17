"""HTTPS/domain checks (deterministic, always run as part of link_whitelist)
plus optional live HEAD/GET reachability (opt-in only, --check-links,
WARNING severity -- external reachability is inherently flaky in CI and must
never be able to fail a run by default).
"""

from dataclasses import dataclass
from urllib.parse import urlparse

import requests


@dataclass
class LinkCheckResult:
    url: str
    ok: bool
    detail: str


def check_https(url: str) -> LinkCheckResult:
    scheme = urlparse(url).scheme
    if scheme == "https":
        return LinkCheckResult(url, True, "https")
    return LinkCheckResult(url, False, f"non-https scheme: {scheme!r}")


def check_live_reachable(url: str, timeout: float = 10) -> LinkCheckResult:
    """Opt-in only. A failure here is always WARNING-severity at the caller,
    never a hard gate -- reachability of a third-party marketing page is not
    something this tool can guarantee moment to moment."""
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            # Some sites don't support HEAD; retry with GET before giving up.
            resp = requests.get(url, timeout=timeout, allow_redirects=True)
        ok = resp.status_code < 400
        return LinkCheckResult(url, ok, f"HTTP {resp.status_code}")
    except requests.RequestException as exc:
        return LinkCheckResult(url, False, f"network error: {exc}")
