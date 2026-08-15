# Upstream issues — Aspose.Email FOSS for C++

Verified: 2026-08-02 against https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-Cpp

## No test-data or fixture files exist anywhere in the repo
- **Severity**: INFORMATIONAL
- **Evidence**: an exhaustive search of the cloned repository found no `.msg`/`.eml` or other sample files anywhere — only unrelated git-hook `.sample` files matched.
- **Impact**: a product-maturity gap rather than a functional defect; every documented example in this README was still verified end-to-end using fixtures generated via the library's own real "create" API rather than left unverified.
- **Not fixable here because**: shipping test fixtures is an upstream repository decision, not something a README edit controls.
