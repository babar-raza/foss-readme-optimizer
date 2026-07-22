# Full-project truth audit — 2026-07-22

## Verdict

`NOT PRESENTABLE`. The working tree is a substantial Level-3 repository-presentation POC: it has
strong allow-list and push-blocking controls, a capability registry, a supervisor, nine specialist
domains, git-ref state/CAS locks, local README commits, validation, and evidence. It is not a
restartable autonomous service and cannot perform the required draft-PR pilot lifecycle. The
default test suite is unusually slow and overlapping/terminated runs left blocked local git-clone
descendants (`OPS-010`), although one clean single-process run did complete green.

Scores: overall 3/8; presentation intelligence 3/8; autonomous runtime 3/8; reliability 2/8;
pilot readiness 2/8; production readiness 1/8.

## Authoritative hierarchy and reconciliation

1. `plans/requirements.md` is the normative obligation/acceptance register.
2. `plans/master.md` is the gated architecture, decision, sequence, and status specification.
3. `plans/GOVERNANCE.md` and `AGENTS.md` govern changes and execution.
4. `docs/` describes current behavior; code, tests, workflows, and execution evidence determine
   whether that description is true.
5. `logs/` records history; `plans/investigations/` records research and evidence, not completion.

Wave-8 reconciliation found that the master status and checklist overclaim closure. The working
tree has major Wave 7/8 additions, but it is uncommitted; 121 requirements remain `PLANNED`, 24
were `BACKLOG`, and 21 were `PARTIAL` before this audit's surgical requirement updates. The master
also reports a stale 622-test baseline. After removing overlapping audit processes, one clean
`pytest -q` completed with 824 passed and 18 deselected in 410.22 seconds; the sequence/concurrency
hazard documented by `OPS-010` remains open. Master correction is pending its mandatory fresh
approval gate.

## Capability inventory

| Component | Intended responsibility | Actual implementation/evidence | Status |
|---|---|---|---|
| Registry/allow-list | Define all managed repositories and permissions | 25 entries; read/write intent gates in `registry/loader.py`; three enabled Java targets | PROVEN |
| Push blocking | Prevent product-remote pushes | disabled push URL, pre-push hook, security tests | PROVEN |
| Inspection/profile | Extract repository/ecosystem facts | multi-ecosystem profiling, GitHub tree/cache path, unit and historical live evidence | PARTIAL |
| Product truth | Provenance-bearing complete technical facts | narrow identity/license/link/talking-point record; not a generation precondition | PARTIAL |
| Presentation assessment | Audit README and GitHub surfaces | reports, validators, nine specialist domains; broad quality requirements remain planned | PARTIAL |
| README mutation | Surgical safe local changes | one owned resources span and one `local_write` capability; no general section-aware editor | PROVEN (narrow) |
| Metadata/community/visuals | Manage broader presentation | audit/proposal/prepare paths; no settings or product-remote apply path | PARTIAL |
| Independent verification | Separate author and verifier | independent domain and deterministic/LLM checks exist; portfolio/pilot acceptance incomplete | PARTIAL |
| State/idempotency | Durable resume and exactly-once effects | git refs, CAS, leases, fingerprints, local effect ledger; state failures are best-effort | PARTIAL |
| Scheduling | Periodic portfolio operation | working-tree daily/manual Actions matrix for enabled entries | PARTIAL |
| Trigger/queue lifecycle | Durable event intake, dedup, backpressure, recovery | no durable queue or event identity; other trigger types absent | MISSING |
| Failure handling | Retry, isolation, rate limits, crash recovery | bounded LLM retry and matrix isolation; no lifecycle checkpoint/alert/missed-run recovery | PARTIAL |
| PR lifecycle | Create/update/deduplicate safe review changes | no `remote_write` capability, product branch, or PR API path | MISSING |
| Observability | Health, metrics, alerts, audit trail | evidence files and summaries; no health/backlog/alert surface | PARTIAL |
| Continuous deployment | Unattended service operation | CI workflow only; no restartable worker/service deployment | PLANNED_ONLY |

