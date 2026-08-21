# Red-test plan for the repository-processability gate

Fixtures below are grouped by what they exercise. "Real" fixtures point at live registry repos
already observed during this audit (`REGISTRY_PROCESSABILITY_MATRIX.json`); "synthetic" fixtures
are proposed local trees for the implementer to construct under a test-fixture directory (this
audit does not create them — no implementation was performed). The rule under test throughout:

> A repository is unprocessable and must be skipped when its pinned tree is empty or, after
> excluding non-product administrative metadata, contains only README and/or LICENSE files.

This is stated as a **generic repository-shape rule** — every fixture below must exercise the
*shape* of the tree, not a family/org/platform label. No fixture may special-case on
`family == "psd"` or any Aspose-specific string; PSD only supplies the real-world existence
proof that the shape occurs in production.

## A. Real fixtures (already observed live, zero setup required)

| # | Fixture | org_repo | Shape | Expected verdict |
|---|---|---|---|---|
| A1 | Empty-except-README, .NET | `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET` | 1 file: `README.md` | **UNPROCESSABLE_SKIP** |
| A2 | Empty-except-README, Python | `aspose-psd-foss/Aspose.PSD-FOSS-for-Python` | 1 file: `README.md` | **UNPROCESSABLE_SKIP** |
| A3 | Missing LICENSE does not block | `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript` | 190 files, 0 LICENSE variants, 188 substantive | **PROCESSABLE** (proves LICENSE absence alone must never flip the verdict) |
| A4 | GitHub SPDX null, file-content MIT present | `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` (or any of `cells/{cpp,net,python,typescript}`) | `github_declared_license_spdx: null`, real `LICENSE`-class file present, 359 substantive | **PROCESSABLE**; regression guard that the classifier's LICENSE-class count is file-presence only and is never confused with (or used to backfill) the `config/policies/*.yml` `declared_license` org fact |
| A5 | Large repo, no truncation | `aspose-words-foss/Aspose.Words-FOSS-for-.NET` | 14,669 files | **PROCESSABLE**; regression guard against `git_tree_sha256`/GitHub tree-API truncation at scale (`truncated` must be `false`; if a future repo trips GitHub's recursive-tree cap, the real implementation must page/walk rather than silently under-counting) |

A1/A2 (PSD) are the only two repositories, across all 33, that hit the unprocessable rule today
— they are the fixture the binding policy explicitly permits ("PSD may be one fixture") and
explicitly forbids treating as definitional. Do not hardcode `family == "psd"`,
`platform in {"net", "python"}`, or the two `org_repo` strings anywhere in the classifier or its
tests as a *condition* — assert on them only as *expected outputs* of the generic shape rule.

## B. Synthetic fixtures — cross the family/ecosystem axis the real registry cannot cover alone

Each row is a minimal tree to construct under the implementer's chosen fixture root (e.g.
`tests/fixtures/repository_processability/<name>/`), independent of PSD and independent of any
one ecosystem, so the test suite proves the rule generalizes rather than fitting the one family
that happens to be empty today.

