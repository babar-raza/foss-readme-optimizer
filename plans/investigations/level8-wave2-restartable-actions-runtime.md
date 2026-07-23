# Level-8 Wave 2 — Restartable GitHub Actions runtime

Date: 2026-07-23
Status: local repairs complete; refreshed independent acceptance pending; production acceptance blocked

## Scope and truth boundary

This investigation implements and audits the active Wave-2 task
`L8-WAVE2-RESTARTABLE-ACTIONS-RUNTIME`. It does not claim Wave-2 closure from unit tests or static
workflow inspection. The acceptance evidence is in
`plans/investigations/evidence/level8-wave2-restartable-actions-2026-07-23/`; its
`sha256sums.txt` covers every file in the bundle.

The working tree already contained valuable Level-8 candidate work. The implementation preserved
the user's unrelated `AGENTS.md`, `plans/idea.md`, `plans/changelog.md`, `plans/roadmap.md`, and
`plans/status.md` changes and never staged or rewrote them.

## Root causes repaired

1. Trigger records, execution profiles, state, and evidence existed as adjacent mechanisms rather
   than one restartable lifecycle. `TriggerEnvelopeV2`, `TriggerLifecycleV2`, `CheckpointV1`, and
   `RunStateV2` now form one versioned contract with explicit V1 migration and fail-closed rejection
   of unknown newer schemas.
2. GitHub profiles could swallow state failures inside the supervisor after a successful intake.
   Strict profiles now propagate state read/write/CAS failures before LLM work or effects and
   require terminal evidence.
3. Duplicate suppression treated unfinished work too much like completed work. Accepted,
   processing, and retryable duplicates now resume; only terminal duplicates suppress.
4. The first recovery implementation marked stale work retryable but did not execute the original
   durable trigger. The production workflow now emits a recovery matrix and calls
   `supervise --resume-trigger-key`, which reloads the original envelope and dedup key.
5. Replayed checkpoints compared fresh timestamps and could falsely report an identity collision.
   Idempotency now compares semantic checkpoint fields and returns the persisted checkpoint;
   changed outputs still fail closed.
6. External retries were duplicated and inconsistent. One Tenacity-backed policy registry now
   drives GitHub reads, LLM calls, all state CAS loops, clone operations, package registries, and
   GitHub writes. GitHub rate-limit headers are honored, while an unmarked permission/auth 403 is
   treated as permanent and is not replayed.
7. The requirement extractor silently omitted IDs containing digits (`L8-*`) and rejected the
   governed `BACKLOG` status. The producer was fixed, the inventory/task graph/coverage evidence
   regenerated, and the consumer assertions updated to the true 390-row/366-mandatory totals.
8. The active taskcard's allowed paths omitted its own dependency declaration, requirement
   reconciliation, governed evidence tooling, and log updates. The same authoritative task graph
   was widened only to the paths actually required by this Wave-2 task; no competing task or plan
   was created.
9. Independent review found the lifecycle could become `completed` before Manifest V3 finalization
   and checksum validation. Final acceptance is now checkpointed first, evidence is finalized and
   validated second, and durable terminal state is written last. An injected evidence failure
   leaves the trigger `retryable`.
10. Health could report green while retryable backlog existed. Backlog now carries age,
    actionability, and reason; retryable or SLA-aged work makes `HealthReportV1` unhealthy, while
    recent bounded in-flight work stays visible without a false incident.
11. The refreshed full suite rejected stale requirement-task coverage after the requirement truth
    correction, then the historical coverage classifier crashed on governed `PARTIAL`/`BACKLOG`
    statuses. Both producers now cover the extractor's complete status vocabulary, expose
    non-mutating `--check` modes, regenerate all dependent outputs, and have an enforced
    producer-consumer status-contract test.
