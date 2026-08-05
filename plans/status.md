# Project status (generated -- do not hand-edit)

Regenerate with `python plans/investigations/tools/traceability_matrix.py`. This replaces `plans/master.md`'s old hand-maintained Status section (Wave 9.3, 2026-07-22) -- see `plans/roadmap.md` for what's next and `logs/` for the dated history.

**Latest Decision Ledger entry**: #98

## Current verified portfolio status

Current completion is derived from the runtime registry, durable repository lifecycle state, and current fact/acceptance contracts.

| Boundary | Current contract-valid | Raw lifecycle label (non-closing) |
|---|---:|---:|
| FACTS_READY | 1/31 | 20/31 |
| CANDIDATE_GENERATED | 0/31 | 15/31 |
| DETERMINISTIC_VALIDATED | 0/31 | 15/31 |
| AGENT_APPROVED | 0/31 | 11/31 |
| NO_OP_PROVEN | 0/31 | 9/31 |
| HUMAN_ACCEPTED | 0/31 | 0/31 |

### Registry authority

- Denominator: **31**, loaded from `data/products.json`.
- Raw SHA-256: `d9d687b42cc7112ee7ffafe0271e4a8cf3db7b9dc25c6a56854524c4129c37e3`.
- Canonical-text SHA-256: `f72c0278616d043aaeedd192e554f19817029a53fb00854f9c771de9cb2f3ecb`.
- Canonical-JSON SHA-256: `ee34782b1f0e567437ad27ced93c73c9e617d8126b2de57875cc5ed694b04aac`.
- Registry revision: `6d80829133b7005da883d47b87ec14ab66b868d52ee53e8883c458c9df53ad39`.
- Gate-A closure eligible: **false**; reasons: pending_intake_present

### Excluded discoveries and intake

- `{"classification": "source_excluded", "org_repo": "aspose-imaging-foss/*", "reason": "No aspose-imaging-foss organization exists; aspose-imaging is a separate non-FOSS source and is not authorized for this portfolio."}`
- `{"classification": "nonconforming_name", "org_repo": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP", "reason": "repository name does not satisfy the governed execution naming contract"}`
- Pending intake: `aspose-3d-foss/Aspose.3D-FOSS-for-Java`.
- Pending intake: `aspose-3d-foss/Aspose.3D-FOSS-for-Python`.
- Pending intake: `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`.
- Pending intake: `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go`.
- Pending intake: `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`.

### Blocked admitted repositories

- `aspose-email-foss/Aspose.Email-FOSS-for-.Net` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-html-foss/Aspose.HTML-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: checksum-sealed ProductFactsV2 commit recovered after interruption
- `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- System failure: `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET` — independent review wiring failed: GroundedRoleFailure: blind_quality reviewer repeatedly returned ungrounded findings: ['f1:mechanical premise cites quick_start.max_nonblank_code_lines instead of quick_start.fenced_blocks']

### Live mission

- Durable state version: `766`.
- Active task: `L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E`.
- Active goal: `GOAL-V0A-FIRST-VERIFIED-README`.
- Delivery complete: **false**.
- Certification complete: **false**.
- Full mission complete: **false**.
- Claim: `c2765ed230b548f9b54c6cb22d21ced0`; expires `2026-08-05T19:08:53.448613+00:00`.
- Loaded graph: `6bfe0443c80dfd1c622271ab57d04d4ef3717d93b5c460c352dc9059803410bc`.
- Durable graph: `6bfe0443c80dfd1c622271ab57d04d4ef3717d93b5c460c352dc9059803410bc`; drift: **false**.

Historical portfolio manifests remain inspectable evidence but never supply headline current status.

## Requirement status counts (supporting detail -- see the Full-registry table above for the primary measure)

| Status | Count |
|---|---:|
| IMPLEMENTED | 163 |
| PLANNED | 123 |
| PARTIAL | 98 |
| GOVERNANCE | 35 |
| BACKLOG | 28 |
| DEPRECATED | 22 |
| RESEARCH-GATED | 6 |

## Build Checklist wave state


## Implementation-truth matrix summary (Wave 9.2)

- 163 `IMPLEMENTED` rows checked.
- 0 with a semantic closure finding.
- 95 with informational-only findings (no test path cited -- often pre-dates this project's later per-row citation convention, not necessarily a real gap).
- 68 fully clean.
- Full detail: `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`.
