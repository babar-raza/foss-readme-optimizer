# Full-Portfolio Idea-Fidelity Autonomous Execution State Machine

## Status and authority

This is a supporting execution design, not a second specification, controller, queue, or durable
state store. Its purpose is to make the existing `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` mission
graph able to execute the product outcome in `plans/idea.md` without sequence ambiguity.

Authority is, in order:

1. `plans/idea.md` -- intended product and operating model.
2. `plans/master.md` -- architecture, decision ledger, sequence, and maturity gates.
3. `plans/requirements.md` -- normative obligations and acceptance.
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` -- sole executable
   task graph.
5. The supervisor's versioned Git-ref mission state -- actual claim and transition state.
6. This document, `plans/codex/production-system-redesign.md`, the former RPOC ledger, roadmap,
   status, reports, and evidence -- supporting reference only.

The immediate outcome is one independently transformation-approved
`trusted_readme_transform` draft PR for every current `data/products.json` entry. Its facts are
extracted from the immutable source README with `README_INHERITED` provenance and are not
repository-verified. The denominator is loaded at runtime; no fixed repository count is
authoritative. After every trusted PR exists, execution resumes
`verified_repository_presentation`: the complete repository-evidence-backed central
presentation system and independently reproducible Level-8 award in `plans/idea.md`.

### Binding trusted-POC amendment (2026-07-29)

This amendment supersedes this document's earlier short-term sequencing wherever it conflicts; it
does not delete or weaken the later verified work.

```text
TRP-00 explicit content assurance and lifecycle separation
→ TRP-01 README_INHERITED fact/claim extraction
→ TRP-02 LLM-first inventory, plan, section composition, and repair
→ TRP-03 deterministic validation plus blind-quality and inheritance-fidelity review
→ TRP-04 real adversarial canaries
→ TRP-05 two-to-four-lane full-registry trusted transformation
→ TRP-06 per-repository authorization and live write-access proof
→ TRP-07 exactly one trusted draft PR per current registry repository
→ resume the preserved L8-INTAKE-02 verified boundary
→ verified full-registry Gate A and every later maturity gate
```

The trusted pipeline deliberately retains the existing fact-oriented shape. `ProductFactsV2`
records may be populated from README claims in this mode, but every record carries the immutable
README revision/span, `README_INHERITED` provenance, and `trusted_inherited` assurance. Approved
contract additions use `CONFIGURED_STANDARD`. The system does not inspect code, tests, manifests,
package registries, documentation, or other external sources to reconcile those claims.
`repository_verified` mode later re-derives and reconciles them and invalidates dependent trusted
acceptance rather than promoting it.

The LLM is the primary interpreter and author for this temporary path. It produces a typed source
inventory, transformation plan, bounded section drafts, and targeted repairs. Deterministic code
only segments/assembles Markdown and enforces schemas, provenance, source accountability,
comment/code-fence/header/Mermaid/link/terminology controls, caching, authorization, and effects.
Short and ordinary READMEs may compose in one call; large READMEs use section groups. Independent
blind-quality and inheritance-fidelity roles must approve the result, and an unchanged or
truncated repair is a system failure.

The owner intends to obtain direct write access for the remaining repositories. The plan records
that intention but treats access as available only after live repository permission checks and
reviewed, unexpired authorization records. Missing access blocks only the affected PR while all
other transformation and effect work continues. The one-day target applies to the already
qualified full-registry campaign, not to implementation, canary repair, or unavailable external
authority.

### Immutable core goal and subordinate goal system

`GOAL-CORE-PRESENTABLE-PORTFOLIO` is always active and cannot be replaced by the currently claimed
task: produce a professional, repository-specific, factually accountable README and GitHub-profile
bundle for every runtime-loaded `data/products.json` entry, independently approve it, prove an
unchanged no-op, and then carry the same deliverable through the ordered human, publication,
production, and maturity gates. The project is not successful because it has schemas, tests,
controllers, reports, evidence directories, or maturity prose; those are supporting means.

Seven subordinate goals may own dependency-ready work, but none is an alternate stopping point:

1. `GOAL-TRUSTED-POC` -- README-derived LLM-first transformations, independent fidelity approval,
   no-op proof, authorization, and one trusted draft PR per current registry repository.
2. `GOAL-TRUTH` -- verified product, acquisition, example, limitation, compatibility, and link
   evidence needed by the core bundle.
3. `GOAL-README` -- the actual marker-free product-specific README, badge header, visual overview,
   examples, contextual links, native patch, validation, repair, approval, and no-op proof.
4. `GOAL-PROFILE` -- GitHub description, homepage, topics, community-file findings,
   generated-surface observations, and product illustration.
5. `GOAL-AUTONOMY` -- the same output through one safe, resumable, isolated, idempotent,
   evidence-complete `supervise` runtime.
6. `GOAL-DELIVERY` -- Gate B, `act`, staging, Gate C, and hosted GitHub App operation in order.
7. `GOAL-MATURITY` -- complete surfaces, Level 5, heterogeneous Level 7, and the independently
   audited 30-day and 90-day operating windows.

Every task must name its subordinate goal and one measurable core contribution: a visible output,
the removal of its first failing boundary, an indispensable safety condition, or required
acceptance proof. A task that provides none is moved to backlog. After every transition, execution
recomputes a goal scoreboard from durable repository lifecycle state:

```text
registry denominator
→ TRUSTED_FACTS_EXTRACTED
→ TRUSTED_CANDIDATE_GENERATED
→ TRUSTED_TRANSFORM_APPROVED
→ TRUSTED_NO_OP_PROVEN
→ TRUSTED_PR_OPEN
→ FACTS_READY
→ CANDIDATE_GENERATED
→ DETERMINISTIC_VALIDATED
→ AGENT_APPROVED
→ NO_OP_PROVEN
→ HUMAN_ACCEPTED
```

The scoreboard also names the first failing boundary, the exact next task, and whether that task
produces output or removes a blocker. Closing machinery without advancing a lifecycle count or
removing its evidenced blocker is a drift failure. Dependency ordering still prevents downstream
work from masquerading as upstream proof, but the core deliverable remains active throughout.

The audit baseline at adoption was `main` at
`f89da6056b13cae19e02a72aa6d5ebf3fc371ee1`, with a large valuable in-flight candidate tree. At
that point the portfolio evidence recorded candidates but zero independently approved local
repositories; the durable active task still described three Java pilots; RPOC was a separate
unregistered ledger; product-truth drafting was not consumed by rendering; the non-pilot path
could skip bundle verification; reviewer repair missed `caller_domain`; review used no durable
backend; dynamic planning was opt-in; coverage/status tooling was stale; and the tree was not
green. These are entry findings, not closure claims.

## Current execution checkpoint and route correction (2026-07-29)

The verified pre-amendment checkpoint for this production-concurrency reassessment is
control-repository `main` at `fb56102082918d81ec1c186b0421b9c37fc6870e`. The tree contains the
preserved in-flight implementation for `L8-REVIEW-02A-REPAIR-CONTROLS`: nine modified tracked files
and five untracked source/test files that bind repair to changed source operations and finding
resolution. No repository-owned test, proof, supervisor, Ruff, or mypy process was active when this
checkpoint was captured. This plan amendment is documentation-only and must not overwrite,
reinterpret, or absorb that task's implementation.

Mission `status` loaded graph
`471a0d29f5e772db2845e51cd5ebe421d1a7813bad72671656f4c189a0a8ab39`
without drift and reported durable state version 502, active task
`L8-REVIEW-02A-REPAIR-CONTROLS`, 40 unresolved tasks, one external block, and no eligible
competing task. The runtime denominator is 31. Durable lifecycle state reports 8 repositories at
`FACTS_READY`, 8 at `CANDIDATE_GENERATED`, 8 at `DETERMINISTIC_VALIDATED`, and zero at
`AGENT_APPROVED`, `NO_OP_PROVEN`, or `HUMAN_ACCEPTED`. The first failing portfolio boundary remains
`FACTS_READY`. These are the current durable counts; the 28 revision-root manifests on disk and the
one-repository `portfolio-summary.json` are historical/compatibility artifacts, not a portfolio
acceptance result.

The current implementation boundary is more advanced than the earlier concurrency draft but still
not parallel-ready:

- commit `db506257` and closed task `L8-COMPOSE-04B-STAGE-TRANSACTIONS` added typed private attempts,
  seals, receipts, and reducer-owned promotion for `CANDIDATE_GENERATED` and
  `DETERMINISTIC_VALIDATED`;
- the registry command still executes one ordered `for` loop and calls the complete
  single-repository `cmd_supervise()` path;
- the stage transaction currently packages candidate and validation results after those results
  were computed in the parent process; it is not yet a process-isolated stage executor;
- there is no campaign scheduler, renewable campaign lease, resource admission controller,
  subprocess lane runner, recovery planner, or deterministic portfolio reducer;
- the currently claimed repair-control task must close before review work can be safely fanned out.

This is a historical reconciliation snapshot, not a substitute for live state. Every continuation
must rerun mission `status`; graph migration and claim recovery remain governed by `evaluate`.

The recovery is convergence, not rollback: preserve the proven supervisor, safety, isolation,
lifecycle, facts, evidence, reviewer, and LLM-accounting foundations; stop extending unrelated
production machinery; use official/native toolchain outputs behind thin isolated adapters; finish
the representative fact boundary; then make seven latest-contract READMEs visible before any
full-registry preflight or fan-out. The three governing outcomes are:

1. seven current-contract `NO_OP_PROVEN` representatives, one per supported ecosystem;
2. current-contract Gate A for every runtime-loaded registry entry;
3. ordered Gate B, `act`, staging, Gate C/D, Level 5, Level 7, and Level 8 proof.

A representative seven-repository result is a qualification milestone, never the full POC.

### 2026-07-26 execution audit: why the previous route was too long

The prior loop repeatedly invoked the complete full-registry command while the durable mission was
still on product truth. That was the wrong execution granularity:

1. `local_poc` has no stage boundary, so a fact task automatically proceeds into assessment,
   composition, deterministic validation, live independent review, repair, and no-op.
2. Prompt, renderer, fact, or reviewer changes correctly invalidate dependent artifacts, but the
   portfolio was already fanning out before those contracts were frozen. Each fix therefore
   reopened earlier repositories and multiplied live-call cost.
3. The portfolio command has per-repository trigger/run leases but no portfolio-wide
   single-writer lease, renewal protocol, or fencing generation. The current sprint has one human
   operator and one Codex operator; this is not a multiple-worker incident. The defect is that the
   runtime would still permit two overlapping invocations from that operator, or later from
   scheduled/event deliveries, to inspect the same campaign and publish competing aggregate
   results.
4. The mission claim has a finite expiry but portfolio, build, and LLM operations do not renew it.
   Long work can therefore remain correct at repository level while losing the mission-level
   authority that is supposed to explain and serialize it.
5. `portfolio-summary.json` describes only the latest bounded prefix and is overwritten by the next
   slice. It is neither a frozen campaign ledger nor a serialized reduction of all accepted lane
   results, so it cannot answer which repositories remain valid under the current
   prompt/renderer/reviewer contract.
6. Runtime evidence is spread across many timestamped retry directories even though canonical
   revision-addressed bundles already exist. This increases audit cost without increasing proof.
7. The active path still contains oversized modules (`supervisor/loop.py`, facts verification,
   reviewer, README specialist, lifecycle, product-truth drafting, command adapter, composition,
   and renderer). Extending them directly has increased coupling and regression risk.
8. `master.md` still reports durable state version 81 and contains a stale edit-approval sentence
   that conflicts with current repository instructions. `idea.md` and `master.md` also retain
   visible mojibake. Those are plan/presentation defects, not runtime proof.
9. Terminal fact acceptance is not coupled to the complete fact-eligibility contract. Replaying
   the current fact gate against four `NO_OP_PROVEN` bundles invalidates three, yet their durable
   states remain terminal.
10. The candidate claim map covers fact-cited document operations, not every material inherited
    claim. `preserve` currently means byte retention but is later treated by reviewers as factual
    endorsement.
11. Source-build and example verification remove credentials but execute repository build logic
    directly on the host. `example_execution.py` explicitly says it is not an OS sandbox, while
    `PKG-006` already records that arbitrary package execution has no sandboxing story.
12. Git history is intact and linear, including commits `f8b83a4` and `a7ac331`, but the canonical
    handover still describes HEAD `e454f7f` and mission state 132. Durable data survived; the
    explanatory history and derived completion claims did not stay synchronized.

The corrected rule is: **never run beyond the active mission task's acceptance boundary**. Add a
typed stage limit to the same `supervise` runtime, qualify each boundary independently, freeze one
campaign contract, and only then fan out Gate A. A full `local_poc` portfolio run before the
qualification-freeze task closes is a process violation and its output is diagnostic only.

### 2026-07-28 outcome-first convergence protocol

The current visitor contract (`L8-020`, `L8-021`, `L8-023`, `L8-024`, and `L8-026`) is frozen
until one Python, .NET, Java, C++, TypeScript, Rust, and Go README is independently approved and
unchanged-no-op-proven. A factual or safety defect reopens its first owner; a non-safety
presentation preference is logged to backlog instead of changing the campaign.

The existing 3D Java candidate is the first negative control. The deterministic contract must
reject its visible marker/comment, absent factual badge header, absent fact-backed Mermaid
overview, incomplete inherited-claim accountability, outdated link treatment, and obsolete
edition terminology before regeneration. Passing that negative control is followed by corrected
representative outputs in the binding platform order—Python, .NET, Java, C++, TypeScript, Rust,
Go—then full-registry truth and candidate fan-out.

Ecosystem evidence comes first from official consumer/build tools inside the isolated executor:

| Ecosystem | Primary authority | Project-owned residual |
| --- | --- | --- |
| Java | Maven effective POM, dependency output, compile/test | normalize facts and apply policy |
| .NET | evaluated MSBuild properties/items, `dotnet` consumer build/pack | select the distributed product root and normalize facts |
| Python | built/installed distribution, `importlib.metadata`, runtime inspection | map distribution-to-import names and bounded public API facts |
| TypeScript | `npm pack`, package exports, pinned `tsc` consumer compile | select canonical import and normalize exports |
| Rust | Cargo metadata/check/doc and locked consumer build | source-pinned acquisition and bounded residual API facts |
| Go | `go list`, `go doc`, `go test` | normalize module/package/API facts |
| C++ | CMake File API, compilation database, Clang or real consumer compile | handle non-CMake residuals and public-header policy |

A custom parser cannot overrule contradictory evaluated consumer behavior. It is added only for a
required residual fact the native tool cannot expose and carries the build-vs-adopt justification
required by decision #30.

The normal paid path is bounded to one composition call, one independent-review call, and one
targeted repair call per repository/revision/campaign. Deterministic failures make zero new prose
calls. Content-addressed cache keys bind the repository revision, selected product root,
manifest/lock inputs, toolchain digest, adapter, fact contract, prompts, renderer, and acceptance
contract. Verification runs at the smallest sufficient scope: focused tests per edit, one real
representative per adapter, all seven representatives per presentation-contract change, the full
official suite at coherent commit/gate boundaries, and the full registry only after campaign
freeze. Runtime bundles are updated in place under `runs/`; one checksum evidence package is
promoted at task closure rather than after every diagnosis.

### 2026-07-28 accepted accelerated goal and execution contract

The functional goal guard remains the sole machine-enforced goal system. Execution agents map it
to three horizons and may not substitute one horizon's machinery for another horizon's output:

| Horizon | Governed goals | Required outcome | Target control |
| --- | --- | --- | --- |
| Short | `GOAL-TRUTH`, `GOAL-README` | Repair the common reviewer; seven ecosystem representatives at `NO_OP_PROVEN`; eight total finalized READMEs; eight Python READMEs; then every current Python README | 3 working days for eight total; 5 for eight Python; 7 for all Python |
| Medium | `GOAL-PROFILE`, `GOAL-DELIVERY` | Finish the remaining .NET, Java, C++, TypeScript, Rust, and Go cohorts; close full-registry Gate A; Gate B; `act`; staging; Gate C; hosted runtime; Level 5 | 7–12 working days for Gate A; 3–5 weeks for Level 5 |
| Long | `GOAL-MATURITY` | Level-8-grade hosted operation, Level 7 at day 30, Level 8 at day 90 | one uninterrupted day-1-to-day-90 series |

`GOAL-AUTONOMY` is cross-cutting. It enters the critical path only for an evidenced blocker or an
indispensable safety/reliability condition. A time target is never a waiver. When a target is
breached, the agent records the first failing boundary, stops unrelated abstraction and evidence
churn, selects the smallest permanent repair, verifies it, and continues through the same graph.
It does not create another plan/controller or close from a report.

The binding platform priority is:

1. Python
2. .NET
3. Java
4. C++
5. TypeScript
6. Rust
7. Go

This is the tie-break and cohort order whenever more than one platform-scoped task or repository
is dependency-ready. `data/platform_priorities.json` is the fail-closed machine-readable source
used by canonical portfolio execution. It does not override a prerequisite, abandon an already valid claim, weaken
a safety gate, or serialize independent work behind a narrow external block. The current
cross-platform facts task therefore closes its remaining Go dependency; the first new
platform-scoped README output after that is Python. If a higher-priority platform is externally
blocked, retain its visible blocked state, advance temporarily, and return to it as soon as the
block clears. Ecosystem enumerations elsewhere are coverage sets unless explicitly labeled an
order.

### 2026-07-29 approved visible-output resequencing

The work is resequenced without deleting, weakening, or deferring any acceptance requirement:

```text
repair and requalify the shared reviewer
-> seven NO_OP_PROVEN ecosystem representatives, Python promoted first
-> zero-paid-call readiness inventory for all runtime-loaded Python repositories
-> eight total finalized READMEs, using the next Python repository for the eighth slot
-> eight finalized Python READMEs
-> every current Python README finalized
-> remaining .NET, Java, C++, TypeScript, Rust, and Go cohorts
-> complete the dynamic-denominator Gate A and every later gate unchanged
```

Here, “finalized” means one current-campaign bundle has verified facts, a repository-specific plan,
candidate and patch, deterministic validation, independent agent approval, effective repair where
needed, unchanged no-op proof, exact call accounting, a redacted manifest, and valid checksums.
It does not mean `HUMAN_ACCEPTED`; Gate B remains a separate human action after full Gate A.

The acceleration uses the existing campaign and scheduler rather than a second queue. After the
seven-representative qualification freezes the shared contract, the sole supervisor may use the
already-governed two-to-four isolated lanes. Python owns every compatible lane while an eligible
Python item exists. A later platform may not take a reserved slot; a narrowly externally blocked
Python repository remains visible while other Python repositories proceed, and all Python entries
must close before the remaining platform cohorts begin.

The executable milestone taskcards are:

- `L8-ACCEL-00-PYTHON-READINESS`;
- `L8-ACCEL-01-EIGHT-TOTAL`;
- `L8-ACCEL-02-EIGHT-PYTHON`;
- `L8-ACCEL-03-ALL-PYTHON`.

These are inspectable scheduling and outcome boundaries inside Gate A, not new product scope. Their
evidence is reused by the existing full-registry truth, cohort, healing, no-op, and independent
reproduction tasks. The 3/5/7-working-day values are planning targets, never waivers: a breach
records and repairs the first failing boundary while all proof standards remain intact.

### 2026-07-29 source-complete discovery and intake amendment

The runtime-loaded registry remains the execution allow-list, but it is not assumed to be a
complete source inventory. A live read-only audit found one active PDF Go MCP repository outside
the existing naming regex and one unavailable configured organization while the latest workflow
still reported success/no additions. The visible-output route therefore starts with four bounded
P0 prerequisites rather than allowing reviewer qualification to proceed against a potentially
stale denominator:

```text
L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY
-> L8-INTAKE-01-STABLE-IDENTITY-AND-RECONCILIATION
-> L8-INTAKE-02-READONLY-PREFLIGHT-ENROLLMENT
-> L8-INTAKE-03-REGISTRY-REVISION-QUEUE-AND-HEALTH
-> L8-REVIEW-00-CONTEXT-CORPUS
-> the approved Python-first sequence unchanged
```

The first task inventories every visible repository from explicit authorized sources, retains
unmatched/ambiguous names, makes source failures block completeness rather than unrelated work,
and repairs the public CLI preflight-before-allow-list ordering. The second reconciles by provider
repository ID and supports rename, transfer, archive, variants, and multiple repositories per
family/platform without changing policy/authorization fields. The third admits new repositories
only as disabled/read-only and runs exactly one durable intake preflight through the existing
lifecycle; a strong existing README may take a byte-identical empty-patch fast path only after
facts, inherited claims, deterministic assessment, independent approval, and no-op proof. The
fourth binds discovery sources, observations, registry contents, changes, failures, and freshness
into `RegistryRevisionV1`, connects reconciliation to the same durable intake queue, and adds
event/daily/weekly/dead-man health controls.

This is prerequisite repair, not added product scope or a second controller. It preserves all 97
existing taskcards, their dependencies, the reviewer repair, Python-first priorities, Gate A/B/C/D
ordering, and every later Level-8 requirement. The revised graph contains 101 taskcards.

The portfolio is executed as 12 family evidence sets, 7 ecosystem evidence sets, and 31 mandatory
repository deltas:

```text
candidate facts
  = applicable content-addressed family evidence
  + applicable content-addressed ecosystem evidence
  + repository-specific source/manifests/API/examples/limitations/license/workflows
  + validated dispositions for the existing README
