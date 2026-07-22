"""Wave 8.7 (Item M): mechanically derives a policy profile for a registry
entry that has none yet, from fields the registry already carries plus one
live, per-repo fact (the detected license) -- never fabricated content.

Confirmed by diffing the 3 real, already-onboarded policy profiles
(`config/policies/aspose-3d-foss.yml`, `aspose-cells-foss.yml`,
`aspose-pdf-foss.yml`): `secondary_links`, `block.word_limit`,
`block.prohibited_terms`, `block.link_whitelist_domains`, and
`relationship_explained.talking_points` are org-wide constants, not
per-product content -- every existing profile uses the identical values.
`products_org_link`/`products_com_link`'s `url`/`family_url`/`label` fields
follow a mechanical pattern confirmed live against the real
products.aspose.org/products.aspose.com pages (2026-07-22): the URL
platform-slug is identical to the registry's own `platform` field for every
platform checked (java, net, python, cpp, typescript, go) -- no
per-platform translation table needed.

`detected_license` is the one genuinely per-repo fact -- deliberately not
defaulted or guessed here; the caller must supply it (see
`scripts/registry/generate_policy_profile.py`, which sources it from a live
GitHub repo-metadata lookup, the same signal `preflight/github_check.py::
check_repo()` already uses)."""

from __future__ import annotations

# Confirmed identical across all 3 existing real policy profiles
# (aspose-3d-foss, aspose-cells-foss, aspose-pdf-foss) -- org-wide policy,
# not per-product content.
SHARED_SECONDARY_LINKS = [
    "docs.aspose.org",
    "docs.aspose.com",
    "reference.aspose.com",
    "releases.aspose.com",
    "blog.aspose.org",
    "kb.aspose.org",
    "forum.aspose.com",
]

SHARED_WORD_LIMIT = {"min": 20, "max": 120}

SHARED_PROHIBITED_TERMS = [
    "guarantee",
    "100%",
    "best in the world",
    "free forever",
    "no bugs",
]

SHARED_LINK_WHITELIST_DOMAINS = [
    "products.aspose.com",
    "docs.aspose.com",
    "reference.aspose.com",
    "releases.aspose.com",
    "products.aspose.org",
    "docs.aspose.org",
    "kb.aspose.org",
    "blog.aspose.org",
    "forum.aspose.com",
]

SHARED_TALKING_POINTS = ["open_source_scope", "commercial_upgrade_path"]


def platform_label(repo_name: str) -> str:
    """The display-name suffix used in every existing profile's
    `products_org_link.label`/`products_com_link.label` (e.g. "Java",
    ".NET", "Cpp") -- derived directly from `repo_name`'s own `-for-<X>`
    suffix rather than a separate hand-maintained mapping, so it always
    matches whatever casing the real repo name actually uses (the registry
    is not internally consistent here -- e.g. `Aspose.Cells-FOSS-for-.NET`
    vs. `Aspose.Email-FOSS-for-.Net` -- and inventing a "corrected" casing
    would risk mismatching the real product name)."""
    return repo_name.rsplit("-for-", 1)[-1]


def generate_policy_profile(
    *,
    profile_name: str,
    family: str,
    family_name: str,
    platform: str,
    repo_name: str,
    detected_license: str,
) -> dict:
    """Returns a dict matching `registry/models.py::PolicyProfile`'s shape,
    ready to dump as YAML. Never writes a file itself -- see
    `scripts/registry/generate_policy_profile.py` for the CLI that does.

    `family_name` (e.g. "Aspose.Cells", "Aspose.3D") is the canonical
    display name already present in `data/families.json` -- deliberately
    NOT derived by capitalizing `family` (e.g. "3d") here, since that would
    produce "3d" (capitalize() doesn't uppercase a letter following a
    digit), not the real "Aspose.3D" every existing profile actually uses."""
    label_suffix = platform_label(repo_name)
    return {
        "schema_version": 2,
        "policy_profile": profile_name,
        "required_elements": {
            "license_mentioned": {"detected_license": detected_license},
            "products_org_link": {
                "url": f"https://products.aspose.org/{family}/{platform}/",
                "family_url": f"https://products.aspose.org/{family}/",
                "label": f"{family_name} FOSS for {label_suffix}",
            },
            "products_com_link": {
                "url": f"https://products.aspose.com/{family}/{platform}/",
                "family_url": f"https://products.aspose.com/{family}",
                "label": f"{family_name} for {label_suffix}",
                "utm": {
                    "utm_source": "github",
                    "utm_medium": "readme",
                    "utm_campaign": "foss-readme-optimizer",
                },
            },
            "relationship_explained": {
                "min_sentences": 2,
                "talking_points": list(SHARED_TALKING_POINTS),
            },
        },
        "secondary_links": list(SHARED_SECONDARY_LINKS),
        "block": {
            "word_limit": dict(SHARED_WORD_LIMIT),
            "prohibited_terms": list(SHARED_PROHIBITED_TERMS),
            "link_whitelist_domains": list(SHARED_LINK_WHITELIST_DOMAINS),
        },
    }
