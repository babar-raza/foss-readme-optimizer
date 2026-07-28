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

The immediate outcome is a complete, repository-specific, independently agent-approved, local
README bundle for every current `data/products.json` entry. The denominator is loaded at runtime;
no fixed repository count is authoritative. The final outcome is the complete central
repository-presentation system and independently reproducible Level-8 award in `plans/idea.md`.

### Immutable core goal and subordinate goal system

`GOAL-CORE-PRESENTABLE-PORTFOLIO` is always active and cannot be replaced by the currently claimed
task: produce a professional, repository-specific, factually accountable README and GitHub-profile
bundle for every runtime-loaded `data/products.json` entry, independently approve it, prove an
unchanged no-op, and then carry the same deliverable through the ordered human, publication,
production, and maturity gates. The project is not successful because it has schemas, tests,
controllers, reports, evidence directories, or maturity prose; those are supporting means.

Six subordinate goals may own dependency-ready work, but none is an alternate stopping point:

1. `GOAL-TRUTH` -- verified product, acquisition, example, limitation, compatibility, and link
   evidence needed by the core bundle.
2. `GOAL-README` -- the actual marker-free product-specific README, badge header, visual overview,
   examples, contextual links, native patch, validation, repair, approval, and no-op proof.
3. `GOAL-PROFILE` -- GitHub description, homepage, topics, community-file findings,
   generated-surface observations, and product illustration.
4. `GOAL-AUTONOMY` -- the same output through one safe, resumable, isolated, idempotent,
   evidence-complete `supervise` runtime.
5. `GOAL-DELIVERY` -- Gate B, `act`, staging, Gate C, and hosted GitHub App operation in order.
6. `GOAL-MATURITY` -- complete surfaces, Level 5, heterogeneous Level 7, and the independently
   audited 30-day and 90-day operating windows.

Every task must name its subordinate goal and one measurable core contribution: a visible output,
the removal of its first failing boundary, an indispensable safety condition, or required
acceptance proof. A task that provides none is moved to backlog. After every transition, execution
recomputes a goal scoreboard from durable repository lifecycle state:

