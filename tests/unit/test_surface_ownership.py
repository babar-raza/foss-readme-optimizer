"""Policy-visible five-class surface ownership and operation gates."""

from readme_agent.registry.models import PolicyProfile
from readme_agent.registry.surface_ownership import (
    default_surface_ownership_map,
    operation_allowed,
)


def test_default_map_contains_exactly_the_five_governed_classes():
    ownership = default_surface_ownership_map()
    assert {rule.ownership_class for rule in ownership.surfaces} == {
        "repository_file",
        "settings_api",
        "manual_ui",
        "product_owned",
        "github_generated",
    }


def test_product_owned_and_generated_surfaces_are_audit_only():
    ownership = default_surface_ownership_map()
    for surface_id in ("releases", "packages", "contributors", "languages"):
        assert operation_allowed(ownership, surface_id, "audit")
        assert not operation_allowed(ownership, surface_id, "propose")
        assert not operation_allowed(ownership, surface_id, "remote_apply")


def test_settings_and_manual_ui_use_distinct_apply_modes():
    ownership = default_surface_ownership_map()
    assert operation_allowed(ownership, "description", "remote_apply")
    assert not operation_allowed(ownership, "description", "manual_apply")
    assert operation_allowed(ownership, "social_preview", "manual_apply")
    assert not operation_allowed(ownership, "social_preview", "remote_apply")


def test_unknown_surface_fails_closed():
    assert not operation_allowed(default_surface_ownership_map(), "unknown", "audit")


def test_policy_schema_materializes_the_ownership_map_without_yaml_duplication():
    policy = PolicyProfile.model_validate(
        {
            "schema_version": 2,
            "policy_profile": "test",
            "required_elements": {
                "license_mentioned": {"detected_license": "MIT"},
                "products_org_link": {
                    "url": "https://example.test/open",
                    "family_url": "https://example.test",
                    "label": "Open",
                },
                "products_com_link": {
                    "url": "https://example.test/commercial",
                    "family_url": "https://example.test",
                    "label": "Commercial",
                },
                "relationship_explained": {"talking_points": []},
            },
            "block": {
                "word_limit": {"min": 1, "max": 100},
                "prohibited_terms": [],
                "link_whitelist_domains": ["example.test"],
            },
        }
    )

    assert policy.surface_ownership.rule_for("readme").ownership_class == "repository_file"
