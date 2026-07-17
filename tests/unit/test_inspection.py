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


class TestFileInventoryPom:
    def test_finds_root_pom(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>", encoding="utf-8")
        inv = file_inventory.scan(tmp_path)
        assert inv.pom_path == tmp_path / "pom.xml"

    def test_missing_pom_is_none(self, tmp_path):
        inv = file_inventory.scan(tmp_path)
        assert inv.pom_path is None
