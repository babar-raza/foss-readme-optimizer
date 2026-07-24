"""Focused tests for the canonical "aspose {family} foss" coordinate rule."""

from readme_agent.ecosystems.foss_coordinate import canonical_foss_coordinate


class TestCanonicalFossCoordinate:
    def test_java_maven(self):
        eco, coord = canonical_foss_coordinate("cells", "java")
        assert eco == "java"
        assert coord == {"group_id": "org.aspose", "artifact_id": "aspose-cells-foss"}

    def test_python_pypi(self):
        eco, coord = canonical_foss_coordinate("cells", "python")
        assert eco == "python"
        assert coord == {"name": "aspose-cells-foss"}

    def test_net_nuget(self):
        eco, coord = canonical_foss_coordinate("cells", "net")
        assert eco == "net"
        assert coord == {"name": "Aspose.cells.FOSS"}

    def test_cpp_resolves_via_nuget_not_conan_or_vcpkg(self):
        """C++ FOSS ships on NuGet -- resolver_ecosystem is 'net', not 'cpp_conan'/'cpp_vcpkg'."""
        eco, coord = canonical_foss_coordinate("cells", "cpp")
        assert eco == "net"
        assert coord == {"name": "Aspose.cells.Cpp.FOSS"}

    def test_typescript_npm(self):
        eco, coord = canonical_foss_coordinate("cells", "typescript")
        assert eco == "typescript"
        assert coord == {"name": "aspose-cells-foss"}

    def test_go_proxy_uses_org_and_lowercased_repo(self):
        eco, coord = canonical_foss_coordinate(
            "pdf", "go", org="aspose-pdf-foss", repo="Aspose-PDF-FOSS-for-Go"
        )
        assert eco == "go"
        assert coord == {"name": "github.com/aspose-pdf-foss/aspose-pdf-foss-for-go"}

    def test_go_without_org_or_repo_has_no_coordinate(self):
        eco, coord = canonical_foss_coordinate("pdf", "go")
        assert eco is None
        assert coord == {}

    def test_rust_crates_io(self):
        eco, coord = canonical_foss_coordinate("cells", "rust")
        assert eco == "rust"
        assert coord == {"name": "aspose-cells-foss"}

    def test_unsupported_ecosystem_has_no_coordinate(self):
        eco, coord = canonical_foss_coordinate("cells", "ruby")
        assert eco is None
        assert coord == {}

    def test_family_case_is_normalized(self):
        eco, coord = canonical_foss_coordinate("Cells", "java")
        assert coord == {"group_id": "org.aspose", "artifact_id": "aspose-cells-foss"}