| # | Fixture name | Tree contents | Ecosystem axis | Expected verdict |
|---|---|---|---|---|
| B1 | `empty-tree` | *(zero files, zero directories)* | ecosystem-agnostic | **UNPROCESSABLE_SKIP** — "pinned tree is empty" |
| B2 | `readme-only-go` | `README.md` | go | **UNPROCESSABLE_SKIP** |
| B3 | `readme-license-only-rust` | `README.md`, `LICENSE` | rust | **UNPROCESSABLE_SKIP** — proves README+LICENSE together still skip, not just README alone |
| B4 | `readme-license-admin-only-cpp` | `README.md`, `LICENSE`, `.github/workflows/ci.yml`, `.github/ISSUE_TEMPLATE/bug.md`, `.gitignore`, `CONTRIBUTING.md` | cpp | **UNPROCESSABLE_SKIP** — the core "admin metadata alone is not implementation" assertion from the binding policy; `.github/**`, workflows, issue templates, `.gitignore`, community files must all classify `admin`, none `substantive` |
| B5 | `readme-license-admin-one-manifest-net` | Same as B4 plus a single empty-bodied `Project.csproj` | net | **PROCESSABLE** — one substantive file is sufficient; also exercises the "manifest with no real body" edge (still counts — presence, not richness, is the bar per the binding rule's plain wording) |
| B6 | `no-readme-no-license-source-only-python` | `pyproject.toml`, `src/pkg/__init__.py` | python | **PROCESSABLE** — proves README/LICENSE presence is irrelevant to the *processable* branch; only their *exclusive* presence triggers the skip |
| B7 | `deeply-nested-manifest-java` | `README.md`, `modules/core/pom.xml`, `modules/core/src/main/java/Foo.java` | java | **PROCESSABLE** — regression guard against a root-only scan (this registry's own `_find_manifest_paths()` docstring in `inspection/file_inventory.py` records a real historical bug of exactly this shape) |
| B8 | `docs-and-assets-only-typescript` | `README.md`, `docs/guide.md`, `assets/logo.png` | typescript | **Borderline — must be recorded explicitly, not silently decided.** This audit's classifier defaults ambiguous `docs/`/`assets/`-rooted, non-manifest, non-source files to `substantive` (see `_fetch_and_classify.py::classify_path()` and the two real high-borderline-count repos in §C below), which would make B8 **PROCESSABLE**. The real implementation must make the same call *deliberately* and document it — a hand-written prose guide or a logo image is weaker "substantive product evidence" than compiled source, and a reviewer may reasonably want `docs/`-only trees to still count as inadequate. This fixture exists to force that decision to be made on purpose, with a named test, rather than falling out of extension-matching accidentally. |
| B9 | `changelog-notice-only` | `README.md`, `CHANGELOG.md`, `NOTICE`, `THIRD_PARTY_NOTICES.md` | ecosystem-agnostic | **UNPROCESSABLE_SKIP** — another explicit borderline call this audit made conservatively (changelog/notice files classified `admin`, not `substantive`); a fixture, not a silent assumption, per the audit's own instruction to record borderlines with paths |
| B10 | `binary-only-no-manifest` | `README.md`, `bin/tool.exe` (no manifest, no recognized source suffix) | ecosystem-agnostic | **Borderline — record explicitly.** An unclassified binary blob with no matching manifest/source-suffix rule falls through this audit's classifier to `substantive` "by elimination" (see `classify_path()`'s trailing `return "substantive", False`). Flag this fixture for the implementer: elimination-based defaulting is safe for *this audit's read-only observation* but the real gate should decide affirmatively, not by exhausting a deny-list, to avoid a false PROCESSABLE on genuine junk (e.g. an accidentally committed build artifact in an otherwise-empty repo). |

## C. Adversarial / drift-guard fixtures

| # | Fixture | Purpose |
|---|---|---|
| C1 | Contract-hash bump | Change `INTAKE_PREFLIGHT_CONTRACT_HASH`-equivalent version constant for the new classifier rule set; assert every previously-cached skip/proceed receipt is invalidated and re-evaluated (see INTEGRATION_POINTS.md §3) even with `source_revision` unchanged. |
| C2 | Revision-bound re-evaluation | Start from fixture A1/A2's shape (README-only), then simulate upstream adding one substantive file at a new `source_revision`; assert the stored `IntakePreflightBindingV1`/skip receipt for the old revision is never reused for the new one (dedup key changes on `source_revision`), and the new run reaches `PROCESSABLE`. This is the live "cache invalidation when substantive content later appears" contract from the audit brief — exercise it concretely rather than only asserting the dedup-key formula in isolation. |
| C3 | MIT-fact non-conflation | Feed the classifier fixture A4's shape (`declared_license` present in `config/policies/*.yml`, no LICENSE file counted as `substantive`, GitHub SPDX null) and assert the processability verdict is unaffected by, and does not write to, `declared_license`/`config/policies/*.yml` in any way. |
| C4 | Truncated-tree honesty | Simulate (mock) a GitHub tree API response with `truncated: true`; assert the gate never silently reports `PROCESSABLE`/`UNPROCESSABLE_SKIP` from a possibly-incomplete listing — it must either page/walk to completion or surface a distinct non-terminal/failure outcome (e.g. route to `SYSTEM_FAILURE` on `IntakePreflightOutcomeV1`, which already exists for exactly this "read-only intake failed" shape), never guess. |

## D. Explicit non-fixtures (do not build these — listed to close off the wrong generalization)

- **Do not** write a test that asserts on `entry.family == "psd"`. The rule is about tree shape,
  not portfolio membership; B1-B10 exist so PSD is provably not load-bearing for the rule.
- **Do not** write a test that asserts `.github/**` presence alone is ever sufficient for
  `PROCESSABLE` — B4 is the negative-control fixture for this.
- **Do not** write a test that requires a LICENSE file for `PROCESSABLE` — A3 and B6 are the
  negative-control fixtures for this (the binding policy is explicit that missing LICENSE must
  not block).
