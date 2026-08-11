/loop

Repeat this canonical execution cycle without creating another controller:

1. Read live authority. From the repository root, inspect `AGENTS.md`, Git branch/HEAD/status,
   repository-owned processes, the Level-8 graph hash, and durable mission `status`. Narrative
   handover/status/roadmap files never override durable state.
2. Reconcile. Run mission `evaluate` after restart, graph change, dependency invalidation, or
   expired claim. Preserve transition history and every dependency-valid content-addressed stage.
3. Select only the highest-priority eligible graph task and its printed
   `TaskExecutionFocusV1`. Claim/reclaim it as `claude-coordinator`; never steal a live claim or
   execute a repository outside scope.
4. Load only its taskcard, always-on invariants, exact affected files, prior attempts, run manifests,
   independent receipts, and acceptance conditions. Protect all unrelated dirty/user-owned paths.
5. State the first failing boundary and smallest complete increment. Research/adopt proven tools
   before new custom infrastructure. Do not broaden into cleanup, redesign, or another plan.
6. Delegate only genuinely independent work. Record each active lease in
   `runs/multi-agent/<task-id>/execution-plan.json`; give exact exclusive paths/checks/evidence;
   workers never edit shared state/plans, transition, commit, aggregate, or perform effects. The
   acceptance verifier must be non-authoring. Current shared PDF repair is serial.
7. Implement the causal repair. Use only `.venv\Scripts\python.exe`; preserve safety, factuality,
   source accountability, component-scoped invalidation, redaction, and no-write boundaries.
8. Run focused Ruff/format/mypy/tests first, then impacted integration, cache, recovery, safety,
   no-op, and real repository proof required by the task. Run the optimized complete non-live suite
   only at its declared shared/Python/Gate-A boundary or a recorded P0 exception.
9. Adversarially review the raw artifacts. An exit 0, candidate, stored verdict, zero diff, or
   same-process recompose is not acceptance. Verify source/candidate/patch hashes, dependency keys,
   deterministic and independent bindings, official Mermaid geometry, manifests, inventories,
   provider/cache accounting, authorization and null effects.
10. Repair verified defects at their first owner and rerun only invalidated stages. Never weaken a
    validator or expectation to accept incorrect output.
11. Run a later complete identical fresh process. Require byte-identical artifacts, zero new
    provider calls, justified cache reuse, no patch, no duplicate lifecycle/effect, and zero
    unauthorized effects.
12. Obtain a separate independent non-authoring PASS. Promote exact accepted bytes to canonical
    checksum evidence and show the README before starting another repository or deferred broad work.
13. Update the same task/evidence/log/requirement source as appropriate; commit only owned coherent
    paths to control `main` with correct Claude attribution. Never stage
    `plans/backlog-post-poc.md` unless the human explicitly assigns it.
14. Transition through the same mission task with evidence, run `evaluate`, rebuild eligibility,
    and continue with the next printed task. Do not execute non-Python work before Python production
    admission closes.

Two-failure / stall recovery: after two materially equivalent failures or 15 minutes without a new
accepted artifact, resolved finding, changed candidate, or narrower root cause, stop that tactic;
preserve evidence; reread the invariant and owner; identify the false assumption; change the causal
owner, mechanism, or dependency-ready sequence; run the smallest decisive test; persist a typed
first-principles replan/material-narrowing record; then resume. Never add retries or rerun a broad
suite as a substitute for diagnosis.

Restart/context compaction: reread `plans/codex/handover/HANDOVER.md`, but immediately refresh Git,
processes, mission status, graph hash, claim expiry, manifests, and inventories. Recover through
mission leases/checkpoints; never infer completion from a missing process or stale report.

Continue unaffected eligible work around a narrowly proven external block. A blocker is valid only
for unavailable external authority, credentials, infrastructure, manual UI, or irrecoverable
external fact ownership after safe alternatives are exhausted. Report: exact objective; evidence;
attempts; why no safe progress remains; unaffected lanes; smallest human/external action; exact
resume predicate. Wiring, cache, planner, validator, dependency-provisioning, test, and code defects
are agent-fixable and cannot end the loop.

Final completion report: map every explicit goal/task/requirement/gate/invariant to current evidence;
give branch/HEAD, exact artifacts/hashes, tests and real workflow/effect proofs, human acceptance and
authorization records, recovery/idempotency results, remaining exclusions, and independent audit.
Declare completion only when no mandatory task is ready, reopened, regressed, agent-fixable, missing,
or unverified.
