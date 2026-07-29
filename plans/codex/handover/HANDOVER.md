# Agent Handover

## 1. Handover Snapshot

| Field | Value |
|---|---|
| Verdict | `HANDOVER_READY` |
| Repository | `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer` |
| Branch / content checkpoint | `main` / `d258f0048e017ff49f7417a2304b9fc7730f10ea` |
| Upstream | `origin/main` at `696dd5d542282a1f9909b9453964c87466257589` |
| Working tree | Clean at the content checkpoint; the containing handover commit is the next commit |
| Mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` |
| Durable state | Version 532; graph `02e71ef95d30c059196a3f9c49553ed58eab22645f99af007b412a4ecc155f10`; no drift |
| Current phase | Source-complete discovery and read-only intake prerequisite |
| Active task | None; checkpoint intentionally released the claim |
| Next eligible task | `L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY` (`READY`) |
| Exact next action | Claim `L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY`; implement complete authorized-source observations and repair the public CLI allow-list-before-preflight ordering, then prove the known PDF Go MCP mismatch and unavailable-source controls. |
| Portfolio boundary | 31 repositories; facts 8, candidates 8, deterministic 8, agent-approved 0, no-op 0, human-accepted 0 |

This is a derived checkpoint. The supervisor Git-ref mission state remains the live claim and
transition authority and must be re-read before acting.

## 2. Ultimate Goal

Deliver and prove the autonomous repository-presentation system defined by `plans/idea.md`. It
must build verified product truth, generate repository-specific presentation proposals, validate
and independently review them, safely manage authorized draft effects, recover without duplicate
effects, and ultimately earn Level 8 through independently reproducible 30-day and 90-day
production evidence.

The immediate visible sequence first establishes a source-complete registry revision and enrolls
new repositories through read-only intake. It then qualifies seven representatives, eight total
finalized READMEs, eight finalized Python READMEs, every current Python README, the remaining
platforms, and full-registry Gate A. Every counted repository must have a deterministic-valid,
independently agent-approved, unchanged-rerun-proven bundle.

## 3. Current Mission and Scope

The only mission is `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`. Work stays on control-repository
`main`. No product write, GitHub App request, Gate C/D work, or human review occurs before its
ordered dependency gate. The system—not a human—selects normal capabilities and repairs.

Completion requires all durable taskcards to be `CLOSED`, truthful requirement/evidence
reconciliation, Gate A/B, `act`, staging, Gate C, hosted operation, Level 5, 30-day Level 7, and
90-day Level 8 proof. A test, commit, report, or partial portfolio is not completion.

## 4. Authority and Reference Map

Authority, in order:

1. `plans/idea.md` — product outcome and ordered gates.
2. `plans/master.md` — governed architecture, decisions, sequence, and maturity gates.
3. `plans/requirements.md` — normative acceptance.
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` — sole executable graph.
5. Supervisor Git-ref mission state — live statuses, claims, leases, and transitions.
6. `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` — supporting design only.

`AGENTS.md` and `plans/GOVERNANCE.md` are binding operating and safety rules. This directory is a
derived restart aid and never overrides durable state.

## 5. Exact Plan and Current Route

The current dependency route is:

1. Complete `L8-INTAKE-00` through `L8-INTAKE-03`: source-complete observation, stable provider
   identity, disabled/read-only enrollment, strong-README fast path, registry-revision binding,
   queue/recovery, and discovery health.