```

This is reuse inside `ProductFactsV2`, not another truth store. A family/ecosystem fragment renders
only after the repository records applicability and provenance. Product-family identity,
audience, stable terminology, catalog links, and one illustration may be reused; coordinates,
public APIs, examples, limitations, license, workflows, compatibility, and inherited claims are
always verified per repository. `FACTS_READY` is claim-driven: every selected material README
claim is supported or omitted, while optional unselected research remains visible but does not
block composition.

Headers, applicable badges, Mermaid structure, navigation, link allocation, and terminology are
deterministic. The normal LLM budget remains one composition, one independent review, and one
targeted repair per repository/revision/campaign. Related repositories may share a physical
request only after typed per-repository accounting, outputs, verdicts, cache keys, and failure
isolation pass cross-product and malformed-item controls.

Parallelism is owned only by the canonical supervisor. One operator starts one top-level
supervisor process tree; the supervisor may later create process-isolated repository lanes after
the applicable promotion gate. Each lane owns its lease, revision root, lifecycle, accounting,
evidence, and result envelope. Shared caches are read-only/content-addressed; only the scheduler
reduces lane results into campaign state; resource-specific backpressure lowers or pauses
admission. A source/toolchain build feeds all dependent checks until its exact key changes. URL,
registry, workflow, and license evidence is fetched once per normalized freshness key.

The authoritative rule remains serial through seven-representative qualification. The active
shared presentation contract is repaired serially, lane isolation is proven on fixtures, and the
seven real representatives are promoted in configured order. Only after the representative
contract, recovery, golden, cost, and campaign-freeze gates close may the sole supervisor admit a
measured two-to-four real repository lanes. The first P3 capacity is reserved for the Python
milestones; full-registry work begins only after every current Python README closes.

The complete local official suite runs at four campaign boundaries: before resumed execution,
after the first latest-contract README, after seven-representative qualification, and at Gate-A
closure. Focused and impact-mapped integration/safety tests remain mandatory between them. Failed
attempts remain redacted runtime diagnostics; one checksum package is promoted per coherent
closure.

After Gate A, Gate-B review and no-effect `act` work may overlap. Staging preparation and remaining
local surfaces proceed when their own dependencies are satisfied, but no gated effect moves early.
On the first qualifying hosted day, the complete Level-8 control set starts one immutable evidence
series. Its first 30 clean days establish Level 7; the same uninterrupted series reaches Level 8
at day 90. A weaker earlier period cannot be backfilled, and an acceptance-breaking day restarts
or extends the applicable consecutive window.

### Campaign-level delivery and verification

The unresolved task count is a durable dependency/state count, not a prescription to run that many
separate implementation sprints, full test suites, evidence promotions, or commits. Adjacent
dependency-ready tasks execute inside the following outcome campaigns while retaining their own
task IDs, acceptance criteria, transitions, and evidence mappings:

| Campaign | Included outcome | Shared verification boundary |
| --- | --- | --- |
| C1 -- first current-contract README | Finish contextual linking, existing-content reconciliation, complete claim accountability, operation coverage, presentation lint, composition, review, and effective repair for the highest-priority Python representative. | Focused/impact checks during implementation; one complete official suite, real Python lifecycle, independent review, repair control, and unchanged no-op at the accepted README boundary. |
| C2 -- seven representatives | Extend the identical accepted contract through .NET, Java, C++, TypeScript, Rust, and Go; close reviewer grounding/cache behavior, fixture-lane isolation, recovery, golden-set qualification, campaign identity, and contract freeze. Real representatives remain serial and Python is promoted first. | Adapter/public-seam checks per ecosystem; fixture-lane/serial-reference equivalence; one seven-repository end-to-end recovery/idempotency campaign; one complete official suite and independent aggregate at qualification closure. |
| C3 -- Python milestones and full-registry Gate A | Freeze the Python readiness queue; reach eight total, eight Python, and all-Python finalized milestones; then process .NET, Java, C++, TypeScript, Rust, and Go through adaptive two-to-four process lanes, heal only invalidated boundaries, prove no-op, and reproduce the serialized portfolio aggregate. | Per-repository deterministic gates and manifest checks; milestone denominator reconstruction; lane pressure/recovery/contamination controls; one complete official suite and independent full-registry denominator/checksum reconstruction at Gate-A closure. |
| C4 -- local profile and workflow | Complete the remaining locally testable presentation surfaces and reproduce the same canonical supervisor under `act`. | Surface-specific integration/safety checks followed by one complete local multi-surface proof and one actual-workflow recovery/idempotency proof. |
| C5 -- staging and controlled delivery | Prove proposal state in disposable staging, obtain Gate-C per-push approvals, prove the Java draft-PR lifecycle, then provision the hosted runtime. | Scenario matrix for create/no-op/update/drift/dedup/lost response/crash/authorization, default-branch byte identity, and token isolation. |
| C6 -- Level 5 and heterogeneous rollout | Complete every `idea.md` surface, run the controlled three-Java pilot, then operate and prove the supported portfolio. | Independent Level-5 audit, one authorized lifecycle per ecosystem, portfolio health/recovery proof, and the uninterrupted day-1-to-day-30 evidence series. |
| C7 -- Level 8 | Continue the same Level-8-grade hosted system through day 90. | Weekly reproducible manifests and reports, continuous safety/recovery metrics, and the final independent Level-8 audit. |

Campaign batching changes execution granularity only. It never changes the end goal, dependency
order, platform priority, requirement status, proof standard, Gate A/B/C/D order, or the rule that
only `CLOSED` satisfies a dependency. A shared campaign result may close several tasks only when it
contains separately inspectable acceptance and evidence mappings for every task. Code existence or
a green downstream smoke run cannot bulk-close unfinished taskcards.

Within C1-C3, the operator uses this verification pyramid:

1. **Edit loop:** run Ruff on touched Python and the smallest affected unit/contract tests. A failure
   is repaired immediately at the first failing boundary.
2. **Integrated slice:** after a public seam or coherent group of adjacent tasks is runnable, run
   its integration, safety, regression, invalidation, and no-op checks. This is the earliest point
   a task may close.
3. **Campaign boundary:** run the real representative/portfolio proof, independent verifier,
   evidence-corruption controls, SHA-256 inventory, and the complete official suite at the four
   local boundaries already fixed above.
4. **Delivery/production boundary:** run the staging, recovery, idempotency, authorization, and
   elapsed-operation proof required by that gate.

Implementing all remaining development first and testing only at the end is prohibited. It would
allow an early fact, document-plan, renderer, or reviewer defect to multiply across every consumer.
The accelerated rule is instead **continuous cheap verification plus deferred expensive aggregate
verification**.

### Additional material accelerators

The following controls are part of the existing mission rather than a separate performance plan:

- **One stable campaign tree.** Keep one operator and one top-level command tree. Avoid repeated
  branch/worktree setup and do not create per-task implementation environments.
- **Fewer coherent commits.** Commit runnable, reviewable campaign slices rather than mechanically
  creating one commit per taskcard. A normal C1/C2 implementation campaign should need only the
  fewest coherent commits its rollback boundaries require; every commit remains green for the
  impact-mapped checks and carries the required trailer.
- **One closure package.** Keep failed attempts as redacted runtime diagnostics and promote one
  checksum-complete evidence package per coherent closure campaign, with per-task result mappings.
- **Deterministic before paid.** Run catalog, facts, source-span, package/example, policy, protected
  content, link, and claim-map gates before any composition/review call. A deterministic failure
  makes zero paid calls.
- **Hash-addressed reuse.** Skip unchanged facts, toolchain outputs, LLM jobs, render stages,
  validation, and no-op work only when the complete dependency fingerprint matches. Invalidate from
  the earliest changed boundary and retain unaffected repository/family/ecosystem evidence.
- **Portfolio evidence reuse.** Compute applicable family and ecosystem evidence once, then add and
  verify each repository delta. Shared evidence never substitutes for repository-specific
  coordinates, APIs, examples, limitations, licenses, workflows, or inherited claims.
- **Bounded call budget.** The normal maximum remains one composition, one independent review, and
  one targeted repair call per repository/revision/campaign. Retry/provider exceptions require an
  explicit ledger rationale.
- **Repair upstream once.** When several repositories fail for the same reason, repair the shared
  adapter/contract once, requalify the affected representative, and resume only invalidated
  repositories. Do not patch candidates individually.
- **Resume, do not replay.** Persist stage outputs and transition receipts after each repository so
  cancellation, machine restart, or a narrow failure resumes from the last checksum-valid boundary.
- **Progressive, governed lanes.** Keep shared-contract repair and all seven real representatives
  serial; fixture isolation may exercise two lanes. After complete seven-representative
  qualification, recovery/golden/cost proof, and campaign freeze, the sole supervisor may use the
  measured safe count of two to four lanes, reserving eligible capacity for Python until every
  Python README closes. Concurrent control-repository editing remains prohibited.
- **Measure before test parallelism.** Enable pytest-xdist, persistent clone optimization, CI cache
  changes, or physical multi-item LLM batching only after the cost-baseline task proves the change
  safe, faster, deterministic, and isolated. Otherwise keep them off the critical path.
- **Impact map, not ritual reruns.** Record which modules/contracts each focused test proves.
  Rerun unaffected expensive suites only at their campaign boundary, while safety-critical touched
  seams always run immediately.

## Production concurrency and repeatability design (2026-07-28)

### Diagnosis: symptoms, root causes, and structural weaknesses

The visible symptom is low throughput: the durable scoreboard is 8/31 at `FACTS_READY`,
`CANDIDATE_GENERATED`, and `DETERMINISTIC_VALIDATED`, but 0/31 at `AGENT_APPROVED` and
`NO_OP_PROVEN`. The solution is not to fan the present command out over 31 repositories. That
would multiply contract defects and produce results faster than they can be trusted.

The production diagnosis is:

| Class | Current evidence | Actual cause | Consequence |
| --- | --- | --- | --- |
| Symptom | `commands_supervision.py::_cmd_supervise_registry()` iterates one ordered `for` loop and stops after a wall-clock slice. | The portfolio adapter is a serial prefix runner, not a durable work scheduler. | Independent repositories and stages cannot use otherwise idle CPU, network, Docker, or LLM capacity. |
| Symptom | Candidate files can exist while the durable lifecycle remains earlier, and historical manifests can claim stages invalid under the current contract. | Artifact existence, durable promotion, and current-campaign validity are separate facts without one portfolio reduction. | Reruns and reports can disagree without a corrupt individual file. |
| Root cause | `stage_limit.py` types three boundaries, but assessment, plan, review, repair, approval, and no-op are not separately schedulable. | Most lifecycle work still runs inside the complete repository command. | Work is under-scoped or allowed to run too far, increasing invalidation and paid-call waste. |
| Root cause | `GitStateBackend` has per-repository write and run locks, but no renewable campaign lease, fencing epoch, or aggregate-writer contract. | Repository mutual exclusion is being asked to provide campaign ownership, which it cannot do. | A late or recovered invocation can publish a stale aggregate or continue after authority has moved. |
| Root cause | `llm/call_ledger.py`, facts context, lifecycle recording, and execution flags use `ContextVar` or process-local state. | A naïve thread pool would not automatically carry the correct repository context and would share mutable module state. | Call accounting, facts, evidence, or lifecycle events could be attributed to the wrong repository. |
| Root cause | Two stages now have private attempts and seals, but their computation is not isolated and the complete bundle/campaign is not transactional. | Atomic rename and stage receipts protect selected outputs, not the whole lifecycle or aggregate. | A crash can leave valid-looking compatibility files that must not count as completed campaign work. |
| Root cause | The coarse control-plane fingerprint hashes broad capability/prompt/ruleset inputs, while lifecycle records also keep selected stage hashes. | Invalidation ownership is split and not compiled from one declared dependency graph. | Some edits reopen more work than necessary; other contract changes can leave stale terminal state until a later check notices. |
| Root cause | LLM output is nondeterministic and retry/provider behavior is external, while exact cache eligibility is still being completed. | “Same repository” is not the same request unless source, facts, prompt, schema, model route, generation settings, and reviewer standard are identical. | Unchanged reruns can differ or spend again unless every job is hash-addressed and replayed from an accepted receipt. |
| Root cause | Reviewer prose and structured findings previously shared one authority boundary. | A blind quality reviewer could make a technical assertion without facts and have its prose drive lifecycle or repair even when the fact-aware reviewer disagreed. | Independence alone did not prevent a confidently wrong reviewer premise from blocking or rewriting a valid candidate. |
| Root cause | Human-readable proof run IDs were reusable across reviewer-contract revisions. | The call ledger appended physical attempts from different prompt/schema standards under one identity. | Per-README call count, cost, retry, and latency evidence became cumulative and could not describe one reproducible contract. |
| Structural weakness | Clone/API reads, Docker builds, CPU validators, author calls, reviewer calls, and Git-ref writes have different capacity and failure behavior but no separate admission budgets. | A single global lane count cannot protect the bottleneck resource. | Four lanes can mean four simultaneous native builds or reviewer calls, causing rate pressure, memory contention, and cascading retries. |
| Structural weakness | Current platform priority is phrased as complete serial exhaustion. | Dispatch order, resource utilization, and acceptance-promotion order are conflated. | A slow Python build can idle independent deterministic or network capacity even when later-platform inputs are ready. |
| Structural weakness | Recovery is repository-oriented; the latest prefix summary overwrites the previous one. | There is no durable campaign reducer with monotonic work-item receipts. | Restart safety exists in pieces but not as one reproducible portfolio result. |
| Structural weakness | Broad supervisor/specialist/security regressions provide little progress output and one campaign took 1,056 seconds for 184 tests. | Test selection and timing are not yet treated as scheduled resources with historical duration budgets. | Starting overlapping broad suites would multiply opacity and wall-clock cost instead of shortening the critical path. |

The first version of this diagnosis predates commit `db506257`. The following current-state
corrections are binding and prevent partial transaction machinery from being mistaken for a
production scheduler:

| Current boundary | Verified implementation state | Production consequence |
| --- | --- | --- |
| Stage ceilings | `FACTS_READY`, `CANDIDATE_GENERATED`, and `DETERMINISTIC_VALIDATED` are now typed. Assessment, plan, review, repair, approval, and no-op are not separately schedulable. | Extend the same stage contract through the lifecycle before portfolio pipelining. Do not wrap the complete repository command in workers. |
| Stage transactions | Candidate and deterministic validation have private attempt roots, checksummed seals, receipts, and reducer promotion. Candidate rendering and validation computation still occur before the private attempt is prepared. | This is a serial publication transaction, not yet isolated stage execution. Move computation behind `prepare_stage()` rather than merely copying its result. |
| Campaign identity | Current `campaign_id` is derived from one repository, revision, and its dependency map. It does not bind the registry revision set or full campaign contract. | Version it as a legacy serial-stage namespace; add a true `CampaignContractV1` rather than silently broadening the old hash. |
| Fencing | `StageFenceV1.generation` is hashed, but no durable lease generation is stored or compared by the reducer. | It cannot reject a late worker after lease reclaim. Promotion needs a backend-issued fencing epoch checked immediately before CAS. |
| Reduction | Reducer functions exist, but there is no single campaign reducer process or monotonic portfolio aggregate. Compatibility files are still materialized one by one and consulted by current readers. | Receipts must become the sole acceptance authority; the revision-root tree becomes a rebuildable compatibility view. |
| Scheduling | No planner, priority, admission, lease-renewal, recovery, subprocess-runner, or metrics module exists. The registry adapter still calls `cmd_supervise()` serially. | Concurrency is not a configuration toggle. P1 must build and fault-test the control plane before two live repository lanes are allowed. |
| Review/repair | Grounded reviewer authority exists; material repair-delta controls are in the currently dirty claimed task. The real route has not qualified an approval. | Keep independent review at one admitted call and finish the repair/no-op/real-corpus chain before paid fan-out. |

### Verified implementation inventory: preserve, complete, or redesign

| Component | Evidence-backed state | Disposition |
| --- | --- | --- |
| `supervise`, capability registry, allow-list, push blocking, durable per-repository lifecycle, trigger deduplication, redaction, checksums, independent review roles, and exact LLM accounting | Implemented and exercised through the canonical public seam. | Preserve. Parallel execution must call these seams rather than copy their logic. |
| `portfolio_scheduler/contracts.py`, `lane.py`, `reducer.py`, and `stages.py` | Real serial prepare/seal/promote support exists for two stages, with focused transaction tests. | Extend in place. Treat it as P0 transaction groundwork, not P1 isolation or P2 concurrency proof. |
| `_cmd_supervise_registry()` | One deterministic, platform-ordered prefix loop with failure isolation and a time slice. | Replace only its iteration policy after P1; retain its CLI/profile/allow-list wiring. |
| Revision-root compatibility bundle | Useful to humans and older readers; not campaign-addressed and updated file by file. | Retain as reducer-generated output only. Prohibit it as acceptance/cache authority after migration. |
| `StageFenceV1.generation` | Metadata without a renewable backend lease generation. | Redesign as a durable campaign/repository fencing epoch. |
| Current `campaign_id` | Stable per-repository stage namespace, not a portfolio campaign identity. | Version rather than reinterpret. Migrate current receipts as legacy serial-stage evidence. |
| Multiple top-level commands or thread-pool fan-out | Unsafe with process-local accounting/context and mutable compatibility views. | Reject. Use one top-level scheduler with spawned, process-isolated, one-stage lanes. |
| LLM author/reviewer concurrency | Provider behavior is external and the reviewer route is not qualified. | Keep review at one initially; composition may rise to two only after exact accounting and circuit-breaker proof. |

There was and is one operator. Child Python, Git, Docker, compiler, and test processes are not
additional workers. The production risk is overlapping invocations and future scheduled
deliveries, not a historical team of concurrent repository editors.

### Fresh production findings from the real Cells C++ review

The live proof at
`plans/investigations/evidence/level8-review-finding-grounding-v2/` materially changed the design:

1. The blind quality route asserted that `Aspose.cells.Cpp.FOSS` was not a NuGet package while the
   accepted fact graph contains the verified NuGet acquisition fact and the factual reviewer
   accepted it. The symptom was a bad review; the structural cause was authority leakage between
   visible-document quality and technical factuality.
2. Blind review now has a closed visible-quality criterion vocabulary. Technical availability,
   compatibility, command, API, and evidence decisions belong only to the fact-aware role.
   Free-form reviewer prose is retained as diagnostic evidence but cannot control lifecycle or
   repair; the reducer uses validated finding IDs, exact spans, criteria, fact citations, and
   polarity only.
3. The reviewer-standard identity now includes both prompts and both tool schemas. The accepted
   evidence records one reproducible run contract and an exact seven-call physical-attempt ledger.
   The live route still ended in `SYSTEM_FAILURE` after failing the grounding contract. The
   candidate was retained, no repair ran, and no remote write occurred. This is truthful cost and
   retry evidence, not a claim of exactly-once provider billing.
4. This result is a valid negative-control proof, not reviewer qualification. The current model
   route remains unqualified for portfolio approval until it produces grounded correct verdicts
   across the governed real corpus. Parallel execution must therefore keep independent review at
   one admitted call initially and open its circuit on repeated contract failure.
5. Logical-call identity, physical attempts, contract revision, and repository run must remain
   separate fields. A display label is never a cache or accounting key.

### Reassessment verdict: parallelize a stage machine, not the current loop

The current implementation is not ready for a thread pool or a larger `max_workers` value. Its
portfolio adapter calls the complete single-repository command inside one ordered loop, and that
command owns trigger acceptance, mutable evidence, lifecycle transitions, LLM context, and final
classification. Running several copies concurrently would make the following existing weaknesses
more frequent rather than solve them:

1. `paths.readme_poc_repository_dir()` keys a complete bundle by repository and source revision
   only. A changed prompt, renderer, validator, fact contract, reviewer standard, model route, or
   toolchain can therefore rewrite the same directory even though it represents a different
   acceptance contract.
2. `write_local_poc_*()` updates several files and repeatedly refreshes `sha256sums.txt`; a whole
   stage is not prepared privately and committed atomically. A crash or second writer can leave a
   mixture that is individually parseable but not one accepted stage.
3. `PortfolioPocSummaryV1` is a timestamped summary of the latest processed prefix. It is neither a
   monotonic campaign ledger nor a deterministic reduction of sealed repository receipts.
4. `_cmd_supervise_registry()` reloads Git-ref state several times per member and derives progress
   from a mix of command-local results, process-local LLM context, durable lifecycle state, and
   mutable files. Those views can be correct individually and still describe different moments.
5. run locks have a fixed lease and no renewal/fencing operation in the backend contract. Holder
   identity protects release, but it does not stop an expired, reclaimed worker from finishing
   computation and writing ordinary bundle files.
6. the stage ceiling exposes only `FACTS_READY`, so the scheduler cannot independently queue,
   retry, cache, or pipeline assessment, composition, validation, review, repair, and no-op.
7. identical source revisions do not imply identical work. External fact freshness, dependency
   resolution, environment/toolchain versions, prompts, schemas, generation parameters, and model
   routes can all change without changing the repository SHA.
8. exact-once promotion is locally achievable; exact-once provider billing is not guaranteed when
   an LLM response is lost and the provider offers no idempotency key. The system must record
   logical calls and physical attempts separately instead of claiming a guarantee it cannot make.

The durable solution is a two-phase, stage-scoped scheduler inside `supervise`:

```text
derive one ready stage from durable state
  -> execute it in a private, fenced attempt
  -> seal its typed result and checksum inventory
  -> validate it outside the worker
  -> promote artifacts and lifecycle exactly once through the reducer
  -> derive the next ready stage
