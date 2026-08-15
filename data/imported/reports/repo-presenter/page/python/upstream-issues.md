# Upstream issues — Aspose.Page FOSS for Python

Verified: 2026-08-02 against https://github.com/aspose-page-foss/Aspose.Page-FOSS-for-Python

## Circular import when xps.document or pdf.writer is imported first
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: importing `aspose.page.xps.document` or `aspose.page.pdf.writer` as the first `aspose.page.*` import in a fresh interpreter raises `ImportError: cannot import name '_contours_to_path' from partially initialized module 'aspose.page.image.raster_renderer' (most likely due to a circular import)`, reproduced deterministically both times.
- **Impact**: any user who imports these modules first (rather than in the order the README happens to use) hits an import failure.
- **Not fixable here because**: the circular dependency is in the package's own module graph. Worked around in this README by pre-importing `aspose.page.ps` first, which resolves the module graph before the circular path is hit — a legitimate real fix for README purposes, but the underlying defect remains in the library.

## Pre-existing failures in the low-level PS interpreter's own test suite
- **Severity**: INFORMATIONAL
- **Evidence**: the full `make test` suite (737 tests) shows 6 failures + 4 errors in low-level PS interpreter internals (stack save/restore, array parsing, charpath).
- **Impact**: none for documented README examples — these are pre-existing internal edge cases not exercised by any documented block.
- **Not fixable here because**: it's the upstream repo's own test suite.
