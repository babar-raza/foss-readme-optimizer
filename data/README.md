# `data/` — registry and link-database files

This directory holds the config-as-data files that drive the agent: the registry
(`products.json`, `families.json`) and the verified domain-specific link databases
(`aspose_com_links.json`, `aspose_org_links.json`). All four are plain JSON so they can be read,
diffed, and reviewed without running any code. Read
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

## `data/platform_priorities.json` — portfolio execution order

This user-owned configuration sets the deterministic order for otherwise ready ecosystem work:
Python, .NET, Java, C++, TypeScript, Rust, then Go. The stored identifiers are the registry values
`python`, `net`, `java`, `cpp`, `typescript`, `rust`, and `go`. The loader requires each supported
ecosystem exactly once and fails closed on missing, duplicate, unknown, or malformed entries.

The canonical `local_poc` portfolio runtime sorts its immutable registry snapshot by this policy
while preserving `data/products.json` order within one ecosystem. Unknown future ecosystems follow
the configured set in stable registry order. This is an execution priority, not a scope or safety
priority: every allow-listed repository remains mandatory, and a valid cached stage is reused
instead of being repeated merely to restate the order.

## `data/families.json` — the discovery seed list

Lists every Aspose FOSS family and the GitHub organization that hosts its per-platform repos —
`aspose-{family}-foss`, one org per family, 26 total. This is **not** an allow-list; being listed
here grants no permission to touch anything. It only tells the discovery script *where to look*.

```json
{ "family": "cells", "name": "Aspose.Cells", "github_org": "aspose-cells-foss" }
```

A source that does not exist or is outside the authorized FOSS portfolio remains in the catalog as
an explicit, revision-bound exclusion. Set `"enabled": false` and provide a nonempty
`"exclusion_reason"`. The inventory records that source as `excluded`; it does not scan it, silently
drop it, substitute a similarly named organization, or count the governed exclusion as an outage.

Execution eligibility is fail-closed and case-insensitive. A repository must have exactly the
shape `Aspose[.-]{Family}-FOSS-for-{Platform}`, with one terminal platform token and no trailing
variant suffix. The separator between `Aspose` and the family may be `.` or `-`, so both
`Aspose.PDF-FOSS-for-Go` and `aspose-pdf-foss-for-go` qualify. `CSSForge` and
`Aspose-PDF-FOSS-for-Go-MCP` do not. Discovery still records every nonconforming repository with a
stable identity and explicit exclusion; it does not silently omit it. A
`repository_classifications` record may clarify an already-conforming repository's family or
platform, but cannot override the naming eligibility contract or admit a nonconforming name.

## How `data/products.json` stays current

[`scripts/data-refresh/update_products_registry.py`](../scripts/data-refresh/update_products_registry.py)
scans every GitHub org in `families.json` (read-only `GET` calls against the GitHub REST API),
records every repository visible to the authorized credential, classifies names against the
case-insensitive `Aspose[.-]{Family}-FOSS-for-{Platform}` eligibility contract, and
merges the result into `data/products.json`. The script is a thin CLI wrapper — the discovery,
classification, and merge logic (and the safety contract) live once in
[`src/readme_agent/registry/discovery.py`](../src/readme_agent/registry/discovery.py), shared with
the runtime self-heal below:

- Newly discovered eligible stable repository identities are added with `mode: "disabled"`,
  `ecosystem: null`, `policy_profile: null` — never auto-enabled.
- Existing entries only have their upstream-shaped fields refreshed (e.g. a renamed repo or a
  newly archived one); `mode`/`ecosystem`/`policy_profile` are left untouched no matter what.
- A repository renamed outside the eligibility grammar is removed from the execution allow-list
  and retained as a discovery exclusion; archived or disappeared conforming identities retain an
  explicit governed disposition rather than being silently discarded.
- The write is atomic (temp file + rename).

Run it yourself:

