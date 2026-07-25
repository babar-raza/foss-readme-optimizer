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

The audit baseline at adoption was `main` at
`f89da6056b13cae19e02a72aa6d5ebf3fc371ee1`, with a large valuable in-flight candidate tree. At
that point the portfolio evidence recorded candidates but zero independently approved local
repositories; the durable active task still described three Java pilots; RPOC was a separate
unregistered ledger; product-truth drafting was not consumed by rendering; the non-pilot path
could skip bundle verification; reviewer repair missed `caller_domain`; review used no durable
backend; dynamic planning was opt-in; coverage/status tooling was stale; and the tree was not
green. These are entry findings, not closure claims.

## Current execution checkpoint (2026-07-25)

The durable mission graph has rerouted the obsolete three-Java-only parent and claimed
`L8-LOCAL-PORTFOLIO-RUNTIME`. Its durable state is the task-status authority; this section is a
concise continuation aid only.

Verified in the current dirty candidate tree: the supervisor accepts the canonical
`supervise --registry data/products.json --execution-profile local_poc` form; that profile
requires durable state, evidence, local fact verification, independent verification, mandatory
dynamic planning, and excludes `remote_write`. The registry is frozen once per pass, all modes
participate, a per-repository failure is isolated, local triggers use a durable `cli_manual`
envelope, and the first immutable snapshot produces a revision-addressed, redacted,
checksum-inventoried local-POC source bundle. The in-place lifecycle migration now has V2 stages
and preserves V1 history on first transition.

This does **not** close the local-runtime task or Gate A. Product facts are not yet fully fed into
the renderer; lifecycle transitions after `SNAPSHOTTED`, complete per-repository bundles,
deterministic bundle enforcement, the real reviewer/backend path, unchanged no-op proof, and a
real full-registry run remain mandatory. Repository-wide official checks are not presently a
stable proof because the tree contains concurrent candidate work; `git diff --check` also reports
unrelated trailing whitespace in `plans/GOVERNANCE.md:107`.

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
6. Obtain the required fresh approval before editing `master.md` Mission, Status, Decision Ledger,
   Architecture, Build Checklist, and Verification Checklist. Revise decision #78 in place.
7. Synchronize idea, requirements, governance, roadmap, status generator, root README, AGENTS,
   logs, and master under the approved authority change.
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

### Phase 3 -- immutable repository truth

1. Capture real default branch, revision, README or explicit absence, inventory, package roots,
   manifests, examples, tests, docs, licenses, tags, and releases.
2. Complete `ProductFactsV2` fields required by `idea.md` with provenance, confidence, owner, and
   affected sections.
3. Integrate `draft_product_truth` into the supervised flow. The verified merged fact graph must
   be consumed by assessment and rendering; policy/README/product-agent content are evidence, not
   sole truth.
4. Verify packages, source-build paths, examples, links, formats, compatibility, limitations,
   maintenance, and commercial/FOSS context in secret-free isolated jobs.
5. Prove the route first across Java, .NET, Python, TypeScript, C++, Go, and Rust representatives.

Exit: false coordinates fail; unsupported facts cannot reach candidates; every representative has
enough evidence for useful content or a precise external fact handoff.

### Phase 4 -- agentic assessment, plan, and candidate composition

1. Classify every material existing section/claim as preserve, clarify, investigate, repair,
   remove/update, replace-generic, add, or not-applicable.
2. Produce a repository-specific `ReadmeDocumentPlanV1` with source spans, expected hashes, fact
   citations, protected-content treatment, validators, rollback, and stop conditions.
3. Preserve the owned-span safety property through byte-preserving adoption. Reconstruct only
   inside the adopted span and only through evidence-backed operations.
4. Generate differentiated structure, terminology, examples, installation, format emphasis,
   navigation, limitations, support, and restrained relationship positioning.
5. Persist a complete candidate, claim map, and native Git patch.

Exit: every candidate has a nonempty plan; no universal template or unapproved content loss passes;
bundle verification is never skippable.

### Phase 5 -- deterministic validation, independent review, and repair

1. Make the deterministic proposal-bundle verifier mandatory before review.
2. Repair the reviewer call path by supplying `caller_domain` and the durable state backend.
3. Separate author/reviewer prompts, context, identity, caches, and evidence.
4. Limit verdicts to `AGENT_APPROVED`, `REJECT_REPAIRABLE`, `BLOCKED_FACT_CONFLICT`,
   `BLOCKED_MISSING_EVIDENCE`, and `SYSTEM_FAILURE`.
5. Convert repairable results to scoped repair instructions; retry automatically; route wiring and
   planner failures to `agent_fixable` resolvers.
6. Prove unchanged reruns yield no patch, lifecycle duplication, bundle duplication, or unnecessary
   LLM call.

Exit: approval always follows deterministic and independent review; controlled repairs succeed;
factual blocks cannot become generic marketing prose.

### Phase 6 -- heterogeneous qualification and governed golden set