2. Requalify `L8-REVIEW-00-CONTEXT-CORPUS`.
3. Return `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to `READY`.
4. Prove good, defective, repairable, conflicting, and missing-evidence behavior across seven real
   ecosystem representatives under the same frozen reviewer standard, promoting Python first.
5. Complete serial heterogeneous qualification and freeze the P3 campaign.
6. Execute `L8-ACCEL-00-PYTHON-READINESS`, `L8-ACCEL-01-EIGHT-TOTAL`,
   `L8-ACCEL-02-EIGHT-PYTHON`, and `L8-ACCEL-03-ALL-PYTHON`.
7. Preserve completed Python work and continue .NET, Java, C++, TypeScript, Rust, Go through full
   Gate A without omitting any existing truth, cohort, healing, no-op, or reproduction task.
8. Gate B human review only after every repository is agent-approved and no-op-proven.
9. Prove the canonical workflow under `act`, then disposable staging.
10. Gate C Java draft-PR proof with fresh per-push authorization.
10. Request GitHub App authority only after Gate C, then hosted runtime and Level 5.
11. Complete Level 7's 30-day and Level 8's 90-day windows and independent audit.

Each task requires focused, integration, regression, safety, real/live-like, recovery,
idempotency, redaction, checksum, and independent evidence appropriate to its claim.

## 6. Work Completed and Truth Classification

Verified and durably closed immediately before this checkpoint:

- `L8-REVIEW-03A-CACHE-MEASUREMENT`: complete-input cache binding and measured invalidation
  evidence; implementation `40e6e73b`, evidence `4d168c97`.
- `L8-REVIEW-04-NO-OP-CACHE`: restart-safe exact reuse and stage-scoped invalidation; implementation
  `e37ba9b`, evidence `5fdf77de`.
- Plan commit `d3657907` added four non-omitting Python-first milestone taskcards, corrected the
  qualification dependency order, and migrated durable state to graph version 530 without losing
  history or changing the current reviewer-repair boundary.

The prior clean full suite at `40e6e73b` passed Ruff, format, mypy, and
`2129 passed, 41 deselected`. Later focused review/cache regressions passed, but no newer complete
suite was claimed for this evidence-only checkpoint.

Contradicted and reopened:

- `L8-REVIEW-00-CONTEXT-CORPUS` had been `CLOSED`. A fresh real C++ run on control HEAD
  `5fdf77de` proved the factual role still cannot complete its schema under the production route.
  Durable state now marks it `REGRESSED`.
- `L8-REVIEW-04A-REAL-CORPUS` was active. It is now `REROUTED` until the owning role route is
  repaired; the remaining six representatives were deliberately not called against a known-broken
  route.

## 7. Current Working State

The sealed C++ candidate is:

`runs/readme-poc/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/3e1edeacd4c1600507009c3fd3bf122d54f5d3a9`

The blind review completed. The factual review received about 25,014 prompt tokens and both
attempts terminated at exactly 2,400 completion tokens with truncated JSON. The second attempt
repeated the same structurally oversized request. The system correctly retained the candidate,
denied approval/repair authority, and made no remote write, but fail-closed behavior is not route
qualification.

Evidence is committed at:

`plans/investigations/evidence/level8-review-real-corpus-route-failure-v1/`

The evidence records the exact three-call delta, candidate/reviewer hashes, reproduction command,
root-cause boundary, and checksums. Commit `bb994cf9` contains it.

## 8. Remaining Gap and Permanent Repair

Gap `DISCOVERY-SOURCE-COMPLETENESS` affects `CORE-003`, `CORE-004`, `CORE-023`, `CORE-034`,
`OPS-005`, `OPS-007`, `ONB-002`, `PIL-015`, and `L8-035`–`L8-039`.

- Symptom: the current registry/workflow reports 31 naming matches while an active PDF Go MCP
  repository is visible but unmatched; one configured organization is unavailable.
- First failing boundary: raw source inventory and public CLI admission ordering.
- Structural cause: naming is an inclusion gate, identity is `(family, platform)`, source failures
  do not invalidate completeness, and new disabled entries have no durable intake path.
- Permanent solution: complete the four `L8-INTAKE-*` tasks exactly as specified in the graph.
- Required proof: complete observations, allow-list-before-preflight negative control,
  provider-ID reconciliation, intake fast/full paths, registry-revision/campaign binding,
  deduplication/recovery/health, and zero effects.

Gap `REVIEW-ROUTE-OUTPUT-BOUND` affects `L8-REVIEW-00-CONTEXT-CORPUS` and blocks
`L8-REVIEW-04A-REAL-CORPUS`.

- Symptom: invalid unterminated JSON on both factual-review attempts.
- First failing boundary: fixed 2,400-token completion cap plus an unchanged retry.
- Structural cause: the response contract is not bounded independently of evidence-rich repository
  size, while the transport treats length exhaustion like an ordinary invalid response.
- Preserve: separate blind/factual roles, grounding requirements, deterministic reducer,
  candidate retention, fail-closed verdicts, exact accounting, and no-write safety.
- Repair: bound the response schema, compact context without dropping evidence grounding, classify
  length termination distinctly, and use a bounded deterministic recovery strategy instead of an
  identical retry.
- Required proof: focused transport/schema/role tests; review integration and lifecycle tests;
  allow-list, push-blocking, and evidence-redaction regressions; successful complete C++ canary;
  then all seven real representatives with zero critical false accepts and effective repair.

Do not solve this only by weakening the schema, dropping fact citations, or blindly raising a
token cap. A larger bounded cap may be one component, but the contract must remain predictable in
cost and output size.

## 9. Ordered Execution Queue

1. Claim `L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY`.
2. Inspect `src/readme_agent/registry/`, `src/readme_agent/commands_supervision.py`,
   `src/readme_agent/preflight.py`, the current registry discovery tests, and the latest live
   discovery/workflow evidence cited by decision #84.
3. Implement typed source/observation inventory and the allow-list-before-preflight repair.
4. Run focused registry/CLI tests, safety regressions, and the live read-only mismatch/source-health
   proof. Write checksummed evidence and transition truthfully.
5. Continue `L8-INTAKE-01`, `L8-INTAKE-02`, and `L8-INTAKE-03` in order.
6. Claim `L8-REVIEW-00-CONTEXT-CORPUS`.
7. Inspect `src/readme_agent/llm/verifier_client.py`,
   `src/readme_agent/llm/reviewer_client.py`,
   `src/readme_agent/specialists/independent_readme_review.py`, the verification prompts, and their
   tests.
8. Implement the smallest complete bounded-output and length-aware recovery design within the
   taskcard's allowed paths.
9. Run focused tests, then review/lifecycle/safety regression.
10. Re-run only the sealed C++ canary. It must return a complete governed verdict, not
   `SYSTEM_FAILURE` from truncation.
11. Write checksum-complete evidence and close the reopened task only if the real canary and
   regressions pass.
12. Transition `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to `READY`, claim it, and execute the
   seven-representative corpus in Python, .NET, Java, C++, TypeScript, Rust, Go order.