```text
registry denominator
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

## Current execution checkpoint and route correction (2026-07-28)

The verified pre-edit checkpoint is control-repository `main` at
`25a2820507febaf0f74860c6e363864105c22465`, clean and aligned with `origin/main`. Mission status
loaded graph `a7e4486a4ddb35a36efb44092893f06d870d003295b665d9d21e0e26dd25c7c5` without drift and reported
durable state version 320, active task `L8-TRUTH-07-SEVEN-ECOSYSTEMS`, 59 unresolved tasks, and one
external block. This document is supporting explanation; after these edits, live `status` and
`evaluate` remain the only authority for graph migration and claim recovery.

The corrected graph was reconciled without stealing the active claim or deleting transition
history. Durable state version 321 now binds graph
`519f4347fa75f1922baa35d0a86f3f89c0576562ac470051804e44891a801ccb`, retains
`L8-TRUTH-07-SEVEN-ECOSYSTEMS` as the exact next task, and reports no graph drift.

The runtime denominator is 31. Durable lifecycle state reports 7 repositories at `FACTS_READY` or
later, one candidate through `NO_OP_PROVEN`, and zero `HUMAN_ACCEPTED`. The single no-op-proven
3D Java candidate is not current-contract finalized output: it still contains visible marker
metadata and lacks the current factual badge header and Mermaid overview, and its inherited-claim,
link-allocation, and Enterprise Edition treatment predate `L8-020` through `L8-026`. The truthful
latest-contract README result is therefore 0/31. Python, TypeScript, and Rust public-consumer truth,
claim polarity, acquisition, public examples, and interpretive render views have current
checksum-complete proof. The active seven-ecosystem facts task still needs a real Go
representative under the same acceptance contract.

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
3. The portfolio command has per-repository trigger leases but no portfolio-wide single-writer
   lease. Two complete runs can inspect and mutate the same durable records concurrently.
4. The mission claim has a 30-minute expiry but portfolio, build, and LLM operations do not renew
   it. The active product-truth claim expired hours before this audit.
5. `portfolio-summary.json` describes only the current bounded prefix. It is not a frozen campaign
   ledger and cannot by itself answer which of 31 repositories remain valid under the current
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
until one Java, .NET, Python, TypeScript, C++, Go, and Rust README is independently approved and
unchanged-no-op-proven. A factual or safety defect reopens its first owner; a non-safety
presentation preference is logged to backlog instead of changing the campaign.

The existing 3D Java candidate is the first negative control. The deterministic contract must
reject its visible marker/comment, absent factual badge header, absent fact-backed Mermaid
overview, incomplete inherited-claim accountability, outdated link treatment, and obsolete
edition terminology before regeneration. Passing that negative control is followed by one
corrected 3D Java output, then the remaining six representatives, then full-registry truth and
candidate fan-out.

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
- clone persistence and specialist/portfolio concurrency are considered only after single-writer
  recovery and representative correctness pass.

Pytest-xdist tiering, CI pip caching, cross-run clone persistence, specialist concurrency, and
portfolio parallelism remain off the current critical path. They may be promoted only when measured
wall-clock or instability blocks the active atomic task. Executing them now would delay the first
trustworthy README while caching potentially invalid outputs. The external plan's separate
`REQ-FAST-*` state machine and evidence authority are rejected; accepted work is represented only
in the sole Level-8 graph.

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
sessions, specialist concurrency, and portfolio fan-out remain disabled during local
implementation unless a later measured task explicitly enables one behind the runtime's own
lease/isolation proof. Subprocesses required by the one active command are allowed, must remain
attributable to it, and must be terminated with their descendants on cancellation.

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

Runtime bundles are revision-addressed under:

```text
runs/readme-poc/<org>__<repo>/<source-revision>/
  source/{README.md,revision.json,repository-profile.json}
  facts/{product-facts.json,provenance.json,conflicts.json,acquisition.json}
  assessment/{current-readme-assessment.json,evidence-map.json}
  planning/{presentation-plan.json,selected-capabilities.json,decision-summary.json}
  candidate/{README.md,README.patch,claim-map.json,candidate-hash.txt}
  review/{deterministic-validation.json,independent-agent-review.json,
          repair-history.json,no-op-proof.json,final-verdict.json}
  manifest.json
