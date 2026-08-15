# Upstream issues — Aspose.Words FOSS for .NET

Verified: 2026-08-02 against https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-.NET

## Repo is unbuildable from a clean clone — missing NuGet package dependency
- **Severity**: BLOCKING (for contributors building from source only — see note below)
- **Evidence**: a genuinely fresh `git clone` followed by `dotnet build Aspose.Words.sln -c Release` fails with `NU1101`. Both `Aspose.Words.csproj` and `Aspose.Foundation.csproj` carry an unconditional `PackageReference` to `Aspose.EnumExtensionsGenerator` v1.0.2, which returns HTTP 404 from nuget.org's real v3-flatcontainer API (re-confirmed 2026-08-04) — this package has apparently never been published publicly.
- **Impact**: a contributor building from source to run the test suite hits this immediately. **Does not affect end users** — `Aspose.Words.FOSS` is genuinely published on nuget.org (v26.2.0, re-confirmed live 2026-08-04; repository field correctly points at this repo), so the README's Installation section now uses `dotnet add package` instead of a from-source build, sidestepping this defect entirely for consumers.
- **Not fixable here because**: the missing dependency reference lives in the upstream repo's own project files and NuGet publication state. The README's Development and testing section now documents the real workaround (comment out the `PackageReference`, build against the checked-in `Generated/**` fallback) for the contributor path that still needs it.
