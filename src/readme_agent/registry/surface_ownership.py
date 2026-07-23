"""Policy-level ownership classes and allowed operations for visible surfaces."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SurfaceOwnershipClass = Literal[
    "repository_file",
    "settings_api",
    "manual_ui",
    "product_owned",
    "github_generated",
]
SurfaceOperation = Literal["audit", "propose", "local_patch", "remote_apply", "manual_apply"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SurfaceOwnershipRuleV1(_StrictModel):
    surface_id: str
    ownership_class: SurfaceOwnershipClass
    authoritative_owner: str
    allowed_operations: list[SurfaceOperation] = Field(min_length=1)
    required_permission: str
    rollback: str


class SurfaceOwnershipMapV1(_StrictModel):
    schema_version: Literal[1] = 1
    surfaces: list[SurfaceOwnershipRuleV1]

    @model_validator(mode="after")
    def _unique_surfaces(self) -> SurfaceOwnershipMapV1:
        ids = [surface.surface_id for surface in self.surfaces]
        if len(set(ids)) != len(ids):
            raise ValueError("surface ownership map contains duplicate surface_id values")
        return self

    def rule_for(self, surface_id: str) -> SurfaceOwnershipRuleV1:
        for rule in self.surfaces:
            if rule.surface_id == surface_id:
                return rule
        raise KeyError(surface_id)


def _rules(
    surface_ids: tuple[str, ...],
    ownership_class: SurfaceOwnershipClass,
    owner: str,
    operations: list[SurfaceOperation],
    permission: str,
    rollback: str,
) -> list[SurfaceOwnershipRuleV1]:
    return [
        SurfaceOwnershipRuleV1(
            surface_id=surface_id,
            ownership_class=ownership_class,
            authoritative_owner=owner,
            allowed_operations=operations,
            required_permission=permission,
            rollback=rollback,
        )
        for surface_id in surface_ids
    ]


def default_surface_ownership_map() -> SurfaceOwnershipMapV1:
    """Return decision #19's complete, policy-visible five-class inventory."""

    repository_files = (
        "readme",
        "readme_visual",
        "license",
        "contributing",
        "code_of_conduct",
        "security",
        "support",
        "issue_templates",
        "pull_request_templates",
    )
    settings = ("description", "homepage", "topics", "feature_settings")
    product_owned = ("releases", "packages", "release_package_facts")
    generated = (
        "contributors",
        "languages",
        "repository_signals",
        "page_layout",
    )
    return SurfaceOwnershipMapV1(
        surfaces=[
            *_rules(
                repository_files,
                "repository_file",
                "repository-owner",
                ["audit", "propose", "local_patch"],
                "local_write",
                "revert the bounded file patch",
            ),
            *_rules(
                settings,
                "settings_api",
                "repository-settings-owner",
                ["audit", "propose", "remote_apply"],
                "github_apply",
                "restore the recorded prior setting value",
            ),
            *_rules(
                ("social_preview",),
                "manual_ui",
                "repository-settings-owner",
                ["audit", "propose", "manual_apply"],
                "manual_ui",
                "operator restores the prior asset through the UI",
            ),
            *_rules(
                product_owned,
                "product_owned",
                "product-owner",
                ["audit"],
                "read_only_network",
                "not applicable: this system has no write operation",
            ),
            *_rules(
                generated,
                "github_generated",
                "github",
                ["audit"],
                "read_only_network",
                "not applicable: this system has no write operation",
            ),
        ]
    )


def operation_allowed(
    ownership: SurfaceOwnershipMapV1, surface_id: str, operation: SurfaceOperation
) -> bool:
    try:
        rule = ownership.rule_for(surface_id)
    except KeyError:
        return False
    return operation in rule.allowed_operations
