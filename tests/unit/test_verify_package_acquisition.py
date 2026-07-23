"""`PKG-005` (Wave 11.2): per-package-root acquisition verification --
unlike `check_install_path.py`'s single boolean, one outcome per detected
`PackageRoot`. All network/filesystem boundaries (`clone_baseline`,
`build_profile`, `parse_manifest`, `resolve`) are monkeypatched -- no real
network or clone in this file."""

from types import SimpleNamespace

from readme_agent.capabilities import verify_package_acquisition as vpa
from readme_agent.ecosystems.resolver import ResolutionResult
from readme_agent.profile.schema import PackageRoot, RepositoryProfile


def _fake_entry():
    return SimpleNamespace(org="acme", repo_name="widget", org_repo="acme/widget", mode="full")


def _stub_common(monkeypatch, tmp_path, package_roots):
    monkeypatch.setattr(vpa, "require_listed", lambda org_repo: _fake_entry())
    monkeypatch.setattr(vpa.paths, "baseline_dir", lambda org, repo: tmp_path)
    monkeypatch.setattr(vpa, "clone_baseline", lambda entry, path: None)
    monkeypatch.setattr(
        vpa,
        "build_profile",
        lambda org_repo, path: RepositoryProfile(org_repo=org_repo, package_roots=package_roots),
    )


class TestManifest:
    def test_is_read_only_network_unscoped(self):
        assert vpa.MANIFEST.side_effect_class == "read_only_network"
        assert vpa.MANIFEST.required_permissions == ["read_only_local", "read_only_network"]
        assert vpa.MANIFEST.allowed_domains == []


class TestExecuteNoPackageRoots:
    def test_reports_not_applicable(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [])

        result = vpa.execute("acme/widget")

        assert result["org_repo"] == "acme/widget"
        assert len(result["results"]) == 1
        assert result["results"][0]["outcome"] == "NOT_APPLICABLE"


class TestExecuteSingleRoot:
    def _java_root(self, path="."):
        return PackageRoot(
            path=path,
            ecosystem="java",
            manifest_path=f"{path}/pom.xml",
            confidence=1.0,
            evidence="found pom.xml",
        )

    def test_registry_verified(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        monkeypatch.setattr(vpa, "parse_manifest", lambda eco, path: {"group_id": "org.acme"})
        monkeypatch.setattr(
            vpa, "resolve", lambda eco, manifest: ResolutionResult(True, "Maven Central: found")
        )

        result = vpa.execute("acme/widget")

        assert result["results"] == [
            {
                "path": ".",
                "ecosystem": "java",
                "outcome": "REGISTRY_VERIFIED",
                "detail": "Maven Central: found",
            }
        ]

    def test_not_published(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        monkeypatch.setattr(vpa, "parse_manifest", lambda eco, path: {"group_id": "org.acme"})
        monkeypatch.setattr(
            vpa,
            "resolve",
            lambda eco, manifest: ResolutionResult(False, "Maven Central: NOT FOUND (0 results)"),
        )

        result = vpa.execute("acme/widget")

        assert result["results"][0]["outcome"] == "NOT_PUBLISHED"

    def test_blocked_network(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        monkeypatch.setattr(vpa, "parse_manifest", lambda eco, path: {"group_id": "org.acme"})
        monkeypatch.setattr(
            vpa,
            "resolve",
            lambda eco, manifest: ResolutionResult(
                False, "network error resolving Maven Central: timeout", blocked=True
            ),
        )

        result = vpa.execute("acme/widget")

        assert result["results"][0]["outcome"] == "BLOCKED_NETWORK"

    def test_missing_manifest_fields_maps_to_capability_gap(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        monkeypatch.setattr(vpa, "parse_manifest", lambda eco, path: {})
        monkeypatch.setattr(
            vpa,
            "resolve",
            lambda eco, manifest: ResolutionResult(
                False, "manifest missing group_id/artifact_id -- cannot resolve"
            ),
        )

        result = vpa.execute("acme/widget")

        assert result["results"][0]["outcome"] == "CAPABILITY_GAP"

    def test_cpp_root_is_capability_gap_without_calling_resolve(self, monkeypatch, tmp_path):
        """`cpp` has no unambiguous resolver (Conan vs vcpkg) -- must never
        guess, and must never even attempt a network call."""
        cpp_root = PackageRoot(
            path=".",
            ecosystem="cpp",
            manifest_path="CMakeLists.txt",
            confidence=1.0,
            evidence="found CMakeLists.txt",
        )
        _stub_common(monkeypatch, tmp_path, [cpp_root])

        def fail_if_called(*a, **k):
            raise AssertionError("must not call resolve() for an ambiguous ecosystem")

        monkeypatch.setattr(vpa, "resolve", fail_if_called)

        result = vpa.execute("acme/widget")

        assert result["results"][0]["outcome"] == "CAPABILITY_GAP"
        assert "cpp" in result["results"][0]["detail"]


class TestExecuteMultiRoot:
    def test_one_outcome_per_root(self, monkeypatch, tmp_path):
        roots = [
            PackageRoot(
                path="src/Widget.Core",
                ecosystem="net",
                manifest_path="src/Widget.Core/Widget.Core.csproj",
                confidence=1.0,
                evidence="found Widget.Core.csproj",
            ),
            PackageRoot(
                path="src/Widget.Cli",
                ecosystem="net",
                manifest_path="src/Widget.Cli/Widget.Cli.csproj",
                confidence=1.0,
                evidence="found Widget.Cli.csproj",
            ),
        ]
        _stub_common(monkeypatch, tmp_path, roots)
        monkeypatch.setattr(vpa, "parse_manifest", lambda eco, path: {"name": str(path)})

        def fake_resolve(eco, manifest):
            found = "Core" in manifest["name"]
            return ResolutionResult(found, "found" if found else "NOT FOUND")

        monkeypatch.setattr(vpa, "resolve", fake_resolve)

        result = vpa.execute("acme/widget")

        outcomes = {r["path"]: r["outcome"] for r in result["results"]}
        assert outcomes == {
            "src/Widget.Core": "REGISTRY_VERIFIED",
            "src/Widget.Cli": "NOT_PUBLISHED",
        }