12. The first real hosted run exposed `actions/create-github-app-token@v3`'s deprecated `app-id`
    input. The workflow now uses the action's current `client-id` contract and the prerequisite
    variable is `GH_APP_CLIENT_ID`; a static regression rejects the legacy input.

## Delivered runtime

- One scheduled/reusable workflow accepts schedule, `workflow_dispatch`, `workflow_call`, and
  `repository_dispatch`.
- The planning job emits the authoritative active-registry matrix, including observe-only entries.
- Repository jobs use `fail-fast: false`, conservative parallelism, GitHub `queue: max`, and the
  existing durable CAS/run leases.
- Eleven named lifecycle checkpoints are persisted at their real producers.
- Every scheduled pass recovers expired accepted/processing/retryable records and resumes each
  original trigger in a separately serialized repository job. Resume restarts canonical
  supervision and relies on idempotent checkpoints/effect reconciliation; it does not use the
  checkpoint as a stage-skipping instruction pointer.
- Analysis and recovery receive freshly minted repository-scoped contents-read GitHub App tokens.
  Production token resolution refuses ambient PAT/`GH_TOKEN` fallback.
- `HealthReportV1` exposes missed windows, backlog, stale leases, repeated failures, open proposals,
  last success, and state failures; the workflow uploads it, creates/updates an issue, fails a
  check, and supports an external dead-man heartbeat.
- `RunManifestV3` binds trigger, terminal state, checkpoints, facts, presentation plan,
  authorization status, verifier output, effects, and requirement results, with atomic writes and
  checksum validation.

## Verification

The bundle records:

- Ruff, format, mypy, actionlint, and plan validation;
- named lifecycle/fault, retry, workflow, CLI, evidence, and health tests;
- one checksum-addressed recovery record for each of the eleven injected checkpoint boundaries;
- negative proof that failed terminal evidence leaves lifecycle state retryable, never completed;
- health-policy proof distinguishing actionable backlog from bounded in-flight work;
- the complete non-live test suite;
- an `act` reproduction of the real recovery and authoritative-matrix path;
- the exact parser-only compatibility transformation needed because local `act` 0.2.89 predates
  GitHub's `concurrency.queue: max` syntax;
- source, workflow, requirements, mission-graph, and repository-state hashes;
- local and remote prerequisite presence checks containing names/presence only, never secret
  values.

The `act` transformation removes only the same parser-unsupported line (`queue: max`) from the two
per-repository concurrency sections in a temporary copy. The production workflow itself remains
unchanged and is separately accepted by actionlint with one documented schema-version suppression.

The eleven local checkpoint records prove persistence, recovery eligibility, same-trigger restart,
and eventual completion after each boundary. They deliberately do not claim stage-directed
continuation or prove that every earlier producer is skipped; current recovery re-enters canonical
supervision and depends on its existing idempotency and effect-reconciliation gates. Producer-level
hosted interruption and repetition evidence remains an open production acceptance item.

## Remaining production acceptance

Wave 2 remains `PARTIAL` until all of the following external proofs exist:

1. Register and install a GitHub App over the governed target repositories.
2. Configure `GH_APP_CLIENT_ID`, `GH_APP_PRIVATE_KEY`, `LLM_BASE_URL`, `LLM_API_KEY`, and an external
   `DEAD_MAN_HEARTBEAT_URL` in the control repository.
3. Authorize publication of the committed production workflow to
   `babar-raza/foss-readme-optimizer`, then run the four trigger types on GitHub-hosted runners.
4. Inject a hosted-runner interruption/state outage and prove recovery in the next sweep.
5. Configure the external monitor and prove both heartbeat receipt and scheduler-absence alerting.
6. Provide fresh approval to edit `plans/master.md` Status, Build Checklist, and Verification
   Checklist after the independent audit accepts the evidence.

PAT substitution is not a valid workaround: it would violate `L8-001` and the approved Level-8
architecture. Local `act` cannot prove GitHub App installation permissions, a hosted scheduler
absence, or an external monitor.
