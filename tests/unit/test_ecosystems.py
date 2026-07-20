import pytest

from readme_agent.ecosystems import cpp, dotnet, go, java, python, registry, typescript
from readme_agent.errors import ConfigError

SIMPLE_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <groupId>com.aspose</groupId>
  <artifactId>aspose-3d-foss</artifactId>
  <version>1.2.3</version>
  <name>Aspose.3D FOSS for Java</name>
  <licenses>
    <license>
      <name>MIT License</name>
    </license>
  </licenses>
</project>
"""


class TestJavaParser:
    def test_parses_identity_fields(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_text(SIMPLE_POM, encoding="utf-8")

        info = java.parse_pom(pom)

        assert info["group_id"] == "com.aspose"
        assert info["artifact_id"] == "aspose-3d-foss"
        assert info["version"] == "1.2.3"
        assert info["name"] == "Aspose.3D FOSS for Java"
        assert info["license"] == "MIT License"

    def test_handles_bom(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_bytes(b"\xef\xbb\xbf" + SIMPLE_POM.encode("utf-8"))

        info = java.parse_pom(pom)

        assert info["group_id"] == "com.aspose"

    def test_known_caveat_parent_block_first_match(self, tmp_path):
        """Documented limitation, matching the actual proven aspose.org
        reference this was adapted from (GOVERNANCE.md rule 8): a <parent>
        block's groupId is matched first if it appears before the project's
        own -- not hardened, just recorded. Not reopened in Wave 3."""
        pom_with_parent = """<project>
          <parent>
            <groupId>com.aspose.parent</groupId>
            <version>9.9.9</version>
          </parent>
          <groupId>com.aspose</groupId>
          <version>1.2.3</version>
        </project>"""
        pom = tmp_path / "pom.xml"
        pom.write_text(pom_with_parent, encoding="utf-8")

        info = java.parse_pom(pom)

        # Documents the caveat rather than hiding it: this asserts the KNOWN
        # wrong behavior, so a future fix is a deliberate, visible change.
        assert info["group_id"] == "com.aspose.parent"
        assert info["version"] == "9.9.9"

    def test_extracts_runtime_min_version_from_compiler_release(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_text(
            SIMPLE_POM.replace(
                "</project>",
                "<properties><maven.compiler.release>21"
                "</maven.compiler.release></properties></project>",
            ),
            encoding="utf-8",
        )

        info = java.parse_pom(pom)

        assert info["runtime_min_version"] == "21"

    def test_parse_gradle_fallback(self, tmp_path):
        gradle = tmp_path / "build.gradle"
        gradle.write_text(
            "group = 'com.aspose'\nversion = '2.0.0'\ntargetCompatibility = '17'\n",
            encoding="utf-8",
        )

        info = java.parse_gradle(gradle)

        assert info["group_id"] == "com.aspose"
        assert info["version"] == "2.0.0"
        assert info["runtime_min_version"] == "17"

    def test_parse_prefers_pom_over_gradle(self, tmp_path):
        (tmp_path / "pom.xml").write_text(SIMPLE_POM, encoding="utf-8")
        (tmp_path / "build.gradle").write_text("group = 'ignored'\n", encoding="utf-8")

        info = java.parse(tmp_path)

        assert info["group_id"] == "com.aspose"  # from pom.xml, not gradle

    def test_parse_falls_back_to_gradle_when_no_pom(self, tmp_path):
        (tmp_path / "build.gradle").write_text(
            "group = 'com.aspose'\nversion = '3.0.0'\n", encoding="utf-8"
        )

        info = java.parse(tmp_path)

        assert info["group_id"] == "com.aspose"
        assert info["version"] == "3.0.0"

    def test_parse_no_manifest_returns_empty(self, tmp_path):
        assert java.parse(tmp_path) == {}


class TestPythonParser:
    def test_parses_pyproject_project_table(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-3d-foss"\nversion = "1.0.0"\n'
            'license = { text = "MIT" }\nrequires-python = ">=3.11"\n',
            encoding="utf-8",
        )

        info = python.parse(tmp_path)

        assert info["name"] == "aspose-3d-foss"
        assert info["version"] == "1.0.0"
        assert info["license"] == "MIT"
        assert info["requires_python"] == ">=3.11"

    def test_extracts_canonical_package_from_namespace_include(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-email-foss"\n'
            "[tool.setuptools.packages.find]\n"
            'include = ["aspose.email_foss", "aspose.email_foss.*"]\n',
            encoding="utf-8",
        )

        info = python.parse(tmp_path)

        assert info["canonical_package"] == "aspose.email_foss"

    def test_extracts_canonical_package_from_flat_packages_list(self, tmp_path):
        """Real crash, found by the full-registry survey (2026-07-19):
        aspose-cells-foss/Aspose.Cells-FOSS-for-Python uses the flatter
        [tool.setuptools] packages = [...] shape, not the nested
        packages.find.include the ported code originally assumed only --
        `.get("find", {})` on a list raised AttributeError."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "aspose-cells-foss"\n'
            "[tool.setuptools]\n"
            'packages = ["aspose", "aspose.cells_foss", "examples"]\n',
            encoding="utf-8",
        )

        info = python.parse(tmp_path)

        assert info["canonical_package"] == "aspose.cells_foss"

    def test_falls_back_to_setup_py_when_no_pyproject_name(self, tmp_path):
        (tmp_path / "setup.py").write_text(
            'setup(name="aspose-3d-foss", version="1.2.3")\n', encoding="utf-8"
        )

        info = python.parse(tmp_path)

        assert info["name"] == "aspose-3d-foss"
        assert info["version"] == "1.2.3"

    def test_no_manifest_returns_empty(self, tmp_path):
        assert python.parse(tmp_path) == {}