```

This permits different repositories to occupy different stages concurrently without allowing
them to share mutable state or bypass an acceptance boundary. It also reduces replay cost because
a failed review no longer reruns snapshot capture, package verification, or composition whose
complete dependency key is unchanged.

### Production consistency contract across reruns

“Consistent” has two precise modes; the system must not blur them:

- **Same-campaign replay.** The complete campaign contract and repository revision are identical.
  The scheduler reuses sealed accepted receipts, makes zero new provider calls for those stages,
  reproduces identical candidate bytes and deterministic verdicts, and derives the same aggregate
  checksum root. Observation timestamps and scheduling telemetry are stored outside the canonical
  digest.
- **New-campaign reevaluation.** At least one declared dependency changed. Only affected stages
  reopen. New LLM prose may differ, but the changed dependency and invalidation edge are explicit,
  the factual/deterministic/reviewer standards are still enforced, and the new result cannot be
  presented as a byte-identical replay.

Define the identities once and use them for caching, invalidation, receipts, and reporting:

```text
campaign_id =
  sha256(canonical CampaignContractV1)

work_id =
  sha256(campaign_id + repository + source_revision + target_stage
         + canonical stage_dependency_hashes)

logical_llm_call_id =
  sha256(work_id + job + prompt_hash + schema_hash + model_route
         + canonical generation_parameters)
```

`CampaignContractV1` must bind at least control HEAD/build hash, dependency lock, registry and
platform-priority hashes, the immutable repository revision set, policies and link catalogs,
fact/schema/eligibility/render-view contracts, prompt inventory and job hashes, renderer and
document-template hashes, deterministic rules, reviewer contracts, model routes and generation
parameters, isolated-executor/toolchain image digests, and external-evidence snapshot or freshness
policy. A field may be deliberately excluded only with a test proving it cannot change an accepted
output or verdict.

External evidence is frozen by normalized key, retrieval result hash, and freshness window for a
campaign. A refresh that changes an acceptance input issues a new campaign or invalidates the
declared dependent stage; it never silently mixes old facts with new review output. Cache entries
are immutable, content-addressed, schema/checksum-validated on read, and disposable on corruption.
Corrupt cache data can cause recomputation, never lifecycle advancement.

### What remains intact

The following are valuable and must not be weakened or replaced:

- `supervise` remains the sole production runtime and capability-registry authority;
- immutable repository snapshots, the allow-list, push-blocking, local no-write policy, and
  isolated example/build execution remain hard gates;
- per-repository CAS state, trigger deduplication, run locks, immutable source revisions,
  redaction, checksums, and independent review remain the repository-level safety spine; existing
  revision-addressed bundles remain historical/compatibility inputs while campaign receipts
  become acceptance authority;
- `ProductFactsV2`, protected-content/claim accountability, deterministic presentation lint,
  bounded LLM use, and no-op proof remain acceptance requirements;
- `data/platform_priorities.json` remains the configured priority source;
- one human operator and one top-level supervisor command remain the local operating model;
- no concurrency setting may lower a validator, skip a reviewer, widen a fact claim, or reinterpret
  a failure as success.

The serial `for` loop, coarse two-state stage ceiling, mutable prefix summary, non-renewable
campaign authority, and undifferentiated lane count must be redesigned. They are implementation
choices, not safety properties.

### Target architecture: one scheduler, isolated lanes, one reducer

Do not create a second controller or queue. Refactor the registry branch of the existing
`supervise` command into `PortfolioSchedulerV1`:

```text
one operator / one top-level supervise process
  -> load and hash registry + platform policy once
  -> load or create immutable CampaignContractV1
  -> acquire renewable campaign lease with fencing epoch
  -> derive ready PortfolioWorkItemV1 rows from durable repository state
  -> admit work through stage-specific resource bulkheads
  -> spawn process-isolated repository lane
       -> acquire renewable per-repository run lease
       -> execute exactly one requested lifecycle boundary
       -> write artifacts into a private attempt directory
       -> validate and seal LaneResultV1
  -> reject late/stale/foreign-fence results
  -> serialized CampaignReducerV1 promotes one sealed result at a time
  -> atomically update durable lifecycle and campaign aggregate
  -> recompute readiness and continue
