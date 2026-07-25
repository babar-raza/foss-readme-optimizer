"""RPOC-041: pom.xml-driven required-JDK-version detection and
auto-provisioning. Every test here is offline -- `runs/` is redirected via
`README_AGENT_RUNS_DIR` (same convention as `test_registry_self_heal.py`),
and every network call is monkeypatched at `java_toolchain.requests.get`,
never a real Adoptium round-trip. See
`plans/investigations/` (root cause) and `facts/local_verification.py`
(`_verify_java`, the wiring this replaces)."""

import hashlib
import io
import tarfile
import zipfile

import pytest

from readme_agent.facts import java_toolchain as jt

_POM_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
    "    <modelVersion>4.0.0</modelVersion>\n"
    "    <groupId>org.example</groupId>\n"
    "    <artifactId>example</artifactId>\n"
    "    <version>1.0.0</version>\n"
)
_POM_FOOTER = "</project>\n"


def _pom(tmp_path, properties_xml: str):
    pom_path = tmp_path / "pom.xml"
    pom_path.write_text(_POM_HEADER + properties_xml + _POM_FOOTER, encoding="utf-8")
    return pom_path


def _write_release_file(jdk_home, java_version: str) -> None:
    jdk_home.mkdir(parents=True, exist_ok=True)
    (jdk_home / "release").write_text(f'JAVA_VERSION="{java_version}"\n', encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolated_runs_dir(tmp_path, monkeypatch):
    """Same convention as `test_registry_self_heal.py`: redirect
    `runs/toolchains/` into `tmp_path` so no test touches the real repo's
    cache, and clear any ambient override so each test starts from a known
    "nothing configured" state."""
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.delenv("README_AGENT_JAVA_HOME", raising=False)
    return tmp_path / "runs"


class TestRequiredJavaMajorVersion:
    """Fixture pom.xml shapes only -- no live network calls."""

    def test_release_only(self, tmp_path):
        pom = _pom(
            tmp_path,
            "<properties><maven.compiler.release>21</maven.compiler.release></properties>",
        )
        assert jt.required_java_major_version(pom) == 21

    def test_source_and_target_only(self, tmp_path):
        # Mirrors aspose-cells-foss's real pom.xml shape (JDK 17).
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.source>17</maven.compiler.source>"
            "<maven.compiler.target>17</maven.compiler.target>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == 17

    def test_aspose_3d_foss_shape_resolves_to_21(self, tmp_path):
        # Mirrors aspose-3d-foss's real pom.xml shape (JDK 21).
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.source>21</maven.compiler.source>"
            "<maven.compiler.target>21</maven.compiler.target>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == 21

    def test_aspose_pdf_foss_shape_resolves_to_11(self, tmp_path):
        # Mirrors aspose-pdf-foss's real pom.xml shape (JDK 11).
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.source>11</maven.compiler.source>"
            "<maven.compiler.target>11</maven.compiler.target>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == 11

    def test_release_takes_priority_over_source_and_target(self, tmp_path):
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.release>21</maven.compiler.release>"
            "<maven.compiler.source>11</maven.compiler.source>"
            "<maven.compiler.target>11</maven.compiler.target>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == 21

    def test_mismatched_source_and_target_uses_the_larger(self, tmp_path):
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.source>11</maven.compiler.source>"
            "<maven.compiler.target>17</maven.compiler.target>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == 17

    def test_old_style_1_dot_8_normalizes_to_8(self, tmp_path):
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.source>1.8</maven.compiler.source>"
            "<maven.compiler.target>1.8</maven.compiler.target>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == 8

    def test_missing_entirely_falls_back_to_default(self, tmp_path):
        pom = _pom(tmp_path, "<properties></properties>")
        assert jt.required_java_major_version(pom) == jt.DEFAULT_JAVA_MAJOR_VERSION

    def test_missing_file_falls_back_to_default_without_crashing(self, tmp_path):
        missing = tmp_path / "does-not-exist" / "pom.xml"
        assert jt.required_java_major_version(missing) == jt.DEFAULT_JAVA_MAJOR_VERSION

    def test_malformed_xml_falls_back_to_default_without_crashing(self, tmp_path):
        pom_path = tmp_path / "pom.xml"
        pom_path.write_text("<project><unterminated>", encoding="utf-8")
        assert jt.required_java_major_version(pom_path) == jt.DEFAULT_JAVA_MAJOR_VERSION

    def test_unresolved_property_placeholder_falls_back_to_default(self, tmp_path):
        pom = _pom(
            tmp_path,
            "<properties>"
            "<maven.compiler.release>${java.version}</maven.compiler.release>"
            "</properties>",
        )
        assert jt.required_java_major_version(pom) == jt.DEFAULT_JAVA_MAJOR_VERSION


class TestFindExistingJdkHome:
    def test_configured_java_home_used_when_it_matches(self, tmp_path, monkeypatch):
        jdk_dir = tmp_path / "custom-jdk-21"
        _write_release_file(jdk_dir, "21.0.5")
        monkeypatch.setenv("README_AGENT_JAVA_HOME", str(jdk_dir))
        assert jt.find_existing_jdk_home(21) == jdk_dir

    def test_configured_java_home_ignored_when_version_does_not_match(self, tmp_path, monkeypatch):
        jdk_dir = tmp_path / "custom-jdk-11"
        _write_release_file(jdk_dir, "11.0.5")
        monkeypatch.setenv("README_AGENT_JAVA_HOME", str(jdk_dir))
        assert jt.find_existing_jdk_home(21) is None

    def test_configured_java_home_pointing_nowhere_is_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("README_AGENT_JAVA_HOME", str(tmp_path / "does-not-exist"))
        assert jt.find_existing_jdk_home(21) is None

    def test_cached_jdk_is_found_without_a_configured_override(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        cached_home = runs_dir / "toolchains" / "temurin-17.0.9+9" / "jdk-17.0.9+9"
        _write_release_file(cached_home, "17.0.9")
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))
        assert jt.find_existing_jdk_home(17) == cached_home

    def test_nothing_available_returns_none(self):
        assert jt.find_existing_jdk_home(21) is None


