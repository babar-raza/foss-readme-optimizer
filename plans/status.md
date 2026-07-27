# Project status (generated -- do not hand-edit)

Regenerate with `python plans/investigations/tools/traceability_matrix.py`. This replaces `plans/master.md`'s old hand-maintained Status section (Wave 9.3, 2026-07-22) -- see `plans/roadmap.md` for what's next and `logs/` for the dated history.

**Latest Decision Ledger entry**: #80

## Full-registry README POC status

**Primary status measure (sprint charter Part B.2 Phase 5 Lane S).** Every `data/products.json` entry, counted live at generation time (never hard-coded), with its current `readme_poc_status` (RPOC-070 lifecycle vocabulary -- `src/readme_agent/state/lifecycle_schema.py::ReadmePocStatusV1`). Test counts, capability counts, plan closure, and three-pilot status are NOT the measure here; the requirement-status and Build Checklist sections below remain as supporting governance detail, not the headline.

Source manifest: `plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/portfolio-proof-manifest.json` (generated_at: 2026-07-25T02:55:29.666916+00:00).

`not yet run` = absent from the source manifest entirely (e.g. the 3 Java pilots, proven through their own dedicated evidence path, or any registry entry newer than the last portfolio run). `not_set` = present in the manifest but the RPOC-070 lifecycle field has not been populated by a real run yet -- expected for most repos today, since that field is brand new.

| Org/Repo | Ecosystem | Mode | README POC status |
|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | net | dry_run | not_set |
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | java | full | not yet run |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | python | dry_run | not_set |
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | typescript | dry_run | not_set |
| aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python | python | dry_run | not_set |
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | net | dry_run | not_set |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | cpp | dry_run | not_set |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | go | dry_run | not_set |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | java | full | not yet run |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Python | python | dry_run | not_set |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Rust | rust | dry_run | not_set |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | typescript | dry_run | not_set |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | net | dry_run | not_set |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp | cpp | dry_run | not_set |
| aspose-email-foss/Aspose.Email-FOSS-for-Python | python | dry_run | not_set |
| aspose-font-foss/Aspose.Font-FOSS-for-Python | python | dry_run | not_set |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | python | dry_run | not_set |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | python | dry_run | not_set |
| aspose-page-foss/Aspose.Page-FOSS-for-Python | python | dry_run | not_set |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | go | dry_run | not_set |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | python | dry_run | not_set |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET | net | dry_run | not_set |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | cpp | dry_run | not_set |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | java | dry_run | not yet run |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | net | dry_run | not_set |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | cpp | dry_run | not_set |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | java | dry_run | not_set |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | python | dry_run | not_set |
| aspose-tex-foss/Aspose.TeX-FOSS-for-Python | python | dry_run | not_set |
| aspose-words-foss/Aspose.Words-FOSS-for-.NET | net | dry_run | not_set |
| aspose-words-foss/Aspose.Words-FOSS-for-Python | python | dry_run | not_set |

- 31 total registry entries (live count from `data/products.json`).
- 3 not yet run (absent from the manifest).
- 28 present in the manifest but lifecycle status not yet set.
- 0 with a real RPOC-070 lifecycle status recorded.

## Requirement status counts (supporting detail -- see the Full-registry table above for the primary measure)

| Status | Count |
|---|---:|
| IMPLEMENTED | 154 |
| PLANNED | 123 |
| PARTIAL | 82 |
| GOVERNANCE | 34 |
| BACKLOG | 26 |
| RESEARCH-GATED | 6 |

## Build Checklist wave state


## Implementation-truth matrix summary (Wave 9.2)

- 154 `IMPLEMENTED` rows checked.
- 0 with a semantic closure finding.
- 83 with informational-only findings (no test path cited -- often pre-dates this project's later per-row citation convention, not necessarily a real gap).
- 71 fully clean.
- Full detail: `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`.