```

The lanes are child processes of the one supervisor, not agents, operators, or independent
controllers. Use process isolation rather than threads because the current LLM accounting, facts,
lifecycle, and execution contexts are process-local and because native tools can mutate process
environment or leave descendants. A future implementation may prove an async/threaded read-only
adapter safe for specific network collectors, but it is not the initial correctness boundary.

The scheduler owns admission and aggregation only. It does not implement facts, composition,
validation, or review. A lane calls the same public repository supervisor seam used by serial
execution. The local executor is a bounded child process; the hosted executor may later be an
Actions matrix job. Both consume and emit the same typed work/result contracts.

### New or strengthened contracts

These contracts extend existing state; they do not create a parallel ledger:

- `CampaignContractV1`: campaign ID and SHA-256 over control HEAD, dependency lock, execution
  profile, registry bytes, platform-priority bytes, immutable source-revision map, policy/catalog
  inputs, fact-acceptance contract, family/ecosystem evidence, prompt manifests, model routes and
  structured schemas, renderer/composer versions, deterministic rule versions, reviewer standard,
  isolated-executor image/toolchain digests, and requested lifecycle ceiling.
- `PortfolioWorkItemV1`: stable work ID; campaign and fence; repository/revision; platform/family;
  earliest invalid stage; target stage; dependency/input hashes; resource class; attempt; lease;
  estimated cost; and not-before time. It is derived from lifecycle state and receipts, never
  hand-appended to another queue file.
- `LaneResultV1`: work ID; campaign/fence; start and reached stages; terminal classification;
  input/output hashes; artifact inventory; lifecycle transitions; LLM call ledger; resource/timing
  observations; retryability; and worker identity.
- `CampaignAggregateV1`: dynamic denominator, one current result per repository, pending/running/
  retryable/blocked/accepted counts, first failing boundary, platform/cohort progress, resource
  pressure, and checksum root. Only the reducer writes it.
- `LeaseV2`: holder, scope, lease generation/fencing token, issued/renewed/expires times, and
  cancellation state. Renewal is compare-and-swap. Every state/evidence promotion presents the
  current fencing token; a stale worker may finish computation but cannot publish it.
- `StageReceiptV1`: exact stage inputs, output hashes, validation result, campaign dependencies,
  timestamps, and acceptance identity. A directory or candidate file without a sealed receipt
  never advances the scoreboard.

The campaign aggregate is a derived view of repository state plus sealed receipts. It is not
allowed to overwrite history with a bounded prefix. The human-readable summary may be replaced on
each reduction, while the durable aggregate version and receipt history remain monotonic.

### Transactional artifacts and compatibility view

Do not let concurrent lanes write the existing revision root directly. Introduce an immutable
campaign/attempt layout:

```text
runs/readme-poc/campaigns/<campaign-id>/
  campaign.json
  aggregate/{current.json,history/*.json,sha256sums.txt}
  repositories/<org>__<repo>/<source-revision>/
    attempts/<work-id>/<attempt>/
      request.json
      artifacts/...
      result.json
      sha256sums.txt
      SEALED
    receipts/<stage>.json
    current.json
```

A lane writes only its private attempt root. It writes `SEALED` last, after schema validation,
redaction, and checksum generation. The reducer revalidates the seal, campaign ID, work ID,
repository revision, dependency hashes, and fencing generation before it creates or replaces a
stage receipt and advances durable state. Promotion is idempotent: the same work/result hash is a
no-op; a different result for an already promoted work ID is a fail-closed conflict.

Keep the current
`runs/readme-poc/<org>__<repo>/<source-revision>/` path as a human-facing compatibility view so
existing review links do not break. Only the reducer materializes it, atomically, from the current
sealed campaign receipt. Its manifest must name the campaign, stage receipts, and aggregate
version. It is never the evidence authority and a lane never mutates it. Existing schema-1 bundles
remain readable historical inputs but are `UNKNOWN_LEGACY` for campaign identity and cannot count
toward a new acceptance campaign without regeneration or a proof-preserving migration.

The worker/reducer split is deliberate:

- the worker computes one stage and emits proposed lifecycle/checkpoint transitions;
- the worker never publishes campaign state or the compatibility view;
- the reducer is the only campaign writer and applies state plus receipt promotion in a recoverable
  order;
- after a crash before sealing, the attempt is ignored/quarantined;
- after sealing but before promotion, restart discovers and promotes the same result once;
- after state promotion but before summary refresh, restart rebuilds the derived summary from
  receipts rather than rerunning the stage.

This is the minimum transaction boundary needed for reliable parallelism. Atomic writes of
individual JSON files alone are insufficient.

### Stage model and invalidation

Extend the typed lifecycle ceiling through at least:

```text
FACTS_READY
CANDIDATE_GENERATED
DETERMINISTIC_VALIDATED
AGENT_APPROVED
NO_OP_PROVEN
```

Each stage declares its input dependencies once. Compile both cache keys and invalidation from that
same declaration:

- source revision or repository inventory change reopens snapshot-dependent stages;
- fact-contract, policy, toolchain, or evidence change reopens facts and all dependent stages;
- presentation policy/catalog/renderer change reopens assessment/composition and later stages;
- deterministic-rule change reopens validation and later stages;
- reviewer prompt/schema/route change reopens review and no-op, not facts or deterministic
  composition;
- aggregate/report code change rebuilds only the derived aggregate when stage receipts remain
  valid.

Admission closes immediately when a shared contract changes. The scheduler records a freeze
barrier, stops launching new work, lets safe deterministic work drain or cancels paid/native work,
computes the affected stage set, issues a new campaign identity when required, and requeues only
invalidated work. Results from the old campaign cannot be promoted into the new one.

For every LLM job, the cache key includes repository, immutable revision, stage, accepted fact/plan
hashes, prompt and schema hashes, model route/provider parameters, and reviewer standard where
applicable. An accepted identical receipt is replayed with zero provider calls. Retries have one
logical call ID and separate attempt records. Different valid model output is permitted only under
a new key/campaign and must pass the same deterministic and independent gates.

### Stage-pipelined scheduling and priority

Different products may progress concurrently at different lifecycle stages only after their own
dependencies and the applicable promotion level are satisfied. One work item advances one
repository through one target boundary. The scheduler cycle is:

1. renew the campaign and mission leases; stop admission immediately on renewal uncertainty;
2. bulk-load repository state, validate current stage receipts, and derive—not append—the ready
   work set;
3. order ready items by recovery/safety, core-goal critical path, configured platform priority,
   stage criticality, age, then stable repository/work ID;
4. reserve resource capacity and launch only items whose complete dependency keys are frozen;
5. collect sealed results, reject stale/foreign fences, and reduce results one at a time;
6. recompute readiness after every promotion rather than waiting for a whole cohort;
7. persist queue, service, retry, cache, cost, and pressure observations separately from the
   acceptance digest.

Platform priority governs admission and acceptance promotion, not artificial hardware idleness.
The highest-priority ready item receives the first compatible slot and one of the two P2 lanes is
reserved for the highest-priority critical path. A later platform may consume a different idle
resource class only when doing so cannot delay the earlier item. It may not bypass an
agent-fixable earlier-platform defect. Aging prevents starvation among items of otherwise equal
priority.

The stage/resource pipeline starts conservatively:

| Stage family | P2 initial admission | P3 maximum before measurement raises it | Parallelism rule |
| --- | ---: | ---: | --- |
| Campaign admission, invalidation, durable reduction, compatibility-view publication | 1 | 1 | Always serialized. |
| Snapshot/API/package-registry read | 2 | 4 | Read-only credentials; provider-specific limiter and circuit breaker. |
| Fact normalization and deterministic planning/validation | 2 | 4 | Separate attempt roots; measured CPU/RAM cap. |
| Disposable native/package/example build | 1 | 2 | OS-isolated, pinned, resource-bounded, deny-by-default network. |
| LLM composition | 1 | 2 | Exact logical-call identity and token/request budget. |
| Independent LLM review | 1 | 1 | Separate route/context/cache; quality bottleneck remains intentionally serialized. |
| Targeted repair | 1 | 1 | Only after a grounded finding and changed-operation precondition. |
| No-op receipt replay and checksum verification | 2 | 4 | Zero provider calls; immutable receipt validation only. |
| Remote effect per repository | 0 locally | 1 | Inert until its later authorized gate; never shares analysis credentials. |

At P2 the total number of live repository lanes is one even if fixture/resource caps are higher;
those caps become useful for real repositories at P3. The scheduler applies the minimum of total-lane,
resource-class, provider, memory, disk, and campaign limits. Additive increase/multiplicative
decrease adjusts one resource class at a time and can only reduce throughput—not acceptance.

### Progressive concurrency ladder

Concurrency is a promoted capability, not a command-line preference:

| Level | Eligibility | Allowed execution | Promotion proof |
| --- | --- | --- | --- |
| P0 -- contract repair | Current state through the complete `L8-REVIEW-*` repair, cache, real-corpus, and live-campaign chain. | One repository lane. No portfolio fan-out while reviewer/repair acceptance is changing. | A grounded rejection causes a material relevant repair or an agent-fixable reroute before rereview; real-corpus qualification and no-op cache pass. |
| P1 -- isolation proof | Scheduler contracts, campaign lease/fencing, process cleanup, stage receipts, and serialized reducer exist. | Two fixture lanes using different repositories and stages; no live paid fan-out. | Duplicate, stale-fence, crash, cancellation, lease expiry, cache-contamination, and aggregate-order tests produce the same result as serial reference execution. |
| P2 -- representative pipeline | One current-contract Python canary reaches `DETERMINISTIC_VALIDATED`; P1 is green; shared contract is frozen. | One real repository lane through all seven representatives; fixture-only isolation may use two lanes. | Seven representatives reach the required stage in configured order with no cross-repository leakage, bounded resources, and exact accounting. |
| P3 -- Gate A | Seven representatives are `NO_OP_PROVEN`; golden thresholds, recovery, cost baseline, and campaign freeze pass. | Adaptive two-to-four repository lanes inside one supervisor. | Full fault/rate/starvation matrix, measured speedup, no duplicate work/calls, and independent aggregate reproduction. |
| P4 -- hosted operation | `act` and disposable staging prove the same contracts. | Actions matrix or hosted workers execute scheduler-issued items; per-repository effect lanes remain serialized and authorization-bound. | Trigger deduplication, lost-response/crash recovery, token isolation, default-branch byte identity, and health/backlog proof. |

Representative execution remains serial through P2. The approved acceleration begins at P3, after
all seven representatives are `NO_OP_PROVEN`, the golden/recovery/cost controls pass, and the
campaign is frozen. P3 then applies the existing two-to-four-lane contract first to the Python
milestones and only afterwards to the remaining platforms. No pre-qualification live fan-out is
authorized by this resequencing.

Platform priority becomes a deterministic admission and promotion policy rather than forced idle
time:

1. dependencies, recovery of an already owned claim, safety, and exact external blocks are handled
   first;
2. the highest-priority ready platform receives the first compatible resource slot;
3. at P3, otherwise idle capacity is assigned to another Python repository or Python stage until
   the all-Python milestone closes; lower platforms do not begin early;
4. after all Python repositories close, admission and promotion order remains .NET, Java, C++,
   TypeScript, Rust, Go;
5. aging prevents indefinite starvation, but never lets later work consume capacity reserved for a
   ready earlier-platform critical-path item.

This distinction preserves the user's priority while permitting independent Python repositories
and stages to overlap at P3. It does not permit lower-platform promotion before the all-Python
milestone or skipping an agent-fixable Python defect.

### Resource bulkheads and backpressure

Do not use one global `max_workers` as the safety control. The stage-pipeline table above is the
binding initial configuration: at P2 the total live-repository cap is one, and P3 begins with the
listed per-resource ceilings of four read/CPU lanes, two build/author lanes, and one
review/reducer lane. A per-repository lifecycle/effect writer always remains one and is protected
by the renewable run lease and fence. Remote-effect capacity is zero locally and one per
authorized repository in staging/production.

Use conservative additive-increase/multiplicative-decrease admission: increase one slot only after a
stable success window; halve the affected bulkhead on rate pressure, repeated retryable failure,
cleanup lag, or resource saturation; reduce to one on uncertainty. Concurrency control may delay or
retry work, never alter facts, prompts, validators, verdict thresholds, or terminal classification.
Persist every admission/backpressure decision in the campaign evidence.

### Production implementation shape

Do not extend the 692-line command adapter or the existing supervisor loop with another nested
orchestration concern. Keep `commands_supervision.py` as argument/profile wiring and introduce one
cohesive package under `src/readme_agent/supervisor/portfolio_scheduler/`:

```text
contracts.py     CampaignContractV1, work/result/receipt/aggregate schemas
dependencies.py declared stage dependency graph, cache keys, invalidation compiler
planner.py       durable-state/receipt reconciliation and ready-work derivation
priority.py      platform, critical-path, aging, and deterministic tie-breaking
admission.py     total-lane and resource-specific bulkheads/backpressure
lease.py         campaign/repository renewal, fencing, loss handling
lane.py          private attempt execution and seal protocol
reducer.py       sole receipt/state/aggregate/compatibility-view promotion
recovery.py      incomplete/sealed attempt reconciliation and retry classification
metrics.py       queue/service/resource/call observations outside acceptance hashes
```

Use an explicit spawned subprocess per live work item rather than threads or a
`ProcessPoolExecutor`. On Windows, the lane starts with `spawn` semantics, an explicit environment
allow-list, its own attempt/runs root, and an attributable process group. Extend the proven bounded
process-tree primitive so cancellation terminates the lane and all Git/compiler/package-manager
descendants. Do not pickle live Git backends, clients, locks, `ContextVar` state, or mutable caches
into a child. The child receives a validated JSON work contract, constructs its own read-only
clients/context, and returns a validated JSON result.

The first implementation refactor separates **prepare** from **promote** at the existing public
supervisor seam:

```text
prepare_stage(work_item, attempt_root) -> sealed LaneResultV1
promote_stage(lane_result, current_fence) -> StageReceiptV1 + lifecycle transition
```

Serial execution uses the same two functions inline. Concurrent execution changes only admission
and transport, so serial and parallel paths cannot drift into separate product logic. Registered
capabilities, validators, independent review, allow-list checks, push-blocking, and terminal
classification remain downstream dependencies of the stage executor rather than being copied into
the scheduler.

Extend the existing state backend protocol instead of creating a new database or queue:

- renewable campaign and per-repository leases with compare-and-swap generation changes;
- `renew_*`, `cancel_*`, and `fence_still_current` operations;
- one campaign-state ref and the existing independent per-repository refs;
- bulk read for scheduling, followed by a fresh CAS read at promotion;
- no force update except the existing exact-lease compare-and-swap release behavior.

If Git-ref measurements later show that renewal/reduction latency dominates, evaluate a backend
migration under the existing `StateBackend` seam. Do not preemptively add a service. Any replacement
must pass the identical CAS, fencing, recovery, history, redaction, and reproduction contract.

### Implementation mapping to the existing mission

No new mission or competing task tree is needed. Reconcile the design into these existing task
owners:

1. Complete `L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY` through
   `L8-INTAKE-03-REGISTRY-REVISION-QUEUE-AND-HEALTH` serially. Preserve the execution allow-list,
   make source inventory complete, enroll newly admitted read-only repositories in the existing
   lifecycle, and bind the campaign to a current complete registry revision.
2. Claim the then-ready regressed `L8-REVIEW-00-CONTEXT-CORPUS` task and repair its bounded factual
   reviewer output/transport contract serially. Requalify the sealed C++ canary, then return
   `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to `READY` and complete it plus
   `L8-REVIEW-05-REAL-CAMPAIGN`. The already closed repair and cache tasks remain reusable unless
   the repair invalidates them. A defect in this shared contract multiplies across every repository.
3. Treat closed `L8-COMPOSE-04B-STAGE-TRANSACTIONS` as P0 groundwork, not concurrency closure. Its
   receipts remain valid serial evidence, while qualification tasks extend the identical seam to
   every lifecycle stage and to a real portfolio campaign identity.
4. In `L8-QUAL-00-CAMPAIGN-SCHEMA` and `L8-QUAL-01-CAMPAIGN-IDENTITY`, implement and prove:
   - canonical `CampaignContractV1`, complete dependency graph, stage input/output contracts,
     logical-call identities, and invalidation compiler;
   - renewable campaign/repository lease generations and promotion fences in the existing backend;
   - receipt-only acceptance and a reducer-materialized compatibility view;
   - migration that labels the current receipt schema as legacy serial-stage evidence rather than
     silently changing its meaning.
5. Preserve the corrected qualification sequence in the sole graph:
   - `L8-QUAL-01A-REPRESENTATIVE-INPUTS` freezes the Python-first immutable
     seven-representative inputs;
   - `L8-QUAL-02A-FAILURE-MATRIX` depends on those inputs and owns P1 scheduler planning,
     deterministic priority, resource admission, spawned process isolation, lease renewal/fencing,
     private attempts, serialized reduction, cancellation/descendant cleanup, recovery, and
     serial/two-fixture-lane equivalence;
   - `L8-QUAL-02-SEVEN-E2E` depends on the P1 failure matrix and remains the only real
     seven-repository qualification campaign;
   - `L8-QUAL-03-RECOVERY` follows the real seven-repository campaign.
6. Under current decision #83, run the seven real representatives serially in Python, .NET, Java,
   C++, TypeScript, Rust, Go promotion order. Fixture concurrency may be proven, but paid/live
   representative fan-out remains disabled until all seven qualify and P3 is frozen.
7. Keep complete crash/recovery and long-duration heartbeat proof in
   `L8-QUAL-03-RECOVERY`; P1 fixture proof is not a substitute for this real boundary.
8. Measure queue wait, service time, provider pressure, cache reuse, call count, critical-path
   utilization, and serial-versus-parallel equivalence in `L8-QUAL-04B-COST-BASELINE`.
9. Freeze lane caps and all campaign dependencies in `L8-QUAL-05-FREEZE`.
10. Use adaptive P3 admission first in `L8-ACCEL-00-PYTHON-READINESS` through
   `L8-ACCEL-03-ALL-PYTHON`, then consume those valid results in
   `L8-GATEA-00-COHORT-CONTROLS` and `L8-GATEA-01-COHORTS`; retain upstream repair and targeted
   invalidation in the existing Gate-A healing tasks.

The executable graph migration must preserve transition history and update the graph hash through
the existing migration/evaluate path. The graph revision corrects the former reversed
qualification dependencies and adds the Python milestone chain atomically, so durable migration
cannot expose a transient cycle or bypass either the representative or full-registry gates.

### Verification and regression controls

Concurrency is accepted only if it is observationally equivalent to the qualified serial path
except for timing and recorded scheduling metadata:

- deterministic scheduler tests: stable work IDs, configured priority, no duplicates, no
  starvation, deterministic resume, and exact denominator;
- model-based state-machine tests: compare the production reducer with a small serial reference
  model over reordered completions, duplicate delivery, lease loss, retry, cancellation, and crash
  cut points. Evaluate the maintained Hypothesis rule-based state-machine library before
  hand-writing a large permutation harness, per decision #30;
- lease/fencing tests: renewal, expiry, reclaim, stale worker completion, late result rejection,
  reducer crash, and CAS conflict;
- process-isolation tests: distinct ContextVars/accounting, environment, attempt roots, work clones,
  caches, stdout/stderr, and descendant cleanup;
- stage/invalidation tests: mutate every campaign dependency and assert only the owning stage and
  descendants reopen;
- artifact-transaction tests: crash before seal, after seal/before promotion, and after promotion;
  partial files never count, while a sealed result promotes exactly once;
- resource tests: one slow build, rate-limited API, LLM timeout/retry, disk pressure, memory
  pressure, cancellation, and provider circuit opening affect only the owning bulkhead;
- cache tests: cold, warm, no-op, corrupted, cross-repository, cross-revision, cross-prompt,
  cross-model, and cross-campaign cases; no foreign cache hit is accepted;
- quality tests: serial and concurrent runs use identical inputs and deterministic outputs; all
  current presentation/factual/safety controls have identical verdicts; independent review still
  catches seeded defects;
- real P1/P2 proof: two fixture lanes, then the full seven-representative campaign serially with
  Python promoted first;
- Gate-A proof: two, three, and four lanes with backpressure, cancellation/resume, failure
  isolation, exact LLM accounting, no remote writes, and independently reconstructed aggregate;
- hosted proof: duplicate events, matrix job loss, scheduler absence, stale lease, lost response,
  and one repository failure without portfolio loss.

The promotion metric is not raw wall-clock speed. Record serial critical-path time, concurrent
critical-path time, queue wait, CPU/RAM/disk peaks, provider calls/tokens/cost, cache reuse,
retries, quality verdicts, false accepts/rejects, and recovery time. Promote a higher cap only when
quality/safety are unchanged, p95 elapsed time improves materially, and resource/retry behavior
remains within the recorded budget.

### Tradeoffs, risks, and limits

- Splitting prepare from promote is a non-trivial refactor of the canonical supervisor. It adds
  short-term implementation work, but avoids maintaining separate serial and concurrent product
  paths and is therefore cheaper than debugging race-dependent evidence later.
- Process lanes have startup and memory cost. At 31 repositories, two-to-four lanes are more likely
  to be stable than unbounded fan-out; measurement may prove that two is the permanent local cap.
- A single reducer is an intentional serialization point. It limits aggregate write throughput but
  makes campaign state reproducible and prevents “last writer wins.”
- Strict contract freezing can pause admission after a shared defect. This loses short-term
  utilization but avoids paying to create invalid candidates across the portfolio.
- Priority-preserving look-ahead is more complex than complete serial exhaustion. If evidence
  cannot prove that it leaves the earlier platform unaffected, P2 remains at one lane.
- LLM review and native builds may remain the bottlenecks. Concurrency cannot safely compress model
  rate limits, toolchain time, external outages, human Gate B, per-push approval, or the 30/90-day
  maturity windows.
- Exact rerun byte identity is realistic for deterministic stages and cache replays. A genuinely
  new LLM execution can vary; production consistency is therefore defined by identical inputs
  reusing the accepted receipt and changed inputs passing unchanged quality gates, not by claiming
  that nondeterministic generation itself is byte-stable.
- A provider call whose response is lost may be attempted again when the provider has no
  idempotency facility. The system guarantees one logical job and one promoted result, records
  every physical attempt and cost, and bounds retries; it must not claim exactly-once billing.
- The compatibility view creates a second physical copy of current artifacts, but not a second
  authority. Its manifest-to-receipt binding and independent reconstruction test are mandatory so
  reviewer convenience cannot become state divergence.
- Git-ref state remains viable at this scale, but campaign and lane measurements may show excessive
  ref latency/contention. A backend migration is justified only from those measurements and must
  preserve CAS, leases, fencing, transition history, and reproduction semantics.

### Disposition of the external testing/performance plan

`C:\Users\prora\.claude\plans\how-to-make-testing-shiny-lamport.md` is a useful supporting
performance investigation, but it is not execution authority and must not run as its own
11-parent/52-child controller. Much of its baseline predates the current 275-module runtime and its
Wave-1 prompt explicitly describes itself as unapproved and based on moving-tree evidence.

The following parts are adopted into the existing mission:

- speed must never change truth; cache hits require exact contract/input hashes and the same
  validation as fresh results;
- cache provenance and an explicit bypass are mandatory;
- measurement precedes optimization;
- unchanged review/no-op caching belongs to `L8-REVIEW-04-NO-OP-CACHE`;
- suite and per-stage cost measurement occurs immediately before qualification freeze;
- clone persistence and adaptive two-to-four-lane portfolio concurrency activate only after
  single-writer recovery and seven-representative correctness pass; the narrower proposed
  two-lane representative overlap activates only after fixture isolation, fencing, and the Python
  current-contract canary pass.

Pytest-xdist tiering, CI pip caching, cross-run clone persistence, and uncontrolled specialist
concurrency remain off the pre-qualification critical path. Process-isolated representative
overlap is admitted only by the progressive ladder above; post-qualification bounded portfolio
lanes remain a Gate-A contract. Other performance changes still require a measured trigger.
Executing them early would delay the first trustworthy README while caching potentially invalid
outputs. The external plan's separate `REQ-FAST-*` state machine and evidence authority are
rejected; accepted work is represented only in the sole Level-8 graph.

The first real full-registry execution disproved the assumption that the upstream composition,
review, and heterogeneous-qualification tasks could remain closed:

- The only `AGENT_APPROVED` live candidate, 3D Java revision
  `8de5f467e93138b3605acdc46ca40e93f0364ee8`, contains duplicate capability bullets, raw internal
  tokens (`java`, `open_source_scope`), and two competing usage examples.
- Its agentic composition plan says the usage section must be repaired to contain only the
  verified minimal example, but the executable document plan merely inserts another example and
  preserves the old one. The agentic assessment therefore does not fully control the candidate.
- The independent reviewer nevertheless returned `ACCEPT`, described the candidate as ready to
  ship, and praised details not actually presented to the visitor. Synthetic reviewer accuracy
  did not predict real-output quality.
- The Python repair loop generated byte-identical candidates on both repair attempts. A repair
  attempt that cannot change the responsible document operation is not a repair.
- .NET product truth advanced past typographic-quote repair but still produced an example with an
  unresolved type/namespace. This is an upstream evidence/example-selection defect, not a
  repository-specific Gate-A exception.
- Gate-A claims have expired repeatedly because the mission lease is shorter than long live
  qualification and test operations and has no active heartbeat.

The present route is therefore **replanned, not abandoned**. Gate-A fan-out pauses. The durable
statuses for composition, independent review/repair, and heterogeneous qualification must be
regressed/reopened with the live evidence above before another portfolio sweep. Product truth is
reopened for the affected ecosystem example boundary. The same mission graph remains the only
controller; resolver children are added beneath the existing local-PoC parent rather than
creating another plan or queue.

The correction is output-first: a system component is not qualified by schemas, test count,
synthetic fixtures, or a reviewer verdict alone. It is qualified only when real repository
outputs satisfy an explicit visitor-facing rubric, the candidate is exactly reconstructable from
the plan that claims to govern it, the independent reviewer detects seeded and naturally
occurring defects, and a repair produces a materially changed candidate that resolves the cited
finding.

## Multi-perspective findings that change execution

| Lens | Current evidence | Hidden factor and execution consequence |
| --- | --- | --- |
| Visitor/product value | `runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Java/8de5f467e93138b3605acdc46ca40e93f0364ee8/candidate/README.md` | The first approved output is less polished than its lifecycle suggests. Internal tokens, repetition, and two examples are visible in the first screen. Gate A must optimize the artifact a visitor sees, not the sophistication of the machinery that produced it. |
| Plan executability | The same bundle's `planning/agentic-composition-plan.json` says to repair the Usage section, while `planning/readme-document-plan.json` only inserts another example. | The agentic plan is partly advisory metadata. Every actionable assessment must compile into candidate-producing operations, or “agentic management” is not real. |
| Epistemic truth | The Java fact graph stores typed structures and policy enums, while the current overview flattens nested values into literal strings. The .NET bundle is `BLOCKED_MISSING_EVIDENCE` after a missing type/namespace. | Provenance validity does not imply prose suitability. Facts need separate typed render views; examples need symbol-level public-API proof, not merely plausible model output. |
| Evidence polarity | The .NET draft labeled existing rendering, mesh, export, and license APIs as limitations because the gate proved only that their positive symbols existed. | Evidence must prove the direction of a claim, not merely share its vocabulary. Negative constraints require explicit constraint evidence; positive API existence can never prove absence, incompleteness, or exclusion. |
| Independent review | `review/independent-agent-review.json` accepts the defective Java candidate and makes favorable assertions not reflected in the candidate. | Showing the reviewer producer plans and a deterministic acceptance result creates anchoring. Quality review and factual/plan review must be separated and reviewer statements must cite candidate spans. |
| Repair economics | The Python bundle's repair history records two identical candidate hashes after `REJECT_REPAIRABLE`. | A bounded retry count is meaningless if the operation space cannot change. Candidate-delta and finding-resolution checks must run before another costly review call. |
| Qualification validity | `plans/investigations/evidence/level8-local-heterogeneous-qualification-d30a811/agentic-qualification-summary.json` scores 157/159, but the first live approved artifact fails obvious quality checks. | Synthetic classification accuracy overstates end-to-end readiness. Qualification must include full real pipeline outputs and hidden real holdouts, with zero critical false accepts. |
| State and invalidation | Durable state version 135 marks composition/review/heterogeneous children `CLOSED`, while live Gate-A evidence disproves their acceptance assumptions. | Child closure is conditional on its contract and evidence standard. A newly observed live counterexample must reopen the first responsible child and invalidate dependent approvals automatically. |
| Time and concurrency | Gate A was recovered from expired claims three times; focused supervisor tests exceeded 60 seconds and left descendants until explicitly stopped. | Long-running work needs lease heartbeats, per-boundary time budgets, descendant cleanup, and resumable cohort execution. Otherwise the controller creates false regressions and operational churn. |
| Portfolio consistency | The registry has 31 entries, but only ten manifests and no current portfolio summary. Prompt, renderer, fact, and reviewer changes invalidate different stages at different times. | Gate A needs a frozen campaign identity. Without it, the denominator and contract move during execution and “31 complete” can become an endless or internally inconsistent target. |
| Reviewer accountability | The .NET reviewer called a selected `SOURCE_BUILD_VERIFIED` example `BUILD_FAILED` and based repair instructions on that false premise. | An independent reviewer is another fallible producer, not an oracle. Every material reviewer finding needs a candidate span and, for factual reasoning, an exact fact/evidence reference whose polarity is checked before the finding controls repair or lifecycle state. |
| Repository topology | The .NET snapshot contains converter, main-library, and test projects with different target frameworks. An unscoped compatibility view initially surfaced `.NET 10` from tooling instead of `.NET Core 3.1` from the acquired library. | Package roots have roles. Visitor claims bind to the acquired or distributed product root; test, sample, benchmark, converter, generator, and build-tool manifests are corroborating context, not interchangeable product truth. |
| Maintainer legitimacy | Byte preservation can retain stale promotion and unverified parity claims, while aggressive reconstruction can erase maintainer intent and repository-specific guidance. | The system needs claim-level ownership and confidence, not a binary preserve/rewrite choice. Machine-verifiable corrections may be automatic; subjective positioning and maintainer voice require policy ownership and visible rationale. |
| Acceptance-contract integrity | Replaying the current `classify_product_truth()` against four `NO_OP_PROVEN` bundles yields one `FACTS_READY` and three `BLOCKED_MISSING_EVIDENCE`. | A facts hash is not enough: required-field sets, eligibility rules, render-view rules, and evidence polarity form a versioned acceptance contract. Cached terminal state must be re-evaluated and reopened when that contract changes. |
| Inherited-claim accountability | `assessment_claims.py` defaults ordinary material prose to `preserve`; `claim_map.py` binds selected facts only to document operations. Python and TypeScript candidates therefore retain blocked capability/format/example claims outside the claim map. | Preservation protects bytes, not truth. Every material final-candidate claim needs an accepted fact, an authoritative policy/maintainer owner, or an explicit uncertainty/remove action before review can approve it. |
| Host and supply-chain safety | `example_execution.py` states that its credential-filtered subprocess is not an OS sandbox; Maven, .NET, Go, CMake, Cargo, npm, and Python build paths can execute repository or dependency code. | No real build or example may run on the operator host merely because secrets were removed. Use a disposable OS-isolated executor with bounded CPU/memory/time/processes/filesystem and deny-by-default network; pin every fetched dependency and record the environment image digest. |
| Complexity-to-value ratio | The control repository now has 275 Python source files and about 35,000 source lines, while no current README bundle survives the corrected end-to-end trust standard. | Machinery volume is not maturity. New work must close a visible failing output boundary, reuse an existing seam, and delete or split obsolete overlap; characterization without a concrete acceptance decision is not a deliverable. |
| Historical continuity | Git ancestry and reflog retain the implementation commits, but the handover's task/status snapshot is stale and contradicts live state. | Narrative handovers are derived views. Refresh them automatically from HEAD, graph, mission state, and evidence after transitions; never use them to override durable state or to prove completion. |
| Cost and latency | One real repository can require source builds, several LLM calls, bundle reconstruction, independent review, and two ineffective repair attempts. Full fan-out multiplies every defect by the registry denominator. | Cost, elapsed time, and call count are acceptance properties. Representative qualification, cache validity, changed-candidate prechecks, bounded cohorts, and per-stage budgets must be proved before scaling. |
| LLM accounting | `RunManifestV2` exposes `llm_call_count`/`llm_calls` but defaults them to zero; the canonical supervisor path does not emit records at the live client/provider boundary. The older evidence writer records only caller-supplied labels. | Existing README bundles cannot prove their call count. Mark them `UNKNOWN_LEGACY`; add one per-attempt redacted transport ledger and reconcile it into per-README and portfolio manifests before another paid campaign. |
| Prompt hygiene | The category layout and eager schema registry are sound. The stale `prompts/README.md` two-prompt claim was corrected during this plan update to inventory all ten active manifests, but manifests still do not declare owner/consumer/invalidation scope and no blocking check reconciles files, routes, call sites, or inline prompt text. | Keep the current categories, add ownership and dependency metadata plus one exact inventory check, and use Git history rather than backup/timestamped prompt files. Prompt mutations reopen only dependent stages. |
| Python product truth | The local adapter parses packaging metadata and detached syntax checks can succeed without proving that a selected module/symbol is publicly importable. The sibling pipeline already resolves package roots, `src`/namespace layouts, re-exports, visibility, typed fields, and stacked property decorators. | Adapt the committed public-API seams and prove the exact import/symbol in an installed disposable consumer. Do not spend another composition/review call on Python until this boundary passes. |
| TypeScript product truth | The local adapter parses `package.json`; repository-wide `tsc` plus a detached example does not establish that the package export map or generated declarations expose the selected API. | Adapt package-root, export/declaration, API-surface, format, and completeness behavior; pack/build the pinned artifact and compile a disposable consumer against its real exports. |
| Rust product truth | Local Cargo metadata and `cargo check` exist, but public visibility, modules/re-exports, traits/impls, fields/variants, rustdoc, and false-format controls are absent. | Adapt the sibling's three committed Rust implementation/hardening slices and their tests before Rust is treated as supported heterogeneous truth. |
| Security and legal | Repository text, examples, manifests, and linked material are untrusted; README changes can also alter license presentation, attribution, or commands visitors execute. | Prompt-injection resistance is necessary but insufficient. Examples run secret-free, fetched artifacts are pinned, licenses and attribution are ownership-sensitive, and no generated command becomes visitor-facing without deterministic safety and provenance checks. |
| Measurement causality | `idea.md` includes referral and traffic reporting, but traffic can change because of releases, campaigns, search ranking, or portfolio seasonality. | Traffic is an operational outcome signal, not proof that a README change is correct. Quality and safety gates remain primary; impact reporting needs baselines, change windows, and confounder notes and must never reward exaggeration. |
| Environment fidelity | A local source build can pass on one workstation while hosted Actions fails on runner images, rate limits, permissions, or network policy. | Local proof establishes product intelligence, not production readiness. `act`, disposable staging, and hosted canary evidence remain separate gates using the same contracts and artifacts. |
| Delivery governance | `plans/idea.md` requires Gate A/B before Java PR/App work; production access is not needed for the defects above. | Do not ask for GitHub App or product-write authority. The present critical path is entirely local and agent-fixable. |
| Maturity claim | Level 7 requires 30 production days and Level 8 requires 90; those clocks cannot begin before accepted hosted operation exists. | Architecture and test volume cannot compress elapsed operational proof. POC, Level 5, Level 7, and Level 8 remain distinct earned states with separate evidence. |

### Pinned `aspose.org` reuse boundary

The sibling repository at `D:\onedrive\Documents\GitHub\aspose.org` was inspected read-only on
`main` at `512a6e8dcdf220f0d7a81ab7882245f95b6d4ef9`. Its working tree is dirty, including metrics
files, so the working copy is not an admissible dependency or evidence source. Adaptation reads
only committed blobs with `git show <commit>:<path>`, records their SHA-256 and license, and maps
each source test to a local contract/test. The runtime must work when the sibling checkout is
missing.

The proven source seams are:

| Platform/concern | Committed source and tests to evaluate | Required local result |
| --- | --- | --- |
| Shared syntax/package extraction | `scripts/pipeline/extraction/tree_helpers.py`, `package_root.py`, `package_manifest.py`, `api_surface.py`, `formats.py`, `snippets.py`, and `outputs.py` at pinned HEAD | Small adapters behind `src/readme_agent/ecosystems/` and facts/public-API seams; no sibling import or monolithic copy |
| Python | `test_python_property_decorator_stack.py`, `test_scout_extraction.py`; property fix `08a861ad37b395c4db9432a6071f8dce42adfc6f` | Canonical package/import, public re-exports/symbols, full decorator-stack property handling, exact installed-consumer example proof |
| TypeScript | `commands/diagnostics/typescript_api_completeness.py`, `test_scout_extraction.py`; diagnostic commit `de78f8bc0c11645f3bec77fa265197483849f7f6` | `exports`/declaration-aware public surface and disposable consumer compilation against the pinned packed/built package |
| Rust | `test_rust_extraction.py`, `test_rust_platform_maps.py`, Rust fixture; commits `e131074708b17a85e078d3ba0939a0d126ea525a`, `e157b7ff992e8f6f48a969644b66422a653e75ba`, `abd634df3d9b2060b77b98aa9d6788553573ceea` | Cargo/lib identity, visibility/re-export/module/impl/field/variant/rustdoc truth, pinned acquisition, isolated example, and false-format controls |
| LLM metrics design reference | committed `commands/ops/metrics_schema.py`, `config/metrics_callsite_registry.yaml`, `tests/test_metrics_autonomous_capture.py` at pinned HEAD | Reuse the principles of transport-level automatic capture, call-site completeness, retries/cache distinction, tokens, redaction, and reconciliation; do not copy its Google-Sheet-specific payload or uncommitted changes |

Tree-sitter is a candidate dependency, not a preapproved conclusion. The implementing task must
evaluate the pinned sibling dependency/version and the current maintained package before adding a
direct lock entry. If it is adopted, parsing stays deterministic and syntax failures become typed
capability gaps; regex fallbacks may not silently claim public-API proof.

The principal architectural correction is therefore:

```text
facts as evidence graph
  -> versioned fact-acceptance contract and stale-state reopening
  -> typed visitor-facing fact views
  -> package-root role and ownership resolution
  -> OS-isolated source/example verification
  -> complete inherited-and-generated claim accountability
  -> executable agentic document operations
  -> deterministic reconstruction and presentation lint
  -> blind visitor-quality review
  -> independently grounded factual/plan review
  -> candidate-changing targeted repair
  -> real heterogeneous pipeline qualification
  -> frozen full-registry campaign
```

## Autonomous execution contract

The sole continuation loop is:

```text
read authority and durable state
  -> fingerprint HEAD and working tree
  -> reconcile the preceding gate
  -> claim the highest-priority dependency-ready task
  -> implement the smallest complete behavior
  -> run focused, regression, safety, and live-like proof
  -> independently verify
  -> repair the first failing boundary
  -> write redacted checksum-complete evidence
  -> transition the same task and update the same requirements/logs
  -> commit the coherent slice directly to main
  -> rebuild eligibility and continue
```

Do not stop for a session boundary, token boundary, completed commit, failing test, or a partial
portfolio result. An `agent_fixable` block creates or reopens a resolver and execution continues.
Only unavailable authority, credentials, external infrastructure, or irrecoverable external facts
may create `BLOCKED_EXTERNAL`; unrelated ready work continues.

No control-repository branches are created. Existing work is preserved: never reset, restore,
clean, force-push, or silently overwrite it. Every AI-authored commit contains the Codex trailer.

### One operator and one top-level process tree

During this autonomous implementation sprint, Codex is the only operator and the only agent allowed
to edit the control repository or launch top-level repository commands. Do not infer additional
workers from child Python, Git, Docker, compiler, or test processes: they belong to the single
operator's current process tree.

Before starting any long-running test, proof builder, supervisor campaign, build, or workflow
reproduction, inspect the repository process inventory. If an earlier top-level command from this
operator is still active, attach to or poll that exact process tree; do not launch a duplicate.
Run only one top-level test/proof/supervisor process tree at a time. Pytest-xdist, parallel test
sessions, and ad hoc portfolio commands remain disabled during local implementation. The canonical
supervisor may create the process-isolated repository lanes defined by the progressive promotion
ladder only after their lease/fencing/isolation gate is active; those lanes remain descendants of
the one command and are not additional operators. Every child must remain attributable to its work
item and must be terminated with its descendants on cancellation.

The future production system still requires leases, deduplication, and concurrency controls because
scheduled/event deliveries may overlap. That runtime obligation must not be misread as permission
to run multiple local implementation operators.

### Standing command authority

The user has granted standing authority for Codex to run every safe, plan-bound command available
in the current environment without a separate conversational approval. This includes repository
inspection, network reads, `.venv` dependency operations, formatting, focused and official tests,
Docker/isolated-executor work, `act`, local/staging preparation inside the authorized gate, runtime
process management for processes Codex started, evidence generation, and control-repository
edits/commits directly to `main`.

Do not pause merely to ask permission to execute such a command. If a command fails because a tool,
OS, sandbox, or credential boundary prevents it, diagnose and exhaust safe in-scope alternatives
immediately. Request human action only when the remaining step genuinely requires unavailable
external authority, credentials, infrastructure, a manual UI action, or an effect that the plan
explicitly gates.

Command authority is not effect authority. It does not authorize a product-repository push,
default-branch write, merge, package/release publication, organization-setting change, secret
disclosure, destructive history rewrite, or deletion of non-disposable user data. Those existing
what/why/where, authorization-record, safety, and human-only boundaries remain unchanged.

## State-machine design

### Mission control

Keep the existing mission schema and CAS Git-ref backend. Correct the following semantics before
using a rerouted full-registry task tree:

- Only `CLOSED` satisfies a dependency. `REROUTED` documents governed delegation and never
  unlocks downstream work.
- A rerouted parent reopens only after every mandatory child is `CLOSED`, then closes from an
  aggregate evidence bundle.
- Claims have expiry and renewal. A stale claim is recorded, released, and deterministically
  reclaimed; no second active claim is possible.
- `status` reads the graph and durable record, compares graph SHA-256, and visibly fails on drift.
- Graph additions, requirement coverage, static seed data, and durable state reconcile through one
  explicit migration command. Static taskcard status is only seed data.
- Requirement coverage, graph freshness, verifier-enforcement checks, semantic traceability, and
  official-check preconditions are blocking checks.
- Official-check evidence records HEAD, branch, dirty-tree fingerprint, dependency-lock hash,
  command versions, start/end time, and exit code. A changing tree invalidates the run.

Absorb valid RPOC and PRODSYS work as additive `L8-*` children in the existing graph. Preserve the
old files as cited diagnostic history, but never execute them as independent ledgers.

### Per-repository lifecycle V2

Migrate the existing additive README-POC lifecycle rather than adding another state store:

```text
DISCOVERED -> SNAPSHOTTED -> PROFILED -> FACTS_COLLECTING -> FACTS_READY
  -> README_ASSESSED -> PLAN_READY -> CANDIDATE_GENERATED
  -> DETERMINISTIC_VALIDATED -> AGENT_REVIEWING -> AGENT_APPROVED
  -> NO_OP_PROVEN -> HUMAN_REVIEW_READY -> HUMAN_ACCEPTED
  -> PR_ELIGIBLE -> PR_PROOF_COMPLETE
```

Permitted failure branches are `BLOCKED_FACT_CONFLICT`, `BLOCKED_MISSING_EVIDENCE`,
`SYSTEM_FAILURE`, `DETERMINISTIC_VALIDATION_FAILED`, `AGENT_REVIEW_REJECTED`, and `REPAIRING`.
Deterministic or agent-review failure enters `REPAIRING`; repair returns to
`CANDIDATE_GENERATED` and repeats validation and independent review. Two targeted repair rounds
are allowed per source revision. Exhaustion creates a visible resolver task; it never becomes
human copy-editing or false approval.

Changed source revision, facts, prompt, reviewer standard, or protected-content fingerprint
invalidates the earliest dependent state. `PR_PROOF_COMPLETE` may reopen on later upstream drift.

### Derived portfolio state

Portfolio state is computed from durable per-repository records and manifest validation, never
hand-authored:

```text
LOCAL_EXECUTING -> LOCAL_AGENT_APPROVED -> HUMAN_ACCEPTED -> ACT_PROVEN
  -> STAGING_PROVEN -> JAVA_README_PR_PROVEN -> GITHUB_APP_PROVEN
  -> LEVEL5_PROVEN -> LEVEL6_OPERATING -> LEVEL7_PROVEN -> LEVEL8_PROVEN
```

`LOCAL_AGENT_APPROVED` requires every registry entry to have an immutable snapshot, profile,
verified facts, assessment, document plan, candidate, native patch, deterministic validation,
independent `AGENT_APPROVED` verdict, unchanged no-op proof, and checksum-valid manifest.

The primary metric is always:

```text
complete local AGENT_APPROVED bundles / len(data/products.json)
```

### Canonical local interface and artifacts

Extend `supervise`; do not add a competing `manage-readmes` command:

```text
readme-agent supervise --registry data/products.json --execution-profile local_poc
```

`local_poc` is a typed profile with durable fail-closed state; read-only-local, read-only-network,
and local-write permissions only; required evidence and independent verification; local product
fact verification; mandatory dynamic planning; and no domain bypass. Every registry mode runs
locally; mode affects remote effects only.

Acceptance-authoritative runtime bundles are campaign-, repository-, revision-, work-, and
attempt-addressed under:

```text
runs/readme-poc/campaigns/<campaign-id>/
  campaign.json
  aggregate/{current.json,history/,sha256sums.txt}
  repositories/<org>__<repo>/<source-revision>/
    attempts/<work-id>/<attempt>/{request.json,artifacts/,result.json,sha256sums.txt,SEALED}
    receipts/<stage>.json
    current.json
```

The current revision-addressed layout remains an atomically generated human-facing compatibility
view whose manifest points back to the authoritative campaign receipts. Portfolio summaries at
`runs/readme-poc/portfolio-summary.{json,md}` are likewise derived views of the monotonic campaign
aggregate. Accepted redacted proof is promoted to one named evidence directory under
`plans/investigations/evidence/`.

## Execution phases and task dependencies

### Phase 0 -- stable checkpoint and constitutional reconciliation

1. Detect active writers, capture HEAD/branch/diff/untracked/process/mission/coverage snapshots,
   and preserve every current candidate artifact.
2. Investigate and split oversized touched modules before extending them.
3. Repair current Ruff/format failures and establish one stable official-check result.
4. Correct stale current-count and encoding defects in touched supporting documents.
5. Update this document in place; mark RPOC and PRODSYS records supporting-only.
6. Maintain `master.md` freely under current `GOV-023` and `GOVERNANCE.md` rule 12 whenever
   evidence, execution state, priorities, or architecture change. No fresh section-specific
   approval is required; preserve material history, update requirements with it, validate
   mechanically, and record significant changes in `logs/`.
7. Synchronize idea, requirements, governance, roadmap, status generator, root README, AGENTS,
   logs, and master under current governance.
8. Commit coherent verified slices directly to `main`.

Exit: clean committed main; truthful authority documents; all requirements including `L8-*` mapped;
stable official checks; no closure claim backed by a moving tree.

### Phase 1 -- one execution control plane

1. Add full-registry children beneath `L8-LOCAL-README-PROPOSAL-PROOF`.
2. Fix `REROUTED` dependency semantics before rerouting the obsolete three-Java interpretation.
3. Add state/graph migration, claim lease, graph-drift status, parent aggregation, and generated
   real-state snapshots.
4. Make coverage, semantic traceability, and verifier enforcement blocking official checks.
5. Reconcile durable state without deleting history, then claim the first full-registry child.

Exit: one graph, one durable state, one active claim, and a visible full-registry critical path.

### Phase 2 -- canonical local portfolio runtime

1. Add `--registry` supervision and `local_poc`.
2. Make dynamic planning unconditional in that profile while retaining compatibility behavior in
   other profiles.
3. Load every target from `data/products.json`; isolate failures per repository; resume from the
   last valid lifecycle state.
4. Write idempotent campaign/attempt artifacts, expose the revision-addressed compatibility view,
   and derive portfolio results from sealed receipts plus durable state.

Exit: a heterogeneous fixture registry runs through `supervise`; cancellation resumes without
duplicate LLM calls or bundles; no local POC run can issue a remote write.

### Atomic execution queue from the current checkpoint

The phase descriptions below remain the acceptance model. Execution uses these smallest
independently closable work items, in this exact dependency order. A taskcard is a durable
acceptance/transition boundary, not necessarily a separate implementation sprint, evidence
package, full-suite invocation, or commit. Adjacent ready items should be implemented as one
coherent campaign slice when they touch the same public seam, while focused proof and a
separately inspectable result mapping remain mandatory for every item. No item earns the next item
merely because code exists.

The executable mission graph decomposes each composition, review, qualification, and Gate-A
implementation item once more into an immediately preceding characterization or negative-control
task (`*-00-*` or `*-0xA-*`). The control task must reproduce the defect and freeze expected
behavior before its paired implementation task can become ready. These are not parallel ledgers:
they are dependency-interleaved children of the same aggregate tasks listed below. Characterize,
implement, and run focused proof without an intervening full-suite/evidence ceremony; promote the
shared campaign evidence only at the next declared output boundary.

#### Product-truth boundary (`L8-LOCAL-PORTFOLIO-PRODUCT-TRUTH`)

| ID | Complete behavior | Focused proof | Depends on |
| --- | --- | --- | --- |
| `L8-TRUTH-01-STAGE-LIMIT` | Add a typed `supervise` lifecycle ceiling so a facts run cannot invoke composition or review. | CLI/profile tests; one fixture registry reaches facts only; zero later-stage calls. | local portfolio runtime |
| `L8-TRUTH-01A-FACT-CONTRACT` | Version the complete fact-acceptance contract and re-evaluate cached fact graphs before reusing later lifecycle state. | the three falsely terminal real bundles reopen at the fact boundary; Java remains valid. | TRUTH-01 |
| `L8-TRUTH-01B-LLM-CALL-LEDGER` | Capture every provider attempt/cache reuse at the shared client seam and reconcile exact per-README/job totals, tokens, latency, outcomes, and optional cost into manifests. | success/failure/timeout/retry/cache/cancel/resume/redaction/dedup controls; legacy unknown; one exact new representative; unchanged no-op has zero new provider calls. | TRUTH-01A |
| `L8-TRUTH-01C-PROMPT-HYGIENE` | Make the active prompt registry a closed owner/consumer/job/dependency inventory and block paid fan-out on orphan, duplicate, inline, stale, or unsafe-deletion findings. | current-tree reconciliation plus negative controls and dependency-scoped cache invalidation. | TRUTH-01B |
| `L8-TRUTH-02-ROOT-ROLES` | Classify product/test/sample/converter/generator/benchmark/build roots and bind compatibility/acquisition to the distributed product root. | .NET multi-root regression plus Java and Python controls. | TRUTH-01C |
| `L8-TRUTH-02A-ASPOSE-ORG-ADAPTATION` | Freeze a provenance/license/test matrix for the pinned committed sibling extraction seams and select the smallest compatible dependencies/public seams. | every adopted behavior has commit/path/hash/source-test/local-test mapping; sibling absent/dirty controls. | TRUTH-02 |
| `L8-TRUTH-03A-ISOLATED-EXECUTOR` | Provide a disposable OS-isolated, resource-bounded, network-governed executor before any repository or dependency code may run. | hostile build-script, filesystem/network/process escape, timeout, cleanup, and environment-image digest controls. | TRUTH-02A |
| `L8-TRUTH-02B-PYTHON-API-TRUTH` | Adapt package/import/public-API/re-export/property/snippet behavior and prove selected symbols from an installed pinned package in the isolated consumer. | real Python representative plus namespace/src/__all__/re-export/private/stacked-property/missing-import controls. | TRUTH-03A |
| `L8-TRUTH-02C-TYPESCRIPT-EXPORT-TRUTH` | Adapt package export/declaration/public-surface behavior and compile exact examples against a pinned packed/built artifact in an isolated consumer project. | real TypeScript representative plus exports/subpaths/declarations/private/missing-export/unpublished controls. | TRUTH-03A |
| `L8-TRUTH-02D-RUST-API-TRUTH` | Adapt Cargo identity, visibility, modules/re-exports, impls, fields/variants, snippets, and formats from the three committed Rust slices. | real Cells Rust plus restricted-visibility/path/re-export/trait/format/acquisition/example controls. | TRUTH-03A |
| `L8-TRUTH-03-CLAIM-POLARITY` | Require positive evidence for capabilities and explicit directional evidence for limitations; shared vocabulary is insufficient. | false limitation controls and real .NET limitation evidence. | TRUTH-02B + TRUTH-02C + TRUTH-02D |
| `L8-TRUTH-04-ACQUISITION` | Verify registry coordinates or an exact source-build path without converting unpublished packages into global blocks. | known-false Cells Maven, NuGet, Go, Rust, C++, and isolated source-build controls. | TRUTH-03 |
| `L8-TRUTH-05-PUBLIC-EXAMPLES` | Prove imports/namespaces/public symbols and compile or execute comment-free visitor examples in the same isolated executor in every supported ecosystem. Evidence anchors remain source-grounding inputs; each consumer verifier derives the actual imported package symbols from the code instead of conflating those roles. | one real Python, .NET, Java, C++, TypeScript, Rust, and Go example in configured priority; source/documentation-comment and comment-like-string controls; filesystem/network/process escape negatives. | TRUTH-04 |
| `L8-TRUTH-06-INTERPRETIVE-VIEWS` | Ground audience/problem facts and expose only typed visitor-facing render views; reject slugs, enum tokens, manifest keys, and fragments. | Java raw-token, TypeScript sentence, and product-identity controls. | TRUTH-05 |
| `L8-TRUTH-07-SEVEN-ECOSYSTEMS` | Preserve and revalidate only when invalidated the completed stage-limited `FACTS_READY` proof for one real representative per supported ecosystem in Python, .NET, Java, C++, TypeScript, Rust, Go priority. Native-tool commands and raw-output hashes remain part of every bundle. | seven checksum-valid fact bundles with reproduction commands and recorded configured order; zero later-stage or unnecessary LLM calls. | TRUTH-06 |

#### Assessment/composition boundary (`L8-LOCAL-README-ASSESSMENT-COMPOSITION`)

| ID | Complete behavior | Focused proof | Depends on |
| --- | --- | --- | --- |
| `L8-COMPOSE-01-DECOMPOSE` | Split the oversized renderer/composition responsibilities before adding further editorial behavior. | public seams unchanged; focused renderer/composition regression. | product-truth aggregate closure |
| `L8-COMPOSE-01B-HEADER-VISUAL-CONTRACT` | Remove visitor-visible agent metadata and produce fact-backed headers, applicable badges, and repository-specific Mermaid overviews. | seven marker-free representative candidates; badge/fact and diagram/fact maps; legacy-marker migration. | COMPOSE-01 |
| `L8-COMPOSE-01C-CONTEXTUAL-LINKING` | Build domain-pure article catalogs, add only reader-useful context-bound links under configured-or-size-derived total/domain/surface ceilings, and render every `aspose.com` product as its Enterprise Edition. | seven example-to-article cases, every auto tier and configured override, catalog/count negatives, and legacy-terminology correction. | COMPOSE-01B |
| `L8-COMPOSE-02-EXISTING-SECTIONS` | Treat product-agent-curated source content as the preferred reusable base; preserve or improve each validated content unit, correct contradictions, and withhold unresolved material without silently discarding it. | real strong/partial README controls proving validated reuse, evidence-backed correction, explicit uncertainty, and unjustified-loss rejection. | COMPOSE-01C + section regressions |
| `L8-COMPOSE-02B-FINAL-CLAIM-CORPUS` | Inventory every material inherited and generated content unit, including claims, commands, examples, limitations, terminology, workflows, and maintainer explanations, and freeze its evidence/owner/correction/uncertainty/omission disposition. | real Python/TypeScript/Java inventories with expected ownership, fact bindings, reuse decisions, and stale/unresolved controls. | COMPOSE-02A |
| `L8-COMPOSE-03-OPERATION-COVERAGE` | Compile every actionable assessment into a bounded operation and require every material final-candidate claim to have an accepted fact, authoritative owner, or uncertainty/correction action. | plan-to-operation coverage, full-candidate claim coverage, inherited unsupported-claim controls, and immutable reconstruction. | COMPOSE-02B |
| `L8-COMPOSE-04-PRESENTATION-LINT` | Reject raw internal values, semantic duplicates, competing examples, cross-product leakage, malformed navigation, and promotional imbalance. | real Java/Python controls plus prompt-injection and strong-content fixtures. | COMPOSE-03 |
| `L8-COMPOSE-04A-CANDIDATE-FIXTURES` | Freeze immutable source revisions, accepted fact receipts, and expected visitor obligations for the seven representatives; do not claim candidate output from this input-only task. | source/fact/obligation hashes and independent input reconstruction. | COMPOSE-04 |
| `L8-COMPOSE-04B-STAGE-TRANSACTIONS` | Extend the canonical runtime through candidate and deterministic-validation ceilings and introduce the serial private-attempt/seal/reducer-promotion path used later by concurrent lanes. | crash-before-seal, seal-before-promotion, idempotent promotion, candidate-stage stop, and zero-review-call controls. | COMPOSE-04A |
| `L8-COMPOSE-05-SEVEN-CANDIDATES` | Produce product-specific candidate/patch/claim-map bundles for the seven representatives without invoking independent review. | stage-limited `CANDIDATE_GENERATED` and `DETERMINISTIC_VALIDATED` receipts plus byte-identical reconstruction. | COMPOSE-04B |

#### Independent review/repair boundary (`L8-LOCAL-INDEPENDENT-REVIEW-REPAIR`)

| ID | Complete behavior | Focused proof | Depends on |
| --- | --- | --- | --- |
| `L8-REVIEW-01-FREEZE-ROLES` | Freeze separate blind visitor-quality and factual/plan reviewer contracts; producer acceptance context is excluded from the blind role. | prompt/context inspection and anchoring negative control. | composition aggregate closure |
| `L8-REVIEW-02-FINDING-GROUNDING` | Require candidate spans and exact fact/evidence references for material reviewer findings; contradicted reviewer premises retry boundedly. | accepted-literal false-block and absent-content controls. | REVIEW-01 |
| `L8-REVIEW-03-EFFECTIVE-REPAIR` | Require changed candidate/operation hashes and resolution of cited spans before rereview; route unchanged repairs upstream. | controlled rejection changes the responsible section; byte-identical repair makes no second review call. | REVIEW-02 |
| `L8-REVIEW-04-NO-OP-CACHE` | Make unchanged reruns reuse valid facts, authoring, and review results without duplicate events, bundles, effects, or unnecessary LLM calls. | call-count, lifecycle-history, checksum, and cancellation/resume controls. | REVIEW-03 |
| `L8-REVIEW-05-REAL-CAMPAIGN` | Accept good and reject defective real outputs across all seven ecosystems under the frozen reviewer contract. | zero false accept for every known critical defect; approved representative bundles. | REVIEW-04 |

#### Heterogeneous qualification boundary (`L8-LOCAL-HETEROGENEOUS-QUALIFICATION`)

| ID | Complete behavior | Focused proof | Depends on |
| --- | --- | --- | --- |
| `L8-QUAL-01-CAMPAIGN-IDENTITY` | Bind HEAD, registry, revisions, dependencies, prompts, templates, facts, renderer, validators, reviewer, and lifecycle hashes into one immutable campaign. | mutation of each dependency invalidates only its dependent stage. | review aggregate closure |
| `L8-QUAL-02-SEVEN-E2E` | Run first proposal and unchanged no-op serially for one real representative per ecosystem under that campaign, promoting Python first and then .NET, Java, C++, TypeScript, Rust, and Go. | seven `NO_OP_PROVEN` manifests; fixture-lane/serial-reference equivalence; governed order; exact accounting; zero prohibited writes. | QUAL-01 + migrated P1 isolation prerequisite |
| `L8-QUAL-03-RECOVERY` | Complete production-like proof of renewable campaign/repository leases, fencing, mission heartbeat, serialized reduction, cancellation/resume, duplicate trigger, controlled failure, and descendant cleanup. | fault injection at every local lifecycle boundary, including a stale lane that finishes after reclaim and is rejected. | QUAL-02 |
| `L8-QUAL-04-GOLDEN-SET` | Run at least 100 governed evaluations in three sessions with 100% deterministic and at least 95% agentic accuracy, zero critical false accepts, and auto-disable regression. | three-session result inventory and route-disable proof. | QUAL-03 |
| `L8-QUAL-04B-COST-BASELINE` | Measure official-check, queue, service, per-stage, clone, registry, Docker, LLM, reducer, and warm/no-op latency, resources, retries, and call counts under the accepted representative contract; determine the safe P3 bulkhead caps. | reproducible cold/warm serial/two-lane distributions, quality equivalence, pressure controls, and explicit optimization triggers. | QUAL-04A |
| `L8-QUAL-05-FREEZE` | Freeze the accepted campaign, stage dependency map, resource caps, and lane contract; prohibit Gate-A execution after any dependent mutation until targeted representative requalification passes again. | enforced preflight rejection, invalidation-scope controls, and signed campaign manifest. | QUAL-04B |

#### Gate-A boundary (`L8-LOCAL-FULL-REGISTRY-GATE-A`)

| ID | Complete behavior | Focused proof | Depends on |
| --- | --- | --- | --- |
| `L8-ACCEL-00-PYTHON-READINESS` | Reconcile all runtime-loaded Python repositories against the frozen campaign and produce a reuse/evidence-readiness queue without a paid LLM call. | dynamic Python denominator, deterministic ordering, complete cache decisions, and zero-call receipt. | qualification aggregate closure |
| `L8-ACCEL-01-EIGHT-TOTAL` | Reuse the seven qualified representatives and finalize the highest-readiness unfinished Python repository so at least eight total repositories are current-contract `NO_OP_PROVEN`. | independent reconstruction of eight complete bundles; stale or mixed-campaign verdicts cannot count. | ACCEL-00 |
| `L8-ACCEL-02-EIGHT-PYTHON` | Use the governed P3 lanes until eight Python repositories are independently approved and no-op-proven. | dynamic Python milestone reconstruction, lane isolation/equivalence, exact calls, checksums, and no writes. | ACCEL-01 |
| `L8-ACCEL-03-ALL-PYTHON` | Continue the same campaign until every current Python repository is independently approved and no-op-proven. | Python numerator equals its runtime denominator; agent-fixable failures zero; external blocks remain non-success. | ACCEL-02 |
| `L8-TRUTH-08-FULL-REGISTRY` | Preserve the completed Python cohort, then run every remaining registry entry to `FACTS_READY` in .NET, Java, C++, TypeScript, Rust, Go order, isolating only narrow essential-fact blocks. | `facts_ready + narrow_external_blocks == len(products)`; zero agent-fixable failures; no valid Python stage repeated. | ACCEL-03 |
| `L8-GATEA-01-COHORTS` | Consume the completed Python cohort and execute the remaining frozen denominator through `PortfolioSchedulerV1` in bounded, resumable platform/family cohorts with one renewable campaign lease, fenced process lanes, stage bulkheads, and a serialized monotonic aggregate. | two-, three-, and four-lane interruption, stale-result, pressure, starvation, cache-contamination, and resume controls produce no duplicate work or order drift. | TRUTH-08 + GATEA-00 controls |
| `L8-GATEA-02-HEAL-FAILURES` | Repair every agent-fixable failure at its upstream task, requalify the affected representative, and rerun only invalidated repositories. | no agent-fixable terminal remains; external blocks are exact and narrow. | GATEA-01 |
| `L8-GATEA-03-NO-OP` | Obtain independent approval and unchanged no-op proof for every eligible current registry entry under the identical frozen campaign. | complete per-repository bundles and zero unnecessary second-run calls/effects. | GATEA-02 |
| `L8-GATEA-04-REPRODUCE` | Independently reconstruct the portfolio result and checksum inventory from registry plus bundles. | approved equals dynamic denominator; failures, unprocessed, and manifest failures equal zero. | GATEA-03 |

After `L8-GATEA-04-REPRODUCE`, close the four aggregate parent tasks from their child evidence,
then close `L8-LOCAL-README-PROPOSAL-PROOF`. Gate B remains a human authority boundary and is not
folded into these local implementation tasks.

### Phase 3 -- real-output acceptance corpus and campaign boundary

1. Reopen the affected upstream tasks using the durable transition mechanism and cite the current
   3D Java, 3D Python, and 3D .NET bundles as regression evidence. Gate A remains regressed until
   these children close again.
2. Establish a named local campaign record that freezes control HEAD, registry hash, prompt
   hashes, reviewer-standard hash, fact-contract hash, and one immutable source revision per
   repository. Later upstream changes create a new campaign; they do not silently move the target
   during a sweep.
3. Build a real-output acceptance corpus from at least one current repository per supported
   ecosystem plus the three governed Java pilots. Include original README, facts, plan, candidate,
   expected visitor-facing findings, and accept/reject rationale.
4. Add the naturally observed defects as mandatory controls: raw enum/taxonomy leakage, semantic
   duplicate bullets, repeated examples, missing limitations, private API use, unresolved
   namespace/type, plan/candidate disagreement, reviewer-reasoning claims absent from the
   candidate, and byte-identical repair attempts.
5. Keep synthetic controls for malformed input, prompt injection, fact conflict, and unsupported
   claims, but never let their score substitute for the real-output corpus.

Exit: the campaign is immutable and reproducible; every observed live defect is represented by a
failing acceptance case; the current Java false acceptance is rejected by the new standard.

### Phase 4 -- renderable product truth, not internal data leakage

1. Before another paid repository call, add `LlmCallRecordV1` at the shared live/fixture client
   boundary. Record success, failure, timeout, retry, and cache reuse with repository/revision,
   campaign/run/stage/job, prompt ID/hash, provider/model, attempt, timing, hashes, tokens, and
   optional versioned cost. Reconcile call IDs into per-README and portfolio manifests. Mark prior
   bundles without transport records `UNKNOWN_LEGACY`; never backfill an invented zero.
2. Reconcile `prompts/` as one closed active inventory. Add owner, job/consumer,
   input/output contract, and invalidation scope to each manifest; compare files to
   `JOB_MODEL_ROUTING`, the eager registry, runtime call sites, and documentation. Block paid
   fan-out on orphaned, duplicated, inline, stale, or still-referenced-deletion findings.
3. Freeze the committed `aspose.org` adaptation matrix from the pinned sources above. Record source
   commit/path/hash/license/source test, selected local seam/test, dependency decision, and any
   deliberately rejected behavior. Do not read the sibling working copy at runtime.
4. Capture real default branch, revision, README or explicit absence, inventory, package roots,
   manifests, examples, tests, docs, licenses, tags, and releases.
5. Keep `ProductFactsV2` as the provenance graph, but add typed, user-facing render views for
   identity, compatibility, relationship, acquisition, and support. Internal enums, manifest
   keys, repository slugs, and classification tokens are never eligible prose.
6. Classify every package root as product, test, sample, converter, generator, benchmark, build
   tool, or unknown. Bind installation, compatibility, and minimal-example claims to the root
   that supplies the acquired or distributed product; other roots may corroborate but must not
   silently override it.
7. Build one disposable, resource-bounded, deny-by-default-network executor before accepting any
   repository/dependency build or example result. Then close the three blocker adapters:
   - Python resolves `src`/namespace/package roots, canonical imports, `__all__`/re-exports,
     visibility, typed fields, and full decorator stacks, then installs the pinned package and
     imports/uses the exact public symbols in an isolated consumer.
   - TypeScript resolves `exports`/`types`/`main`/`module`, declaration or source public exports,
     visibility, and formats, then compiles a disposable consumer against a pinned packed/built
     artifact and its real export map.
   - Rust resolves Cargo/lib identity, canonical crate name, modules including `#[path]`, bare
     versus restricted visibility, re-exports, types/fields/variants/traits/impls/rustdoc,
     snippets, and format direction, then checks the pinned example in the isolated executor.
8. Prefer an existing public repository example that can be isolated and executed. If none exists,
   synthesize the smallest example only through the ecosystem adapter and require compile/run
   proof with diagnostic-driven repair. A missing import, namespace, symbol, private member, or
   unverified external input prevents `example.minimal` from becoming verified.
9. Enforce evidence polarity. Capabilities require positive implementation evidence; limitations
   require an exact repository-authored constraint anchor such as unsupported, incomplete, only,
   requires, or out-of-scope wording. A shared symbol or file path is not directional proof.
10. Distinguish facts required for a useful README from optional enhancement facts. An unresolved
   optional fact is omitted; an essential identity/acquisition/usage fact creates a narrow block.
11. Reconcile source-build-only repositories truthfully. Never describe a source build as a
   published package, and never make an unpublished artifact a global repository block when a
   verified build path exists.

Exit: no raw internal value can enter prose; every selected fact has evidence with the correct
claim direction; every selected example uses a public consumer surface and passes its ecosystem
proof; Python, TypeScript, and Rust blockers pass their pinned-source negative controls; every new
LLM call is exactly attributable; the prompt inventory is clean; and each real representative has
enough visitor-facing truth or one exact essential fact block.

### Phase 5 -- executable assessment and composition

1. Begin from the exact product-agent-curated README and inventory every material claim, command,
   example, limitation, terminology choice, workflow, and maintainer explanation. Prefer reuse:
   preserve validated content, improve it only when the change adds verified clarity, correct
   contradictions with cited evidence, and withhold unresolved factual material while retaining
   its source span and owner handoff. Never regenerate wholesale merely because it is easier.
2. Classify every material existing content unit as preserve-validated, improve-validated,
   investigate, correct, uncertainty/owner-handoff, omit-unsupported, add, or not-applicable.
3. Require every non-preserve assessment decision to map to one or more bounded
   `ReadmeDocumentPlanV1` operations. A decision that is not executable is a validation failure,
   not explanatory metadata.
4. Generate the candidate solely by applying the document plan to the immutable source. Rebuild
   the candidate independently from source plus operations and require byte identity.
5. Let the agentic author write visitor-facing section prose with explicit sentence/paragraph
   fact citations. Deterministic code constrains allowed facts, source spans, protected content,
   commands, coordinates, links, examples, and claim-map integrity; it must not flatten arbitrary
   nested fact values into prose.
6. Treat a link as contextual only when its verified target directly extends the adjacent claim,
   workflow, command, format, or code example. An exact family/platform/API-matched docs, KB, or
   reference article outranks a generic product page; product-domain preference breaks only ties.
   Store the target title and evidence plus a binding to the exact candidate section and
   claim/example ID. If no verified target adds useful detail, add no link.
7. Render every visitor-facing `aspose.com` product label as the verified product name plus
   `Enterprise Edition`. Correct legacy “commercial,” “On-Premise,” “paid,” “full,” or
   “proprietary edition” labels; retain them only inside immutable historical negative fixtures or
   machine-only compatibility fields that cannot render.
8. Allocate Aspose link slots through typed policy. Explicit configured total, parent-domain, and
   `products`/`docs`/`kb`/`blog`/`reference` maxima replace automatic allocation. Otherwise use the
   deterministic pre-link content-unit tiers in `L8-024`. Slots are maxima, not quotas, and neither
   configuration nor automatic availability can bypass context, verification, placement, or
   anti-promotion rules.
9. Add deterministic presentation validators for raw-token leakage, exact and semantic
   duplication, duplicate examples, heading/navigation consistency, unsupported plan omissions,
   stale or contradictory maintainer claims, contextual-link bindings, link allocation, and
   Enterprise Edition terminology.
10. Preserve the owned-span safety property, but do not confuse byte preservation with quality.
    Valuable validated content is preserved or improved; evidence-backed corrections replace the
    exact governed spans; unresolved content stays traceable outside factual presentation; the
    verifier rejects both unsupported retention and unjustified loss.

Exit: the plan, patch, candidate, and claim map agree exactly; the 3D Java usage repair removes or
reconciles the competing example; all real representatives are materially product- and
ecosystem-specific.

### Phase 6 -- blind quality review, factual review, and effective repair

1. Split independent acceptance into two fail-closed judgments:
   - a blind visitor-quality review sees original and candidate but not the producer verdict or
     deterministic “accept” result, preventing anchoring;
   - a factual/plan review sees the candidate, ProductFactsV2, claim map, and executable plan and
     checks support, preservation, and plan fidelity.
2. Combine both judgments deterministically. Either rejection prevents `AGENT_APPROVED`.
   Reviewer reasoning is itself checked: claims about content must point to candidate spans;
   factual premises must cite exact selected fact IDs and evidence excerpts; the cited evidence
   must prove the direction of the finding. An ungrounded or contradicted review is
   `SYSTEM_FAILURE`, never a repair instruction.
3. Calibrate the model route on the real-output acceptance corpus. The existing synthetic
   95-percent threshold remains necessary but is insufficient; real-output false-accept rate must
   be zero for all known critical defects and remain below the governed threshold on holdouts.
4. Feed section-scoped findings into the authoring/operation planner. Before another review call,
   require a changed candidate hash and mechanically prove that each cited span changed or the
   finding was explicitly shown inapplicable. A byte-identical “repair” immediately becomes an
   `agent_fixable` producer defect.
5. Do not spend both repair attempts on the same unchanged plan. Route factual defects to product
   truth, operation defects to composition, and quality defects to authoring; then repeat every
   deterministic and independent gate.
6. Preserve separate author/reviewer prompts, contexts, identities, caches, and evidence. If the
   current gateway route cannot satisfy the real corpus, disable it and qualify another available
   route before fan-out.
7. Derive per-stage duration, provider-call count, cache reuse, token totals, build time, failure
   class, and optional cost exclusively from the reconciled call/build ledgers. Reviewer retries
   remain separate attempts, and a cache hit never masquerades as a provider call. Establish a
   representative cost and latency envelope before the frozen campaign; a route that is correct
   but cannot finish within the resumable cohort budget is not portfolio-ready.

Exit: the former Java false acceptance is rejected and repaired; controlled real defects are
detected; repair changes the responsible operations and resolves the findings; identical reruns
create no new call, patch, event, or bundle.

### Phase 7 -- real heterogeneous qualification and contract freeze

1. Run the complete canonical pipeline—not isolated prompts—on the real acceptance corpus across
   Java, .NET, Python, TypeScript, C++, Go, and Rust.
2. Require every representative to reach `AGENT_APPROVED`, then rerun unchanged to
   `NO_OP_PROVEN`. Exercise cancellation/resume and one controlled failure at real lifecycle
   boundaries.
3. Run at least 100 governed agentic evaluations across three independent sessions after the real
   defects are incorporated. Require 100-percent deterministic validation and at least 95-percent
   agentic accuracy, with zero critical false accepts.
4. Add lease heartbeat/renewal around long repository, LLM, example-build, test, and portfolio
   operations. Recovery may reclaim an actually expired runtime claim/process tree, but ordinary
   long work must not regress every 30 minutes.
5. Freeze the accepted prompt, fact, renderer, validator, reviewer, and lifecycle hashes for the
   full-registry campaign. Any later contract change invalidates only the dependent artifacts and
   requires representative requalification before fan-out resumes.

Exit: every real ecosystem representative is approved and no-op-proven under one frozen contract;
known critical defects have zero false accepts; long operations retain or renew their claim.

### Phase 8 -- bounded full-registry local execution and Gate A

Run the canonical profile over the frozen campaign denominator in bounded ecosystem/family
cohorts. Produce a portfolio summary after every repository rather than waiting for the whole pass.
Repair agent-fixable failures at their upstream boundary, requalify the affected representative,
then resume only invalidated repositories. Requeue fact-blocked repositories after autonomous
evidence refresh and generate exact product-agent handoffs only for unrecoverable essential facts.
Continue until every registry entry has a complete approved bundle and no-op proof.

Gate A requires:

```text
approved == len(data/products.json)
system_failed == 0
unprocessed == 0
manifest_failures == 0
```

This is the locally proven full-registry README POC, not Level 5, 7, or 8.

### Phase 9 -- Gate B human-review package

Generate one indexed package with every source README, candidate, patch, facts, plan, validation,
review, limitation, and reproduction command. Human review starts only here. A human rejection
returns to autonomous repair, deterministic validation, and independent review.

### Phase 10 -- actual workflow under act

Run the same supervisor/profile under the reusable workflow using isolated local remotes. Exercise
workflow dispatch, repository dispatch, workflow call, simulated schedule recovery, matrix isolation,
deduplication, checkpoint resume, evidence upload, and health aggregation. Prove production profiles
reject PAT/GH-token fallback. Docker is needed only at this gate.

### Phase 11 -- disposable GitHub staging

Complete the staging subsets of `VerifiedProposalV1` and `OpenProposalV2`, then prove draft PR
create/no-op/update/drift/dedup/lost-response/expired-authorization/crash reconciliation with
staging-scoped credentials. Default branches remain byte-identical and analysis never receives a
write token.

### Phase 12 -- Gate C Java README PR publication proof

Use the already accepted Java candidates; do not regenerate README intelligence here. Before every
product push, present the exact diff, reason, repository, branch, and remote and obtain fresh
approval. Create or update draft PRs only. Never merge, mark ready, force-push, close, or write a
default branch. Gate C proves publication, not the README POC or Level 5.

### Phase 13 -- Gate D GitHub App and hosted runtime

Only after Gate C request the App registration, installation, permissions, repository scope, and
secrets. Validate short-lived effect-job tokens, analysis/effect isolation, deployment, trigger
recovery, leases, retry classes, health, alerts, backlog, dead-man monitoring, and manifests.

### Phase 14 -- broader presentation and Level 5

Implement and verify metadata, community files, license/contribution/security, visuals, truthful
manual social-preview handoff, package/release audit findings, generated-signal observations, and
cross-surface consistency. Then execute the controlled three-Java production pilot and obtain the
independent Level-5 award.

### Phase 15 -- Levels 6 and 7

Operate every registry repository in observe/proposal mode, prove one complete authorized lifecycle
per supported ecosystem, roll out remaining families, and maintain recovery, health, drift, proposal
age, authorization-expiry, dependency, SBOM, vulnerability, and quality reporting. Activate the
complete Level-8 control set and immutable evidence series on hosted day 1; the first 30 clean days
of that same series establish Level 7.

### Phase 16 -- Level 8

Continue the same hosted-day-1 series until it reaches 90 consecutive production days with weekly
full-registry audits, incremental
reevaluation, onboarding proposals, automatic route regression disablement, state migration and
outage recovery proof, stale-proposal reconciliation, external dead-man monitoring, and weekly
quality/referral reporting. Require every Level-8 metric in the authoritative plan and an independent
reproducibility audit. A period with weaker controls cannot be backfilled; an acceptance-breaking
day restarts or extends the affected consecutive window.

## Exact autonomous resume sequence

Execution resumes in this order; it does not start an official 31-repository campaign:

1. Re-read live HEAD, tree, graph hash, durable state, claim expiry, and the evidence paths in the
   multi-perspective table. Inventory repository-owned processes and establish Codex as the sole
   operator with exactly one active top-level command tree. Poll an existing tree instead of
   launching an overlapping test/proof/supervisor run. Treat any run whose HEAD or campaign
   dependencies moved as diagnostic only.
2. Run mission `status`; if the graph hash differs from durable state, run `evaluate` once to
   migrate without deleting transition history, then claim only the highest-priority eligible
   task. The expected next task after this amendment is
   `L8-INTAKE-00-DISCOVERY-TRUTH-AND-SAFETY`; live durable state supersedes this snapshot.
3. Complete the four `L8-INTAKE-*` tasks: source-complete observation, allow-list-before-preflight
   safety, provider-ID reconciliation, disabled/read-only enrollment, strong-README fast path,
   registry-revision campaign binding, same-run queueing, recovery, and discovery health.
4. Repair the bounded factual-review output and length-aware recovery contract. Preserve blind/factual
   role separation, evidence grounding, fail-closed behavior, exact calls, and candidate retention.
   Re-run focused, supervisor, safety, and no-remote-write regressions, then require the sealed C++
   canary to produce a complete governed verdict rather than transport truncation.
5. Close the repaired owner task only from checksum-complete evidence, return
   `L8-REVIEW-04A-REAL-CORPUS` from `REROUTED` to `READY`, and complete the real corpus and
   `L8-REVIEW-05-REAL-CAMPAIGN` serially in Python, .NET, Java, C++, TypeScript, Rust, Go order.
   The reviewer contract must freeze before any paid portfolio fan-out.
6. In `L8-QUAL-00-CAMPAIGN-SCHEMA` and `L8-QUAL-01-CAMPAIGN-IDENTITY`, version the existing
   serial-stage receipts, implement the complete campaign/dependency/call identity, and make
   receipts—not compatibility files—the acceptance authority.
7. Use `L8-QUAL-01A-REPRESENTATIVE-INPUTS` for one current-contract Python canary and the immutable
   seven-representative input freeze. Do not mislabel it as seven-repository proof.
8. Verify the migrated qualification edges, then implement P1 in
   `L8-QUAL-02A-FAILURE-MATRIX`: renewable fenced leases, deterministic planning and priority,
   resource bulkheads, process-isolated one-stage fixture lanes, sealed results, serialized
   reduction, recovery, and descendant cleanup. Two fixture lanes must be serial-equivalent; real
   representative execution remains one lane.
9. Execute `L8-QUAL-02-SEVEN-E2E` serially through the complete public supervisor path in configured
   order. Require all seven representatives to reach current-contract `AGENT_APPROVED` and unchanged
   `NO_OP_PROVEN`, with recovery, idempotency, safety, cache provenance, exact call accounting, and
   measured cost/latency evidence. Run the complete official suite once at this campaign boundary.
9. Freeze the registry, repository revisions, control HEAD, prompt/fact/renderer/validator/reviewer
   hashes, dependency lock, invalidation graph, lane caps, and cost envelope as one named campaign.
10. Run the Python-first acceleration chain under the frozen P3 contract:
    `L8-ACCEL-00-PYTHON-READINESS` with zero paid calls, then
    `L8-ACCEL-01-EIGHT-TOTAL`, `L8-ACCEL-02-EIGHT-PYTHON`, and
    `L8-ACCEL-03-ALL-PYTHON`. Use adaptive two-to-four supervisor-owned lanes, serialized
    aggregation, and the same per-repository proof. Do not stop at either eight milestone.
11. Preserve the closed Python bundles, run `L8-TRUTH-08-FULL-REGISTRY` for the remaining
    repositories to the facts-only ceiling, then resume Gate A in .NET, Java, C++, TypeScript,
    Rust, Go cohorts. A new live defect closes admission, reopens the first responsible task,
    requalifies the affected representative, and resumes only invalidated repositories. Promote
    one closure evidence package after the final official suite, not one package per failed attempt.
12. Present the Gate-B package only when the runtime-derived Gate-A equation is true. Continue with
   no-effect `act` work while Gate-B review is pending, then staging, Gate C, Gate D, and Level 5
   as their own dependencies permit. Start the complete Level-8 control/evidence series on hosted
   day 1, award Level 7 from days 1–30, and continue the same uninterrupted series to Level 8 at
   day 90.

## Verification, evidence, and human boundaries

Every task needs focused tests, integration tests through public seams, safety/regression tests,
live-like proof appropriate to the claim, failure/recovery/idempotency/evidence-corruption controls,
an independent verifier, a SHA-256 inventory, and reproduction instructions.

Those proofs may be produced by a shared campaign run, provided its manifest maps each result to the
owning task and requirement. Focused and affected safety checks run as soon as their seam changes.
The expensive aggregate is intentionally deferred to the next campaign boundary; it is not omitted.

The official control-repository gate runs Ruff, format check, mypy, non-live pytest, plan validation,
blocking coverage, blocking semantic traceability, blocking verifier enforcement, actionlint, and
`git diff --check` against a recorded stable tree at the four local campaign boundaries and every
later gate that claims the same scope. Re-running it after every micro-fix is churn; skipping it at
a declared boundary is incomplete proof.

Human involvement is limited to Gate-B review of already agent-approved candidates, Docker or
staging access if unavailable locally, staging credentials, exact per-product-push approval,
GitHub App registration
and secrets after Gate C, genuinely manual UI actions, independent acceptance authority, and
elapsed production time. All other implementation, testing, remediation, evidence, commits, setup,
monitoring, command execution, and continuation is autonomous. The operator does not request
permission for an available safe in-scope command; it requests only the external authority or
resource that the command cannot supply.

The mission closes only when every mandatory graph task is `CLOSED`, all requirements are
truthfully evidenced, all gates pass, the 30-day and 90-day periods complete, the independent audit
awards Level 8, and reevaluation finds no mandatory ready, reopened, regressed, or agent-fixable
blocked work.