class _FakeResponse:
    def __init__(self, *, json_data=None, content: bytes = b"", status_code: int = 200):
        self._json_data = json_data
        self._content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise jt.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data

    def iter_content(self, chunk_size):
        yield self._content


def _java_version_from_release_name(release_name: str) -> str:
    """ "jdk-99.0.1+1" -> "99.0.1" -- real Temurin `release` files carry the
    bare semver in `JAVA_VERSION` (no `+build` suffix); confirmed against
    this repo's own already-extracted `runs/toolchains/temurin-21.0.11+10/
    jdk-21.0.11+10/release` (`JAVA_VERSION="21.0.11"`)."""
    return release_name.removeprefix("jdk-").split("+", 1)[0]


def _fake_temurin_zip(release_name: str) -> bytes:
    buffer = io.BytesIO()
    java_version = _java_version_from_release_name(release_name)
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"{release_name}/release", f'JAVA_VERSION="{java_version}"\n')
        archive.writestr(f"{release_name}/bin/javac.exe", "fake javac")
    return buffer.getvalue()


def _fake_temurin_tar_gz(release_name: str) -> bytes:
    buffer = io.BytesIO()
    java_version = _java_version_from_release_name(release_name)
    release_content = f'JAVA_VERSION="{java_version}"\n'.encode()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo(name=f"{release_name}/release")
        info.size = len(release_content)
        archive.addfile(info, io.BytesIO(release_content))
    return buffer.getvalue()


def _install_fake_adoptium(monkeypatch, *, release_name: str, archive_bytes: bytes, file_name: str):
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    metadata_response = _FakeResponse(
        json_data=[
            {
                "release_name": release_name,
                "binaries": [
                    {
                        "package": {
                            "link": f"https://example.invalid/{file_name}",
                            "checksum": checksum,
                            "name": file_name,
                        }
                    }
                ],
            }
        ]
    )
    download_response = _FakeResponse(content=archive_bytes)
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return download_response if kwargs.get("stream") else metadata_response

    monkeypatch.setattr(jt.requests, "get", fake_get)
    return calls, checksum


