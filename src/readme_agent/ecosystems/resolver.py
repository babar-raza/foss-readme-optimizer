"""Live package-registry resolution, dispatched by ecosystem string -- mirrors
ecosystems/registry.py's "new ecosystems are new entries, not new call sites"
contract. Opt-in only: never called by default -- see links/validator.py for
the established pattern of live network checks staying opt-in, WARNING-only,
never a default hard gate.

Maven implemented first (Java is the only ecosystem with a shipped manifest
parser today); Python is next in priority by repository count (10 of 25
registry entries), not before -- see the portfolio-survey finding this
session recorded (plans/investigations/full-registry-portfolio-survey.md).

Maven resolution uses the AUTHORITATIVE `repo1.maven.org` metadata endpoint
(200 => published, 404 => not), NOT `search.maven.org`'s Solr index. Corrected
2026-07-24: the Solr index does not index the `org.aspose` group at all, so it
falsely reported every published Aspose Java package (3d/cells/pdf, all live on
`repo1.maven.org`) as "0 results" -- inverting the README pipeline into stripping
correct Maven installs. See
plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/.

Wave 11.2 (`PKG-001`-`004`): five more registries, one per remaining
ecosystem parser (`ecosystems/registry.py::_PARSERS`) -- PyPI (python), npm
(typescript), NuGet (net), the Go module proxy (go). Every URL/status-code
shape below was live-verified against the real registry, 2026-07-23 (a
real known-good package returning 200, a deliberately nonexistent name
returning 404), not assumed from documentation -- see each resolver's own
docstring for the specific packages checked.

`cpp` deliberately has no single `"cpp"` entry in `_RESOLVERS`: unlike
every other ecosystem, C/C++ has no one canonical registry (Conan Center
and vcpkg are two independent, unrelated indices, and `ecosystems/cpp.py`'s
own manifest has no field indicating which, if either, a given repository
actually publishes to) -- silently guessing which one applies would be
exactly the kind of guess `ECO-003`'s own "recorded, never guessed"
discipline forbids elsewhere. `resolve_conan()`/`resolve_vcpkg()` are
registered under the explicit `"cpp_conan"`/`"cpp_vcpkg"` keys instead, so
a caller checks whichever registry it has actual evidence for, never both
folded into one ambiguous "cpp" verdict.
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

from readme_agent.ecosystems.registry_request import registry_request_url
from readme_agent.retry import RetryableOperationError, run_http_with_retry

# crates.io's crawler policy rejects generic library User-Agents outright --
# live-verified 2026-07-25: the default `python-requests/x.y` UA gets 403 for
# BOTH an existing crate (serde) and a made-up name, which would otherwise be
# misread as a real network failure (blocked=True) rather than the true
# found/not-found answer. A descriptive UA naming this project fixes it.
_CRATES_IO_HEADERS = {"User-Agent": "readme-agent-foss-optimizer (github.com/aspose-cells-foss)"}
# Neither Conan Center nor vcpkg exposes a simple package-existence REST API
# (both are community-curated, git-hosted *recipe* indices, not centralized
# binary hosts the way PyPI/npm/NuGet are) -- live-verified 2026-07-23 that
# the recipe/port path itself, fetched as a raw file, is a reliable
# existence check: 200 for a real package (zlib, both registries), 404 for
# a made-up one. This checks "is there a build recipe for this name in the
# community index," the correct question for these two ecosystems, not "is
# a binary hosted" (neither registry hosts binaries centrally).
_RETRYABLE_STATUS = {429, 502, 503, 504}


@dataclass
class ResolutionResult:
    found: bool
    detail: str
    # Wave 11.2 (`PKG-005`): distinguishes "the registry was actually asked
    # and said no" (`blocked=False`) from "a real network failure meant no
    # answer was ever obtained" (`blocked=True`) -- `capabilities/
    # verify_package_acquisition.py` needs this to report `BLOCKED_NETWORK`
    # rather than the false-negative `NOT_PUBLISHED`. Defaults `False`,
    # preserving every existing call site's exact behavior.
    blocked: bool = False
    registry_label: str | None = None
    request_url: str | None = None
    status_code: int | None = None
    response_sha256: str | None = None
    retrieved_at: datetime | None = None


def _registry_get(
    url: str,
    *,
    timeout: float,
    params: dict | None = None,
    headers: dict | None = None,
) -> requests.Response:
    return run_http_with_retry(
        "package_registry",
        lambda: requests.get(url, params=params, timeout=timeout, headers=headers),
        retryable_statuses=_RETRYABLE_STATUS,
        sleep=time.sleep,
    )


def _resolve_maven(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    group_id = manifest.get("group_id")
    artifact_id = manifest.get("artifact_id")
    if not group_id or not artifact_id:
        return ResolutionResult(False, "manifest missing group_id/artifact_id -- cannot resolve")
    url = registry_request_url("java", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "Maven Central", f"{group_id}:{artifact_id}", timeout)


def _resolve_by_existence_url(
    url: str, label: str, subject: str, timeout: float = 10, *, headers: dict | None = None
) -> ResolutionResult:
    """Shared shape for every registry below whose "does this exist"
    question is answered by one GET returning 200 (exists) or 404 (does
    not) -- every resolver here except Maven Central's own richer
    search-query API above."""
    try:
        resp = _registry_get(url, timeout=timeout, headers=headers)
    except (requests.RequestException, RetryableOperationError) as exc:
        return ResolutionResult(
            False,
            f"network error resolving {label}: {exc}",
            blocked=True,
            registry_label=label,
            request_url=url,
            retrieved_at=datetime.now(UTC),
        )
    response_sha256 = hashlib.sha256(getattr(resp, "content", b"")).hexdigest()
    retrieved_at = datetime.now(UTC)
    if resp.status_code == 404:
        return ResolutionResult(
            False,
            f"{label}: {subject} NOT FOUND (404)",
            registry_label=label,
            request_url=url,
            status_code=resp.status_code,
            response_sha256=response_sha256,
            retrieved_at=retrieved_at,
        )
    try:
        resp.raise_for_status()
        return ResolutionResult(
            True,
            f"{label}: {subject} found",
            registry_label=label,
            request_url=url,
            status_code=resp.status_code,
            response_sha256=response_sha256,
            retrieved_at=retrieved_at,
        )
    except (requests.RequestException, RetryableOperationError) as exc:
        return ResolutionResult(
            False,
            f"network error resolving {label}: {exc}",
            blocked=True,
            registry_label=label,
            request_url=url,
            status_code=resp.status_code,
            response_sha256=response_sha256,
            retrieved_at=retrieved_at,
        )


def _resolve_pypi(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `pypi.org/pypi/requests/json` -> 200;
    a made-up name -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    url = registry_request_url("python", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "PyPI", name, timeout)


def _resolve_npm(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `registry.npmjs.org/lodash` -> 200; a
    made-up name -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    url = registry_request_url("typescript", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "npm", name, timeout)


def _resolve_nuget(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `api.nuget.org/v3-flatcontainer/
    newtonsoft.json/index.json` -> 200; a made-up id -> 404. NuGet's flat
    container index requires the package id lowercased in the URL path
    (its own documented convention) -- applied here, not left to chance."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    url = registry_request_url("net", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "NuGet", name, timeout)


def _resolve_go_proxy(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `proxy.golang.org/github.com/pkg/errors/
    @v/list` -> 200 (a real version list); a made-up module path -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    url = registry_request_url("go", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "Go proxy", name, timeout)


def _resolve_crates_io(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-25: `crates.io/api/v1/crates/serde` -> 200 (with
    the required custom User-Agent -- see `_CRATES_IO_HEADERS`); a made-up
    name -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    url = registry_request_url("rust", manifest)
    assert url is not None
    return _resolve_by_existence_url(
        url,
        "crates.io",
        name,
        timeout,
        headers=_CRATES_IO_HEADERS,
    )


def _resolve_conan(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: the `zlib` recipe path -> 200; a made-up
    name -> 404. See this module's own docstring for why this checks the
    recipe index, not a package host."""
    name = manifest.get("name") or manifest.get("library_target")
    if not name:
        return ResolutionResult(False, "manifest missing name/library_target -- cannot resolve")
    url = registry_request_url("cpp_conan", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "Conan Center", name, timeout)


def _resolve_vcpkg(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: the `zlib` port path -> 200; a made-up
    name -> 404. See this module's own docstring for why this checks the
    port index, not a package host."""
    name = manifest.get("name") or manifest.get("library_target")
    if not name:
        return ResolutionResult(False, "manifest missing name/library_target -- cannot resolve")
    url = registry_request_url("cpp_vcpkg", manifest)
    assert url is not None
    return _resolve_by_existence_url(url, "vcpkg", name, timeout)


_RESOLVERS = {
    "java": _resolve_maven,
    "python": _resolve_pypi,
    "typescript": _resolve_npm,
    "net": _resolve_nuget,
    "go": _resolve_go_proxy,
    "rust": _resolve_crates_io,
    "cpp_conan": _resolve_conan,
    "cpp_vcpkg": _resolve_vcpkg,
}


def resolve(ecosystem: str, manifest: dict[str, str]) -> ResolutionResult:
    resolver = _RESOLVERS.get(ecosystem)
    if resolver is None:
        return ResolutionResult(False, f"no live resolver registered for ecosystem {ecosystem!r}")
    return resolver(manifest)
