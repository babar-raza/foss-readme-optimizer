<!-- This control artifact is consumed by scripts/retrofits/consolidate_level8_master_program.py. -->

<!-- BEGIN:MISSION -->
## Mission

Source: "GitHub Readme Agent – 2026.07.17", the 2026-07-18 follow-up comments, and the
approved 2026-07-23 Level-8 consolidation. Owner: Babar Raza.

- **Evidence-first product truth.** Repository source, manifests, tests, and verified package
  registries are authoritative for mechanically testable claims. Human-approved policy owns
  intent and positioning that code cannot prove. Existing README prose is a claim to verify,
  never truth merely because it already exists.
- **Credibility first, referral value second.** The system helps a developer understand,
  acquire, use, and trust each FOSS product before presenting relevant commercial context.
  Referral reporting is an outcome metric; it may never override factuality, ownership, or trust.
- **Central repository-presentation system, not a generic README rewriter.** The system assesses
  every applicable presentation surface, produces repository-specific plans, changes only
  authorized surfaces, and records findings for surfaces it cannot own.
- **Autonomous operation with passive human review.** `supervise` is the only production runtime.
  Normal authorized operation may create or update draft pull requests without synchronous
  operator initiation. Humans review proposals, authorization changes, blocked facts, and manual
  UI work; they do not select capabilities or drive normal runs command-by-command.
- **GitHub App production identity.** Production write jobs mint fresh, short-lived GitHub App
  tokens. Analysis, repository inspection, package/example execution, LLM work, and validation
  never receive a target-write token. Production profiles never fall back to `GH_TOKEN` or a PAT.
- **Bounded effects, never silent publication.** The system never auto-merges, marks a proposal
  ready, force-pushes, writes a target default branch, publishes packages/releases, or writes
  GitHub-generated surfaces. Repository settings require a distinct `github_apply`
  authorization after file-proposal review.
- **Per-repository quality, shared safety.** Each result is tailored to the product, ecosystem,
  audience, maturity, and verified facts. Shared standards define evidence and safety, not a
  cloned README template.
- **Measured maturity, not a feature-count claim.** The three Java repositories establish the
  controlled Level-5 pilot; heterogeneous production evidence and 30 clean days establish
  Levels 6–7; Level 8 requires an independently reproducible 90-day unattended proof.
<!-- END:MISSION -->

<!-- BEGIN:STATUS -->
## Status

The repository has a substantial capability, safety, authorization, state, specialist, evidence,
and proposal foundation, but it is **not Level 8**. The only active execution sequence is the
Waves 0–8 Build Checklist below.

Wave 0 truth consolidation completed on 2026-07-23:

- all preserved working-tree candidates were inventoried without deletion or implicit acceptance;
- all 85 high-confidence semantic closure findings were consumed: 76 `IMPLEMENTED` claims gained
  exact proof and 9 literal overclaims were downgraded to `PARTIAL`;
- the implementation-truth matrix now reports zero high-confidence closure findings;
- a clean `--no-local` clone of commit `146d81d` installed solely from the committed lock and
  passed 1,196 non-live tests, Ruff, formatting, mypy, plan validation, and actionlint for all
  nine workflows; and
- this approved consolidation replaces the obsolete phase/sprint tracks with one current program.

Primary current evidence:

- `plans/investigations/evidence/level8-semantic-closure-verification.json`
- `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`
- `plans/investigations/evidence/level8-requirement-taskcard-coverage/`
- `plans/investigations/evidence/level8-wave0-fresh-clone-head-reproduction/`
- `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`

`plans/requirements.md` is the normative obligation register. `logs/` is history.
`docs/architecture.md`, `docs/safety-model.md`, `docs/policy-authoring.md`,
`docs/presentation-standard.md`, and `docs/github-surface-control.md` describe current
implementation contracts. No untracked plan candidate is execution authority.
<!-- END:STATUS -->

<!-- BEGIN:DECISION-26-AMENDMENT -->
    **Amended 2026-07-23 for the Level-8 consolidation:** `supervise` is the sole production
    runtime and controller. `generate`, `run`, and `run-registry` may remain only as read-only or
    compatibility façades routed through the same registered capabilities, authorization checks,
    effect ledger, and independent final verifier; they may not retain an alternate production
    mutation path. Normal production work is schedule/event driven and humans passively review
    verified proposals rather than selecting capabilities or invoking pipeline stages.
<!-- END:DECISION-26-AMENDMENT -->