class TestProvisionJdk:
    def test_prefers_a_matching_cached_jdk_over_the_network(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        cached_home = runs_dir / "toolchains" / "temurin-17.0.9+9" / "jdk-17.0.9+9"
        _write_release_file(cached_home, "17.0.9")
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))

        def fail_if_called(*args, **kwargs):
            raise AssertionError("must not call the network when a cached JDK already matches")

        monkeypatch.setattr(jt.requests, "get", fail_if_called)

        assert jt.provision_jdk(17) == cached_home

    def test_downloads_verifies_checksum_and_extracts_a_zip(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))
        monkeypatch.setattr(jt.platform, "system", lambda: "Windows")
        monkeypatch.setattr(jt.platform, "machine", lambda: "AMD64")
        archive_bytes = _fake_temurin_zip("jdk-99.0.1+1")
        calls, _ = _install_fake_adoptium(
            monkeypatch,
            release_name="jdk-99.0.1+1",
            archive_bytes=archive_bytes,
            file_name="OpenJDK99U-jdk_x64_windows_hotspot_99.0.1_1.zip",
        )

        jdk_home = jt.provision_jdk(99)

        assert jdk_home == runs_dir / "toolchains" / "temurin-99.0.1+1" / "jdk-99.0.1+1"
        assert (jdk_home / "release").is_file()
        assert len(calls) == 2  # one metadata GET, one streamed download GET

        # RPOC-041 requirement 3: a second call for the same version must be
        # a pure cache hit -- no further network calls at all.
        calls.clear()
        assert jt.provision_jdk(99) == jdk_home
        assert calls == []

    def test_downloads_and_extracts_a_tar_gz_on_linux(self, tmp_path, monkeypatch):
        """Requirement 5: usable from CI (linux runners) without change --
        exercises the non-Windows/non-zip extraction branch."""
        runs_dir = tmp_path / "runs"
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))
        monkeypatch.setattr(jt.platform, "system", lambda: "Linux")
        monkeypatch.setattr(jt.platform, "machine", lambda: "x86_64")
        archive_bytes = _fake_temurin_tar_gz("jdk-97.0.1+1")
        _install_fake_adoptium(
            monkeypatch,
            release_name="jdk-97.0.1+1",
            archive_bytes=archive_bytes,
            file_name="OpenJDK97U-jdk_x64_linux_hotspot_97.0.1_1.tar.gz",
        )

        jdk_home = jt.provision_jdk(97)

        assert jdk_home == runs_dir / "toolchains" / "temurin-97.0.1+1" / "jdk-97.0.1+1"
        assert (jdk_home / "release").is_file()

    def test_checksum_mismatch_is_refused(self, tmp_path, monkeypatch):
        runs_dir = tmp_path / "runs"
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))
        monkeypatch.setattr(jt.platform, "system", lambda: "Windows")
        monkeypatch.setattr(jt.platform, "machine", lambda: "AMD64")
        archive_bytes = _fake_temurin_zip("jdk-98.0.1+1")
        metadata_response = _FakeResponse(
            json_data=[
                {
                    "release_name": "jdk-98.0.1+1",
                    "binaries": [
                        {
                            "package": {
                                "link": "https://example.invalid/x.zip",
                                "checksum": "0" * 64,  # deliberately wrong
                                "name": "x.zip",
                            }
                        }
                    ],
                }
            ]
        )
        download_response = _FakeResponse(content=archive_bytes)

        def fake_get(url, **kwargs):
            return download_response if kwargs.get("stream") else metadata_response

        monkeypatch.setattr(jt.requests, "get", fake_get)

        with pytest.raises(jt.JavaToolchainError, match="checksum mismatch"):
            jt.provision_jdk(98)

        # A rejected download must not be left behind for a future run to
        # mistake for a verified cache hit.
        assert jt.find_existing_jdk_home(98) is None

    def test_unsupported_os_fails_closed_without_a_network_call(self, tmp_path, monkeypatch):
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
        monkeypatch.setattr(jt.platform, "system", lambda: "PlanNine")

        def fail_if_called(*args, **kwargs):
            raise AssertionError("must not call the network for an unsupported OS")

        monkeypatch.setattr(jt.requests, "get", fail_if_called)

        with pytest.raises(jt.JavaToolchainError, match="unsupported OS"):
            jt.provision_jdk(21)

    def test_network_error_is_wrapped_as_java_toolchain_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
        monkeypatch.setattr(jt.platform, "system", lambda: "Windows")
        monkeypatch.setattr(jt.platform, "machine", lambda: "AMD64")

        def raise_connection_error(*args, **kwargs):
            raise jt.requests.ConnectionError("dns failure")

        monkeypatch.setattr(jt.requests, "get", raise_connection_error)

        with pytest.raises(jt.JavaToolchainError):
            jt.provision_jdk(21)

    def test_no_published_build_for_version_is_reported_not_crashed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
        monkeypatch.setattr(jt.platform, "system", lambda: "Windows")
        monkeypatch.setattr(jt.platform, "machine", lambda: "AMD64")
        monkeypatch.setattr(jt.requests, "get", lambda *a, **k: _FakeResponse(json_data=[]))

        with pytest.raises(jt.JavaToolchainError, match="no ga Eclipse Temurin"):
            jt.provision_jdk(5)
