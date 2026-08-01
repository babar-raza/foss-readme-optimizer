# L8-INTAKE-03 verified local closure

This evidence closes the local registry-revision, intake-queue, recovery, and health task at
control commit `1f4f8a98f1f3c4e1510ce028d11c55f10bf0320b`. It does not claim hosted
dead-man operation, Gate A, or finished README proposals.

## Live authorized-source result

The 2026-08-01 all-visibility scan enumerated public and private repositories from every enabled
source and produced complete `RegistryRevisionV1`
`d610fc75069655d0f9d83f37198c3ba1f92b29d06bc210858150bf245722bb7e`:

- 33 admitted and observed repositories;
- zero unexplained observations, source failures, stale scans, or pending intake;
- one explicit source exclusion for nonexistent `aspose-imaging-foss`, with the separate
  non-FOSS `aspose-imaging` organization deliberately not substituted;
- one newly discovered private product repository, `aspose-html-foss/CSSForge`, bound to GitHub
  repository ID `1319039143` and node ID `R_kgDOTp7wpw`;
- one deduplicated CSSForge intake, classified `READY_FULL_PIPELINE` at immutable source revision
  `b972777dd11f1045ac695513e73d68883404e7bc`;
- a clean identical replay with no queue, no new effect, and an eligible intake gate.

Private read clone and control-state Git operations use a process-local GitHub HTTPS header. No
credential is stored in Git config, command arguments, or evidence. Git LFS smudging is disabled
for source inspection. The initial CSSForge retry exposed a stale `SYSTEM_FAILURE` lifecycle even
after a successful intake receipt; commit `1f4f8a98` permanently repairs both future retries and
historical reconciliation. The durable scoreboard now contains 14 `INTAKE_READY`, 10
`NO_OP_PROVEN`, 7 `DETERMINISTIC_VALIDATED`, and 2 `BLOCKED_MISSING_EVIDENCE` records, with no
`SYSTEM_FAILURE`; the next portfolio boundary is `FACTS_READY`.

Raw ignored runtime artifacts and their SHA-256 hashes are recorded in
`live-registry-all-visibility-summary.json`. The clean no-op replay is bound to the committed
33-entry registry and the clean official campaign is bound to `1f4f8a98`.

## Workflow, failure, and recovery proof

The actual reusable workflow passed under Docker/ACT through registry, recovery, matrix planning,
canonical supervision, evidence, and health:

- run 42: complete 32-member fixture revision, `INTAKE_READY`, `RunManifestV3`, zero LLM calls;
- run 43: injected one matrix failure, preserved unrelated Note/Python completion, surfaced
  unhealthy workflow evidence, and exited nonzero;
- run 44: recovered an expired `processing` trigger, resumed the exact dedup key, reused intake,
  and exited zero.

Separate ACT controls cover `workflow_dispatch`, `schedule`, `repository_dispatch`, and
`workflow_call`; one logical observation creates one intake; an enabled-source outage fails
closed while preserving diagnostic evidence. ACT fixture revisions carry `proof_scope:
act_fixture` and are rejected outside ACT, so they cannot impersonate live enumeration.

The current local health report checks 33 repositories and reports zero missed windows, stale
leases, state failures, evidence failures, or workflow failures. Overall health remains false
because 111 historical retry records and 66 repeated-failure records remain visible. Those
historical records are truthful operational backlog, not a current registry-gate failure; the
embedded registry revision gate is eligible.

Hosted schedule/dead-man operation remains part of later trusted T3/hosted-runtime proof and is
therefore still `PARTIAL` under global requirement `L8-039`. This local task explicitly neither
requests nor requires GitHub App authority.

## Verification

The clean `main` commit passed Ruff, formatting, mypy, 2,604/2,604 non-live tests, plan
validation, verifier wiring, prompt hygiene, requirement/task coverage, semantic traceability,
pinned actionlint 1.7.7, and `git diff --check`. The pytest manifest records a clean tree, exact
dependency-lock and test-inventory hashes, four workers, zero worker restart, and zero leaked
process IDs.

`independent-verification.json` is a separate deterministic replay of the committed evidence
contract. `mission-contribution.json` binds every task acceptance check to the current lifecycle
scoreboard hash.

Reproduction commands:

```powershell
.venv/Scripts/readme-agent registry-preflight --registry data/products.json --force-refresh --output runs/registry-revisions/live-preflight.json
.venv/Scripts/readme-agent registry-preflight --registry data/products.json --no-refresh --output runs/registry-revisions/live-preflight-noop.json
.venv/Scripts/readme-agent health-report --output runs/registry-revisions/live-health.json
.venv/Scripts/python scripts/governance/run_official_checks.py
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7
```

No target product remote was written.