<!-- BEGIN:DECISION-32-AMENDMENT -->
    **Amended 2026-07-23 for restartable production operation:** the per-repository Git-ref backend
    remains the selected store, but production correctness now requires versioned state migrations,
    durable trigger intake, all lifecycle checkpoints, expired-lease recovery, proposal
    reconciliation, and fail-closed behavior whenever state is uncertain. GitHub-native
    concurrency queues jobs; it does not replace durable recovery because scheduled jobs can be
    delayed or dropped. Revisit the backend only when measured scale, state size, or cross-repo
    query/dashboard needs exceed the Git-ref design.
<!-- END:DECISION-32-AMENDMENT -->

<!-- BEGIN:DECISION-33-AMENDMENT -->
    **Amended 2026-07-23 for the final production authorization model:** reviewed, expiring
    authorization records may permit normal automation to create or update **draft** pull
    requests without a synchronous per-run confirmation. This never authorizes auto-merge,
    ready-for-review transitions, force pushes, default-branch writes, package/release writes, or
    GitHub-generated-surface writes. Repository settings require a separate `github_apply`
    authorization and effect. Production write jobs use a fresh GitHub App installation token;
    production profiles do not accept PAT/`GH_TOKEN` fallback. Every proposal still records exact
    what/why/where, fact sources, validation, verifier result, rollback, and authorization ID.
<!-- END:DECISION-33-AMENDMENT -->

<!-- BEGIN:DECISION-37-AMENDMENT -->
    **Amended 2026-07-23 for `ProductFactsV2`:** repository/source/manifests/tests and verified
    external registries take precedence for mechanically testable facts; approved policy facts
    own intent or positioning that code cannot prove; releases and approved documentation follow;
    existing README prose is only a claim to verify. Every fact carries provenance, revision or
    retrieval time, verification state, authoritative owner, confidence, conflicts, and affected
    surfaces. Missing facts block only dependent actions; conflicts block affected proposals and
    produce actionable findings.
<!-- END:DECISION-37-AMENDMENT -->

<!-- BEGIN:NEW-DECISIONS -->
73. **One production runtime and one write boundary.** `supervise` consumes every production
    trigger and is the only runtime allowed to reach a target-repository effect. All mutations pass
    through the capability registry, typed profile/permission checks, authorization registry,
    effect ledger, independent verifier, and terminal classifier. Analysis and effect execution
    are separate GitHub Actions jobs; only the effect job receives a fresh GitHub App token.
    Compatibility commands cannot independently acquire write authority. Production never falls
    back to a PAT or `GH_TOKEN`, never auto-merges, and never writes a target default branch.

74. **Versioned lifecycle and checkpoint recovery are production contracts.**
    `TriggerEnvelopeV2`, `CheckpointV1`, and schema migrations define durable intake and progress.
    Trigger states are `accepted`, `processing`, `blocked`, `retryable`, `failed`, `completed`, and
    `deduplicated`; unknown/newer schema versions fail closed. Every scheduled sweep recovers
    accepted/processing/retryable work whose lease expired. `HealthReportV1` exposes missed
    windows, backlog, stale leases, repeated failures, rate limits, evidence failures, open
    proposals, and last success. `RunManifestV3` binds trigger, checkpoints, facts, plan,
    authorization, verifier, effects, and requirement results.

75. **Verified proposal is the immutable boundary before an effect.** `ProductFactsV2` feeds a
    repository-specific `RepositoryPresentationPlanV1`; bounded renderers produce candidates;
    factuality, ownership, regression validators, and an independent verifier produce
    `VerifiedProposalV1` against an immutable base revision. `open_presentation_pr` is a separately
    authorized terminal effect. It refetches the target head before every push, rebuilds and
    reverifies on drift, uses one agent-owned branch without force push, and reconciles branch,
    commit, and PR crash boundaries into `OpenProposalV2`. Settings remain separate effects.

76. **Maturity levels are awarded only by elapsed production evidence.** Level 5 requires the
    complete controlled three-Java-repository pilot. Level 6 requires restartable scheduled/event
    operation with passive human review. Level 7 requires terminal evidence across every active
    registry repository, one full lifecycle per supported ecosystem, operational health/recovery,
    and 30 consecutive production days with zero unauthorized writes, duplicate effects, or false
    convergence. Level 8 requires 90 consecutive production days, at least 99% eligible-run
    completion without human intervention, checksum-complete manifests for every terminal run,
    recovery within 24 hours, visible proposal age/drift, 100% deterministic validation, at least
    95% agentic golden-set accuracy, and an independent reproducible audit.