class TestDotnetParser:
    def test_parses_single_target_framework(self, tmp_path):
        (tmp_path / "widget.csproj").write_text(
            "<Project><PropertyGroup><PackageId>Aspose.3D</PackageId>"
            "<Version>1.0.0</Version><TargetFramework>net6.0</TargetFramework>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )

        info = dotnet.parse(tmp_path)

        assert info["name"] == "Aspose.3D"
        assert info["version"] == "1.0.0"
        assert info["target_framework"] == "net6.0"
        assert info["min_framework"] == "net6.0"

    def test_multi_target_ranks_netstandard_below_net(self, tmp_path):
        (tmp_path / "widget.csproj").write_text(
            "<Project><PropertyGroup>"
            "<TargetFrameworks>net8.0;netstandard2.0</TargetFrameworks>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )

        info = dotnet.parse(tmp_path)

        assert info["min_framework"] == "netstandard2.0"

    def test_picks_shallowest_of_multiple_csproj(self, tmp_path):
        (tmp_path / "root.csproj").write_text(
            "<Project><PropertyGroup><PackageId>Root</PackageId></PropertyGroup></Project>",
            encoding="utf-8",
        )
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "deep.csproj").write_text(
            "<Project><PropertyGroup><PackageId>Deep</PackageId></PropertyGroup></Project>",
            encoding="utf-8",
        )

        info = dotnet.parse(tmp_path)

        assert info["name"] == "Root"

    def test_no_csproj_returns_empty(self, tmp_path):
        assert dotnet.parse(tmp_path) == {}


class TestTypescriptParser:
    def test_parses_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"name": "@aspose/cells", "version": "1.0.0", "license": "MIT", '
            '"engines": {"node": ">=18"}}',
            encoding="utf-8",
        )

        info = typescript.parse(tmp_path)

        assert info["name"] == "@aspose/cells"
        assert info["version"] == "1.0.0"
        assert info["license"] == "MIT"
        assert info["engines_node"] == ">=18"

    def test_malformed_json_returns_empty_not_raises(self, tmp_path):
        (tmp_path / "package.json").write_text("{not valid json", encoding="utf-8")

        assert typescript.parse(tmp_path) == {}

    def test_no_package_json_returns_empty(self, tmp_path):
        assert typescript.parse(tmp_path) == {}


class TestGoParser:
    def test_parses_module_and_go_version(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module github.com/aspose/pdf-foss-go\n\ngo 1.21\n", encoding="utf-8"
        )

        info = go.parse(tmp_path)

        assert info["name"] == "github.com/aspose/pdf-foss-go"
        assert info["go_version"] == "1.21"
        assert info["runtime_min_version"] == "Go 1.21+"

    def test_extracts_package_name_from_source_excluding_main_and_tests(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/widget\n\ngo 1.21\n", encoding="utf-8")
        (tmp_path / "main.go").write_text("package main\n", encoding="utf-8")
        (tmp_path / "widget_test.go").write_text("package widget_test\n", encoding="utf-8")
        (tmp_path / "widget.go").write_text("package widget\n", encoding="utf-8")

        info = go.parse(tmp_path)

        assert info["package_name"] == "widget"

    def test_no_go_mod_returns_empty(self, tmp_path):
        assert go.parse(tmp_path) == {}


class TestCppParser:
    def test_parses_project_name_version_and_standard(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.20)\n"
            "project(AsposeWidget VERSION 1.2.3)\n"
            "add_library(aspose_widget src/widget.cpp)\n"
            "set(CMAKE_CXX_STANDARD 17)\n",
            encoding="utf-8",
        )

        info = cpp.parse(tmp_path)

        assert info["name"] == "AsposeWidget"
        assert info["version"] == "1.2.3"
        assert info["cmake_min_version"] == "3.20"
        assert info["library_target"] == "aspose_widget"

    def test_no_cmakelists_returns_empty(self, tmp_path):
        assert cpp.parse(tmp_path) == {}


class TestEcosystemRegistry:
    def test_java_dispatch(self, tmp_path):
        (tmp_path / "pom.xml").write_text(SIMPLE_POM, encoding="utf-8")

        info = registry.parse_manifest("java", tmp_path)

        assert info["artifact_id"] == "aspose-3d-foss"

    def test_java_without_manifest_returns_empty(self, tmp_path):
        assert registry.parse_manifest("java", tmp_path) == {}

    def test_unknown_ecosystem_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            registry.parse_manifest("cargo", tmp_path)

    def test_known_manifest_globs_covers_all_registered_platforms(self):
        globs = registry.known_manifest_globs()
        assert set(globs) == {"java", "python", "net", "typescript", "go", "cpp"}
