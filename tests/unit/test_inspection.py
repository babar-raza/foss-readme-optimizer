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
