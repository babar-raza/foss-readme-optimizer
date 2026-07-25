"""Detect the JDK major version a repo's Maven build REQUIRES, and
auto-provision a checksum-verified Eclipse Temurin build for it -- RPOC-041.

Root cause this replaces: `_verify_java` (`facts/local_verification.py`)
used to compile/run every repo's minimal example with whatever JDK
`env.java_home()`/ambient PATH happened to provide, never the repo's own
declared `<maven.compiler.release>`/`source`/`target`. Real per-repo
requirements differ -- confirmed from actual `pom.xml` files:
aspose-3d-foss needs JDK 21, aspose-cells-foss needs 17, aspose-pdf-foss
needs 11 -- so one machine-wide `--java-home` cannot serve every repo, and
the prior "fix" (manually pointing at a pre-existing local JDK install)
was fragile, machine-specific, and did not scale to CI or new repos.

Two independent steps, each usable on its own:
  * `required_java_major_version()` -- pure, offline pom.xml parsing.
  * `provision_jdk()` -- given a required major version, prefer whatever
    is already usable (an already-matching `README_AGENT_JAVA_HOME`, or a
    prior download cached under `runs/toolchains/`) and only download when
    nothing available already matches.

Local/CLI-invocable logic today; a later taskcard wires an isolated
Actions job around it -- nothing here assumes an interactive/local-only
environment (no shelling out to a platform-specific archiver, no
hardcoded OS/arch), so it should need no changes to run from CI later.
"""

from __future__ import annotations

import hashlib
import platform
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

from readme_agent import env, paths
from readme_agent.retry import RetryableOperationError, run_http_with_retry

# No `<maven.compiler.release>`/`source`/`target` specified at all: fall
# back to the newest LTS this project's own registered repos have needed
# so far (aspose-cells-foss's 17), rather than crashing or guessing an
# older/newer value with no evidence behind it.
DEFAULT_JAVA_MAJOR_VERSION = 17

_ADOPTIUM_ASSETS_URL = "https://api.adoptium.net/v3/assets/feature_releases/{major}/ga"
_ADOPTIUM_METADATA_TIMEOUT_SECONDS = 30
_ADOPTIUM_DOWNLOAD_TIMEOUT_SECONDS = 900
# Same retryable-status set `ecosystems/resolver.py` uses for the other
# read-only external-registry GETs in this project.
_RETRYABLE_STATUSES = {429, 502, 503, 504}
_DOWNLOAD_CHUNK_BYTES = 1024 * 1024

# platform.system()/platform.machine() -> Adoptium's own `os`/`architecture`
# query values (https://api.adoptium.net/v3/assets/feature_releases/...).
_ADOPTIUM_OS_NAMES = {"Windows": "windows", "Linux": "linux", "Darwin": "mac"}
_ADOPTIUM_ARCH_NAMES = {
    "AMD64": "x64",
    "x86_64": "x64",
    "ARM64": "aarch64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
}


class JavaToolchainError(RuntimeError):
    """Required-version detection or JDK provisioning failed unrecoverably.

    Callers (`_verify_java`) treat this as `BLOCKED_TOOLCHAIN`, never a
    crash -- toolchain unavailability is an expected, reportable outcome
    for this pipeline, not a programming error.
    """


@dataclass(frozen=True)
class _ReleaseAsset:
    release_name: str  # e.g. "jdk-21.0.11+10"
    download_url: str
    sha256: str
    file_name: str


# --------------------------------------------------------------------------
# Step 1: what does the repo's own pom.xml require?
# --------------------------------------------------------------------------


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _first_property_text(root: ET.Element, name: str) -> str | None:
    """First non-empty text of any element named `name`, ignoring the Maven
    POM namespace -- properties are declared as `<maven.compiler.source>21
    </maven.compiler.source>`, so the tag's *local* name IS the property
    name, wherever in the tree it lives."""
    for elem in root.iter():
        if _local_name(elem.tag) == name and elem.text and elem.text.strip():
            return elem.text.strip()
    return None


def _normalize_major(raw: str | None) -> int | None:
    """ "1.8" -> 8, "8"/"11"/"17"/"21" -> themselves, an unresolved property
    placeholder (`"${java.version}"`) or any other unparsable text -> None
    (treated as "not specified", never crashes)."""
    if raw is None:
        return None
    text = raw.strip()
    if not text or text.startswith("${"):
        return None
    if text.startswith("1.") and len(text) > 2:
        text = text[2:]
    try:
        return int(text)
    except ValueError:
        return None