```

Portfolio summaries are `runs/readme-poc/portfolio-summary.{json,md}`. Accepted redacted proof is
promoted to one named evidence directory under `plans/investigations/evidence/`.

## Execution phases and task dependencies

### Phase 0 -- stable checkpoint and constitutional reconciliation

1. Detect active writers, capture HEAD/branch/diff/untracked/process/mission/coverage snapshots,
   and preserve every current candidate artifact.
2. Investigate and split oversized touched modules before extending them.
3. Repair current Ruff/format failures and establish one stable official-check result.
4. Correct stale current-count and encoding defects in touched supporting documents.
5. Update this document in place; mark RPOC and PRODSYS records supporting-only.
6. Edit `master.md` freely under current repository governance when delivery evidence changes its
   Mission, Status, Decision Ledger, Architecture, Build Checklist, or Verification Checklist.
   Revise decision #78 in place instead of adding a competing decision.
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
4. Write idempotent revision-addressed artifacts and derive portfolio results from state/manifests.

Exit: a heterogeneous fixture registry runs through `supervise`; cancellation resumes without
duplicate LLM calls or bundles; no local POC run can issue a remote write.

### Atomic execution queue from the current checkpoint

The phase descriptions below remain the acceptance model. Execution uses these smallest
independently closable work items, in this exact order. Each item is one coherent commit plus
focused proof; no item earns the next item merely because code exists.

The executable mission graph decomposes each composition, review, qualification, and Gate-A
implementation item once more into an immediately preceding characterization or negative-control
task (`*-00-*` or `*-0xA-*`). The control task must reproduce the defect and freeze expected
behavior before its paired implementation task can become ready. These are not parallel ledgers:
they are dependency-interleaved children of the same aggregate tasks listed below.

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
| `L8-TRUTH-05-PUBLIC-EXAMPLES` | Prove imports/namespaces/public symbols and compile or execute comment-free visitor examples in the same isolated executor in every supported ecosystem. Evidence anchors remain source-grounding inputs; each consumer verifier derives the actual imported package symbols from the code instead of conflating those roles. | one real Java, .NET, Python, TypeScript, C++, Go, and Rust example; source/documentation-comment and comment-like-string controls; filesystem/network/process escape negatives. | TRUTH-04 |
| `L8-TRUTH-06-INTERPRETIVE-VIEWS` | Ground audience/problem facts and expose only typed visitor-facing render views; reject slugs, enum tokens, manifest keys, and fragments. | Java raw-token, TypeScript sentence, and product-identity controls. | TRUTH-05 |
| `L8-TRUTH-07-SEVEN-ECOSYSTEMS` | Run the same stage-limited runtime to `FACTS_READY` for one real representative per supported ecosystem, completing Go and reusing unchanged valid stages. Native-tool commands and raw-output hashes are part of every bundle. | seven checksum-valid fact bundles with reproduction commands; zero later-stage or unnecessary LLM calls. | TRUTH-06 |

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
| `L8-COMPOSE-05-SEVEN-CANDIDATES` | Produce product-specific candidate/patch/claim-map bundles for the seven representatives without invoking independent review. | stage-limited `CANDIDATE_GENERATED` bundles and byte-identical reconstruction. | COMPOSE-04 |

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
| `L8-QUAL-02-SEVEN-E2E` | Run first proposal and unchanged no-op for one real representative per ecosystem under that campaign. | seven `NO_OP_PROVEN` manifests; zero prohibited writes. | QUAL-01 |
| `L8-QUAL-03-RECOVERY` | Prove single-writer lease, mission heartbeat, cancellation/resume, duplicate trigger, controlled failure, and descendant cleanup. | fault injection at every local lifecycle boundary. | QUAL-02 |
| `L8-QUAL-04-GOLDEN-SET` | Run at least 100 governed evaluations in three sessions with 100% deterministic and at least 95% agentic accuracy, zero critical false accepts, and auto-disable regression. | three-session result inventory and route-disable proof. | QUAL-03 |
| `L8-QUAL-04B-COST-BASELINE` | Measure official-check, per-stage, clone, registry, LLM, and warm/no-op latency and call counts under the accepted representative contract. | reproducible cold/warm distributions and explicit optimization triggers. | QUAL-04A |
| `L8-QUAL-05-FREEZE` | Freeze the accepted campaign and prohibit Gate-A execution after any contract mutation until representative requalification passes again. | enforced preflight rejection and signed campaign manifest. | QUAL-04B |

#### Gate-A boundary (`L8-LOCAL-FULL-REGISTRY-GATE-A`)

| ID | Complete behavior | Focused proof | Depends on |
| --- | --- | --- | --- |
| `L8-TRUTH-08-FULL-REGISTRY` | Run all dynamically loaded registry entries to `FACTS_READY`, isolating narrow essential-fact blocks only after the seven latest-contract lifecycles qualify. | `facts_ready + narrow_external_blocks == len(products)`; zero agent-fixable failures. | qualification aggregate closure |
| `L8-GATEA-01-COHORTS` | Execute the frozen denominator in bounded, resumable ecosystem/family cohorts with one portfolio-wide writer lease and incremental summary. | interruption between every cohort resumes without duplicate work. | TRUTH-08 |
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
age, authorization-expiry, dependency, SBOM, vulnerability, and quality reporting. Accumulate 30
clean production days for Level 7.

### Phase 16 -- Level 8

Operate for 90 consecutive production days with weekly full-registry audits, incremental
reevaluation, onboarding proposals, automatic route regression disablement, state migration and
outage recovery proof, stale-proposal reconciliation, external dead-man monitoring, and weekly
quality/referral reporting. Require every Level-8 metric in the authoritative plan and an independent
reproducibility audit.

## Exact autonomous resume sequence

Execution resumes in this order; it does not start an official 31-repository campaign:

1. Re-read live HEAD, tree, graph hash, durable state, claim expiry, and the evidence paths in the
   multi-perspective table. Inventory repository-owned processes and establish Codex as the sole
   operator with exactly one active top-level command tree. Poll an existing tree instead of
   launching an overlapping test/proof/supervisor run. Enforce one portfolio writer and treat any
   run whose HEAD moved as diagnostic only.
2. Rebuild requirement coverage for the reviewed graph, validate it, run mission `status` and
   `evaluate`, and reconcile any historical claim without stealing a live lease. Execute
   `L8-MISSION-GOAL-GUARD` before resuming ordinary machinery work so every remaining task has a
   validated subordinate-goal and core-contribution binding and status exposes the live lifecycle
   scoreboard.
3. Resume `L8-TRUTH-07-SEVEN-ECOSYSTEMS` after durable evaluation. Complete the missing Go
   representative through `go list`, `go doc`, and `go test` inside the existing isolated executor;
   reuse unchanged valid facts for the other six ecosystems. Every representative records the
   official/native command, pinned toolchain identity, raw-result hash, normalized facts, and
   reproduction command. Do not start the full-registry facts preflight.
4. Execute `L8-LOCAL-README-ASSESSMENT-COMPOSITION`. First make the historical 3D Java candidate
   fail the frozen current-contract validator. Then split only touched responsibilities and
   implement marker/comment-free output, factual badges, fact-backed Mermaid, contextual
   catalog-backed link allocation, exact Enterprise Edition terminology, and complete
   inherited/generated claim dispositions. Regenerate and approve 3D Java before composing the
   remaining six representatives.
5. Execute `L8-LOCAL-INDEPENDENT-REVIEW-REPAIR`. Add span/fact-grounded reviewer findings,
   contradicted-review rejection, repair routing, candidate-delta checks, and finding-resolution
   checks before another paid review call.
6. Execute `L8-LOCAL-HETEROGENEOUS-QUALIFICATION` through the complete public supervisor path.
   Require seven real representatives to reach current-contract `AGENT_APPROVED` and unchanged
   `NO_OP_PROVEN`, with recovery, idempotency, safety, cache provenance, and measured cost/latency
   evidence. The normal provider budget is one composition, one independent review, and one
   targeted repair call; deterministic failures make zero new prose calls.
7. Freeze the registry, repository revisions, control HEAD, prompt/fact/renderer/validator/reviewer
   hashes, dependency lock, and cost envelope as one named campaign.
8. Run `L8-TRUTH-08-FULL-REGISTRY` to the facts-only ceiling under the qualified contract, then
   resume Gate A in bounded cohorts and publish the dynamic portfolio summary after every
   repository. A new live defect reopens the first responsible task, requalifies the affected
   representative, and resumes only invalidated repositories.
9. Present the Gate-B package only when the runtime-derived Gate-A equation is true. Continue with
   `act`, staging, Gate C, Gate D, Level 5, Level 7's 30-day proof, and Level 8's 90-day proof in
   the dependency order above.

## Verification, evidence, and human boundaries

Every task needs focused tests, integration tests through public seams, safety/regression tests,
live-like proof appropriate to the claim, failure/recovery/idempotency/evidence-corruption controls,
an independent verifier, a SHA-256 inventory, and reproduction instructions.

The official control-repository gate runs Ruff, format check, mypy, non-live pytest, plan validation,
blocking coverage, blocking semantic traceability, blocking verifier enforcement, actionlint, and
`git diff --check` against a recorded stable tree.

Human involvement is limited to Gate-B review of already agent-approved candidates, Docker or
staging access if unavailable locally, staging credentials, exact per-product-push approval,
GitHub App registration and secrets after Gate C, genuinely manual UI actions, independent
acceptance authority, and elapsed production time. `plans/master.md` remains freely editable under
the current repository governance. All other implementation, testing, remediation, evidence,
commits, setup, monitoring, command execution, and continuation is autonomous. The operator does
not request permission for an available safe in-scope command; it requests only the external
authority or resource that the command cannot supply.

The mission closes only when every mandatory graph task is `CLOSED`, all requirements are
truthfully evidenced, all gates pass, the 30-day and 90-day periods complete, the independent audit
awards Level 8, and reevaluation finds no mandatory ready, reopened, regressed, or agent-fixable
blocked work.
