# Upstream issues — Aspose.Cells FOSS for Go

Verified: 2026-08-02 against https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Go

## examples/go.mod has an invalid version string, breaking the repo's own example runner
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `examples/go.mod` declares `require .../v26 v0.0.0` — an invalid version string for a `/v26` major-version module path. This fails to parse on Go 1.26.4, breaking the upstream repo's own documented `cd examples && for d in */; do go run ./$d; done` loop for every single example.
- **Impact**: contributors following the upstream repo's own example-running instructions hit an immediate failure.
- **Not fixable here because**: `examples/go.mod` is the upstream repo's own file, not this README.

## Upstream repo's own README claims a golang.org/x/crypto dependency that doesn't exist
- **Severity**: INFORMATIONAL
- **Evidence**: the real `go.mod` declares zero `require` entries (pure stdlib) and `go.sum` is empty — confirmed directly, not assumed. The upstream repo's own top-level README mentions a `golang.org/x/crypto` dependency that isn't actually present anywhere.
- **Impact**: none for actual usage (our generated README correctly uses the verified zero-dependency `go.mod` truth instead), but worth flagging as a stale claim in the upstream repo's own docs.
- **Not fixable here because**: it's the upstream repo's own README, not this one.
