# Live pilot attempt — status: interrupted, incomplete

**This attempt did not reach the point of exercising `RepositoryWorkerPool` against a real
repository.** It was still in the calibration phase (a bare, direct CLI invocation, zero
involvement from the pool) when the user interrupted it to redirect toward this document instead.
Nothing below should be read as a completed proof of the worker pool against real repositories --
it is an honest record of what was attempted, what was learned, and exactly where it stopped, so
whoever continues this does not have to redo the calibration.

## What was planned

Real, `--execution-profile local_dry_run` (`requires_durable_state=False`, allows `local_write`,
never pushes) runs against real allow-listed repositories, all `mode: dry_run` in
`data/products.json` (so any `local_write`-capable dispatch would legitimately `BLOCKED`/
`infra_external` at `mode != "full"`, per `action_dispatch.py` -- expected, not a defect):

- A "serial baseline" pair (two repos, run one after another via the plain CLI -- today's existing
  behavior) vs. a "concurrent pool" pair (two different repos, run together through
  `RepositoryWorkerPool` for the first time) -- deliberately **different repos per arm**, not the
  same repos twice, because this system is explicitly idempotent (a second run of the same repo is
  supposed to make zero new provider calls) and reusing repos across arms would have made the
  "before" and "after" timings incomparable.
- Each arm was going to get its own `README_AGENT_RUNS_DIR` so state never leaked between arms.

Before spending real GitHub/LLM cost on all four repos, one calibration run against a fifth,
throwaway repo (`aspose-tex-foss/Aspose.TeX-FOSS-for-Python` -- not one of the four planned pilot
repos) was run first, direct CLI, no pool, to learn real timing and behavior. This is as far as the
attempt got.

## What was actually run and observed

1. **Credential liveness, confirmed real and working.** `gh auth status` confirmed a live GitHub
   token (`babar-raza`, scopes `gist, read:org, repo`). `readme-agent preflight` confirmed real
   connectivity to all 32 configured repositories (all `HTTP 200`) and a live LLM connection
   (`selected_model=qwen3-next, confirmed live`). Both were run from inside this lane, using the
   lane's own isolated venv (`C:\ra-venv-e731ea56ebb5`) and this branch's checked-out source.

