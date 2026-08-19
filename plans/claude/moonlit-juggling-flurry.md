# Autonomous README Freshness Service — Implementation Plan

*Primary plan document. Annex A — this session's full production assessment (deliverables
5-partial/6: evidence inventory and root-cause assessment) — is EXTRACTED to a separate frozen
file (see §21 for its location); it is referenced, never duplicated, never executed from.*

**Plan lineage** (for any future session): (1) template-standard plan → superseded; (2) production
assessment → preserved as **Annex A, frozen historical evidence — its TC-series taskcards are
superseded by this plan's T-series and must NOT be executed from Annex A**; (3) aspose.org-process
adoption plan → absorbed into this plan (recoverable from session transcript if needed); (4)
link-semantics plan → absorbed as task T10 + §7b register rows; (5) **this document — the sole
active plan.** The 15,248-line aspose.org historical plan is an external reference reconciled in §2,
never executed top-to-bottom.

## 0. Reading order, resume protocol, baseline, and binding resolutions (plan-repair run 2026-08-15)

**Reading order for any cold-started agent**: §0 (this section) → §8 (binding decisions) → §14
(taskcards + embedded machine-readable state) → §9-13 (architecture) → §15-16 (milestones/tests) →
§21 (certification) → everything else as reference. **Resume protocol**: read the canonical task
state (the JSON in §14, materialized as the repository task-state file once registered) for
statuses; the next task = lowest-numbered `ready` card whose prereqs are `complete`; never re-run a
`complete` card unless its listed inputs changed; Annex A is frozen evidence — never execute from
it.

### Repository baseline (recorded 2026-08-15, read-only commands)

Repo `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer`, branch `main`, HEAD
`8cb9afabeb31b69e6948a33a7502d89952caf701`, remote `origin =
https://github.com/babar-raza/foss-readme-optimizer.git`. Dirty worktree (pre-existing, protected —
never staged/stashed/reset/committed by this plan): `M plans/backlog-post-poc.md`,
`M plans/requirements.md` (CRLF-only), untracked
`plans/investigations/evidence/l8-horizon-01-deferral-2026-08-13/`. Tools verified present: gh
2.83.2, Docker 28.4.0, act 0.2.89, Python 3.13.2, node 24.13.1, `.venv/Scripts/readme-agent.exe`.
Credentials: `GH_TOKEN` ✓, `LLM_API_KEY` ✓, `LLM_BASE_URL` **env var absent** — gateway base URL is
configured elsewhere in the client stack; TP-00 must verify the effective endpoint config before any
LLM step. Checks run: `scripts/governance/validate_plan_structure.py` → **clean** (111 size-guidance
warnings only); all 11 workflow YAMLs parse. Hosted CI (`ci.yml`): **red on every push since
2026-08-02** (latest failure 2026-08-12). `readme-agent-production.yml`: still failing on schedule
(24-32s, token-minting; latest **2026-08-15 05:42**). Full non-live suite: **re-run fresh during this
repair (2026-08-15, 20m18s): 10 failed / 3,697 passed / 24 deselected.** The 10 failing tests, by
exact name (this list IS the input to the G0 baseline-exception record — any failure not on it is
NEW and blocks): `test_agentic_readme_composition.py::test_agentic_plan_is_source_and_fact_bound_and_changes_the_candidate`;
`test_local_poc_review_evidence.py::test_no_op_proof_reuses_the_exact_accepted_review_binding`;
`test_portfolio.py::test_completed_local_poc_status_advances_only_with_valid_bundle`;
`test_readme_composition_characterization.py::test_document_composition_bytes_and_plan_are_characterized`
(3 parametrizations: cells/3d/pdf Java);
`test_trusted_transform_review.py::test_canonical_trusted_pipeline_persists_approval_then_exact_no_op`;
`test_verified_source_opening.py` ×3 (all reference a missing evidence dir
`…/finalized-repository-readmes-v1/repositories/python/pdf--537b8273b185--bd8699b68869/ORIGINAL-README.md`
— an evidence-revision mismatch, classified stale-fixture). A second in-session run at the same
HEAD collected 3,714 selected (3,704 passed / 41 deselected) with the IDENTICAL 10 failures — the
failure set is stable; the selected/deselected delta is a collection-snapshot difference, and
TP-00 re-records the authoritative counts via the governed runner. Hosted CI additionally fails on
runner-environment-dependent tests (gitignored `runs/baseline/` content absent on the runner) —
a distinct class from the local 10, resolved by TB-04 + TB-05 with zero new skip markers.

**Baseline failure classification**: the 10 local failures and the red hosted CI are **NOT
classified as "unrelated baseline"** — they cover the exact machinery this plan modifies
(composition, no-op proof, portfolio advancement, trusted transform, verified source handling).
**G0 closes only with zero relevant failures and zero new skip markers**: every failure is fixed
by its TB card (TB-01–TB-05); the single environment-dependent case (MAX_PATH) passes under the
governed runner and is documented (TB-06), not excepted. **Red CI must never be read as
implementation success.** Production-workflow token-minting failure = *external
authority blocker* (App installation scope; owner action) → gates only hosted-lane proofs (G5
partial), nothing else. `LLM_BASE_URL` env absence = *environment note* → TP-00 verification item.
Requirements-catalog validator asymmetry (Annex A) = *known machinery defect*, avoid new
requirement-catalog rows until fixed. Dirty worktree = *protected user state*, excluded from all
commits.

### BINDING AMENDMENT (2026-08-15, round 3) — portfolio-wide local approval before ANY remote write

**This amendment supersedes every conflicting instruction in this plan.** Nothing may be pushed,
committed, proposed, or otherwise written to any target repository until: (1) the complete
authoritative portfolio has been processed locally; (2) every candidate README has passed all
required local gates; (3) the complete end-to-end delivery workflow has been verified locally
without changing any target repository; (4) the human has reviewed and **explicitly approved all
portfolio README candidates locally**. No product/platform/urgency/automation/confidence
exceptions. The unit of approval is the **complete portfolio** — never one product, family,
platform, pilot, or batch; a passing pilot never opens the remote-write gate. Pre-approval,
target repos permit read-only operations only (clone/fetch/inspect/refs/read/hash-compare/public
metadata); prohibited: push, remote branch, PR **including draft PRs**, commit inside a
remote-destined checkout, merge, settings/topics/description/homepage/social-preview edits,
issues/comments/labels/releases/tags/workflows, uploads, any mutating API endpoint, and any
"test-mode" write against a real target.

Enforcement is **technical, not conventional**, and its scope is stated honestly: it governs
**system-owned execution** (this runtime, its subprocesses, supervisors, recovery and resumed
runs) — no application-level control can stop an independent human or arbitrary process holding
separate credentials, and this plan does not claim otherwise (amendment cards, all in §14):
**TW-01** defense in depth — layer 1: pre-approval, target-repo operations receive read-only
credentials where available, write-capable `GH_TOKEN`/Git credentials are removed/masked from
every target-repo subprocess environment, and target clones run with credential-helper
inheritance disabled; layer 2: a transport-layer choke-point covering every system-owned git push
and GitHub API mutation (target-remote match across HTTPS/SSH/alternate URL forms;
enable-condition = verified portfolio approval receipt only; fail-closed on
missing/malformed/stale/ambiguous approval state; rejected attempts recorded); layer 3:
`AuthorizationRecordV1` and the portfolio receipt as independent gates. **TW-02** local E2E simulation of all 22 delivery steps with real git operations against
isolated local bare repos + disposable clones + mocked GitHub API — never real targets;
print-what-it-would-do is not proof. **TW-03** product state machine
(DISCOVERED→INPUTS_PINNED→GENERATED→LOCALLY_VALIDATED→LOCALLY_E2E_VERIFIED→
READY_FOR_PORTFOLIO_REVIEW→HUMAN_APPROVED→REMOTE_ELIGIBLE) + portfolio aggregate
(PORTFOLIO_DISCOVERED→…→AWAITING_GLOBAL_HUMAN_REVIEW→GLOBALLY_APPROVED→REMOTE_WRITES_ENABLED,
reachable only when EVERY in-scope product is HUMAN_APPROVED) + full accountability matrix
(family, platform, target repo, active/excluded with authoritative reason, candidate path, source
revision, README hash, candidate hash, validation, E2E, review status — silent omission
forbidden). **TW-04** one browsable local human-review bundle (no internal run-dir spelunking).
**TW-05** immutable approval receipt bound to exact candidate + source hashes, with automatic
invalidation (candidate byte change, target README change, relevant default-branch advance,
inventory change, validator/contract change, E2E-implementation drift, regeneration, gate
invalidation → remote writes stay disabled, revalidate, rebuild bundle, re-approve the COMPLETE
portfolio; approval never silently carried forward) and the post-approval execution rules
(hash/revision recheck, authorized-files-only diffs, bounded lanes, drift stops the product and
reassesses the receipt, approved bytes preserved exactly, per-action receipts). The ten
amendment-mandated regression tests are distributed across TW-01/TW-02/TW-03/TW-05 closeouts.

**Supersessions applied**: §8's family-by-family rollout is LOCAL GENERATION SEQUENCING only —
remote eligibility is portfolio-global, never per-family; MS3's "candidate publication" means a
local candidate + bundle entry, never a remote write; the §12–13 trust ladder's future per-repo
grants now require BOTH the per-repo `AuthorizationRecordV1` AND the portfolio approval receipt.
**This plan's terminal state is `AWAITING_GLOBAL_HUMAN_REVIEW`** — the complete portfolio bundle
exists, the guard is proven, and remote writes are technically impossible within this plan.

### Binding contradiction resolutions (one decision per subject)

1. **Import-and-own** (pin-read-through fully purged from this plan). 2. **Repo rename: removed
from the active graph** — an optional rename must not leave the run externally blocked; if the
owner ever exercises it, it is a separate future plan with its own downstream-integration
inventory and rollback proof. 3. **Implementation begins only after TP-00**; the import path is TP-00 → TD-01 (storage decision) → T1A → T1B — nothing bypasses the preflight. 4. **Canonical corpus =
`reports/repo-presenter/`** (owner-finalized 08-14 batch lives there; regen-full retained in import
as comparison evidence only). 5. **Uncommitted upstream material** imported via the T1A snapshot
manifest (base commit + dirty-marker + tracked-modification patch + untracked-file inventory +
per-file sha256 + reconstruction verification) — reproducibility comes from the manifest, never
from a bare SHA claim. 6. **Storage model — DECIDED during plan repair on measured evidence (2026-08-15): plain git,
lean import set, no LFS, no split branch.** Measurements (source: `D:\onedrive\Documents\GitHub\aspose.org`
— note the second OneDrive mount, NOT `D:\Users\prora\OneDrive\...`; HEAD `7f72da4e14235461`,
dirty: 4,811 modified / 209 deleted / 72 untracked): raw specified set = 1.15 GB / 6,289 files
incl. `knowledge/_vectors/pdf/go/api.vectors.json` at 123.6 MB (**exceeds GitHub's hard 100 MB
blob limit — raw import is not viable without LFS**) + one more >50 MB. Applying the source
repo's OWN `.gitignore` exclusions (its comments classify them regenerable: `knowledge/_vectors/`
626.6 MB, `knowledge/*/*/scout/` 98.1 MB, `data/backlinks/workspace/` 316.6 MB, `__pycache__/`)
= **lean set 108.5 MB / 3,277 files, largest blob 19.0 MB (`data/aspose_com_targets.json`), zero
files >50 MB — comfortably inside plain-git/GitHub limits; LFS and split-branch add cost for no
benefit at this size**. Embedding vectors are regenerated here via our own gateway + cache (§10)
rather than imported. TD-01 (card) re-measures at execution and confirms these numbers within
±10%; a material deviation fails closed back to re-decision, never improvisation. Import
constraints recorded from measurement: copy from the DIRTY WORKTREE (not HEAD — `dependency_
extract.py` is untracked; `reports/repo-presenter/` is gitignored upstream and exists ONLY in
that working copy; `knowledge/` is mid git-tracking-migration); scope to exactly
`reports/repo-presenter/` (sibling `- Copy`/`-regen-*` trees = 3.05 GB / 201k files — a
`repo-presenter*` glob is forbidden); scrub the hardcoded `C:\Users\prora\...humble-tome.md`
local paths from the three foss modules' docstrings; no LICENSE exists upstream (first-party
corporate code, all-rights-reserved default) → destination applies its own license deliberately +
`IMPORTED-FROM.md` provenance record + per-file `Adapted from aspose.org: <path> @ <sha>` headers
(existing repo convention); filename-level secret scan clean, content-level scan runs at T1B. 7. **Check inventory is derived** (grep/tests)
— "81" is a point-in-time audit measurement, never a binding constant. 8. **Invalidation:
per-section fingerprints + a separate document-global fingerprint**; section change → that section
only; global-contract/assembly change → whole document; both proven by tests (§16). 9. **Milestone↔
task mapping fixed**: G3/MS1-deterministic = T5; G4/MS1-complete = T6 + T7A + T7B + T8 no-op proof
(MS1 is composition-through-idempotent-double-run only — freshness/scheduling belongs to T9/MS2,
not MS1); MS2 = T9; MS3 = candidate publication + takeover-idempotency; T10 AND the preservation
gate (TP-11A core; TP-11B residuals before rollout) must both be green before any candidate is called reviewable.
10. **Delivery = candidate-only** for this entire plan; PR/issue/metadata/merge actions each require
a future named grant (`AuthorizationRecordV1` / App permission) — no card in this plan opens one.
11. **Old composer paths remain reachable only as in-DAG fallbacks**; they stop being independent
entrypoints at G1 (poc runner stamped diagnostic-only) and retire fully at T12. 12. **Annex A
status**: frozen evidence; its RC9 is superseded by the owner's Java-pilot clarification; its
TC-series is superseded by §14; its measured findings (RC1-RC8, RC10-RC11) remain current unless a
G0 re-check contradicts them.

### TP-00 — Mandatory preflight (first card; blocks ALL implementation)

`ready` · agent · Prereqs: plan approval. **Actions**: re-read authoritative artifacts (AGENTS.md,
idea.md, master.md+ledger, GOVERNANCE.md, mission graph, durable state via `readme-agent supervise
--mission-action status`, hook configs, workflows, execution-profile + authorization schemas);
re-verify this §0 baseline (identity, dirty status unchanged or re-recorded, tools, credentials,
effective LLM endpoint config + one probe call, model routes via golden-set status); verify **no**
`AuthorizationRecordV1` exists (`config/authorization/` absent/empty) and no unexpected
`mode: full` beyond the two known Java pilots; create the worktree/branch topology exactly as
specified in "Git worktree & branch model" below (fixed strategy, not a choice); re-verify the
import source recorded in resolution 6 (`D:\onedrive\Documents\GitHub\aspose.org` — HEAD, dirty
inventory, lean-set size within ±10% of 108.5 MB / 3,277 files);
run the full non-live suite and record counts vs the §0 baseline; classify any NEW failures before
proceeding. **Closeout**: materialize the plan-repair evidence bundle (deferred file writes from
this read-only repair run): copy this §0 + command outputs into
`plans/investigations/evidence/freshness-service-preflight-<date>/` with sha256 manifest; write the
machine-readable taskcard state file from §14's canonical JSON (staged bytes; the in-repo landing
and umbrella registration are TS-01–TS-03's work, not TP-00's). **STOP RULE**: if repository reality differs materially from the §0 baseline (new failing tests beyond the recorded set, changed authorization state, changed worktree, unreachable LLM endpoint), TP-00 fails closed and returns the plan to repair — no improvisation. **Done-when**: all checks recorded, zero unexplained deltas vs baseline (or the baseline-exception record created), evidence bundle exists on disk. **Rollback**: none needed (read-only + additive evidence).

### Optimizer-repo vs target-repo authority (explicit)

**Verified from repository governance during this repair** (GOVERNANCE.md rules 9/10/12/19,
Decisions #31/#32/#33/#81 + GOV-018, HANDOVER.md §13, and git-history observation — full citations
in the repair bundle), each effect encoded per-card in §14; nothing below is inferred from token
availability:

| Effect on optimizer repo | Authority | Source |
|---|---|---|
| Edit files (incl. master.md, workflow files) | GRANTED (standing, Decision #81; rule 12; workflow edits pass actionlint + heavier verification tier) | GOVERNANCE 12/19 |
| Append logs/ shards | GRANTED freely | GOVERNANCE 12 |
| Commit to LOCAL `main` | GRANTED — **coordinator only** (workers never commit, integrate, or transition state — rule 19) | Decision #81 |
| Create/use LOCAL branches + worktrees | Not enumerated by any grant; purely local git state, no remote effect — used by this plan for index-level lane isolation, disclosed here as a first (repo history shows zero branch checkouts ever) | rule 19 scope |
| Push `refs/readme-agent-state/*` | GRANTED — architecturally required (39 such refs already on origin) | Decision #32 |
| Push `main` or any branch to origin | **NOT granted.** Established steady state: agents commit locally, THE USER pushes (local main is 8 commits ahead of origin right now, documented in HANDOVER.md as normal) | HANDOVER §13; rule 10 |
| Open PRs / merge via remote | **NOT granted** (no PR has ever existed on this repo) | HANDOVER §13 |
| `workflow_dispatch` | **Human-only by convention** — every workflow is deliberately manual with a comment saying so; agents test via `act` (explicitly granted by rule 19) | workflow files; rule 19 |
| Create optimizer-repo issues | Only via CI workflow steps with `github.token`; no agent-side grant | production workflow |
| Force-push / reset / clean / broad-stash | FORBIDDEN | rule 9 / Decision #31 |
| Mission-state writes | `readme-agent supervise --mission-action status` is the ONLY read-only action; `evaluate/claim/transition/record-*` WRITE and default-push state refs to origin — any mission write must set `README_AGENT_STATE_REMOTE` deliberately | git_backend.py:749 |

**Consequences bound into this plan**: all lane work is LOCAL (worktrees + local branches, zero
pushes); hosted CI verification of plan commits happens only after THE USER pushes `main` (or
grants a named push authorization) — this is a **standing external-authority item**, and G-gates
that want hosted proof re-run their verification after a user push rather than pushing
themselves; TA-01's decisive dispatch test is likewise a user-triggered action (agent supplies
the exact command); optimizer-issue run-tracking is dropped from this plan (no grant). Target
product repos: **read-only, candidate-mode, zero writes of any kind** (no push, no PR, no issue,
no metadata) for this entire plan — each future write class requires its own named
`AuthorizationRecordV1` grant (`config/authorization/` does not even exist yet — nothing is
authorized for remote_write today). Merging `freshness-service/integration` into local `main` is
likewise **a later USER action** (or happens only after the user provides a clean governed
integration worktree for `main`) — see the worktree model below.

