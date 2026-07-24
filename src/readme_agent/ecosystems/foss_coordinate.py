"""Canonical Aspose FOSS package coordinate per registry -- the "aspose {family} foss" rule.

Verified live 2026-07-24 against authoritative registries (see
plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/). The published FOSS
package is derived from the repository's *family + ecosystem*, and resolved against the
AUTHORITATIVE registry for that ecosystem:

  java   -> Maven Central   org.aspose:aspose-{family}-foss   (checked on repo1.maven.org)
  python -> PyPI            aspose-{family}-foss
  net    -> NuGet           Aspose.{Family}.FOSS
  cpp    -> NuGet           Aspose.{Family}.Cpp.FOSS           (C++ ships on NuGet, not Conan/vcpkg)
  typescript -> npm         aspose-{family}-foss
  go     -> Go proxy        github.com/{org}/{repo-lower}

It is NEVER the manifest's self-declared name (e.g. the npm placeholder ``excel-cells``) and NEVER
the similarly-named *commercial* package (``aspose.cells`` / ``aspose.cells.node`` /
``aspose.{family}.cpp`` without ``.foss``). When no FOSS package exists in that registry the honest
outcome is NOT_PUBLISHED -> source-build, which is correct, not a gap to paper over.
"""

from __future__ import annotations


def canonical_foss_coordinate(
    family: str,
    ecosystem: str,
    org: str | None = None,
    repo: str | None = None,
) -> tuple[str | None, dict[str, str]]:
    """Return ``(resolver_ecosystem, manifest)`` for ``ecosystems.resolver.resolve`` derived from
    the FOSS naming rule, or ``(None, {})`` when the ecosystem has no canonical FOSS coordinate.

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
    return None, {}