<!-- END:NEW-DECISIONS -->

<!-- BEGIN:ARCHITECTURE -->
## Architecture

### Canonical production flow

```text
schedule / repository_dispatch / workflow_call / operator request
  → normalize TriggerEnvelopeV2
  → persist and deduplicate trigger
  → acquire per-repository lease
  → capture immutable repository snapshot
  → profile repository and every package root
  → build provenance-complete ProductFactsV2
  → assess every applicable presentation surface
  → build RepositoryPresentationPlanV1
  → render bounded candidates/proposals
  → factuality + ownership + regression validators
  → independent final verifier
  → persist VerifiedProposalV1 / effect request
  → separately authorized effect job with fresh GitHub App token
      → create or update draft PR
      → or apply separately authorized repository settings
      → never merge, force-push, or write a default branch
  → reconcile effect and OpenProposalV2 state
  → write checksum-complete RunManifestV3 and terminal checkpoint
  → aggregate health, backlog, proposal age, and drift
```

GitHub Actions is the production compute platform. A planning job emits the authoritative
repository matrix; per-repository jobs use GitHub concurrency queuing plus durable CAS leases.
GitHub concurrency is an optimization and overlap guard, not the recovery system.

### Trust and token boundaries

| Boundary | Allowed identity and behavior |
|---|---|
| Analysis | Read-only repository/package access; no target-write token; repository text is untrusted data |
| LLM planning | Structured proposals/actions only; no credentials or direct effects |
| Validation | Secret-free, isolated examples/install checks; deterministic factuality, ownership, and regression gates |
| Verification | Independent from the proposal author; produces a candidate-bound verdict |
| Effect job | Fresh, short-lived GitHub App installation token; exact authorization/effect scope only |
| Default branch, merge, releases/packages, GitHub-generated surfaces | No autonomous write path |

Every GitHub production profile fails closed if durable state, authorization, facts, verification,
or effect identity is uncertain. Production profiles never accept PAT/`GH_TOKEN` fallback.

### Versioned lifecycle contracts

- `TriggerEnvelopeV2`: provider event ID, event type, repository scope, delivery/run ID, source
  revision, schedule window, occurrence time, and deduplication key.
- `CheckpointV1`: trigger, run, repository, stage, task/action, attempt, input/output hashes,
  timestamps, and failure classification.
- `ProductFactsV2`: stable fact IDs, values, provenance, revision/time, verification, owner,
  confidence, conflicts, and affected surfaces.
- `RepositoryPresentationPlanV1`: findings, surface actions, dependencies, fact citations,
  ownership class, operation, validators, rollback, and stop conditions.
- `VerifiedProposalV1`: immutable base revision, facts/plan/candidate hashes, validation and
  verifier results, authorization ID, and expiry.
- `OpenProposalV2`: stable proposal/PR/branch identity, base/head/candidate revisions, state, age,
  drift, authorization, and reconciliation result.
- `HealthReportV1`: schedule/backlog/lease/failure/rate-limit/evidence/proposal health.
- `RunManifestV3`: the checksum-complete terminal evidence index.

All contracts have explicit migrations from supported older schemas. Unknown/newer versions fail
closed. Recovery resumes or reconciles from checkpoints; it does not infer success from absence.

### Facts and surface ownership

Fact precedence is:

1. mechanically verified repository/source/manifests/tests and external package registries;
2. approved policy facts for intent or positioning code cannot prove;
3. releases and approved documentation;
4. existing README prose as a claim requiring verification.

Each surface is classified as repository-file, settings/API, manual UI, product-owned, or
GitHub-generated. Missing facts block only dependent actions. Conflicts block affected proposals.
Protected terminology, commands, examples, limitations, and maintainer-authored regions receive
fingerprints; removing or weakening protected content fails validation.

### Proposal and effect lifecycle

File proposals use one agent-owned presentation branch per repository and draft PRs only. Before
each push the effect job refetches the target head; drift invalidates the candidate and requires a
new snapshot, plan, render, and verification. Durable state and GitHub are both reconciled after
crashes at branch-created, commit-pushed, and PR-created boundaries. No force push is permitted.

Repository description, homepage, and topics are separate fact-backed proposals and require
distinct `github_apply` authorization. Social preview is a prepared asset plus manual-application
evidence. Releases/packages are audit and owner findings only. GitHub-generated signals are
observations only.

