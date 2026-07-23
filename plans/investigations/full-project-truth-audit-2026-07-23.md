# Full-project truth audit — 2026-07-23

## 1. Executive verdict

`NOT PRESENTABLE`. Overall maturity remains **3/8 (substantial proof of concept)**.
The working tree contains genuine advances in authorization, typed facts, trigger identity,
execution profiles, evidence manifests, and multi-ecosystem profiling. They are uncommitted,
several claimed waves lack their own acceptance artifacts, and a production-like heterogeneous
run exposed a P0 false-success condition. That condition has been corrected and regression-tested
locally in this audit, but its production-like rerun is still outstanding.

Scores: presentation intelligence 3/8; autonomous runtime 3/8; reliability 2/8;
pilot readiness 2/8; production readiness 1/8.

## 2. Audit scope and method

The audit reconciled the authoritative plans, requirements, governance, current source, tests,
workflows, registry, working-tree state, and dated evidence. It traced normal supervision,
specialist failure, state, authorization, trigger, evidence, and remote-write paths. It also ran
an independent adversarial review and the repository's official validation driver. No product
remote was written.

## 3. Version and working-tree truth

`HEAD` and `origin/main` both identify commit `f9e389e`. The audited tree is not that shipped
state: it has 61 tracked files modified plus numerous untracked production modules, tests,
workflows, evidence, lock data, and generated plan views. Accordingly:

- the committed branch must not be described as containing the July 23 implementation;
- the working tree must be preserved as user work;
- a green check in this tree is evidence for the candidate state, not proof of what is deployed.

## 4. Authority reconciliation

The controlling order is `plans/requirements.md`, gated `plans/master.md`,
`plans/GOVERNANCE.md`/`AGENTS.md`, then descriptive documentation. Code and execution evidence
decide whether claims are true.

The requirement register currently contains 375 rows before this audit's `VER-009` addition:
151 `IMPLEMENTED`, 120 `PLANNED`, 37 `PARTIAL`, 33 `GOVERNANCE`, 28 `BACKLOG`, and
6 `RESEARCH-GATED`. `plans/roadmap.md` leaves Waves 9.4–13.7 open while the master/log narrative
claims decisions #58–72 closed them. The roadmap and claimed wave closure therefore disagree.
Correcting the gated master requires fresh, section-specific user approval.

## 5. Repository and policy coverage

The allow-list contains 31 repositories: 2 `full`, 24 `dry_run`, and 5 `disabled`, spanning
Python, .NET, Java, C++, TypeScript, Go, and Rust. Read-only portfolio work correctly includes
all entries regardless of mode. End-to-end mutation proof remains constrained by access to the
three enabled Java pilots; this is an access boundary, not representative heterogeneous proof.

## 6. Capability and specialist inventory

The working tree has a broad capability registry and ten ordered specialist domains. The
independent verifier is registered last and depends on the other domains. Important limits remain:

- `open_presentation_pr` is not automatically selected by specialists, supervisor, commands, or
  workflows;
- no specialist populates `OpenProposalV1`;
- product-claim conflicts are diagnostic rather than proposal-blocking;
- independent-verifier findings do not create a corrective task;
- the legacy `run` mutation path still lacks the supervisor verifier guarantee.

## 7. Actual runtime

```text
manual/scheduled workflow -> registry matrix -> supervise
  -> execution profile + allow-list + optional trigger dedup
  -> probe/clone -> sequential specialist tier
  -> optional planner capability loop
  -> local verification/commit where applicable
  -> evidence + best-effort durable state
  -> stop

separate manual dispatch -> authorization record check -> open_presentation_pr
```

This is not yet a durable autonomous service: no queue owns work, recovery is incomplete, and the
remote proposal effect is not part of ordinary convergence.

## 8. Intended runtime

```text
all supported triggers -> durable deduplicating intake
  -> leased/checkpointed worker -> complete provenance-bearing product truth
  -> repository-specific multi-surface plan -> bounded proposal
  -> ownership + factuality + regression + independent verification gates
  -> authorized create/update/supersede draft-PR transaction
  -> durable state/evidence/health -> retry, resume, alert, periodic reevaluation
```

## 9. Critical correctness finding

The heterogeneous proof log is not a success artifact. .NET, Python, and C++ report
`CONVERGED_NO_CHANGE` and exit 0 while the same runs record failed README verification and blocked
candidates. Go has no terminal result, and Rust was not detected in the profiling proof.

Root cause: specialist failures were intentionally isolated outside the planner task graph, but
`final_status()` classified only that graph. The July 23 audit changed the terminal classifier to
fail closed when any final specialist result starts with `ERROR:` and added `VER-009`. This
prevents evidence from simultaneously saying “verification failed” and “converged.”

