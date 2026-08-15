# Upstream issues — Aspose.Slides FOSS for Java

Verified: 2026-08-02 against https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Java

## Presentation.save() silently ignores the format parameter for non-PPTX targets
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `save("test.pdf", SaveFormat.PDF)` and `save("test.html", SaveFormat.HTML)` both return normally with no exception, but the output files start with the ZIP signature `PK\x03\x04` and contain `[Content_Types].xml` — i.e. they are still real PPTX/OOXML packages, just written under a different filename/extension. Confirmed by direct byte inspection of the output.
- **Impact**: a user requesting PDF/HTML export via `save()` silently gets a mislabeled PPTX file instead of the requested format or an error.
- **Not fixable here because**: it's the published library's `save()` implementation, not the README. (This README's Scope and limitations section previously noted these formats aren't exported, but didn't warn that the failure mode is silent rather than an exception — now made explicit.)
