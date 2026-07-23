"""Static contracts for the sole scheduled/reusable production workflow."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/readme-agent-production.yml")
LEGACY_PORTFOLIO = Path(".github/workflows/readme-agent-portfolio.yml")


def test_production_workflow_has_all_trigger_and_recovery_surfaces():
    text = WORKFLOW.read_text(encoding="utf-8")

    for trigger in ("schedule:", "workflow_dispatch:", "workflow_call:", "repository_dispatch:"):
        assert trigger in text
    assert "readme-agent recovery-sweep" in text
    assert "--resume-trigger-key" in text
    assert "Resume the original durable trigger" in text
    assert "has_recovery" in text
    assert "readme-agent runtime-matrix" in text
    assert "readme-agent health-report" in text
    assert "queue: max" in text
    assert "fail-fast: false" in text


def test_analysis_uses_dedicated_read_only_app_token_and_observe_profile():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/create-github-app-token@v3" in text
    assert text.count("client-id: ${{ vars.GH_APP_CLIENT_ID }}") == 2
    assert "app-id:" not in text
    assert "permission-contents: read" in text
    assert "README_AGENT_PRODUCTION_AUTH: github_app" in text
    assert "README_AGENT_GITHUB_APP_TOKEN:" in text
    assert "--execution-profile github_observe" in text
    assert "GITHUB_PAT" not in text


def test_only_production_runtime_is_scheduled():
    legacy = LEGACY_PORTFOLIO.read_text(encoding="utf-8")

    assert "legacy manual diagnostic" in legacy
    assert "schedule:" not in legacy


def test_health_is_visible_as_artifact_issue_check_and_external_heartbeat():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "portfolio-health-" in text
    assert "gh issue create" in text
    assert "Fail the Actions check" in text
    assert "DEAD_MAN_HEARTBEAT_URL" in text
