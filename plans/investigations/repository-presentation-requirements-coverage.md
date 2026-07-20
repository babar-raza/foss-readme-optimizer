# Repository-Presentation Requirements Coverage Matrix

governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md`  
artifact_role: analysis_or_evidence_only  
(223 requirements @ HEAD `4adbaaf`)

Coverage counts a requirement only when this investigation defines all 10 elements (authoritative input, owner, current behavior, gap, target, state, failure handling, implementation direction, acceptance test, evidence). Judgments: per-ID overrides over status defaults, with an independent-review downgrade pass — see `tools/coverage_classify.py` for every note.

## Totals by classification

| Classification | Count |
|---|---:|
| FULLY_INVESTIGATED | 67 |
| DEFERRED_WITH_DESIGN | 54 |
| ALREADY_PROVEN | 52 |
| PARTIALLY_INVESTIGATED | 37 |
| DEFERRED_WITHOUT_DESIGN | 13 |

## Totals by group x classification

| Group | ALREADY_PROVEN | DEFERRED_WITHOUT_DESIGN | DEFERRED_WITH_DESIGN | FULLY_INVESTIGATED | PARTIALLY_INVESTIGATED | Total |
|---|---:|---:|---:|---:|---:|---:|
| BIZ | 0 | 0 | 2 | 4 | 2 | 8 |
| CORE | 24 | 2 | 1 | 3 | 2 | 32 |
| DOC | 0 | 3 | 1 | 4 | 2 | 10 |
| FACT | 0 | 0 | 4 | 3 | 3 | 10 |
| GOV | 0 | 0 | 1 | 11 | 1 | 13 |
| INT | 0 | 0 | 4 | 6 | 0 | 10 |
| LLM | 8 | 0 | 3 | 0 | 3 | 14 |
| MET | 0 | 3 | 3 | 2 | 0 | 8 |
| NFR | 2 | 0 | 0 | 3 | 7 | 12 |
| OPS | 4 | 3 | 1 | 0 | 0 | 8 |
| OWN | 0 | 0 | 0 | 12 | 3 | 15 |
| PIL | 0 | 0 | 6 | 3 | 1 | 10 |
| RDM | 2 | 1 | 14 | 3 | 3 | 23 |
| SAFE | 8 | 1 | 2 | 3 | 4 | 18 |
| SURF | 0 | 0 | 8 | 7 | 0 | 15 |
| VAL | 4 | 0 | 4 | 3 | 6 | 17 |

## Totals by priority

| Priority | Total | In gap classes (NAMED_ONLY/DEFERRED_WITHOUT_DESIGN/MISSING) |
|---|---:|---:|
| P0 | 87 | 0 |
| P1 | 109 | 7 |
| P2 | 27 | 6 |

## P0/P1 requirements in gap classes -- 7 (P0: 0)

Every P0/P1 gap carries an explicit repair route (enforced by this script).

| ID | Pri | Coverage | Why deferred | Repair route |
|---|---|---|---|---|
| OPS-001 | P1 | DEFERRED_WITHOUT_DESIGN | act local CI simulation not performed (system package install needs approval); P1 | Roadmap card: install act + workflow_dispatch e2e (Phase 16) |
| MET-001 | P1 | DEFERRED_WITHOUT_DESIGN | Referral baseline study = Phase-20 homework, not this sprint; P1 | Roadmap Wave 0 card (Phase-20 traffic study) |
| MET-002 | P1 | DEFERRED_WITHOUT_DESIGN | Feasibility-study contents = Phase-20; P1 | Roadmap Wave 0 card (Phase-20 traffic study) |
| MET-006 | P1 | DEFERRED_WITHOUT_DESIGN | Observation period definition = Phase-20; P1 | Roadmap Wave 0 card (Phase-20 traffic study) |
| DOC-003 | P1 | DEFERRED_WITHOUT_DESIGN | Presentation-standard research (n8n/nuget) not in sprint; P1 | Roadmap Wave 0 card (Phase-20 research) |
| DOC-004 | P1 | DEFERRED_WITHOUT_DESIGN | Presentation-standard contents; P1 | Roadmap Wave 0 card (Phase-20 research) |
| DOC-007 | P1 | DEFERRED_WITHOUT_DESIGN | Traffic study; P1 | Roadmap Wave 0 card (Phase-20 traffic study) |

## Notes on contested classifications

- **CORE-012 / CORE-031 / NFR-002** are `PARTIALLY_INVESTIGATED` despite IMPLEMENTED status: the current-state evidence proves the work-clone-as-durable-state design fails portability and ephemeral CI; routed to a supersession delta (work clone -> cache; `.state/` StateStore; idempotency strengthening).
- **DOC-003/004/007, MET-001/002/006, OPS-001** are the only P1 gap-class rows: all are Phase-16/20 research/ops deliverables this investigation sprint intentionally does not perform; each is routed to an explicit roadmap card.
- **No P0 requirement is in a gap class.** No requirement is `MISSING` or `NAMED_ONLY`.

Full per-requirement rows: `control/requirements-coverage.csv`.
