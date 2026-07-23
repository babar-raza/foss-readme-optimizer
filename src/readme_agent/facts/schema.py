"""Wave 11.3 (`FACT-010`): a typed, honestly-scoped product-facts record --
deliberately NOT the full decision #22 field list (audience, problems
solved, capabilities, verified examples, docs, releases, support level,
maturity, maintenance state all remain unbuilt -- see the new `FACT-011`
`BACKLOG` row for exactly why, not a silent omission). This covers exactly
what `capabilities/get_product_facts.py` can genuinely derive today:
policy-declared identity/license/links/talking-points/block-policy, Wave
11.1's multi-root package graph (`ECO-004`), and Wave 11.2's live per-root
acquisition verification (`PKG-005`) when a caller supplies it.

`ProductFactsV1.from_capability_results()` is a pure, additive combining
function -- it does not call either capability itself (`get_product_facts`/
`verify_package_acquisition` stay independently dispatched, decision
#26(b)'s "one capability never reaches into another's dispatch path"), and
it does not change either capability's own declared output shape or
`side_effect_class`. `verify_package_acquisition`'s results are optional:
omitting them (the common case, since that capability makes real network
calls `get_product_facts` itself never has) still produces a complete
`ProductFactsV1`, just with `verification_outcome=None` per coordinate."""

from pydantic import BaseModel, Field


class PackageCoordinateFactV1(BaseModel):
    """One package root's claimed coordinates plus, when a caller supplied
    it, its live-verified acquisition status (Wave 11.2, `PKG-005`) -- the
    concrete, load-bearing evidence a future reconciliation phase (Wave
    12.1) needs to correct a README's own install-claim text against
    verified reality, closing the real `cells/java` failure mode (a
    known-false Maven coordinate shipped untouched in a real PR) this
    project's own sprint-plan Context section names."""

    path: str
    ecosystem: str
    manifest_path: str
    verification_outcome: str | None = None
    verification_detail: str | None = None


class ProductFactsV1(BaseModel):
    org_repo: str
    family: str | None = None
    platform: str | None = None
    ecosystem: str | None = None
    declared_license: str | None = None
    package_coordinates: list[PackageCoordinateFactV1] = Field(default_factory=list)
    relationship_talking_points: list[str] = Field(default_factory=list)
    secondary_links: list[dict] = Field(default_factory=list)
    unresolved_manifests: list[str] = Field(default_factory=list)

    @classmethod
    def from_capability_results(
        cls,
        facts_result: dict,
        *,
        acquisition_results: list[dict] | None = None,
    ) -> "ProductFactsV1":
        """`facts_result` is `capabilities/get_product_facts.py::execute()`'s
        own dict output (must include the additive Wave 11.3 `package_roots`
        key). `acquisition_results`, if given, is
        `capabilities/verify_package_acquisition.py::execute()`'s own
        `result["results"]` list for the SAME `org_repo` -- merged in by
        matching `path`, never assumed to cover every root."""
        acquisition_by_path = {r["path"]: r for r in (acquisition_results or [])}

        coordinates = []
        for root in facts_result.get("package_roots", []):
            acquisition = acquisition_by_path.get(root["path"])
            coordinates.append(
                PackageCoordinateFactV1(
                    path=root["path"],
                    ecosystem=root["ecosystem"],
                    manifest_path=root["manifest_path"],
                    verification_outcome=acquisition["outcome"] if acquisition else None,
                    verification_detail=acquisition["detail"] if acquisition else None,
                )
            )

        return cls(
            org_repo=facts_result["org_repo"],
            family=facts_result.get("family"),
            platform=facts_result.get("platform"),
            ecosystem=facts_result.get("ecosystem"),
            declared_license=facts_result.get("declared_license"),
            package_coordinates=coordinates,
            relationship_talking_points=facts_result.get("relationship_talking_points", []),
            secondary_links=facts_result.get("secondary_links", []),
            unresolved_manifests=facts_result.get("unresolved_manifests", []),
        )
