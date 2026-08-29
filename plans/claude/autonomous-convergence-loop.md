# Autonomous convergence loop — hardened, taskcard-driven execution plan

Sprint identity: **autonomous-convergence-loop** (unchanged).
Mission: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`. Controller: `readme-agent supervise` (Decision #26).
Authoritative task graph: `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`.
Evidence chain: `plans/investigations/evidence/autonomous-convergence-loop/`.

This file is the **single governing sprint plan** for this line of work. It supersedes the plan-mode
draft that previously lived at `~/.claude/plans/i-want-to-autonomously-hidden-crown.md`; that file now
points here so no competing copy exists. It does **not** supersede `plans/master.md`,
`plans/GOVERNANCE.md`, or `plans/requirements.md`, which remain authoritative for their own domains.

---

## 1. Plan File Hardening Change Log

| # | Change | Reason | Source |
|---|---|---|---|
| H1 | Moved the plan into the repository at `plans/claude/autonomous-convergence-loop.md`; the plan-mode file became a pointer. | A plan governing in-repo taskcards, gates and evidence must be versioned and readable by every agent working here, including ones with no access to `~/.claude/`. Precedent: `plans/claude/moonlit-juggling-flurry.md`, `plans/codex/*.md`. | Governance placement rules |
| H2 | **Deleted the "all 10 taskcards are TODO" premise.** Replaced with the authoritative status table (§4.1) and a standing rule that the graph file's `status:` field is not live truth. | Proven false: 5 CLOSED, 2 REGRESSED, 1 IN_PROGRESS at G0. The plan's entire "promote something to READY first" opening move was based on a wrong read. | `gate-outputs/g0-plan-versus-authoritative-state-reconciliation.md` Conflict 1 |
| H3 | **Deleted gate G2 "add four new taskcards".** The work now maps onto the existing ten cards through the plan-local register (§5); graph insertion is a capped, conditional sub-gate (§5.1). | The live critical path is `L8-PF-02-COMPLETE-CANDIDATE-SEAM`, which is already in the graph and already claimed. Adding `L8-PF-00A/02A/03A/08` would have spent 4 of 5 free budget slots to restate cards that already exist. | Conflict 5; `validate_compact_authority.py:229` |
| H4 | Corrected the citation "mission `evaluate` reconciles graph drift, claims, lifecycle freshness, and component hashes" from `plans/master.md` to **`plans/idea.md:158`**. | The sentence is not in `master.md`; `master.md:476` says only "first reconciles closed-task freshness". The misattribution had reached production source, a test, a log shard and an evidence file. | Independent verification, "Misattributed citation" |
| H5 | Corrected the evidence-bundle manifest filename from `SHA256SUMS` to **`sha256sums.txt`**. | The plan named a file the producer does not write; a checker keyed on the planned name would have passed vacuously. | `plans/investigations/evidence/autonomous-convergence-loop/` |
| H6 | Corrected the baseline metric from "`no_op_proven 1/34`" to **contract-valid `no_op_proven 0/34`, `raw_lifecycle_progress` 1/34**. | The plan quoted the raw counter as if it were the contract-valid one. 22 repositories carry stale fact contracts, which is why every contract-valid counter reads 0. | Conflict 5 |
| H7 | Added a mandatory **canonical-runner clause** to every test-related acceptance check: a new test counts only when green under `scripts/governance/run_full_pytest.py`, never under a bare `pytest`. | A commit's own new tests passed under bare `pytest` and failed under the canonical runner's deliberately short `--basetemp`, turning a claimed "5 → 2" into an actual "5 → 4". | Independent verification, D1 |
| H8 | Added a **sibling-site sweep** obligation to the repair loop (§10). | The MAX_PATH fix was landed at one site while two siblings carried the identical defect, one of them failing **open**. | Independent verification, D2 |
| H9 | Added evidence-contract rules: seal only on a clean tree, list **every** commit, and cite findings to committed artifacts, never to a session transcript. | The sealed bundle records `tree_clean_at_seal: false`, `mission-contribution.json` lists 1 of 4 commits, and `independent-verification.json` points at "the session transcript". | §8; bundle inspection |
| H10 | Renamed the gate that carries independent verification so it no longer collides with the scheduler gate. | `gate-outputs/g5-independent-verification-findings-and-repairs.md` sits under the label the gate table gives to "G5 convergence scheduler". Two different things were called G5. | Bundle inspection |
| H11 | Every unresolved item is now a taskcard with 16 declared fields (§5). Nothing actionable remains prose-only. | Hardening requirement. | — |
| H12 | Added `ACL-CLAIM-LEASE-HYGIENE` as the first executable card. | The current claim on `L8-PF-02` by `readme-agent-supervisor` expired at `2026-08-29T08:54:02Z`. Any resumed run starts inside the exact deadlock this sprint fixed. | Live state read, this run |
| H13 | Replaced "human review" and "ask the human" phrasing throughout with the standing-authority position: no item in this plan needs external authority (§13). | Required review point: do not treat the human as a blocker unless the action truly requires external authority or credentials the agent cannot access. | GOVERNANCE rule 19; Decision #107 |
| H14 | Preserved unchanged: sprint identity, gate letters G0–G7, lane names, the seven proposed requirement IDs, the proof chain, the rollback table, and the single-go execution prompt (repaired in place, not rewritten). | Preservation rule. | — |
| H15 | **Cycle 2.** Marked `ACL-CLAIM-LEASE-HYGIENE`, `ACL-TRACEABILITY-ROW-EVIDENCE-REPAIR` and `ACL-VER012-REVIEWER-DOUBLE-MIGRATION` `completed_verified`, and updated §9 to the measured result. | The canonical suite reached **0 failed, 5507 passed, 1 skipped** on a clean tree — the first fully green suite of the sprint. | `run_full_pytest.py` JSON with `dirty_tree: false`, `tree_changed_during_run: false` |
| H16 | Added `ACL-PYTEST-LEAK-GUARD-CONCURRENCY`. The sole remaining official-checks failure is a false positive, not a test failure. | `run_full_pytest.py::_repository_process_ids` matches **any** python process whose command line contains the repo root, with no parent/descendant check, so any concurrent python activity registers as a leak. Two runs leaked exactly as many PIDs as there were concurrent processes. | source read + measured PID correspondence |
| H17 | Added `ACL-REVIEW-REPAIR-SCOPE-MISMATCH` and rewrote the PF-02 diagnosis around it. | The blind reviewer reviews **13** section roots; the repair layer owns **5** authoring slots. 8 of 13 have no repair path, and `rereview_authorized` requires *every* finding addressed — so one finding in any of those 8 permanently disables that repository's repair loop. | `bounded-review-plan.json` (14 packets, 13 roots) vs `_SECTION_FIELDS` (5 slots) |
| H18 | Added `ACL-COMPOSITION-TRUNCATION-RETRY` — **fixed in cycle 2**, recorded under RDM-033 as a sibling site. | `plan_readme_composition` answered a truncated call with `_repair_hints()`' full vocabularies, making the one permitted retry longer than the attempt that had already overrun the 6000-token output ceiling. 3 repositories measured blocked on it. | 3 blocked-decision records truncating at 5184/7402/10698 chars |
| H19 | Added §4.3, the measured portfolio blocker leverage map. | Prioritisation in this plan had been asserted rather than measured. | all 31 `blocked-decision.json` records, 104 cumulative reproductions |
| H20 | **Independent verification refuted this cycle's PF-02 root cause.** Added `ACL-REPAIR-LOOP-BLIND-TO-DISCARDED-UNITS` as the real proximate cause and downgraded `ACL-REVIEW-REPAIR-SCOPE-MISMATCH` from P0 to P1, with a correction note on the card. Also added `ACL-PREMISE-GUARD-SUBSTRING-BRITTLENESS`. | `scope-and-limitations` routed correctly; the author ran (139 completion tokens); deterministic acceptance rejected **both** its units, leaving `units: []`, so the template re-emitted the rejected paragraph. `changed_operation_ids: []` was structurally forced by a single-operation document plan. | `assurance/section_authoring/cache/e6d5e5b6b642.json`, `planning/readme-document-plan.json` |
| H21 | Restored `reviewer_call_count_before/after == 1/2`, dropped a near-vacuous `>= 2` assertion, removed two dead merged-reviewer doubles, and derived the depth in CORE-041's cited long-path test. | The relational assertions were weaker than the literals they replaced (those counters are round counts, stable under bounded review); `>= 2` was cleared by a single round of ~18 packet calls; and the cited CORE-041 proof failed `assert 260 > 260` under the canonical short basetemp run serially. | independent verification, cycle 2 |
| H22 | Recorded the first fully green official-checks run: **exit 0, all ten checks OK, `leaked_process_ids: []`, 5509 passed / 0 failed, clean tree** at `3310543c6`. | Same code and commit as the run that failed; the only difference was that nothing else touched the repository. That is the proof for `ACL-PYTEST-LEAK-GUARD-CONCURRENCY`. | `official-checks-isolated.log` |
| H23 | **Checked CI for the first time this session and found it red on Linux since before the sprint.** Fixed both causes. | "Official checks pass" was a Windows-only claim. The Linux runners failed 6: five `test_external_fact_block_adapters` tests, because the `_snapshot()` fixture hardcodes `snapshot_root="C:/tmp/widget"` and `PurePosixPath('C:/tmp/widget').is_absolute()` is **False**; plus the same long-path test the verifier flagged, failing `assert 236 > 260` there. The derive-depth fix cleared the sixth (measured 6 → 5), and the portability fix reuses the idiom `test_curated_readme_evidence.py:1807` already established. | CI runs 33249439761, 33250041179 |
| H24 | Added `ACL-CAS-LOST-UPDATE-ON-LINUX` (P0) and recorded the final measured state. | The portability fix took CI 5 failed -> 1. The one remaining Linux failure is a concurrent-CAS test returning `['saved','saved']` where exactly one writer must see `stale` — untouched by this sprint, green on Windows, and a lost update on the property the durable-state model rests on. Final local official checks at `bde7d7d37`: **all ten OK, exit 0, 0 failed / 5509 passed, TREE CLEAN, `leaked_process_ids: []`**. | CI 33250290143/33250344649; `c2-official-checks-final-head-all-passed.log` |

---

## 2. Audit Findings Incorporated

Audit source: `plans/investigations/evidence/autonomous-convergence-loop/` at HEAD `68b503342`
(`REPORT.md`, `closeout-control.json`, `independent-verification.json`, `mission-contribution.json`,
13 `gate-outputs/` artifacts), plus a live read of the authoritative mission record on `origin`
performed while writing this file.

| ID | Finding | Class | Taskcard |
|---|---|---|---|
| A1 | Two tests still fail: VER-012 reviewer-double drift. Rewiring alone moves the failure to `independent_review_exception:StopIteration`. | verification gap | `ACL-VER012-REVIEWER-DOUBLE-MIGRATION` |
| A2 | `L8-PF-02` canary reached `DETERMINISTIC_VALIDATED` + factual `ACCEPT`, then `REJECT_REPAIRABLE` on four named visitor-quality findings. | implementation gap | `ACL-PF02-VISITOR-QUALITY-REPAIR` |
| A3 | `L8-PF-04` is `CLOSED` against `supervisor/proven_transaction_runner/`, which has no production importer, no external `run_proven_transaction` caller, and no `cli.py`/`commands*.py` reference. | claimed-unproven closure | `ACL-PF04-CLOSURE-RECONCILIATION` |
| A4 | `plans/master.md` Status and Build Checklist are stale (Decision #110 listed pending though `PROSE_QUALITY_CONTRACT_VERSION` exists); 674 lines against a 600 budget; `validate_compact_authority.py` red and unwired from CI. | planning/governance gap | `ACL-MASTER-AUTHORITY-COMPACTION` |
| A5 | Decisions #111 and #112 open; the structural cause behind 22 repositories carrying stale fact contracts. | implementation gap | `ACL-SCOPED-COMPOSITION-INVALIDATION`, `ACL-DURABLE-SHARED-RATCHET-TIER` |
| A6 | D1: new tests passed under bare `pytest`, failed under the canonical runner's short `--basetemp`. Claimed "5 → 2" was actually "5 → 4". | false-green risk | rule H7 + `ACL-VER012-REVIEWER-DOUBLE-MIGRATION` |
| A7 | D2: two sibling `rglob` sites carried the identical MAX_PATH defect; `_is_checksum_valid_intake_only_bundle` fails **open**. Repaired; the incomplete-fix pattern is not. | implementation gap | rule §10.3 |
| A8 | D3/D4/D5: three docstrings overstated safety ("fails closed", "no change outside long paths", "an unexpired claim is never touched"). Repaired. | overclaim | §11 |
| A9 | D6: `persist_evaluation` now raises `StateBackendError` where `evaluate` used to return. Latent, untested, on a read-mostly command. **Open.** | safety gap | `ACL-EVALUATE-FAILURE-SURFACE-TIGHTENING` |
| A10 | D7: equivalence narrowing has no staleness re-check and no negative-control test. **Open.** | verification gap | `ACL-EQUIVALENCE-NARROWING-STALENESS-CONTROL` |
| A11 | `traceability_matrix.py --check` exits 1 on `LLM-023`, `CORE-041`, `CORE-042` — `IMPLEMENTED` rows citing neither a pytest node nor a committed artifact. Pre-existing, keeps `run_official_checks.py` red. | evidence gap | `ACL-TRACEABILITY-ROW-EVIDENCE-REPAIR` |
| A12 | The bundle records `tree_clean_at_seal: false`; `mission-contribution.json` lists 1 of 4 commits; `independent-verification.json` cites "the session transcript". | evidence gap | `ACL-EVIDENCE-BUNDLE-RESEAL-ON-CLEAN-TREE` |
| A13 | The graph file's `status:` reads `TODO` for all ten cards while durable state holds CLOSED/REGRESSED/IN_PROGRESS. Any agent trusting the file draws wrong conclusions. | governance gap | `ACL-GRAPH-STATUS-FIELD-DIVERGENCE` |
| A14 | The claim on `L8-PF-02` expired `2026-08-29T08:54:02Z`; the mission is currently in the same stale-lease shape this sprint diagnosed. | state-management gap | `ACL-CLAIM-LEASE-HYGIENE` |
| A15 | G3/G4/G5/G6/G7 of the original plan were never started: typed violations, in-run repair loop, fitness + signature stores, `converge` scheduler, full sweep, replay-gated adaptation. | implementation gap | five cards, §5 |
| A16 | Three known defects were parked without rows: `poc` writes `README.md` unconditionally (Decision #100 violation), `portfolio-proof` discards the supervisor return code, the suspended `trusted_*` lane (~15 files). | backlog gap | `ACL-BACKLOG-ROW-CAPTURE` |
| A17 | Reading `runs/local-poc-state/state.git` for mission authority produced a confidently wrong answer that changed a conclusion. | method gap | §11 rule 4 |
| A18 | The container-registry failure looked external and was not — an unstarted Docker daemon, resolved locally under standing authority. | blocker-standard gap | §11 rule 6 |

---

## 3. Resolved / Preserved Work

Verified complete. **Do not redo, do not revert, do not re-litigate.** Each line is independently
confirmed by a lane that did not implement it.

| Item | Evidence | Status |
|---|---|---|
| `_inventory_valid()` MAX_PATH under-enumeration fixed — this had made `NO_OP_PROVEN` unreachable for the longest-named repositories. Verifier's own probe at a 271-char path: sealed 4, old `rglob` 2, old `False`, new `True`, tampered `False`. | `g1-…-root-causes.md`, `g5-…-findings-and-repairs.md` | completed_verified |
| Both sibling sites (`local_poc_snapshot_evidence.py::_is_checksum_valid_intake_only_bundle`, `evidence.py::assert_evidence_complete`) migrated to `enumerate_files()`. | D2 repair | completed_verified |
| `persist_evaluation()` now reconciles expired claims. Live proof on the `origin` record: `active_task_id=L8-PF-05` with a lease expired `2026-08-28T08:33:24Z` and empty eligibility → cleared, `REGRESSED` recorded, `eligible_tasks=L8-PF-02-COMPLETE-CANDIDATE-SEAM` at state_version 1792. | `g2-expired-claim-recovery-live-proof.md` | completed_verified |
| Check-battery manifest re-pinned and the CI blind spot closed (`validate_pinned_hash_dedicated_tests.py --all` wired into the `pinned-hashes` job). Verifier: exit 0 unmodified, exit 1 on temp-copy drift with the exact mismatch printed. | `g1-…`, `.github/workflows/ci.yml` | completed_verified |
| `verified_equivalence` producer/consumer divergence repaired in `claim_accountability_validation.py`. Verifier reverted the file in memory and reproduced `structured_fact_coordinates_exact failed`, and read the compensating checks. Load-bearing and symmetric, not a weakening. | D-series confirmations | completed_verified |
| Three overstated docstrings corrected; the `idea.md:158` citation corrected in production source, test, log shard and evidence file. | D3/D4/D5 + H4 | completed_verified |
| `GOV-0NN` placeholders replaced with GOV-033/GOV-034 in `install_hooks.py`, `validate_governance_write_lock.py`, `state/git_backend.py`. | commit `176b679db` | completed_verified |
| Container-runtime blocker self-resolved (Docker Desktop daemon started locally, server 28.4.0). Not an external blocker. | `g3-container-runtime-blocker-resolved.md` | completed_verified |
| Graph drift healed `true → false` through `--mission-action evaluate`. | `g0-baseline-repository-state.md` | completed_verified |
| Canonical suite moved 5 failed / 5498 passed → **2 failed / 5505 passed**. | `g6-official-checks-clean-tree.log` | completed_verified |
| Four commits on `main`, auto-pushed, tree clean, synced: `176b679db`, `65935a5ea`, `68b503342`, `8d29adc16`. | `git log` | completed_verified |

**Preserved architecture decisions** — in force, not reopened by this plan: #26 (supervise is the sole
runtime), #93 (compact authority budgets), #95 (delegation admission thresholds), #100 (no unconditional
product writes), #107 (post-commit auto-push), #110 (prose-quality contract version).

---

## 4. Unresolved Work Register

### 4.1 Authoritative mission state (read live from `origin`, not from the graph file)

Read at the time of writing via
`git fetch origin 'refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION:refs/inspect/mission' --force`
then `git cat-file -p refs/inspect/mission:state.json`.

| Graph card | File says | Durable state says | Plan-local cards |
|---|---|---|---|
| `L8-PF-00-CAMPAIGN-AUTHORITY-RECONCILIATION` | TODO | **CLOSED** | traceability, master compaction, graph-status, backlog, D6, D7 |
| `L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY` | TODO | **CLOSED** | — |
| `L8-PF-01A-QWEN-SECTION-ENGINE-INTEGRATION` | TODO | **CLOSED** | — |
| `L8-PF-02-COMPLETE-CANDIDATE-SEAM` | TODO | **IN_PROGRESS, claim expired `2026-08-29T08:54:02Z`** | lease hygiene, visitor-quality repair, repair loop |
| `L8-PF-03-SEALED-CANDIDATE-NO-OP` | TODO | **CLOSED** | fitness + signatures |
| `L8-PF-04-MINIMAL-GRAPH-RUNNER` | TODO | **CLOSED (unsupported)** | closure reconciliation, scheduler |
| `L8-PF-05-SEVEN-ECOSYSTEM-CANARIES` | TODO | **REGRESSED** | — (unblocks after PF-02) |
| `L8-PF-06-REGISTRY-FREEZE-AND-FACT-WARMUP` | TODO | TODO | — |
| `L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY` | TODO | **REGRESSED** | invalidation, ratchet tier, sweep, adaptation |
| `L8-PF-07-AUTONOMOUS-PUBLICATION-READINESS` | TODO | TODO | — |

Mission is **not** complete: `mission_complete = false`. Contract-valid lifecycle counters read
`facts_ready 1/34`, `no_op_proven 0/34`; `raw_lifecycle_progress` reads `facts_ready 22`,
`candidate_generated 3`, `deterministic_validated 2`, `agent_approved 1`, `no_op_proven 1`. The gap
between the two is the 22 repositories carrying stale fact contracts (A5).

### 4.2 Unresolved item summary

21 taskcards in §5. Cycle 2 closed three (`ACL-CLAIM-LEASE-HYGIENE`,
`ACL-TRACEABILITY-ROW-EVIDENCE-REPAIR`, `ACL-VER012-REVIEWER-DOUBLE-MIGRATION`) and added three
(`ACL-PYTEST-LEAK-GUARD-CONCURRENCY`, `ACL-REVIEW-REPAIR-SCOPE-MISMATCH`,
`ACL-COMPOSITION-TRUNCATION-RETRY` — the last already fixed).

### 4.3 Portfolio blocker leverage map (measured)

From all 31 `runs/readme-poc/*/blocked-decision.json` records, 104 cumulative live reproductions.
This replaces asserted prioritisation with counted prioritisation.

| Blocked cause | Repos | Note |
|---|---|---|
| **claim accountability** | **10** | all at `FACTS_READY`; **6 have exactly ONE blocking claim** |
| `product_truth_not_ready:BLOCKED_MISSING_EVIDENCE` | 6 | cannot establish product truth at all |
| `LLMTruncatedResponseError` (composition) | 3 | fixed in cycle 2 — `ACL-COMPOSITION-TRUNCATION-RETRY` |
| `LLMInfrastructureError` (forced tool call after retries) | 3 | provider reliability, not content |
| `composition.segmen…` | 2 | |
| bounded aggregate grounding failed | 1 | `api-reference` findings — the same scope mismatch as H17 |
| candidate persistence `ValueError` | 1 | stale stage receipt owned by a different `work_id` |
| compiled presentation invalid | 1 | |
| `check_unqualified` / `template.section` / `verified_omissions` / `presentation.forma` / `unauthorized prote` | 1 each | |

Status distribution: 20 `FACTS_READY`, 8 `BLOCKED_MISSING_EVIDENCE`, 1 `SYSTEM_FAILURE`,
1 `README_ASSESSED`, 1 `DETERMINISTIC_VALIDATION_FAILED`.

**Leverage reading.** Claim accountability is the single largest lever at 10 repositories, and six
of those need exactly one claim resolved. It is emphatically **not** a gate to loosen: a blocking
claim is a source claim the candidate failed to account for, which is the preservation property the
whole product rests on. The lever is to resolve or record those claims, never to stop counting them.

---

## 5. Taskcard Register

Every entry is executable. **No unresolved audit finding exists outside this register.**

Field vocabulary matches `TaskCardV1.audit_classification` where the graph has an equivalent:
`blocker` ⇒ `final_outcome_blocker`, `follow_up` ⇒ `future_hardening_work`.

### 5.1 Graph-insertion rule (budget control)

These are **plan-local** cards. Each maps to an existing graph card and is executed under that card's
claim. Insert a card into `level8-autonomous-mission-task-graph.yaml` **only** when a plan-local card
cannot map to any existing graph card, and then only if all of these hold:

- total graph taskcards after insertion ≤ **15** (`validate_compact_authority.py:229`);
- `READY` count never exceeds **5**;
- every one of `TaskCardV1`'s required fields is supplied — the model is `extra="forbid"`, and
  `execution_kind` in `{infrastructure, shared_repair}` additionally requires `infrastructure_admission`;
- `validate_plan_structure.py`, `validate_compact_authority.py` and
  `build_level8_requirement_taskcard_coverage.py --check` all exit 0 in the same commit;
- a paired `logs/<date>.md` line is appended in that same commit, not batched.

No insertion is required to start work. Current free slots: **5**.

---

### `ACL-CLAIM-LEASE-HYGIENE`

- **Title** Clear and re-establish the mission claim before any execution
- **Source audit finding** A14 — claim on `L8-PF-02` by `readme-agent-supervisor` expired `2026-08-29T08:54:02Z`
- **Why it matters** The mission is sitting in exactly the stale-lease shape this sprint diagnosed. Any agent that resumes without clearing it sees "no eligible work" and stops, or works without a valid lease and burns the attempt. Two burned attempts burn the task.
- **Current status** `completed_verified` (cycle 2) · **Priority** P0 · **Lane owner** `first-complete-candidate` (coordinator)
- **Dependencies** none — this is the first executable card
- **Required work** Run `--mission-action evaluate` (which now recovers expired claims), confirm eligibility is restored, then `--mission-action claim --mission-task-id L8-PF-02-COMPLETE-CANDIDATE-SEAM --mission-observer readme-agent-supervisor`. Record the narrowing immediately on claim. Re-claim before every 30-minute lease boundary; never let a lease lapse mid-work.
- **Required verification** `--mission-action status` shows `active_task_id=L8-PF-02-…`, a `claim_expires_at` in the future, and `graph_drift: false`
- **Required evidence** `gate-outputs/g0-claim-lease-reestablished.txt` — raw before/after `status` output with `state_version` on both sides
- **Acceptance criteria** Lease unexpired at the moment work begins; narrowing recorded; `graph_drift` false
- **Stop conditions** `graph_drift: true`; claim rejected by another live observer; lease cannot be held for a full work unit
- **Allowed actions** mission `evaluate`, `claim`, `status`; reading `origin` state refs
- **Forbidden actions** editing durable state by hand; forcing a claim held by another live observer; treating a local-store read as mission authority
- **Closeout rules** Release or transition the claim explicitly at end of cycle; never leave an expired lease behind for the next agent

### `ACL-PF02-VISITOR-QUALITY-REPAIR`

- **Title** Repair the four named visitor-quality findings and prove the immediate no-op
- **Source audit finding** A2 — `REJECT_REPAIRABLE` after one bounded repair
- **Why it matters** This is the live critical path. `L8-PF-02` is the only `IN_PROGRESS` card and everything from `L8-PF-05` onward depends on it. The candidate already clears deterministic validation and factual review; only prose quality stands between the portfolio and its first contract-valid acceptance.
- **Current status** `partially_done` · **Priority** P0 · **Lane owner** `first-complete-candidate`
- **Dependencies** `ACL-CLAIM-LEASE-HYGIENE`
- **Required work** Repair, on the Aspose.3D-FOSS-for-Python candidate: additional-examples `example_presentation` and `clarity`; scope-and-limitations `clarity` and `promotional_balance`. Re-run the transaction to `AGENT_APPROVED`, then prove the immediate complete-transaction no-op.
- **Required verification** Live `supervise --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python --execution-profile local_poc --bounded-verified-canary`; second consecutive run makes **zero** provider calls and produces a byte-identical candidate
- **Required evidence** Per-attempt reviewer verdict JSON; `llm_accounting=EXACT` call counts for both runs; the no-op replay record
- **Acceptance criteria** `AGENT_APPROVED` reached; `NO_OP_PROVEN` reached; the 30-point bar met without lowering it; contract-valid `no_op_proven` ≥ 1/34
- **Stop conditions** Repair would require widening the fact set (fail, do not repair); repair drifts toward validator-appeasement rather than truth; three materially different evidence-backed attempts exhausted
- **Allowed actions** prose repair through the existing bounded repair path; prompt-slot repair hints; re-running the canary
- **Forbidden actions** editing any rubric, gate, or acceptance threshold; hand-editing the candidate outside the pipeline; writing to any product repository or default branch
- **Closeout rules** The 30-point bar is immutable input; no threshold is lowered to raise a pass count; the no-op proof must be an actual replay, not an assertion

### `ACL-VER012-REVIEWER-DOUBLE-MIGRATION`

- **Title** Migrate the reviewer double to the current bounded review-packet contract
- **Source audit finding** A1, A6 — 2 remaining failures; naive rewiring yields `StopIteration`
- **Why it matters** These are the last two failures in the canonical suite. Until they are green, `run_official_checks.py` cannot exit 0 on pytest, and every later gate inherits an untrustworthy verification signal.
- **Current status** `completed_verified` (cycle 2) · **Priority** P0 · **Lane owner** `verification-baseline`
- **Dependencies** none (independent of the live lane)
- **Required work** Migrate `_RejectThenAcceptBlindReviewClient` to the current bounded review-packet contract **first**. Then rewire `test_local_poc_repairs_revalidates_and_rereviews_before_accepting` and `test_local_poc_byte_identical_repair_reroutes_before_rereview` from `build_live_merged_review_client` to `build_live_role_review_clients`, using the already-written `_fake_repair_role_clients`. Rewiring before migrating moves the failure to `independent_review_exception:StopIteration` — that was tried and reverted rather than left as a half-migration.
- **Required verification** `scripts/governance/run_full_pytest.py` — **the canonical runner, not a bare `pytest`** (rule H7). Target: 0 failed.
- **Required evidence** Canonical-runner log showing the pass count moving 2 failed → 0 failed, with the two node ids named
- **Acceptance criteria** Both tests pass under the canonical runner; no test skipped, `xfail`ed, or deleted to get there; the double exercises the reviewer that actually runs
- **Stop conditions** A failure turns out to be a real product regression rather than fixture drift — then exit this card and open a BACKLOG row instead of forcing green
- **Allowed actions** `tests/`, the reviewer double, fixture builders
- **Forbidden actions** `--no-verify`; skip/xfail/delete to reach green; weakening an assertion to accommodate the double
- **Closeout rules** Leaving a half-migration is worse than leaving the tracked failure; either complete it or record the exact resume condition

### `ACL-TRACEABILITY-ROW-EVIDENCE-REPAIR`

- **Title** Give `LLM-023`, `CORE-041`, `CORE-042` real traceability evidence
- **Source audit finding** A11 — `traceability_matrix.py --check` exits 1 on three `IMPLEMENTED` rows citing neither a pytest node nor a committed artifact
- **Why it matters** This is one of the ten official checks. It keeps `run_official_checks.py` red independently of any other work, so no gate in this plan can honestly report a clean official-checks pass until it is fixed. It is also the exact class of unevidenced closure this sprint exists to eliminate.
- **Current status** `completed_verified` (cycle 2) · **Priority** P0 · **Lane owner** `verification-baseline`
- **Dependencies** none
- **Required work** For each of the three rows (commits `3e4da1b88`, `67f66f6d9`, `f1efd83a2`, all predating this sprint): either cite a real pytest node id or a committed evidence artifact, or downgrade the row's status to what the evidence actually supports. Do not invent a citation.
- **Required verification** `.venv/Scripts/python plans/investigations/tools/traceability_matrix.py --check` exits 0
- **Required evidence** The check's own output before and after, plus the per-row justification
- **Acceptance criteria** Exit 0 with every cited node id actually collected by pytest and every cited artifact actually committed
- **Stop conditions** A row cannot be honestly evidenced **and** cannot be honestly downgraded — record why and stop; do not fabricate
- **Allowed actions** `plans/requirements.md`, `plans/requirements/catalog.jsonl`, `tests/`, evidence directories
- **Forbidden actions** citing a node id that does not exist; citing an uncommitted file; marking a row IMPLEMENTED on the strength of a summary
- **Closeout rules** Pin refresh and coverage rebuild land in the same commit as the catalog edit, with a paired `logs/<date>.md` line

### `ACL-EVIDENCE-BUNDLE-RESEAL-ON-CLEAN-TREE`

- **Title** Reseal the evidence bundle on a clean tree with a complete commit list
- **Source audit finding** A12 — `tree_clean_at_seal: false`; 1 of 4 commits listed; findings cited to a session transcript
- **Why it matters** A bundle sealed on a dirty tree cannot prove what it claims to prove: the checksums cover files that were not the committed state. A contribution record naming one of four commits understates the change surface. A citation to "the session transcript" is an orphan reference — the transcript is not a committed artifact and no later reader can retrieve it.
- **Current status** `completed_but_weakly_verified` · **Priority** P0 · **Lane owner** `verification-baseline`
- **Dependencies** none
- **Required work** Re-run `plans/investigations/tools/build_autonomous_convergence_loop_evidence.py` on a clean tree so `tree_clean_at_seal` is `true`. List all four commits in `mission-contribution.json`. Repoint `independent-verification.json` at `gate-outputs/g5-independent-verification-findings-and-repairs.md`. Rename that artifact so its `g5` prefix stops colliding with the scheduler gate (H10).
- **Required verification** `sha256sums.txt` verifies; `tree_clean_at_seal` is `true`; every `REPORT.md` citation resolves to a committed file in the bundle
- **Required evidence** The resealed bundle itself
- **Acceptance criteria** No orphan artifacts and no orphan citations, both directions (GOVERNANCE org rules 7 and 8)
- **Stop conditions** The tree cannot be made clean without discarding real work — commit first, then seal
- **Allowed actions** `plans/investigations/evidence/autonomous-convergence-loop/`, `plans/investigations/tools/`
- **Forbidden actions** hand-editing `sha256sums.txt`; sealing over uncommitted changes; deleting a gate artifact to make a citation resolve
- **Closeout rules** Seal is the last action of a cycle, after the final commit, never before

### `ACL-PF04-CLOSURE-RECONCILIATION`

- **Title** Integrate `proven_transaction_runner/` or reopen `L8-PF-04`
- **Source audit finding** A3 — CLOSED against machinery no production path can reach
- **Why it matters** A closed taskcard whose deliverable is unreachable is a false-green at the mission level: the graph reports capability the system does not have. It is also a hard prerequisite for the scheduler card, which would otherwise be built next to unreachable machinery that already claims to do the job.
- **Current status** `claimed_unproven` · **Priority** P0 · **Lane owner** `proven-transaction-runner`
- **Dependencies** none
- **Required work** Re-verify the three negative facts (no production importer outside the package; no `run_proven_transaction` caller outside the package and its tests; no `cli.py`/`commands*.py` reference). Then either wire the subtree into a real production path with a test that reaches it from a CLI entry point, or transition `L8-PF-04` out of `CLOSED` with a recorded reason.
- **Required verification** Either an import/call trace from a CLI entry point to `run_proven_transaction` exercised by a test, or a durable-state transition record with the reason
- **Required evidence** The three grep/import-trace results, dated, plus whichever outcome was chosen
- **Acceptance criteria** No graph card remains `CLOSED` against machinery with zero production reachability
- **Stop conditions** Integration would duplicate the existing supervise runtime — then reopen rather than integrate, and say so (Decision #26: supervise is the sole runtime)
- **Allowed actions** `src/readme_agent/supervisor/`, `tests/`, mission transitions
- **Forbidden actions** closing the card again on the strength of its own package-internal tests; deleting the subtree without recording the decision
- **Closeout rules** "Its own tests pass" is not reachability; the trace must start at a production entry point

### `ACL-MASTER-AUTHORITY-COMPACTION`

- **Title** Bring `plans/master.md` into budget and wire `validate_compact_authority.py` into CI
- **Source audit finding** A4
- **Why it matters** `master.md` is the single executable spec. While it is 674 lines against a 600 budget and lists a delivered decision as pending, it actively misinforms every agent that reads it first — and the validator that would catch this is red and not wired into CI, so the drift is invisible.
- **Current status** `partially_done` · **Priority** P0 · **Lane owner** `verification-baseline` (coordinator-owned file)
- **Dependencies** none
- **Required work** Update Status and Build Checklist to reflect that Decision #110's prose-quality ratchet is delivered (`PROSE_QUALITY_CONTRACT_VERSION` exists in `verification/prose_quality_cache.py`). Move detail to `plans/status.md`, `plans/roadmap.md` or `logs/` until `master.md` ≤ 600 lines. Regenerate the validator's semantic-hash pins and add it to `.github/workflows/ci.yml`.
- **Required verification** `validate_compact_authority.py` exit 0; `validate_plan_structure.py` exit 0; CI green on `main` including the new job
- **Required evidence** Line count before/after; validator output before/after; the CI run URL
- **Acceptance criteria** ≤ 600 lines, validator green, wired into CI, no Changelog entry lost
- **Stop conditions** Compaction would drop a Decision Ledger entry or a Changelog line — relocate, never delete
- **Allowed actions** `plans/master.md`, `plans/status.md`, `plans/roadmap.md`, `logs/`, `scripts/governance/`, `.github/workflows/ci.yml`
- **Forbidden actions** deleting ledger or changelog history; raising the 600 budget instead of meeting it
- **Closeout rules** Every `master.md` edit gets a paired `logs/<date>.md` line appended immediately, not batched (GOVERNANCE rule 6)

### `ACL-GRAPH-STATUS-FIELD-DIVERGENCE`

- **Title** Stop the graph file's `status:` field from being read as truth
- **Source audit finding** A13 — file says TODO for all ten; state holds CLOSED/REGRESSED/IN_PROGRESS
- **Why it matters** This single divergence produced the largest wrong conclusion in the whole sprint: an execution plan built on "nothing is promoted yet" when five cards were already closed and the real obstacle was a stale lease. It will do it again to the next agent.
- **Current status** `not_attempted` · **Priority** P1 · **Lane owner** `portfolio-proof-authority`
- **Dependencies** none
- **Required work** Either reconcile the file's `status:` to durable state on every `evaluate`, or annotate the field in-file as non-authoritative and make `--mission-action status` the only documented status source. Whichever is chosen, state it in `plans/GOVERNANCE.md` and in the graph file header.
- **Required verification** A check that fails when file status and durable status disagree, or a documented rule plus a test that the documentation matches the code path
- **Required evidence** The divergence table (§4.1) before, and the chosen mechanism after
- **Acceptance criteria** No agent can read the file's `status:` and reach a wrong conclusion without tripping something
- **Stop conditions** Auto-reconciliation would make the committed file churn on every evaluate — then choose annotation, and record why
- **Allowed actions** `plans/investigations/control/`, `plans/GOVERNANCE.md`, `src/readme_agent/supervisor/`, `scripts/governance/`
- **Forbidden actions** hand-editing durable state to match the file (the file is the derived side)
- **Closeout rules** Durable state is authority; the file is a checked-in convenience

### `ACL-DETERMINISTIC-VALIDATION-REPAIR-LOOP`

- **Title** Typed validation violations and a bounded in-run repair loop
- **Source audit finding** A15 — original G3, never started. Root finding: the dominant failure class hard-stops with no remediation path.
- **Why it matters** This is the structural fix behind the whole sprint. Today a deterministic-validation failure is a terminal `presentation_plan:blocked`, so "autonomy" is supplied by a human-driven coding agent, one failure class at a time. Typed violations plus bounded self-repair is what converts a hard stop into a retry the system can make itself.
- **Current status** `not_attempted` · **Priority** P0 · **Lane owner** `deterministic-repair-loop`
- **Dependencies** `ACL-VER012-REVIEWER-DOUBLE-MIGRATION` (trustworthy suite first)
- **Required work** (a) Convert `DocumentCandidateValidationV1.errors: list[str]` to `violations: list[ValidationViolationV1]`, keeping `errors` as a derived `@property` so every existing consumer and test keeps working; classify the ~40 production sites with `rule_id`, `section_slot`, `remediable`, `signature`. (b) Replace the hard `return` at `specialists/readme_presentation.py:793-813` with a bounded loop that renders a `RepairDirectiveV1` into the prompt's **existing** `$repair_hint` slot and reauthors only affected clusters via `author_and_persist_readme_sections()`, reusing `section_authoring_repair.py`'s `_REVIEW_SECTION_TO_AUTHORING_SLOT`. Budget 2 attempts (matches `MAX_PROSE_REPAIR_ATTEMPTS`). (c) Cache `verify_prose_quality` on `sha256(final_text) + PROSE_QUALITY_CONTRACT_VERSION`.
- **Required verification** Full canonical suite; existing `document_validation` tests pass **unmodified** against the derived `errors` property; `--no-deterministic-repair` reproduces today's behaviour byte-for-byte; ≥1 real repository that previously ended `presentation_plan:blocked` advances live
- **Required evidence** Before/after live outcome for that repository; the byte-identical flag-off comparison; provider call counts per attempt
- **Acceptance criteria** Every violation carries a stable non-colliding signature; the **full** validator re-runs each attempt, never just the failing check; non-remediable violations never reach the LLM
- **Stop conditions** Repair drifts candidates toward validator-appeasement rather than truth — disable by flag and reroute to fact-extraction work
- **Allowed actions** `readme/document_validation.py`, `specialists/readme_presentation.py`, `specialists/deterministic_repair.py` (new), `specialists/section_authoring_repair.py`, `tests/`, `runs/`, `logs/`
- **Forbidden actions** widening a fact set to make a repair succeed; any prompt text outside `prompts/`; lowering an acceptance threshold
- **Closeout rules** The 30-point bar is immutable input; a repair that would require weakening any gate fails closed

### `ACL-CANDIDATE-FITNESS-AND-FAILURE-SIGNATURES`

- **Title** Durable candidate-fitness and failure-signature stores
- **Source audit finding** A15 — original G4, never started
- **Why it matters** The project has no numerical answer to "did that change help?". Without it, prompt adaptation cannot be gated on anything but opinion, and every regression is discovered by narrative rather than by measurement.
- **Current status** `not_attempted` · **Priority** P0 · **Lane owner** `fitness-and-signatures`
- **Dependencies** `ACL-VER012-REVIEWER-DOUBLE-MIGRATION`. Runs concurrently with `ACL-DETERMINISTIC-VALIDATION-REPAIR-LOOP` (disjoint paths, §6).
- **Required work** Persist `CandidateQualityRecordV1` (deterministic 30-point rubric, term retention from `plans/investigations/tools/compare_candidate_parity.py`, capability-bullet count, blocking-violation count, provider calls, wall seconds) and `FailureSignatureRecordV1` (signature, `rule_id`, occurrences, affected repos, repair attempts/successes, attribution, resolution) through `GitStateBackend` under their own key namespaces — **not** `runs/`.
- **Required verification** One command prints the fitness trend across sweeps; a fresh clone recovers both stores; signature keys stable across reruns with unchanged input
- **Required evidence** The fresh-clone recovery transcript; a trend output across ≥2 sweeps
- **Acceptance criteria** Both stores durable and fresh-clone-recoverable; a signature marked `wontfix` does not re-enter the repair queue; a fitness record is never writable by the composer
- **Stop conditions** CAS write load unacceptable at 34-repo scale — degrade to batched per-sweep writes and record the measurement rather than falling back to `runs/`
- **Allowed actions** `evidence/`, `state/`, `supervisor/candidate_fitness.py` (new), `supervisor/failure_signature_store.py` (new), `plans/investigations/tools/`, `tests/`, `runs/`, `logs/`
- **Forbidden actions** writing either store to gitignored `runs/`; letting the component being graded write its own grade
- **Closeout rules** Additive namespaces only; deleting the refs must restore prior behaviour

### `ACL-CONVERGENCE-SCHEDULER`

- **Title** `readme-agent converge` — budgeted, starvation-free, crash-isolated sweeps
- **Source audit finding** A15 — original G5, never started
- **Why it matters** The last real sweep dispatched 34 and finished 1: 27 repositories ended `NOT_STARTED_DEADLINE_EXPIRED` against a 1046s batch deadline at concurrency 2, while one repository consumed 1265s alone. The current driver is a bash loop whose control flow reads log text. Until scheduling is typed and budgeted, portfolio convergence is not reachable regardless of per-repository quality.
- **Current status** `not_attempted` · **Priority** P0 · **Lane owner** `proven-transaction-runner`
- **Dependencies** `ACL-PF04-CLOSURE-RECONCILIATION`, `ACL-DETERMINISTIC-VALIDATION-REPAIR-LOOP`, `ACL-CANDIDATE-FITNESS-AND-FAILURE-SIGNATURES`
- **Required work** Per-repository wall and provider budgets; starvation-free ordering (least-recently-attempted first); crash isolation at the repository boundary so one failure never halts the fleet; a typed `SweepReportV1` replacing log-text control.
- **Required verification** A dry-run sweep shows **zero** `NOT_STARTED_DEADLINE_EXPIRED`; kill a sweep mid-flight and prove resume does not re-run completed repositories and loses no fitness or signature record
- **Required evidence** `SweepReportV1` for the dry run; the interrupt/resume transcript
- **Acceptance criteria** Every repository ends in a typed terminal state; no repository can be starved by a slow peer; control flow reads structured data, never log text
- **Stop conditions** Budgets cannot be met without lowering an acceptance threshold — record and stop
- **Allowed actions** `supervisor/`, `cli.py`, `tests/`, `runs/`, `logs/`
- **Forbidden actions** deleting `run_gate_a_local_poc_portfolio_loop.sh` before the sweep card passes twice; grepping log text for control decisions
- **Closeout rules** The bash driver is retained as a shim until `ACL-FULL-PORTFOLIO-SWEEP` passes twice

### `ACL-SCOPED-COMPOSITION-INVALIDATION`

- **Title** Per-repository composition-plan invalidation (Decision #111)
- **Source audit finding** A5 — 22 repositories carrying stale fact contracts
- **Why it matters** This is why every contract-valid counter reads 0/34 while raw progress reads 22 facts-ready. A single global `document_template_hash()` change re-stales the entire portfolio, so accepted work is destroyed by unrelated edits faster than it accumulates. It is the direct structural cause of the 3/33 → 1/34 regression.
- **Current status** `not_attempted` · **Priority** P0 · **Lane owner** `readme-portfolio-delivery`
- **Dependencies** `ACL-CANDIDATE-FITNESS-AND-FAILURE-SIGNATURES`
- **Required work** Key composition-plan reuse on the recorded **per-repository** dependency-set hash. Land only after a **one-full-pass dual-hash shadow period**. The global `document_template_hash()` remains a non-blocking provenance label and full-fleet-revalidation trigger.
- **Required verification** Change a file outside a repository's recorded dependency set → plan reused; inside → invalidation fires. Both proven live, not synthetically.
- **Required evidence** The dual-hash shadow-period comparison; both invalidation cases on a real repository
- **Acceptance criteria** No accepted repository is invalidated by an edit outside its own dependency set; every in-scope edit still invalidates
- **Stop conditions** The shadow period shows the two hashes disagreeing in a way that would have wrongly preserved an accepted candidate — stop and root-cause before landing
- **Allowed actions** `readme/`, `supervisor/`, `state/`, `tests/`, `runs/`, `logs/`
- **Forbidden actions** landing without the shadow pass; making the global hash blocking again
- **Closeout rules** `invalidation_scope` in each edited manifest is honoured; dependants are reopened, never silently left accepted

### `ACL-DURABLE-SHARED-RATCHET-TIER`

- **Title** Promote ratchets and blocked-decision caches out of gitignored `runs/` (Decision #112)
- **Source audit finding** A5
- **Why it matters** Claim-disposition ratchets and blocked-decision records are load-bearing skip logic, but they live as plain JSON under gitignored `runs/`: not CAS-governed, not restored by CI, lost on a fresh clone. A sweep on a clean checkout re-litigates every known-blocked repository from zero.
- **Current status** `not_attempted` · **Priority** P1 · **Lane owner** `readme-portfolio-delivery`
- **Dependencies** `ACL-CANDIDATE-FITNESS-AND-FAILURE-SIGNATURES` (same backend pattern)
- **Required work** Route ratchet and blocked-decision state through `GitStateBackend` after a 34-repo load characterisation.
- **Required verification** Fresh-clone recovery of both stores; measured CAS write load at 34-repo scale
- **Required evidence** The load characterisation numbers; the fresh-clone recovery transcript
- **Acceptance criteria** A fresh clone reproduces the same skip decisions as the working checkout
- **Stop conditions** Measured write load makes sweeps slower than the caching saves — record the measurement and choose batching, not reversion
- **Allowed actions** `state/`, `supervisor/`, `tests/`, `runs/`, `logs/`
- **Forbidden actions** leaving load-bearing skip logic in gitignored paths once a durable tier exists
- **Closeout rules** Additive namespaces; deleting the refs restores prior behaviour

### `ACL-FULL-PORTFOLIO-SWEEP`

- **Title** One full 34-repository sweep inside budget
- **Source audit finding** A15 — original G6, never started
- **Why it matters** This is the mission's actual measurement. Everything before it is preparation; nothing before it proves portfolio convergence.
- **Current status** `not_attempted` · **Priority** P1 · **Lane owner** `readme-portfolio-delivery`
- **Dependencies** `ACL-CONVERGENCE-SCHEDULER`, `ACL-SCOPED-COMPOSITION-INVALIDATION`
- **Required work** Run one full sweep across the registry. Then run a second consecutive sweep on unchanged inputs.
- **Required verification** Completion inside declared budget; zero `NOT_STARTED_DEADLINE_EXPIRED`; every repository in a typed terminal state; accepted count **not below** the recorded baseline; second sweep makes zero new provider calls for accepted repositories and produces byte-identical candidates
- **Required evidence** Both `SweepReportV1` records; per-sweep provider spend; the accepted-count delta against baseline
- **Acceptance criteria** All of the above, measured — not inferred from a summary
- **Stop conditions** Accepted count falls below baseline — record and halt; **do not auto-tune to make the number look better**
- **Allowed actions** running sweeps; recording results
- **Forbidden actions** adjusting thresholds, budgets, or the registry between the two sweeps; excluding a failing repository from the denominator
- **Closeout rules** Report the number that occurred, including when it is worse than the last one

### `ACL-PROMPT-ADAPTATION-REPLAY-GATE`

- **Title** Replay-gated prompt self-adaptation with auto-revert (conditional)
- **Source audit finding** A15 — original G7, never started
- **Why it matters** This is the part of the original goal — "tweak its own prompts, adjust its own working" — that nothing else in the plan delivers. It is also the single most dangerous card here, because a system that edits its own prompts without a trustworthy offline score will optimise for whatever it can measure.
- **Current status** `not_attempted` · **Priority** P1 · **Lane owner** `prompt-adaptation`
- **Dependencies** `ACL-FULL-PORTFOLIO-SWEEP`, `ACL-CANDIDATE-FITNESS-AND-FAILURE-SIGNATURES`
- **Required work** (a) Capture a frozen, versioned replay corpus of real `(packet → response)` pairs so a prompt change is scorable offline at zero provider cost. (b) `AdaptationController`: attribute a signature cluster to one prompt, draft a `PromptCandidateV1` (real `prompts/*.yaml` diff with a `version` bump), replay before/after, auto-apply **iff strictly improved with zero regressions**; auto-revert on next-sweep fitness regression.
- **Required verification** The corpus reproduces a known-good baseline; scoring uses the **deterministic** rubric and term-retention metrics, never a model judge; `check_prompt_hygiene.py` stays clean
- **Required evidence** Corpus version and baseline reproduction; before/after replay scores per applied change; one demonstrated auto-revert
- **Acceptance criteria** One prompt change per sweep so attribution stays unambiguous; every application and revert lands as an ordinary commit with a `logs/` line
- **Stop conditions** **If the replay corpus cannot reproduce a known-good baseline, stop at the corpus and report. Do not ship auto-apply on a weak signal.**
- **Allowed actions** `prompts/`, `llm/`, `supervisor/adaptation/` (new), `tests/`, `runs/`, `logs/`
- **Forbidden actions** writing to `readme/`, `presentation/`, `validation/`, `verification/`, or any rubric or gate definition — **the adaptation layer may never edit what grades it**. Prompt text outside `prompts/` is forbidden repository-wide.
- **Closeout rules** A candidate that improves its target signature but regresses **any** other corpus scenario is rejected; a candidate touching a forbidden path is rejected before replay

### `ACL-EVALUATE-FAILURE-SURFACE-TIGHTENING`

- **Title** Bound the widened `StateBackendError` surface on `evaluate`
- **Source audit finding** A9 / D6 — left open deliberately by the independent verifier
- **Why it matters** `evaluate` is a read-mostly command a monitoring loop calls often. It can now raise where it used to return normally: `active_task_id` set, lease expired, that task's status not `IN_PROGRESS`. Latent rather than demonstrated — `transition_task` clears `active_task_id` on any non-`IN_PROGRESS` transition — but real, and untested.
- **Current status** `follow_up` · **Priority** P1 · **Lane owner** `verification-baseline`
- **Dependencies** none
- **Required work** Construct the state directly (bypassing `transition_task`) and decide: either make the reconciliation tolerant on `evaluate` and strict on `claim`, or keep it strict and document the raise as intended. Add the missing test either way.
- **Required verification** A test that reaches the state and asserts the chosen behaviour
- **Required evidence** The constructed-state reproduction, before and after
- **Acceptance criteria** The behaviour is chosen deliberately and covered by a test, not left latent
- **Stop conditions** none — this is bounded work
- **Allowed actions** `supervisor/mission_control.py`, `tests/`
- **Forbidden actions** closing this by editing the docstring alone
- **Closeout rules** A documented raise is acceptable; an undocumented untested one is not

### `ACL-EQUIVALENCE-NARROWING-STALENESS-CONTROL`

- **Title** Staleness re-check and negative control for `verified_equivalence` narrowing
- **Source audit finding** A10 / D7 — left open deliberately by the independent verifier
- **Why it matters** The producer raises `ValueError` on a stale resolution (span/content-hash mismatch) **before** narrowing; the validator applies the narrowing with no staleness re-check. And no test exists proving an equivalence record that omits an *in-scope* coordinate is still rejected — so the narrowing's safety rests on reading the code, not on a control.
- **Current status** `follow_up` · **Priority** P1 · **Lane owner** `verification-baseline`
- **Dependencies** none
- **Required work** Add the staleness re-check on the validator side. Add a negative control proving an in-scope omission is still rejected.
- **Required verification** The negative control fails against a deliberately narrowed-too-far record and passes against a correct one
- **Required evidence** Both control outcomes
- **Acceptance criteria** The narrowing is proven symmetric by a test, not by inspection
- **Stop conditions** none — bounded work
- **Allowed actions** `readme/claim_accountability_validation.py`, `readme/claim_accountability.py`, `tests/`
- **Forbidden actions** widening the narrowing to make a test pass
- **Closeout rules** A negative control that cannot fail is not a control (§11 rule 3)

### `ACL-PYTEST-LEAK-GUARD-CONCURRENCY`

- **Title** Stop the pytest leak guard from failing on unrelated concurrent processes
- **Source audit finding** Cycle 2. Official checks exit 1 with `bounded full pytest: FAILED (exit 1)` while that same run records `outcome_counts: {failed: 0, passed: 5507, skipped: 1}` and `exit_code: 0`. The sole cause is `leaked_process_ids`.
- **Why it matters** This is the only thing standing between this project and its first green official-checks run, and it fails for a reason unrelated to code quality. `run_full_pytest.py::_repository_process_ids` matches **any** python/pytest process whose command line contains the repository root, with no parent or descendant check at all — so a second agent, a second terminal, or an IDE test runner is counted as a leak. Measured twice: a run during concurrent diagnostics leaked 2 PIDs, and a run during the independent-verification lane leaked exactly the 2 PIDs that lane was running.
- **Current status** `blocker` · **Priority** P0 · **Lane owner** `verification-baseline`
- **Dependencies** none
- **Required work** Make the guard distinguish descendants of the launched pytest process from unrelated concurrent processes. **Do not simply delete the guard** — real subprocess leaks are what it exists to catch. Preferred shape: keep the before/after diff, add ancestry, fail only on descendants, and report unrelated concurrent processes informationally.
- **Required verification** Two controls: the guard still fails on a synthetic real leak (a test that spawns a surviving child), and passes with an unrelated concurrent python process running against the repository.
- **Required evidence** Both control outcomes, plus one official-checks run at exit 0 with a clean tree
- **Acceptance criteria** `run_official_checks.py` exits 0 on a clean tree with nothing else running, and still exits 1 on a genuine leak
- **Stop conditions** If descendants cannot be tracked reliably on Windows after a real attempt, record the measurement and add an explicit opt-out flag for known-concurrent runs rather than removing the check
- **Allowed actions** `scripts/governance/run_full_pytest.py`, `tests/`
- **Forbidden actions** deleting the check; downgrading it to advisory; "fixing" it by promising to run tests serially forever
- **Closeout rules** A guard that cannot fail is not a guard — the synthetic-leak control is mandatory

### `ACL-REVIEW-REPAIR-SCOPE-MISMATCH`

- **Title** The reviewer can reject 13 section roots; the repair layer owns 5
- **Source audit finding** Cycle 2, PF-02 root cause, corroborated by the `Aspose.3D-FOSS-for-.NET` bounded-grounding failure on `api-reference`
- **Why it matters** This is the concrete mechanism behind "the dominant failure class hard-stops with no remediation path". `bounded-review-plan.json` shows 14 visitor packets across **13** section roots. `section_authoring_repair.py::_REVIEW_SECTION_TO_AUTHORING_SLOT` maps **eight** keys onto the **5** slots `_SECTION_FIELDS` actually defines (`summary`, `key_capabilities`, `installation`, `quick_start`, `scope_and_limitations`). The other 8 roots — `additional-examples`, `api-reference`, `at-a-glance`, `dependencies`, `development-and-testing`, `documentation-resources`, `license`, `navigation` — have no section-authoring repair route, `_slot()` returns `None`, and those findings are dropped from `by_slot` silently. Because `rereview_authorized = bool(findings) and not unresolved_ids` requires **every** finding addressed, a single unroutable finding permanently disables that repository's repair loop — and the reroute reason names none of this, which is why it presents as a generic byte-identical repair.
- **Current status** `blocker` · **Priority** P1 (**downgraded from P0** — see the correction below) · **Lane owner** `deterministic-repair-loop`
- **Dependencies** none
- **CORRECTION (independent verification, cycle 2).** This card was originally written as PF-02's root cause. **It is not.** It is a real defect, but fixing it alone would not have unblocked PF-02, and doing it first would have burned a cycle. The proximate cause is `ACL-REPAIR-LOOP-BLIND-TO-DISCARDED-UNITS` below: `scope-and-limitations` *did* route to a slot, the author *was* called, and post-call deterministic acceptance discarded every unit. Do that card first. Priority downgraded accordingly.
- **Required work** Make the mismatch explicit and bounded. Either give the unowned roots a repair route, or make an unroutable finding a distinct, named, surfaced outcome instead of a silent drop. Note that `at-a-glance` *is* repairable through the composition re-planning path rather than section authoring, so the two repair mechanisms must be considered together before declaring any root unowned — the count of 8 is an upper bound on "no section-authoring route", not a proven count of "no route at all".
- **Required verification** A repository whose only rejection is in an unowned root produces a reroute reason that names the unroutable finding and its root; a repository whose rejections are all in owned roots still repairs
- **Required evidence** Before/after reroute reasons for both cases
- **Acceptance criteria** No finding is silently dropped; the operator can tell "we tried and failed" from "we had no way to try"
- **Stop conditions** Giving all 8 roots authoring slots turns out to be a composition redesign — then ship the diagnosis and reroute the redesign to `ACL-DETERMINISTIC-VALIDATION-REPAIR-LOOP`
- **Allowed actions** `specialists/section_authoring_repair.py`, `specialists/readme_review_repair*.py`, `tests/`
- **Forbidden actions** making `rereview_authorized` ignore unaddressed findings — that would accept prose the reviewer rejected, which is lowering the bar
- **Closeout rules** The reviewer's scope is not narrowed to match the repair layer; the mismatch is closed from the repair side or surfaced honestly

### `ACL-REPAIR-LOOP-BLIND-TO-DISCARDED-UNITS`

- **Title** The repair loop cannot tell "author produced nothing" from "acceptance threw it away"
- **Source audit finding** Independent verification, cycle 2 — it refuted this sprint's published PF-02 root cause and supplied this one. Confirmed directly against the bundle before acceptance.
- **Why it matters** **This is PF-02's actual proximate cause**, and it is not the slot gap. `scope-and-limitations` routes correctly to a repair slot. The repair ran: `assurance/section_authoring/cache/e6d5e5b6b642.json` (the repair variant — its own cache key, because `packet.canonical_hash()` covers the mutated `section_objective`) records `logical_call_count: 1`, 139 completion tokens, and **two** entries in `deterministically_rejected_unit_sha256`, leaving `units: []` and one `omitted` reason: "Authored unit crossed the deterministic format-rendering boundary." The deterministic template then owns the section by design and re-emits the exact paragraph the reviewer rejected. The canonical entry `ab1ea94f8297.json` has the same shape, so that section has *never* carried authored prose in this bundle. Meanwhile `changed_operation_ids: []` was structurally forced regardless: `planning/readme-document-plan.json` holds exactly **one** operation, `readme.verified-template.compile`, so that field carries no signal at all here. The loop observes only a byte-identical candidate and reroutes as though nothing was attempted.
- **Current status** `blocker` · **Priority** P0 · **Lane owner** `deterministic-repair-loop`
- **Dependencies** none — do this **before** `ACL-REVIEW-REPAIR-SCOPE-MISMATCH`
- **Required work** Give the repair receipt a signal distinguishing (a) no repair attempted, (b) author called and produced units that deterministic acceptance rejected, (c) author called and produced accepted units that did not change the compiled candidate. Surface which occurred in the reroute reason. Separately, `changed_operation_ids` must not be treated as evidence of repair inaction when the document plan has a single monolithic compile operation.
- **Required verification** A repository whose authored units are all rejected produces a reroute reason naming that, distinct from a genuine no-change; the single-operation case does not silently read as "nothing changed"
- **Required evidence** Before/after reroute reasons for a rejected-units case and a true no-change case
- **Acceptance criteria** An operator can tell "we tried and acceptance refused it" from "we never tried"
- **Stop conditions** If the deterministic format-rendering boundary is itself the thing that must change, that is a separate card — do not widen it here to make a repair land
- **Allowed actions** `specialists/readme_repair_validation.py`, `specialists/readme_review_repair*.py`, `specialists/section_cluster_authoring.py`, `tests/`
- **Forbidden actions** relaxing deterministic acceptance so units survive; treating a rejected unit as accepted
- **Closeout rules** The fix is a signal, not a loosened gate

### `ACL-CAS-LOST-UPDATE-ON-LINUX`

- **Title** Two concurrent CAS writers both reported `saved` against the same expected version
- **Source audit finding** CI, cycle 2 (runs 33250290143 and 33250344649, both on `main`)
- **Why it matters** `tests/integration/test_state_git_backend_local_parallel.py::test_separate_process_workspaces_preserve_same_ref_cas` spawns two processes that each call `save(..., expected_version=1)` on the same ref and asserts `sorted(outcomes) == ["saved", "stale"]`. On the Linux runners it returned `['saved', 'saved']`. `_cas_worker` returns `SaveResult.outcome` directly with no exception handling, so that is `save()` genuinely reporting success twice against a version that could only be current for one of them — a lost update on the compare-and-set that the entire durable-state model rests on. `save()` decides staleness from `_fetch_remote_sha()` (`git_backend.py:559`), so a fetch that does not observe the peer's just-pushed ref would produce exactly this.
- **Current status** `blocker` · **Priority** P0 · **Lane owner** `verification-baseline`
- **Dependencies** none. **Not caused by anything in this sprint** — nothing in these nine commits touches the state backend.
- **Required work** Reproduce on Linux, then determine whether the fetch underlying the staleness check can observe a stale ref, and whether the guarantee needs the push's own rejection rather than a pre-read comparison. Do not "fix" the test.
- **Required verification** The reproduction runs many times without a false `saved`; a deliberately induced concurrent write is still rejected
- **Required evidence** The failing CI logs, a local Linux reproduction, and the before/after outcome distribution over repeated runs
- **Acceptance criteria** Two concurrent writers against the same expected version never both report `saved`
- **Stop conditions** If it proves to be pure runner timing with no reachable lost update, say so with the measurement — but do not assume that; it passed twice and failed twice on the same day
- **Allowed actions** `src/readme_agent/state/git_backend.py`, `tests/integration/`
- **Forbidden actions** relaxing or deleting the assertion; marking it flaky without a measurement
- **Closeout rules** This is the property every durable store in this project depends on; "probably a flake" is not a closure

### `ACL-PREMISE-GUARD-SUBSTRING-BRITTLENESS`

- **Title** The producer/reviewer premise guard is a substring allowlist that silently no-ops
- **Source audit finding** Independent verification, cycle 2
- **Why it matters** `specialists/review_standard_premises.py::validate_configured_standard_premise` already contains a `claims_workflow_preview_is_raw` branch built for exactly the deterministic-`workflow_preview` conflict this sprint hit. Run against this cycle's four real findings it matched **none of them**: the reviewer wrote "First paragraph **is** a raw task list", the allowlist carries "read**s like** a raw task list". A substring allowlist against free-form model prose degrades to a no-op on one verb of drift, and does so silently — the guard reports nothing rather than reporting that it could not decide.
- **Current status** `follow_up` · **Priority** P1 · **Lane owner** `deterministic-repair-loop`
- **Dependencies** none
- **Required work** Either match on structure rather than phrasing, or make a non-match an explicit "guard could not evaluate" signal instead of silent success.
- **Required verification** The four recorded findings from this cycle are matched, or explicitly reported as unevaluable
- **Required evidence** The guard's output against those four findings, before and after
- **Acceptance criteria** No silent no-op: every input either matches, mismatches, or is reported unevaluable
- **Stop conditions** none — bounded work
- **Allowed actions** `specialists/review_standard_premises.py`, `tests/`
- **Forbidden actions** adding this cycle's exact four phrasings to the allowlist and calling it fixed
- **Closeout rules** A guard that cannot say "I don't know" will keep reporting false confidence

### `ACL-COMPOSITION-TRUNCATION-RETRY`

- **Title** A truncated composition call must retry shorter, not longer *(fixed in cycle 2)*
- **Source audit finding** Cycle 2 sibling-site sweep of RDM-033
- **Why it matters** `plan_readme_composition` caught `LLMTruncatedResponseError` but answered it with `_repair_hints()`' full section-decision, phrase-option and diagram-role vocabularies, so the single retry `MAX_AUTHORING_ATTEMPTS = 2` allows was strictly longer than the attempt that had already overrun the client's 6000-token output ceiling. Three repositories were blocked on it.
- **Current status** `completed_verified` · **Priority** P1 · **Lane owner** `deterministic-repair-loop`
- **Dependencies** none
- **Required work** *(done)* Truncation gets its own retry branch with a fixed-size brevity directive (`agentic_composition_inputs.py::truncation_repair_hint`), withholding the repository-sized blocks while **keeping** the authoritative diagram role vocabulary.
- **Required verification** *(done)* Positive test plus negative control; non-vacuity proved by disabling the branch in place; impacted sweep 123 passed; mypy clean
- **Required evidence** *(done)* Commit `37b7a7517`; RDM-033 evidence marker `RDM033-COMPOSITION-CALL-SIBLING-001`
- **Acceptance criteria** *(met)* Retry contains the brevity directive, omits `_repair_hints()`' blocks, retains the role vocabulary, and grows by a bounded amount
- **Stop conditions** n/a
- **Allowed actions** `readme/agentic_composition*.py`, `tests/`
- **Forbidden actions** raising `max_tokens` as the fix — `agentic_composition` hardcodes 6000 where the module default is 8000, but changing it alters output for every repository and is a separate, fleet-wide decision
- **Closeout rules** Live recovery of a real truncation is still pending a natural recurrence, exactly as RDM-033's original entry records for its own site

### `ACL-BACKLOG-ROW-CAPTURE`

- **Title** Open BACKLOG rows for three known non-blocking defects
- **Source audit finding** A16
- **Why it matters** GOV-014: a non-blocking issue found here gets an open row, or it is lost. All three are real and all three are currently untracked.
- **Current status** `follow_up` · **Priority** P2 · **Lane owner** `portfolio-proof-authority`
- **Dependencies** none
- **Required work** Open rows for: (1) `poc` writes `README.md` unconditionally at `commands_poc.py:617`, violating Decision #100; (2) `portfolio-proof` discards the supervisor's return code at `full_pipeline_modes.py:89`; (3) the suspended `trusted_*` lane (~15 files) needs removal or quarantine.
- **Required verification** `validate_plan_structure.py` exit 0 after the edits
- **Required evidence** The three rows, each citing the file and line
- **Acceptance criteria** Three open rows with exact locations
- **Stop conditions** none
- **Allowed actions** `plans/backlog-post-poc.md`, `logs/`
- **Forbidden actions** fixing these inline instead of rowing them — they are out of scope for this sprint and would widen it
- **Closeout rules** Paired `logs/<date>.md` line appended immediately

---

## 6. Lane Ownership

The coordinator is `readme-agent-supervisor`.

**Coordinator-exclusive, never written by a worker** (GOVERNANCE rule 19): `plans/**`, `logs/**`, the
mission graph, `plans/requirements/catalog.jsonl`, all task transitions, all commits, aggregate evidence.

| Lane | Exclusive paths | Cards | Overlap |
|---|---|---|---|
| `first-complete-candidate` | live canary execution; candidate bundles under `runs/readme-poc/` | lease hygiene, visitor-quality repair | none |
| `verification-baseline` | `tests/`, `scripts/governance/`, `.github/workflows/ci.yml`, `plans/master.md`, `supervisor/mission_control.py`, `readme/claim_accountability*.py` | VER-012, traceability, reseal, master compaction, D6, D7 | none |
| `deterministic-repair-loop` | `readme/document_validation.py`, `specialists/readme_presentation.py`, `specialists/deterministic_repair.py`, `specialists/section_authoring_repair.py` | repair loop | **none** with `fitness-and-signatures` |
| `fitness-and-signatures` | `evidence/`, `state/`, `supervisor/candidate_fitness.py`, `supervisor/failure_signature_store.py`, `plans/investigations/tools/` | fitness + signatures | **none** with `deterministic-repair-loop` |
| `proven-transaction-runner` | `supervisor/proven_transaction_runner/`, `cli.py` converge entry | PF-04 closure, scheduler | none |
| `readme-portfolio-delivery` | sweep execution, registry revision records | invalidation, ratchet tier, sweep | none |
| `prompt-adaptation` | `prompts/`, `llm/`, `supervisor/adaptation/` | adaptation | none |
| `portfolio-proof-authority` | graph header, `plans/GOVERNANCE.md`, `plans/backlog-post-poc.md` | graph-status divergence, backlog rows | coordinator-serialised |

**Shared, coordinator-serialised**: `tests/unit/`, `tests/integration/`, `runs/`, `logs/`. Commits are
serialised by the coordinator; two lanes never commit concurrently.

**Only one genuinely concurrent pair exists**: `deterministic-repair-loop` ∥ `fitness-and-signatures`
(verified-disjoint file ownership). If delegation actually occurs, write
`runs/multi-agent/L8-PF-02-COMPLETE-CANDIDATE-SEAM/execution-plan.json` first, recording each worker's
objective, exclusive allowed paths, forbidden shared paths, focused checks, evidence destination,
timing and measured throughput. **If no useful independent lane exists, stay serial — no ceremonial
role records.** Delegation is admitted only while measured speedup ≥ 1.5× and coordination overhead
≤ 25% (Decision #95).

**Independent verification is mandatory** before closing any card carrying a live proof, and before
sprint closeout. **The verifier must not have authored the work it accepts** — this is not optional,
and it found six defects in the last cycle, one of them blocking.

---

## 7. Gate Contract

A gate that fails **stops the run at that gate**. It never advances on a partial result. Each gate
ends with a commit (which auto-pushes, Decision #107) and a `logs/<date>.md` line appended immediately.

| Gate | Cards | Entry | Exit (all required) | On fail | Last outcome |
|---|---|---|---|---|---|
| **G0 Preflight** | lease hygiene | — | `git status --porcelain` recorded; `mission_resume_capsule.py --check` exit 0 (regenerate if stale); mission `status` captured **from `origin`**; `GH_TOKEN` liveness re-verified via the `env -u GH_TOKEN -u GITHUB_TOKEN -u GITHUB_PAT gh auth token` recipe; claim held with an unexpired lease; `graph_drift: false` | Halt; report | **PASS** |
| **G1 Verification baseline** | VER-012, traceability, reseal, master compaction | G0 | `run_official_checks.py` exit 0 **on a clean, unchanged tree**; `validate_pinned_hashes.py` 0; `validate_compact_authority.py` 0; `master.md` ≤ 600 lines; CI green on `main` | Halt; do not enter G2 | **PARTIAL** — 5 failures → 2; pytest and traceability still red |
| **G2 Authority reconciliation** | PF-04 closure, graph-status divergence, backlog rows | G1 | No graph card `CLOSED` against unreachable machinery; file-vs-state divergence resolved or annotated; three BACKLOG rows open; `validate_plan_structure.py` 0; coverage `--check` 0. **Graph insertion only under §5.1.** | Revert the authority commits; halt | **NOT STARTED** |
| **G3 Repair loop** | repair loop | G2 + claim held | Typed violations landed; loop landed behind `--no-deterministic-repair`; prose-quality cache landed; ≥1 previously-blocked repository advances live; negative controls pass | Disable the flag, keep typed violations, halt | **NOT STARTED** |
| **G4 Fitness** | fitness + signatures | G2 + claim held; **may run concurrently with G3** | Both stores durable through `GitStateBackend`; fresh-clone recovery proven; trend command works | Halt before G5 | **NOT STARTED** |
| **G5 Scheduler** | scheduler | G3 **and** G4 | `readme-agent converge` exists; per-repo budgets; least-recently-attempted ordering; crash isolation; typed `SweepReportV1`; dry-run sweep shows zero `NOT_STARTED_DEADLINE_EXPIRED` | Halt; bash shim remains | **NOT STARTED** |
| **G6 Live sweep** | sweep, invalidation, ratchet tier | G5 | One full 34-repository sweep inside budget; every repo typed-terminal; accepted count ≥ baseline; second consecutive sweep makes zero new provider calls for accepted repos | Record and halt; **do not auto-tune** | **NOT STARTED** |
| **G7 Adaptation** *(conditional)* | adaptation | G6 **and** the corpus reproduces a known-good baseline | Corpus frozen and versioned; ≥1 auto-applied change with before/after evidence; a working auto-revert demonstrated | **If the corpus is not trustworthy, stop at the corpus and report** | **NOT STARTED** |
| **GV Independent verification** | — | any gate carrying a live proof, and closeout | An agent that did not implement the work refutes each claim, hunts for weakened checks, proves new tests are non-vacuous, and reports suite numbers itself | Repair every material finding **in the same cycle**, then re-verify | **PASS** — 6 defects found, 6 repaired, 2 recorded open |

**Global stop conditions** (any one halts the run): two equivalent ineffective attempts on one approach
fingerprint, or 15 minutes without material narrowing, without a recorded first-principles replan
(Decision #97) · claim lease expiry · `graph_drift: true` · any product-repository write attempt · any
acceptance threshold lowered to raise a pass count.

**Blocker standard.** An item is blocked only after **at least three materially different,
evidence-backed attempts**. Repeating the same command or the same hypothesis does not count. A
missing local prerequisite is not an external blocker — start it (see §11 rule 6).

---

## 8. Evidence Contract

**Bundle root**: `plans/investigations/evidence/autonomous-convergence-loop/`

**Required files**, exactly these names:

| File | Content |
|---|---|
| `REPORT.md` | Per gate: what passed, what failed, what was skipped and why, and the exact commands run. Cites every artifact. |
| `sha256sums.txt` | Manifest. **Lowercase `sha256sums.txt`** — not `SHA256SUMS` (H5). Written by the producer, never by hand. |
| `closeout-control.json` | Gate outcomes, `remaining_work`, `verdict`, `tree_clean_at_seal` |
| `independent-verification.json` | Verifier lane, brief, and a **path to a committed artifact** — never "the session transcript" (H9) |
| `mission-contribution.json` | Task id, contribution kind, summary, **every** commit in the cycle, state versions touched |
| `gate-outputs/<gate>-<self-explanatory-name>.<ext>` | One artifact per gate that ran |

**Producer**: `plans/investigations/tools/build_autonomous_convergence_loop_evidence.py`, using
`refresh_sha256sums()`. The bundle is generated, never assembled by hand.

**Rules**:

1. **Seal only on a clean tree.** Commit first, then seal. `tree_clean_at_seal` must be `true`; a bundle sealed over uncommitted changes does not cover the committed state and proves nothing (A12).
2. **No orphan artifacts, no orphan citations** — both directions (GOVERNANCE org rules 7 and 8). Every file in the bundle is cited by `REPORT.md`; every citation in `REPORT.md` resolves to a file in the bundle.
3. **Every commit in the cycle is listed** in `mission-contribution.json`.
4. **Findings cite committed artifacts.** A session transcript is not an artifact.
5. **Self-explanatory names** (GOVERNANCE naming rule 2): no `proof1`, `S1`, `run2`, `temp`. Gate prefixes must not collide across different gates (H10).
6. **`verify_sha256sums` must return true** at seal, and the check is part of closeout — not an assumption.

---

## 9. Verification Matrix

| Check | Command | Status at last measurement | Owning card |
|---|---|---|---|
| ruff | `ruff check .` | OK | — |
| ruff-format | `ruff format --check .` | OK | — |
| mypy | `mypy src` | OK | — |
| **pytest (canonical)** | `scripts/governance/run_full_pytest.py` | **OK** — 0 failed, 5509 passed, 1 skipped, `leaked_process_ids: []`, clean tree, at `3310543c6` | — |
| plan structure | `scripts/governance/validate_plan_structure.py` | OK | — |
| verifiers wired | `scripts/governance/check_verifiers_are_wired.py` | OK | — |
| prompt hygiene | `scripts/governance/check_prompt_hygiene.py` | OK | — |
| requirement/taskcard coverage | `build_level8_requirement_taskcard_coverage.py --check` | OK | — |
| **traceability** | `plans/investigations/tools/traceability_matrix.py --check` | **OK** (cycle 2) | — |
| actionlint | via official checks | OK | — |
| **official checks (all ten)** | `scripts/governance/run_official_checks.py` | **EXIT 0 — all ten OK**, TREE CLEAN, at `3310543c6`. Reproducing it requires that nothing else run python against the repository during the run; an identical earlier run exited 1 purely on `leaked_process_ids` from concurrent processes. | `ACL-PYTEST-LEAK-GUARD-CONCURRENCY` (still open: the guard is concurrency-sensitive) |
| pinned hashes | `scripts/governance/validate_pinned_hashes.py` | OK | — |
| pinned-hash dedicated tests | `validate_pinned_hash_dedicated_tests.py --all` | OK, wired into CI | — |
| compact authority | `scripts/governance/validate_compact_authority.py` | **RED**, unwired from CI; `master.md` 674 > 600 | `ACL-MASTER-AUTHORITY-COMPACTION` |
| **CI (Linux)** | `gh run list --branch main --limit 5` | **RED since long before this sprint** — including at baseline `8d29adc16`. `pinned-hashes` green throughout; the `test` matrix failed 6 on Linux while the same suite was green on Windows. Cycle 2 took it 6 → 5 (long-path fix) → 0 expected (`snapshot_root` portability, `daaf18b01`). | — |

**Proof chain — must be demonstrated end to end at G6:**

```
REAL INPUT     data/products.json @ frozen RegistryRevisionV1 + live repository sources
   |
ENTRY POINT    readme-agent converge --execution-profile local_poc   (Decision #26/#100)
   |
PROCESSING     ConvergenceScheduler -> isolated worker subprocess -> readme_presentation graph
               -> validate -> RepairController -> revalidate -> independent review -> no-op replay
   |
STATE/ARTIFACT candidate bundle + CandidateQualityRecordV1 + FailureSignatureRecordV1
               + DomainStateV1   (all durable)
   |
GATE           deterministic validation + 30-point rubric + independent review + no-op proof
   |
CONSUMER       SweepReportV1 -> AdaptationController -> PromptCandidateV1 (replay-gated)
   |
OBSERVED       accepted count non-decreasing across sweeps, with fitness trend and
               provider spend recorded per sweep
```

**Cross-cutting verification obligations**

- **Rerun/idempotency** — two consecutive sweeps on unchanged inputs: zero new provider calls for accepted repositories, byte-identical candidates.
- **Recovery** — kill a sweep mid-flight; resume must not re-run completed repositories and must not lose signature or fitness records.
- **Stale state** — a file outside a repository's recorded dependency set: plan reused. Inside: invalidation fires.
- **Scale** — one full 34-repository sweep inside its declared budget with zero `NOT_STARTED_DEADLINE_EXPIRED`.
- **Security** — no product-repository write, no default-branch write, allow-list enforced, no credential in state, evidence, or logs.
- **Canonical runner** (H7) — every test claim is made under `run_full_pytest.py`. A bare `pytest` run is not evidence: its longer `tmp_path` masked a real failure once already.

---

## 10. Repair Loop

Applies to every card. This is the same-cycle discipline, not a suggestion.

1. **Repair material findings in the same execution cycle, then repeat verification.** The independent lane found six defects in the last cycle; all six were repaired before closeout and two were explicitly recorded as left open. That is the standard.
2. **Root cause, not symptom.** A failing check is repaired at the source that produced it. When two mechanisms could explain a failure, instrument and measure rather than choosing the convenient one — the MAX_PATH defect was found by counting sealed vs. enumerated files (64 / 46 / 18 missing), not by reasoning.
3. **Sibling-site sweep (H8).** When a defect is found in one implementation of a pattern, search for every other implementation of the same pattern **before** claiming the fix is complete. The MAX_PATH fix shipped at one site while two siblings carried it, one failing **open**. Record the sweep in the evidence, including "no siblings found".
4. **Fail-open is worse than fail-closed.** When triaging duplicates, repair the fail-open site first.
5. **Re-prove non-vacuity.** After fixing a test, restore the pre-fix implementation in memory and confirm the positive test fails and the negative control still passes. A test that cannot fail is not a test.
6. **Never leave a half-migration.** If a rewiring moves a failure rather than fixing it, revert to the tracked failure and record the exact resume condition. A tracked known failure is more honest than an obscured one.
7. **Two equivalent ineffective attempts, or 15 minutes without material narrowing** ⇒ stop and record a first-principles replan (Decision #97). Do not keep pushing the same hypothesis.
8. **Repair the plan too.** When repository reality contradicts this plan, the plan is wrong. Amend it in the same cycle and record the amendment in §1 — five such conflicts were found and recorded at G0.

---

## 11. Anti-Overclaim Rules

Each rule exists because the corresponding mistake was actually made and caught.

1. **Repository reality and raw evidence outrank plans, reports, task statuses, and agent summaries.** Including this document.
2. **The graph file's `status:` field is not live truth.** Durable state is. The file read `TODO` for all ten cards while state held five `CLOSED`, two `REGRESSED` and one `IN_PROGRESS` (A13).
3. **A negative control that cannot fail is not a control.** Prove non-vacuity by restoring the defect.
4. **Name which of the three state stores you are reading, and why, before drawing a conclusion** (A17): mission authority → `origin`; repository lifecycle → `runs/local-poc-state/state.git`; caches → gitignored JSON under `runs/`. Reading the wrong one does not error; it answers confidently and wrongly. When a state read contradicts the CLI, assume the wrong store before assuming the CLI is wrong.
5. **Test claims are made under the canonical runner only** (H7).
6. **A missing local prerequisite is not an external blocker** (A18). The "container registry acquisition unavailable" failure was an unstarted daemon; starting it is covered by standing authority. Diagnose before escalating.
7. **Docstrings state what is true, not what was intended.** Three overstated safety guarantees were caught in one review: "fails closed", "no change outside long paths", "an unexpired claim is never touched" — the last false under a malformed timestamp or clock skew.
8. **Cite the document that actually contains the sentence.** The `evaluate`-reconciliation quotation is `plans/idea.md:158`, not `plans/master.md` (H4). A misattribution propagated into production source, a test, a log shard and an evidence file.
9. **Distinguish the raw counter from the contract-valid counter** (H6). `raw_lifecycle_progress` 1/34 is not `no_op_proven` 1/34.
10. **Report the number that occurred.** "5 failing → 2" was actually "5 → 4" under the canonical runner at the time it was claimed. State partial results as partial.
11. **Reject false green** caused by skipped work, empty discovery, stale caches, swallowed errors, mocks, placeholders, permissive fallbacks, or validators that exclude the affected paths. An empty result set is a finding to investigate, never a pass.
12. **Separate pre-existing failures from failures this work caused**, explicitly, whenever reporting a red check.
13. **Never claim mission completion from a summary.** Completion is `mission_complete = true` in durable state with contract-valid counters to match.

---

## 12. Closeout Criteria

A cycle closes only when **all** of these hold. Anything less is reported as partial with the exact gap named.

1. Every card in §5 is `completed_verified`, or carries a recorded exact resume condition.
2. `run_official_checks.py` exits **0** on a clean, unchanged tree — all ten checks, pytest and traceability included.
3. CI green on `main`: both the `test` matrix and the `pinned-hashes` job.
4. Working tree clean; `main` in sync with `origin`; every commit auto-pushed with hooks honoured (never `--no-verify`, never force-push).
5. Durable mission state reconciled: `graph_drift: false`, no expired claim left behind, no card `CLOSED` against unreachable machinery.
6. Evidence bundle sealed per §8 on a clean tree, `verify_sha256sums` true, every commit listed.
7. Independent verification performed by a lane that did not implement the work; every material finding repaired in the same cycle and re-verified; anything left open stated as open with its reason.
8. `logs/<date>.md` complete, with `logs/README.md` index rows matching.
9. The final response states: mission verdict, baseline and final repository state, work completed, root causes repaired, verification and pilot results, task and state reconciliation, independent-verification verdict, remaining blockers with exact resume conditions, changed files and commits, **the evidence bundle's absolute path**, and known limitations.

**Mission closeout** (distinct from cycle closeout) requires every processable repository at 30/30
with an immediate complete-transaction no-op. Current: contract-valid `no_op_proven` **0/34**,
`facts_ready` **1/34**. `MISSION_COMPLETE — NO_ELIGIBLE_WORK_REMAINS` is returnable only when that is
met in durable state. **Do not return it, or `MISSION_BLOCKED — TRUE_EXTERNAL_BLOCKER`, on any weaker
basis; when neither is true, say so plainly.**

---

## 13. Remaining True Blockers

**None.**

Every item in this plan is executable under standing authority: reads, `.venv`, tests, evidence
generation, control-repo edits, commits, and pushes to this repository's own `origin`
(GOVERNANCE rule 19; Decision #107; the standing pilot authorization for `dry_run` registry-mode flips
at each wave's closing live-proof pass).

Re-checked, item by item:

| Candidate blocker | Verdict |
|---|---|
| Container runtime | **Not a blocker** — unstarted local daemon, started under standing authority, server 28.4.0 confirmed |
| `GH_TOKEN` liveness | **Not a blocker** — re-verified live; use `GH_TOKEN=$(env -u GH_TOKEN -u GITHUB_TOKEN -u GITHUB_PAT gh auth token)`. Re-verify each cycle; do not assume it is dead |
| Provider access | **Not a blocker** — `qwen3-next` via `https://llm.professionalize.com/v1` configured and exercised (57 calls, `llm_accounting=EXACT`) |
| Full-portfolio compute | **Not a blocker, a cost** — roughly 40 minutes of wall clock per repository transaction across 34 repositories is multi-session work, not unavailable authority |
| Product-repository writes | **Out of scope** — Gate C, separately authorized, not required by any card here |
| Full-mode registry flips | **Out of scope** — `dry_run` flips are pre-authorized; full-mode flips require asking, and no card here needs one |

The remaining distance to the mission is **engineering plus provider compute**. It is named,
taskcarded, and ordered above.

---

## Appendix — single-go execution prompt (repaired in place)

> Execute the autonomous-convergence-loop plan at `plans/claude/autonomous-convergence-loop.md` as a
> single controlled run. You are the coordinator (`readme-agent-supervisor`). One governing plan, one
> controller, one authoritative task graph, one continuation state, one evidence chain. Do not create
> competing plans, supervisors, queues, or mission states.
>
> Work gate by gate (§7). A failing gate stops the run at that gate — never advance on a partial result.
>
> **G0.** Record `git status --porcelain`. Run `mission_resume_capsule.py --check`; regenerate if stale.
> Read mission status **from `origin`**, not from `runs/local-poc-state/state.git`, and not from the
> graph file's `status:` field. Re-verify `GH_TOKEN` with the `env -u` recipe. Clear the expired claim
> via `--mission-action evaluate`, re-claim `L8-PF-02-COMPLETE-CANDIDATE-SEAM`, record the narrowing
> immediately, and keep the lease unexpired.
>
> **G1.** Close `ACL-VER012-REVIEWER-DOUBLE-MIGRATION`, `ACL-TRACEABILITY-ROW-EVIDENCE-REPAIR`,
> `ACL-EVIDENCE-BUNDLE-RESEAL-ON-CLEAN-TREE`, `ACL-MASTER-AUTHORITY-COMPACTION`. Never skip, `xfail`,
> or delete a test to reach green — a real regression exits the gate and opens a BACKLOG row. Exit
> condition: `run_official_checks.py` exit 0 on a clean, unchanged tree, plus
> `validate_pinned_hashes.py` and `validate_compact_authority.py` both 0, plus green CI on `main`.
>
> **G2.** Close `ACL-PF04-CLOSURE-RECONCILIATION`, `ACL-GRAPH-STATUS-FIELD-DIVERGENCE`,
> `ACL-BACKLOG-ROW-CAPTURE`. Insert a graph taskcard **only** under §5.1 — the existing ten cards
> already carry this work, and the budget is 15 with 5 free.
>
> **G3 ∥ G4.** `ACL-DETERMINISTIC-VALIDATION-REPAIR-LOOP` and
> `ACL-CANDIDATE-FITNESS-AND-FAILURE-SIGNATURES`. Verified-disjoint file ownership (§6). Run them
> concurrently only if you actually delegate, and then write
> `runs/multi-agent/<task-id>/execution-plan.json` first. Otherwise stay serial — no ceremonial role
> records. Prove at least one previously `presentation_plan:blocked` repository advances live.
>
> **G5.** `ACL-CONVERGENCE-SCHEDULER`. Keep `run_gate_a_local_poc_portfolio_loop.sh` as a shim until
> G6 passes twice.
>
> **G6.** `ACL-FULL-PORTFOLIO-SWEEP` with `ACL-SCOPED-COMPOSITION-INVALIDATION` and
> `ACL-DURABLE-SHARED-RATCHET-TIER`. Record the result — do not auto-tune to make it look better.
>
> **G7, conditional.** `ACL-PROMPT-ADAPTATION-REPLAY-GATE`. Build and freeze the replay corpus first.
> If it cannot reproduce a known-good baseline, **stop there and report** — do not ship auto-apply on
> a weak signal.
>
> **Standing rules.** One commit per closed causal cluster; stage exact paths only; preserve unrelated
> work. Pre-commit runs plan-structure/ruff/format/mypy plus a blocking pinned-hash dedicated-test
> gate; post-commit auto-pushes to this repository's own `origin` (Decision #107). Never `--no-verify`,
> never force-push, no destructive git, no broad staging, no secret exposure, no publication or
> deployment. Append a `logs/<date>.md` line immediately with each governance edit, not batched. No
> product-repository write, no default-branch write, no acceptance threshold lowered to raise a pass
> count. Apply §10 (repair loop) and §11 (anti-overclaim) throughout. Before closeout, have an
> independent agent or lane that did not implement the work verify it, and repair every material
> finding in the same cycle.
>
> **Blocker standard.** At least three materially different, evidence-backed attempts. Repeating the
> same command or hypothesis does not count. A missing local prerequisite is not an external blocker.
>
> **Deliverable.** Seal the evidence bundle at
> `plans/investigations/evidence/autonomous-convergence-loop/` per §8, **on a clean tree**, and
> **state its absolute path in your final response** along with the gate reached and the honest
> pass/fail of each gate. Return `MISSION_COMPLETE — NO_ELIGIBLE_WORK_REMAINS` or
> `MISSION_BLOCKED — TRUE_EXTERNAL_BLOCKER` only under §12. If neither is true, say so plainly rather
> than claiming either.