13. Complete serial qualification and campaign freeze.
14. Run the four `L8-ACCEL-*` milestones: Python readiness, eight total, eight Python, all Python.
15. Continue the remaining platforms and all original Gate-A/later tasks through the graph-selected
    successors.

No other task currently needs a second editing operator. Later portfolio parallelism must be
runtime-owned, lease-isolated, and introduced only after representative qualification.

## 10. Decisions and Constraints

- One Codex operator; no overlapping top-level test/proof/supervisor process.
- Work only on `main`; preserve all existing work; no reset, restore, clean, or force-push.
- Every Codex commit requires the Codex co-author trailer.
- Maintain any `plans/master.md` section freely under current GOV-023/rule 12; preserve evidence,
  history, traceability, and mechanical validation.
- No product-repository write without fresh exact what/why/where approval.
- Use `.venv/Scripts/python`; no second environment or global installation.
- Prefer proven libraries/reference implementations before bespoke machinery.
- Deterministic control and safety remain authoritative; LLM output is a proposal.
- A `BLOCKED` result is agent-fixable unless proven external.
- No GitHub App request before local Gate A/B, `act`, staging, and Gate C.

## 11. Tests, Proof, and Evidence

This checkpoint and its immediate predecessor ran:

- source discovery audit: 31 checked-in entries, one active unmatched PDF Go MCP repository, and
  one unavailable configured source;
- requirement coverage: all 432 normative rows mapped;
- focused mission/governance tests: `38 passed`;
- mission migration: state 532, graph current, `L8-INTAKE-00` sole eligible task;
- live `readme-agent preflight`: GitHub reads and configured LLM route passed;
- real C++ reviewer probe: three new calls, `SYSTEM_FAILURE`, candidate retained, no write;
- `tests/security/test_no_secrets_in_evidence.py`: `2 passed`;
- commit hooks: Ruff, format, mypy, plan structure, and diff checks passed.

The next agent must not claim the real-corpus task complete from the current negative evidence.

## 12. Risks and Uncertainty

- The exact future authorized-source catalog still needs a durable typed representation; the
  current 26-organization seed is evidence, not proof of all future organization scope.
- The production route may need both response-contract compaction and a higher bounded completion
  budget; current evidence cannot establish which alone is sufficient.
- The current proof tool's stable campaign ledger accumulates old calls. Evidence therefore uses an
  explicit set-difference call delta. The eventual campaign tool should report per-invocation and
  cumulative accounting separately.
- A complete C++ verdict may expose genuine semantic defects after transport repair. That is
  expected and must flow through governed repair or fact-block paths.
- Six representatives remain untested under the corrected route.

## 13. Receiving Agent Startup Steps

1. Read `AGENTS.md`, `plans/GOVERNANCE.md`, the five authority layers above, and this handover.
2. Verify `main`, HEAD, clean tree, no repository-owned process, graph hash, and durable status.
3. If the snapshot differs, trust live durable state and reconcile this handover.
4. Claim only `L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY` through the supervisor lease mechanism.
5. Read all four `L8-INTAKE-*` taskcards, decision #84, and `L8-035`–`L8-039`.
6. Implement and prove each intake task in dependency order without starting reviewer work early.
7. Record redacted checksummed evidence, transition truthfully, commit to `main`, and rebuild
   eligibility.
8. Resume `L8-REVIEW-00-CONTEXT-CORPUS`, repair the bounded factual reviewer, and continue
   autonomously through the unchanged Python-first and maturity route.

## 14. Closure Standard

The mission may be called complete only when every mandatory durable task is `CLOSED`, requirements
and evidence agree, all local/workflow/staging/publication/hosted safety and recovery gates pass,
the 30-day and 90-day operating windows complete, and an independent audit awards Level 8. The
current state is not Gate A, Level 5, Level 7, or Level 8.
