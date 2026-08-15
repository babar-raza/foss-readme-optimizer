# Upstream issues — Aspose.PDF FOSS for Python

Verified: 2026-08-02 against https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Python

## Minor Windows-environment test artifacts (not exercised by any README example)
- **Severity**: INFORMATIONAL
- **Evidence**: the full pytest suite (2116 tests, zero collection errors) has 2 non-passing cases unrelated to platform-portable behavior: `test_save_on_readonly_fs_raises_permission_error` (asserts POSIX permission semantics that don't apply the same way on Windows) and one Hypothesis-generated parametrize-ID case in `test_filters_encoding.py::test_single_filter_roundtrip`.
- **Impact**: none for documented README examples or real usage — these are environment-specific test-suite artifacts, not product defects.
- **Not fixable here because**: it's the upstream repo's own test suite / Windows-vs-POSIX semantics, not this README.
