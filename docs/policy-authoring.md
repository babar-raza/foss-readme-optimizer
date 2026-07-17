# Adding a repo / a new policy profile

## Enabling an already-listed repo

Every real Aspose FOSS repo is already present in `data/products.json` (copied verbatim from
Aspose's own registry) with `mode: "disabled"`. To enable one:

1. Confirm `GH_TOKEN` has read access: `gh api repos/{org}/{repo}`.
2. Author `config/policies/<policy_profile>.yml` (see shape below) — the `products_org_link`/
   `products_com_link` URLs should follow the pattern already used by the fully-compliant
   `aspose-3d-foss` profile (`products.aspose.org/{family}/{platform}/`,
   `products.aspose.com/{family}/{platform}/`).
3. In `data/products.json`, flip that entry's `mode` to `"dry_run"` (recommended first) and set
   `ecosystem` (only `"maven"` is implemented today — see `ecosystems/registry.py`) and
   `policy_profile` to match the file from step 2.
4. Run `readme-agent inspect --repo {org}/{repo}` to confirm the clone + manifest parse works.
5. Run `readme-agent generate --repo {org}/{repo}` (defaults to live LLM) and review the rendered
   spans by hand before ever setting `mode: "full"`.

## Policy file shape

```yaml
schema_version: 2
policy_profile: <matches the filename, without .yml>
required_elements:
  license_mentioned:
    detected_license: MIT   # ground truth; never invented -- see license/auditor.py
  products_org_link:
    url: "https://products.aspose.org/<family>/<platform>/"
    family_url: "https://products.aspose.org/<family>/"
    label: "<Product> FOSS for <Platform>"
  products_com_link:
    url: "https://products.aspose.com/<family>/<platform>/"
    family_url: "https://products.aspose.com/<family>"
    label: "<Product> for <Platform>"
    utm: { utm_source: github, utm_medium: readme, utm_campaign: foss-readme-optimizer }
  relationship_explained:
    min_sentences: 2
    talking_points: [open_source_scope, commercial_upgrade_path]
secondary_links: [docs.aspose.org, docs.aspose.com, ...]   # tracked, never a hard gate
block:
  word_limit: { min: 20, max: 120 }
  prohibited_terms: ["guarantee", "100%", "best in the world", "free forever", "no bugs"]
  link_whitelist_domains: [products.aspose.com, docs.aspose.com, ...]
```

**Why one file per product, not one shared file per org**: promotional links are inherently
per-product (3D vs Cells vs PDF each point somewhere different). `block`/`secondary_links`
boilerplate duplication across profiles is accepted debt, not worth a config-inheritance system at
today's scale (3 profiles) — revisit if a 4th+ product family makes the duplication a real
maintenance cost.

## Onboarding a genuinely new (non-Aspose) org

The engine itself has zero Aspose-specific logic — `gap_detector.py`'s domain checks are generic
(`products\.[a-z0-9-]+\.(org|com)`, not hardcoded to "aspose"). A new org needs: new
`data/products.json` entries (any schema-valid entries, not just Aspose's), a new policy profile
per product following the shape above, and nothing else — no code changes.