## Actual and intended runtime

Actual:

```text
schedule/manual Actions -> enabled registry matrix -> supervise
  -> preflight/probe -> clone/cache -> specialist classify/run
  -> optional planner loop -> validators/verifier
  -> local push-blocked commit -> best-effort git-ref state + runs/ evidence
  -> stop (no product branch/PR, no durable event record)
```

Intended:

```text
schedule/push/release/product-update/operator/full-audit triggers
  -> durable deduplicating queue -> per-repo lock + checkpointed worker
  -> refresh caches -> provenance-complete product truth
  -> repository-specific multi-surface plan -> deterministic/agentic proposal
  -> factuality + ownership + regression + independent verification gates
  -> approved branch/draft-PR create-or-update transaction
  -> durable state/evidence/metrics -> retry, resume, alerts, periodic reevaluation
```

The missing middle is not cosmetic: durable trigger intake, fail-closed state, full facts and
ownership contracts, generalized regression protection, and PR transaction reconciliation are the
minimum boundary between the actual POC and the intended service.

## Complete material gap register

| Gap | Category | Evidence/consequence | Required fix and objective proof | Wave | Pilot | Production |
|---|---|---|---|---|---|---|
| AUD-001 | Validation | Clean suite passes, but overlapping/terminated runs leave blocked pytest/git descendants and `OPS-010` remains open | Fix `OPS-010`; repeated full suite and cancellation cleanup proof on clean process trees | Foundation | yes | yes |
| AUD-002 | Factuality | `FACT-001` partial; `FACT-002`–`010` largely planned | Typed complete facts/provenance schema enforced before proposals; negative claim tests | Foundation | yes | yes |
| AUD-003 | Ownership | `OWN-010/011/013` incomplete; no real product-agent receiver | Explicit file/region/fact ownership and blocking conflict record | Foundation/change management | yes | yes |
| AUD-004 | Reliability | supervisor state load/save deliberately best-effort | `RUN-005` fail-closed semantics and failure-injection/resume proof | Foundation | yes | yes |
| AUD-005 | Autonomy | schedule/manual matrix only; no durable event identity/queue | `RUN-002/006`, durable dedup queue and restart proof | Autonomous runtime | targeted demo yes | yes |
| AUD-006 | Reliability | no missed-run recovery/backpressure; incomplete rate-limit proof | queue policy, retry/backoff budgets, controlled 429/outage tests | Autonomous runtime | failure demo yes | yes |
| AUD-007 | Integration | no remote-write/branch/draft-PR capability | `PIL-014`: gated create/update/dedup/reconcile transaction | Change management | yes | yes |
| AUD-008 | Presentation quality | broad README edits and technical claim preservation remain planned | section-aware fact-linked proposals and before/after semantic checks | Presentation intelligence | yes | yes |
| AUD-009 | Regression | one owned span and narrow license cross-check only | generalized protected-content baseline, semantic regression and provenance | Change management | yes | yes |
| AUD-010 | Pilot readiness | only enabled targets are Java | label them controlled POC or onboard at least one non-Java target with verified access/policy | Pilot | yes | no |
| AUD-011 | Evidence | no single three-repo lifecycle bundle | `PIL-013` committed manifest and independent reproduction | Pilot | yes | yes |
| AUD-012 | Observability | evidence exists but no health/backlog/alert interface | `RUN-007` health report, last-success and alert tests | Production hardening | no | yes |
| AUD-013 | Planning | closed-wave prose conflicts with open requirements and runtime | reopen/resequence master and refresh stale rows/traceability | Foundation | yes | yes |
| AUD-014 | Deployment | Actions fan-out is not a restartable service | choose CI+durable-queue or worker deployment; soak and recovery proof | Production hardening | no | yes |

## Traceability and corrected dependency order

