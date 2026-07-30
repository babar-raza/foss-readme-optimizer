# Continue the Repository-Presentation Mission

Resume `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer` as the sole operator on
`main`. Live Git, GitHub, and supervisor state override this snapshot.

Authority:

1. `plans/idea.md` — product outcome.
2. `plans/master.md` — architecture, decisions, order, and maturity gates.
3. `plans/requirements.md` — normative acceptance.
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` — sole executable graph.
5. Supervisor Git-ref state — actual tasks, claims, and transitions.
6. `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` — supporting route only.

Checkpoint: published `main` content HEAD before the handover-only commit
`9c4fe79e96c79ef07e3e38a82a93bbd7babb0dce`, graph
`b06692278422289619d543b9877d11fa75472aeb48363d100ed48008c8383ae3`, durable state version
620, no graph drift or active claim. The active goal is `GOAL-TP-TRUSTED-COHORT-POC`.
`TRP-04P-GITHUB-APP-HOSTED-QUALIFICATION` is `BLOCKED_EXTERNAL`; there is no eligible task.

The immediate goal is to carry the frozen three-member Python `TRUSTED_NO_OP_PROVEN` cohort
through the real hosted App, authorization, and draft-PR path, present it honestly, then resume
`TRP-04-CANARY-QUALIFICATION`. Do not call this cohort full-registry, verified Gate A/B/C, or a
maturity level. The ultimate goal remains the complete `verified_repository_presentation`
mission through independently reproduced Level 8.

Startup:

1. Read `AGENTS.md`, `HANDOVER.md`, the authority set above, and
   `plans/investigations/evidence/trp-04p-github-app-hosted-qualification-v1/provisioning-request.json`.
2. Inspect `git status`, HEAD/upstream, and repository-owned processes.
3. Run:

   ```powershell
   .venv/Scripts/readme-agent supervise `
     --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
     --mission-action status `
     --mission-observer codex
   ```

4. Query whether repository variable `GH_APP_CLIENT_ID` and repository secret
   `GH_APP_PRIVATE_KEY` exist. Never print or request the secret value.
5. If either is absent, retain the external block and provide the exact provisioning handoff. Do
   not substitute a PAT, ambient token, broader App, or product-organization installation.
6. If both exist, validate that the App is installed only on:
   `babar-raza/readme-agent-staging-note-python`,
   `babar-raza/readme-agent-staging-page-python`, and
   `babar-raza/readme-agent-staging-pdf-python`.
7. Reopen/claim the hosted task through the same supervisor and run:

   ```powershell
   gh workflow run readme-agent-production.yml `
     --repo babar-raza/foss-readme-optimizer `
     --ref main `
     --field proof_mode=github_app_staging_effect `
     --field qualified_cohort_manifest=plans/investigations/evidence/trp-04p-qualified-trusted-cohort-v1/1773cf81721531515766e5a61dc1a2e1ca467e1d6cc8350920f04dbb15095331/manifest.json `
     --field staging_target_manifest=plans/investigations/evidence/trp-04p-github-app-hosted-qualification-v1/staging-targets.json
   ```

8. Prove separate short-lived read/write installation tokens, zero analysis write-token exposure,
   trigger/recovery/health/effect behavior, one correct staging proposal per member, unchanged
   default branches, complete redacted manifests, and idempotent rerun.
9. Repair every agent-fixable failure at the first failing boundary; independently verify and
   close the task only with checksum-complete evidence.
10. Continue through `TRP-04P-AUTHORIZATION-ACCESS`. Before product effects, present the user the
    exact commit/diff/content, reason, repository, branch, and remote for fresh approval.
11. After approval, create/reconcile draft PRs only; never merge, mark ready, close, force-push, or
    write a default branch.
12. Present the indexed cohort POC and require mission evaluation to resume TRP-04 before TRP-05
    or any verified/maturity gate.

Continue autonomously:

```text
verify authority and live state
→ reconcile graph drift and claim lease
→ claim/reclaim only the highest-priority ready task
→ implement the smallest complete task slice
→ focused proof
→ integration/regression/safety/recovery/idempotency/live-like proof
→ independent verification
→ repair the first failing boundary
→ checksum-complete redacted evidence
→ update the same task/requirements/log/handover
→ commit coherent work directly to main
→ evaluate and continue
```

Do not create another plan, controller, queue, state store, or runtime. Do not stop for a completed
subtask, test failure, report, evidence bundle, checkpoint, dirty tree, or convenience. A real
external-authority block may pause the affected path only after all eligible graph-bound work is
exhausted. Documentation cannot keep an inactive chat alive; durable state makes restart safe.
