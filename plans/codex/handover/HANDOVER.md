# Agent Handover

## 1. Handover Snapshot

- Repository: `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer`
- Branch and published content checkpoint: `main`,
  `9c4fe79e96c79ef07e3e38a82a93bbd7babb0dce`; the handover-only commit follows this checkpoint
- Working tree at snapshot: clean; `main` equals `origin/main`
- Executable authority:
  `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`
- Graph SHA-256:
  `b06692278422289619d543b9877d11fa75472aeb48363d100ed48008c8383ae3`
- Durable mission state: version 620, no graph drift, no active claim
- Current phase: qualified trusted-cohort production-path POC
- Current task: `TRP-04P-GITHUB-APP-HOSTED-QUALIFICATION`,
  `BLOCKED_EXTERNAL`
- Exact next action: the owner provisions the narrowly scoped private GitHub App described in
  `plans/investigations/evidence/trp-04p-github-app-hosted-qualification-v1/provisioning-request.json`;
  Codex then validates the App and runs the disclosed hosted staging workflow.
- Overall status: the trusted cohort is frozen and proven under `act` and disposable staging;
  hosted App proof, authorization, product draft PRs, and presentation remain open.

This is a historical checkpoint. On restart, live Git, GitHub, and supervisor state override it.

## 2. Ultimate Goal

The ultimate goal remains `verified_repository_presentation`: an autonomous, repository-evidence-
backed system that manages applicable GitHub presentation surfaces safely and earns independently
reproducible Level 5, Level 7, and Level 8 evidence.

The immediate delivery goal is a deliberately partial trusted POC. Three current Python
`TRUSTED_NO_OP_PROVEN` bundles are being carried through the actual production-shaped workflow,
GitHub App identity, authorization, and draft-PR effect path. This gives the user a presentable,
reviewable POC while preserving the full adversarial qualification task.

The cohort POC does not satisfy full-registry trusted transformation, verified Gate A/B/C, or any
maturity level. Immediately after the cohort presentation, execution must resume
`TRP-04-CANARY-QUALIFICATION` at its durable boundary.

## 3. Current Mission and Scope