## 10. State, idempotency, and recovery

Trigger identity/dedup, effect identities, execution profiles, and authorization records are real
candidate improvements. However:

- `supervisor/loop.py::_load_prior_run_state()` still catches a state-backend error and continues;
- several record writes remain best effort;
- only one of the eleven required lifecycle checkpoints is represented;
- there is no durable queue, missed-run recovery, or backpressure owner;
- run-manifest fields do not yet consistently carry authorization and trigger-dedup identities.

`RUN-005` and `RUN-009` are correctly not complete.

## 11. Facts, ownership, and presentation intelligence

Typed partial facts and fact changesets are implemented in the candidate tree, but full technical
facts and provenance are not enforced as a generation precondition. Ownership/conflict detection
is not yet a blocking contract. The system remains strongest at a narrow, policy-driven README
resources span; section-aware technical presentation, protected-content semantics, and broad
multi-surface change application remain planned or partial.

## 12. Authorization and remote change management

The new authorization gate correctly makes remote writes unavailable by default because
`config/authorization/` contains no filed records. This is safe. It also means no current
unattended run can lawfully open a product PR. Beyond authorization, PR proposal state,
automatic invocation, update/supersede/drift reconciliation, draft behavior, and restart proof
remain incomplete.

## 13. Evidence quality

The implementation-truth matrix is useful inventory but tests path existence rather than semantic
acceptance. The heterogeneous directory contains raw logs but no expected portfolio manifest.
Dependency evidence contains an SBOM but no verification record. No July 23 consolidated audit
bundle existed before this file. Evidence claims must therefore stay narrower than wave-closure
narrative.

## 14. Validation

The independent audit ran 49 focused tests successfully. Post-fix targeted regression coverage
passed (4 tests), followed by a clean official pass: Ruff lint and format, mypy, actionlint, plan
structure validation, and the complete non-live suite (1,170 passed, 18 deselected). The plan
validator reported 51 pre-existing row-length warnings. Historical July 22 bootstrap evidence
reports clean 938- and 944-test runs, but those historical results are not used as proof for this
newly changed candidate tree.

## 15. Prioritized gap register

| Priority | Gap | Required proof to close |
|---|---|---|
| P0 | `VER-009` false convergence after specialist failure | Rerun failed heterogeneous cases; each must be `BLOCKED`/non-zero with complete evidence |
| P0 | `RUN-005` state access remains best effort | Failure-injection proves required state read/write failures stop safely and resume deterministically |
| P0 | `FACT-001`–`FACT-010` incomplete enforcement | Provenance-complete facts gate with negative hallucination/conflict tests |
| P0 | `OWN-010`/`OWN-011` ownership conflicts non-blocking | Conflict prevents proposal/effect and produces an actionable record |
| P0 | `ORC-005` verifier bypass in legacy mutation path | Remove the second writer or enforce the same independent gate |
| P0 | `PIL-013` controlled-pilot evidence absent | Independently reproduced three-pilot lifecycle bundle |
| P1 | `PRL-002/003/005/006` incomplete PR lifecycle | Authorized create/update/dedup/supersede/drift/restart proof |
| P1 | `RUN-002/006/007/009` runtime operations incomplete | Durable intake, recovery, health, alerts, and checkpoint proof |
| P1 | `VER-008` findings are passive | Cross-domain finding creates/prevents the appropriate corrective action |
| P1 | heterogeneous proof incomplete | Java/.NET/Python/TS/C++/Go/Rust terminal manifests with explicit unsupported outcomes |
| P2 | roadmap/master/status disagreement | Governed reconciliation against delivered evidence |
| P2 | semantic evidence weak | Evidence verifier validates claims, hashes, command outcomes, and expected artifacts |

## 16. Executable next sequence

1. Rerun the targeted convergence and supervisor tests, then all four official checks.
2. Rerun the previously false-success heterogeneous cases and save terminal manifests.
3. Reconcile the generated roadmap/status and evidence claims without editing gated master text.
4. Make required state operations fail closed and prove outage/restart behavior.
5. Enforce facts and ownership before any proposal-ready state.
6. Integrate authorized PR lifecycle only after the preceding safety gates are demonstrated.
7. Produce `PIL-013` and an independent reproduction before any “presentable” claim.

## 17. Final presentation decision

The system is credible research and a serious engineering POC, but it is not ready to present as
an autonomous repository-presentation system. A truthful demonstration may show deterministic
auditing, policy controls, specialist analysis, local guarded mutation, and the authorization
gate. It must explicitly label remote PR dispatch, durable recovery, full facts/ownership,
heterogeneous acceptance, and controlled-pilot evidence as incomplete.
