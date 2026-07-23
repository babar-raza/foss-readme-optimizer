"""Wave 11.3 (`FACT-012`): a pure diff between two `ProductFactsV1`
snapshots (e.g. two successive supervised runs for the same `org_repo`) --
surfaces exactly which facts changed, so a caller never has to re-derive
"what's different" from two raw dicts by hand. Deliberately a plain
dataclass, not a durable `RunStateV1` field -- this is a computed,
point-in-time comparison, not something persisted for its own sake."""

from dataclasses import dataclass, field

from readme_agent.facts.schema import ProductFactsV1

_SCALAR_FIELDS = ("family", "platform", "ecosystem", "declared_license")


@dataclass
class ProductChangeSetV1:
    org_repo: str
    changed_fields: list[str] = field(default_factory=list)
    package_coordinate_changes: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_fields or self.package_coordinate_changes)


def diff_product_facts(before: ProductFactsV1, after: ProductFactsV1) -> ProductChangeSetV1:
    if before.org_repo != after.org_repo:
        raise ValueError(
            f"cannot diff ProductFactsV1 for different repos: "
            f"{before.org_repo!r} vs {after.org_repo!r}"
        )

    changed_fields = [
        field_name
        for field_name in _SCALAR_FIELDS
        if getattr(before, field_name) != getattr(after, field_name)
    ]

    before_by_path = {c.path: c for c in before.package_coordinates}
    after_by_path = {c.path: c for c in after.package_coordinates}

    coordinate_changes = []
    for path, after_coord in after_by_path.items():
        before_coord = before_by_path.get(path)
        if before_coord is None:
            coordinate_changes.append(f"{path}: new package root ({after_coord.ecosystem})")
        elif before_coord.verification_outcome != after_coord.verification_outcome:
            coordinate_changes.append(
                f"{path}: {before_coord.verification_outcome} -> {after_coord.verification_outcome}"
            )
    for path in before_by_path:
        if path not in after_by_path:
            coordinate_changes.append(f"{path}: package root no longer detected")

    return ProductChangeSetV1(
        org_repo=after.org_repo,
        changed_fields=changed_fields,
        package_coordinate_changes=coordinate_changes,
    )