def required_java_major_version(pom_path: Path) -> int:
    """Parse a Maven `pom.xml` for the JDK major version its build actually
    REQUIRES -- never inspected before RPOC-041, which is exactly why a
    version-mismatch build failure previously had to be pattern-matched out
    of Maven's error text (`_java_toolchain_blocked`) instead of predicted
    up front.

    Priority: `maven.compiler.release` (single source of truth when
    present) > the larger of `maven.compiler.source`/`maven.compiler.target`
    (a build must satisfy both) > `DEFAULT_JAVA_MAJOR_VERSION` when none are
    specified. A missing or unparsable pom.xml also falls back to the
    default rather than raising -- this function never crashes.
    """
    if not pom_path.is_file():
        return DEFAULT_JAVA_MAJOR_VERSION
    try:
        root = ET.parse(pom_path).getroot()
    except ET.ParseError:
        return DEFAULT_JAVA_MAJOR_VERSION

    release = _normalize_major(_first_property_text(root, "maven.compiler.release"))
    if release is not None:
        return release

    source = _normalize_major(_first_property_text(root, "maven.compiler.source"))
    target = _normalize_major(_first_property_text(root, "maven.compiler.target"))
    candidates = [version for version in (source, target) if version is not None]
    if candidates:
        return max(candidates)

    return DEFAULT_JAVA_MAJOR_VERSION


# --------------------------------------------------------------------------
# Step 2: is a matching JDK already usable, and if not, provision one.
# --------------------------------------------------------------------------


def _major_from_release_version(raw: str) -> int | None:
    """Adoptium `release` files record the full semver in `JAVA_VERSION`
    (e.g. `"21.0.11"`, confirmed against this repo's own already-extracted
    `runs/toolchains/temurin-21.0.11+10/jdk-21.0.11+10/release`; or
    old-style `"1.8.0_452"`) -- unlike a pom.xml's single-value
    `maven.compiler.*` properties (`_normalize_major`), this always has
    multiple dot-separated components, so it needs its own parser."""
    text = raw.strip()
    if not text:
        return None
    components = text.replace("_", ".").split(".")
    if not components or not components[0].isdigit():
        return None
    first = int(components[0])
    if first == 1 and len(components) > 1 and components[1].isdigit():
        return int(components[1])
    return first


def _jdk_home_major_version(jdk_home: Path) -> int | None:
    """Read a JDK install's own `release` file (present in every Temurin --
    and effectively every vendor's -- distribution) rather than shelling out
    to `java -version`, so this stays a cheap, side-effect-free file read."""
    release_file = jdk_home / "release"
    if not release_file.is_file():
        return None
    try:
        text = release_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("JAVA_VERSION="):
            raw = line.split("=", 1)[1].strip().strip('"')
            return _major_from_release_version(raw)
    return None


def _configured_jdk_home(major: int) -> Path | None:
    """`README_AGENT_JAVA_HOME`, but ONLY when it already matches `major` --
    RPOC-041 requirement 4: an explicit override that does not match the
    repo's actual requirement must not be silently used (that was the
    original bug); it must fall through to auto-provisioning instead."""
    configured = env.java_home()
    if not configured:
        return None
    home = Path(configured)
    if not home.is_dir():
        return None
    return home if _jdk_home_major_version(home) == major else None