**GitHub App failure — RECLASSIFIED as a configuration bug, not an owner blocker** (agentic
re-evaluation 2026-08-15, full evidence in the repair bundle): the production workflow's
`discovery-token` step (readme-agent-production.yml:79-86) is the ONLY one of four
`actions/create-github-app-token@v3` steps that omits `owner:`/`repositories:`, so the action
defaults to the current repo and calls
`GET /repos/babar-raza/foss-readme-optimizer/installation` → 404 (log-confirmed, run 31867614801)
— the control repo, where the App (owner `babar-raza`, client-id var `GH_APP_CLIENT_ID`, secret
`GH_APP_PRIVATE_KEY` — both present) was never meant to be installed. The other three minting
steps correctly pass per-matrix `owner:`/`repositories:`. Introduced by commit `d56ca3651`
(copy-paste omission). The token's sole consumer is registry discovery over 26 public orgs — it
functions as a rate-limit credential (public reads), and `discovery.py` already treats it as
optional. **Fix = card TA-01**: add `owner: aspose-cells-foss` + `repositories:
Aspose.Cells-FOSS-for-Java` (an installation that exists; strictly narrower than the intended
default), preserving `tests/unit/test_production_workflow.py` count assertions (4× client-id, 3×
permission-contents: read). Verification: that test + actionlint agent-side; the decisive proof
is an empty-input `workflow_dispatch` (already defined in the workflow) which hits the registry
job in under a minute — **dispatch is human-only per the authority table, so the agent supplies
the exact command (`gh workflow run readme-agent-production.yml`) and the USER triggers it after
pushing**; `act` cannot exercise the step (guarded `if: env.ACT != 'true'`) and is used only to
confirm the surrounding job. **No control-repo App installation is required** — the control-repo
state writes use the default `GITHUB_TOKEN`. Remaining GENUINE owner actions (exact): (1) push +
dispatch after TA-01 lands — **the dispatch outcome itself is the installation proof**
(discovery-mint against `aspose-cells-foss` + per-matrix mint against `aspose-3d-foss` succeed or
404, decisively); a manual App-settings check is requested ONLY if that result is ambiguous;
(2) create repo secrets `LLM_BASE_URL` + `LLM_API_KEY` (declared `required: true` for
workflow_call but absent from the repo — the next failure behind the token step) — a user action
if governance bars the agent from setting secrets (it does: no grant exists). No App permission
or workflow action that can mutate a target repository is used anywhere in this plan.

### Repository-native task-state registration (decision RESOLVED during this repair; TD-02 removed)

