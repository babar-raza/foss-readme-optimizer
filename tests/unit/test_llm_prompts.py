"""Prompt assets load from prompts/relationship_explained/ (prompts/README.md
rule 1) and prompt_content_hash() actually reflects file content, so an edited
prompt file changes the generation hash rather than silently reusing a stale
one (rule 3)."""

from pathlib import Path

from readme_agent.llm import prompts as prompts_module
from readme_agent.llm.prompts import build_prompt, prompt_content_hash
from readme_agent.readme.facts import GapReportFacts, RepositoryFacts
from readme_agent.readme.gap_detector import GapReport
from readme_agent.registry.loader import load_policy

REPO_ROOT = Path(__file__).resolve().parents[2]


def _policy():
    return load_policy("aspose-3d-foss", REPO_ROOT / "config" / "policies")


def _facts() -> RepositoryFacts:
    return RepositoryFacts(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        commit_sha="abc123",
        manifest={"artifact_id": "aspose-3d-foss", "name": "Aspose.3D FOSS"},
        detected_license="MIT",
        gap_report=GapReportFacts.from_gap_report(
            GapReport(
                license_mentioned=False,
                products_org_link=False,
                products_com_link=False,
                relationship_explained=False,
            )
        ),
        policy_content_hash="policyhash123",
        prompt_content_hash="prompthash123",
    )


class TestBuildPromptLoadsExternalAssets:
    def test_messages_have_system_and_user_roles(self):
        messages = build_prompt(_facts(), _policy())
        assert [m["role"] for m in messages] == ["system", "user"]

    def test_user_message_substitutes_facts_and_policy_values(self):
        messages = build_prompt(_facts(), _policy())
        user = messages[1]["content"]
        assert "aspose-3d-foss/Aspose.3D-FOSS-for-Java" in user
        assert "Aspose.3D FOSS" in user
        assert "MIT" in user

    def test_response_shape_braces_survive_template_substitution(self):
        # $-style placeholders (string.Template) must not choke on the
        # literal JSON example's braces the way str.format() would.
        messages = build_prompt(_facts(), _policy())
        assert '"relationship_paragraph"' in messages[1]["content"]


class TestPromptContentHash:
    def test_stable_across_calls(self):
        assert prompt_content_hash() == prompt_content_hash()

    def test_changes_when_prompt_file_content_changes(self, tmp_path, monkeypatch):
        asset_dir = tmp_path / "relationship_explained"
        asset_dir.mkdir()
        (asset_dir / "system.txt").write_text("original system\n", encoding="utf-8")
        (asset_dir / "user.txt").write_text("original user $org_repo\n", encoding="utf-8")
        monkeypatch.setattr(prompts_module, "PROMPTS_DIR", asset_dir)

        before = prompt_content_hash()
        (asset_dir / "system.txt").write_text("edited system\n", encoding="utf-8")
        after = prompt_content_hash()

        assert before != after
