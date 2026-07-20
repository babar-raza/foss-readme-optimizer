# `data/` — registry and link-database files

This directory holds the config-as-data files that drive the agent: the registry
(`products.json`, `families.json`) and the verified link database (`aspose_com_links.json`). All
three are plain JSON so they can be read, diffed, and reviewed without running any code. Read
`AGENTS.md`, `docs/safety-model.md`, and `docs/policy-authoring.md` before editing any of them by
hand.

## `data/products.json` — the allow-list (safety-critical)

The **only** list of repos this tool is ever permitted to touch. Every entry point that accepts a
repo argument calls `registry.loader.is_permitted()` **before** any network or git operation
(`docs/safety-model.md`, safety property 2). A repo that is missing from this file, or present
with `mode: "disabled"`, is a hard `NotAllowlistedError` — no clone is attempted.

Each entry:

```json
{
  "family": "cells", "platform": "java", "repo_name": "Aspose.Cells-FOSS-for-Java",
  "repo_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
  "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.git",
  "active": true, "discovered_via": "github",
  "mode": "full", "ecosystem": "maven", "policy_profile": "aspose-cells-foss"
}
```

Two field groups, owned differently:

- **Upstream-shaped** (`family`, `platform`, `repo_name`, `repo_url`, `clone_url`, `active`,
  `discovered_via`, `overrides`) — describe the repo as GitHub reports it. Safe to refresh from a
  live scan.
- **Agent-owned** (`mode`, `ecosystem`, `policy_profile`) — decide whether this project is allowed
  to *act* on the repo. `mode` is `"full"` / `"dry_run"` / `"disabled"`. These fields are **never**
  set by automation — only by a human editing this file, following
  [`docs/policy-authoring.md`](../docs/policy-authoring.md). A repo appearing in this file, even
  with real upstream data, grants **zero** permission until a human explicitly sets a non-`disabled`
  `mode`.

**For agents (human or AI) working in this repo**: never flip `mode` away from `"disabled"` as a
side effect of a registry refresh, a bug fix, or "cleaning up" the file. That decision requires the
policy-authoring steps (policy profile file, `ecosystem`, manual review) — see
[`docs/policy-authoring.md`](../docs/policy-authoring.md).

## `data/families.json` — the discovery seed list

Lists every Aspose FOSS family and the GitHub organization that hosts its per-platform repos —
`aspose-{family}-foss`, one org per family, 26 total. This is **not** an allow-list; being listed
here grants no permission to touch anything. It only tells the discovery script *where to look*.

```json
{ "family": "cells", "name": "Aspose.Cells", "github_org": "aspose-cells-foss" }
```

## How `data/products.json` stays current

[`scripts/update_products_registry.py`](../scripts/update_products_registry.py) scans every
GitHub org in `families.json` (read-only `GET` calls against the GitHub REST API), classifies
each public repo by its `Aspose.{Family}-FOSS-for-{Platform}` naming convention, and merges the
result into `data/products.json`:

- Newly discovered `(family, platform)` pairs are added with `mode: "disabled"`,
  `ecosystem: null`, `policy_profile: null` — never auto-enabled.
- Existing entries only have their upstream-shaped fields refreshed (e.g. a renamed repo or a
  newly archived one); `mode`/`ecosystem`/`policy_profile` are left untouched no matter what.
- No entry is ever deleted, even if a repo disappears from GitHub — that's a human decision.
- The write is atomic (temp file + rename).

Run it yourself:

```bash
python scripts/update_products_registry.py --dry-run     # preview, no write
python scripts/update_products_registry.py                # scan every org, write data/products.json
python scripts/update_products_registry.py --org aspose-pdf-foss   # scan one org
```

`GH_TOKEN` / `GITHUB_PAT` (same precedence as the rest of the project, see `.env.example`) raises
the GitHub API rate limit; the script also works unauthenticated (60 requests/hour).

### Scheduled automation

[`.github/workflows/update-products-registry.yml`](../.github/workflows/update-products-registry.yml)
runs the script weekly (plus `workflow_dispatch` for a manual run) and, if `data/products.json`
changed, opens a pull request — it never pushes straight to `main`. Merging that PR only updates
the upstream-shaped fields and/or adds new `disabled` entries; it can never by itself make a repo
operable.