Governance facts (verified): the Level-8 mission graph
(`plans/investigations/control/level8-autonomous-mission-task-graph.yaml`, `TaskCardV1` schema,
strict pydantic) is the **sole** active machine-readable task graph (GOVERNANCE rule 14 — "create
no competing plan/controller/store"); durable supervisor state (git ref
`refs/readme-agent-state/mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` on origin, per Decision
#32) is the sole live status authority; the graph is at its **15/15 active-task cap** with 10
durably-CLOSED cards occupying slots, unretireable because
`mission_graph.py::_validate_graph` resolves active-task dependencies against active cards only —
a gap the repo's own evidence (`l8-horizon-01-deferral-2026-08-13/findings.md`, Finding 3) already
identifies with its prescribed fix; a free-floating `plans/freshness-service/taskcards.json`
would violate the layout closed-set, the control-data placement rule, and the sole-graph rule.
Therefore the governed structure is fixed as three registration cards that precede ALL
implementation (§14): **TS-01** — land the graph-loader retirement fix exactly as the repo's own
findings prescribe (active dependencies may resolve to `deferred_task_index` entries whose
durable status is CLOSED; negative control included; plus `mission_control.py`
`_DEPENDENCY_SATISFIED` counterpart). **TS-02** — retire durably-CLOSED active cards to the
deferred catalog (DeferredTaskRecordV1 + index entries + sha256/record-count pins), then register
one umbrella active card `L8-FRESH-00-FRESHNESS-SERVICE` (complete TaskCardV1: mission_id
`LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`, a valid campaign_id/stage_goal_id/goal_ids,
allowed/forbidden paths = this plan's ownership manifest, execution_focus), append it to
`migration-matrix.json` `new_tasks[]` with its semantic sha256, rebuild the requirement-coverage
receipt, and run BOTH `run_official_checks.py` AND — explicitly, because it is not in the
official suite — `validate_compact_authority.py`. **TS-03** — materialize the subordinate
artifacts: `plans/investigations/control/freshness-service-taskcards.json` (STATIC card
definitions only — a control inventory with a typed schema in `src/readme_agent/supervisor/` +
mirrored unit test, pinned by sha256 from the umbrella card) and the live-status mechanism as an
**append-only transition ledger** in the evidence tree (precedent:
`agile-authority-reset-v1/multi-agent-execution-plan.json`) — statuses/transitions are recorded
there and validated by a consistency test against §14's transition model, while the umbrella
card's durable status remains the sole runtime authority (no competing status store). The
supervise mission-write trap is bound into all three cards: only `--mission-action status` is
read-only; any writing action sets `README_AGENT_STATE_REMOTE` deliberately (default pushes
state refs to origin). **Plan-mode honesty**: the exact file contents for TS-02/TS-03 are staged
byte-complete in the repair evidence bundle and schema-checked; the repository validators
themselves run at TS-01–03 execution (they validate graph+matrix files this read-only repair
cannot touch). TS-03 completion is a prerequisite of **every** implementation card, so no
implementation work can start before registration succeeds. The frozen Annex A archives at
`plans/investigations/control/freshness-service-plan-annex-production-assessment-2026-08-15.md`
(the repo's frozen-checkpoint precedent home) as part of TS-03.

### Gates G0–G8 (coordinator-enforced; a failed gate stops the lane, never advances)

G0 = TP-00 complete (authority + baseline + state reconciliation; evidence bundle exists) AND
every TB baseline card closed (each of the 10 local failures fixed or conclusively root-caused
with a narrow, governed, per-test exception record — no broad exceptions, and no exception at all
for a failure whose machinery this plan modifies unless its root cause is proven independent of
that machinery). G1 = TS-01+TS-02+TS-03 complete (umbrella task registered, control inventory +
transition ledger live, ownership manifest in force, `validate_compact_authority.py` +
`run_official_checks.py` both green) + tool readiness green (incl. LLM probe). G2 = TD-01+T1A+T1B import complete: snapshot manifest verifies (incl. T1A reconstruction proof),
every consumer resolves in-repo, staged reviewable commits, license/attribution/secret-scan clean. G3 =
T5 deterministic pilot green (full battery + byte-identical double run). G4 = T6 + T7A + T7B + T8
+ TP-11A + TW-01: calibrated LLM steps beat fallbacks, repair routing bounded, **no-op proof
(zero LLM/embedding calls, byte-identical)**, **preservation core green (every original unit
accounted)**, remote-write defense in depth proven. G5 = T9 scheduler proofs local + the hosted
lane attempt — hosted proof requires: TA-01 merged on integration, the USER pushing and
dispatching (the dispatch outcome — token-mint success/failure for both Java orgs — IS the
App-installation proof; manual App-settings confirmation only if that result is ambiguous), and
the two LLM secrets existing; **if any remains unresolved when G5 is evaluated, the run's final
verdict includes BLOCKED_PRODUCTION** — local completion is reported as such, and the production
definition of done is explicitly NOT claimable. G6 = family pilot + takeover-idempotency on ≥2
aspose.org-published repos. G7 = complete-portfolio local rollout incl. TF-01 (Font/Python
acceptance) + portfolio-wide & section-scoped idempotency; **any quarantined/blocked active
product makes the portfolio non-approvable — verdict BLOCKED_PORTFOLIO** (safe sibling lanes may
still finish; "candidate or quarantine report" never satisfies the approval gate). G8 = final
regression at the TG-00 zero-failure standard, state reconciliation, aggregate evidence closeout
(loose files + `sha256sums.txt` + handoff ZIP outside tracked paths with its own SHA-256, both
absolute paths reported); **verdict precedence: BLOCKED_PORTFOLIO (any quarantined product) /
BLOCKED_PRODUCTION (hosted proof unresolved) — may co-report; otherwise the terminal state is
AWAITING_GLOBAL_HUMAN_REVIEW** — never "done". Each gate's evidence = named files under
`plans/investigations/evidence/freshness-service-g<N>-*/` with sha256 manifests.

### Git worktree & branch model (index-level swarm safety; fixed, not a choice)

**The user's working tree at `D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer`
stays on `main` and is NEVER switched, staged, stashed, merged, reset, or cleaned by this plan** —
its three dirty paths remain untouched for the plan's entire life. All plan work happens in
dedicated worktrees under the sibling root `D:\Users\prora\OneDrive\Documents\GitHub\.fro-worktrees\`:

| Worktree path (under `.fro-worktrees\`) | Branch | Created from | Used by |
|---|---|---|---|
| `coord` | `freshness-service/integration` | recorded base commit (§0 HEAD, re-verified at TP-00) | coordinator only |
| `l-import` | `freshness-service/l-import` | `freshness-service/integration` | L-import lane |
| `l-contract` | `freshness-service/l-contract` | `freshness-service/integration` | L-contract lane |
| `l-compose` | `freshness-service/l-compose` | `freshness-service/integration` | L-compose lane |
| `l-service` | `freshness-service/l-service` | `freshness-service/integration` | L-service lane |

Creation (coordinator, at TP-00): `git worktree add ..\.fro-worktrees\coord -b
freshness-service/integration <base-commit>` then one `git worktree add ..\.fro-worktrees\<lane>
-b freshness-service/<lane> freshness-service/integration` per lane activated (lanes are created
lazily — only when their first card goes `in_progress`). **All branches are LOCAL-ONLY — nothing
in this plan pushes any branch to origin** (per the §0 authority table; the user pushes `main`).
**Commit rules (rule-19-conformant)**: lane worker agents EDIT files in their own worktree only —
they never run `git commit`; the **coordinator** reviews and commits each card's changes in that
lane's worktree (only files matching the lane's rows in the path-ownership manifest, one card per
commit series, standard trailer). Shared-file changes are prepared by the lane as `*.patch` files
under its own evidence dir, applied + committed by the coordinator in `coord`. **Integration**:
coordinator only, in `coord`, in gate order: run the overlap validator, then `git merge --no-ff
freshness-service/<lane>` per closing card, re-run the card's verification in `coord` (official
checks require a clean tree — the `coord` worktree provides exactly that; the user's dirty
worktree never hosts a proof run), then advance state. **Local `main` is NEVER updated by this
plan**: `main` is checked out in the user's dirty worktree, and updating a branch checked out in
another worktree is both refused by git and — via any workaround — would desynchronize the user's
index; no `git -C` invocation can make that safe, so no such claim is made. All agent commits
terminate on `freshness-service/integration`; merging or cherry-picking the completed integration
branch into `main` is **a later USER action** (or happens only after the user first provides a
clean, governed integration worktree for `main`). **Lane sync**: before each dependent card
starts, the coordinator synchronizes that lane's branch with the latest
`freshness-service/integration` (`git -C ../.fro-worktrees/<lane> merge freshness-service/integration`,
or recreate the lane worktree from integration). **Cleanup**: after a lane's last card merges,
`git worktree remove ../.fro-worktrees/<lane>` and delete only `freshness-service/<lane>` (a
branch this plan created), first verifying merged status **against integration** (`git branch
--merged freshness-service/integration`) AND that its evidence is durable on disk. **User-worktree
invariance (tested, not assumed)**: TP-00 snapshots the user worktree (`git rev-parse HEAD`,
`git status --porcelain` byte-recorded); a scripted check re-verifies branch, index, tracked
modifications, and untracked paths byte-identical after EVERY card and at every gate — any delta
is a stop-the-run defect. **Recovery**: worktrees are disposable — a corrupted lane worktree is
removed (`git worktree remove --force` + `git worktree prune`) and re-added from its branch;
commits are never lost because they live on the lane branch.

### Lane model + file ownership (coordinator-led)

Bounded concurrency ≤3 active lanes; coordinator owns all shared-state transitions, integration
order, and gate advancement. **Path-ownership manifest**: the table below is materialized
machine-readably at registration (see §14) as `plans/investigations/control/freshness-service-ownership.json` (single canonical location)
(lane → exact path patterns); the **overlap validator** (registered with the state machinery, see
§14) runs (a) before any lane's first card enters `in_progress` and (b) before every integration
merge, and **fails hard** if two active lanes claim the same file or a lane's commit touches a
file outside its ownership rows. Shared rows are coordinator-only (lanes propose patches); **no
concurrent edits ever** to governance files, task-state, workflows, registries, schemas. Unrelated
user changes (the §0 dirty set) exist only in the user's worktree and are structurally untouchable
from the lane worktrees.

| Lane | Cards | Exclusive ownership | Shared (coordinator-only) |
|---|---|---|---|
| L-baseline | TB-01–TB-06 | the six cards' named test files, `src/readme_agent/llm/call_ledger.py`, `tests/conftest.py`, `tests/fixtures/note_golden_workflow/`, AGENTS.md testing note, its own evidence dirs | — (runs before all other lanes activate; no temporal overlap) |
| L-import | TD-01, T1A, T1B | `src/readme_agent/vendored_asposeorg/`, `data/imported/`, `plans/investigations/evidence/imported-corpus-v1/`, its own evidence dirs | — |
| L-contract | T2, T3, T14, T10 | `docs/readme-process.md`, `src/readme_agent/validation/aspose_checks/`, `templates/readme/*.json` (section registry), section plugins, `presentation_contract.py`, link-semantics modules + their tests, its own evidence dirs | — |
| L-compose | T4, T5, T6, T7A-F, T8 | `facts/composer_factpack.py`, `facts/render_views.py` (new view only), slot-step modules, `prompts/generation/*` new manifests, `scripts/calibration/`, its own evidence dirs | `stage_dependencies.py` rows (lane proposes a patch; coordinator applies) |
| L-service | T9, T11, T13 | freshness/queue modules, metadata-engine modules, issue-lane modules, its own evidence dirs | workflow YAMLs + `supervisor/` shared files (lane proposes; coordinator applies) |
| Coordinator | TP-00, TS-01/02/03, TA-01, TU-01, TG-06A/B, TG-07, TG-08, T12, all gates, ALL commits | mission graph + deferred catalog + migration matrix (TS cards), control inventory + transition ledger, `stage_dependencies.py` (applying lane patches), aggregate evidence bundles, integration/merge commits, workflow YAMLs | — (coordinator IS the shared-file owner) |

Handoff format: each lane closes a card with (files changed, tests run + results, evidence path,
state transition request); coordinator validates overlap + integrates + transitions state.

### Rollback & external-compensation catalog (all non-destructive; never stash/reset/clean user changes)

Local: Failed/interrupted import → `git revert` the import commits on the lane branch; manifest
identifies partial state; re-run staged. Failed task commit → `git revert <sha>` on the lane
branch; card back to `ready`; cache invalidation by hash. Cache/schema incompatibility → bump
schema version, invalidate by key prefix, recompute. Corrupted/stale durable state → the existing
recovery command, exact invocation `readme-agent recovery-sweep` (a TOP-LEVEL subcommand,
verified at cli.py:341 — not a supervise flag; re-verified at TP-00; evidence = its output
captured to the card's evidence dir); never hand-edit state refs.
Abandoned locks → existing lock-expiry + recover path. LLM outage → breaker opens, products
deferred, next cycle retries; no partial fragments persisted. Rate limits → adapter backoff +
per-cycle budget stop. Failed Docker verification → product quarantined with report; never a
weakened gate. Failed scheduler run → resume from stage checkpoints. Partial candidate artifacts →
temp-dir compose + atomic promote only on full validation. Hosted workflow interruption → rerun;
run receipts identify the resume point.

External effects (each requires a **rollback receipt written to the acting card's evidence dir
BEFORE its gate advances**; "close/delete" vagueness removed): **Branch pushed to origin
(optimizer repo)** → delete only the exact branch this plan created (`git push origin --delete
freshness-service/<name>`) after verifying with `git branch -r --merged` that no unmerged work is
lost; never delete a branch the plan did not create. **PR opened (optimizer repo, if used)** →
close the PR via `gh pr close <n> --comment <reason>` and delete its automation branch as above;
receipts record PR number + close timestamp. **Issue created (optimizer repo run-tracking only in
this plan)** → close with a corrective comment (`gh issue close <n> --comment <reason>`); deletion
is NOT claimed (GraphQL deleteIssue needs admin and is not assumed). **Metadata writes** (future
authorized mode only): before any write, record the exact previous values in the receipt; rollback
= restore those exact values via the same API. **Target product repos**: zero writes in this plan
⇒ zero external compensation surface. **Repo rename**: removed from this plan (see resolution 2).

### Single-go execution evidence bundle (required at G8 — for successful, quarantined, failed, AND externally-blocked outcomes alike)

`plans/investigations/evidence/freshness-service-final-<date>/`, following the verified repository
evidence convention: **loose, individually-diffable files with a `sha256sums.txt` at the bundle
root** (two-space format, CRLF-normalized hashing via `evidence/writer.py::sha256_file`; secrets
pass through `evidence/redaction.py`). Repository governance has no committed-ZIP convention
(every .zip in the tree is disposable act output under gitignored `runs/`), so nothing ZIPped is
committed — but the **user-level handoff requirement** is satisfied by ALSO producing, after the
manifest is finalized, a ZIP of the final evidence directory **outside tracked source paths**
(under the session scratchpad or `runs/`), with its own SHA-256; the final report states BOTH
absolute paths and the ZIP hash. The same dual rule applies to the plan-repair evidence bundle.
Contents: §0-style repo baseline before/after (branch, commit, status); taskcard state
before/after; lane ownership + overlap-check results; import provenance manifest; every command +
exit code; hook/lint/type/test/Docker/Mermaid/workflow-validation results; hosted run URLs +
conclusions; LLM/embedding call counts + redacted ledger summary; freshness/no-change proofs;
idempotency results; per-product outcome matrix; candidate/quarantine/rollback receipts;
authorization decisions + proof of zero unauthorized remote writes; remaining blockers; final DoD
assessment. The executing agent's final message must state this bundle's **absolute path**.

## 1. Executive feasibility verdict

**FEASIBLE, QUICKLY, BY REUSE.** The content engine is proven (aspose.org: 31 accepted READMEs, real
merged PRs, 81 deterministic checks, 646 tests, hardened through 34 recorded incidents). The
autonomous control plane is ~75% built in this repo (scheduler workflows with daily+weekly cron and
`repository_dispatch`, git-ref state machine, component-versioned invalidation cache, call ledger,
locking, GitHub App auth, fail-closed execution profiles, `AuthorizationRecordV1` write gate). The
genuine gaps are: (a) the human-composition step in the proven engine → replaced by the bounded
gateway composition worker (designed this session, §10); (b) wiring the freshness predicate into the
scheduler; (c) the metadata engine (net-new by scope ruling, but its design exists in the historical
plan). The fastest credible delivery is a complete vertical pilot on one accepted-history product,
not a portfolio rewrite — reachable without building any new orchestration.

## 2. Historical-plan supersession ledger

From two complete chunked reads of the 15,248-line historical plan (`d-users-prora-…-humble-tome.md`).
Statuses per mission vocabulary. Only decision-bearing chains listed; prose restatements omitted.

| Decision/section | Order | Status | Superseded by / evidence | Current relevance |
|---|---|---|---|---|
| Diagram Gen-1 (per-node wiring, traceability edges) | 08-03..06 | Implemented, later superseded | MT024 Gen-2 → MT025 Gen-3 | Use Gen-3 only: archetype-keyed `StartingPoints?→Product→Capabilities→Outputs`, no per-node edges, no styling |
| Templates A/B/C bake-off | 08-02 | Rejected | golden-review-v1 seed → corpus+checks | Contract = checks + corpus, never a single file |
| `dropped_claims.json` | 08-04 | Proposed only, never built | `content-dispositions.json` (MT030) | Adopt dispositions schema; ignore all dropped_claims prose |
| Banner plain/unlinked (user AskUserQuestion) | 08-09 | Implemented, later superseded | TC-HARDEN-27: link to verified homepage | Banner links to `products.aspose.org/{f}/{p}/`, local-file-verified |
| `--draft` PRs; human clicks merge; 4-section PR body | 08-05..10 | Implemented, later superseded | MT032 chain: no draft; agent merges with explicit `--subject`/`--body`; 3-section body, never an upstream-defects section | Copy the FINAL rules; note code drift (run.py still passes `--draft` — known-wrong, do not port) |
| `check_diagram_connectivity`, 2 siblings; `format_support_claims` | 08-06..08 | Implemented, retired | `diagram_shape`+`column_balance`; `verified_format_claims` (2-of-3) | Port current checks only |
| `installation_matches_package_registry`, `dependency_scope_claim` as hard gates | 08-10..14 | Implemented, downgraded | heuristic (registry proven wrong both directions) | Never hard-gate on unreliable evidence sources |
| MT043 bridge-disclosure anchor contract | 08-14 | Implemented same-day, REVOKED | MT044 (landed in working tree, uncommitted) | Binding: destination-driven anchors, leading-public-platform for compound slugs, never "via", family = last resort. User re-confirmed this session |
| `cells/java` Outputs-node exception | 08-05 | Closed, tightened away | MT025 format-purity rule | No per-product diagram exceptions |
| Check-count prose (45/46/47/49/50) | various | Contradictory | grep: **81** `check_` functions | Never trust counts in prose; verify by grep |
| `verify_examples` per-language | 08-03.. | Current, partially implemented | Python runner real (opt-in `--python-runner`); 6 languages honest stubs | This repo's Docker verifiers (6 ecosystems) are STRONGER — keep ours, adopt their per-block status vocabulary |
| CLI live `push` | — | Current but never executed | only dry-run receipt exists; 4 real PRs via hand-run SOP | Trust the SOP semantics; treat CLI push as unproven |
| Two candidate trees (`repo-presenter` vs `-regen-full`) | 08-13.. | Contradictory, unresolved upstream | MT044 declined to resolve | Canonical corpus = `reports/repo-presenter/` (owner's 08-14 finalization landed there); recorded in the import manifest |
| `/repo-presenter-metadata` skill | 08-02 | Design only, never built | TC-HARDEN-08 | **Now in scope here** (ruling): implement from that design |
| `reports/` gitignored, no backup | — | Current, unresolved | TC-HARDEN-17 (policy decision) | Our pin snapshot must copy from the working tree (captures uncommitted MT041-44 + corpus) |
| Aspose.org-side residuals (note/python duplicate CTA, docs.aspose.com anchors ungated, words/net+pdf/cpp map gaps, uncommitted machinery) | 08-14 | Current, reported | this session's fresh audit | **Report-only** (ruling): owner actions, not ours |
| This repo: POC freeze; golden-sample authority | 08-09 | Informally abandoned; to retire | erosion mechanism traced (Annex A RC10) | Golden authority retires immediately, harvest first (ruling) |

Unresolved contradictions honestly carried: the two-trees question (pinned, not resolved); em-dash in
anchor form (MT044 uses " — Enterprise Edition"; owner's casual phrasing omitted dash — defaulting to
MT044 form, one-constant change if corrected).

## 3. Verified implementation manifest (aspose.org, all code-read this session)

| Component | Source path (imported at T1B) | Purpose | Proven | Portable | Required change |
|---|---|---|---|---|---|
| Run CLI/state machine | `scripts/pipeline/commands/foss/readme_refresh_run.py` (~2,760 ln) | 11 subcommands, CREATED→…→PUSHED, locks, receipts | states/detectors yes; live push no | **No — not ported** | Orchestration stays with this repo's `supervise`; port only detector logic |
| Check battery | `…/readme_refresh_checks.py` (~6,300 ln, 81 checks) | the de-facto README contract | yes (515 tests, portfolio-run) | **Yes — vendor** | Path/config indirection to pin; fail-closed fixtures per check |
| 13 `_detect_*` factpack builders | in run.py | license/install/enterprise/archetype/SEO/deps/badges… | yes | **Yes — adapt** | Re-source inputs to pin + this repo's facts |
| `dependency_extract.py` | same dir | 7-ecosystem manifest → `DependencySnapshot`, fail-closed | yes (29 tests) | **Yes — vendor** | none material |
| `backlink_targets.py` + overrides YAML | `scripts/pipeline/lib/` + `data/backlinks/` | Enterprise URL resolution | yes (override demonstrably wins) | **Yes — vendor URL half** | never port `build_enterprise_anchor_suffix` (different convention) |
| Data registries | `data/*.json`, `keywords/` | products/families/archetypes/targets/casing | yes | **Imported** | hash into factpack |
| Knowledge trees | `knowledge/{f}/{p}/merged/` | model/api_surface/formats/claims/limitations/snippets | yes (drives corpus) | **Imported** | formats.md never sole authority (2-of-3 rule) |
| Dispositions ledgers ×3 | per-product JSON | reconciliation contract | yes (hard-gated) | **Adopt schema** | authored by our gateway worker (§10.4) |
| Accepted corpus | `reports/repo-presenter/{f}/{p}/readme.md` ×31 | quality bar, calibration reference | yes (owner-finalized 08-14) | **Imported** | leave-one-out exemplars; never a byte-template |

## 4. Effective current README contract (reconciled; enforced by vendored checks, not prose)

**Agility principle (owner ruling — binding)**: the template is agile; sections may be removed or
added at any time, and the system must absorb such changes **plug-and-play**. Therefore the contract
below is the *current content of a versioned section registry* (data), not a hardcoded list — the
architecture that makes this true is §9's section-plugin design, and the registry hash is part of
the freshness tuple so a template change invalidates exactly the affected work and nothing else.

**Deterministic structure (registry v1)**: 10 required H2s (At a Glance, Key Capabilities, Installation,
Dependencies, Quick Start, API Reference, Documentation & Resources, Scope and Limitations,
Development and Testing, License) + optional Navigation/Additional Examples/Project Structure/
`### Project History`; badge row + floor (License + ≥1 of version/lang/CI/contributors); banner
linked to verified homepage; Mermaid Gen-3 archetype contract (28-char token ceiling, no
styling/classDef, box-drawing project trees); flagship-example-then-collapse; two-tier API reference
mirroring the reference index; fixed License template (starts-with, real path casing); Enterprise
link: exactly one, in Scope and Limitations, **destination-driven MT044 anchor**
(`Aspose.{Family} for {Platform} — Enterprise Edition` on platform pages; family form on family
pages; leading-public-platform for compound slugs; **never "via"**; family = last resort; unresolved
= omit with recorded reason); "Enterprise Edition" label kept (owner convention — documented as not
Aspose's own page wording); no forum/*.aspose.app links; no process narration (5 categories incl.
generation-mechanism); title case incl. `<summary>`; single-mention rules; internal artifacts never
named. **Verified facts** (deterministic only): identity, coordinates, install commands, platforms,
dependencies (snapshot), capabilities/formats (2-of-3 corroboration), API surface, limitations,
links (catalog+overrides), license, source revision. **LLM-composed fields** (each: structured
inputs, forced-tool-call schema, prohibition list, deterministic post-validation, bounded repair —
full DAG in §10): opening summary; per-bullet capability elaborations; per-limitation rewrites +
2-line summary; Quick-Start lead-in; Additional-Examples brief; residual disposition
classifications; per-unit preserved-content restyles. The LLM never decides structure, facts, link
destinations, coordinates, or publication state.

### 4b. Original-README preservation contract (hard gate — TP-11A deterministic core at G4, TP-11B LLM residuals at G7)

The system must preserve all verified information from each target repository's existing README
while restructuring and improving it. This is a **blocking gate on reviewability**, owned by card
TP-11A (deterministic core — gates the pilot at G4: every original unit accounted, residuals explicitly `blocked_unverified`) and TP-11B (LLM residual dispositions — gates the rollout at G7), enforced every cycle, not once:

1. **Unit extraction**: the original README is parsed into traceable content units (the imported
   `content_unit_*` extraction), each carrying a positional `unit_id` AND an **excerpt
   content-hash** (U8 control) so positional-ledger drift is mechanically detected by a bijection
   check (fresh extraction vs stored hashes) every cycle.
2. **Verification**: every factual unit is verified against repository evidence; evidence
   references are **re-resolved every cycle** (U9 control — `evidence_resolves` on fresh state).
3. **Disposition**: every original unit receives exactly one disposition from the closed enum
   `preserved | reframed | merged | superseded | omitted_invalid | blocked_unverified`. Every
   non-`preserved` disposition carries evidence refs + a written rationale; a unit with no entry
   is a hard failure (silent content loss is prohibited by construction).
4. **Coverage floor**: verified installation details, examples, API information, supported
   formats, limitations, dependencies, project history, links, testing instructions, and
   platform-specific guidance are preservation-class content — they may be `reframed`/`merged`
   but never `omitted_invalid` without evidence that they are factually wrong, and never
   `superseded` without the superseding candidate text identified.
5. **Reconciliation matrix**: each candidate ships an original-to-candidate matrix (original
   unit → disposition → candidate section/span or ledger rationale), emitted as a per-product
   artifact beside the dispositions ledgers.
6. **Gate**: a candidate cannot enter `reviewable` until every original unit is accounted for and
   all preservation checks pass (TP-11A gates T8/the pilot; TP-11B gates TG-07/the rollout).
7. **Negative tests** (part of TP-11A's closeout): a fixture in which a verified original-README
   detail is silently dropped MUST fail validation (one negative fixture per preservation-class
   category above); a fixture with a positionally-shifted ledger MUST trip the bijection check.

## 5. Production-evidence inventory

Aspose.org: 31 accepted candidates (pinned corpus) + 3-ledger sidecars; real merged PRs
(cells/java, cells/net, cells/typescript, 3d family, email/*, words/net); 62/62 candidates clean on
link semantics (fresh audit); run receipts incl. one full failure-and-fix worked example
(cells/typescript events.jsonl: 14 hard-gate failures → 1 → pass). This repo: rejected 10-README
delivery (negative evidence), 31-repo POC diagnostic tree, measured gateway characterization (191
identical-request groups, 90.6% variance; forced tool-calls 5/5 reliable; ~71k context), full
workflow/CLI/profile inventory. Historical evidence is referenced, never regenerated.

## 6. Autonomous-project root-cause assessment

**Annex A, extracted** (RC1–RC11, symptoms→causes→weaknesses, superseded taskcards; location in
§21). Phase-5 summary in
mission terms — symptoms: no published results, repeated planning, rerun drift. Root causes: rebuilt
the generator instead of reusing the proven one (its deterministic composer was rejected on
quality); grounding evidence stripped before composition (RC1); execution lane never proven (RC3);
discipline erosion mechanism (RC10). Structural weakness, exactly the mission's phrase:
**orchestration without a proven content engine** — plus duplicated spec authority (golden samples
vs contract vs corpus). What is genuinely stronger here and is preserved: Docker-isolated 6-ecosystem
example verification, byte-span claim accountability, component-versioned invalidation,
prompt-registry governance, forced-tool-call client + call ledger, execution profiles +
authorization gate, GitHub App workflow lane. Nothing is preserved merely for effort spent: the
deterministic prose composers are demoted to fallbacks; `plan_readme_composition`'s diagram/section
surfaces and the SEO title generator retire after parity; `commands_poc.py` is diagnostic-only.

## 7. Capability reuse map

| Capability | aspose.org | This repo | Preferred owner | Action |
|---|---|---|---|---|
| Product inventory + exclusions | products.json/exclusions | data/products.json (+modes) | **this repo** (delivery scope) | reconcile against pin; mismatches = findings |
| Scheduler/triggers | none (gap) | cron daily+weekly + dispatch | **this repo** | reuse; add freshness queue |
| State machine/locks/receipts | run-tree per product | git-ref durable state + trigger lifecycle | **this repo** | reuse ours |
| Freshness/invalidation | pinned inputs, recompute-fresh | component-versioned cache | **this repo** | extend key tuple (§11) |
| Factpack semantics | 13 detectors | ProductFactsV2 (richer verification) | **merged** | adapter builds ComposerFactpack from both |
| Composition | human agent | rejected deterministic composer | **new worker** (§10) | gateway DAG; old composers = fallbacks |
| README contract/validation | 81 checks | 24-check validator + lints | **vendored checks + ours** | both run; ours adds claim accountability |
| Example verification | Python-only runner | Docker 6-ecosystem | **this repo** | keep ours; adopt status vocabulary |
| Reconciliation | 3 dispositions ledgers | byte-span claim accountability | **both** | ledgers = public contract; spans = inner proof |
| GitHub delivery | hand-run SOP (proven), CLI push (unproven) | profiles + App + AuthorizationRecordV1 | **this repo** | SOP semantics encoded in our lane |
| Metadata engine | design only | surface_ownership.py stub | **this repo (new)** | implement from historical design (§14 track B) |

### 7b. Upstream defect register — tackled professionally here, never inherited

Every known aspose.org problem found this session, each with the specific control in this system.
Reuse transfers the *proven capability*, not the defects. Each row gets a test or design control;
none may be silently reproduced (enforced via §16).

| # | Upstream problem (evidence-verified) | Our control |
|---|---|---|
| U1 | Code/skill drift: `push` still passes `--draft` (skill forbids it); post-conditions prose contradicts its own step 8; co-author trailer hardcoded | Their push path is **not ported**. Our delivery lane encodes the final MT032 rules (no draft; explicit subject/body; trailer read fresh from the acting session) |
| U2 | Prose-carried spec rots: `_briefing.md` says ~47 checks (real: 81), omits mandatory Dependencies section; skill doc's Starting Points rule was actively wrong; composition rules repeatedly never reached the artifact composers read | Our composer is driven by **governed prompt manifests + vendored checks**, not prose briefings. `docs/readme-process.md` carries a drift test against the vendored check inventory; hand-maintained counts banned — derived by grep/tests |
| U3 | Two candidate trees, no canonicality rule (their largest open contradiction); 25/31 candidates composed outside any tracked run; all 6 run dirs ABANDONED; state machine never completed a live publication | **One candidate store**, all composition through the tracked `supervise` lane — out-of-band composition structurally impossible (no separate diagnostic composer for production content); canonical-corpus choice recorded in the import manifest |
| U4 | `reports/` gitignored — the entire 30-product deliverable has no history/backup (disk-loss exposure); MT041–44 machinery uncommitted | Our candidates + ledgers live in **tracked, hash-manifested evidence paths**; the pin snapshot captures their working tree (preserving their uncommitted fix); commit urged in the report annex |
| U5 | `verify_examples` stubbed for 6 of 7 languages | Keep **our Docker-isolated 6-ecosystem verification** (already stronger); adopt only their per-block status vocabulary |
| U6 | `data/dependency_overrides.json` referenced everywhere, never created — the sanctioned escape hatch has no working remedy | Created **day one** with schema + per-entry provenance (`verified_by/at/evidence_note`), validated at load |
| U7 | Upstream data unreliability worked around ad hoc: package_registry wrong both directions; targets map stale (`cells/python→python-java`) and incomplete (`words/net`, `pdf/cpp` missing); `formats.md` 4 failure modes; keywords cross-platform contamination; knowledge `limitations.md` ~90 C++ false positives | Systematized: **never hard-gate on an unreliable source** (rule adopted); 2-of-3 corroboration; overrides with provenance; every consumed source carries a staleness/coverage **finding surface** instead of silent trust; map gaps reported per product |
| U8 | Disposition ID drift class: position-based `unit_id`s shift on upstream edits; **two confirmed live incidents; durable detector identified but never built** | Built here: ledger entries carry an **excerpt content-hash beside the positional id**; a mechanical bijection check runs every cycle (fresh extraction vs. stored hashes) — drift becomes a blocking finding, not a silent corruption |
| U9 | Ledger evidence-refs go stale (28/66 paths after a package rename; nothing detects automatically) | Evidence re-resolution runs **every cycle** (vendored `evidence_resolves` gate on fresh state); any input-hash change invalidates and forces re-authoring of affected fragments via the component cache |
| U10 | Tone-exemplar contamination: one narration defect propagated into 9 products through the exemplar-reading step; no contamination filter | Calibration harness admits an exemplar **only if it has zero live findings** across all gates (automated screen, leave-one-out) — the propagation channel is filtered by construction |
| U11 | Hybrid-archetype `decided_at` must equal *today* — by design the portfolio degrades daily (24/30→ drops on calendar advance with zero content change) | Redesigned to **identity-based freshness**: hybrid evidence is re-verified when its inputs change (clone HEAD / archetype entry), not by wall-clock — consistent with §11; no self-triggering decay |
| U12 | No scheduler; `audit-portfolio` on-demand only and covers one tree only; drift accumulates silently | Daily + weekly scheduler over the **whole** store by construction (§9, §12) |
| U13 | Concurrency hazard: gitignored content tree not session-safe (observed cross-contamination under 8 parallel agents) | Our per-product locking, isolated stage dirs, and bounded concurrency (existing supervise machinery) |
| U14 | LLM boundary unversioned: composition steered by prose briefings to interactive agents; no prompt registry, no calibration, no regression gate on prompt changes | Governed prompt manifests (hash-versioned), calibration scorecards keyed to prompt hashes, regression gate on every prompt bump (§10) |
| U15 | Silent bypass precedent: registry-excluded product run via in-process monkeypatch "per user instruction," undocumented path | Exclusions enforced in code; any exception requires an explicit, recorded, bounded authorization artifact — never a monkeypatch |
| U16 | Link gate scope hole: `docs.aspose.com` platform-named anchors entirely unchecked; duplicate commercial CTA shipped (note/python) | Our link-semantics validators (T10) cover **all aspose product/docs/kb/reference hosts**, both domains, plus duplicate-destination detection |
| U17 | Ad hoc gitignored `_scratch` scripts performing real verification (their own named anti-pattern) | All verification lives in tracked, tested modules — no scratch-path executables (standing house rule) |
| U18 | Diagram rendering assumptions: 28-char ceiling not font-measured; light theme never live-verified; GitHub's real renderer (viewscreen iframe) first exercised only at incident 30 | Keep our **real mermaid-cli render gate** in-pipeline; pilot spot-checks via the validated mermaid.ink proxy; ceiling kept as a heuristic with honest labeling |
| U19 | Governance registry rot (skill description placeholders silently regenerated by a sync bug; unsatisfiable DAR gate; env-var check bypass) | Not applicable to our governance stack; recorded report-only for the owner — explicitly **not** ported |
| U20 | Product defects found during generation stay buried in internal files (`upstream-issues.md` "NEVER pushed"; `UPSTREAM-DEFECTS.md` local-only) — product agents never systematically see them | **Issue-filing lane (owner ruling)**: every upstream *product* defect discovered during generation becomes a structured GitHub issue **in the target product repo** — full details (severity per the BLOCKING/FUNCTIONAL-DEFECT/VERSION-DRIFT/INFORMATIONAL taxonomy, exact evidence paths/lines, reproduction, impact on the README, "not fixable here because"), deduplicated against existing open issues, so product agents can pick them up systematically. Internal-only logging is superseded. Issue creation is a GitHub write: drafts-only in candidate mode, real filing only at the authorized trust level (needs `issues:write` App permission — flagged authorization boundary) |

## 8. Clarification questions — asked and answered (binding record)

Schedule: **daily sweep + weekly deep revalidation; lag target 24–48h.** Trust: **shadow → candidate
through the entire rollout; PR mode only after full-portfolio local proof AND the §0-amendment
portfolio approval receipt AND per-repo `AuthorizationRecordV1` grants (all three necessary);
merge always human.** Rollout (LOCAL generation sequencing only — remote eligibility is
portfolio-global per the §0 amendment): **family-by-family, inventory-driven
and dynamic** (owner clarification: "all families means all families, no exception; all platforms
means all platforms under a family, which differ per family — and the list is growing"). The
controller enumerates the **authoritative registry live each cycle** — no hardcoded family or
platform list anywhere; a newly discovered/admitted product automatically enters the portfolio in
shadow→candidate mode with no code change. The sequence cells → 3d → pdf → slides → email → words →
remaining families is an **initial ordering only** (it happens to cover both Java App pilots inside
their families), not a bound list — every family present in the registry at rollout time is covered,
whatever its platform set. Scope: **root README.md + full metadata**
(description/topics/homepage/community files/social-preview-handoff) — metadata as a second track
implementing the historical design — **plus upstream product-defect issue filing (U20)**. Prior
rulings incorporated, with the newest superseding: **full import-and-own of every reusable
aspose.org component — scripts, data, knowledge, corpus — into this repo** (owner ruling: aspose.org
is under rapid development and agents there could break things; this project becomes independent,
improving/customizing imported components here — supersedes the earlier pinned-read-through
posture); gateway-only composition with stepwise prompt hardening; idempotent takeover;
golden-retirement-immediately; Enterprise Edition label; MT044 anchors; never-via; aspose.org
untouchable (report-only). Defaults adopted as decisions (evidence-backed, no open "determine
later"): LLM budget ≤ ~50 calls/README first run, 0 unchanged, concurrency ≤6, per-repo quarantine
after bounded repair; endpoint-down ⇒ circuit-break, defer product, retry next cycle, never partial
writes; existing aspose.org open PRs untouched (report-only); model routing per measured
characterization (§10).

## 9. Target architecture (thin control plane over the imported, independent engine)

**Independence principle (owner ruling)**: everything reusable is **imported into this repo** —
vendored check battery, factpack detector logic, dependency extractor, backlink/URL resolution,
registries and override data, knowledge trees, the 31-README corpus + ledgers — under tracked paths
with a versioned **import manifest** (source repo revision, per-component sha256, import date).
After import, this repo owns and evolves every component; aspose.org changes reach us only through
**deliberate, reviewed cherry-pick re-imports** (an advisory upstream-diff report may flag drift,
but nothing auto-syncs). This removes the runtime cross-repo dependency, immunizes us against
upstream churn/agent mistakes, and makes their gitignored deliverables durable here (fixes U4).

**Plug-and-play section architecture (owner ruling — template is agile)**: the README template lives
as a versioned **section registry** (data file, e.g. `templates/readme/section-registry-v2.json`):
one entry per section — `{id, heading, order, required|optional, composer_binding
(deterministic fn | LLM slot-step ids), section_checks[], ledger_obligations, invalidation_scope}` —
plus an explicit **document-global check list** (title case, narration, link semantics, single-
mention rules…) that applies regardless of section set. Each section is a self-contained plugin
module (composer + its checks + its tests + optional prompt manifests). **Adding a section = one
registry entry + one plugin module; removing = deleting the entry (plugin retires); reordering = the
`order` field** — zero cross-cutting edits to assembly, validation wiring, freshness, or calibration.
The assembler iterates the registry; the check runner activates each section's checks only when the
section is registered; the calibration corpus is keyed **per section id**, so a removed section
drops its fragments harmlessly and a new section bootstraps exemplar-less (deterministic fallback
first, exemplars harvested from its own accepted outputs over time — a template change can never
produce false calibration regressions for unrelated sections). The registry hash joins the freshness
tuple (§11): a template change reopens exactly the affected sections of affected products. During
T3, every imported check is classified section-scoped vs document-global as part of the vendoring —
this mapping is the enabling work for plug-and-play and is validated by the §16 agility tests.

**Portfolio controller** = existing `supervise` + **live registry enumeration each cycle** (all
families, per-family platform sets, dynamic growth — no hardcoded lists) + exclusions + bounded
concurrency + per-product isolation; adds a freshness queue: sweep computes per-product staleness,
enqueues only stale products, emits one portfolio status line-set
(checked/unchanged/refreshed/blocked). Freshness reads of target repos need no App: the product
repos are public (anonymous/`GH_TOKEN` HTTPS reads, as the existing clone machinery already does);
the App remains scoped to its authorized write-lane proofs only. **Issue-filing lane (U20)**:
structured product-defect issue drafts generated alongside candidates; dedupe against open issues
(public API reads, rate-limit-aware); filing gated by trust level + `issues:write` authorization.
**Freshness engine** (§11) — identity-based, never timestamps. **README engine**: imported
inputs → merged factpack → deterministic sections + gateway DAG slots → assembly → vendored 81
checks + our validators + claim accountability → Docker example verification → candidate + isolated
diff + ledgers. **Adapter** (§10). **Review policy engine**: trust levels as data
(shadow/candidate/pr/merge per product), high-risk classifiers (install/license/link-destination
changes, verified-content removal, large diff, new limitations, failed verification) force human
review regardless of level. **GitHub delivery**: our profiles/App lane; disposable clones; surgical
changed-path verification; duplicate-branch/PR guards; receipts; resume — PR/merge stages dormant
until authorized. **Checkpoint/recovery**: stage cache + durable manifests; resume = cache hits;
crash mid-stage re-enters at last valid stage. **Observability**: existing `health-report` +
freshness-lag metric + per-product LLM call/cost from the ledger; unchanged runs emit one status
row, no evidence bundles.

## 10. `llm.professionalize.com` integration + composition worker (deep design)

**Root problem this design must solve** (not just "call the API carefully"): the proven engine's
quality came from a frontier agent composing whole documents; our gateway offers two mid-size models
with token-window limits and measured weaknesses — `qwen3-next` (forced tool-calls 5/5 reliable,
freeform weaker, real context ceiling ~71k, non-byte-stable at temp-0: 90.6% repeat variance) and
`gpt-oss` (freeform structured output unreliable: 0.4–0.8 validity swing across sessions; tool-calls
reliable) — plus `qwen3-embedding-8b`. Whole-document or even whole-section prose from these models
is exactly what already failed. The durable answer is structural, not prompt-tuning: **shrink each
LLM decision until the model's weakness no longer fits inside it**, keep every fact and structure
decision deterministic, and use the embedding model to do the *selection* work that otherwise
bloats prompts past what these models handle well.

**Adapter** (one production adapter, consolidating the existing stack — `LiveForcedToolClient`,
hash-versioned prompt registry, call-transport ledger with request/response hashes, Tenacity retry
registry, golden-set route qualification): env-configured endpoint + per-job model routing table;
startup capability probe (OpenAI-compatibility verified this session, still probed not assumed);
temperature 0, forced tool-choice always (no freeform markdown from any model, ever); timeouts,
bounded retries + backoff, rate + concurrency caps (≤6), circuit breaker; token/cost accounting per
call; redacted diagnostics; deterministic replay fixtures from pinned fragments (no live secrets).

**Model routing** (per-job, config-driven, guarded by the existing golden-set qualification gates
with auto-disable): `qwen3-next` = all composition slot-steps and classification tool-calls (the
only model trusted for authoring). `gpt-oss` = optional secondary roles only where tool-call-shaped
and independently qualified (e.g., a second disagreement-vote on review verdicts, cheap unit
pre-classification) — never authoring, never sole authority; if its golden-set pass-rate gate fails,
the route auto-disables and the pipeline runs without it (it is an optimization, not a dependency).
`qwen3-embedding-8b` = five deterministic-adjacent jobs, none authoritative on facts:
1. **Exemplar retrieval**: per slot-step, embed the corpus's reference fragments once (cached by
   content hash); at composition time select top-k semantically-nearest exemplars for few-shot —
   better than family-proximity heuristics, and keeps prompts small under the token budget.
2. **Evidence packing**: rank a product's evidence excerpts by relevance to the slot being composed;
   deterministic packer fills the ≤8k context by whole-unit boundaries in rank order — the model
   never sees a truncated excerpt, and prompts stay far from the window ceiling.
3. **Reconciliation assist**: embedding similarity as an additional *heuristic* signal beside the
   deterministic token-overlap checks when matching old-README units to candidate sections (the
   fragile 0.6-threshold word-overlap class of failure) — flags likely matches/misses for the
   deterministic gates to verify; never itself accepts or rejects a unit.
4. **Semantic-duplicate detection**: capability bullets, disposition probable-duplicates,
   duplicate-destination anchors — embedding-cosine screen feeding existing heuristic findings.
5. **Calibration scoring**: embedding similarity to reference fragments as one scorecard metric
   beside Jaccard/ROUGE-L/gates (catches paraphrase-quality that lexical metrics miss).
   Embedding outputs are cached by input content hash — zero recompute on unchanged inputs; index
   versions pinned in the import manifest so a model-version change invalidates deliberately.

**Worker = the composition DAG** (full step table preserved in session evidence): deterministic
steps compose the majority of bytes (header/badges/banner, Mermaid, Installation shell,
Dependencies, Quick-Start code, API tables, Docs & Resources, Enterprise paragraph, License,
navigation, assembly + overflow normalization); LLM slot-steps are per-unit forced tool-calls with
evidence-excerpt grounding via `EvidenceGroundedRenderViewV2` (closes RC1), each with schema,
prohibition list, deterministic post-validation, ≤2 repairs, deterministic fallback (worst case =
plain-but-passing README, never silent drops, never a weakened validator). **Decomposition ladder**
(the "smallest realistic step" escalation, applied wherever calibration stalls instead of prompt
polishing): section → per-unit (one bullet / one limitation / one disposition) → two-stage
select-then-phrase (deterministic/embedding selection of the evidence, LLM phrases one sentence
from it) → sentence-split (e.g., opening summary as two single-sentence calls: identity+purpose,
then audience) → deterministic fallback. Each rung is cheaper to verify than the last; the ladder
position per step is recorded in the step's manifest so reruns are stable. Dispositions:
deterministic pre-filter (mechanical NON_CONTENT / exact-match merges / contradiction supersedes) →
embedding-assisted candidate-target shortlists → residual per-unit classification from supplied
evidence-ID menus only → vendored `content_unit_*` gates. Finding→step routing repairs only the
owning step. First-accepted-wins fragment pinning ⇒ unchanged inputs reproduce byte-identical
output with **zero LLM and zero embedding calls**.

**Prompt hardening = the calibration harness** (repeatable, not vibes): per-step reference fragments
decomposed from the imported 31-corpus; deterministic scoring (hard gates, shape, lexical
similarity, embedding similarity, groundedness, banned vocabulary); scorecards keyed by prompt hash;
regression gate on every prompt version bump; exemplars admitted only with zero live findings (U10)
and leave-one-out. **Honest limits**: prose quality ceiling of mid-size models is real — the design
guarantees structure, facts, grounding, and validation deterministically, and buys prose quality
with decomposition + exemplars + calibration; where a step still can't clear its bar after the
ladder is exhausted, the deterministic fallback ships and the step is quarantine-reported — the
system never trades correctness for fluency.

## 11. Freshness model

Per product, pinned tuple — **content-derived fingerprints, never repo-HEAD-alone or timestamps**:
target-repo README blob hash + tree hashes of the consumed source paths (a docs-only upstream
commit that touches nothing consumed must NOT trigger regeneration; HEAD is recorded as provenance,
not as the trigger); engine **import-manifest revision** (+ per-component hashes of the imported
data/knowledge the product consumes); package-registry evidence identity (+ cache TTL policy — a
stale registry read is a finding, not a trigger); knowledge/factpack hash; **per-section
fingerprints** (registry entry + plugin + its checks + its prompts) and a separate
**document-global fingerprint** (global checks, assembly, contract invariants) — section change
reopens that section only; global change reopens the document (both proven by §16 tests);
embedding-index version; last successful generation id; last accepted/delivered README hash.
Operational semantics: state updates are atomic (temp+rename); per-product locks carry expiry +
the existing abandoned-lock recovery; external API reads are rate-limit-aware with per-cycle
budgets (hitting a limit defers the product, never partial-processes it); **quarantine** = a
product whose bounded repairs are exhausted or whose inputs are contradictory — it gets an
actionable report, stays excluded from reruns until an input changes, and never blocks siblings.
**Zero-call conditions (exact)**: tuple unchanged ⇒ no factpack rebuild, no LLM call, no embedding
call, no candidate write — one status row only; weekly deep pass recomputes fingerprints from
sources and re-runs validators over the existing candidate but still makes zero model calls when
fingerprints match.
Regenerate iff a relevant component changes (existing component-versioned scoping decides *which
stages* reopen) or the weekly deep pass forces revalidation. No-change ⇒ exit after tuple
comparison: zero LLM calls, zero PRs, one status row. All evidence freshness — including
hybrid-archetype re-verification — is keyed to these identity hashes, never to wall-clock dates
(fixes upstream U11's by-design daily decay). **Takeover idempotency** (binding): first run
against an aspose.org-delivered repo treats the live README as reconciliation source; acceptance
requires converge-to-no-op or an explained, classified trivial diff (Regeneration Comparison
Protocol) — proven on ≥2 published repos before any family rollout.

## 12–13. Scheduler/recovery + trust/GitHub policy

Reuse the production workflow's triggers; recovery via existing resume machinery + stage cache;
endpoint failure ⇒ breaker + defer + next-cycle retry; no partial writes ever. Trust ladder as ruled
(§8); GitHub authority: GH_TOKEN locally, App (2 Java repos, contents:read) for workflow-lane proof
only; `AuthorizationRecordV1` stays empty until owner grants per-repo; **metadata writes need added
App permissions — flagged as a future authorization boundary, candidate/handoff mode meanwhile**
(social preview is always prepare+handoff, never claimed applied, per idea.md).

## 14. Canonical task state (single source of truth)

**The JSON below is canonical.** The prose table after it is GENERATED from the JSON (by
`rebuild_s14.py`, re-validated on every regeneration: status enum, prereq referential integrity,
cycle-free, single ready root TP-00, every gate owned, **gate-order enforced structurally** (no
card depends on a later-gate card; G0 completion is a real prerequisite chain — TG-00 gates
TS-01, so no G1+ card can auto-transition `blocked->ready` while any G0 card is incomplete),
**registration enforced structurally** (every implementation card carries TS-03 in its prerequisite
ancestry), and full TG-08 reachability; the same data is materialized as the staged state file
that TS-03 lands in-repo; the TS-03 consistency test re-encodes these checks in-repo, including
the negative test that no G1 card becomes ready while any G0 card is incomplete). Never hand-edit
prose statuses.

**Status enum + complete transition model** -- `blocked | ready | in_progress | verification |
complete | quarantined | cancelled`. Transitions: `blocked->ready` (automatic when every prereq is
`complete` -- prereqs are ONLY task IDs); `ready->in_progress` (lane claims; coordinator approves
+ overlap validator green); `in_progress->verification` (lane returns evidence);
`verification->complete` (coordinator only, evidence verified + committed);
`verification->in_progress` (coordinator, repair; decrements retries_left);
`in_progress->quarantined` (coordinator: retries exhausted or contradictory inputs; report
required); `quarantined->ready` (coordinator, only when a listed input fingerprint changed);
`any->cancelled` (coordinator, reason required; terminal). A card with an external blocker whose
authority has not acted leaves the run **BLOCKED_PRODUCTION** at final verdict -- reported, never
skipped. Every transition from TS-03 onward appends to the transition ledger; the consistency test
rejects illegal transitions.

**Gate-ownership map** (every G-condition owned by cards; nothing exists only in prose):
**G0**: TP-00, TB-01, TB-02, TB-03, TB-04, TB-05, TB-06, TG-00. **G1**: TS-01, TS-02, TS-03. **G2**: TD-01, T1A, T1B, T2, T3, T4, TL-01. **G3**: T14, T5. **G4**: T6, T7A, T7B, T8, TP-11A, TW-01. **G5**: TA-01, T9. **G6**: T10, TU-01, TW-02, TW-03, TG-06A, TG-06B. **G7**: T7C, T7D, T7E, T7F, TP-11B, TF-01, T11, T13, TG-07. **G8**: TW-04, TW-05, T12, TG-08.
External (user) actions feeding G5/G8, never silently skipped: push of `main`; workflow dispatch;
App-installation confirmation on `aspose-cells-foss` + `aspose-3d-foss`; `LLM_BASE_URL` +
`LLM_API_KEY` repo secrets.

```json
{
 "schema": "freshness-service-taskcards-v3",
 "updated": "2026-08-15",
 "defaults": {
  "entry": "all prereqs complete + overlap validator green + lane worktree clean",
  "commit_authority": "coordinator only (rule 19); lane agents edit, never commit; zero pushes to origin",
  "failure_class": "per section-0 taxonomy; retries exhausted => quarantined with report, never a weakened gate",
  "rollback": "git revert the card's commits on its lane branch; invalidate caches by hash; card -> ready",
  "shared_paths": "via *.patch in lane evidence dir, applied+committed by coordinator in coord",
  "evidence_manifest": "sha256sums.txt at bundle root (CRLF-normalized, evidence/writer.py)",
  "transition_evidence": "append-only entry in transition-ledger.jsonl (live from TS-03; TP-00..TS-02 transitions recorded retroactively at TS-03)",
  "last_transition": "2026-08-15 bootstrap (plan repair); no live transitions yet",
  "fingerprints_note": "cards list input fingerprints where invalidation is non-obvious; default = owned_paths + prereq evidence hashes"
 },
 "cards": [
  {
   "id": "TP-00",
   "title": "Mandatory preflight",
   "status": "ready",
   "lane": "coordinator",
   "prereqs": [],
   "gate": "G0",
   "owned_paths": [
    "(read-only + worktree creation only)"
   ],
   "commands": [
    "git status/identity vs section-0 baseline; verify the 3 protected dirty paths unchanged",
    "readme-agent supervise --mission-action status (the ONLY read-only mission action)",
    "git ls-remote origin refs/readme-agent-state/* ; confirm durable mission-state version on origin (authority) vs local snapshots (v1188 handoff / v778 local-poc known divergent)",
    "tool probes (missing tool => governed install/fallback sub-task or true blocker, never quarantine on a guessed command): gh, docker, act, python, node, actionlint, mmdc (Mermaid CLI), pytest-xdist import check; LLM endpoint probe (env.py default https://llm.professionalize.com/v1); verify config/authorization/ absent; verify only 2 mode:full products; verify `readme-agent recovery-sweep` subcommand exists (cli.py:341 - top-level, NOT a supervise flag)",
    ".venv/Scripts/python.exe scripts/governance/run_full_pytest.py  # fresh baseline; ANY failure not in the section-0 list of 10 = STOP",
    ".venv/Scripts/python.exe scripts/governance/validate_plan_structure.py",
    "re-measure lean import set vs 108.5MB/3277 files (tolerance 10pct)",
    "git worktree add ../.fro-worktrees/coord -b freshness-service/integration <base-commit>  # Git Bash; all worktree paths forward-slash",
    "snapshot the user worktree invariant: git rev-parse HEAD + git status --porcelain byte-recorded; re-checked after EVERY card (branch, index, tracked modifications, untracked paths byte-identical)"
   ],
   "closeout": [
    "all checks recorded; zero unexplained deltas (else STOP rule fires: fail closed, return plan to repair)",
    "preflight evidence bundle with sha256sums.txt"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tp-00/",
   "retries_left": 1,
   "fingerprints": [
    "section-0 baseline record"
   ],
   "stop_rule": "material delta vs baseline => fail closed"
  },
  {
   "id": "TB-01",
   "title": "Refresh composition characterization baselines (7 constants)",
   "status": "blocked",
   "lane": "L-baseline",
   "prereqs": [
    "TP-00"
   ],
   "gate": "G0",
   "owned_paths": [
    "tests/unit/test_readme_composition_characterization.py",
    "tests/unit/test_agentic_readme_composition.py"
   ],
   "commands": [
    "set verified constants (round2-investigation-record.md in the repair bundle): cells cand=cbc79611b94171d7... plan=641b04c447144b0e...; 3d cand=676e0d9a81b82427... plan=f551bbaf2ee5f144...; pdf cand=617605150e13217c... plan=f54241b5acdbe8eb...; agentic plan=95639f4ff7e03c66... (full 64-hex values there)",
    "AGENT-EXECUTABLE diff acceptance (no human eyeball): render before/after Mermaid via mmdc to PNG in BOTH light and dark themes; agent visually inspects the rendered images; compare diagram semantics, node inventory completeness, edge set, clipping/overflow, light+dark readability, and unrelated-byte stability (non-Mermaid bytes identical); emit evidence images + a machine-readable comparison receipt; escalate to the human ONLY if repository governance explicitly requires subjective approval at this gate (none found)",
    "RA_BASETEMP=\"${LOCALAPPDATA//\\\\//}/Temp/ra-p\"; .venv/Scripts/python.exe -m pytest tests/unit/test_readme_composition_characterization.py tests/unit/test_agentic_readme_composition.py -q --basetemp \"$RA_BASETEMP\""
   ],
   "closeout": [
    "both files green; consider scripts/governance/refresh_composition_characterization.py (recurring need, none exists)"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tb-01/",
   "retries_left": 2,
   "fingerprints": [
    "src/readme_agent/presentation/*",
    "supervisor/stage_dependencies.py"
   ]
  },
  {
   "id": "TB-02",
   "title": "Retarget verified-source-opening evidence via cohort manifest",
   "status": "blocked",
   "lane": "L-baseline",
   "prereqs": [
    "TP-00"
   ],
   "gate": "G0",
   "owned_paths": [
    "tests/unit/test_verified_source_opening.py"
   ],
   "commands": [
    "replace hardcoded pdf--537b8273b185--bd8699b68869 with resolution from finalized-repository-readmes-v1/cohort-manifest.json (suffix = candidate_sha256[:12], drifts on every re-promotion by design: promotion_paths.py:12-25); current dir --189b3321da5e verified passing all 3 unchanged",
    "grep repo for other literal --<12hex> promoted paths; NEVER run promote_finalized_verified_readmes.py for this",
    "RA_BASETEMP=\"${LOCALAPPDATA//\\//}/Temp/ra-p\"; .venv/Scripts/python.exe -m pytest tests/unit/test_verified_source_opening.py -q --basetemp \"$RA_BASETEMP\""
   ],
   "closeout": [
    "3 tests green via manifest resolution; grep findings recorded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tb-02/",
   "retries_left": 2,
   "fingerprints": [
    "cohort-manifest.json"
   ]
  },
  {
   "id": "TB-03",
   "title": "Complete portfolio acceptance-chain fixture + BACKLOG row",
   "status": "blocked",
   "lane": "L-baseline",
   "prereqs": [
    "TP-00"
   ],
   "gate": "G0",
   "owned_paths": [
    "tests/unit/test_portfolio.py"
   ],
   "commands": [
    "extend fixture with full acceptance chain via bind_deterministic_validation/build_review_acceptance_binding + write_local_poc_review_evidence/write_local_poc_no_op_evidence (reuse, no hand-rolled JSON); contract tightened by e695713a1, fixture predates it",
    "GOV-014 BACKLOG row (target file plans/backlog-post-poc.md is a PROTECTED USER-DIRTY path this plan may never stage): prepare the exact row as a *.patch in this card's evidence dir; application is a named USER action after the user reconciles their dirty edits - never committed by this plan",
    "RA_BASETEMP=\"${LOCALAPPDATA//\\\\//}/Temp/ra-p\"; .venv/Scripts/python.exe -m pytest tests/unit/test_portfolio.py -q --basetemp \"$RA_BASETEMP\""
   ],
   "closeout": [
    "test green; BACKLOG row patch staged in evidence + user informed"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tb-03/",
   "retries_left": 2,
   "fingerprints": [
    "local_poc_acceptance_binding.py"
   ]
  },
  {
   "id": "TB-04",
   "title": "Reset LLM call-ledger accounting between tests",
   "status": "blocked",
   "lane": "L-baseline",
   "prereqs": [
    "TP-00"
   ],
   "gate": "G0",
   "owned_paths": [
    "src/readme_agent/llm/call_ledger.py",
    "tests/conftest.py"
   ],
   "commands": [
    "add reset_llm_call_accounting() (_CONTEXT.set(None)) + autouse teardown fixture (mirrors credential-isolation fixture conftest.py:16-39); real isolation defect: leaked ContextVar makes result order-dependent; ALSO the hosted-CI no-op RuntimeError",
    "RA_BASETEMP=\"${LOCALAPPDATA//\\//}/Temp/ra-p\"; .venv/Scripts/python.exe -m pytest tests/unit/test_llm_call_ledger.py tests/unit/test_local_poc_review_evidence.py -q --basetemp \"$RA_BASETEMP\"  # deterministic repro order; must pass"
   ],
   "closeout": [
    "ordered repro green; order-independent under -n 4 worksteal"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tb-04/",
   "retries_left": 2,
   "fingerprints": [
    "call_ledger.py"
   ]
  },
  {
   "id": "TB-05",
   "title": "Self-contained Note golden-workflow fixture (unblocks hosted CI)",
   "status": "blocked",
   "lane": "L-baseline",
   "prereqs": [
    "TP-00"
   ],
   "gate": "G0",
   "owned_paths": [
    "tests/fixtures/note_golden_workflow/",
    "tests/unit/test_golden_workflow_coordinates.py",
    "tests/unit/test_verified_template_golden_workflow.py",
    "tests/unit/test_python_golden_workflow.py"
   ],
   "commands": [
    "commit minimal collector input set (129KB measured): README.md, pyproject.toml, tools/regenerate_pdf_goldens.py, tests/test_aspose_note_pdf_goldens.py, tests/_pdf_goldens.py, tests/goldens/pdf/* (13); keep sha256 pins (README 180a16f74735..., revision 6d97a522a9ed...)",
    "CAUTION: collect_python_golden_workflow fails closed on len(candidates)!=1 - copy ONLY listed files",
    "retarget the 3 test modules from runs/baseline/ to the fixture; zero new skip markers"
   ],
   "closeout": [
    "6 formerly runner-broken tests pass without runs/baseline/; fixture provably real bytes via pins"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tb-05/",
   "retries_left": 2,
   "fingerprints": [
    "python_golden_workflow.py"
   ]
  },
  {
   "id": "TB-06",
   "title": "MAX_PATH runner doctrine (document, not code around)",
   "status": "blocked",
   "lane": "L-baseline",
   "prereqs": [
    "TP-00"
   ],
   "gate": "G0",
   "owned_paths": [
    "AGENTS.md testing-note patch PROPOSED as *.patch in evidence (AGENTS.md is a shared governance file: coordinator applies + commits)"
   ],
   "commands": [
    "record: run_full_pytest.py (which sets its own short basetemp internally) is the only supported full-suite entry point; targeted runs use the RA_BASETEMP pattern; test_trusted_transform_review 260-char path failure is ENV-DEPENDENT (proven: passes with short basetemp; LongPathsEnabled=0) - no exception record needed because it PASSES under the governed runner"
   ],
   "closeout": [
    "patch staged; coordinator applied + committed it"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tb-06/",
   "retries_left": 1
  },
  {
   "id": "TG-00",
   "title": "Baseline green verification (closes G0)",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TB-01",
    "TB-02",
    "TB-03",
    "TB-04",
    "TB-05",
    "TB-06"
   ],
   "gate": "G0",
   "owned_paths": [
    "(verification only)"
   ],
   "commands": [
    ".venv/Scripts/python.exe scripts/governance/run_full_pytest.py  in the coord worktree => expect ZERO failures",
    "record receipt runs/verification/pytest-full-latest.json content into evidence"
   ],
   "closeout": [
    "governed full suite green locally; hosted ci.yml status recorded when the user pushes (external; non-blocking here, feeds G5/G8)"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tg-00/",
   "retries_left": 1
  },
  {
   "id": "TS-01",
   "title": "Mission-graph retirement loader fix",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TG-00"
   ],
   "gate": "G1",
   "owned_paths": [
    "src/readme_agent/supervisor/mission_graph.py",
    "src/readme_agent/supervisor/mission_control.py",
    "tests/unit/test_mission_graph.py",
    "tests/unit/test_mission_control.py"
   ],
   "commands": [
    "extend _validate_graph (~line 270) so active-task dependencies may resolve to deferred_task_index entries with durable status CLOSED; counterpart in mission_control _DEPENDENCY_SATISFIED; exactly the fix the repo's own l8-horizon-01-deferral-2026-08-13/findings.md Finding 3 prescribes",
    "negative control test: dependency-ineligible task fails activation",
    ".venv/Scripts/python.exe scripts/governance/run_official_checks.py  (in coord worktree; clean tree required)"
   ],
   "closeout": [
    "tests + official checks green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-ts-01/",
   "retries_left": 1
  },
  {
   "id": "TS-02",
   "title": "Retire CLOSED actives; register umbrella L8-FRESH-00-FRESHNESS-SERVICE",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TS-01"
   ],
   "gate": "G1",
   "owned_paths": [
    "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
    "plans/investigations/control/level8-deferred-task-catalog.jsonl",
    "plans/investigations/evidence/agile-authority-reset-v1/migration-matrix.json"
   ],
   "commands": [
    "retire ONLY actives whose CLOSED status is confirmed in the CURRENT origin durable state (stale-CLOSED provenance caution from the findings file); DeferredTaskRecordV1 + index entries + sha256/record_count pins",
    "add umbrella TaskCardV1 (staged byte-complete in repair bundle): mission_id LEVEL8-CENTRAL-REPOSITORY-PRESENTATION, valid campaign/stage_goal/goal_ids, allowed/forbidden paths = ownership manifest, execution_focus; respect 15-active/5-ready/25-requirement budgets",
    "append new_tasks[] semantic sha256 to migration-matrix.json",
    ".venv/Scripts/python.exe scripts/governance/build_level8_requirement_taskcard_coverage.py --check",
    ".venv/Scripts/python.exe scripts/governance/validate_compact_authority.py  (EXPLICIT - not in official suite)",
    ".venv/Scripts/python.exe scripts/governance/run_official_checks.py"
   ],
   "closeout": [
    "graph loads; all four validators green; umbrella registered"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-ts-02/",
   "retries_left": 1
  },
  {
   "id": "TS-03",
   "title": "Materialize control inventory, transition ledger, ownership manifest, annex archive",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TS-02"
   ],
   "gate": "G1",
   "owned_paths": [
    "plans/investigations/control/freshness-service-taskcards.json",
    "plans/investigations/control/freshness-service-ownership.json",
    "plans/investigations/control/freshness-service-plan-annex-production-assessment-2026-08-15.md",
    "src/readme_agent/supervisor/freshness_taskcard_inventory.py",
    "scripts/governance/validate_freshness_lane_ownership.py",
    "tests/unit/test_freshness_taskcard_inventory.py",
    "tests/unit/test_freshness_lane_ownership.py"
   ],
   "commands": [
    "land the staged bytes (repair bundle) as the control inventory (STATIC definitions; typed pydantic schema + mirrored test; sha256-pinned from umbrella card); statuses live ONLY in the append-only transition-ledger.jsonl (evidence tree; precedent agile-authority-reset-v1/multi-agent-execution-plan.json) + umbrella durable status (sole runtime authority)",
    "overlap validator script + consistency test (ledger transitions legal per the section-14 model)",
    "archive frozen Annex A to the control path (frozen-checkpoint precedent)",
    ".venv/Scripts/python.exe scripts/governance/run_official_checks.py"
   ],
   "closeout": [
    "inventory+ledger+manifest+annex landed; validators green. TS-03 IS the registration gate: prerequisite of every implementation card"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-ts-03/",
   "retries_left": 1
  },
  {
   "id": "TA-01",
   "title": "Production workflow discovery-token scope fix",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TS-03"
   ],
   "gate": "G5",
   "owned_paths": [
    ".github/workflows/readme-agent-production.yml"
   ],
   "commands": [
    "add two lines to the discovery-token step: owner: aspose-cells-foss / repositories: Aspose.Cells-FOSS-for-Java (config bug d56ca3651: only 1 of 4 minting steps omits them => 404 on control-repo installation lookup, log-proven run 31867614801); preserves test count assertions (4x client-id, 3x permission-contents: read)",
    ".venv/Scripts/python.exe -m pytest tests/unit/test_production_workflow.py -q",
    "actionlint",
    "supply the USER: git push origin main + gh workflow run readme-agent-production.yml (dispatch is human-only; registry job proves in <1 min)",
    "INSTALLATION PROOF = the dispatch outcome itself: token-mint success/failure for BOTH Java orgs (aspose-cells-foss discovery mint + aspose-3d-foss per-matrix mint) IS the installation-scope evidence; ask for manual App-settings confirmation ONLY if the workflow result is ambiguous; no App permission or workflow action that can mutate a target repo is used in this plan"
   ],
   "closeout": [
    "local checks green; dispatch receipt recorded when user acts (external-pending; feeds G5, never silently skipped)"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-ta-01/",
   "retries_left": 2,
   "blocker": "external-partial",
   "unblock": "user push + dispatch; LLM_BASE_URL/LLM_API_KEY secrets if governance bars the agent from setting them"
  },
  {
   "id": "TD-01",
   "title": "Import storage re-measurement + confirmation",
   "status": "blocked",
   "lane": "L-import",
   "prereqs": [
    "TS-03",
    "TG-00"
   ],
   "gate": "G2",
   "owned_paths": [
    "import manifest (decision record)"
   ],
   "commands": [
    "re-measure lean set at D:/onedrive/Documents/GitHub/aspose.org (exclusions: knowledge/_vectors/, knowledge/*/*/scout/, data/backlinks/workspace/, __pycache__/; EXACT dir reports/repo-presenter only - sibling regen trees are 3.05GB); confirm 108.5MB/3277 files within 10pct, zero >50MB",
    "decision = plain git (evidence-resolved in plan repair); material deviation => fail closed to re-decision"
   ],
   "closeout": [
    "measured values + confirmation recorded in import manifest"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-td-01/",
   "retries_left": 1
  },
  {
   "id": "T1A",
   "title": "Import enumeration + snapshot manifest + reconstruction proof",
   "status": "blocked",
   "lane": "L-import",
   "prereqs": [
    "TD-01"
   ],
   "gate": "G2",
   "owned_paths": [
    "plans/investigations/evidence/imported-corpus-v1/"
   ],
   "commands": [
    "snapshot manifest: upstream remote https://github.com/aspose/aspose.org, base commit 7f72da4e14 (APPROXIMATE anchor - worktree dirty 4811M/209D/72 untracked), dirty marker, tracked-modification patch, deleted-file list, untracked inventory (dependency_extract.py is untracked; reports/repo-presenter/ exists ONLY in the worktree), per-file sha256",
    "reconstruction verification: rebuild the set from manifest into a temp dir; byte-identical diff REQUIRED (T1B is blocked without it)"
   ],
   "closeout": [
    "manifest complete; reconstruction test passed"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t1a/",
   "retries_left": 2
  },
  {
   "id": "T1B",
   "title": "Staged import execution",
   "status": "blocked",
   "lane": "L-import",
   "prereqs": [
    "T1A",
    "TL-01"
   ],
   "gate": "G2",
   "owned_paths": [
    "src/readme_agent/vendored_asposeorg/",
    "data/imported/"
   ],
   "commands": [
    "copy per manifest; scrub hardcoded C:/Users/prora/... docstring paths (3 foss modules); per-file 'Adapted from aspose.org: <path> @ <sha>' headers + IMPORTED-FROM.md (existing repo convention); apply destination license deliberately (upstream has NO license file - first-party corporate code)",
    "content-level secret scan (filename-level already clean)",
    ".venv/Scripts/python.exe scripts/governance/run_official_checks.py"
   ],
   "closeout": [
    "every consumer resolves in-repo; staged reviewable commits; license/attribution/secret-scan clean"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t1b/",
   "retries_left": 2
  },
  {
   "id": "T2",
   "title": "Golden-authority retirement (harvest first)",
   "status": "blocked",
   "lane": "L-contract",
   "prereqs": [
    "TS-03",
    "TG-00"
   ],
   "gate": "G2",
   "owned_paths": [
    "golden-sample/** (the authority dir)",
    "code/doc references to golden-sample (grep-enumerated into evidence BEFORE edits; overlap validator runs on the ACTUAL changed set)",
    "NOTE: src/readme_agent/golden_set/ (LLM route qualification) is UNRELATED and untouched"
   ],
   "commands": [
    "harvest reusable golden assets into the corpus/calibration inputs; stamp golden runner surfaces retired; drift test that golden files are no longer an authority"
   ],
   "closeout": [
    "retirement + harvest evidence recorded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t2/",
   "retries_left": 2
  },
  {
   "id": "T3",
   "title": "Vendored check battery + section/global mapping",
   "status": "blocked",
   "lane": "L-contract",
   "prereqs": [
    "T1B"
   ],
   "gate": "G2",
   "owned_paths": [
    "src/readme_agent/validation/aspose_checks/** (new)",
    "tests/unit/test_aspose_checks_battery.py (new)",
    "docs/readme-process.md"
   ],
   "commands": [
    "vendor the 81-check battery with path/config indirection + fail-closed fixtures per check; classify every check section-scoped vs document-global (enables plug-and-play, validated by section-16 agility tests); derived check inventory (grep/tests), never prose counts; drift test vs docs"
   ],
   "closeout": [
    "battery green on corpus fixtures; mapping complete"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t3/",
   "retries_left": 2
  },
  {
   "id": "T4",
   "title": "Merged factpack + evidence views + trust surfaces",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T1B"
   ],
   "gate": "G2",
   "owned_paths": [
    "src/readme_agent/facts/composer_factpack.py (new)",
    "src/readme_agent/facts/render_views.py (new view only)",
    "tests/unit/test_composer_factpack.py (new)"
   ],
   "commands": [
    "adapter builds ComposerFactpack from ProductFactsV2 + 13 vendored detectors; EvidenceGroundedRenderViewV2 (closes RC1); per-source staleness/coverage finding surfaces (U7)"
   ],
   "closeout": [
    "factpack schema tests green; views grounded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t4/",
   "retries_left": 2
  },
  {
   "id": "T14",
   "title": "Section registry + plugin framework",
   "status": "blocked",
   "lane": "L-contract",
   "prereqs": [
    "T3",
    "T4"
   ],
   "gate": "G3",
   "owned_paths": [
    "templates/readme/section-registry-v2.json (new)",
    "src/readme_agent/presentation/sections/** (new plugin package)",
    "tests/unit/test_section_registry.py (new)"
   ],
   "commands": [
    "registry v1 reproduces current contract byte-compatibly; plugin add/remove/reorder with zero cross-cutting edits; registry hash joins freshness tuple; section-16 agility tests a-d"
   ],
   "closeout": [
    "agility tests green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t14/",
   "retries_left": 2
  },
  {
   "id": "T5",
   "title": "Deterministic pilot skeleton (cells/python)",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T14"
   ],
   "gate": "G3",
   "owned_paths": [
    "deterministic composer steps"
   ],
   "commands": [
    "full deterministic section set for cells/python; full check battery + Docker verification; byte-identical double run"
   ],
   "closeout": [
    "G3: full battery green + byte-identical double run"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t5/",
   "retries_left": 2
  },
  {
   "id": "T6",
   "title": "Calibration harness",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T5"
   ],
   "gate": "G4",
   "owned_paths": [
    "scripts/calibration/"
   ],
   "commands": [
    "per-step reference fragments from imported corpus; deterministic scoring (gates/shape/lexical/embedding/groundedness/banned-vocab); scorecards keyed by prompt hash; regression gate on prompt bumps; zero-live-findings exemplar screen (U10), leave-one-out"
   ],
   "closeout": [
    "harness runs on pilot fragments; scorecards emitted"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t6/",
   "retries_left": 2
  },
  {
   "id": "T7A",
   "title": "Slot-step: opening summary",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T6"
   ],
   "gate": "G4",
   "owned_paths": [
    "slot-step module + prompts/generation manifest"
   ],
   "commands": [
    "forced tool-call schema; prohibition list; deterministic post-validation; <=2 repairs; decomposition-ladder position recorded; deterministic fallback"
   ],
   "closeout": [
    "calibration bar met or ladder-exhausted fallback recorded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t7a/",
   "retries_left": 2
  },
  {
   "id": "T7B",
   "title": "Slot-step: capability bullets",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T6"
   ],
   "gate": "G4",
   "owned_paths": [
    "slot-step module + manifest"
   ],
   "commands": [
    "same mechanics as T7A; semantic-duplicate screen (embedding)"
   ],
   "closeout": [
    "bar met or fallback recorded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t7b/",
   "retries_left": 2
  },
  {
   "id": "T7C",
   "title": "Slot-step: limitations + summary",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T7B"
   ],
   "gate": "G7",
   "owned_paths": [
    "slot-step module + manifest"
   ],
   "commands": [
    "same mechanics"
   ],
   "closeout": [
    "bar met or fallback recorded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t7c/",
   "retries_left": 2
  },
  {
   "id": "T7D",
   "title": "Slot-step: dispositions residue",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T7B"
   ],
   "gate": "G7",
   "owned_paths": [
    "slot-step module + manifest"
   ],
   "commands": [
    "deterministic pre-filter -> embedding shortlists -> per-unit classification from evidence-ID menus only; content_unit_* gates"
   ],
   "closeout": [
    "bar met; gates green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t7d/",
   "retries_left": 2
  },
  {
   "id": "T7E",
   "title": "Slot-step: preserved-unit restyles",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T7D"
   ],
   "gate": "G7",
   "owned_paths": [
    "slot-step module + manifest"
   ],
   "commands": [
    "restyle preserves fact content exactly; preservation gate (4b) validates"
   ],
   "closeout": [
    "bar met; preservation checks green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t7e/",
   "retries_left": 2
  },
  {
   "id": "T7F",
   "title": "Slot-steps: quickstart lead + examples brief",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T7A"
   ],
   "gate": "G7",
   "owned_paths": [
    "slot-step modules + manifests"
   ],
   "commands": [
    "same mechanics"
   ],
   "closeout": [
    "bar met or fallback recorded"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t7f/",
   "retries_left": 2
  },
  {
   "id": "T8",
   "title": "Repair routing + fragment pinning + no-op proof",
   "status": "blocked",
   "lane": "L-compose",
   "prereqs": [
    "T7A",
    "T7B",
    "TP-11A"
   ],
   "gate": "G4",
   "owned_paths": [
    "repair router, fragment pin store"
   ],
   "commands": [
    "finding->step routing repairs only the owning step; first-accepted-wins pinning; NO-OP PROOF: unchanged inputs => byte-identical output, zero LLM + zero embedding calls (ledger-proven)"
   ],
   "closeout": [
    "G4: no-op proof green on pilot"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t8/",
   "retries_left": 2
  },
  {
   "id": "TP-11A",
   "title": "Preservation core, deterministic (pilot gate)",
   "status": "blocked",
   "lane": "L-contract",
   "prereqs": [
    "T3",
    "T5"
   ],
   "gate": "G4",
   "owned_paths": [
    "src/readme_agent/presentation/original_preservation.py (new)",
    "tests/unit/test_original_preservation.py"
   ],
   "commands": [
    "unit extraction w/ excerpt hashes (U8 bijection every cycle); evidence re-resolution every cycle (U9); closed disposition enum (section 4b); deterministic dispositions only (preserved / merged-exact / omitted_invalid-with-evidence / blocked_unverified); EVERY original unit accounted - residuals awaiting LLM classification are explicitly blocked_unverified, never absent; original-to-candidate reconciliation matrix artifact; coverage floor for preservation-class content",
    "NEGATIVE TESTS: silently-dropped verified detail MUST fail validation (one fixture per preservation-class category); positionally-shifted ledger MUST trip the bijection check"
   ],
   "closeout": [
    "pilot (MS1/G4) cannot complete or be called reviewable without full unit accounting; tests green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tp-11a/",
   "retries_left": 2
  },
  {
   "id": "TP-11B",
   "title": "Preservation enhancement: LLM residual dispositions",
   "status": "blocked",
   "lane": "L-contract",
   "prereqs": [
    "TP-11A",
    "T7D"
   ],
   "gate": "G7",
   "owned_paths": [
    "residual-disposition integration in original_preservation.py",
    "tests/unit/test_original_preservation.py additions"
   ],
   "commands": [
    "route TP-11A's blocked_unverified residue through T7D's classification (evidence-ID menus only); matrix updated in place; all TP-11A gates re-run after enhancement"
   ],
   "closeout": [
    "portfolio rollout blocked until residual dispositions resolve or carry explicit blocked_unverified rationale"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tp-11b/",
   "retries_left": 2
  },
  {
   "id": "T9",
   "title": "Freshness engine + scheduler wiring",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "T5"
   ],
   "gate": "G5",
   "owned_paths": [
    "freshness/queue modules"
   ],
   "commands": [
    "content-derived fingerprint tuple (section 11); EXTENDS the existing freshness evaluator (_evaluate_local_poc_cache / validate_acceptance_artifact_chain) - never parallels it; document supersession vs FRESH-001..006 contracts (no-silent-duplicates rule); zero-call no-change fast path; scheduler wiring on existing workflow triggers"
   ],
   "closeout": [
    "G5 local: no-change fast path + resume + endpoint-failure drill + bounded repair proven"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t9/",
   "retries_left": 2
  },
  {
   "id": "T10",
   "title": "Link-semantics validators + relationship model",
   "status": "blocked",
   "lane": "L-contract",
   "prereqs": [
    "TS-03",
    "TG-00"
   ],
   "gate": "G6",
   "owned_paths": [
    "link-semantics modules + tests"
   ],
   "commands": [
    "destination-driven MT044 anchor contract; all aspose product/docs/kb/reference hosts both domains; anchor-platform vs destination comparison (the shipped-defect class); duplicate-destination detection; never-via"
   ],
   "closeout": [
    "validators green over imported corpus (62/62 clean expected) + this repo's candidates"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t10/",
   "retries_left": 2
  },
  {
   "id": "TU-01",
   "title": "U1-U20 register enforcement table test",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "T3",
    "T10"
   ],
   "gate": "G6",
   "owned_paths": [
    "register table test"
   ],
   "commands": [
    "table test asserting each U-id resolves to an existing test/module; register row without live control fails"
   ],
   "closeout": [
    "test green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tu-01/",
   "retries_left": 1
  },
  {
   "id": "TW-01",
   "title": "Remote-write defense in depth (system-owned execution)",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "TS-03",
    "TG-00"
   ],
   "gate": "G4",
   "owned_paths": [
    "src/readme_agent/delivery/remote_write_guard.py (new)",
    "credential-scoping changes in target-clone/subprocess launch paths",
    "tests/unit/test_remote_write_guard.py"
   ],
   "commands": [
    "HONEST SCOPE: the guard controls SYSTEM-OWNED execution (this runtime, its subprocesses, supervisors, recovery, resumed runs); it cannot and does not claim to stop an independent human or arbitrary process with separate credentials - that residual risk is stated, not defined away",
    "layer 1 credentials: pre-approval, target-repo operations receive read-only credentials where available; write-capable GH_TOKEN/Git credentials are REMOVED/MASKED from every target-repo subprocess environment; target clones launch with credential-helper inheritance disabled (git -c credential.helper= + scrubbed env) so ambient push-capable helpers cannot leak in",
    "layer 2 transport guard: single choke-point for every system-owned git push + GitHub API mutation; rejects push destinations matching real target remotes (allow-list from data/products.json orgs, matched across HTTPS/SSH/alternate URL forms); blocks every mutating API method pre-approval; enable-condition = verified portfolio approval receipt (TW-05) ONLY; fail closed on missing/malformed/stale/ambiguous approval state; rejected attempts recorded",
    "layer 3 independent gates: AuthorizationRecordV1 registry + the portfolio receipt remain separate necessary conditions",
    "REGRESSION TESTS: direct helper invocation, subprocess invocation, HTTPS + SSH + alternate URL forms, draft-PR creation (a draft PR IS a remote write), issue creation, metadata change, resumed/recovery paths - all rejected pre-approval + recorded; credential-scrub test proves target subprocess env carries no write-capable token"
   ],
   "closeout": [
    "defense-in-depth proven by tests BEFORE any delivery-capable lane runs; zero system-owned target-write paths open"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tw-01/",
   "retries_left": 1
  },
  {
   "id": "TL-01",
   "title": "Import licensing / authorization gate",
   "status": "blocked",
   "lane": "L-import",
   "prereqs": [
    "TD-01"
   ],
   "gate": "G2",
   "owned_paths": [
    "licensing-authorization record in plans/investigations/evidence/imported-corpus-v1/"
   ],
   "commands": [
    "identify copyright owner + source-repo licensing status (verified: NO LICENSE/COPYING/NOTICE upstream; origin github.com/aspose/aspose.org; default = all rights reserved); verify authority to copy/modify/relicense - DO NOT infer from same-company relatedness; record an explicit internal authorization (user/owner attestation naming scope) or other legally sufficient provenance",
    "preserve any copyright/provenance notices found in imported files; inline 'Adapted from' headers ONLY in comment-supporting formats (.py); manifest-level provenance for JSON/Markdown/corpus files where headers would corrupt syntax or alter accepted candidate bytes; corpus stays byte-identical where calibration requires original bytes; NO destination license applied to the imported material without demonstrated authority",
    "missing legal authority => genuine external-authority blocker: T1B stays blocked"
   ],
   "closeout": [
    "authorization record exists and covers the enumerated import set, or card reports blocked-external"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tl-01/",
   "retries_left": 1,
   "blocker": "external-potential",
   "unblock": "explicit owner authorization attestation for the import set"
  },
  {
   "id": "TF-01",
   "title": "Font/Python audit conversion + regeneration acceptance proof",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "T8",
    "T7C",
    "T7E",
    "T7F",
    "TP-11B",
    "T10"
   ],
   "gate": "G7",
   "owned_paths": [
    "portfolio-wide machinery requirements derived from the audit (global modules/tests, NO Font-specific hardcoding)",
    "Font/Python candidate + evidence"
   ],
   "commands": [
    "read the COMPLETE Font/Python audit record set at plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/font--800ea256fec1--636bf4e263cc/ (ORIGINAL-README.md, README.md, claim-map.json, deterministic-validation.json, independent-agent-review.json, repair-history.json, no-op-proof.json, provenance.json + the rest) plus any newer Font/Python audit artifacts the TP-00 sweep finds; convert EVERY global finding into a portfolio-wide machinery requirement + regression test (global machinery, never a Font-specific exception)",
    "regenerate the Font/Python candidate locally AFTER the global fixes; preserve every verified detail from the current Font/Python README through the section-4b disposition/reconciliation contract; produce its original-to-candidate reconciliation matrix",
    "PROOFS: silently dropping any verified Font/Python detail fails validation (negative fixture); byte-idempotency on a second unchanged run with zero LLM + zero embedding calls (ledger-proven); section-scoped idempotency - changing one section's input regenerates ONLY that section, all unrelated Font/Python sections byte-identical"
   ],
   "closeout": [
    "Font/Python candidate + audit closeout are prerequisites of the complete-portfolio rollout (TG-07)"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tf-01/",
   "retries_left": 2
  },
  {
   "id": "TW-02",
   "title": "Local delivery E2E simulation harness (22 steps, zero target contact)",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "T8",
    "TW-01"
   ],
   "gate": "G6",
   "owned_paths": [
    "E2E simulation harness + local bare-repo fixtures + mocked GitHub API"
   ],
   "commands": [
    "exercise ALL 22 amendment steps (discovery, source sync, fact refresh, reconciliation, generation, deterministic validation, example verification, rendering, diff isolation, disposable clone, temp branch, approved-files-only copy, commit construction, changed-path verification, simulated push, simulated PR, simulated CI/checks, simulated merge, branch cleanup, interruption recovery, duplicate-run prevention, second-run idempotency)",
    "REAL git operations + state transitions against ISOLATED LOCAL BARE REPOS + disposable clones + mocked/sandboxed GitHub API; simulated push/PR NEVER pointed at a real target remote; print-what-it-would-do is NOT proof",
    "REGRESSION TEST: failed local E2E blocks approval (portfolio state cannot reach AWAITING_GLOBAL_HUMAN_REVIEW)"
   ],
   "closeout": [
    "all 22 steps pass locally; no target repository contacted for writes (guard logs prove zero attempts)"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tw-02/",
   "retries_left": 2
  },
  {
   "id": "TW-03",
   "title": "Portfolio + product state machines + accountability matrix",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "TS-03"
   ],
   "gate": "G6",
   "owned_paths": [
    "portfolio state modules + inventory matrix schema + tests"
   ],
   "commands": [
    "product states DISCOVERED->INPUTS_PINNED->GENERATED->LOCALLY_VALIDATED->LOCALLY_E2E_VERIFIED->READY_FOR_PORTFOLIO_REVIEW->HUMAN_APPROVED->REMOTE_ELIGIBLE; portfolio states PORTFOLIO_DISCOVERED->...->AWAITING_GLOBAL_HUMAN_REVIEW->GLOBALLY_APPROVED->REMOTE_WRITES_ENABLED",
    "REMOTE_WRITES_ENABLED reachable ONLY when every in-scope product is HUMAN_APPROVED + aggregate gates pass; per-entry record: family, platform, target repo, active/excluded + authoritative exclusion reason, candidate path, source revision, existing README hash, candidate hash, validation result, E2E result, review status; silent omission (blocked/difficult/unchanged) forbidden",
    "AWAITING_GLOBAL_HUMAN_REVIEW reachable ONLY when every active in-scope product has: candidate README, complete original-README reconciliation, factual/example/link/rendering/preservation/idempotency/local-E2E gates passed, and NO unresolved quarantine or blocked state; any quarantined product => portfolio verdict BLOCKED_PORTFOLIO, not an approvable bundle",
    "REGRESSION TESTS: one approved README cannot open the global gate; an unreviewed/failed/stale/blocked/quarantined product blocks ALL remote writes AND blocks AWAITING_GLOBAL_HUMAN_REVIEW"
   ],
   "closeout": [
    "state machines + matrix live in supervisor state contracts; tests green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tw-03/",
   "retries_left": 2
  },
  {
   "id": "TW-04",
   "title": "Portfolio human-review bundle builder",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "TG-07",
    "TW-03"
   ],
   "gate": "G8",
   "owned_paths": [
    "review-bundle builder + browsable local index"
   ],
   "commands": [
    "one complete local bundle: portfolio inventory, every candidate README, diff vs each target's current README, preservation report (4b matrix), factual/example/link+rendering/idempotency/E2E results, blocked-or-waived checks, candidate + source hashes, exact per-repo changed-path list, portfolio readiness matrix",
    "human inspects every candidate WITHOUT touching internal run directories (single browsable index)",
    "quarantined/blocked products appear DIAGNOSTICALLY but the bundle is stamped NON-APPROVABLE whenever any exists (BLOCKED_PORTFOLIO)"
   ],
   "closeout": [
    "bundle builds for the complete portfolio; approvable stamp ONLY when every active product fully passed"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tw-04/",
   "retries_left": 2
  },
  {
   "id": "TW-05",
   "title": "Approval receipt + invalidation machinery",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "TW-02",
    "TW-03"
   ],
   "gate": "G8",
   "owned_paths": [
    "receipt schema + invalidation watchers + tests"
   ],
   "commands": [
    "immutable-after-creation receipt: inventory revision, per-candidate hash, per-target source commit, validation-result hashes, E2E-result hash, timestamp, human note, identity per existing governance mechanism (AuthorizationRecordV1 registry); remote ops must re-verify candidate + target revision against the receipt",
    "invalidation on: candidate byte change; target README change; relevant default-branch advance; inventory change; validator/contract change; E2E-vs-implementation drift; regeneration; any gate invalidation => remote writes stay disabled, affected products revalidated, bundle rebuilt, COMPLETE portfolio re-approved (never silently carried forward)",
    "REGRESSION TESTS: candidate-hash drift invalidates; target-revision drift invalidates; inventory change invalidates; fully-approved unchanged portfolio enables the governed remote path; second local run idempotent"
   ],
   "closeout": [
    "receipt + invalidation proven by tests; post-approval execution rules (hash/revision recheck, authorized-files-only, bounded lanes, drift stops product + reassesses receipt, approved bytes exact, per-action receipts) encoded for the future phase"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tw-05/",
   "retries_left": 2
  },
  {
   "id": "TG-06A",
   "title": "Family pilot: complete cells family",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "T8",
    "T9",
    "T10",
    "TU-01",
    "TW-01"
   ],
   "gate": "G6",
   "owned_paths": [
    "(gate verification)"
   ],
   "commands": [
    "all 6 cells products through the full pipeline; cells/java workflow-lane read-only proof; per-product candidates or quarantine reports"
   ],
   "closeout": [
    "G6 evidence bundle; MS4"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tg-06a/",
   "retries_left": 1
  },
  {
   "id": "TG-06B",
   "title": "Takeover-idempotency proof (>=2 published repos)",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "T8",
    "T10"
   ],
   "gate": "G6",
   "owned_paths": [
    "(gate verification)"
   ],
   "commands": [
    "first run vs aspose.org-delivered README treats live README as reconciliation source; converge-to-no-op or explained trivial diff (Regeneration Comparison Protocol)"
   ],
   "closeout": [
    "proof on >=2 published repos; MS3"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tg-06b/",
   "retries_left": 2
  },
  {
   "id": "T11",
   "title": "Metadata engine (candidate/handoff mode)",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "TG-06A"
   ],
   "gate": "G7",
   "owned_paths": [
    "metadata-engine modules"
   ],
   "commands": [
    "description/topics/homepage/community/social-preview-handoff proposals from historical design; candidate artifacts only (App metadata permissions = named future boundary)"
   ],
   "closeout": [
    "family metadata candidates emitted"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t11/",
   "retries_left": 2
  },
  {
   "id": "T13",
   "title": "Issue-filing lane (drafts only)",
   "status": "blocked",
   "lane": "L-service",
   "prereqs": [
    "TG-06A"
   ],
   "gate": "G7",
   "owned_paths": [
    "issue-lane modules"
   ],
   "commands": [
    "U20 structured defect drafts + dedupe vs open issues (public API reads); draft-mode never writes (test-proven); filing needs future issues:write grant"
   ],
   "closeout": [
    "draft lane green; dedupe fixture test green"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t13/",
   "retries_left": 2
  },
  {
   "id": "TG-07",
   "title": "Portfolio rollout (complete portfolio, locally; family order = generation sequencing only)",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TG-06A",
    "TG-06B",
    "T7C",
    "T7D",
    "T7E",
    "T7F",
    "TP-11B",
    "TF-01",
    "T11",
    "T13",
    "TW-02",
    "TW-03"
   ],
   "gate": "G7",
   "owned_paths": [
    "(gate verification)"
   ],
   "commands": [
    "live registry enumeration each cycle (no hardcoded lists); EVERY active product accounted (matrix row); family order is local generation sequencing only, NEVER per-family remote eligibility; metadata + issue drafts part of rollout DoD; zero target writes (guard active)",
    "PORTFOLIO-WIDE IDEMPOTENCY (amendment): every portfolio product run twice from unchanged pinned inputs; second run = zero LLM + zero embedding calls, candidate bytes + reconciliation matrices unchanged, no candidate/state/issue-draft/metadata-proposal/review-artifact rewritten unnecessarily; one section-input change regenerates only that section (unrelated sections byte-identical); a document-global contract change invalidates the whole document; cross-product changes never invalidate unrelated products; per-product idempotency matrix emitted",
    "QUARANTINE SEMANTICS: quarantine lets SAFE SIBLING LANES continue but a quarantined/blocked product makes the PORTFOLIO non-approvable - rollout closes as BLOCKED_PORTFOLIO for approval purposes; 'candidate or quarantine report' NEVER satisfies the approval gate; only an authoritative pre-existing registry exclusion may be absent (reason in the matrix)"
   ],
   "closeout": [
    "G7 evidence incl. idempotency matrix; MS5; portfolio state advances to review-eligible ONLY if every active product fully passed"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tg-07/",
   "retries_left": 1
  },
  {
   "id": "T12",
   "title": "Retirements (old composer surfaces, SEO gen, poc stamp)",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TG-07"
   ],
   "gate": "G8",
   "owned_paths": [
    "plan_readme_composition diagram/section surfaces (exact modules grep-enumerated into evidence before edits)",
    "the SEO title generator module",
    "commands_poc.py (diagnostic-only stamp)"
   ],
   "commands": [
    "retire per resolution 11 after parity; poc runner stamped diagnostic-only at G1 remains"
   ],
   "closeout": [
    "retirement commits + drift tests"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-t12/",
   "retries_left": 1
  },
  {
   "id": "TG-08",
   "title": "Final regression + state reconciliation + aggregate evidence + portfolio review handoff",
   "status": "blocked",
   "lane": "coordinator",
   "prereqs": [
    "TG-07",
    "T12",
    "TA-01",
    "T2",
    "TW-04",
    "TW-05"
   ],
   "gate": "G8",
   "owned_paths": [
    "(gate verification)"
   ],
   "commands": [
    ".venv/Scripts/python.exe scripts/governance/run_full_pytest.py => ZERO failures (TG-00 standard maintained; no NEW failures ever excepted)",
    ".venv/Scripts/python.exe scripts/governance/run_official_checks.py",
    ".venv/Scripts/python.exe scripts/governance/validate_compact_authority.py",
    "state reconciliation (ledger vs umbrella durable status); aggregate bundle per section-0 spec: loose diffable files + sha256sums.txt in the repo evidence tree, PLUS a handoff ZIP of the finalized bundle stored OUTSIDE tracked source paths with its own SHA-256; report BOTH absolute paths + the ZIP hash; includes the TW-04 portfolio review bundle, the per-product idempotency matrix, and guard logs proving ZERO system-owned target-write attempts",
    "final verdict precedence: any quarantined/blocked active product => BLOCKED_PORTFOLIO; hosted-proof shortfall => BLOCKED_PRODUCTION (may co-report); otherwise terminal portfolio state AWAITING_GLOBAL_HUMAN_REVIEW"
   ],
   "closeout": [
    "bundle + ZIP exist for successful/quarantined/failed/blocked outcomes alike; both absolute paths + ZIP sha256 reported"
   ],
   "evidence": "plans/investigations/evidence/freshness-service-tg-08/",
   "retries_left": 1
  }
 ]
}
```

**Generated prose view** (regenerate, never hand-edit):

| id | title | status | lane | gate | prereqs |
|---|---|---|---|---|---|
| TP-00 | Mandatory preflight | ready | coordinator | G0 | -- |
| TB-01 | Refresh composition characterization baselines (7 constants) | blocked | L-baseline | G0 | TP-00 |
| TB-02 | Retarget verified-source-opening evidence via cohort manifest | blocked | L-baseline | G0 | TP-00 |
| TB-03 | Complete portfolio acceptance-chain fixture + BACKLOG row | blocked | L-baseline | G0 | TP-00 |
| TB-04 | Reset LLM call-ledger accounting between tests | blocked | L-baseline | G0 | TP-00 |
| TB-05 | Self-contained Note golden-workflow fixture (unblocks hosted CI) | blocked | L-baseline | G0 | TP-00 |
| TB-06 | MAX_PATH runner doctrine (document, not code around) | blocked | L-baseline | G0 | TP-00 |
| TG-00 | Baseline green verification (closes G0) | blocked | coordinator | G0 | TB-01, TB-02, TB-03, TB-04, TB-05, TB-06 |
| TS-01 | Mission-graph retirement loader fix | blocked | coordinator | G1 | TG-00 |
| TS-02 | Retire CLOSED actives; register umbrella L8-FRESH-00-FRESHNESS-SERVICE | blocked | coordinator | G1 | TS-01 |
| TS-03 | Materialize control inventory, transition ledger, ownership manifest, annex archive | blocked | coordinator | G1 | TS-02 |
| TA-01 | Production workflow discovery-token scope fix | blocked | coordinator | G5 | TS-03 |
| TD-01 | Import storage re-measurement + confirmation | blocked | L-import | G2 | TS-03, TG-00 |
| T1A | Import enumeration + snapshot manifest + reconstruction proof | blocked | L-import | G2 | TD-01 |
| T1B | Staged import execution | blocked | L-import | G2 | T1A, TL-01 |
| T2 | Golden-authority retirement (harvest first) | blocked | L-contract | G2 | TS-03, TG-00 |
| T3 | Vendored check battery + section/global mapping | blocked | L-contract | G2 | T1B |
| T4 | Merged factpack + evidence views + trust surfaces | blocked | L-compose | G2 | T1B |
| T14 | Section registry + plugin framework | blocked | L-contract | G3 | T3, T4 |
| T5 | Deterministic pilot skeleton (cells/python) | blocked | L-compose | G3 | T14 |
| T6 | Calibration harness | blocked | L-compose | G4 | T5 |
| T7A | Slot-step: opening summary | blocked | L-compose | G4 | T6 |
| T7B | Slot-step: capability bullets | blocked | L-compose | G4 | T6 |
| T7C | Slot-step: limitations + summary | blocked | L-compose | G7 | T7B |
| T7D | Slot-step: dispositions residue | blocked | L-compose | G7 | T7B |
| T7E | Slot-step: preserved-unit restyles | blocked | L-compose | G7 | T7D |
| T7F | Slot-steps: quickstart lead + examples brief | blocked | L-compose | G7 | T7A |
| T8 | Repair routing + fragment pinning + no-op proof | blocked | L-compose | G4 | T7A, T7B, TP-11A |
| TP-11A | Preservation core, deterministic (pilot gate) | blocked | L-contract | G4 | T3, T5 |
| TP-11B | Preservation enhancement: LLM residual dispositions | blocked | L-contract | G7 | TP-11A, T7D |
| T9 | Freshness engine + scheduler wiring | blocked | L-service | G5 | T5 |
| T10 | Link-semantics validators + relationship model | blocked | L-contract | G6 | TS-03, TG-00 |
| TU-01 | U1-U20 register enforcement table test | blocked | coordinator | G6 | T3, T10 |
| TW-01 | Remote-write defense in depth (system-owned execution) | blocked | L-service | G4 | TS-03, TG-00 |
| TL-01 | Import licensing / authorization gate | blocked | L-import | G2 | TD-01 |
| TF-01 | Font/Python audit conversion + regeneration acceptance proof | blocked | coordinator | G7 | T8, T7C, T7E, T7F, TP-11B, T10 |
| TW-02 | Local delivery E2E simulation harness (22 steps, zero target contact) | blocked | L-service | G6 | T8, TW-01 |
| TW-03 | Portfolio + product state machines + accountability matrix | blocked | L-service | G6 | TS-03 |
| TW-04 | Portfolio human-review bundle builder | blocked | L-service | G8 | TG-07, TW-03 |
| TW-05 | Approval receipt + invalidation machinery | blocked | L-service | G8 | TW-02, TW-03 |
| TG-06A | Family pilot: complete cells family | blocked | coordinator | G6 | T8, T9, T10, TU-01, TW-01 |
| TG-06B | Takeover-idempotency proof (>=2 published repos) | blocked | coordinator | G6 | T8, T10 |
| T11 | Metadata engine (candidate/handoff mode) | blocked | L-service | G7 | TG-06A |
| T13 | Issue-filing lane (drafts only) | blocked | L-service | G7 | TG-06A |
| TG-07 | Portfolio rollout (complete portfolio, locally; family order = generation sequencing only) | blocked | coordinator | G7 | TG-06A, TG-06B, T7C, T7D, T7E, T7F, TP-11B, TF-01, T11, T13, TW-02, TW-03 |
| T12 | Retirements (old composer surfaces, SEO gen, poc stamp) | blocked | coordinator | G8 | TG-07 |
| TG-08 | Final regression + state reconciliation + aggregate evidence + portfolio review handoff | blocked | coordinator | G8 | TG-07, T12, TA-01, T2, TW-04, TW-05 |

**Uniform card mechanics**: all commands are Git Bash syntax (forward-slash paths; targeted
pytest uses the task variable `RA_BASETEMP="${LOCALAPPDATA//\\//}/Temp/ra-p"` -- never `%TEMP%`,
never repurposed HOME/system variables); all work in lane worktrees on local `freshness-service/*`
branches (section-0 model; zero pushes; the user's `main` worktree is NEVER updated by this plan);
before a dependent card starts, the coordinator syncs its lane branch with the latest
`freshness-service/integration` (merge into the lane branch, or recreate the lane worktree from
integration); commits by the coordinator only, one card per commit series; the overlap validator
runs against the ACTUAL changed-file set (`git diff --name-only`) of every card, not only declared
patterns; evidence to the card's `plans/investigations/evidence/freshness-service-<id>/` dir with
`sha256sums.txt`; full-suite runs ONLY via `scripts/governance/run_full_pytest.py`; official
checks only in the clean `coord` worktree; state-corruption recovery uses the verified top-level
subcommand `readme-agent recovery-sweep`; commands above are resolved now -- a card whose
commands turn out wrong at execution fails closed to `quarantined`, never improvises (a MISSING
TOOL spawns a governed install/fallback sub-task or a true blocker instead). **G4 coherence**:
G4 = T6 + T7A + T7B + T8 + TP-11A (preservation core gates the pilot); T7C-F + TP-11B + TF-01
close before TG-07 (enforced as its prereqs).

## 15. Pilot and rollout sequence (mission milestones)

**MS1** cells/python complete local vertical slice — factpack→gateway composition→checks→
preservation gate→Docker verification→diff→**double-run byte-idempotency** (no scheduler, no
freshness engine: those are MS2's subject — MS1 = T5+T6+T7A+T7B+T8+TP-11A). **MS2** same product
through the real scheduler + freshness engine (T9): no-change zero-call fast path, resume,
endpoint-failure drill, bounded repair, state persistence. **MS3** candidate-mode delivery pilot =
takeover-idempotency proof on ≥2 aspose.org-published repos (TG-06B), presented for review.
**MS4** complete cells family README candidates (6 products incl. cells/java workflow-lane
read-only proof) = TG-06A. **MS5** complete-portfolio local rollout (TG-07; family order = generation
sequencing only, per the §0 amendment) — TG-07 opens only when T7C–T7F, T11 (metadata
candidates), T13 (issue drafts), TW-02 (local E2E), and TW-03 (state machines) are complete;
per-product quarantine-not-block with authoritative reasons. **MS6 (terminal)**: TW-04 review
bundle + TW-05 receipt machinery complete → portfolio state `AWAITING_GLOBAL_HUMAN_REVIEW`; the
plan ends there — `GLOBALLY_APPROVED`/`REMOTE_WRITES_ENABLED` require the human's explicit
portfolio-wide approval and are outside this plan. Autonomy is claimed only after MS2 completes a
real scheduled cycle end-to-end. Every milestone criterion above is owned by the named card(s) —
nothing exists only in prose (§14 gate-ownership map).

## 16. Validation/regression plan

Everything in the mission list mapped: vendored-check drift + fail-closed fixtures (T3); factpack +
LLM-output schema tests; reconciliation gates (dispositions + claim spans + the U8 excerpt-hash
bijection check); structural/factual/link (incl. new link-semantics validators covering all aspose
hosts)/dependency/Mermaid-render (real mermaid-cli in-pipeline, mermaid.ink spot-checks for pilots
[U18])/collapse checks; Docker example execution; changed-path isolation; no-secret scans
(existing); idempotency + no-change fast path; scheduler, retry/breaker, crash-resume, duplicate-PR,
cross-product isolation tests; upgrade compatibility = re-pin drift test. Real corpus products as
E2E fixtures; no single file is the universal source of truth (golden authority retired in T2).
**Upstream-defect register enforcement**: every §7b row (U1–U20) must map to a named test or design
control; the mapping is a checked artifact (a small table test asserting each U-id resolves to an
existing test/module), reviewed at every milestone gate — a register row without a live control
fails the milestone, so no upstream defect can be silently reproduced. **Template-agility tests
(T14)**: (a) registry v1 reproduces the current contract byte-compatibly; (b) adding a synthetic
section (registry entry + plugin only) makes it compose, validate, and calibrate with zero edits
elsewhere; (c) removing a section deactivates its checks/fragments cleanly with no orphan findings
and no false calibration regressions on unrelated sections; (d) a registry change flips the
freshness tuple for exactly the affected sections/products. Issue-lane tests: draft-mode never
writes; dedupe correct against a fixture issue set.

## 17–19. Effort, tradeoffs, risks

Reuse ≈75–80%. Per-task sizing (S ≤1 day, M = days, L = week+, iterative): TB-cards S–M each ·
TD-01+T1A+T1B M · T2 S · T3 L · T4 M · T14 M · T5 M · T6 M · T7A–T7F **L-iterative (the long
pole)** · T8 M · TP-11A/B M · TF-01 M · TL-01 S · TW-01/02/03/04/05 M each · T9 M · T10 M · T11 M · T13 S · T12 S. New work: composition worker + calibration (the long pole —
iterative by design), section-registry framework (medium), freshness wiring (small), metadata
engine (medium; design exists), issue-filing lane (small), import (small-medium). Tradeoffs addressed honestly: **import-and-own vs pin-read-through
vs live-sharing** — import chosen (owner ruling): full independence, tracked durability (fixes U4),
immunity to upstream churn and upstream-agent mistakes; costs accepted: upgrades become manual
cherry-picks (mitigated by the import manifest + advisory upstream-diff report), repo size grows
(knowledge trees + 19MB targets map + corpus — tracked deliberately), and upstream improvements
after import date don't arrive free; central contract now lives in the imported checks, evolving
here. Gateway quality vs cost (per-unit calls + embedding-assisted packing + fallbacks; ~16–50
calls/README first run, 0 after); polling vs events (daily+weekly chosen; dispatch remains
available); PR-only vs merge (candidate-until-proof ruled); strict validation vs quarantine
(quarantine, never weaken a validator); full example execution vs speed (Docker verification kept —
it is the moat); evidence completeness vs overhead (no bundles for unchanged runs); **no
deterministic-prose claim** — deterministic structure/facts/validation/acceptance + pin-on-accept
byte stability instead. Risks: prose-quality ceiling of mid-size models (decomposition ladder +
exemplars + calibration + fallbacks; honestly unresolvable to frontier level — fallback output is
correct-but-plainer); embedding model adds a dependency (all uses non-authoritative + cached +
degradable to lexical heuristics); metadata + issues App permissions boundary; aspose.org
uncommitted machinery exists only in a working tree (mitigated: T1A/T1B import it; owner urged to
commit — report annex); two-trees ambiguity (import choice recorded); gateway variance irreducible
(accepted, absorbed by design). Repo rename: out of this plan (resolution 2) — if the owner wants
it, it should happen before T1B lands (near-zero cost pre-import) as its own planned change.

## 20. Definition of done

**Amendment terminal conditions (override where stricter)**: the complete portfolio is the
enforced scope; all candidates reviewable locally as ONE bundle (TW-04); full local E2E succeeds
without any target-repository change (TW-02); remote mutations are technically impossible before
global approval (TW-01 guard, test-proven); approval is bound to exact candidate + source hashes
with automatic drift invalidation (TW-05); no target repository has been changed during any
development or testing (guard logs prove zero attempts); the plan ends at portfolio state
`AWAITING_GLOBAL_HUMAN_REVIEW` with the human able to approve the complete portfolio locally
before any remote action begins.

MS1–MS6 complete: every portfolio product has a validated, candidate-mode, human-reviewable README
(and metadata proposal) or a quarantine report; takeover-idempotency proven; scheduled cycles run
with no-change zero-LLM fast path; all validators green incl. drift test; golden authority retired;
link-semantics contract enforced; observability live (freshness lag visible); **the §7b
upstream-defect register is fully enforced — every U1–U20 row has a passing named control, and none
of the known aspose.org defects is reproduced in this system**; every discovered upstream product
defect has a structured issue draft (or filed issue, once authorized) in its target repo's lane;
the portfolio is enumerated live from the registry (a product added to the inventory enters the
service with zero code change); **template agility proven** — the §16 agility tests pass, and a
section add/remove demonstrably requires only a registry entry + plugin module; no unauthorized
GitHub action ever taken; autonomy claim backed by a real scheduled cycle that detected change,
produced a validated candidate, and took the authorized (candidate-publication) action. PR/merge
modes remain explicitly gated on future per-repo owner authorization.

## 21. Certification (single active verdict)

**Verdict: READY_FOR_SINGLE_GO_EXECUTION — repaired per the 2026-08-15 round-4 review (15
sections), on top of the round-2 repairs and the round-3 binding amendment. Execution starts at
TP-00 and proceeds only through the §14 graph; terminal states: AWAITING_GLOBAL_HUMAN_REVIEW /
BLOCKED_PORTFOLIO / BLOCKED_PRODUCTION.**

All previously-issued verdicts and repair narratives are superseded; this section is the only
one. The graph is **47 cards**, validated on regeneration: status enum, prerequisite referential
integrity, cycle-free, single ready root TP-00, every gate G0–G8 owned, gate-order enforced
structurally (no card depends on a later-gate card; TG-00 gates TS-01, so G0 completion is a
prerequisite chain, not prose), registration enforced structurally (every implementation card has
TS-03 in its ancestry), and full TG-08 reachability.

**Round-4 repairs**: (1) gate ordering structural (TG-00→TS-01; validator + TS-03 consistency
test incl. the no-G1-before-G0 negative test); (2) preservation split — TP-11A deterministic core
gates the pilot at G4 (every original unit accounted; residuals explicitly `blocked_unverified`),
TP-11B LLM residuals gate the rollout at G7 — the T7D/G7 contradiction is gone; (3) TF-01
Font/Python acceptance card: reads the complete audit set at
`plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/font--800ea256fec1--636bf4e263cc/`,
converts every global finding into portfolio-wide machinery + regression tests (no Font-specific
hardcoding), regenerates and proves preservation, byte-idempotency (zero calls), and
section-scoped idempotency — prerequisite of TG-07; (4) worktree model corrected: local `main` is
NEVER updated by this plan (agent commits terminate on `freshness-service/integration`;
main-merge is a later user action), lane branches sync from integration before dependent cards,
cleanup verified against integration, user-worktree invariance re-checked byte-exactly after
every card; (5) all commands are Git Bash (forward-slash paths, `RA_BASETEMP` task variable, no
`%TEMP%`), the recovery command verified as top-level `readme-agent recovery-sweep` (cli.py:341),
tool probes extended (actionlint, mmdc, pytest-xdist…) with governed install/fallback instead of
quarantine-on-guess; (6) TB-01 human eyeball replaced by agent-executable rendered-image
comparison (mmdc light+dark renders, semantics/nodes/clipping/readability checks, machine-readable
receipt), and the "known unrelated baseline" classification removed — G0 closes only at zero
relevant failures, zero new skip markers; (7) ownership exact: GOV-014 row prepared as a patch
(its target `plans/backlog-post-poc.md` is a protected user-dirty file — application is a named
user action), TB-06's AGENTS.md note is a proposed patch applied by the coordinator, vague path
patterns replaced with exact ones (incl. `src/readme_agent/facts/render_views.py`), one canonical
ownership manifest (`plans/investigations/control/freshness-service-ownership.json`), overlap
validator runs on actual changed-file sets; (8) guard claim made honest — TW-01 is defense in
depth over SYSTEM-OWNED execution (read-only credentials + credential scrubbing/helper isolation,
transport choke-point across HTTPS/SSH/URL forms, independent authorization gates, full test
matrix incl. resume/recovery paths) and explicitly does not claim to stop out-of-band humans;
(9) TL-01 licensing gate blocks T1B until copy/modify/relicense authority is explicitly recorded
(never inferred from same-company relatedness; header-vs-manifest provenance by format; corpus
bytes preserved; missing authority = genuine external blocker); (10) portfolio semantics:
quarantine lets safe lanes continue but any quarantined active product makes the portfolio
NON-APPROVABLE (BLOCKED_PORTFOLIO; TW-04 bundle stamped non-approvable; TW-03 states + negative
tests updated); (11) portfolio-wide idempotency required at TG-07 (every product twice, zero
calls, per-product idempotency matrix in the final bundle, section-scoped + document-global +
cross-product isolation proofs); (12) App confirmation simplified — the user's post-TA-01
push+dispatch outcome IS the installation proof; manual UI check only on ambiguity; (13) stale
text removed (annex-below claim, duplicate authority paragraph, stale classifications, T1/T7/
TP-11 references, task counts); (14) dual evidence delivery — loose diffable bundle +
`sha256sums.txt` in-repo PLUS an untracked handoff ZIP with its own SHA-256, both paths reported,
for the final bundle and the plan-repair bundle alike; (15) full re-validation run (results in
the final handoff).

**Authoritative artifact locations**: canonical task state = the §14 JSON, staged as
`C:/Users/prora/.claude/plans/moonlit-taskcards.json`, landing in-repo at TS-03 as
`plans/investigations/control/freshness-service-taskcards.json` (+
`freshness-service-ownership.json` beside it; transition ledger in the TS-03 evidence dir).
Annex A: the ONE governed location is the in-repo archive created at TS-03
(`plans/investigations/control/freshness-service-plan-annex-production-assessment-2026-08-15.md`);
until TS-03 lands, the interim file
`C:/Users/prora/.claude/plans/moonlit-annex-a-production-assessment-frozen.md` is explicitly
NON-AUTHORITATIVE frozen evidence, sha256 `daa2a1862336ef992f756c1e4686777d66bf53523369ebb9e9a2c66f01cf7a8f`.
Plan-repair evidence bundle (loose): `C:/Users/prora/AppData/Local/Temp/claude/d--Users-prora-OneDrive-Documents-GitHub-foss-readme-optimizer/7f3f696e-ccf8-4a8a-bbda-c73de1656081/scratchpad/plan-repair-evidence-2026-08-15`
(+ sibling ZIP with SHA-256, reported in the handoff).

**Honest limits**: (a) this repair ran in plan mode (read-only outside the plan file) — staged
artifacts land at TS-01–TS-03, the first post-preflight cards; no decision is deferred, only the
writes; (b) the production DoD remains gated on the named user actions (push, dispatch, LLM
secrets) and the portfolio DoD on the user's global approval — absent them the run ends
BLOCKED_PRODUCTION / AWAITING_GLOBAL_HUMAN_REVIEW and says so; (c) the full suite ran fresh this
session (identical 10 failures across two runs, all root-caused, fix cards gate G0); plan repairs
changed no repository code, so that baseline stands until TP-00 re-runs it as its first act.

---

# Annex A — extracted

Annex A (the production assessment, frozen evidence) now lives in
`C:/Users/prora/.claude/plans/moonlit-annex-a-production-assessment-frozen.md`.
It is non-executable; its TC-series and verdicts are superseded by this plan.