Detailed current module placement and the preserved shipped-engine seams live in
`docs/architecture.md`; safety properties remain normative in `docs/safety-model.md`.
<!-- END:ARCHITECTURE -->

<!-- BEGIN:BUILD-CHECKLIST -->
## Build Checklist

This is the only active execution sequence. The former Phases 0–26 and Waves 0–15 are retained
only as historical implementation evidence in decisions and `logs/`; they are not parallel plans.

- [x] **Wave 0 — Truth consolidation and shippable baseline**
  - [x] Preserve and classify every dirty/untracked artifact without reset, restore, clean, or
        implicit acceptance.
  - [x] Commit the controller, requirement coverage, semantic closure, and fresh-clone evidence in
        coherent green commits.
  - [x] Reduce active planning authority to `idea.md` (vision), this file (architecture/sequence),
        `requirements.md` (normative obligations), the durable task graph (execution state), and
        `logs/` (history). Untracked `roadmap.md`, `status.md`, and `changelog.md` are not authority.
  - [x] Replace path-only closure with semantic proof; downgrade unsupported `IMPLEMENTED` claims.
  - [x] Reproduce the committed code/dependency baseline from a fresh lock-only clone.
  - [x] Install this approved Waves 0–8 sequence and synchronize requirements.
  - **Exit:** plan validation and semantic traceability pass; no master/requirements/task-graph
    contradiction remains; the code/dependency baseline reproduces cleanly.

- [ ] **Wave 1 — Canonical correctness and safety spine**
  - Split oversized supervisor/orchestrator/command responsibilities before extension.
  - Make `supervise` the sole production path; turn legacy commands into read-only/compatibility
    façades through the same registry, authorization, ledger, and verifier.
  - Eliminate the legacy unverified mutation path and enforce typed capability I/O plus complete
    terminal classification.
  - Reprove .NET, Python, C++, and Go false-success scenarios fail closed; return explicit
    unsupported results for unimplemented ecosystems.
  - Make offline cancellation credential-free and descendant-clean.
  - **Exit:** no required failure exits zero or converges; no production mutation bypass exists.

- [ ] **Wave 2 — Restartable GitHub Actions runtime**
  - Ship `TriggerEnvelopeV2`, `CheckpointV1`, migrations, seven trigger states, and all lifecycle
    checkpoints.
  - Ship one reusable production workflow, authoritative planning matrix, per-repo queueing/CAS
    leases, recovery sweeps, typed retry policies, rate-limit handling, and fail-closed state.
  - Ship `HealthReportV1`, alerts, external dead-man monitoring, and `RunManifestV3`.
  - **Exit:** kill/resume passes at every checkpoint; duplicate delivery creates one logical
    execution/effect; every accepted trigger is terminal or visibly retryable/blocked.

- [ ] **Wave 3 — Product truth and ownership**
  - Ship `ProductFactsV2`, precedence/conflict behavior, per-surface ownership, fact citations,
    protected-content fingerprints, and prompt-injection treatment.
  - Execute examples/package acquisition in isolated, secret-free jobs.
  - **Exit:** false coordinates cannot reach proposals; missing/conflicting facts cannot create
    generic replacement prose; removing protected facts fails.

- [ ] **Wave 4 — Presentation intelligence and complete surfaces**
  - Ship `RepositoryPresentationPlanV1`, source-span README patches with `markdown-it-py`, Git
    three-way application, ten presentation dimensions, and differentiated archetypes.
  - Implement fact-backed metadata/community/visual proposals and audit-only package/release and
    GitHub-generated surfaces.
  - Establish the real/synthetic golden set, 100% deterministic validation, and ≥95% agentic
    selection over at least 100 evaluations across three sessions; auto-disable regressed routes.
  - **Exit:** independent reviewers need no prose repair and no unsupported/template/ownership
    violation passes.

- [ ] **Wave 5 — Verified proposal and effect lifecycle**
  - Ship `VerifiedProposalV1`, `OpenProposalV2`, automatic draft-PR terminal effects, stale-head
    rebuild/reverification, branch/commit/PR crash reconciliation, and proposal age/drift.
  - Separate file PR authorization from later settings authorization; mint GitHub App tokens only
    in the effect job; prohibit production PAT fallback.
  - **Exit:** create/no-op/update/drift/duplicate/lost-response/expired-auth/crash scenarios each
    produce exactly one correct proposal state with zero write-token exposure before effect.

