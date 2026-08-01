# L8-INTAKE-03 partial verification

This evidence records the first production-like local proof of registry revision, durable
discovery intake, and portfolio health binding. It is intentionally **PARTIAL**, not task closure.

The 2026-08-01 forced read-only scan observed 32 accessible repositories, generalized the product
variant naming contract, admitted `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP` as the 32nd disabled
entry, and delivered exactly one provider-ID plus observation-revision trigger. The existing intake
pipeline classified its immutable source revision as `READY_FAST_PATH`; the repeated-delivery unit
control reused the same trigger.

The resulting revision is not Gate-A eligible. The configured `aspose-imaging-foss` source returns
HTTP 404 to the current credential, so the revision retains one explicit source failure and health
reports `source_scan_incomplete` plus `source_failures_present`. The remaining task boundary is a
source-complete live scan with organization-compliant all-visibility authority. No product remote
was written.

The coherent regression campaign passed Ruff, formatting, mypy, all 2,580 non-live tests, plan
validation, verifier wiring, prompt hygiene, requirement/taskcard coverage, semantic traceability,
pinned actionlint 1.7.7, and `git diff --check`. Expanding the registry correctly invalidated the
historical three-member trusted cohort by its registry hash; focused controls prove this is a
fail-closed contract transition, not a relaxation of frozen-cohort admission.

The real reusable workflow's `registry` job then passed under Docker/ACT at control commit
`dc47169a` with exit 0. It emitted and uploaded a complete 32-member fixture revision, with zero
source failures, pending intake, or unexplained observations. The fixture is explicitly bound as
`proof_scope: act_fixture`; evaluating the persisted revision outside ACT fails closed with
`act_fixture_not_admissible`. This proves the new workflow boundary without pretending the fixture
is live source-enumeration evidence. `act-registry-job-summary.json` binds the raw disposable log
and uploaded artifact by SHA-256.

The same registry job also exits 0 for `schedule`, `repository_dispatch`, and `workflow_call` in
ACT, with each run uploading its own revision artifact. An injected `aspose-imaging-foss` source
outage exits 1, preserves the 32-entry registry, records both incomplete-source gate reasons, and
still uploads diagnostic evidence through the workflow's `always()` path. These results close
trigger parity and source-outage behavior for the registry job.

Clean control commit `845bbaa31483c8656905548571653dfdf079ef44` then passed the actual
workflow under ACT through registry, recovery, matrix planning, canonical supervision, evidence,
and health. Run 42 reached `INTAKE_READY` for the newly admitted Go MCP repository, emitted a
`RunManifestV3` bound to all 32 admitted repositories, made zero LLM calls, and exited 0. Run 43
injected one pre-supervisor Go MCP matrix failure; Note/Python still completed with its own
registry-bound evidence, health recorded `workflow_failures: [{job: analyze, result: failure}]`,
and the workflow exited 1. Run 44 recovered one deliberately expired `processing` trigger,
incremented its recovery count, resumed the exact dedup key, reused the intake result, and exited
0. `act-registry-intake-workflow-summary.json` binds all raw disposable artifacts by SHA-256.

This is complete local workflow-fixture proof for downstream intake, isolation, recovery, and
health. It does not convert the ACT fixture into live enumeration proof and therefore does not
close the task while `aspose-imaging-foss` remains unresolved.

Reproduction commands:

```powershell
.venv/Scripts/readme-agent registry-preflight --registry data/products.json --force-refresh --output runs/registry-revisions/live-preflight.json
.venv/Scripts/readme-agent health-report --output runs/registry-revisions/live-health.json
.venv/Scripts/python -m pytest -q tests/unit/test_registry_discovery.py tests/unit/test_registry_reconciliation.py tests/unit/test_registry_revision.py tests/unit/test_registry_self_heal.py tests/unit/test_commands_lifecycle.py tests/unit/test_lifecycle_state.py tests/unit/test_production_workflow.py tests/unit/test_cli.py::TestLocalPocPortfolioCommand
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/readme-agent-production.yml
.venv/Scripts/python scripts/governance/run_official_checks.py
```
