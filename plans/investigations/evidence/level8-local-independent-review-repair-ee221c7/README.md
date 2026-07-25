# Local Independent README Review and Repair Proof

This evidence binds task `L8-LOCAL-INDEPENDENT-REVIEW-REPAIR` to control-repository
commit `ee221c7480402234acaba2e121ae7724b4560d96`.

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
records the focused controlled proof.

`official-checks-invalidated-by-concurrent-edit.log` records a passing diagnostic suite whose
own end precondition says `TREE MODIFIED DURING RUN`; it is retained for truthfulness and is not
acceptance proof. `official-checks-cancelled-after-concurrent-edit.log` records a second run stopped
after another concurrent edit made it ineligible. `official-checks-attempt-1.log` is reserved for
the later clean-tree rerun.
