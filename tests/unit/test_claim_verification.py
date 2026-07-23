"""`RDM-024` (Wave 12.1): `find_claim_conflicts()` -- cross-checks README
install claims against Wave 11.3's live-verified `ProductFactsV1.
package_coordinates`. Read-only, no network -- `ProductFactsV1` is
constructed directly from plain data, matching this project's own
established capability-boundary test convention (no real dispatch)."""

from readme_agent.facts.schema import PackageCoordinateFactV1, ProductFactsV1
from readme_agent.readme.claim_verification import find_claim_conflicts

# The real, live-fetched README excerpt (2026-07-23) from
# aspose-cells-foss/Aspose.Cells-FOSS-for-Java's own `master` branch --
# the exact text the real PR (#1) shipped without correcting, confirmed
# live via `verify_package_acquisition` to resolve to `NOT_PUBLISHED` on
# Maven Central (`RDM-007`'s own already-recorded finding).
_REAL_CELLS_JAVA_INSTALL_EXCERPT = """## Installation

Add the following dependency to your `pom.xml`:

```xml
<dependency>
    <groupId>org.aspose</groupId>
    <artifactId>aspose-cells-foss</artifactId>
    <version>1.0.0</version>
</dependency>
```
"""


def _facts(**coord_overrides) -> ProductFactsV1:
    coord = PackageCoordinateFactV1(
        path=".",
        ecosystem="java",
        manifest_path="pom.xml",
        verification_outcome="NOT_PUBLISHED",
        verification_detail="Maven Central: org.aspose:aspose-cells-foss NOT FOUND (0 results)",
    )
    coord = coord.model_copy(update=coord_overrides)
    return ProductFactsV1(
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-Java", package_coordinates=[coord]
    )


class TestFindClaimConflictsRealRegression:
    """The named regression case: a real fixture reproducing the actual
    PR's exact starting state must produce a finding, not silence."""

    def test_real_cells_java_readme_produces_a_conflict_finding(self):
        facts = _facts()

        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)

        assert len(findings) == 1
        finding = findings[0]
        assert finding.claimed_coordinate == "org.aspose:aspose-cells-foss"
        assert finding.ecosystem == "java"
        assert finding.verification_outcome == "NOT_PUBLISHED"
        assert "aspose-cells-foss" in finding.readme_excerpt


class TestFindClaimConflictsGuards:
    def test_registry_verified_never_produces_a_finding(self):
        facts = _facts(verification_outcome="REGISTRY_VERIFIED", verification_detail="found")
        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)
        assert findings == []

    def test_capability_gap_never_produces_a_finding(self):
        """A capability gap means "couldn't check," never a confirmed
        false claim -- must not be treated as evidence of one."""
        facts = _facts(verification_outcome="CAPABILITY_GAP", verification_detail="no resolver")
        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)
        assert findings == []

    def test_blocked_network_never_produces_a_finding(self):
        facts = _facts(verification_outcome="BLOCKED_NETWORK", verification_detail="timeout")
        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)
        assert findings == []

    def test_none_outcome_never_produces_a_finding(self):
        facts = _facts(verification_outcome=None, verification_detail=None)
        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)
        assert findings == []

    def test_no_readme_claim_at_all_produces_no_finding(self):
        facts = _facts()
        findings = find_claim_conflicts("# Widget\n\nNo install section here.\n", facts)
        assert findings == []

    def test_no_package_coordinates_produces_no_finding(self):
        facts = ProductFactsV1(org_repo="acme/widget")
        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)
        assert findings == []


class TestFindClaimConflictsOtherEcosystems:
    def test_python_pip_install_claim(self):
        facts = _facts(ecosystem="python", manifest_path="pyproject.toml", path=".")
        readme = "Install via `pip install aspose-cells-foss`.\n"
        findings = find_claim_conflicts(readme, facts)
        assert len(findings) == 1
        assert findings[0].claimed_coordinate == "aspose-cells-foss"

    def test_npm_install_claim(self):
        facts = _facts(ecosystem="typescript", manifest_path="package.json", path=".")
        readme = "```\nnpm install @aspose/cells-foss\n```\n"
        findings = find_claim_conflicts(readme, facts)
        assert len(findings) == 1
        assert findings[0].claimed_coordinate == "@aspose/cells-foss"

    def test_nuget_install_claim(self):
        facts = _facts(ecosystem="net", manifest_path="Widget.csproj", path=".")
        readme = "Run `dotnet add package Aspose.Cells.Foss` to install.\n"
        findings = find_claim_conflicts(readme, facts)
        assert len(findings) == 1
        assert findings[0].claimed_coordinate == "Aspose.Cells.Foss"

    def test_unresolvable_ecosystem_produces_no_finding(self):
        """`cpp` deliberately has no resolvable single registry (`PKG-004`)
        -- there should never be a `NOT_PUBLISHED` cpp coordinate to check
        in the first place, but this proves the claim-matcher itself
        degrades safely (empty) rather than guessing a pattern."""
        facts = _facts(ecosystem="cpp", manifest_path="CMakeLists.txt", path=".")
        readme = "Build with CMake and link against the library.\n"
        findings = find_claim_conflicts(readme, facts)
        assert findings == []


class TestFindClaimConflictsMultiRoot:
    def test_only_the_conflicting_root_produces_a_finding(self):
        """Wave 11.1's multi-root awareness carried through: a second,
        correctly-resolving root must never be flagged just because a
        sibling root's claim is false."""
        broken = PackageCoordinateFactV1(
            path="module-a",
            ecosystem="java",
            manifest_path="module-a/pom.xml",
            verification_outcome="NOT_PUBLISHED",
            verification_detail="Maven Central: org.aspose:aspose-cells-foss NOT FOUND (0 results)",
        )
        working = PackageCoordinateFactV1(
            path="module-b",
            ecosystem="java",
            manifest_path="module-b/pom.xml",
            verification_outcome="REGISTRY_VERIFIED",
            verification_detail="Maven Central: org.aspose:aspose-cells-cli found",
        )
        facts = ProductFactsV1(org_repo="acme/widget", package_coordinates=[broken, working])

        findings = find_claim_conflicts(_REAL_CELLS_JAVA_INSTALL_EXCERPT, facts)

        assert len(findings) == 1
        assert findings[0].package_root_path == "module-a"