def _cached_jdk_home(major: int) -> Path | None:
    """A JDK this module itself previously downloaded and extracted under
    `runs/toolchains/`, matching `major` -- checked by reading each cached
    install's own `release` file, not by parsing the cache directory name,
    so this stays correct even if a directory was seeded/renamed by hand."""
    cache_root = paths.toolchains_dir()
    if not cache_root.is_dir():
        return None
    for entry in sorted(cache_root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("temurin-"):
            continue
        for release_file in sorted(entry.glob("*/release")):
            jdk_home = release_file.parent
            if _jdk_home_major_version(jdk_home) == major:
                return jdk_home
    return None


def find_existing_jdk_home(major: int) -> Path | None:
    """Already-usable JDK for `major`, or `None` if one must be downloaded.

    Preference order: an explicit, already-matching `README_AGENT_JAVA_HOME`
    override, then anything this module previously downloaded into the
    cache -- both avoid an unnecessary network round-trip.
    """
    return _configured_jdk_home(major) or _cached_jdk_home(major)


def _adoptium_os() -> str:
    system = platform.system()
    try:
        return _ADOPTIUM_OS_NAMES[system]
    except KeyError:
        raise JavaToolchainError(f"unsupported OS for JDK auto-provisioning: {system!r}") from None


def _adoptium_arch() -> str:
    machine = platform.machine()
    try:
        return _ADOPTIUM_ARCH_NAMES[machine]
    except KeyError:
        raise JavaToolchainError(
            f"unsupported CPU architecture for JDK auto-provisioning: {machine!r}"
        ) from None


def _fetch_release_asset(major: int) -> _ReleaseAsset:
    """Query Adoptium's `assets/feature_releases` endpoint (live-confirmed
    2026-07-25 against the real API: filtered by os/architecture/image_type
    it returns exactly one release with one matching binary, whose
    `package.link`/`package.checksum` are the download URL and its
    published sha256 -- the same shape as the `OpenJDK21U-jdk_x64_windows_
    hotspot_21.0.11_10.zip` already sitting in this repo's own
    `runs/toolchains/`)."""
    url = _ADOPTIUM_ASSETS_URL.format(major=major)
    params: dict[str, str] = {
        "os": _adoptium_os(),
        "architecture": _adoptium_arch(),
        "image_type": "jdk",
        "vendor": "eclipse",
        "heap_size": "normal",
        "page_size": "1",
    }
    try:
        response = run_http_with_retry(
            "package_registry",
            lambda: requests.get(url, params=params, timeout=_ADOPTIUM_METADATA_TIMEOUT_SECONDS),
            retryable_statuses=_RETRYABLE_STATUSES,
        )
        response.raise_for_status()
        releases = response.json()
    except (requests.RequestException, RetryableOperationError, ValueError) as exc:
        raise JavaToolchainError(f"Adoptium release lookup failed for JDK {major}: {exc}") from exc

    if not releases or not releases[0].get("binaries"):
        raise JavaToolchainError(
            f"Adoptium has no ga Eclipse Temurin JDK {major} build for "
            f"{params['os']}/{params['architecture']}"
        )
    package = releases[0]["binaries"][0]["package"]
    return _ReleaseAsset(
        release_name=releases[0]["release_name"],
        download_url=package["link"],
        sha256=package["checksum"],
        file_name=package["name"],
    )


def _download_checksum_verified(url: str, expected_sha256: str, destination: Path) -> None:
    try:
        response = requests.get(url, stream=True, timeout=_ADOPTIUM_DOWNLOAD_TIMEOUT_SECONDS)
        response.raise_for_status()
        digest = hashlib.sha256()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK_BYTES):
                if not chunk:
                    continue
                handle.write(chunk)
                digest.update(chunk)
    except requests.RequestException as exc:
        destination.unlink(missing_ok=True)
        raise JavaToolchainError(f"JDK download failed for {url}: {exc}") from exc

    actual_sha256 = digest.hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        destination.unlink(missing_ok=True)
        raise JavaToolchainError(
            f"checksum mismatch downloading {url}: "
            f"expected {expected_sha256}, got {actual_sha256} -- refusing to use it"
        )


def _extract_archive(archive_path: Path, destination_root: Path) -> Path:
    destination_root.mkdir(parents=True, exist_ok=True)
    try:
        if archive_path.name.endswith(".zip"):
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(destination_root)
        else:
            with tarfile.open(archive_path) as archive:
                archive.extractall(destination_root, filter="data")
    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        raise JavaToolchainError(f"failed to extract {archive_path}: {exc}") from exc

    top_level_dirs = [item for item in destination_root.iterdir() if item.is_dir()]
    if len(top_level_dirs) != 1:
        raise JavaToolchainError(
            f"unexpected Temurin archive layout after extracting {archive_path}: "
            f"expected exactly one top-level directory, found "
            f"{sorted(item.name for item in top_level_dirs)}"
        )
    return top_level_dirs[0]


def provision_jdk(major: int) -> Path:
    """Return a usable JDK home directory for `major`.

    Prefers whatever is already available (`find_existing_jdk_home`) --
    an explicitly configured, already-matching `README_AGENT_JAVA_HOME`, or
    a prior download this module cached under `runs/toolchains/` -- and
    only reaches the network when nothing available already matches.
    Raises `JavaToolchainError` on any unrecoverable provisioning failure
    (unsupported platform, no published Adoptium build, network failure,
    checksum mismatch, unexpected archive layout); never raises for a
    bare "nothing configured yet" state -- that is the expected first-run
    case this function exists to handle.
    """
    existing = find_existing_jdk_home(major)
    if existing is not None:
        return existing

    asset = _fetch_release_asset(major)
    cache_root = paths.toolchains_dir()
    cache_root.mkdir(parents=True, exist_ok=True)
    # Matches the layout already present in this repo's own
    # `runs/toolchains/temurin-21.0.11+10/` (hand-provisioned before this
    # taskcard): `jdk-21.0.11+10` -> `temurin-21.0.11+10`.
    destination_root = cache_root / f"temurin-{asset.release_name.removeprefix('jdk-')}"
    if destination_root.is_dir():
        # This exact release was already extracted (e.g. by a concurrent or
        # prior run) -- re-scan instead of re-downloading ~200MB.
        rescanned = _cached_jdk_home(major)
        if rescanned is not None:
            return rescanned

    with tempfile.TemporaryDirectory(prefix="readme-agent-temurin-download-") as temp_dir:
        archive_path = Path(temp_dir) / asset.file_name
        _download_checksum_verified(asset.download_url, asset.sha256, archive_path)
        jdk_home = _extract_archive(archive_path, destination_root)
    return jdk_home
