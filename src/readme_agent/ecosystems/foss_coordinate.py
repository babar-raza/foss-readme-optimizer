"""Fallback Aspose FOSS package coordinate per registry.

Verified live 2026-07-24 against authoritative registries (see
plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/). Acquisition first
verifies a complete coordinate from the selected product manifest. This module supplies the
portfolio naming convention when that coordinate is absent or unpublished:

  java   -> Maven Central   org.aspose:aspose-{family}-foss   (checked on repo1.maven.org)
  python -> PyPI            aspose-{family}-foss
  net    -> NuGet           Aspose.{Family}.FOSS
  cpp    -> NuGet           Aspose.{Family}.Cpp.FOSS           (C++ ships on NuGet, not Conan/vcpkg)
  typescript -> npm         aspose-{family}-foss
  go     -> Go proxy        github.com/{org}/{repo-lower}
  rust   -> crates.io       aspose-{family}-foss

The registry check prevents an unpublished placeholder from becoming an installation claim.
Commercial-package exclusion remains a claim-validation concern. When neither the repository
coordinate nor this fallback is published, the honest outcome is NOT_PUBLISHED -> source-build.
"""

from __future__ import annotations


def canonical_foss_coordinate(
    family: str,
    ecosystem: str,
    org: str | None = None,
    repo: str | None = None,
) -> tuple[str | None, dict[str, str]]:
    """Return the convention-derived fallback for ``ecosystems.resolver.resolve``.

    ``resolver_ecosystem`` may differ from ``ecosystem``: C++ resolves via the ``net`` (NuGet)
    resolver because the Aspose C++ FOSS packages ship on NuGet.
    """
    fam = family.lower()
    if ecosystem == "java":
        return "java", {"group_id": "org.aspose", "artifact_id": f"aspose-{fam}-foss"}
    if ecosystem == "python":
        return "python", {"name": f"aspose-{fam}-foss"}
    if ecosystem == "net":
        return "net", {"name": f"Aspose.{fam}.FOSS"}
    if ecosystem == "cpp":
        return "net", {"name": f"Aspose.{fam}.Cpp.FOSS"}
    if ecosystem == "typescript":
        return "typescript", {"name": f"aspose-{fam}-foss"}
    if ecosystem == "go" and org and repo:
        return "go", {"name": f"github.com/{org}/{repo.lower()}"}
    if ecosystem == "rust":
        return "rust", {"name": f"aspose-{fam}-foss"}
    return None, {}
