# OPT-REGISTRY-PROCESSABILITY-AUDIT

Read-only full-registry audit preparing the generic repository-processability gate. No tracked
file was created, edited, committed, or pushed to produce this bundle; nothing in
`data/`, `config/`, `plans/`, or `src/` was touched. Qwen was not invoked; no README candidate
was generated. All writes are confined to
`runs/owner_audit_staging/repository-processability-aa9981021/`.

- **Repo pin (this project's own commit, verified before starting):**
  `aa998102191c530af4dca3a6895d62a4027a613e` — matched `git rev-parse HEAD` exactly; working
  tree was clean.
- **Registry source:** `data/products.json`, loaded dynamically (not hand-copied) — 33 entries
  confirmed, matching `src/readme_agent/registry/loader.py::load_products()`'s own contract.
- **Target-repo access:** read-only GitHub REST API (`GET` only — repo metadata, branch/commit,
  recursive git tree), using `gh auth token` per this environment's standing recipe. Zero writes
  issued to any target repository or org.
- **Coverage:** 33/33 registry entries fetched successfully. 0 API errors. 0 truncated trees
  (GitHub's recursive-tree API truncation flag was checked explicitly on every response,
  including the 14,669-file `words/net` repo — see `tree_truncated_by_github_api` in the
  matrix).
- **Method:** `_fetch_and_classify.py` in this directory (a one-shot audit helper, not tracked
  machinery) resolves each entry's `owner/repo`, fetches `GET /repos/{o}/{r}`,
  `GET /repos/{o}/{r}/branches/{default_branch}`, and
  `GET /repos/{o}/{r}/git/trees/{tree_sha}?recursive=1`, then classifies every blob path with
  rules deliberately mirroring the existing generic name/glob sets in
  `src/readme_agent/inspection/file_inventory.py` and
  `src/readme_agent/ecosystems/registry.py::known_manifest_globs()`, rather than inventing a
  second, drifting definition of README/LICENSE/manifest.

## Headline result

**31 of 33 registry entries are PROCESSABLE. 2 are UNPROCESSABLE_SKIP under the binding
policy's generic shape rule** — both are the `psd` family (`aspose-psd-foss/Aspose.PSD-FOSS-for-
.NET` and `aspose-psd-foss/Aspose.PSD-FOSS-for-Python`), and both are already recorded as
`mode: "disabled"` in the live registry. Each of the two has a pinned tree of exactly **one
file, `README.md`** — no LICENSE, no admin metadata, no substantive product evidence at all.
This is a real, already-observed instance of the rule, not a hypothetical: it is the strongest
available confirmation that the binding policy's generic shape test is correctly targeted at a
real registry condition, and that PSD is (as the task brief anticipated) the one fixture the
current registry happens to supply.

Portfolio-wide file totals across all 33 pinned trees (27,951 files observed):

| Class | Files | Repos with ≥1 |
|---|---:|---:|
| README variants | 71 | 33/33 |
| LICENSE variants | 33 | 31/33 |
| Administrative metadata | 87 | 27/33 |
| Substantive product evidence | 27,760 | 31/33 |

Registry `mode` breakdown: `full`=2, `dry_run`=29, `disabled`=2 (the 2 `disabled` entries are
exactly the 2 unprocessable PSD rows — the registry's own operators had already independently
flagged these as not-yet-enabled; see `config/policies/aspose-psd-foss-net.yml`'s
`detected_license: 'TODO(human): could not verify automatically -- confirm manually before
enabling'`). `mode` is otherwise orthogonal to processability and this audit does not use it as
a signal — the classification is derived only from tree shape, per the binding policy's
"generic repository-shape rule, not PSD/family/organization/platform-specific" instruction.

## Per-row matrix

See **`REGISTRY_PROCESSABILITY_MATRIX.json`** for the complete, machine-checkable per-repo
record: registry identity, `repository_sha` (resolved default-branch HEAD commit),
`tree_sha_github` (the commit's own Git tree SHA — a real, content-addressed inventory
identity) plus `tree_inventory_sha256` (this audit's own sha256 over the sorted path list, since
a live `git ls-tree` was not available through the read-only API-only path — see
"Implementation note on the inventory hash" below), per-class counts, up to 5 representative
paths per class, explicit `borderline_paths` (2,238 total flags across the portfolio, capped at
15 recorded per row — see below), final `classification`, and an exact `reason` string.

Two representative rows:

```
psd      net        files=1    sub=0     readme=1  lic=0  admin=0   -> UNPROCESSABLE_SKIP
  reason: "pinned tree contains only README and/or LICENSE files"
3d       typescript files=190  sub=188   readme=1  lic=0  admin=1   -> PROCESSABLE
  reason: "188 substantive product-evidence file(s) present"
```

The second row is also this audit's live proof that **missing a repository-level LICENSE file
does not, by itself, block processability** — `3d/typescript` has zero LICENSE-class files and
is still `PROCESSABLE` on the strength of its 188 substantive files, exactly as the binding
policy requires.

## Borderline calls — recorded explicitly, not silently decided

Per the audit instruction ("If a borderline case appears, record it explicitly with paths rather
than silently choosing"), the classifier flags — but does not hide — every path it could not
place with full confidence. 2,238 such flags occurred across the portfolio, concentrated in a
few repos with large `docs/`, `resources/`, or `TestData/` trees:

- **`docs/apidocs/**` (generated API HTML)** — `cells/java` (128 flagged), `pdf/*` (18-119
  flagged per repo). Classified `substantive` (generated reference documentation of the actual
  product API is real product evidence), flagged because a naive rule keyed only on the `docs/`
  path prefix could easily miscall this `administrative`.
- **`resources/*.ttf`, `readme.resources/*.png`** — `page/python` (1,590 flagged, by far the
  largest single concentration; this repo ships an embedded font/test-image resource tree).
  Classified `substantive` (product test/runtime resources), flagged for the same reason.
- **`TestData/Images/**`** — `words/net` (278 flagged). Classified `substantive` (real test
  fixtures exercising the product), flagged for the same reason.
- Smaller counts (0-28) across most other repos are the same `docs/`/`assets/`/image-suffix
  pattern at a smaller scale.

None of these borderline flags changed a repo's overall PROCESSABLE verdict (every repo with
borderline flags already has hundreds of unambiguous substantive files besides them). Their
practical importance is entirely for the two currently-empty PSD repos and for
**`RED_TEST_PLAN.md` fixtures B8-B10**, which construct trees where a `docs/`-only or
binary-only borderline call *would* be outcome-determining and must therefore be made on
purpose by whoever implements the real gate, not fall out of an extension-matching accident.

## Earliest production-runtime gate point

`registry/intake.py::classify_readonly_intake()`, invoked from
`supervisor/intake.py::run_readonly_intake_preflight()` — which its own module docstring
describes as running "before the normal supervisor" — is the earliest point in the production
runtime that inspects a repository at all. It runs strictly before facts collection
(`facts/provider.py`), Qwen/specialist-tier calls (`supervisor/specialist_tier.py` ->
`llm/planner_client.py`), candidate generation (`readme/candidate_pipeline.py`), independent
review (`specialists/independent_readme_review.py`), and any scoring pass. Full detail,
including the exact lifecycle-status ordering (`ReadmePocStatusV2` in
`state/lifecycle_schema.py`) that proves this ordering, is in **`INTEGRATION_POINTS.md` §1**.

## Typed terminal/outcome model to reuse

**`IntakePreflightOutcomeV1` / `ReadOnlyIntakePreflightV1` / `IntakePreflightBindingV1`**
(`state/lifecycle_schema.py` + `registry/intake.py`) already is the existing, source-bound,
hashable, typed read-only-intake outcome model — its own docstring calls
`IntakePreflightBindingV1` a "Source-bound terminal outcome of one read-only intake inspection."
This audit recommends reusing it (adding one new `Literal` outcome value and one new
classification branch inside the existing function) rather than proposing a second controller.
`ConvergenceOutcome`/`SuperviseStatus` and `BlockedDecisionRecordV1` were both considered and
are documented as deliberately **not** the right fit (too late in the pipeline, or a
reuse-across-runs cache layered on top of an already-classified outcome rather than the
classification itself). Full reasoning and field-by-field skip-receipt mapping (including how
cache invalidation on new upstream content already falls out of the existing
`source_revision`/`contract_hash`-bound dedup key, with zero new invalidation logic needed) is
in **`INTEGRATION_POINTS.md` §2-3**.

## Portfolio-wide MIT license policy authority

**`config/policies/<policy_profile>.yml`'s `required_elements.license_mentioned.detected_license`**
(consumed at `facts/provider.py:257` into the `declared_license` fact) is the correct existing
authority for the organization-policy MIT fact — a human-confirmed, per-repo config value, not a
live repository re-scan. `license/auditor.py::detect_license()` is a *different*, legitimately
also-used mechanism (repository-file/GitHub-API detection evidence, consumed by
`readme/candidate_pipeline.py`, `capabilities/detect_readme_gaps.py`,
`capabilities/audit_community_files.py`, `facts/repository_ingestion.py`) that answers a
different question ("what does this repo's own files currently say") and must not be conflated
with the org-policy fact. This audit's own collected data shows exactly why the two must stay
separate: `cells/{cpp,java,net,python,typescript}` all report `github_declared_license_spdx:
null` from GitHub's API (see `REGISTRY_PROCESSABILITY_MATRIX.json`) even though each has a real
in-tree LICENSE file and a human-confirmed `detected_license: MIT` in its policy YAML — file
detection and org policy legitimately disagree here, and the binding policy's warning
("repository-file absence must not be represented as repository-detected MIT evidence") is
guarding against exactly this kind of divergence being papered over. Full detail in
**`INTEGRATION_POINTS.md` §4**, including a secondary, currently-unconsumed `overrides.license`
slot on individual `data/products.json` entries (present on `cells/typescript` only) that this
audit confirmed has no reader anywhere in `src/` today and is therefore *not* the authority.

## Cross-family / cross-ecosystem red-test fixtures

**`RED_TEST_PLAN.md`** provides: 5 real fixtures already observed live in this audit (including
both PSD repos and the `3d/typescript`-missing-LICENSE proof), 10 synthetic fixtures spanning
go/rust/cpp/net/python/java/typescript so the rule is proven generic rather than PSD-shaped, and
4 adversarial/drift-guard fixtures (contract-hash bump, revision-bound re-evaluation, MIT-fact
non-conflation, truncated-tree honesty). Two synthetic fixtures (B8 docs-and-assets-only, B10
binary-with-no-manifest) are marked as genuinely open borderline calls this audit deliberately
did not resolve on the implementer's behalf.

## Implementation note on the inventory hash

The audit brief asks for a "tree/inventory hash" per row. Production code already has a
precedent for exactly this: `repository_snapshot.py::RepositorySnapshotV1.inventory_sha256`,
computed as `sha256(git ls-tree -r --full-tree HEAD output)` inside a real local clone. This
audit ran entirely through the read-only GitHub REST API (no clone, per the brief's read-only
constraint) and therefore could not reproduce that exact byte format; `tree_inventory_sha256`
in the matrix is instead `sha256(sorted "\n".join(paths))` — a different but equally
deterministic and content-addressed hash. `tree_sha_github` (the commit's own Git tree SHA, as
returned by the GitHub API) is also recorded per row and is directly comparable across audit
runs without needing this script at all. **The real production classifier, running inside
`classify_readonly_intake()` against an already-cloned `RepositorySnapshotV1`, should reuse
`inventory_sha256` directly rather than adopting either of this audit's two substitute hashes.**

## Time-box

Audit completed within the requested 60-minute time-box. All JSON was validated (`json.load`
round-trip on `REGISTRY_PROCESSABILITY_MATRIX.json`) and all checksums in `SHA256SUMS` were
computed from the final on-disk bytes of each listed file. No classifier implementation was
written; `_fetch_and_classify.py` is audit tooling only (fetch + read-only observation), not a
proposal for the production gate's code — that remains a separate, not-yet-authorized change.
