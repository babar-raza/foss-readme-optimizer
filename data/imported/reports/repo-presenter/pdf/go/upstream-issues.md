# Upstream issues — Aspose.PDF FOSS for Go

Verified: 2026-08-02 against https://github.com/aspose-pdf-foss/Aspose-PDF-FOSS-for-Go

## "AI copilots" feature not present at the originally-pinned tag
- **Severity**: VERSION-DRIFT
- **Evidence**: the `ai` subpackage (~25 exported types) was not present at the originally-pinned `v0.5.0` tag — it was added roughly three weeks later, first appearing at `v0.6.0`. `go get module/ai@v0.5.0` fails with "module found, but does not contain package .../ai". Confirmed via `go list -m -versions` and direct `go get` attempts at both tags.
- **Impact**: version pinning for this fast-moving repo needs re-checking at every refresh — a feature documented as available may not exist yet at whatever tag happens to be current when a README is generated.
- **Not fixable here because**: it's a characteristic of this repo's release cadence, not a one-time README bug. (Already handled in this pass: retagged the Installation section to `v0.6.0` and re-verified all 13 code blocks against it.)
