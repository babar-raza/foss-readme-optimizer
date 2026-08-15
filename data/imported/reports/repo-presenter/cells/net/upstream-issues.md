# Upstream issues — Aspose.Cells FOSS for .NET

Verified: 2026-08-02 against https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-.NET

## Source .csproj version tag lags the actually-published NuGet version
- **Severity**: INFORMATIONAL
- **Evidence**: the cloned source's `.csproj` internally declares `<Version>26.6.0.0</Version>`, while the actually-published, live NuGet package resolves to `26.7.0` — one release ahead of what's committed to source. Confirmed by comparing the real csproj against a live NuGet resolve.
- **Impact**: none for end users (this README correctly documents the live-published 26.7.0); only relevant to someone inspecting the source directly and expecting the version tag to match what's live.
- **Not fixable here because**: it's a characteristic of the upstream release pipeline (the version bump happens outside the source commit), not this README.
