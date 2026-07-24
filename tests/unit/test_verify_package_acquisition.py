"""`PKG-005`: per-package-root acquisition verification -- one outcome per detected
`PackageRoot`, resolving the canonical "aspose {family} foss" coordinate against the
authoritative registry (never the manifest's self-declared name). All network/clone
boundaries are monkeypatched -- no real network or clone in this file."""

from types import SimpleNamespace

from readme_agent.capabilities import verify_package_acquisition as vpa
from readme_agent.ecosystems.resolver import ResolutionResult
from readme_agent.profile.schema import PackageRoot, RepositoryProfile


def _fake_entry(family="cells", ecosystem="java"):
    return SimpleNamespace(
        org="aspose-cells-foss",
        repo_name="Aspose.Cells-FOSS-for-Java",
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        mode="full",
        family=family,
        ecosystem=ecosystem,
    )


def _stub_common(monkeypatch, tmp_path, package_roots, entry=None):
    entry = entry or _fake_entry()
    monkeypatch.setattr(vpa, "require_listed", lambda org_repo: entry)
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

    def test_registry_verified_resolves_canonical_coordinate(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        captured = []

        def fake_resolve(eco, manifest):
            captured.append((eco, manifest))
            return ResolutionResult(True, "Maven Central: org.aspose:aspose-cells-foss found")

        monkeypatch.setattr(vpa, "resolve", fake_resolve)
        result = vpa.execute("acme/widget")
        assert result["results"][0]["outcome"] == "REGISTRY_VERIFIED"
        # Resolved the canonical FOSS coordinate, NOT any manifest-declared name.
        assert captured[0] == (
            "java",
            {"group_id": "org.aspose", "artifact_id": "aspose-cells-foss"},
        )

    def test_not_published(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        monkeypatch.setattr(
            vpa,
            "resolve",
            lambda eco, m: ResolutionResult(False, "Maven Central: NOT FOUND (404)"),
        )
        result = vpa.execute("acme/widget")
        assert result["results"][0]["outcome"] == "NOT_PUBLISHED"

    def test_blocked_network(self, monkeypatch, tmp_path):
        _stub_common(monkeypatch, tmp_path, [self._java_root()])
        monkeypatch.setattr(
            vpa,
            "resolve",
            lambda eco, m: ResolutionResult(False, "network error: timeout", blocked=True),
        )
        result = vpa.execute("acme/widget")
        assert result["results"][0]["outcome"] == "BLOCKED_NETWORK"

    def test_cpp_resolves_via_nuget(self, monkeypatch, tmp_path):
        """C++ FOSS ships on NuGet -- it resolves via the NuGet (net) resolver with the
        Aspose.{Family}.Cpp.FOSS coordinate, no longer a CAPABILITY_GAP."""
        cpp_root = PackageRoot(
            path=".",
            ecosystem="cpp",
            manifest_path="CMakeLists.txt",
            confidence=1.0,
            evidence="found CMakeLists.txt",
        )
        _stub_common(monkeypatch, tmp_path, [cpp_root], entry=_fake_entry("cells", "cpp"))
        captured = []

        def fake_resolve(eco, manifest):
            captured.append((eco, manifest))
            return ResolutionResult(True, "NuGet: Aspose.cells.Cpp.FOSS found")

        monkeypatch.setattr(vpa, "resolve", fake_resolve)
        result = vpa.execute("acme/widget")
        assert result["results"][0]["outcome"] == "REGISTRY_VERIFIED"
        assert captured[0] == ("net", {"name": "Aspose.cells.Cpp.FOSS"})

    def test_unsupported_ecosystem_is_capability_gap_without_network(self, monkeypatch, tmp_path):
        rust_root = PackageRoot(
            path=".",
            ecosystem="rust",
            manifest_path="Cargo.toml",
            confidence=1.0,
            evidence="found Cargo.toml",
        )
        _stub_common(monkeypatch, tmp_path, [rust_root], entry=_fake_entry("cells", "rust"))

        def fail_if_called(*a, **k):
            raise AssertionError("must not resolve an ecosystem with no canonical FOSS coordinate")

        monkeypatch.setattr(vpa, "resolve", fail_if_called)
        result = vpa.execute("acme/widget")
        assert result["results"][0]["outcome"] == "CAPABILITY_GAP"


class TestExecuteMultiRoot:
    def test_one_outcome_per_root(self, monkeypatch, tmp_path):
        roots = [
            PackageRoot(
                path=".",
                ecosystem="java",
                manifest_path="pom.xml",
                confidence=1.0,
                evidence="found pom.xml",
            ),
            PackageRoot(
                path="dotnet",
                ecosystem="net",
                manifest_path="dotnet/x.csproj",
                confidence=1.0,
                evidence="found x.csproj",
            ),
        ]
        _stub_common(monkeypatch, tmp_path, roots)
        # Different ecosystems -> different canonical coordinates -> independent outcomes.
        monkeypatch.setattr(
            vpa,
            "resolve",
            lambda eco, m: ResolutionResult(
                eco == "java", "found" if eco == "java" else "NOT FOUND"
            ),
        )
        result = vpa.execute("acme/widget")
        outcomes = {r["path"]: r["outcome"] for r in result["results"]}
        assert outcomes == {".": "REGISTRY_VERIFIED", "dotnet": "NOT_PUBLISHED"}
