# Resource and cancellation invariants

## Why subprocess isolation, not threads, for the actual repository work

Verified by reading the real code, not assumed:

- `os.environ` is process-wide and read live by `env.py`/`authorization/registry.py` with no
  per-call override -- two concurrent threads in one process can never have different
  `LLM_BASE_URL`/`README_AGENT_PRODUCTION_AUTH`/etc. simultaneously; two OS processes can (each gets
  its own `env=` mapping).
- `paths.baseline_dir()`/`work_dir()` are persistent clones, force-`rmtree`'d and recreated in place
  by `gitsafety/clone.py`, with **no filesystem lock at that layer**. `gitsafety/clone.py`'s own
  `_baseline_clone_memo` module-global dict docstring already states "a new process starts with an
  empty memo" -- i.e. the existing code's own safety reasoning already assumes fresh-process-per-run
  and has never been audited for thread-safety.
- The LLM call-ledger (`llm/call_ledger.py`) is safe today only because each run gets its own file
  path (`{org_repo}/{run_id}.jsonl`), serialized by an in-process `threading.Lock` that would do
  nothing to coordinate two separate OS processes -- it doesn't need to, because two processes each
  owning a distinct `(org_repo, run_id)` never target the same path.

Subprocess isolation matches every one of these existing assumptions exactly, rather than requiring
a new thread-safety audit of each site.

## Verified concurrency posture of shared state outside this module's control

This module only controls the directories and environment named in each `RepositoryJobSpecV1`. Real
`supervise` children touch considerably more shared state. This was investigated directly (reading
the actual lock/cache/heal code), not assumed:

| Component | Verified posture | Evidence |
|---|---|---|
| `StateBackend` per-repo lock/save (`state/git_backend.py`) | **Safe for concurrent disjoint repos.** Per-`org_repo` git ref; real compare-and-swap via non-force `git push` + `_is_non_fast_forward` rejection detection. A losing `acquire_run_lock`/`acquire_lock` returns `None` immediately -- never blocks, never corrupts -- and both call sites (`supervisor/loop.py:860-869,1153-1168`) turn that into a typed `BLOCKED`/`infra_external` result. The one global (non-per-repo) ref, `MODEL_ROUTE_REF`, is read-only on the plain `supervise` path. | `git_backend.py:132-145,260-302` |
| JDK toolchain cache (`facts/java_toolchain.py::provision_jdk`) | **Unsafe under concurrency.** Check-then-act on `destination_root.is_dir()` (the code's own comment names "a concurrent... run" as a scenario it's aware of but doesn't fully close), no lock, no atomic staging-then-rename. Two processes provisioning the same JDK major version at the same time can extract into the same shared directory simultaneously. | `java_toolchain.py:346-381` |
| Registry self-heal (`registry/self_heal.py`, `registry/revision_store.py`) | **Unsafe under concurrency, and triggered on every `supervise` invocation before any per-repo lock.** The TTL check is read-only with no lock, so two concurrent different-repo processes can both decide to heal. `write_atomic()` itself is corruption-safe (`tempfile.mkstemp` + atomic rename), but the higher-level read-merge-write has no CAS -- a real lost-update race can silently drop one process's newly-discovered registry entries, and `current_registry_revision_path()` is a bare last-write-wins pointer with the same gap. | `self_heal.py:130-138,246-252`; `discovery.py:235-248`; `revision_store.py:18-30`; trigger site `commands_supervision.py:257-264` |
| LLM gateway under real concurrent load | **Untested -- an explicitly acknowledged gap**, not a solved problem. | `plans/investigations/capability-dispatch-production-readiness.md:242,251-253` |
| GitHub secondary rate limits under concurrent clones/API calls | **Unverified**, no evidence either way. | -- |

This is why `ResourceRequirementV1.resource_classes` is a named, extensible set rather than a single
"provider" boolean, and why the required integration preconditions in `INTEGRATION.md` exist. The
two unsafe rows above are **outside this module's writable scope** -- they were read, not edited.

## Deadlock avoidance for multi-resource-class jobs

A job may declare more than one resource class (e.g. a job tagged both `"provider"` and
`"jdk_toolchain_provisioning"`). All gates a single job needs are acquired in one fixed, global
sorted-name order (never declaration order) and released in reverse. Two jobs that each need the
same two classes, submitted in opposite declaration order, cannot deadlock via circular wait, because
both resolve to the same acquisition order regardless of how the caller wrote them. A duplicate class
name within one job's own `resource_classes` is deduplicated via `set()` before acquisition, which
also prevents a distinct, simpler self-deadlock: a `threading.Semaphore` is not reentrant, so
acquiring the same class twice in the same thread without dedup would hang forever at limit 1.
Proven by `test_multi_resource_class_jobs_do_not_deadlock` (two jobs, two shared classes each at
limit 1, asserts bounded completion) rather than only asserted in a comment.

## Cancellation invariants

- A job's own `deadline_seconds` (not the batch deadline) is what can cut off an already-running
  child.
- Termination is always two-stage: graceful signal first (POSIX `SIGTERM` to the process group via
  `os.killpg`; Windows `CTRL_BREAK_EVENT`, deliverable only because the child is spawned with
  `CREATE_NEW_PROCESS_GROUP`), a bounded `grace_period_seconds` wait, then forced kill (POSIX
  `SIGKILL` to the process group; Windows `taskkill /PID <pid> /T /F`) only if still alive.
  `CancellationOutcomeV1.process_confirmed_terminated` records whether the process was actually
  gone afterward -- proven, not assumed, by
  `test_bounded_cancellation_leaves_no_leaked_process` (writes the real child's own pid to a file
  before it sleeps, then asserts that pid no longer exists after `.run()` returns, using the same
  cross-platform existence check `tests/unit/test_bounded_process.py` already uses in this repo).
- A global batch deadline **only stops new jobs from starting** (see `EXECUTOR_CONTRACT.md`'s
  ordering section for exactly where "starting" is defined) -- it never reaches into an
  already-running job.
- One job's `SPAWN_FAILED`, `CHILD_NONZERO_EXIT`, `TIMED_OUT`, or `MISSING_EXPECTED_RECEIPT` never
  raises out of `_execute_one`/`_run_child` and never affects any other job's own gate acquisition
  or execution -- each job's outcome is fully contained in its own `WorkerResultV1`.

## No false success

A zero return code is necessary but not sufficient for `SUCCEEDED` when `expected_receipt_path` is
set: the pool checks `Path.is_file()` on that exact path after the child exits and classifies a
missing receipt as `MISSING_EXPECTED_RECEIPT`, `succeeded=False` -- proven by
`test_missing_expected_receipt_becomes_incomplete_not_success`.
