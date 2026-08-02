# Project status (generated -- do not hand-edit)

Regenerate with `python plans/investigations/tools/traceability_matrix.py`. This replaces `plans/master.md`'s old hand-maintained Status section (Wave 9.3, 2026-07-22) -- see `plans/roadmap.md` for what's next and `logs/` for the dated history.

**Latest Decision Ledger entry**: #88

## Current verified portfolio status

Current completion is derived from the runtime registry, durable repository lifecycle state, and current fact/acceptance contracts.

| Boundary | Current contract-valid | Raw lifecycle label (non-closing) |
|---|---:|---:|
| FACTS_READY | 1/31 | 17/31 |
| CANDIDATE_GENERATED | 1/31 | 10/31 |
| DETERMINISTIC_VALIDATED | 1/31 | 10/31 |
| AGENT_APPROVED | 1/31 | 3/31 |
| NO_OP_PROVEN | 0/31 | 2/31 |
| HUMAN_ACCEPTED | 0/31 | 0/31 |

### Registry authority

- Denominator: **31**, loaded from `data/products.json`.
- Raw SHA-256: `d9d687b42cc7112ee7ffafe0271e4a8cf3db7b9dc25c6a56854524c4129c37e3`.
- Canonical-text SHA-256: `f72c0278616d043aaeedd192e554f19817029a53fb00854f9c771de9cb2f3ecb`.
- Canonical-JSON SHA-256: `ee34782b1f0e567437ad27ced93c73c9e617d8126b2de57875cc5ed694b04aac`.
- Registry revision: `35e44d036bf1097394ecfaeaeb3ba15e842d398cc28df0d2e3371d54a93652f9`.
- Gate-A closure eligible: **false**; reasons: pending_intake_present, unexplained_observations_present

### Excluded discoveries and intake

- `{"classification": "source_excluded", "org_repo": "aspose-imaging-foss/*", "reason": "No aspose-imaging-foss organization exists; aspose-imaging is a separate non-FOSS source and is not authorized for this portfolio."}`
- `{"classification": "unmatched", "org_repo": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP", "reason": "non-matching observation remains discovery-only pending explicit disposition"}`
- Unexplained observation: `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP`.
- Pending intake: `aspose-3d-foss/Aspose.3D-FOSS-for-Java`.

### Blocked admitted repositories

- `aspose-html-foss/Aspose.HTML-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary

### Live mission

- Durable state version: `706`.
- Active task: `L8-PLAN-RECONCILIATION-ACCELERATION`.
- Active goal: `GOAL-P0-PLAN-FREEZE`.
- Claim: `bbd698f280b143e282b396867c959bad`; expires `2026-08-02T19:16:46.109448+00:00`.
- Loaded graph: `033ef111ab2c4810f3747ecc8b482c6cbb0dfdfdbe71b3a0d414997ebe67f456`.
- Durable graph: `37e33944e5d99ca32897c2a23dcf7e882f14ccb3d4a37c5edc510d99c9231ae3`; drift: **true**.

Historical portfolio manifests remain inspectable evidence but never supply headline current status.

## Requirement status counts (supporting detail -- see the Full-registry table above for the primary measure)

| Status | Count |
|---|---:|
| IMPLEMENTED | 155 |
| PLANNED | 123 |
| PARTIAL | 95 |
| GOVERNANCE | 35 |
| BACKLOG | 28 |
| DEPRECATED | 22 |
| RESEARCH-GATED | 6 |

## Build Checklist wave state


## Implementation-truth matrix summary (Wave 9.2)

- 155 `IMPLEMENTED` rows checked.
- 0 with a semantic closure finding.
- 87 with informational-only findings (no test path cited -- often pre-dates this project's later per-row citation convention, not necessarily a real gap).
- 68 fully clean.
- Full detail: `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`.