| Goal | Requirements | Current implementation | Validation | Status/gap |
|---|---|---|---|---|
| Safe repository scope | `CORE-003/004/033`, `SAFE-*` | registry intent gates and push blocking | unit/security/live history | PROVEN |
| Complete product truth | `FACT-001`–`010` | narrow facts capability | unit + one historical live selection | PARTIAL/AUD-002 |
| Autonomous runtime | `RUN-001`–`007`, `SCL-001`–`008` | Actions schedule, locks, state | static/unit; suite currently hangs | PARTIAL/AUD-004–006 |
| Presentation intelligence | `RDM-*`, `SURF-*`, `OWN-*` | audits/proposals plus narrow README write | unit/historical live | PARTIAL/AUD-003/008/009 |
| Reviewable delivery | `PIL-014`, `CORE-021/022`, `OWN-014/015` | none for product remote | none | MISSING/AUD-007 |
| Three-repo acceptance | `PIL-001`–`014` | three enabled Java repos; historical individual runs | no complete bundle | MISSING/AUD-010/011 |

Correct order:

1. Truth/foundation: reconcile specs, fix test hang, enforce facts/provenance/ownership, make required
   state fail closed.
2. Autonomous runtime: durable event identity/queue, trigger unification, retry/backoff, resume and
   isolation proof.
3. Presentation intelligence: complete repository-specific, fact-linked README and surface plans.
4. Change management: protected content, semantic regression, branch/draft-PR lifecycle and
   transaction reconciliation.
5. Controlled pilot: three baselines, proposals, approved draft PRs, reruns, trigger/recovery/failure
   demonstrations, independent acceptance bundle.
6. Production hardening: health/alerts, deployment, portfolio scaling, security review, soak test.

## Three-repository pilot assessment

Live read-only GitHub API checks on 2026-07-22 returned `push=true`, `admin=true`, and
`archived=false` for:

