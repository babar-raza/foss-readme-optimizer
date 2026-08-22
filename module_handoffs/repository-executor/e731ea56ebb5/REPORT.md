# Repository worker pool — handoff report

Base SHA: `e731ea56ebb50c6002d7fb5459e02d8b32f0cc71` (verified: local `main` == remote `main` at
lane creation, re-checked identical at handoff time -- no drift, see `BASE_AND_DRIFT.json`).
Branch: `claude/standalone-repository-executor-e731ea56ebb5`.
Implementation commit: `aab2245e8481016da103d21f08b303996ebc1a23` (see `COMMITS.txt`).

## What this is

A process-isolated, subordinate executor
(`src/readme_agent/supervisor/portfolio_proof_engine/repository_worker_pool.py`) that runs an
already-decided, ordered list of repository jobs concurrently via real OS subprocesses, bounded by
repository- and named-resource-concurrency limits, and reports typed results back. It never decides
which repository is eligible, what stage/action runs next, whether a repair is warranted, or whether
a goal is complete. It has zero imports from any other `readme_agent` module. It was designed,
built, and proven entirely in an isolated worktree/branch and has not been wired into any existing
file.

## Why this took two design passes

The first pass treated this as a self-contained coding problem: build the executor, satisfy the
listed test bullets. On reflection, a "correct" executor that only proves its own job-level
directory disjointness gives a false sense of production safety, because the real children it
launches (`supervise` invocations) share far more mutable state than any directory this module
controls. Before finalizing the design, this lane read the actual lock/cache/heal code for that
shared state rather than assuming it was fine -- see `RESOURCE_AND_CANCELLATION_INVARIANTS.md` for
the full findings table. Two concrete design changes came directly out of that investigation:

1. **Resource gating generalized** from a single hardcoded `"provider"` boolean to named,
   caller-defined resource classes (`ResourceRequirementV1.resource_classes`), because real
   `supervise` children also touch a JDK toolchain cache and a registry self-heal path that are
   *verified unsafe under concurrency today* -- not hypothetically, confirmed by reading the actual
   check-then-act races in `facts/java_toolchain.py` and `registry/self_heal.py`.
