# Integration guide (for Codex)

This module is a subordinate executor only. It was built and proven in an isolated lane and has
never been imported or called from any existing file. Everything below is Codex's decision to make,
not something already wired in.

## Call boundary

- Codex's existing scheduling logic (`portfolio_scheduler/`, `stage_classifier.py`,
  `registry_cohort.py`, and whatever drives `commands_supervision.py`'s per-repository dispatch
  today) already decides, for each repository, whether it's eligible, what stage/action comes next,
  and whether a repair is warranted. Nothing changes there.
- Where that logic currently builds one `argparse.Namespace` per repository and calls
  `cmd_supervise(repository_args)` in a serial `for` loop (`commands_supervision.py:747-978`), Codex
  can instead build one `RepositoryJobSpecV1` per repository for the current dispatch cycle --
  `argv` would be the equivalent of invoking the CLI out-of-process (e.g.
  `[sys.executable, "-m", "readme_agent.cli", "supervise", "--repo", org_repo, ...]`, or whatever
  the real subprocess-invocable entry point turns out to be -- this module does not know or care) --
  and call `RepositoryWorkerPool(repository_concurrency=2).run(jobs)` once per cycle instead of the
  serial loop.
- Receipts/results flow back through the **existing single reducer** exactly as today: each
  `WorkerResultV1` is evidence a human or Codex reads and folds through
  `stage_classifier.classify_repository_stage` / `portfolio_scheduler/reducer.py`, the same as a
  serial `cmd_supervise` call's exit code and durable-state side effects are folded today. This
  module never writes lifecycle state, never calls the reducer, and never decides what a result
  means for the mission graph -- it only reports what happened to each process it launched.
- Workers never mutate the graph/state directly: the pool's only filesystem writes are `mkdir`s for
  each job's own `work_dir`/`output_dir`/`evidence_dir` (paths Codex assigns, disjoint by
  construction) and reading (never writing) `expected_receipt_path` to check it exists. All actual
  state mutation happens inside the child process Codex's own argv points at, using the exact same
  code path (`supervise_repo()`, `StateBackend`) that already runs today -- this module changes
  *how many of those run at once and in what OS process*, not *what they do*.

## Required preconditions before `repository_concurrency > 1` against real repository jobs

1. **Every pool-dispatched job's argv must include `--no-registry-heal`.** That flag already exists
   and is already wired (`commands_supervision.py:257-264`, `args.no_registry_heal`) -- this is a
   zero-source-change mitigation for the registry self-heal race (see
   `RESOURCE_AND_CANCELLATION_INVARIANTS.md`), not a new mechanism this module introduces. Codex
   performs registry healing exactly once, outside the pool (e.g. immediately before starting a
   concurrent batch), never inside a pool-dispatched child.
2. **Any job whose repository is on an ecosystem that triggers JDK auto-provisioning
   (`facts/java_toolchain.py::provision_jdk`) must be tagged with a dedicated resource class** (e.g.
   `resource=ResourceRequirementV1(resource_classes=("provider", "jdk_toolchain_provisioning"))`)
   **capped at concurrency 1** via `extra_resource_limits={"jdk_toolchain_provisioning": 1}`, until
   `provision_jdk()` itself is fixed (see the recommended fix shape below). This contains the blast
   radius of the unfixed race to "no speedup for concurrent Java-ecosystem jobs specifically," not
   an intermittent, unexplained toolchain-cache corruption.
3. **One bounded, live, low-N concurrency probe against the real LLM gateway is required before
   trusting any cost/latency numbers from a concurrent portfolio run.** This codebase has never
   measured gateway behavior under concurrent load (verified absence:
   `plans/investigations/capability-dispatch-production-readiness.md:242,251-253`). This is not this
   module's automated test suite -- it uses only fake local children, per the task's own constraint
   -- it's a separate, explicit, `live`-marked probe Codex runs once, matching the shape already
   proposed there (N=5 simultaneous tool-calling requests, observe latency/error-rate).
