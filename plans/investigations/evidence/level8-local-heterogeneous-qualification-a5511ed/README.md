# Local Heterogeneous Qualification Evidence

Status: **ACCEPTED** for task `L8-LOCAL-HETEROGENEOUS-QUALIFICATION`.

The accepted live campaign is bound to qualification source commit
`a5511ed0bd84994e6bfb13fce9ba6ddb2ecea87a`. `campaign-source.json` records SHA-256 hashes for
the exact prompts, planner and reviewer corpora, harnesses, qualification logic, and forced-tool
reviewer client used by all three sessions. Later documentation and evidence commits did not
change any of those hashed inputs.

## Acceptance result

- Three distinct live sessions: `initial-discrimination`, `stability-repetition`, and
  `independent-reproduction`.
- 159/159 governed agentic evaluations passed.
- Supervisor planner route: 51/51 (100%).
- Independent README-review route: 108/108 (100%).
- Java, .NET, Python, TypeScript, C++, Go, and Rust are represented.
- Required generic-template, identity-leakage, unsupported-claim, broken-example,
  promotional-imbalance, prompt-injection, multi-root, source-build-only, malformed-Markdown,
  strong-content, and conflicting-fact controls are represented.
- Every volume, deterministic-validation, overall-rate, and per-route acceptance flag is true.
- `route-enforcement.json` records no disabled route.
- The focused deterministic proof records 115/115 passing tests.
- The broader safety and regression proof records 281/281 passing tests.
- The evidence secret-pattern scan was clean and `sha256sums.txt` inventories the complete
  promoted bundle.

## Recovery and idempotency

The first attempt to start the third session was correctly rejected after a documentation-only
commit changed `HEAD`. Investigation showed that every hashed qualification input remained
identical. Commit `d8020ad` narrowed campaign continuity to those actual source hashes while still
requiring a clean tree and failing closed on any prompt, corpus, harness, or reviewer change.
Re-running the same session ID produced exactly one third session record. The inter-process
`filelock` gate also rejected duplicate concurrent writers.

Representative first-run, repair, unchanged no-op, checkpoint-resume, false-coordinate,
protected-content, source-build, multi-root, prompt-injection, push-blocking, and secret-redaction
controls are included in the deterministic JUnit evidence or in the prerequisite evidence
referenced by `agentic-qualification-summary.json`.

## Scope boundary

This closes heterogeneous route qualification only. It does not claim full-registry Gate A,
human Gate B acceptance, `act`, staging, product-repository publication, hosted operation, or
Level 5/7/8 maturity.

The earlier
`plans/investigations/evidence/level8-local-heterogeneous-qualification-d30a811/` campaign is
superseded: its review harness exposed scenario IDs in reviewer context, weakening its otherwise
numerically passing result. This bundle removes that label leakage and is the authoritative proof.

