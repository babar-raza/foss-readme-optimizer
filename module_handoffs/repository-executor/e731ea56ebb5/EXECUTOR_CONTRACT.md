# Executor contract — `repository_worker_pool.py`

Module: `src/readme_agent/supervisor/portfolio_proof_engine/repository_worker_pool.py`.
Self-contained: zero imports from any other `readme_agent` module (stdlib + pydantic only),
verified by `test_module_imports_no_mission_state_apis` (parses the module's own AST and asserts no
import root is `readme_agent`).

## Typed V1 models

All frozen pydantic `BaseModel` (`ConfigDict(extra="forbid", frozen=True)`), `schema_version:
Literal[1] = 1`, matching the house convention in `portfolio_proof_engine/contracts.py`.

### `ResourceRequirementV1`
| field | type | notes |
|---|---|---|
| `resource_classes` | `tuple[str, ...]` | Empty = no gated resource. `"provider"` is always recognized via the pool's own `provider_concurrency` knob; any other name is gated only if the caller supplies a limit via `extra_resource_limits`. |

### `RepositoryJobSpecV1`
| field | type | notes |
|---|---|---|
| `job_id` | `str` (min length 1) | Coordinator-stable identity. Must be unique within a batch. |
| `input_ordinal` | `int` (`>=0`) | Position in the coordinator's ordered list. |
| `org_repo` | `str` | Validated `"org/repo"` shape. |
| `source_revision` | `str \| None` | Optional git-revision-shaped hex string. |
| `action` | `str` (min length 1) | Opaque coordinator-issued stage/action label -- this module never interprets it. |
| `argv` | `tuple[str, ...]` (min length 1) | The literal, process-isolated child invocation. Never run through a shell. |
| `work_dir` / `output_dir` / `evidence_dir` | `Path` | Unique per job; validated for cross-job collisions before any subprocess starts. `work_dir` is the child's `cwd`; the pool creates all three directories (`mkdir(parents=True, exist_ok=True)`) immediately before spawning that job. |
| `environment` | `dict[str, str]` | **The complete child environment.** Deny-by-default -- never merged with the parent process's `os.environ`. The coordinator must include anything the child needs (`PATH`, tokens, etc.) explicitly. Verified live: a bare `sys.executable` child with `env={}` starts and runs correctly (tested on this Windows machine before relying on this design). |
| `deadline_seconds` | `float \| None` (`>0`) | This job's own wall-clock cap. `None` = no per-job cap (only the batch deadline and running-forever risk apply). |
| `resource` | `ResourceRequirementV1` | See above. |
| `expected_receipt_path` | `Path \| None` | If set, a zero exit code alone is not success unless this file exists when the child finishes. |

Method `contract_hash() -> str` = `canonical_sha256(self.model_dump(mode="json"))` -- identical
specs (even distinct Python objects with identical field values) always hash identically
(`test_identical_job_specs_produce_identical_contract_hash`).

### `CancellationOutcomeV1`
`requested`, `reason: Literal["NONE","JOB_DEADLINE_EXCEEDED"]`, `graceful_signal_sent_at`,
`forced_kill_sent_at`, `process_confirmed_terminated`.

### `WorkerResultV1`
| field | notes |
|---|---|
| `job_id`, `input_ordinal`, `org_repo`, `contract_hash` | Echoed from the job. |
| `exit_classification` | `SUCCEEDED \| CHILD_NONZERO_EXIT \| MISSING_EXPECTED_RECEIPT \| TIMED_OUT \| SPAWN_FAILED \| REJECTED_DUPLICATE \| NOT_STARTED_DEADLINE_EXPIRED` |
| `succeeded` | `True` iff `exit_classification == "SUCCEEDED"`. |
| `return_code`, `started_at`, `ended_at`, `duration_seconds` | Standard bookkeeping; `started_at`/`return_code` are `None` for jobs that never actually started. |
| `provider_slot_requested` / `provider_slot_acquired` / `provider_wait_seconds` | Literal task-required "provider-slot accounting," derived from whether `"provider"` is in `resource_classes`. |
| `resource_wait_seconds` | `dict[str, float]` -- wait time per acquired resource class generally, so a caller can observe whether a compensating-control resource class (e.g. `jdk_toolchain_provisioning` at concurrency 1) is creating a real backlog. |
| `output_dir`, `evidence_dir`, `expected_receipt_path`, `receipt_observed` | Echoed + the actual observed filesystem check. |
| `stdout_excerpt` / `stdout_sha256` / `stdout_byte_count` (and `stderr_*`) | Excerpt bounded to `max_capture_bytes` (default 65536); the sha256 is over the **entire** stream regardless of truncation. |
| `environment_names` | Names only (never values) of `job.environment` entries, with secret-shaped names (`TOKEN`/`SECRET`/`PASSWORD`/`PASSWD`/`PRIVATE_KEY`/`API_KEY`/`CREDENTIAL`, case-insensitive) filtered out. |
| `cancellation` | A `CancellationOutcomeV1`. |
| `failure_reason` | Human-readable, only set for non-success outcomes that don't already carry enough context via `exit_classification` alone. |

