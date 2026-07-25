# Local Independent README Review and Repair Proof

This evidence binds task `L8-LOCAL-INDEPENDENT-REVIEW-REPAIR` to the implementation at
`ee221c7480402234acaba2e121ae7724b4560d96`, the lifecycle-evidence correction at
`907e9b41c700cf98e9cb060d0d284fe7d905418b`, and the clean-tree official-check guard at
`0411827cd615cf530072c304f81e2fb692a4c215`.

The controlled local-POC run proves:

- deterministic proposal-bundle validation precedes independent review;
- `REJECT_REPAIRABLE` supplies section-scoped feedback to a distinct authoring pass;
- the repaired candidate is regenerated, deterministically revalidated, and independently
  rereviewed before `AGENT_APPROVED`;
- the accepted repaired candidate hash is the hash persisted in the revision-addressed bundle;
- exact fact-block, missing-evidence, and system-failure verdicts remain distinct;
- an identical rerun reaches `NO_OP_PROVEN` without another author call, reviewer call, patch,
  lifecycle event, or run-scoped proposal bundle;
- the local profile dispatches no write effect.

The `readme-poc/` subtree is the revision-addressed final bundle. The
`readme-proposal-bundles/` subtree retains the initial and repaired immutable attempts. The
`evidence/` subtree contains the supervisor run manifests. `focused-acceptance-tests.log`
records the focused controlled proof. `independent-adversarial-tests.log` records the separate
generic, factuality, protected-content, bundle-integrity, and lifecycle negative controls.

The promoted controlled-run bundle was captured before the lifecycle-manifest preservation
correction and is retained unchanged as historical evidence. Its final manifest omits intermediate
stages that the underlying review artifacts prove occurred. `corrected-lifecycle-manifest.json`
and `corrected-no-op-proof.json` are the post-correction controlled proof: the unchanged rerun
preserves every stage from `SNAPSHOTTED` through `AGENT_APPROVED` before appending
`NO_OP_PROVEN`. `independent-implementation-review.md` records an adversarial implementation and
evidence review, including this discrepancy and its correction.

`official-checks-invalidated-by-concurrent-edit.log` records a passing diagnostic suite whose
own end precondition says `TREE MODIFIED DURING RUN`; it is retained for truthfulness and is not
acceptance proof. `official-checks-cancelled-after-concurrent-edit.log` records a second run stopped
after another concurrent edit made it ineligible. `official-checks-attempt-1.log` is the accepted
clean-tree run: 1,638 tests passed, 24 live tests were deselected, every official static/governance
check passed, and both tree preconditions reported `TREE CLEAN`.