Build fixtures and negative controls for every ecosystem, multi-root repositories, missing README,
malformed Markdown, bindings, source-build-only packages, published/unpublished packages, strong
existing content, prompt injection, stale claims, product-agent contradiction, identity leakage,
unsupported formats, false installation, protected loss, broken examples, generic templates, and
promotional imbalance.

Require 100% deterministic validation and at least 95% governed agentic routing/review accuracy over
at least 100 evaluations across three independent sessions. Automatically disable a regressed route.

### Phase 7 -- full-registry local execution and Gate A

Run the canonical profile over the runtime registry denominator in bounded ecosystem/family cohorts.
Repair agent-fixable failures at their first boundary. Requeue fact-blocked repositories after
autonomous refresh and generate exact product-agent handoffs only for unrecoverable essential facts.
Continue independent work until every registry entry has a complete approved bundle and no-op proof.

Gate A requires:

```text
approved == len(data/products.json)
system_failed == 0
unprocessed == 0
manifest_failures == 0
```

This is the locally proven full-registry README POC, not Level 5, 7, or 8.

### Phase 8 -- Gate B human-review package

Generate one indexed package with every source README, candidate, patch, facts, plan, validation,
review, limitation, and reproduction command. Human review starts only here. A human rejection
returns to autonomous repair, deterministic validation, and independent review.

### Phase 9 -- actual workflow under act

Run the same supervisor/profile under the reusable workflow using isolated local remotes. Exercise
workflow dispatch, repository dispatch, workflow call, simulated schedule recovery, matrix isolation,
deduplication, checkpoint resume, evidence upload, and health aggregation. Prove production profiles
reject PAT/GH-token fallback. Docker is needed only at this gate.

### Phase 10 -- disposable GitHub staging

Complete the staging subsets of `VerifiedProposalV1` and `OpenProposalV2`, then prove draft PR
create/no-op/update/drift/dedup/lost-response/expired-authorization/crash reconciliation with
staging-scoped credentials. Default branches remain byte-identical and analysis never receives a
write token.

### Phase 11 -- Gate C Java README PR publication proof

Use the already accepted Java candidates; do not regenerate README intelligence here. Before every
product push, present the exact diff, reason, repository, branch, and remote and obtain fresh
approval. Create or update draft PRs only. Never merge, mark ready, force-push, close, or write a
default branch. Gate C proves publication, not the README POC or Level 5.

### Phase 12 -- Gate D GitHub App and hosted runtime

Only after Gate C request the App registration, installation, permissions, repository scope, and
secrets. Validate short-lived effect-job tokens, analysis/effect isolation, deployment, trigger
recovery, leases, retry classes, health, alerts, backlog, dead-man monitoring, and manifests.

### Phase 13 -- broader presentation and Level 5

Implement and verify metadata, community files, license/contribution/security, visuals, truthful
manual social-preview handoff, package/release audit findings, generated-signal observations, and
cross-surface consistency. Then execute the controlled three-Java production pilot and obtain the
independent Level-5 award.

### Phase 14 -- Levels 6 and 7

Operate every registry repository in observe/proposal mode, prove one complete authorized lifecycle
per supported ecosystem, roll out remaining families, and maintain recovery, health, drift, proposal
age, authorization-expiry, dependency, SBOM, vulnerability, and quality reporting. Accumulate 30
clean production days for Level 7.

### Phase 15 -- Level 8

Operate for 90 consecutive production days with weekly full-registry audits, incremental
reevaluation, onboarding proposals, automatic route regression disablement, state migration and
outage recovery proof, stale-proposal reconciliation, external dead-man monitoring, and weekly
quality/referral reporting. Require every Level-8 metric in the authoritative plan and an independent
reproducibility audit.

## Verification, evidence, and human boundaries

Every task needs focused tests, integration tests through public seams, safety/regression tests,
live-like proof appropriate to the claim, failure/recovery/idempotency/evidence-corruption controls,
an independent verifier, a SHA-256 inventory, and reproduction instructions.

The official control-repository gate runs Ruff, format check, mypy, non-live pytest, plan validation,
blocking coverage, blocking semantic traceability, blocking verifier enforcement, actionlint, and
`git diff --check` against a recorded stable tree.

Human involvement is limited to fresh approval for the specified `master.md` sections, Gate-B review
of already agent-approved candidates, Docker/staging access if unavailable locally, staging
credentials, exact per-product-push approval, GitHub App registration and secrets after Gate C,
genuinely manual UI actions, independent acceptance authority, and elapsed production time. All
other implementation, testing, remediation, evidence, commits, setup, monitoring, and continuation
is autonomous.

The mission closes only when every mandatory graph task is `CLOSED`, all requirements are
truthfully evidenced, all gates pass, the 30-day and 90-day periods complete, the independent audit
awards Level 8, and reevaluation finds no mandatory ready, reopened, regressed, or agent-fixable
blocked work.
