# Repository-Presentation Requirements Coverage Matrix

governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md`  
artifact_role: analysis_or_evidence_only  
(390 requirements @ HEAD `a7ac331`)

Coverage counts a requirement only when this investigation defines all 10 elements (authoritative input, owner, current behavior, gap, target, state, failure handling, implementation direction, acceptance test, evidence). Judgments: per-ID overrides over status defaults, with an independent-review downgrade pass — see `tools/coverage_classify.py` for every note.

## Totals by classification

| Classification | Count |
|---|---:|
| ALREADY_PROVEN | 133 |
| PARTIALLY_INVESTIGATED | 87 |
| DEFERRED_WITH_DESIGN | 82 |
| FULLY_INVESTIGATED | 75 |
| DEFERRED_WITHOUT_DESIGN | 13 |

## Totals by group x classification

| Group | ALREADY_PROVEN | DEFERRED_WITHOUT_DESIGN | DEFERRED_WITH_DESIGN | FULLY_INVESTIGATED | PARTIALLY_INVESTIGATED | Total |
|---|---:|---:|---:|---:|---:|---:|
| AGT | 5 | 0 | 0 | 0 | 3 | 8 |
| AUTH | 5 | 0 | 1 | 0 | 1 | 7 |
| BIZ | 0 | 0 | 2 | 4 | 2 | 8 |
| CAP | 5 | 0 | 3 | 0 | 1 | 9 |
| CORE | 24 | 2 | 1 | 3 | 4 | 34 |
| DEP | 5 | 0 | 1 | 0 | 0 | 6 |
| DOC | 0 | 3 | 1 | 4 | 2 | 10 |
| ECO | 4 | 0 | 1 | 0 | 0 | 5 |
| EFF | 6 | 0 | 0 | 0 | 0 | 6 |
| EVID | 2 | 0 | 0 | 0 | 2 | 4 |
| FACT | 2 | 0 | 5 | 3 | 3 | 13 |
| FRESH | 6 | 0 | 0 | 0 | 0 | 6 |
| GAP | 2 | 0 | 1 | 0 | 0 | 3 |
| GOV | 5 | 0 | 3 | 17 | 1 | 26 |
| INT | 0 | 0 | 4 | 6 | 0 | 10 |
| L8 | 1 | 0 | 2 | 0 | 10 | 13 |
| LLM | 14 | 0 | 5 | 0 | 3 | 22 |
| MEM | 3 | 0 | 0 | 0 | 2 | 5 |
| MET | 0 | 3 | 3 | 2 | 0 | 8 |
| NFR | 2 | 0 | 0 | 4 | 7 | 13 |
| ONB | 0 | 0 | 2 | 0 | 2 | 4 |
| OPS | 5 | 3 | 3 | 0 | 2 | 13 |
| ORC | 3 | 0 | 2 | 0 | 3 | 8 |
| OWN | 0 | 0 | 0 | 12 | 3 | 15 |
| PIL | 0 | 0 | 8 | 4 | 2 | 14 |
| PKG | 5 | 0 | 1 | 0 | 0 | 6 |
| PRL | 3 | 0 | 4 | 0 | 2 | 9 |
| RDM | 5 | 1 | 10 | 3 | 6 | 25 |
| RUN | 3 | 0 | 0 | 0 | 7 | 10 |
| SAFE | 7 | 1 | 3 | 3 | 5 | 19 |
| SCL | 2 | 0 | 4 | 0 | 3 | 9 |
| SURF | 0 | 0 | 6 | 7 | 2 | 15 |
| VAL | 4 | 0 | 5 | 3 | 6 | 18 |
| VER | 5 | 0 | 1 | 0 | 3 | 9 |

## Totals by priority

| Priority | Total | In gap classes (NAMED_ONLY/DEFERRED_WITHOUT_DESIGN/MISSING) |
|---|---:|---:|
| P0 | 143 | 0 |
| P1 | 170 | 7 |
| P2 | 72 | 6 |

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