2. **Four required integration preconditions** were added to `INTEGRATION.md`, most concretely: every
   pool-dispatched job's argv must include the already-existing `--no-registry-heal` CLI flag, and
   any JDK-provisioning-triggering job must be tagged with a dedicated resource class capped at
   concurrency 1, until the two out-of-scope races get their real source fix (fix shapes provided,
   not implemented -- both files are outside this lane's writable scope).

A second, smaller bug was also caught and fixed before it ever reached a test failure: the initial
batch-deadline design checked "has the deadline expired" only at job-submission time, which is
nearly instantaneous for an entire job list regardless of how long earlier jobs take -- meaning a
limited-concurrency pool would queue every job before the deadline could ever meaningfully block a
later one. The fix moved the authoritative check to the moment a job actually acquires its
repository-concurrency slot (see `EXECUTOR_CONTRACT.md`'s ordering section), which is the true
"about to start" moment.

## What was built

- `src/readme_agent/supervisor/portfolio_proof_engine/repository_worker_pool.py` -- the module (5
  frozen V1 models + `RepositoryWorkerPool`; full contract in `EXECUTOR_CONTRACT.md`).
- `tests/unit/test_portfolio_proof_engine_repository_worker_pool.py` -- 22 tests (all fake local
  child commands, no Qwen/Docker/GitHub/product repos), listed in `TEST_RESULTS.json`.
- `tests/fixtures/repository_worker_pool/fake_repository_job.py` -- one parametrized fake child
  script covering every test scenario (sleep, exit code, receipt writing, stdout/stderr volume,
  invocation counting, pid reporting, environment echoing).

No other file was touched. `git diff --name-status` against base shows exactly these three new
files (`CHANGED_FILES.txt`).

## Verification

```
pytest -q tests/unit/test_portfolio_proof_engine_repository_worker_pool.py           # 22 passed, 7.6s
ruff check ...                                                                        # clean
ruff format --check ...                                                              # clean
mypy src/.../repository_worker_pool.py                                               # clean
pytest -q tests/unit/test_portfolio_proof_engine_{provider_concurrency,deadline,contracts,receipt_store}.py
                                                                                       # 31 passed, 1.3s
```

Full detail (including the four platform-conditional `# type: ignore[attr-defined]` comments added
to mirror `gitsafety/process.py`'s existing pattern for the same OS-stub-resolution reason) in
`TEST_RESULTS.json`.

## Benchmark

6 synthetic jobs, 0.5s sleep each: serial baseline 3.69s, `repository_concurrency=2` (required
default) 1.97s (1.88x), `repository_concurrency=3` (explicit) 1.29s (2.86x). Both exceed decision
#95's >=1.5x speedup bar -- **on synthetic children with zero real contention**. This proves the
scheduling mechanism, not real portfolio speedup; see `BENCHMARK_RESULTS.json`'s caveat and
`INTEGRATION.md`'s required live-probe precondition before trusting real numbers.

## Maximum observed concurrency / cancellation / collision proofs

- `observed_max_repository_concurrency` reached exactly 2 at the default config and exactly 3 when
  explicitly configured, never more (`test_default_repository_concurrency_never_exceeds_two`,
  `test_explicit_repository_concurrency_of_three_is_reached`).
- `observed_max_provider_concurrency` and a named non-`"provider"` class both bounded correctly,
  including a job needing both classes at once without deadlock
  (`test_provider_tagged_concurrency_never_exceeds_provider_limit`,
  `test_named_non_provider_resource_class_is_bounded`,
  `test_multi_resource_class_jobs_do_not_deadlock`).
- Cancellation: a child given a 0.2s deadline against a 60s sleep was terminated and confirmed gone
  (via its own reported pid) within a bounded ~8s ceiling, no leaked process
  (`test_bounded_cancellation_leaves_no_leaked_process`).
- Collision: two jobs sharing an output root were both rejected before either's fixture side-effect
  file was ever created (`test_duplicate_output_roots_rejected_before_any_child_starts`).

## Root-cause findings and out-of-scope fix recommendations handed to Codex

See `RESOURCE_AND_CANCELLATION_INVARIANTS.md`'s findings table and `INTEGRATION.md`'s "Recommended
fixes" section. Summary: `state/git_backend.py`'s per-repo lock is safe for concurrent disjoint
repositories (verified by reading the CAS/fail-closed code); `facts/java_toolchain.py::provision_jdk`
and `registry/self_heal.py`/`registry/revision_store.py` both have real, currently-latent
check-then-act races that only serial execution has been masking, and both have a precise recommended
fix (uniquely-staged atomic rename + `FileLock` for the toolchain cache; `FileLock` + expected-value
CAS for the registry heal/revision pointer) that this lane could not implement because both files
are outside its writable scope. These were read, not edited. Codex should log them per `GOV-014`
(`plans/requirements.md`, out of this lane's writable scope) informed by this exact diagnosis.

## Known limitations

See `KNOWN_LIMITATIONS.md` in full; headline items: the integration preconditions depend on Codex
tagging jobs correctly (this module cannot self-verify that without importing forbidden logic), the
state-backend safety claim is inspection-based, not empirically load-tested, and the benchmark is
synthetic.

## Handoff paths

- `module_handoffs/repository-executor/e731ea56ebb5/{REPORT.md (this file), EXECUTOR_CONTRACT.md,
  RESOURCE_AND_CANCELLATION_INVARIANTS.md, INTEGRATION.md, BENCHMARK_RESULTS.json,
  TEST_RESULTS.json, KNOWN_LIMITATIONS.md, CHANGED_FILES.txt, COMMITS.txt, BASE_AND_DRIFT.json}`
- `runs/parallel_staging/repository-executor/e731ea56ebb50c6002d7fb5459e02d8b32f0cc71/WORKLOG.md` --
  the full session log, including the root-cause investigation transcript.
- `runs/parallel_staging/repository-executor/e731ea56ebb50c6002d7fb5459e02d8b32f0cc71/handoff/` --
  format-patch set, git bundle, and combined diff (created after this commit).

## Exact Codex integration commit list

None yet -- nothing has been integrated. Codex's own future commit(s) would need to: (1) construct
`RepositoryJobSpecV1` instances from its existing per-repository dispatch decisions (replacing or
wrapping the serial loop in `commands_supervision.py`/the mode drivers), including
`--no-registry-heal` in every pool-dispatched job's argv and the `jdk_toolchain_provisioning`
resource-class tag for Java-ecosystem jobs; (2) call `RepositoryWorkerPool(...).run(jobs)` and fold
`WorkerResultV1`s back through the existing single reducer; (3) optionally re-point
`--max-provider-concurrency` at this pool's `provider_concurrency`; (4) separately, on its own
schedule, apply the two recommended out-of-scope fixes (or log them as `BACKLOG` rows if deferred).

## Confirmations

No changes were made to `plans/**`, the mission/task graph, state machine, task catalog, decisions,
status, or resume capsule, `AGENTS.md`, `docs/**`, `.github/**`, CLI registration, existing execution
modes or the stage classifier, existing candidate/review/facts/validation logic, provider
clients/prompts, existing evidence, any product repository, the parent checkout, or the `main`
branch. `facts/java_toolchain.py`, `registry/self_heal.py`, and `registry/revision_store.py` were
read (to produce the findings above) but not edited. `git status`/`git diff --name-status` against
base confirm exactly the three files listed in `CHANGED_FILES.txt` were added, and nothing else was
modified.