4. GitHub secondary-rate-limit headroom under `repository_concurrency=2` real clones/API calls
   should be spot-checked (`X-RateLimit-Remaining`) before scaling to 3.

## Starting at 2, raising to 3

`repository_concurrency=2`/`provider_concurrency=2` are this module's required defaults and match
`plans/master.md` decision #95's own "two disjoint repository workers" starting point. Per that
decision, a third worker is admitted only after one complete repository transaction proves isolation
and measured speedup stays >=1.5x with coordination overhead <=25% -- **against real repository
jobs**, not this module's synthetic benchmark (`BENCHMARK_RESULTS.json` measured 1.88x/2.86x with
fake sleeping children under zero contention; that proves the executor mechanism works, not that
real portfolio runs will see the same numbers). Metrics to actually check before raising to 3:
wall-clock speedup, LLM gateway error/latency rate under the probe in precondition 3, GitHub
secondary-rate-limit headroom, and whether the `jdk_toolchain_provisioning` compensating control (if
any Java repos are in the concurrent cohort) is creating a backlog large enough to erase the
speedup (`WorkerResultV1.resource_wait_seconds` reports this directly).

## Disabling / reverting to serial

Nothing existing was touched, so there is nothing to flag or revert. To go back to serial execution,
simply stop calling `RepositoryWorkerPool` and keep (or restore) the existing serial `for` loop in
`commands_supervision.py`/the mode drivers. No feature flag needed inside this module or any
existing file.

## Recommended fixes for the two out-of-scope races (for Codex to log and schedule)

These are diagnoses and concrete fix shapes, not something this lane implemented -- both files are
outside this module's writable scope, and `plans/**`/`plans/requirements.md` (where a `BACKLOG` row
would normally be logged per `GOV-014`) are also outside this lane's writable scope. Handing this off
precisely is the mechanism available here instead of silently dropping it.

- **`facts/java_toolchain.py::provision_jdk`/`_extract_archive`**: stage each download+extraction
  into a uniquely-named temp directory under `paths.toolchains_dir()`
  (`tempfile.mkdtemp(dir=cache_root, prefix="temurin-download-")`), extract there, then
  `Path(staging_dir).rename(destination_root)` -- one atomic filesystem rename, mirroring the
  already-correct pattern in `supervisor/portfolio_scheduler/lane.py::atomic_copy_file` (which
  already uses `FileLock` + a unique temp path + `os.replace`/rename in this same codebase). A
  `FileLock` keyed by JDK major version closes the remaining check-then-act window on the initial
  `destination_root.is_dir()` probe.
- **`registry/self_heal.py`/`registry/revision_store.py`**: wrap the TTL-check-through-write
  sequence in a `FileLock` keyed off `products_path` (the codebase already has this exact primitive
  in active use -- `local_poc_backend.py`'s `state-init.lock`, `portfolio_scheduler/lane.py`'s copy
  lock), and give `current_registry_revision_path()` writes the same expected-previous-value
  compare-and-swap discipline `StateBackend` already uses for `state.json`, instead of a bare
  last-write-wins `write_redacted_json`.

## Tests required after integration

- Whatever wires `RepositoryJobSpecV1.argv` to the real `supervise` CLI invocation needs its own
  test proving the exact argv shape round-trips correctly (this module never validates argv
  semantics, only that it's a non-empty tuple of non-empty strings).
- A test proving every call site that constructs pool-dispatched jobs actually includes
  `--no-registry-heal` in argv (precondition 1) -- this module cannot self-verify that, since
  checking it would require parsing argv semantics this module is deliberately blind to.
- A test proving Java-ecosystem job construction actually attaches the
  `jdk_toolchain_provisioning` resource class (precondition 2) -- same reasoning.
- The live gateway-concurrency probe itself (precondition 3), marked `@pytest.mark.live`.
- Once `repository_concurrency` is actually raised above 1 in a real profile, the existing
  `--max-provider-concurrency` CLI flag (`commands_portfolio_proof.py`) should be re-pointed at this
  pool's `provider_concurrency` instead of the current unwired print statement.