| Repository | Role and risk | Suitability |
|---|---|---|
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` | blank-slate/local-write value proof; package resolution and quality gaps | controlled POC |
| `aspose-3d-foss/Aspose.3D-FOSS-for-Java` | zero-promotional-gap but bot-authored quality/regression case | controlled POC |
| `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` | partial-gap deterministic case; registry mode is dry-run | controlled POC after exact write approval/config change if a PR is required |

These are the only configured write/dry-run targets, but all are Java. They can honestly support a
homogeneous engineering POC. A heterogeneous pilot requires onboarding and fresh write-access
verification for at least one non-Java repository; disabled mode must never be silently bypassed.

Pilot demonstration and gate are exactly `PIL-013/014`: all three complete baseline through draft
PR/no-op/recovery/failure isolation with no unsupported claims, no manual content repair, and one
independently reviewed evidence bundle. No product remote will be written without a separate exact
what/why/where approval.

Earliest credible point: optimistic—after the foundation and change-management gates plus one
homogeneous controlled run; realistic—after foundation, autonomous-runtime, presentation, and
change-management work plus two full pilot rehearsals and independent review; blocked—until test
hang, facts/ownership, fail-closed state, and PR lifecycle are resolved. No calendar date is
defensible from repository evidence.

## Direct answers to the 27 audit questions

1. Designed toward the requested system: yes; implemented as that system: no.
2. Existing: registry/safety, inspection/profiling, supervisor/capabilities, specialist audits,
   local README mutation, validators/verifier, git-ref state/locks, scheduled enabled-repo matrix.
3. Partial: facts, presentation intelligence, state/recovery, idempotency, scheduling, failure
   handling, evidence, ownership and regression protection.
4. Planned only: unified triggers, full facts, broad surface management, PR lifecycle, monitoring,
   deployment and portfolio production gates.
5. Optimistic/manual: historical live claims without a current green suite; product-agent handoff;
   social preview delivery; product-remote changes; much acceptance evidence is mocked/unit-only.
6. Level 3, repeatable single-repository dry-run/local-commit POC.
7. No: best-effort durable state and absent queue/recovery/health prevent long-running autonomy.
8. No: major route elements exist as rows but are incomplete, unsequenced, or absent from runtime.
9. No: status/checklist and requirement states conflict.
10. No: reliability/facts/ownership/PR foundations must move before pilot/production claims.
11. Previously weak/absent: fail-closed state, durable event identity, lifecycle evidence bundle,
    explicit homogeneous-pilot truth gate, and PR transaction reconciliation; now `RUN-005`–`007`
    and `PIL-012`–`014`.
12. Yes: scheduled portfolio execution arrived before the queue/recovery and green-suite gates.
13. Yes: many planned rows name outcomes without end-to-end failure and recovery evidence.
14. Yes: legacy `run` and `supervise` overlap; plan counts/CLI descriptions are stale; historical
    closure claims coexist with open acceptance gates.
15. Current blockers: unresolved suite process-lifecycle risk, incomplete facts/ownership/regression, best-effort state, no PR
    lifecycle, and no complete three-repo bundle.
16. Production blockers additionally include durable queue/triggers, rate-limit/backpressure proof,
    monitoring/alerts, deployment and soak testing.
17. Fix the suite and truth claims first; freeze new specialist abstractions meanwhile.
18. Exact placements: foundation (`FACT/OWN/RUN-005`), autonomous runtime (`RUN-002/006`, `SCL-*`),
    change management (`PIL-014`, `OWN-*`), pilot (`PIL-012/013`), production (`RUN-007`).
19. Wave placement is the six-step dependency order above.
20. Move facts/ownership, fail-closed state, validation stability, and PR reconciliation earlier.
21. Freeze feature expansion, reopen overclaims, select `supervise` as the pilot path, and require
    evidence before status promotion; no wholesale rewrite is justified.
22. Earliest credible presentation is after foundation/change-management gates and complete pilot
    rehearsals, not at the current state.
23. The three verified-access Java repos above are the only safe current POC set; a true
    heterogeneous pilot needs a newly onboarded non-Java target.
24. Demonstrate registry intake through repository-specific audit/proposal, approved draft PR,
    unchanged rerun, targeted trigger, regression prevention, restart, and isolated failure.
25. Evidence must satisfy `PIL-013/014` and include independent review.
26. After a pilot, full event coverage, portfolio scaling, monitoring/alerts, deployment/security
    review and soak testing remain.
27. The project is at least three dependency waves plus a controlled pilot away from passive-review
    autonomy, and a further production-hardening wave from production candidacy.

## Drastic-action decision

Freeze new specialist/domain abstractions until `AUD-001`–`007` are closed. Retain the registry,
safety model, state/CAS primitives, deterministic rendering, validators, and supervisor; they are
valuable. Use `supervise` as the sole pilot path and label `run` compatibility-only during the
pilot. Do not delete either path until parity/migration evidence exists. Replace closure-by-unit-test
with the `PIL-013` lifecycle bundle. This is required for the pilot except monitoring/deployment,
which are production-only.

## Verification record

- `ruff check .`: pass.
- `ruff format --check .`: 229 files already formatted.
- `mypy src`: pass across 144 source files.
- Early overlapping `pytest -q`/unit runs were terminated and left pytest/git descendants in local
  clone operations; those audit-created processes were cleaned up by PID. A subsequent clean,
  single-process `pytest -q` passed: 824 passed, 18 deselected in 410.22 seconds. This establishes a
  current green baseline but does not close the pre-existing `OPS-010` process-lifecycle risk.
- `gh api repos/{repo}`: all three configured pilots currently report push/admin access and are not
  archived; this was read-only and made no remote changes.
- Independent adversarial agent verdict: `NOT PRESENTABLE`, Level 3; it independently identified
  no PR path, best-effort state, incomplete facts/ownership, homogeneous pilots, and the suite hang.
