"""Live package-registry resolution, dispatched by ecosystem string -- mirrors
ecosystems/registry.py's "new ecosystems are new entries, not new call sites"
contract. Opt-in only: never called by default -- see links/validator.py for
the established pattern of live network checks staying opt-in, WARNING-only,
never a default hard gate.

Maven implemented first (Java is the only ecosystem with a shipped manifest
parser today); Python is next in priority by repository count (10 of 25
registry entries), not before -- see the portfolio-survey finding this
session recorded (plans/investigations/full-registry-portfolio-survey.md).

This is the concrete mechanism that would have caught the real cells-java
finding automatically: its README instructs a Maven Central dependency
(org.aspose:aspose-cells-foss) that returns zero results.

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

from dataclasses import dataclass

import requests

_MAVEN_CENTRAL_SEARCH_URL = "https://search.maven.org/solrsearch/select"
_PYPI_URL_TEMPLATE = "https://pypi.org/pypi/{name}/json"
_NPM_URL_TEMPLATE = "https://registry.npmjs.org/{name}"
_NUGET_URL_TEMPLATE = "https://api.nuget.org/v3-flatcontainer/{name}/index.json"
_GO_PROXY_URL_TEMPLATE = "https://proxy.golang.org/{module}/@v/list"
# Neither Conan Center nor vcpkg exposes a simple package-existence REST API
# (both are community-curated, git-hosted *recipe* indices, not centralized
# binary hosts the way PyPI/npm/NuGet are) -- live-verified 2026-07-23 that
# the recipe/port path itself, fetched as a raw file, is a reliable
# existence check: 200 for a real package (zlib, both registries), 404 for
# a made-up one. This checks "is there a build recipe for this name in the
# community index," the correct question for these two ecosystems, not "is
# a binary hosted" (neither registry hosts binaries centrally).
_CONAN_CENTER_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/conan-io/conan-center-index/master/recipes/{name}/config.yml"
)
_VCPKG_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/microsoft/vcpkg/master/ports/{name}/vcpkg.json"
)


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


def _resolve_maven(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    group_id = manifest.get("group_id")
    artifact_id = manifest.get("artifact_id")
    if not group_id or not artifact_id:
        return ResolutionResult(False, "manifest missing group_id/artifact_id -- cannot resolve")
    try:
        resp = requests.get(
            _MAVEN_CENTRAL_SEARCH_URL,
            params={"q": f"g:{group_id} AND a:{artifact_id}", "rows": "1", "wt": "json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        found = resp.json()["response"]["numFound"] > 0
        return ResolutionResult(
            found,
            f"Maven Central: {group_id}:{artifact_id} "
            f"{'found' if found else 'NOT FOUND (0 results)'}",
        )
    except requests.RequestException as exc:
        return ResolutionResult(
            False, f"network error resolving Maven Central: {exc}", blocked=True
        )
    except (KeyError, ValueError) as exc:
        return ResolutionResult(False, f"unexpected Maven Central response shape: {exc}")


def _resolve_by_existence_url(
    url: str, label: str, subject: str, timeout: float = 10
) -> ResolutionResult:
    """Shared shape for every registry below whose "does this exist"
    question is answered by one GET returning 200 (exists) or 404 (does
    not) -- every resolver here except Maven Central's own richer
    search-query API above."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 404:
            return ResolutionResult(False, f"{label}: {subject} NOT FOUND (404)")
        resp.raise_for_status()
        return ResolutionResult(True, f"{label}: {subject} found")
    except requests.RequestException as exc:
        return ResolutionResult(False, f"network error resolving {label}: {exc}", blocked=True)


def _resolve_pypi(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `pypi.org/pypi/requests/json` -> 200;
    a made-up name -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    return _resolve_by_existence_url(_PYPI_URL_TEMPLATE.format(name=name), "PyPI", name, timeout)


def _resolve_npm(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `registry.npmjs.org/lodash` -> 200; a
    made-up name -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    return _resolve_by_existence_url(_NPM_URL_TEMPLATE.format(name=name), "npm", name, timeout)


def _resolve_nuget(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `api.nuget.org/v3-flatcontainer/
    newtonsoft.json/index.json` -> 200; a made-up id -> 404. NuGet's flat
    container index requires the package id lowercased in the URL path
    (its own documented convention) -- applied here, not left to chance."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    return _resolve_by_existence_url(
        _NUGET_URL_TEMPLATE.format(name=name.lower()), "NuGet", name, timeout
    )


def _escape_go_module_path(module: str) -> str:
    """The Go module proxy protocol escapes uppercase letters as `!`+
    lowercase (`golang.org/x/mod/module`'s own `EscapePath` convention) --
    live-verified 2026-07-23: `proxy.golang.org/.../PuerkitoBio/...` 404s;
    the escaped `.../!puerkito!bio/...` resolves."""
    return "".join(f"!{c.lower()}" if c.isupper() else c for c in module)


def _resolve_go_proxy(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: `proxy.golang.org/github.com/pkg/errors/
    @v/list` -> 200 (a real version list); a made-up module path -> 404."""
    name = manifest.get("name")
    if not name:
        return ResolutionResult(False, "manifest missing name -- cannot resolve")
    escaped = _escape_go_module_path(name)
    return _resolve_by_existence_url(
        _GO_PROXY_URL_TEMPLATE.format(module=escaped), "Go proxy", name, timeout
    )


def _resolve_conan(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: the `zlib` recipe path -> 200; a made-up
    name -> 404. See this module's own docstring for why this checks the
    recipe index, not a package host."""
    name = manifest.get("name") or manifest.get("library_target")
    if not name:
        return ResolutionResult(False, "manifest missing name/library_target -- cannot resolve")
    return _resolve_by_existence_url(
        _CONAN_CENTER_URL_TEMPLATE.format(name=name.lower()), "Conan Center", name, timeout
    )


def _resolve_vcpkg(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    """Live-verified 2026-07-23: the `zlib` port path -> 200; a made-up
    name -> 404. See this module's own docstring for why this checks the
    port index, not a package host."""
    name = manifest.get("name") or manifest.get("library_target")
    if not name:
        return ResolutionResult(False, "manifest missing name/library_target -- cannot resolve")
    return _resolve_by_existence_url(
        _VCPKG_URL_TEMPLATE.format(name=name.lower()), "vcpkg", name, timeout
    )


_RESOLVERS = {
    "java": _resolve_maven,
    "python": _resolve_pypi,
    "typescript": _resolve_npm,
    "net": _resolve_nuget,
    "go": _resolve_go_proxy,
    "cpp_conan": _resolve_conan,
    "cpp_vcpkg": _resolve_vcpkg,
}


def resolve(ecosystem: str, manifest: dict[str, str]) -> ResolutionResult:
    resolver = _RESOLVERS.get(ecosystem)
    if resolver is None:
        return ResolutionResult(False, f"no live resolver registered for ecosystem {ecosystem!r}")
    return resolver(manifest)