2. **First calibration attempt failed on a Windows path-length artifact, unrelated to the module or
   the real pipeline.** Running with the default `README_AGENT_RUNS_DIR` (i.e. `<cwd>/runs`, and
   `<cwd>` here is the deeply nested lane path
   `runs/parallel_staging/repository-executor/<64-hex-base-sha>/repo`) produced two failures from
   the same root cause: `registry-heal: SKIPPED_ERROR` (a `.tmp` write failed with
   `No such file or directory` for a `registry-revisions/revisions/<64-hex>.json.tmp` path), and a
   real git clone failure: `fatal: '$GIT_DIR' too big` / `fatal: remote helper 'https' aborted
   session`. Both are the identical Windows `MAX_PATH` class of problem already hit once before in
   this same lane (installing the lane's own `.venv`, documented in `WORKLOG.md`) -- the lane's
   own mandated directory depth pushes derived paths (git's internal `.git` bookkeeping paths,
   `registry-revisions/revisions/<hash>.json.tmp`) over 260 characters, and `LongPathsEnabled` is
   `0` on this machine. **This is an artifact of the lane's own deeply nested path, not a defect in
   the module, the real pipeline, or `README_AGENT_RUNS_DIR`'s own semantics.**

3. **Worked around exactly like the earlier venv issue: relocated the disposable runtime state to a
   short path.** Setting `README_AGENT_RUNS_DIR=/c/ra-pilot/calibration/runs` (short, outside the
   lane's nested tree; the checked-out source and git history stayed exactly on this branch) let
   the same command proceed further: `registry-heal: NO_DRIFT` (clean, no error this time), and the
   baseline clone of `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` succeeded.

4. **The run then reached real specialist dispatch and genuinely `BLOCKED` on a separate,
   real environment gap**, fully unrelated to path length and, again, with **zero involvement from
   `RepositoryWorkerPool`** (this was the bare CLI, direct, no pool):

   ```
   aspose-tex-foss/Aspose.TeX-FOSS-for-Python: BLOCKED (specialist_failed:metadata_presentation:
   ERROR:execution_error:IsolatedExecutionError: container registry acquisition remained
   unavailable after bounded retry; category=agent_fixable) [llm_accounting=EXACT; provider_calls=1;
   cache_reuse=0]
     [0] specialist_retry: 'metadata_presentation' reported an error on its first classify attempt
         this run; retried once, still failing (same IsolatedExecutionError)
     [0] specialist_retry: 'readme_presentation' reported an error on its first classify attempt
         this run; retried once, still failing (same IsolatedExecutionError)
     [0] specialist_retry: 'visual_preparation' reported an error on its first classify attempt this
         run; retried once, still failing (same IsolatedExecutionError)
     [0] stop: deterministic specialist-failure stop before general planning
   ```

   `provider_calls=1` -- exactly one real LLM call was made before this blocked, so real API cost
   was minimal. `category=agent_fixable` (not `infra_external`) is the runtime's own classification
   -- per `AGENTS.md`'s "Blocked means classify, then fix" rule, this specific block is *not* one
   this lane is positioned to triage (it needs a working Docker/container runtime in this
   environment, which is outside a worker-pool-scoped task), but it should not be accepted as
   final without someone checking Docker/container-runtime availability in whatever environment
   runs the real proof next. This looks like the `facts/isolated_execution.py`/
   `LocalDockerCommandRunner` container-based execution boundary (referenced in `AGENTS.md`'s
   "Credential filtering is not execution isolation" section) being unable to acquire its container
   image/registry in this specific shell -- most likely Docker Desktop not running, or not
   reachable from this non-interactive shell, or a registry pull blocked by network policy. This
   was not investigated further before being interrupted.

5. **Total wall time for the (incomplete, blocked) calibration run: ~1m30s.** Not representative of
   a full run's duration (it stopped early, before any candidate authoring), but it's the only real
   timing data point collected before being interrupted.

## What this means for the worker pool itself

Nothing here is a finding about `RepositoryWorkerPool` -- the pool was never invoked in this
attempt. It is, however, directly relevant to whoever runs the next live pilot:

- **Any real proof run from a path this deeply nested must relocate `README_AGENT_RUNS_DIR`
  (and, if durable state is ever used, likely `README_AGENT_STATE_REMOTE` too) to a short path.**
  This applies regardless of whether the pool is involved -- it is a property of the lane's own
  mandated directory structure on Windows, not of anything this task built.
- **Docker/container-runtime availability must be confirmed in whatever environment runs the next
  live attempt**, or the pilot repos should be chosen/configured to avoid the specialist stages
  that need it, or the pilot should be explicitly bounded with `--max-readme-poc-stage` to a stage
  that doesn't reach specialist dispatch (e.g. `FACTS_READY`), if the goal is only to prove
  concurrent *facts-stage* dispatch through the pool rather than full candidate authoring.
- **Real GitHub and LLM connectivity from this exact lane, venv, and branch are confirmed live**,
  so a retry does not need to re-verify that.

## Honest status

Real, end-to-end proof of `RepositoryWorkerPool` against real repositories is **not done**. What
exists instead: the full synthetic proof (22/22 tests, lint/mypy clean, synthetic 1.88x/2.86x
benchmark -- see `REPORT.md`/`TEST_RESULTS.json`/`BENCHMARK_RESULTS.json`), plus this partial,
pool-free calibration that surfaced one packaging-of-environment issue (path length, worked around)
and one real, unresolved environment gap (container runtime) that blocks the specialist stages of a
full live run in this specific development environment. Neither finding required, or resulted in,
any change to `repository_worker_pool.py` itself.