```bash
python scripts/data-refresh/update_products_registry.py --dry-run     # preview, no write
python scripts/data-refresh/update_products_registry.py                # scan every org, write data/products.json
python scripts/data-refresh/update_products_registry.py --org aspose-pdf-foss   # scan one org
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

### Runtime self-heal (supervise)

Registry drift is also a self-healed class at runtime (`CORE-034`): every `readme-agent supervise`
invocation first runs `registry/self_heal.py::heal_registry_drift()`, which re-uses the exact
discovery/merge core above in-process — so a repo GitHub added since the last weekly scan is
merged (as `mode: "disabled"`, owned fields untouched, additive-only) before the allow-list gate
is consulted, instead of waiting for the cron. Properties:

- **Fail-open**: a scan/merge failure (network, rate limit over a 60 s wait cap, missing token)
  never blocks supervision — the heal reports a `SKIPPED_*` status and the run proceeds.
- **Throttled**: a TTL marker (`runs/registry-heal/last_heal.json`, 6 h default) makes a
  sequential multi-repo pass scan GitHub once, not once per repo.
- **Evidenced**: every attempt writes `runs/evidence/<run_id>/registry_heal.json` (orgs scanned,
  org failures, entries added/refreshed).
- **Opt-out**: `readme-agent supervise --no-registry-heal` skips it (the portfolio workflow's
  matrix jobs do this; a dedicated job heals once per pass instead).
- In CI, a healed `data/products.json` surfaces as a PR on the same branch as the weekly scan —
  never a push to `main`.

The heal can never enable a repo: it shares `merge()`'s invariants, so its write surface is
exactly the weekly cron's.

## `data/aspose_com_links.json` — the verified aspose.com link catalog

The Aspose Enterprise Edition target catalog is domain-pure, registry-scoped, and generated from
aspose.org's verified `data/aspose_com_targets.json`. It includes product landing pages plus a
bounded set of exact docs, KB, blog, and reference targets relevant to current source-backed terms.
Deep source-database slugs remain non-linkable until content evidence exists; a resolving URL alone
does not prove contextual relevance.

## `data/aspose_org_links.json` — the verified aspose.org link catalog

The FOSS target catalog is built from the sibling aspose.org source tree at an immutable revision.
It records current product, docs, KB, blog, and reference pages for every active family/platform in
`products.json`. Source existence never becomes an HTTP-200 claim: only retained prior verification
or an explicit live probe can make a record linkable.

Both files use the same strict schema:

```json
{
  "schema_version": "2.0",
  "parent_domain": "aspose.org",
  "provenance": {
    "generated_at": "...",
    "generator": "scripts/data-refresh/build_aspose_link_catalogs.py",
    "generator_version": "2.0.0",
    "sources": ["..."],
    "total_records": 1,
    "verified_records": 1,
    "output_hash": "sha256:..."
  },
  "records": {
    "stable-record-id": {
      "url": "https://docs.aspose.org/...",
      "http_status": 200,
      "verified_at": "...",
      "http_verification_source": "live_probe",
      "content_evidence": "source_body"
    }
  }
}
```

The runtime loads both catalogs through `readme_agent.links.catalog`, validates their SHA-256
inventories and domain boundaries, and selects only exact records whose HTTP and content evidence
make them linkable. It never constructs a URL from a family or platform string.

### How both catalogs are produced

Run the sole paired generator from the repository root:

```powershell
.venv/Scripts/python scripts/data-refresh/build_aspose_link_catalogs.py

# Re-probe selected discovered targets before committing their HTTP status.
.venv/Scripts/python scripts/data-refresh/build_aspose_link_catalogs.py `
  --verify-org-pattern "docs.aspose.org/html/python/getting-started/quickstart/"
```

The generator derives scope from `data/products.json`, writes both catalogs atomically, rejects
empty or wholly unverified output, preserves explicit verification provenance, and is byte-stable
when source and proof inputs are unchanged. `scripts/fetch_aspose_com_links.py` is retained only as
a compatibility façade and forwards supported arguments to this paired generator.

The catalogs are refreshed on demand. A newly discovered source page remains non-linkable
(`http_status == -1`) until explicitly verified. Configured runtime allocation ceilings determine
whether any eligible target is used; catalog presence is never a quota or permission to add a link.

## `data/working_condition_exceptions.json` — human-accepted working-condition exceptions

