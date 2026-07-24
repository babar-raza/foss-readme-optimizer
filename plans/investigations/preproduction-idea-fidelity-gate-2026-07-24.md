# Pre-production idea-fidelity gate

Date: 2026-07-24

Source of truth assessed: `plans/idea.md` as present in the working tree on this date. This report
does not edit or normalize that user-owned candidate.

## Decision

Production GitHub App provisioning, production secrets, and production-pilot execution are
deferred. The next active gate is:

1. direct local end-to-end proof;
2. complete current-workflow proof under `act`;
3. isolated staging proof;
4. only then production authentication and production deployment.

The three pre-production layers must exercise the same canonical `supervise` runtime, typed
capabilities, product-fact reconciliation, presentation planning, verification, effect ledger,
durable lifecycle, and terminal evidence contracts. Authentication is the intended
environment-specific seam: local and staging may use an operator `GH_TOKEN`; production must use a
fresh GitHub App installation token and must reject PAT/`GH_TOKEN` fallback.

The control repository uses `main` only. No control-repository feature branch or PR is part of
this execution program. Target-repository proposals are different: they must continue to use a
non-default, agent-owned branch and a draft PR, because the safety model prohibits direct target
default-branch writes. If a target branch is not allowed, the only safe alternative is no target
write.

## Evidence-based current verdict

The system is not yet pre-production proven against the complete operating model.

- `origin/main` and local `main` both resolve to
  `f8b83a41506fb22a6884f494f1b16ffb8213076e`; its parent delivery commit is
  `a7ac3311debe3c1561711e639c59d225748d815e`.
- Docker 28.4.0 and `act` 0.2.89 are locally available.
- An operator `GH_TOKEN` is present; no production App token is present or needed for this gate.
- The Wave-2 `act` evidence has return code 0 but executes only the `plan` job. It does not run
  `supervise`, proposal preparation, lifecycle completion, or health aggregation.
- The recorded hosted workflow reached recovery and matrix planning but stopped before
  `supervise` because the GitHub App client ID was empty. That proves fail-closed behavior, not
  the operating model.
- The current production workflow invokes `github_observe` only. It contains no separate verified
  proposal/effect job, so it cannot yet demonstrate the complete draft-proposal lifecycle.
- `ProductFactsV2` and `RepositoryPresentationPlanV1` have strong local foundations, but their
  normative rows remain `PARTIAL`: full-field ingestion, complete cross-surface planning,
  protected-content coverage, archetype depth, and portfolio proof remain open.
- `VerifiedProposalV1`/`OpenProposalV2`, drift rebuilding, changed-candidate update, crash-boundary
  reconciliation, and proposal age visibility remain incomplete.
- README obligations central to `idea.md` remain open, including verified first-use examples,
  accurate capability/format breadth, purposeful links, navigation, community cross-links,
  protected commands/examples/terminology, and generic-prose detection.
- The active registry has 31 entries across Java, .NET, Python, TypeScript, C++, Go, and entries
  without a configured ecosystem. Full heterogeneous readiness is later work; the pre-production
  gate begins with the governed three-Java pilot archetypes.

## Clause-level proof matrix

| `idea.md` obligation | Local gate | `act` gate | Staging gate | Production-only remainder |
|---|---|---|---|---|
| Product-first, useful, credible README | Three pilot-specific candidates prove opening, audience, problem, capabilities, installation, example, maintenance, and restrained commercial context from facts. | Same candidates are produced and verified through the workflow entry point. | Reviewable draft proposals require no manual prose repair. | Long-run quality and overwrite-defense observation. |
| Autonomous monitoring and triggers | Normalize simulated schedule, dispatch, and repository events; persist/deduplicate them. | Exercise `workflow_dispatch`, `repository_dispatch`, and scheduled recovery paths. | Deliver event-driven reevaluation without a human selecting a capability. | Real GitHub scheduler behavior, missed-run observation, and dead-man service. |
| Persistent state, caches, idempotency | Prove same-input no-op, duplicate delivery, state outage, and all checkpoint resumes. | Use an isolated Git remote for the production Git-ref contracts. | Prove create/update/no-op/drift/lost-response reconciliation. | Production ref contention and elapsed operation. |
| Passive human oversight | Generate complete proposals/findings/handoffs without an operator selecting steps. | Workflow owns planning and execution. | Human only reviews the draft proposal and genuine fact/manual-UI blocks. | Production authorizations and operational review cadence. |
| Local Actions-compatible reproduction | Direct CLI result is the reference behavior. | Every applicable job in the current workflow reaches an honest terminal outcome; plan-only is failure. | Reuse the same commands/contracts, changing only environment boundaries. | None; this is a pre-production obligation. |
| Environment-specific authentication | Operator token is read-only unless a staging effect is explicitly authorized. | Inject local/staging auth without weakening the production marker. | Short-lived or bounded staging credential targets only disposable staging repositories. | GitHub App registration, installation, token minting, and no-PAT proof. |
| Deterministic/agentic boundary | Fixture and live-routed planning produce typed actions; deterministic validators remain final authority. | The workflow reaches the same planner/verifier wiring. | Agentic plan is independently accepted or rejected before any effect. | Golden-set monitoring over production routes. |
| Repository-grounded truth | Reconcile code, manifests, examples, tests, docs, license, history, releases, and registry evidence; false Cells Maven claim is blocked. | Facts and conflicts are present in terminal workflow evidence. | Unsupported claims cannot reach a draft proposal. | External owner-resolution operations and portfolio freshness. |
| Full surface ownership | Emit README, metadata, community, visual/manual-UI, package/release, and GitHub-generated decisions even when audit-only/blocked. | Preserve those outcomes in manifests. | Apply only repository-file draft proposals; settings remain separately authorized and social preview remains a truthful handoff. | Authorized settings apply and real manual-UI completion evidence. |
| Product-specific, non-template output | Compare the three pilot outputs and reject cloned structure/prose. | Workflow determinism does not collapse repositories to one template. | Independent reviewer accepts each proposal without prose repair. | Heterogeneous portfolio and long-run regression monitoring. |

