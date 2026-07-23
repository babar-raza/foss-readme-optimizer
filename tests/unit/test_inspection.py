import os

from readme_agent.gitsafety._git import run_git
from readme_agent.inspection import file_inventory
from readme_agent.inspection.git_metadata import get_git_metadata


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    (path / "README.md").write_text("# test\n", encoding="utf-8")
    run_git(["add", "."], cwd=path)
    run_git(["commit", "-m", "initial"], cwd=path)
    return path


class TestGitMetadata:
    def test_extracts_branch_and_sha(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        run_git(["remote", "add", "origin", "https://github.com/example/example.git"], cwd=repo)

        meta = get_git_metadata(repo)

        assert meta.remote_url == "https://github.com/example/example.git"
        assert meta.branch == "main"
        assert meta.commit_sha is not None and len(meta.commit_sha) == 40


class TestFileInventoryReadme:
    def test_finds_standard_readme_md(self, tmp_path):
        (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.readme_path == tmp_path / "README.md"

    def test_finds_lowercase_readme(self, tmp_path):
        (tmp_path / "readme.md").write_text("# hi", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.readme_path == tmp_path / "readme.md"

    def test_missing_readme_is_none(self, tmp_path):
        inv = file_inventory.scan(tmp_path)
        assert inv.readme_path is None


class TestFileInventoryLicense:
    def test_finds_root_level_license_uppercase(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.license_path == tmp_path / "LICENSE"

    def test_finds_root_level_license_titlecase_txt(self, tmp_path):
        (tmp_path / "License.txt").write_text("MIT", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.license_path == tmp_path / "License.txt"

    def test_finds_license_in_nested_license_directory(self, tmp_path):
        """Real case: aspose-cells-foss repos put it at License/LICENSE.txt."""
        nested = tmp_path / "License"
        nested.mkdir()
        (nested / "LICENSE.txt").write_text("MIT", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.license_path == nested / "LICENSE.txt"

    def test_missing_license_is_none(self, tmp_path):
        inv = file_inventory.scan(tmp_path)
        assert inv.license_path is None


class TestFileInventoryManifests:
    def test_finds_root_pom_as_java(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.manifest_paths["java"] == tmp_path / "pom.xml"

    def test_missing_manifest_is_absent(self, tmp_path):
        inv = file_inventory.scan(tmp_path)
        assert inv.manifest_paths == {}

    def test_java_prefers_pom_over_gradle_when_both_present(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "build.gradle").write_text("", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.manifest_paths["java"] == tmp_path / "pom.xml"

    def test_finds_build_gradle_when_no_pom(self, tmp_path):
        (tmp_path / "build.gradle").write_text("", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.manifest_paths["java"] == tmp_path / "build.gradle"

    def test_finds_csproj_via_glob(self, tmp_path):
        (tmp_path / "widget.csproj").write_text("<Project/>", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.manifest_paths["net"] == tmp_path / "widget.csproj"

    def test_synthetic_multi_ecosystem_fixture(self, tmp_path):
        """ECO-001's own stated acceptance evidence: a RepositoryProfile
        must represent multiple languages/manifests per repository, not a
        single ecosystem string -- proven here at the detection layer with
        two real, simultaneously-present manifests."""
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)

        assert inv.manifest_paths["java"] == tmp_path / "pom.xml"
        assert inv.manifest_paths["python"] == tmp_path / "pyproject.toml"
        assert len(inv.manifest_paths) == 2

    def test_finds_nested_csproj_not_just_root(self, tmp_path):
        """Real bug, found by the full-registry survey (2026-07-19): every
        .NET repo in the registry has its .csproj under src/<Project>/, not
        at the repo root -- a root-only check missed 100% of them."""
        nested = tmp_path / "src" / "Widget"
        nested.mkdir(parents=True)
        (nested / "Widget.csproj").write_text("<Project/>", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)

        assert inv.manifest_paths["net"] == nested / "Widget.csproj"

    def test_finds_nested_cmakelists_not_just_root(self, tmp_path):
        """Same class of real bug for a literal (non-glob) filename: a real
        registry repo has CMakeLists.txt under a project subdirectory, not
        at the repo root."""
        nested = tmp_path / "Widget.Cpp"
        nested.mkdir()
        (nested / "CMakeLists.txt").write_text("project(widget)", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)

        assert inv.manifest_paths["cpp"] == nested / "CMakeLists.txt"

    def test_skips_noise_directories(self, tmp_path):
        """A vendored/build-output manifest is not the repo's own -- and
        descending into node_modules on a real repo is also the main
        performance risk this detection has to avoid."""
        noisy = tmp_path / "node_modules" / "some-dep"
        noisy.mkdir(parents=True)
        (noisy / "package.json").write_text("{}", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)

        assert "typescript" not in inv.manifest_paths

    def test_walk_stops_at_max_files_scanned_bound(self, tmp_path, monkeypatch):
        """Decision #40/Part B: a genuinely pathological tree (huge,
        single-ecosystem, most patterns never resolve) must not force an
        unbounded walk. Lower the bound to something small and prove a
        manifest past it is never found -- the bound actually took effect,
        not just "didn't crash"."""
        monkeypatch.setattr(file_inventory, "_MAX_FILES_SCANNED", 50)

        for d in range(6):
            noisy = tmp_path / f"d{d}"
            noisy.mkdir()
            for f in range(10):
                (noisy / f"noise{f}.txt").write_text("x", encoding="utf-8")
        past_bound = tmp_path / "d6"
        past_bound.mkdir()
        (past_bound / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)

        assert "python" not in inv.manifest_paths

    def test_bound_is_reached_deterministically_regardless_of_os_walk_order(
        self, tmp_path, monkeypatch
    ):
        """Wave 13.6 (`DEP-004`): `os.walk()`'s own directory/file order is
        filesystem-dependent, never guaranteed -- found live when a real
        `act` (Linux/Docker) run of this exact test disagreed with its own
        Windows-local result. Proven directly here by monkeypatching
        `os.walk` to yield entries in a deliberately reversed order (the
        opposite of this test's own construction order, simulating exactly
        the divergence found) and confirming the bound still trips on the
        same files regardless -- the fix (`dirs[:] = sorted(...)`/
        `sorted(files)`) makes the walk's own effective order deterministic,
        not dependent on whatever order the OS happens to hand back."""
        monkeypatch.setattr(file_inventory, "_MAX_FILES_SCANNED", 50)

        for d in range(6):
            noisy = tmp_path / f"d{d}"
            noisy.mkdir()
            for f in range(10):
                (noisy / f"noise{f}.txt").write_text("x", encoding="utf-8")
        past_bound = tmp_path / "d6"
        past_bound.mkdir()
        (past_bound / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

        real_walk = os.walk

        def _reversed_order_walk(path):
            for root, dirs, files in real_walk(path):
                dirs.reverse()
                files.reverse()
                yield root, dirs, files

        monkeypatch.setattr(file_inventory.os, "walk", _reversed_order_walk)

        inv = file_inventory.scan(tmp_path)

        assert "python" not in inv.manifest_paths

    def test_walk_within_max_files_scanned_bound_still_finds_manifest(self, tmp_path, monkeypatch):
        """Control case: the bound doesn't break the common, well-within-
        bound case -- a manifest found before the ceiling is hit is
        unaffected."""
        monkeypatch.setattr(file_inventory, "_MAX_FILES_SCANNED", 50)

        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        for d in range(6):
            noisy = tmp_path / f"d{d}"
            noisy.mkdir()
            for f in range(10):
                (noisy / f"noise{f}.txt").write_text("x", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)

        assert inv.manifest_paths["python"] == tmp_path / "pyproject.toml"


class TestFindAllManifestRoots:
    """Wave 11.1 (`ECO-004`): unlike `scan().manifest_paths` (deliberately
    "first match per ecosystem wins," unchanged), this finds every manifest
    across the whole tree -- the monorepo-support gap
    `resolve_manifest_candidates()`'s own docstring already names."""

    def test_single_root_returns_exactly_one_entry(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")

        roots = file_inventory.find_all_manifest_roots(tmp_path)

        assert roots == [("java", tmp_path / "pom.xml")]

    def test_multiple_csproj_files_all_returned(self, tmp_path):
        """A multi-project .NET solution -- the real, common layout this
        project's own registry already has multiple entries for."""
        (tmp_path / "src" / "Widget.Core").mkdir(parents=True)
        (tmp_path / "src" / "Widget.Core" / "Widget.Core.csproj").write_text(
            "<Project/>", encoding="utf-8"
        )
        (tmp_path / "src" / "Widget.Cli").mkdir(parents=True)
        (tmp_path / "src" / "Widget.Cli" / "Widget.Cli.csproj").write_text(
            "<Project/>", encoding="utf-8"
        )

        roots = file_inventory.find_all_manifest_roots(tmp_path)

        paths = {path for _, path in roots}
        assert paths == {
            tmp_path / "src" / "Widget.Core" / "Widget.Core.csproj",
            tmp_path / "src" / "Widget.Cli" / "Widget.Cli.csproj",
        }
        assert all(ecosystem == "net" for ecosystem, _ in roots)

    def test_multi_module_maven_at_different_depths_all_returned(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "module-a").mkdir()
        (tmp_path / "module-a" / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "module-b" / "nested").mkdir(parents=True)
        (tmp_path / "module-b" / "nested" / "pom.xml").write_text("<project/>", encoding="utf-8")

        roots = file_inventory.find_all_manifest_roots(tmp_path)

        assert len(roots) == 3
        assert all(ecosystem == "java" for ecosystem, _ in roots)

    def test_mixed_ecosystem_roots_all_returned(self, tmp_path):
        """An npm workspace root plus a Python subproject -- two different
        ecosystems, each its own root, neither hiding the other."""
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / "tools" / "scripts").mkdir(parents=True)
        (tmp_path / "tools" / "scripts" / "pyproject.toml").write_text(
            "[project]\nname='x'\n", encoding="utf-8"
        )

        roots = file_inventory.find_all_manifest_roots(tmp_path)

        ecosystems = {ecosystem for ecosystem, _ in roots}
        assert ecosystems == {"typescript", "python"}
        assert len(roots) == 2

    def test_no_manifests_returns_empty_list(self, tmp_path):
        assert file_inventory.find_all_manifest_roots(tmp_path) == []

    def test_skips_noise_directories(self, tmp_path):
        noisy = tmp_path / "node_modules" / "some-dep"
        noisy.mkdir(parents=True)
        (noisy / "package.json").write_text("{}", encoding="utf-8")

        assert file_inventory.find_all_manifest_roots(tmp_path) == []

    def test_does_not_mutate_scan_s_first_match_wins_behavior(self, tmp_path):
        """The existing `scan()`/`manifest_paths` contract (first match per
        ecosystem) must stay exactly as it was -- this new function is
        additive, not a replacement."""
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        (tmp_path / "module-a").mkdir()
        (tmp_path / "module-a" / "pom.xml").write_text("<project/>", encoding="utf-8")

        inv = file_inventory.scan(tmp_path)
        roots = file_inventory.find_all_manifest_roots(tmp_path)

        assert inv.manifest_paths["java"] == tmp_path / "pom.xml"  # unchanged: still one
        assert len(roots) == 2  # new function: both


class TestFileInventoryCommunityPaths:
    """Decision #19's repository-file-managed control class; decision #38's
    content fingerprint (`readme/facts.py::compute_tracked_content_hash`)
    depends on these being found the same case-insensitive way README/LICENSE
    already are."""

    def test_finds_contributing_uppercase_extension(self, tmp_path):
        (tmp_path / "CONTRIBUTING.md").write_text("please contribute", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.community_paths["CONTRIBUTING"] == tmp_path / "CONTRIBUTING.md"

    def test_finds_code_of_conduct_lowercase(self, tmp_path):
        (tmp_path / "code_of_conduct.md").write_text("be nice", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.community_paths["CODE_OF_CONDUCT"] == tmp_path / "code_of_conduct.md"

    def test_finds_security_and_support(self, tmp_path):
        (tmp_path / "SECURITY.md").write_text("report issues here", encoding="utf-8")
        (tmp_path / "SUPPORT.md").write_text("get help here", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.community_paths["SECURITY"] == tmp_path / "SECURITY.md"
        assert inv.community_paths["SUPPORT"] == tmp_path / "SUPPORT.md"

    def test_missing_community_files_produce_an_empty_dict(self, tmp_path):
        inv = file_inventory.scan(tmp_path)
        assert inv.community_paths == {}
