# Agent Handover

## 1. Handover Snapshot

| Field | Value |
|---|---|
| Verdict | `HANDOVER_READY` |
| Repository | `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer` |
| Branch / content checkpoint | `main` / `d3657907679824cb67ed55f5fd726a02064a73df` |
| Upstream | `origin/main` at `5fdf77deb3898db4994413d5f77b8470a9ee1290` |
| Working tree | Clean at the content checkpoint; the containing handover commit is the next commit |
| Mission | `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` |
| Durable state | Version 531; graph `8486ade4cdfbee608dce30d0859eab4afa5d15efec58ef43848dc7cfb4aa2997`; no drift |
| Current phase | Independent-review production-route qualification |
| Active task | None; checkpoint intentionally released the claim |
| Next eligible task | `L8-REVIEW-00-CONTEXT-CORPUS` (`REGRESSED`) |
| Exact next action | Claim `L8-REVIEW-00-CONTEXT-CORPUS`, repair the bounded factual-review output/transport contract, and re-run the sealed C++ canary before resuming the seven-representative corpus. |
| Portfolio boundary | 31 repositories; facts 8, candidates 8, deterministic 8, agent-approved 0, no-op 0, human-accepted 0 |

This is a derived checkpoint. The supervisor Git-ref mission state remains the live claim and
transition authority and must be re-read before acting.

## 2. Ultimate Goal

Deliver and prove the autonomous repository-presentation system defined by `plans/idea.md`. It
must build verified product truth, generate repository-specific presentation proposals, validate
and independently review them, safely manage authorized draft effects, recover without duplicate
effects, and ultimately earn Level 8 through independently reproducible 30-day and 90-day
production evidence.

The immediate visible sequence is seven qualified representatives, eight total finalized
READMEs, eight finalized Python READMEs, every current Python README, then the remaining platforms
and full-registry Gate A. Every counted repository must have a deterministic-valid, independently
agent-approved, unchanged-rerun-proven bundle.

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

1. Requalify `L8-REVIEW-00-CONTEXT-CORPUS`.
2. Return `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to `READY`.
3. Prove good, defective, repairable, conflicting, and missing-evidence behavior across seven real
   ecosystem representatives under the same frozen reviewer standard, promoting Python first.
4. Complete serial heterogeneous qualification and freeze the P3 campaign.
5. Execute `L8-ACCEL-00-PYTHON-READINESS`, `L8-ACCEL-01-EIGHT-TOTAL`,
   `L8-ACCEL-02-EIGHT-PYTHON`, and `L8-ACCEL-03-ALL-PYTHON`.
6. Preserve completed Python work and continue .NET, Java, C++, TypeScript, Rust, Go through full
   Gate A without omitting any existing truth, cohort, healing, no-op, or reproduction task.
7. Gate B human review only after every repository is agent-approved and no-op-proven.
8. Prove the canonical workflow under `act`, then disposable staging.
9. Gate C Java draft-PR proof with fresh per-push authorization.
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

1. Claim `L8-REVIEW-00-CONTEXT-CORPUS`.
2. Inspect `src/readme_agent/llm/verifier_client.py`,
   `src/readme_agent/llm/reviewer_client.py`,
   `src/readme_agent/specialists/independent_readme_review.py`, the verification prompts, and their
   tests.
3. Implement the smallest complete bounded-output and length-aware recovery design within the
   taskcard's allowed paths.
4. Run focused tests, then review/lifecycle/safety regression.
5. Re-run only the sealed C++ canary. It must return a complete governed verdict, not
   `SYSTEM_FAILURE` from truncation.
6. Write checksum-complete evidence and close the reopened task only if the real canary and
   regressions pass.
7. Transition `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to `READY`, claim it, and execute the
   seven-representative corpus in Python, .NET, Java, C++, TypeScript, Rust, Go order.
8. Complete serial qualification and campaign freeze.
9. Run the four `L8-ACCEL-*` milestones: Python readiness, eight total, eight Python, all Python.
10. Continue the remaining platforms and all original Gate-A/later tasks through the graph-selected
    successors.

No other task currently needs a second editing operator. Later portfolio parallelism must be
runtime-owned, lease-isolated, and introduced only after representative qualification.

## 10. Decisions and Constraints

- One Codex operator; no overlapping top-level test/proof/supervisor process.
- Work only on `main`; preserve all existing work; no reset, restore, clean, or force-push.
- Every Codex commit requires the Codex co-author trailer.
- No `plans/master.md` edit without fresh section-specific approval.
- No product-repository write without fresh exact what/why/where approval.
- Use `.venv/Scripts/python`; no second environment or global installation.
- Prefer proven libraries/reference implementations before bespoke machinery.
- Deterministic control and safety remain authoritative; LLM output is a proposal.
- A `BLOCKED` result is agent-fixable unless proven external.
- No GitHub App request before local Gate A/B, `act`, staging, and Gate C.

## 11. Tests, Proof, and Evidence

This checkpoint ran:

- live `readme-agent preflight`: GitHub reads and configured LLM route passed;
- real C++ reviewer probe: three new calls, `SYSTEM_FAILURE`, candidate retained, no write;
- `tests/security/test_no_secrets_in_evidence.py`: `2 passed`;
- commit hooks: Ruff, format, mypy, plan structure, and diff checks passed.

The next agent must not claim the real-corpus task complete from the current negative evidence.

## 12. Risks and Uncertainty

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
4. Claim only `L8-REVIEW-00-CONTEXT-CORPUS` through the supervisor lease mechanism.
5. Read its complete taskcard and the failure evidence.
6. Inspect the output contract and transport before editing.
7. Implement a bounded, length-aware, grounded reviewer route.
8. Run focused and regression proof, then the sealed C++ live canary.
9. Record redacted checksummed evidence, transition truthfully, commit to `main`, and rebuild
   eligibility.
10. Resume `L8-REVIEW-04A-REAL-CORPUS` and continue autonomously.

## 14. Closure Standard

The mission may be called complete only when every mandatory durable task is `CLOSED`, requirements
and evidence agree, all local/workflow/staging/publication/hosted safety and recovery gates pass,
the 30-day and 90-day operating windows complete, and an independent audit awards Level 8. The
current state is not Gate A, Level 5, Level 7, or Level 8.
