# Independent Implementation Review

## Verdict

`PASS` for task `L8-LOCAL-HETEROGENEOUS-QUALIFICATION`.

## Reviewed boundaries

- `src/readme_agent/golden_set/scenarios.py` exercises exact planner selection, stop, no-repeat,
  malformed arguments, and seven prompt-injection/effect attempts through the real planner prompt.
- `src/readme_agent/golden_set/review_scenarios.py` exercises Java, .NET, Python, TypeScript, C++,
  Go, and Rust plus generic-template, fact-conflict, unsupported-claim, prompt-injection,
  strong-content, multi-root, source-build-only, malformed Markdown, broken-example,
  identity-leakage, and promotional-imbalance controls.
- `src/readme_agent/llm/reviewer_client.py` reuses the already live-proven forced-tool transport
  with the strict five-way independent-review schema. Malformed freeform JSON cannot become a
  verdict.
- `src/readme_agent/golden_set/qualification.py` requires at least three sessions, at least 100
  evaluations, 100% deterministic validation, at least 95% overall, and at least 95% for each
  model route.
- `src/readme_agent/golden_set/auto_disable.py` disables a regressed route only after the
  qualification volume threshold is complete; a one-session diagnostic cannot disable it.
- `plans/investigations/tools/collect_local_heterogeneous_qualification_evidence.py` writes
  redacted, resumable session records and binds one campaign to one immutable source snapshot.

## Evidence findings

1. The isolated campaign is bound to
   `d30a811cc414cc71a83f9a09cb345821a0fe14c2`; every path and hash in
   `campaign-source.json` matches that detached worktree.
2. `agentic-qualification-summary.json` records three sessions, 159 evaluations, 157 passes,
   98.74% overall, 100% planner accuracy, and 98.15% reviewer accuracy. Every acceptance flag is
   true.
3. The only two failures are conservative `REJECT_REPAIRABLE` verdicts for the fully grounded C++
   positive candidate. There are zero false accepts across generic, conflicting, unsupported,
   injected, broken-example, and identity-leakage controls.
4. `route-enforcement.json` records `evaluated: true`, `qualified: true`, and no disabled route.
5. `deterministic-heterogeneous-qualification-tests.xml` records 53 tests with zero failures or
   errors. It covers the canonical first proposal, repair/revalidation/rereview, unchanged no-op,
   seven-ecosystem supervisor path, crash-resume at every checkpoint, false package claims,
   protected command loss, source-build acquisition, multi-root profiling, and injection
   handling.
6. The third live session was interrupted before its atomic session record was written. Re-running
   the same session ID resumed from the two stored sessions and produced exactly one third record.
7. A numerically passing campaign from the mutable `main` checkout was correctly rejected after a
   source-fingerprint race. The accepted campaign was rerun from a detached worktree, closing that
   evidence-integrity boundary.
8. `official-checks.log` records `TREE CLEAN` at both boundaries, 1,653 passed and 24 live tests
   deselected, with every required static, governance, traceability, verifier, coverage, and
   workflow-syntax check passing.

## Acceptance conclusion

The planner and independent-review routes exceed the governed accuracy and volume thresholds.
Deterministic controls remain 100%, required heterogeneous and adversarial categories are covered,
route enforcement stayed enabled, interruption was safely resumable, and the accepted evidence is
bound to immutable source. No unresolved task-blocking defect remains at this gate.
