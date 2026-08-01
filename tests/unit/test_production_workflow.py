"""Static contracts for the sole scheduled/reusable production workflow."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/readme-agent-production.yml")
LEGACY_PORTFOLIO = Path(".github/workflows/readme-agent-portfolio.yml")


def test_production_workflow_has_all_trigger_and_recovery_surfaces():
    text = WORKFLOW.read_text(encoding="utf-8")

    for trigger in ("schedule:", "workflow_dispatch:", "workflow_call:", "repository_dispatch:"):
        assert trigger in text
    assert "readme-agent recovery-sweep" in text
    assert "readme-agent registry-preflight" in text
    assert "--act-fixture-inventory" in text
    assert text.count('cron: "') == 2
    assert "SCHEDULE_EXPRESSION: ${{ github.event.schedule }}" in text
    assert "needs: registry" in text
    assert "needs: [registry, recover]" in text
    assert "registry-revision-${{ github.run_id }}-${{ github.run_attempt }}" in text
    assert "--resume-trigger-key" in text
    assert "Resume the original durable trigger" in text
    assert "has_recovery" in text
    assert "readme-agent runtime-matrix" in text
    assert "readme-agent health-report" in text
    assert text.count("cancel-in-progress: false") == 2
    assert "queue: max" not in text
    assert "fail-fast: false" in text


def test_analysis_uses_dedicated_read_only_app_token_and_observe_profile():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/create-github-app-token@v3" in text
    assert text.count("client-id: ${{ vars.GH_APP_CLIENT_ID }}") == 4
    assert text.count("permission-contents: read") == 3
    assert "app-id:" not in text
    assert "permission-contents: read" in text
    assert "|| 'github_app' }}" in text
    assert "README_AGENT_GITHUB_APP_TOKEN:" in text
    assert "--execution-profile github_observe" in text
    assert "GITHUB_PAT" not in text


def test_act_proof_is_explicit_isolated_and_still_uses_the_canonical_supervisor():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "ACT proof modes are forbidden outside ACT=true" in text
    assert "readme-agent qualified-cohort-matrix" in text
    assert "readme-agent restore-qualified-cohort" in text
    assert "--execution-profile act_poc" in text
    assert "--max-readme-poc-stage TRUSTED_NO_OP_PROVEN" in text
    assert "--qualified-cohort-manifest" in text
    assert "README_AGENT_ACT_GITHUB_TOKEN:" in text
    assert "README_AGENT_STATE_REMOTE=" in text
    assert 'export README_AGENT_STATE_REMOTE="$PWD/runs/act-poc/state.git"' in text
    assert "shared-workspace-${GITHUB_RUN_ID}.marker" in text
    assert "invoke act with --bind" in text
    assert "README_AGENT_ACT_FAIL_REPOSITORY == matrix.repo" in text
    assert "controlled ACT failure for matrix-isolation proof" in text


def test_act_registry_intake_uses_current_registry_without_trusted_cohort():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'requested" = "act_registry_intake"' in text
    assert "ACT proof modes are forbidden outside ACT=true" in text
    assert "runs/act-registry-intake/state.git" in text
    assert "readme-agent runtime-matrix" in text
    assert "--execution-profile act_registry_intake" in text
    assert "--max-readme-poc-stage INTAKE_READY" in text


def test_staging_effect_consumes_frozen_candidates_without_rerunning_analysis():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "analyze:\n    name: Observe ${{ matrix.repo }}\n    needs: plan" in text
    assert "if: ${{ needs.plan.outputs.is_staging_effect != 'true' }}" in text
    staging_job_header = (
        "stage-proposal:\n    name: Stage trusted proposal for ${{ matrix.repo }}\n    needs: plan"
    )
    assert staging_job_header in text
    assert "needs: [plan, analyze]" not in text
    assert "requested repository is not in the qualified cohort" in text
    assert "runs/evidence/${{ github.run_id }}/${{ matrix.owner }}__${{ matrix.name }}/" in text
    assert "remote issue effect was correctly suppressed" in text


def test_hosted_staging_effect_mints_an_app_token_only_inside_the_effect_job():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'requested" = "github_app_staging_effect"' in text
    assert "github_app_staging_effect requires a frozen cohort manifest" in text
    assert "github_app_staging_effect requires a staging target manifest" in text
    assert "is_hosted_staging_effect=true" in text
    assert "Restore immutable hosted cohort candidates" in text
    assert "Resolve immutable disposable target before token minting" in text
    assert "Mint target-scoped GitHub App effect token" in text
    assert "permission-contents: write" in text
    assert "permission-pull-requests: write" in text
    assert '--auth-provider "$auth_provider"' in text
    assert "README_AGENT_GITHUB_APP_TOKEN: ${{ steps.staging-token.outputs.token }}" in text
    assert (
        "plans/investigations/evidence/"
        "trp-04p-github-app-hosted-qualification-v1/authorization" in text
    )

    effect_job = text.split("  stage-proposal:", maxsplit=1)[1].split("  health:", maxsplit=1)[0]
    analysis_job = text.split("  analyze:", maxsplit=1)[1].split("  stage-proposal:", maxsplit=1)[0]
    assert "permission-contents: write" in effect_job
    assert "permission-pull-requests: write" in effect_job
    assert "permission-pull-requests: write" not in analysis_job
    assert "README_AGENT_STAGING_WRITE_TOKEN" not in analysis_job


def test_hosted_staging_effect_has_no_pat_or_product_analysis_fallback():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "if: ${{ needs.plan.outputs.is_staging_effect != 'true' }}" in text
    assert (
        "needs.recover.outputs.has_recovery == 'true' && "
        "needs.recover.outputs.is_staging_effect != 'true'" in text
    )
    assert "auth_provider=github_app" in text
    assert "auth_provider=staging_pat" in text
    assert "GITHUB_PAT" not in text


def test_every_production_job_uses_the_locked_pip_cache_key():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert text.count("uses: actions/setup-python@v5") == 7
    assert text.count("cache: pip") == 7
    assert text.count("cache-dependency-path: requirements-lock.txt") == 7


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
