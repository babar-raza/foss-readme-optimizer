# Package-acquisition ground truth (all 31 products.json entries)

Generated 2026-07-24T15:39:26.089652+00:00.

Rule: aspose {family} foss against the authoritative registry per ecosystem; Maven uses repo1.maven.org (not search.maven.org); cpp uses NuGet; never the manifest name, never the commercial package

**13 published, 13 not published, 5 excluded (disabled entries).**

Each row verified by a direct HTTP GET against that ecosystem's AUTHORITATIVE registry (Maven uses `repo1.maven.org`, NOT `search.maven.org`). This is the regression baseline the corrected resolver must match. Reproduce via `reproduction-command.txt`.

| org_repo | ecosystem | mode | coordinate | HTTP | verdict |
|---|---|---|---|---|---|
| aspose-3d-foss/Aspose.3D-FOSS-for-Java | java | full | org.aspose:aspose-3d-foss | 200 | PUBLISHED |
| aspose-3d-foss/Aspose.3D-FOSS-for-.NET | net | dry_run | Aspose.3d.FOSS (NuGet) | 200 | PUBLISHED |
| aspose-3d-foss/Aspose.3D-FOSS-for-Python | python | dry_run | aspose-3d-foss (PyPI) | 404 | NOT_PUBLISHED |
| aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript | typescript | dry_run | aspose-3d-foss (npm) | 404 | NOT_PUBLISHED |
| aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python | python | dry_run | aspose-barcode-foss (PyPI) | 404 | NOT_PUBLISHED |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp | cpp | dry_run | Aspose.cells.Cpp.FOSS (NuGet) | 200 | PUBLISHED |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Go | - | disabled | - | - | excluded |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Java | java | full | org.aspose:aspose-cells-foss | 200 | PUBLISHED |
| aspose-cells-foss/Aspose.Cells-FOSS-for-.NET | net | dry_run | Aspose.cells.FOSS (NuGet) | 200 | PUBLISHED |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Python | python | dry_run | aspose-cells-foss (PyPI) | 200 | PUBLISHED |
| aspose-cells-foss/Aspose.Cells-FOSS-for-Rust | - | disabled | - | - | excluded |
| aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript | typescript | dry_run | aspose-cells-foss (npm) | 404 | NOT_PUBLISHED |
| aspose-email-foss/Aspose.Email-FOSS-for-Cpp | cpp | dry_run | Aspose.email.Cpp.FOSS (NuGet) | 404 | NOT_PUBLISHED |
| aspose-email-foss/Aspose.Email-FOSS-for-.Net | net | dry_run | Aspose.email.FOSS (NuGet) | 200 | PUBLISHED |
| aspose-email-foss/Aspose.Email-FOSS-for-Python | python | dry_run | aspose-email-foss (PyPI) | 200 | PUBLISHED |
| aspose-font-foss/Aspose.Font-FOSS-for-Python | python | dry_run | aspose-font-foss (PyPI) | 404 | NOT_PUBLISHED |
| aspose-html-foss/Aspose.HTML-FOSS-for-Python | - | disabled | - | - | excluded |
| aspose-note-foss/Aspose.Note-FOSS-for-Python | python | dry_run | aspose-note-foss (PyPI) | 404 | NOT_PUBLISHED |
| aspose-page-foss/Aspose.Page-FOSS-for-Python | python | dry_run | aspose-page-foss (PyPI) | 404 | NOT_PUBLISHED |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp | - | disabled | - | - | excluded |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Go | go | dry_run | github.com/aspose-pdf-foss/aspose-pdf-foss-for-go (Go proxy) | 200 | PUBLISHED |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-Java | java | dry_run | org.aspose:aspose-pdf-foss | 200 | PUBLISHED |
| aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET | net | dry_run | Aspose.pdf.FOSS (NuGet) | 200 | PUBLISHED |
| aspose-pdf-foss/Aspose-PDF-FOSS-for-Python | - | disabled | - | - | excluded |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Cpp | cpp | dry_run | Aspose.slides.Cpp.FOSS (NuGet) | 404 | NOT_PUBLISHED |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Java | java | dry_run | org.aspose:aspose-slides-foss | 404 | NOT_PUBLISHED |
| aspose-slides-foss/Aspose.Slides-FOSS-for-.NET | net | dry_run | Aspose.slides.FOSS (NuGet) | 404 | NOT_PUBLISHED |
| aspose-slides-foss/Aspose.Slides-FOSS-for-Python | python | dry_run | aspose-slides-foss (PyPI) | 200 | PUBLISHED |
| aspose-tex-foss/Aspose.TeX-FOSS-for-Python | python | dry_run | aspose-tex-foss (PyPI) | 404 | NOT_PUBLISHED |
| aspose-words-foss/Aspose.Words-FOSS-for-.NET | net | dry_run | Aspose.words.FOSS (NuGet) | 404 | NOT_PUBLISHED |
| aspose-words-foss/Aspose.Words-FOSS-for-Python | python | dry_run | aspose-words-foss (PyPI) | 200 | PUBLISHED |

## Key finding

The old Maven resolver queried `search.maven.org` (Solr), which returns 0 results for the entire `org.aspose` group, so it falsely reported the three published Java packages (3d/cells/pdf) as NOT_PUBLISHED. `slides-java` is genuinely not published yet (404 on `repo1.maven.org` too). C++ ships on NuGet (`aspose.cells.cpp.foss` is published), not Conan/vcpkg. npm has no FOSS package today (the commercial `aspose.cells` is NOT the FOSS product and must never be substituted). Reality is genuinely mixed per package -- 13 of 26 resolvable entries are published -- so each must be verified against its own registry.