- [ ] **Wave 6 — Controlled three-repository Java pilot (Level 5)**
  - Prove the governed 3D, Cells, and PDF Java cases across facts, every surface, verified draft
    PR, no-op, upstream change, maintainer overwrite, interruption, deduplication, controlled
    failure, evidence bundle, and independent review.
  - **Exit:** all three complete the full production-like acceptance bundle. This is a controlled
    Java pilot, not heterogeneous proof.

- [ ] **Wave 7 — Heterogeneous production portfolio (Levels 6 and 7)**
  - Run all registry repositories in observe/proposal mode; then prove one authorized repository
    per Java, .NET, Python, TypeScript, C++, Go, and supported Rust ecosystem.
  - Roll out by Java pilots, seven-ecosystem set, remaining families, then observe-only discovery.
  - **Level 6 exit:** restartable schedule/event operation creates draft proposals without routine
    human initiation; humans only review proposals, authorization, blocked facts, and manual UI.
  - **Level 7 exit:** every active repository has terminal evidence, each ecosystem has a full
    lifecycle, health/recovery is operational, and 30 consecutive production days have zero
    unauthorized writes, duplicate effects, or false convergence.

- [ ] **Wave 8 — Proven self-maintenance (Level 8)**
  - Run weekly full-portfolio and incremental reevaluation, observe-only discovery proposals,
    golden-set route disablement, dependency/SBOM/vulnerability monitoring, authorization expiry,
    schema migrations, stale-proposal reconciliation, freshness, dead-man monitoring, and weekly
    quality/traffic reporting.
  - **Exit after 90 consecutive production days:** zero prohibited writes/duplicate effects/false
    success; all accepted triggers terminal or visible; all terminal manifests checksum-complete;
    ≥99% eligible runs autonomous; crash/outage recovery ≤24h; proposal age/drift visible ≤24h;
    deterministic validation 100%; agentic accuracy ≥95%; independent audit awards Level 8.
<!-- END:BUILD-CHECKLIST -->

<!-- BEGIN:VERIFICATION-CHECKLIST -->
## Verification Checklist

- [x] **Wave 0 truth gate:** candidate inventory is checksum-addressed and originals remain
      recoverable; semantic matrix has zero high-confidence closure findings; unsupported claims
      are downgraded.
- [x] **Wave 0 reproducibility gate:** lock-only fresh clone passes Ruff, formatting, mypy,
      1,196 non-live tests, plan validation, and actionlint for nine workflows.
- [x] **Wave 0 authority gate:** the user explicitly approved Mission, Status, Decision Ledger,
      Architecture, Build Checklist, and Verification Checklist; this consolidation changes only
      those master sections.
- [ ] **Wave 1 correctness gate:** every required specialist/task/validation/verifier/effect
      failure is terminally non-successful; no alternate production mutation path remains.
- [ ] **Wave 2 recovery gate:** checkpoint kill/resume, duplicate delivery, state outage, matrix
      isolation, missed-window recovery, and dead-man alert scenarios pass.
- [ ] **Wave 3 truth gate:** fact provenance/conflict/ownership, false package coordinate,
      protected-content loss, isolated example execution, and prompt-injection scenarios pass.
- [ ] **Wave 4 presentation gate:** golden set covers real and heterogeneous/malformed/
      multi-root/prompt-injected/strong-content cases; deterministic validators score 100% and
      agentic plan selection scores ≥95% across three sessions.
- [ ] **Wave 5 proposal gate:** create, unchanged retry, changed-candidate update, drift,
      duplicate delivery, lost response, authorization expiry, and every crash boundary reconcile
      to one correct draft proposal without pre-effect write-token exposure.
- [ ] **Wave 6 pilot gate:** all three Java repositories pass baseline, facts, surface plan,
      verified draft PR, no-op, targeted change, overwrite, resume, deduplication, controlled
      failure, complete evidence, and independent acceptance.
- [ ] **Wave 7 Level-6 gate:** scheduled/event-triggered restartable operation creates proposals
      without routine human initiation and keeps every block visible.
- [ ] **Wave 7 Level-7 gate:** all active registry repositories have terminal evidence, at least
      one lifecycle per supported ecosystem is proven, operations/alerts/recovery are live, and
      the 30-day clean-production window completes.
- [ ] **Wave 8 Level-8 gate:** the 90-day window satisfies every decision #76 metric and an
      independent auditor reproduces the evidence and awards Level 8.
- [ ] **Business measurement gate:** weekly github.com referral reporting is operational and
      reported beside quality/factuality measures; traffic never overrides trust gates.
<!-- END:VERIFICATION-CHECKLIST -->