Mission ID: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`.

Current mandatory outcomes:

1. Keep the frozen cohort revision-, assurance-, contract-, and checksum-bound.
2. Use the canonical supervisor and reusable workflow; no direct retrofit effect path.
3. Prove GitHub App authentication in hosted staging without PAT or ambient-token fallback.
4. Keep analysis jobs free of target-write credentials.
5. Check live product access and consume reviewed, expiring authorization.
6. Obtain fresh exact what/why/where confirmation before each product-repository effect.
7. Create or update draft PRs only; never merge, mark ready, force-push, or write a default branch.
8. Present the cohort honestly as a partial trusted tranche.
9. Resume TRP-04, then the full-registry trusted and verified mission.

Non-goals at this checkpoint: regenerating cohort README intelligence, silently widening the App
installation, calling trusted claims repository-verified, closing TRP-04 from cohort PRs, or
requesting a production-organization App installation.

## 4. Authority and Reference Map

| Reference | Role | Current status |
|---|---|---|
| `plans/idea.md` | Product outcome | Current |
| `plans/master.md` decision #86 and Build Checklist | Governed sequence and test economy | Current |
| `plans/requirements.md` `TRP-016`–`TRP-019`, `NFR-014` | Normative acceptance | Current |
| Mission task graph | Sole executable dependency graph | Current, hash above |
| Supervisor Git-ref state | Task transitions and claims | Current, version 620 |
| `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` | Detailed supporting route | Supporting |
| `AGENTS.md` and `plans/GOVERNANCE.md` | Safety and effect authority | Binding |
| This handover set | Restart aid | Snapshot only |

The former TRP-00 handover snapshot at commit `e437e1d3` is stale and is superseded by this file.

## 5. Exact Plan

### Current cohort path

1. `TRP-04P-COHORT-FREEZE` — closed.
2. `TRP-04P-ACT-WORKFLOW-PARITY` — closed.
3. `TRP-04P-STAGING-EFFECT-PROOF` — closed.
4. `TRP-04P-TEST-LATENCY` — closed; an indispensable safety contribution that does not alter the
   README lifecycle scoreboard.
5. `TRP-04P-GITHUB-APP-HOSTED-QUALIFICATION` — externally blocked on App registration,
   installation, Client ID variable, and private-key secret.
6. `TRP-04P-AUTHORIZATION-ACCESS` — prove live product permissions and reviewed authorization.
7. `TRP-04P-DRAFT-PR-COHORT` — create/update exactly one authorized disclosed draft PR per cohort
   member.
8. `TRP-04P-POC-PRESENTATION` — deliver the indexed review package and transition back to TRP-04.

### Mandatory continuation

Resume `TRP-04-CANARY-QUALIFICATION`, then execute the full-registry trusted transformation,
workflow/staging/App delivery, and verified repository-presentation gates. Continue through the
three-Java Level-5 pilot, heterogeneous Level 6/7 operation, the 30-day Level-7 window, and the
90-day Level-8 window. No work is omitted; only the order changed.

## 6. Work Completed

Verified complete:

- Qualified cohort manifest for Note, Page, and PDF Python:
  `plans/investigations/evidence/trp-04p-qualified-trusted-cohort-v1/1773cf81721531515766e5a61dc1a2e1ca467e1d6cc8350920f04dbb15095331/manifest.json`.
- Canonical reusable-workflow parity under `act`.
- Disposable-staging create, no-op, update, drift, deduplication, lost-response, authorization
  expiry, and crash-boundary recovery.
- Staging default branches remained byte-identical and each target has one draft PR.
- Hosted App path implementation is committed and published at
  `03bdcd414e054b91c5aa182d1b42c3824e148825`.
- Bounded full-suite runner and verification economy are independently accepted.
- Latest published CI run `30544627395` passed Python 3.11, 3.12, and 3.13.

Implemented but not yet externally verified:

- Hosted App workflow inputs, token separation, and staging effect path exist, but no installed App
  identity is available to run them.

Not complete:

- Hosted App qualification, product access/authorization, product draft PRs, cohort presentation,
  resumed TRP-04, full-registry trusted delivery, and every later verified/maturity gate.

## 7. Current Working State

The worktree is clean. There is no repository-owned test, proof, or supervisor process running.
The durable graph reports:

- state version 620;
- no active task or claim;
- no eligible task;
- 54 unresolved tasks;
- two `BLOCKED_EXTERNAL` tasks;
- active goal `GOAL-TP-TRUSTED-COHORT-POC`;
- portfolio denominator 31;
- verified-lane facts/candidates/validation `7/31`;
- verified-lane agent approval/no-op/human acceptance `0/31`;
- first verified-lane failing boundary `FACTS_READY`.

The three trusted cohort members are not counted in the verified-lane headline scoreboard. This is
intentional assurance separation, not missing cohort evidence.

The required repository variable `GH_APP_CLIENT_ID` and secret `GH_APP_PRIVATE_KEY` were absent
when this checkpoint was refreshed. The current `gh` token cannot enumerate App installations.

## 8. Remaining Gaps

- `GAP-APP-AUTHORITY` / `TRP-04P-GITHUB-APP-HOSTED-QUALIFICATION`, P0:
  private App creation, key generation, and selected-repository installation require owner browser
  authority. Follow the exact provisioning request; do not widen scope.
- `GAP-HOSTED-PROOF` / `TRP-017`, P0:
  run the hosted staging workflow and prove short-lived token minting, analysis/effect isolation,
  trigger/recovery/health/effect behavior, and manifest completeness.
- `GAP-PRODUCT-AUTHORITY` / `TRP-018`, P0:
  check live permissions, create reviewed expiring authorization, and obtain fresh what/why/where
  approval for each product effect.
- `GAP-COHORT-PR` / `TRP-018`, P0:
  create/update exactly one draft PR per current cohort member and re-prove default-branch identity.
- `GAP-POC-PRESENTATION` / `TRP-019`, P0:
  package URLs, hashes, assurance disclosure, exclusions, review feedback, and the exact TRP-04
  resume transition.
- `GAP-TRP-04`, P0:
  the adversarial real canary matrix remains `REGRESSED`; cohort publication cannot close it.

## 9. Ordered Execution Queue

1. Owner provisions the App exactly as `provisioning-request.json` specifies.
2. Codex validates the variable, secret presence, installation scope, and separately minted
   short-lived read/write installation tokens.
3. Codex runs the hosted workflow using the frozen cohort and staging-target manifests.
4. Codex repairs any agent-fixable hosted failure and independently closes hosted qualification.
5. Codex proves product access and prepares reviewed, expiring assurance-specific authorization.
6. Codex presents the exact what/why/where product-effect package for fresh approval.
7. After approval, Codex creates/reconciles draft cohort PRs and proves default-branch identity.
8. Codex presents the indexed trusted POC.
9. Mission evaluation must select/reopen `TRP-04-CANARY-QUALIFICATION`.
10. Continue the complete graph without creating a competing plan or controller.

## 10. Decisions and Constraints

- Sole operator, one top-level process tree, control-repository `main` only.
- Preserve user work; no reset, restore, clean, force-push, or destructive history operation.
- Use the existing supervisor, task graph, state backend, authorization, effect ledger, and
  evidence system.
- Keep trusted and verified assurance mechanically disjoint.
- Never expose a target-write token to analysis, LLM, clone inspection, or validation.
- App installation at this gate is limited to the three named disposable staging repositories.
- Product effects require fresh exact what/why/where approval.
- Draft PR only; no merge, ready transition, force-push, close, or default-branch write.
- TRP-04 is held and must be resumed; it is not waived.
- A trusted cohort is not full-registry or maturity proof.
- Every Codex commit carries `Co-Authored-By: Codex <noreply@openai.com>`.

## 11. Tests, Proof, and Evidence

Current closure proof:

- Local full suite: 2,353 passed in 236.63 pytest seconds, selected inventory unchanged.
- Hosted CI: run `30544627395`, success across Python 3.11–3.13.
- Test-economy evidence:
  `plans/investigations/evidence/trp-04p-test-latency-v1/`.
- Staging proof:
  `plans/investigations/evidence/trp-04p-staging-effect-proof-v1/`.
- App handoff and hosted inputs:
  `plans/investigations/evidence/trp-04p-github-app-hosted-qualification-v1/`.

Not yet run: the App-authenticated hosted staging proof and all product-repository effects.

## 12. Risks and Uncertainty

- The two-day cohort target now depends on prompt owner provisioning and later product-effect
  approval.
- App permission or installation-scope mistakes may require correction before token minting.
- Hosted execution can reveal environment/recovery defects not visible under `act` or staging.
- The cohort contains only three Python repositories and may reveal README defects during review;
  common defects must become regression controls before TRP-04 resumes.
- Historical plan prose and the persisted umbrella goal may name older starting tasks. Live durable
  mission state is authoritative.

## 13. Receiving Agent Startup Steps

1. Read `AGENTS.md`, this handover, `CONTINUE.md`, and the provisioning request.
2. Verify `main`, HEAD, upstream, clean tree, repository processes, graph hash, and mission status.
3. Query only the names—not values—of `GH_APP_CLIENT_ID` and `GH_APP_PRIVATE_KEY`.
4. If absent, do not invent credentials or widen scope; report the exact owner handoff and retain
   the durable external block.
5. If present, validate the selected-repository installation and run the hosted workflow command in
   `CONTINUE.md`.
6. Capture focused, integration, recovery, idempotency, safety, and checksum-complete evidence.
7. Independently verify, repair the first failing boundary, update the same task/requirements/log/
   handover, commit to `main`, evaluate, and continue.
8. At the product-effect boundary, stop only for the required fresh exact what/why/where approval;
   continue automatically after it.

## 14. Closure Standard

The cohort POC closes only when hosted App proof passes, each authorized cohort repository has
exactly one disclosed draft PR, default branches are unchanged, evidence is checksum-valid, and
the indexed package is presented honestly. That closure must reactivate TRP-04.

The complete mission closes only after every mandatory task is evidence-backed `CLOSED`, every
requirement has truthful current proof, all local/workflow/staging/delivery/production/recovery/
idempotency/safety gates pass, the 30-day and 90-day windows finish, and an independent audit
awards Level 8.
