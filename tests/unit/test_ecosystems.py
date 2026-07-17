import pytest

from readme_agent.ecosystems import maven, registry
from readme_agent.errors import ConfigError
from readme_agent.inspection.file_inventory import FileInventory

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


class TestMavenParser:
    def test_parses_identity_fields(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_text(SIMPLE_POM, encoding="utf-8")

        info = maven.parse_pom(pom)

        assert info["group_id"] == "com.aspose"
        assert info["artifact_id"] == "aspose-3d-foss"
        assert info["version"] == "1.2.3"
        assert info["name"] == "Aspose.3D FOSS for Java"
        assert info["license"] == "MIT License"

    def test_handles_bom(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_bytes(b"\xef\xbb\xbf" + SIMPLE_POM.encode("utf-8"))

        info = maven.parse_pom(pom)

        assert info["group_id"] == "com.aspose"

    def test_known_caveat_parent_block_first_match(self, tmp_path):
        """Documented limitation: a <parent> block's groupId is matched first
        if it appears before the project's own -- not hardened, just recorded."""
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

        info = maven.parse_pom(pom)

        # Documents the caveat rather than hiding it: this asserts the KNOWN
        # wrong behavior, so a future fix is a deliberate, visible change.
        assert info["group_id"] == "com.aspose.parent"
        assert info["version"] == "9.9.9"


class TestEcosystemRegistry:
    def test_maven_dispatch(self, tmp_path):
        pom = tmp_path / "pom.xml"
        pom.write_text(SIMPLE_POM, encoding="utf-8")
        inventory = FileInventory(readme_path=None, license_path=None, pom_path=pom)

        info = registry.parse_manifest("maven", inventory)

        assert info["artifact_id"] == "aspose-3d-foss"

    def test_maven_without_pom_returns_empty(self, tmp_path):
        inventory = FileInventory(readme_path=None, license_path=None, pom_path=None)
        assert registry.parse_manifest("maven", inventory) == {}

    def test_unknown_ecosystem_raises(self):
        inventory = FileInventory(readme_path=None, license_path=None, pom_path=None)
        with pytest.raises(ConfigError):
            registry.parse_manifest("cargo", inventory)