### `BatchReportV1`
`batch_contract_hash` (hash of the ordered list of per-job `contract_hash()`es),
`repository_concurrency_limit`, `provider_concurrency_limit`,
`observed_max_repository_concurrency`, `observed_max_provider_concurrency`,
`observed_max_resource_concurrency: dict[str, int]` (per named class, including `"provider"`),
`batch_deadline_seconds`, `batch_deadline_expired`, `results: tuple[WorkerResultV1, ...]` **always in
input order, never completion order**, `rejected_duplicate_job_ids`/`rejected_duplicate_output_roots`
(non-empty only when the whole batch was rejected pre-execution), `started_at`/`ended_at`,
`total_duration_seconds`.

## `RepositoryWorkerPool`

```python
RepositoryWorkerPool(
    *,
    repository_concurrency: int = 2,       # DEFAULT_REPOSITORY_CONCURRENCY
    provider_concurrency: int = 2,         # DEFAULT_PROVIDER_CONCURRENCY
    extra_resource_limits: Mapping[str, int] | None = None,
    max_capture_bytes: int = 65536,
    grace_period_seconds: float = 10.0,
)
```

Raises `ValueError` if any concurrency value (repository, provider, or any entry in
`extra_resource_limits`) is `< 1`. A third-or-higher repository worker, or any named resource
concurrency above what a caller configures, is reachable **only** by explicitly passing a higher
value -- nothing in the pool auto-escalates.

```python
pool.run(
    jobs: Sequence[RepositoryJobSpecV1],
    *,
    batch_deadline_seconds: float | None = None,
) -> BatchReportV1
```

Behavior, in order:
1. **Pre-execution validation.** Duplicate `job_id`s and any path (`work_dir`/`output_dir`/
   `evidence_dir`, resolved) claimed by more than one job are detected before anything is spawned.
   If either is found, the **entire batch** is rejected -- every job's result is
   `REJECTED_DUPLICATE`, zero subprocesses are ever started for any job in that call.
2. **Bounded dispatch.** A `ThreadPoolExecutor(max_workers=repository_concurrency)` manages child
   processes -- threads only block on subprocess I/O/wait, never touch global interpreter state
   themselves. Each job additionally acquires every resource-class gate it declares
   (`resource.resource_classes`), always in one fixed sorted-name order (not declaration order) to
   prevent circular-wait deadlock between two jobs needing the same two classes, and releases them
   in reverse.
3. **Deadline semantics.** The batch deadline is checked twice: once as a cheap pre-submission fast
   path, and authoritatively inside the worker right after it actually acquires a
   repository-concurrency slot (the true moment a job "starts" -- a submission-time-only check
   would let an already-queued job run long after the deadline passed, since submission to a
   bounded thread pool is instantaneous regardless of how long earlier jobs take). Once expired, no
   further job acquires that slot for real work -- it gets `NOT_STARTED_DEADLINE_EXPIRED`
   immediately, gate released, no subprocess. Already-running jobs are bounded only by their own
   `deadline_seconds`, never retroactively cut off by the batch deadline.
4. **Termination.** On a job's own deadline expiring, a graceful signal is sent first (POSIX
   `SIGTERM` to the process group; Windows `CTRL_BREAK_EVENT`, valid because the child is created
   with `CREATE_NEW_PROCESS_GROUP`), then, if the child hasn't exited within `grace_period_seconds`,
   a forced kill (POSIX `SIGKILL` to the process group; Windows `taskkill /PID <pid> /T /F`) --
   mirroring but not importing `gitsafety/process.py`'s flags (that file's own forced-kill helper is
   `_`-private).
5. **Ordering.** Futures are collected in submission order; `entry.result()` is called on each in
   that same order regardless of which finished first -- blocking on an earlier slow job's future
   never blocks a later job's own execution on another pool thread, only the order results are
   assembled in.
6. **No retries, ever.** `.run()` executes each given job exactly once. There is no code path that
   resubmits a job; this is an absence of logic that a future change must not accidentally add.