The explicit, per-repository gate for the working-condition-presentation exception lane (Decision
#101). `readme-agent poc` output is diagnostic-only by default (Decision #100) — it cannot
independently issue delivery, approval, or no-op states. A human may still explicitly accept a
specific poc-delivered README for a specific repository when the strict `supervise` pipeline
cannot currently pass because of a genuine, evidence-backed *upstream* defect (not an agent-fixable
gap) — for example, a broken PEP 517 build backend with no PyPI release, verified only by running
the repository's own example directly against its pinned source tree. Only a repository listed here
is eligible for promotion by
[`scripts/governance/promote_working_condition_exceptions.py`](../scripts/governance/promote_working_condition_exceptions.py);
everything else stays governed strictly by Decision #100.

```json
{
  "repository": "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
  "platform": "python",
  "family": "html",
  "accepted_date": "2026-08-12",
  "accepted_by": "product owner",
  "acceptance_basis": "the exact human instruction that authorized this exception",
  "blocking_defect_summary": "what's broken upstream and what was verified anyway",
  "resume_predicate": "what upstream must fix for this repository to re-enter the strict lane, after which this entry is removed"
}
```

Each entry is added or removed only by hand, following an explicit human acceptance decision —
never by automation, and never as a blanket policy for a family or platform. A repository whose
*source itself* is non-importable or missing (no verified working content exists to present at
all) does not qualify for this lane; its defect goes to
`report/findings/<family>/<platform>/upstream-issues.md` for the owning product team instead. See
`plans/decisions/catalog.jsonl` decision #101 for the full policy and
`plans/investigations/evidence/working-condition-presentation-exceptions-v1/README.md` for the
promoted evidence this registry currently gates.

## `data/template_clone_findings.json` — periodic embedding-similarity findings (Wave 8.6)

Pairwise cosine-similarity findings across the enabled portfolio's real READMEs (owned spans
stripped first), flagging pairs likely to be template clones or generic/mechanically-inserted
prose (`LLM-017`/`VAL-016`/`RDM-020`). Evidence only, never a sole verdict — consumed by the
`get_template_clone_findings` capability for a given org_repo, or read directly by a human.

```json
{
  "similarity_threshold": 0.70,
  "repos_embedded": ["aspose-cells-foss/Aspose.Cells-FOSS-for-Java", "..."],
  "repos_failed": [],
  "flagged_pairs": [{"repo_a": "...", "repo_b": "...", "cosine_similarity": 0.788}]
}
```

**How it's produced**: [`scripts/data-refresh/detect_template_clones.py`](../scripts/data-refresh/detect_template_clones.py),
via `.github/workflows/detect-template-clones.yml` (`workflow_dispatch` only for now — no
`schedule:` trigger until a manual run has been confirmed clean, per `GOVERNANCE.md` rule 10).
Deliberately **not** run by the per-run supervisor loop — `LLM-017`'s own acceptance text keeps
this a periodic batch job, explicitly out of the per-run planner path.

```bash
python scripts/data-refresh/detect_template_clones.py
```

## Quick reference for agents

| Question | Answer |
|---|---|
| Can I operate on this repo? | Only if it's in `data/products.json` with `mode != "disabled"` — check via `registry.loader.is_permitted()`, never by reading the file yourself. |
| Does `mode: "disabled"` mean I can ignore this entry for research/development? | **No.** `mode` gates write access only. Every registry entry remains mandatory. Among otherwise ready work, `data/platform_priorities.json` sets Python -> .NET -> Java -> C++ -> TypeScript -> Rust -> Go execution order; it never changes allow-list scope or acceptance. See `AGENTS.md`, `plans/master.md` decisions #24/#40/#83, and `PIL-011`/`L8-034` in `plans/requirements.md`. |
| I found a new FOSS repo GitHub added — how does it get tracked? | It doesn't need manual entry: the next `readme-agent supervise` run self-heals it into the registry in-process (added as `disabled`), and the weekly scheduled (or manual) run of `scripts/data-refresh/update_products_registry.py` is the out-of-band safety net. |
| I want to enable a repo the scan discovered. | Follow [`docs/policy-authoring.md`](../docs/policy-authoring.md) — author a policy profile, then flip `mode` by hand. Never scripted. |
| A new Aspose FOSS family/org launches. | Add it to `data/families.json` by hand (one line) — that's the only manual step; `products.json` then fills in automatically. |
| Does `families.json` need to match `products.json`'s orgs exactly? | Every org referenced by `products.json` must exist in `families.json` — enforced by `test_real_families_json_covers_every_org_referenced_by_products_json` in `tests/unit/test_registry_discovery.py`. |
| I need a `products.aspose.com`/`products.aspose.org` (or docs/reference/kb/blog) link for a family or platform. | Look up `.com` targets in `data/aspose_com_links.json` and `.org` targets in `data/aspose_org_links.json`; use only `http_status == 200`. Never construct the URL by string-formatting a family/platform name — the domain-appropriate database is what confirms it actually resolves. (2026-07-22 incident: a session did exactly that for 22 policy profiles; 9 guessed `.com` platform URLs 404'd and had to be corrected by live re-verification.) |
| Either Aspose link catalog looks stale. | Re-run `scripts/data-refresh/build_aspose_link_catalogs.py`; add a narrow `--verify-org-pattern` or `--verify-com-pattern` only for discovered targets that require fresh HTTP proof. Never guess or move records across domain catalogs. |
