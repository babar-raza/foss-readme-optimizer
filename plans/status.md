# Project status (generated -- do not hand-edit)

Regenerate with `python plans/investigations/tools/traceability_matrix.py`. This replaces `plans/master.md`'s old hand-maintained Status section (Wave 9.3, 2026-07-22) -- see `plans/roadmap.md` for what's next and `logs/` for the dated history.

**Latest Decision Ledger entry**: #106

## Current verified portfolio status

Current completion is derived from the runtime registry, durable repository lifecycle state, and current fact/acceptance contracts.

| Boundary | Current contract-valid | Raw lifecycle label (non-closing) |
|---|---:|---:|
| FACTS_READY | 0/33 | 16/33 |
| CANDIDATE_GENERATED | 0/33 | 1/33 |
| DETERMINISTIC_VALIDATED | 0/33 | 1/33 |
| AGENT_APPROVED | 0/33 | 1/33 |
| NO_OP_PROVEN | 0/33 | 0/33 |
| HUMAN_ACCEPTED | 0/33 | 0/33 |

### Registry authority

- Denominator: **33**, loaded from `data/products.json`.
- Raw SHA-256: `eb526af1d1c70b700a89e4445d399e1131170e5ecfb7359147bc671be6da8479`.
- Canonical-text SHA-256: `2e71e7f2c9ccbe7662ed37a5545a5f1af07363de0d6da8579e109fe4db20c1e7`.
- Canonical-JSON SHA-256: `04367cbbf60e69c721e0986192b8a76bc26ea7ecbb4fc9a2ac6e3faa572b8b1e`.
- Registry revision: `af29e03d72e7900c92175e297474d88d6a683b6865633dfc8bafa163ccff60ab`.
- Gate-A closure eligible: **true**; reasons: none

### Excluded discoveries and intake

- `{"classification": "source_excluded", "org_repo": "aspose-imaging-foss/*", "reason": "No aspose-imaging-foss organization exists; aspose-imaging is a separate non-FOSS source and is not authorized for this portfolio."}`
- `{"classification": "nonconforming_name", "org_repo": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP", "reason": "repository name does not satisfy the governed execution naming contract"}`
- `{"classification": "nonconforming_name", "org_repo": "aspose-slides-foss/.github", "reason": "repository name does not satisfy the governed execution naming contract"}`

### Blocked admitted repositories

- `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-cells-foss/Aspose.Cells-FOSS-for-Go` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-cells-foss/Aspose.Cells-FOSS-for-Rust` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-email-foss/Aspose.Email-FOSS-for-.Net` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-html-foss/Aspose.HTML-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-pdf-foss/Aspose-PDF-FOSS-for-Go` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-psd-foss/Aspose.PSD-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-slides-foss/Aspose.Slides-FOSS-for-Java` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- `aspose-tex-foss/Aspose.TeX-FOSS-for-Python` — BLOCKED_MISSING_EVIDENCE: product facts persisted with a narrowly scoped unresolved evidence boundary
- System failure: `aspose-3d-foss/Aspose.3D-FOSS-for-Python` — independent review wiring failed: LLMError: forced tool call returned an invalid structured response after 1 attempts: forced tool call arguments were not valid JSON: Unterminated string starting at: line 84 column 30 (char 7128); finish_reason='length'; completion_tokens=4000

### Live mission

- Durable state version: `1213`.
- Active task: `-`.
- Active goal: `GOAL-V0B-POST-PYTHON-SLICES`.
- Delivery complete: **false**.
- Certification complete: **false**.
- Full mission complete: **false**.
- Claim: `-`; expires `-`.
- Loaded graph: `ff8b0ff722024e673b87a54b6ae828fb8d16e3d819b5fe270c6fc6ed02ea93db`.
- Durable graph: `30f2d9dba62896462960f5ed0d7adf1d47e1fd1e70f15953184998333ec8f4fe`; drift: **true**.

Historical portfolio manifests remain inspectable evidence but never supply headline current status.

## Requirement status counts (supporting detail -- see the Full-registry table above for the primary measure)

| Status | Count |
|---|---:|
| IMPLEMENTED | 166 |
| PLANNED | 123 |
| PARTIAL | 101 |
| GOVERNANCE | 35 |
| BACKLOG | 34 |
| DEPRECATED | 23 |
| RESEARCH-GATED | 6 |

## Build Checklist wave state


## Implementation-truth matrix summary (Wave 9.2)

- 166 `IMPLEMENTED` rows checked.
- 5 with a semantic closure finding.
- 94 with informational-only findings (no test path cited -- often pre-dates this project's later per-row citation convention, not necessarily a real gap).
- 67 fully clean.
- Full detail: `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`.
