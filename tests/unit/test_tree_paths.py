"""inspection/tree_paths.py -- the git-tree-API-based counterpart to
file_inventory.py's os.walk()-based manifest detection (decision #40/Part
F, SCL-004). No network: operates on a plain list of tree-entry dicts,
matching get_tree()'s own response["tree"] shape."""

from readme_agent.inspection.tree_paths import (
    find_all_manifest_roots_from_tree,
    find_manifest_paths_from_tree,
)


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


class TestFindAllManifestRootsFromTree:
    """Wave 11.1 (`ECO-004`): the tree-API counterpart to
    `find_manifest_paths_from_tree()`'s own "first match per ecosystem"
    limitation -- every manifest across the whole tree, not just one."""

    def test_single_root_returns_exactly_one_entry(self):
        entries = [_blob("pom.xml")]
        assert find_all_manifest_roots_from_tree(entries) == [("java", "pom.xml")]

    def test_multiple_csproj_files_all_returned(self):
        entries = [
            _blob("src/Widget.Core/Widget.Core.csproj"),
            _blob("src/Widget.Cli/Widget.Cli.csproj"),
        ]

        found = find_all_manifest_roots_from_tree(entries)

        paths = {path for _, path in found}
        assert paths == {"src/Widget.Core/Widget.Core.csproj", "src/Widget.Cli/Widget.Cli.csproj"}
        assert all(ecosystem == "net" for ecosystem, _ in found)

    def test_multi_module_maven_at_different_depths_all_returned(self):
        entries = [_blob("pom.xml"), _blob("module-a/pom.xml"), _blob("module-b/nested/pom.xml")]

        found = find_all_manifest_roots_from_tree(entries)

        assert len(found) == 3
        assert all(ecosystem == "java" for ecosystem, _ in found)

    def test_skips_noise_directories(self):
        entries = [_blob("node_modules/some-dep/package.json")]
        assert find_all_manifest_roots_from_tree(entries) == []

    def test_tree_entries_are_never_candidates_themselves(self):
        entries = [_tree("pom.xml")]
        assert find_all_manifest_roots_from_tree(entries) == []

    def test_empty_tree_finds_nothing(self):
        assert find_all_manifest_roots_from_tree([]) == []

    def test_does_not_mutate_first_match_wins_behavior(self):
        """`find_manifest_paths_from_tree()`'s existing contract (first
        match per ecosystem) stays exactly as it was -- additive, not a
        replacement."""
        entries = [_blob("pom.xml"), _blob("module-a/pom.xml")]

        first_match = find_manifest_paths_from_tree(entries)
        all_roots = find_all_manifest_roots_from_tree(entries)

        assert first_match["java"] == "pom.xml"  # unchanged: still one
        assert len(all_roots) == 2  # new function: both
