# TRP-04P ACT Workflow Parity Reproduction

This evidence binds commit `700b232d39918b0d77fe1b36c18d6e9bea0ae209` and cohort
`1773cf81721531515766e5a61dc1a2e1ca467e1d6cc8350920f04dbb15095331`.

Use the repository `.venv`. Docker must be running. ACT must use `--bind`; copy mode is
intentionally rejected because it cannot share ignored durable state between job containers.

```powershell
$act = 'C:\Users\prora\AppData\Local\Microsoft\WinGet\Packages\nektos.act_Microsoft.Winget.Source_8wekyb3d8bbwe\act.exe'
$manifest = 'plans/investigations/evidence/trp-04p-qualified-trusted-cohort-v1/1773cf81721531515766e5a61dc1a2e1ca467e1d6cc8350920f04dbb15095331/manifest.json'

# The value is supplied through the environment, never on the process command line.
$env:ACT_GITHUB_READ_TOKEN = $env:GH_TOKEN

& $act workflow_dispatch --bind `
  -W .github/workflows/readme-agent-production.yml `
  -j health `
  --env GITHUB_RUN_ID=16 `
  --input proof_mode=act_qualified_cohort `
  --input "qualified_cohort_manifest=$manifest" `
  -s ACT_GITHUB_READ_TOKEN `
  -s LLM_API_KEY `
  -s 'LLM_BASE_URL=' `
  -s 'GH_APP_PRIVATE_KEY=act-not-used' `
  -s 'GH_APP_ID=0' `
  --artifact-server-path runs/act-poc/artifacts
```

Expected result:

- the exact three-member frozen matrix is emitted;
- each member is `STAGE_COMPLETE` or a durable `DEDUPLICATED` retry;
- every terminal manifest reports `trusted_inherited`, `TRUSTED_NO_OP_PROVEN`, zero LLM calls,
  zero effects, and five repository-bound evidence files;
- `runs/workflow/health-report.json` reports `healthy: true` for all three repositories.

The recovery proof seeds an expired `processing` trigger in `runs/act-poc/state.git`, then invokes
the same workflow with `--bind -j resume`. The raw accepted run is
`runs/act-poc/bind-recovery-run-15.stdout.log`. Failure isolation uses the same logical delivery
after terminal completion with:

```powershell
--env 'README_AGENT_ACT_FAIL_REPOSITORY=aspose-page-foss/Aspose.Page-FOSS-for-Python'
```

Note and PDF must deduplicate successfully, Page must fail at the controlled boundary, and the
aggregate ACT result must remain failed. Ambient-token rejection omits `ACT_GITHUB_READ_TOKEN`
while leaving ambient PAT variables present; the workflow must emit the dedicated-token error
recorded in `verification.json`.

Run focused regression checks:

```powershell
.venv/Scripts/python -m pytest -q `
  tests/unit/test_cli.py `
  tests/unit/test_env.py `
  tests/unit/test_execution_profile.py `
  tests/unit/test_git_state_backend_fetch.py `
  tests/unit/test_gitsafety.py `
  tests/unit/test_production_workflow.py `
  tests/unit/test_trusted_cohort_runtime.py `
  tests/unit/test_content_assurance.py `
  tests/unit/test_lifecycle_state.py `
  tests/unit/test_commands_lifecycle.py `
  tests/unit/test_readme_poc_lifecycle.py `
  tests/security/test_no_secrets_in_evidence.py
```

The accepted result is `238 passed`.
