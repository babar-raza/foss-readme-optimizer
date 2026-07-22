"""inspection/tree_paths.py -- the git-tree-API-based counterpart to
file_inventory.py's os.walk()-based manifest detection (decision #40/Part
F, SCL-004). No network: operates on a plain list of tree-entry dicts,
matching get_tree()'s own response["tree"] shape."""

from readme_agent.inspection.tree_paths import find_manifest_paths_from_tree


def _blob(path: str) -> dict:
    return {"path": path, "type": "blob", "sha": "deadbeef", "size": 1}


def _tree(path: str) -> dict:
    return {"path": path, "type": "tree", "sha": "deadbeef"}


class TestFindManifestPathsFromTree:
    def test_finds_root_pom_as_java(self):
        entries = [_blob("pom.xml"), _blob("README.md")]

        found = find_manifest_paths_from_tree(entries)

        assert found["java"] == "pom.xml"

    def test_finds_nested_csproj(self):
        """Same real-world layout _find_manifest_paths() had to be hardened
        for -- a manifest under a subdirectory, not the repo root."""
        entries = [_tree("src"), _tree("src/Widget"), _blob("src/Widget/Widget.csproj")]

        found = find_manifest_paths_from_tree(entries)

        assert found["net"] == "src/Widget/Widget.csproj"

    def test_skips_noise_directories(self):
        entries = [
            _tree("node_modules"),
            _tree("node_modules/some-dep"),
            _blob("node_modules/some-dep/package.json"),
        ]

        found = find_manifest_paths_from_tree(entries)

        assert "typescript" not in found

    def test_tree_entries_are_never_candidates_themselves(self):
        """A directory literally named like a manifest pattern (unusual, but
        not impossible) must never be matched -- only `type: "blob"` entries
        are eligible."""
        entries = [_tree("pom.xml")]

        found = find_manifest_paths_from_tree(entries)

        assert "java" not in found

    def test_multi_ecosystem_fixture(self):
        entries = [_blob("pom.xml"), _blob("pyproject.toml")]

        found = find_manifest_paths_from_tree(entries)

        assert found["java"] == "pom.xml"
        assert found["python"] == "pyproject.toml"
        assert len(found) == 2

    def test_empty_tree_finds_nothing(self):
        assert find_manifest_paths_from_tree([]) == {}