**Local test** (this repo already has `.actrc` / `.env.act.example` set up for
[`act`](https://github.com/nektos/act), which simulates a GitHub Actions runner locally in
Docker — no runner registration needed):

```bash
act workflow_dispatch -W .github/workflows/update-products-registry.yml
```

## `data/aspose_com_links.json` — the verified aspose.com link database

A database of **known-valid** `aspose.com` URLs, at exactly the two depths this project ever
links to — family (`products.aspose.com/words/`) and platform
(`products.aspose.com/words/python-net/`) — for the four content surfaces `products`, `docs`,
`reference`, `kb.aspose.com`, plus `blog.aspose.com` category-root URLs (the blog has no
family/platform landing pages, so its canonical page per category is derived separately, see
below). This exists so the renderer never has to *guess* or *construct* a `products.*.com` link —
it looks one up here and checks `http_status`.

```json
{
  "schema_version": "1.0",
  "provenance": { "generated_at": "...", "generator": "fetch_aspose_com_links.py", "mode": "live|from-source", "sources": [...], "total_links": 293, "output_hash": "sha256:..." },
  "surfaces": {
    "products.aspose.com": {
      "families": { "words": { "url": "https://products.aspose.com/words/", "http_status": 200 } },
      "platforms": { "words/python-net": { "url": "https://products.aspose.com/words/python-net/", "http_status": 200 } }
    },
    "docs.aspose.com": { "...": "..." },
    "reference.aspose.com": { "...": "..." },
    "kb.aspose.com": { "...": "..." }
  },
  "blog": {
    "subdomain": "blog.aspose.com",
    "categories": { "words": { "url": "https://blog.aspose.com/categories/aspose.words-product-family/", "http_status": 200, "post_count": 42 } }
  }
}
```

**Governance guard**: `http_status` is either the real, live-verified HTTP status, or exactly
`-1` when verification was skipped (`--skip-http-verify`) — never a guessed `200`. Consumers
**must** treat only `http_status == 200` as linkable; `-1` or any non-200 value means "don't use
this URL yet."

### How it's produced

[`scripts/fetch_aspose_com_links.py`](../scripts/fetch_aspose_com_links.py) — adapted from
aspose.org's `scripts/pipeline/commands/ops/fetch_aspose_com_targets.py` (see
`plans/master.md`'s "Patterns adapted from aspose.org" table), trimmed to only the two URL depths
and four+blog surfaces this project actually links to. Two modes:

```bash
# Offline: trim an aspose.org checkout's full 20 MB target map down to what this project needs
python scripts/fetch_aspose_com_links.py --from-source <aspose.org checkout>/data/aspose_com_targets.json

# Live: fetch products/reference/kb/blog sitemaps + a synthesized family x platform candidate
# grid (docs.aspose.com has no usable sitemap), then HEAD->GET-verify every candidate URL
python scripts/fetch_aspose_com_links.py
```

Both modes write atomically (temp file + rename) and refuse to write an empty result (exit 1 if
zero links were collected — never silently overwrite a good file with an empty one).

**Unlike `products.json`, this file has no scheduled workflow** — same as its aspose.org source,
it's refreshed on demand by an operator when aspose.com content is known to have changed. If this
project starts consuming it for rendered links, revisit whether it needs the same weekly-PR
treatment as `products.json` (see `data/families.json` subsection above for that pattern).

## Quick reference for agents

| Question | Answer |
|---|---|
| Can I operate on this repo? | Only if it's in `data/products.json` with `mode != "disabled"` — check via `registry.loader.is_permitted()`, never by reading the file yourself. |
| Does `mode: "disabled"` mean I can ignore this entry for research/development? | **No.** `mode` gates write/execution access only. Every entry — all 25, active or `disabled` — has equal precedence for portfolio surveys, fact-gathering, and policy/validator design; a `disabled` entry is not a lower-priority one. Only end-to-end execution is scoped to the three enabled Java pilots (`3d`, `cells`, `pdf`), and only because they're the sole non-`disabled` entries today. See `AGENTS.md`, `plans/master.md` decision #24, and `PIL-011` in `plans/requirements.md`. |
| I found a new FOSS repo GitHub added — how does it get tracked? | It doesn't need manual entry: the next scheduled (or manual `--dry-run`/live) run of `scripts/update_products_registry.py` picks it up automatically, added as `disabled`. |
| I want to enable a repo the scan discovered. | Follow [`docs/policy-authoring.md`](../docs/policy-authoring.md) — author a policy profile, then flip `mode` by hand. Never scripted. |
| A new Aspose FOSS family/org launches. | Add it to `data/families.json` by hand (one line) — that's the only manual step; `products.json` then fills in automatically. |
| Does `families.json` need to match `products.json`'s orgs exactly? | Every org referenced by `products.json` must exist in `families.json` — enforced by `test_real_families_json_covers_every_org_referenced_by_products_json` in `tests/unit/test_update_products_registry.py`. |
| I need a `products.aspose.com` (or docs/reference/kb/blog) link for a family or platform. | Look it up in `data/aspose_com_links.json`; use it only if `http_status == 200`. Never construct the URL by string-formatting a family/platform name — the link database is what confirms it actually resolves. |
| `aspose_com_links.json` looks stale. | Re-run `scripts/fetch_aspose_com_links.py` (live mode) yourself — there's no scheduled workflow for it yet, unlike `products.json`. |
