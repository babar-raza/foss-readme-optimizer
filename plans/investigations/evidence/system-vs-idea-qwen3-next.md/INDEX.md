# Gap Index

This is the master index of all gaps identified in the truth audit of foss-readme-optimizer.

## Legend

- **HIGH**: Blocks pilot or production readiness - must fix before release
- **MEDIUM**: Important improvement, not blocking - should fix before production
- **LOW**: Nice-to-have, cosmetic issues - can defer

## Gaps by Priority

### HIGH Priority (11 total)

| ID | Title | Severity | Requirements Affected | Wave Assignment |
|---|---|---|---|---|
| [GAP-001](GAP-001.md) | No Continuous Scheduling | HIGH | OPS-004 | Phase 18 |
| [GAP-002](GAP-002.md) | VER-004 Gap: Durable Skip Masks Stale Compliance | HIGH | VER-004 | Wave 8.6 |
| [GAP-003](GAP-003.md) | VER-005 Gap: Coarse Shortcut Blindness | HIGH | VER-005 | Wave 8.6 |
| [GAP-005](GAP-005.md) | OPS-009: Live Test Hangs | HIGH | OPS-009 | Any wave |
| [GAP-007](GAP-007.md) | Pilot Not Truly Heterogeneous | HIGH | PIL-012 | Phase 26 |
| [GAP-008](GAP-008.md) | No Commit-to-PR Pipeline | HIGH | PIL-014 | Phase 25 |
| [GAP-012](GAP-012.md) | Missing `act` CI Simulation Proof | HIGH | OPS-001 | Phase 16 |
| [GAP-013](GAP-013.md) | Supervisor Planner Prompt Not Migrated | HIGH | GOV-024 | Wave 8.6 |
| [GAP-014](GAP-014.md) | No Supervisor Live Evidence | HIGH | GOV-018 | Wave 5-6 |
| [GAP-015](GAP-015.md) | No Community Template Audit | HIGH | SURF-007 | Phase 23 |
| [GAP-016](GAP-016.md) | No Product Facts Enforcement | HIGH | FACT-001 | Phase 20 |

### MEDIUM Priority (5 total)

| ID | Title | Severity | Requirements Affected | Wave Assignment |
|---|---|---|---|---|
| [GAP-004](GAP-004.md) | OPS-011: Missing Decision Quality Metrics | MEDIUM | OPS-011 | Phase 18 |
| [GAP-006](GAP-006.md) | OPS-010: Test Network Dependency | MEDIUM | OPS-010 | Any wave |
| [GAP-009](GAP-009.md) | LLM-017: Embedding Model Unwired | MEDIUM | LLM-017 | Phase 19 |
| [GAP-017](GAP-017.md) | No API-Managed Fields Workflow | MEDIUM | SURF-004, OWN-014 | Phase 22 |
| [GAP-018](GAP-018.md) | No Visual Asset Approval Mechanism | MEDIUM | SURF-010 | Phase 24 |

### LOW Priority (1 total)

| ID | Title | Severity | Requirements Affected | Wave Assignment |
|---|---|---|---|---|
| [GAP-010](GAP-010.md) | SAFE-019: No Converged-No-Work Evidence | LOW | SAFE-019 | Any wave |

## Summary Statistics

- **Total gaps identified**: 15
- **HIGH priority**: 11
- **MEDIUM priority**: 5
- **LOW priority**: 1

## Wave Assignment Summary

| Wave | Gaps Assigned | Notes |
|---|---|---|
| Phase 16 | 1 | `act` CI simulation proof |
| Phase 18 | 2 | Continuous scheduling, decision quality metrics |
| Phase 19 | 1 |Embedding model wiring |
| Phase 20 | 1 | Product facts enforcement |
| Phase 22 | 2 | API-managed fields, visual approval |
| Phase 23 | 1 | Community template audit |
| Phase 24 | 1 | Visual asset mechanism |
| Phase 25 | 1 | Commit-to-PR pipeline |
| Phase 26 | 1 | Truly heterogeneous pilot |
| Wave 5-6 | 1 | Supervisor live evidence |
| Wave 8.6 | 4 | VER-004, VER-005, GOV-024, prompt migration |
| Any wave | 3 | Test hangs, network dependency, evidence |

## Recommended Fix Order

**Week 1 (Critical Path to Pilot):**
1. GAP-007 - Pilot heterogeneity (must fix before calling it "heterogeneous")
2. GAP-008 - Commit-to-PR pipeline (required for "proof" requirement)
3. GAP-012 - `act` CI simulation (required for "Phase 16" completion)

**Week 2 (Production Readiness):**
4. GAP-001 - Continuous scheduling (OPS-004)
5. GAP-003 - VER-005 coarse shortcut (production reliability)
6. GAP-002 - VER-004 durable skip (same reliability)

**Week 3 (Quality & Polish):**
7. GAP-013 - Supervisor prompt migration (GOV-024 compliance)
8. GAP-009 - Embedding model (template clone detection)
9. GAP-004 - Decision quality metrics (monitoring)

**Week 4 (Final Polish):**
10. GAP-005 - Test hangs (developer productivity)
11. GAP-006 - Test network dependency (developer productivity)
12. GAP-010 - No-work evidence (CI clarity)
13. GAP-014 - Supervisor live evidence (GOV-018 compliance)
14. GAP-015 - Community templates (phase 23)
15. GAP-016 - Product facts enforcement (phase 20)
16. GAP-017 - API fields workflow (phase 22)
17. GAP-018 - Visual approval (phase 24)
