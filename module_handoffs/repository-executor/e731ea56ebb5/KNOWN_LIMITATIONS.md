# Known limitations and honest tradeoffs

- **The `--no-registry-heal`/resource-class mitigations depend on Codex tagging jobs correctly at
  the integration layer.** This module cannot self-verify "this job is a Java repo" or "this argv
  omits the heal flag" without importing ecosystem/registry logic, which is explicitly forbidden by
  its own charter (no mission-state access). The multi-resource-class and environment-isolation
  tests prove the *mechanism* works; they cannot prove Codex's future call sites use it correctly --
  that is an integration-time review item, not something a unit test inside this lane can close.
- **`--no-registry-heal` sidesteps the TTL race for pool-dispatched jobs; it does not fix the
  underlying lost-update bug** in `self_heal.py`/`revision_store.py`. Any other caller that invokes
  `supervise` concurrently without that flag (e.g. a human running two terminals) is still exposed.
  This is a policy workaround scoped to this module's own integration, not a source fix -- see
  `INTEGRATION.md`'s recommended fix shape for the real one.
- **The `StateBackend`'s CAS mechanism was verified by reading code, not by an empirical concurrent
  race.** The fetch/push/CAS-detection logic and the callers' fail-closed handling of a lost race
  were read directly and are sound by inspection. No live two-process race against a real git
  remote was run to empirically confirm timing behavior under load; that remains a reasonable but
  unverified inference, not a proven guarantee.
- **The LLM gateway's and GitHub's real behavior under concurrent load remain genuinely unverified**
  after this investigation -- this handoff recommends the probes in `INTEGRATION.md`, it does not
  assert the answer. Decision #95's own "prove isolation, then measure >=1.5x speedup, <=25%
  overhead" gate already anticipated exactly this category of unknown.
- **Serializing JDK-toolchain-needing jobs at concurrency 1 has a real cost**: no speedup for that
  ecosystem slice of the portfolio until `facts/java_toolchain.py::provision_jdk` gets the source
  fix recommended in `INTEGRATION.md`. This is a deliberate, bounded tradeoff, not a free mitigation.
- **The benchmark numbers in `BENCHMARK_RESULTS.json` are synthetic** (fake sleeping children, zero
  real contention). They prove the executor's own scheduling mechanism delivers the expected
  concurrency multiplier; they are not evidence of real portfolio-run speedup and must not be quoted
  as such.
- **No live portfolio cohort, real repository, Docker, or GitHub API call was exercised anywhere in
  this lane**, per the task's explicit constraint. Everything above about real `supervise` behavior
  under concurrency is a static-code-reading investigation, clearly labeled where it is verified
  (state backend) versus where it is a real, currently-unfixed gap (toolchain cache, registry
  self-heal) versus where it is simply unknown (gateway/GitHub under load).
- **A single-file module is larger than this repository's usual ~300-line-per-module guidance**
  (`repository_worker_pool.py` is ~690 lines including five typed models, the concurrency gate, the
  drain/termination helpers, and the pool class). This is a direct, accepted consequence of the
  task's writable scope being restricted to exactly one module file plus its test file -- splitting
  it further was not available without violating that scope. Codex may choose to split it into
  multiple files at integration time, when the scope restriction no longer applies.
- **This module does not, and structurally cannot, verify that the coordinator's ordering/
  eligibility decisions were correct** -- it runs exactly the jobs it is given, in the concurrency
  bounds it is given, and reports what happened. Any defect in *which* jobs were decided, or *when*,
  is entirely outside what this lane could have caught, by design.