## Exact execution sequence

### Gate A — direct local

1. Freeze production provisioning and preserve the existing production fail-closed boundary.
2. Build a versioned pre-production scenario inventory from the three Java pilots:
   strong/no-op, false-package-claim/complex, and partial-gap.
3. Capture immutable upstream revisions and provenance-complete facts.
4. Run the canonical supervisor through all applicable specialists and structured presentation
   planning.
5. Produce bounded README/metadata/community/visual-handoff/package-release/generated-surface
   outcomes with ownership and stop conditions.
6. Verify factuality, protected-content preservation, permissions, change boundaries, and terminal
   evidence independently.
7. Re-run unchanged, then inject upstream change, maintainer overwrite, prompt injection, state
   outage, duplicate trigger, and every lifecycle interruption.
8. Close Gate A only when all results are honest (`verified`, `blocked`, `unsupported`, or
   `no_change` as appropriate), manifests are checksum-complete, and no production remote is
   touched.

### Gate B — complete current workflow under `act`

1. Introduce one explicit staging/local authentication provider behind the existing GitHub access
   boundary; do not add a production PAT fallback.
2. Provide an isolated bare Git remote for durable state and disposable target fixtures.
3. Run the current workflow definition, or a reusable workflow implementation shared byte-for-byte
   by production and staging, through recovery, matrix planning, analysis/resume, evidence upload,
   and health.
4. Exercise `workflow_dispatch`, `repository_dispatch` with delivery identity, duplicate delivery,
   and scheduled recovery.
5. Prove one repository failure does not cancel the remaining matrix.
6. Reject the gate if `act` skips `supervise`, replaces it with a fixture-only controller, or runs
   only the matrix job.

### Gate C — isolated staging

1. Use disposable staging repositories that contain the three pilot archetypes and cannot affect
   Aspose production repositories.
2. Use a bounded operator/staging token; store it only in the staging secret boundary.
3. Run the same workflow/runtime contracts used in Gate B.
4. Prove draft proposal create, unchanged retry, changed-candidate update, target drift rebuild,
   duplicate delivery, lost response, expired authorization, and crash recovery.
5. Verify the staging target default branch is byte-identical before and after every proposal
   effect; only the agent proposal branch and draft PR may change.
6. Perform independent review and record whether each proposal requires manual prose repair.

### Gate D — production later

Only after Gates A-C pass:

1. register/install the production GitHub App and configure production-only secrets;
2. prove the read-token analysis job and separately authorized write-token effect job;
3. configure external dead-man monitoring;
4. run the controlled three-repository production pilot;
5. expand to the heterogeneous portfolio;
6. accumulate the 30-day Level-7 and 90-day Level-8 evidence windows.

## Human and Codex responsibilities

Codex owns all work through Gate B: implementation, fixtures, fault injection, `act` runs,
evidence, checksums, blocker logging, and independent-verification handoff. Codex must not ask for
production App work during those gates.

The human has no immediate production setup task. Before Gate C, the human supplies or approves:

- the exact disposable staging repositories;
- a staging-scoped token with the minimum permissions needed for draft PR proof; and
- the reviewer/acceptance authority for the staging proposal.

The human later supplies GitHub App registration/installation, production secrets, production
authorization records, dead-man endpoint, analytics, and elapsed-period reviewer only after the
pre-production gate passes.

## Blockers to log, not hide

1. Full current-workflow `act` execution has not happened.
2. There is no staging execution profile/authentication seam yet.
3. The workflow has no verified-proposal/effect job.
4. Complete three-pilot, idea-level README quality is not yet proven.
5. Complete `VerifiedProposalV1`/`OpenProposalV2` reconciliation is not built.
6. Several core README and cross-surface requirements remain planned or partial.
7. A real GitHub staging draft PR will eventually require disposable staging repositories and a
   staging-scoped credential; it does not require the production GitHub App.

These are pre-production engineering tasks. None is a reason to begin production credential
provisioning early.
