# Aspose Candidate Quality Calibration Audit

## Executive result

The Aspose bundle provides a strong, reusable model for **source-bound composition,
old-README reconciliation, reader-oriented structure, and candidate-bound evidence**. It does
not prove a perfect portfolio. The correct denominator is 30 eligible products: the canonical
tree contains 31 candidates and `products.json` marks all 31 active, but
`data/registry_exclusions.json` excludes `cells/typescript`. The bundled canonical portfolio
audit reports **8 clean and 22 dirty**.

The practical calibration is therefore not “make an optimizer README look as long as Aspose.”
It is: prove every material claim and every preservation decision, provide the reader a usable
task flow, and bind checks/review to the exact candidate bytes. `RUBRIC_30.md` turns that into 30
binary, evidenced criteria with hard disqualifiers. Word count, example count, table volume,
badges, and Mermaid usage are diagnostics only.

## Scope and pins

- Source archive: `upload/readme-refresh-complete-bundle-20260819-174412.zip`
- Archive SHA-256: `2d8eb6ae810d920b98136f3fa587b46d36b2e0c6b5250df109fa98c73e470465`
- Canonical candidate store: `files/reports/repo-presenter-regen-full/`
- Candidate-store authority: `files/data/readme_candidate_store.json`
- Product registry/exclusion authority: `files/data/products.json` and
  `files/data/registry_exclusions.json`
- Portfolio audit used: `files/reports/_scratch/mt056_audit_portfolio_FINAL.json`
- Pinned published/source snapshots: `files/runs/.clone_cache/*/README.md`, mapped by
  `files/CLONE-CACHE-PINS.json`
- Optimizer tip observed for context only: `56a5f09c80f57581d977d77142ed8809ed1ede9d`
- Audit date: 2026-08-19. No repository or GitHub writes were made.

## Population reconciliation

| Population | Count | Meaning |
|---|---:|---|
| Canonical `readme.md` tree entries | 31 | All family/platform candidates physically present. |
| Registry rows with `active: true` | 31 | Raw registry state. |
| Registry-excluded canonical entries | 1 | `cells/typescript`; not launchable under the recorded exclusion. |
| Eligible portfolio denominator | 30 | `active: true` minus exclusions. |
| Clean in bundled portfolio audit | 8 | No hard findings in that audit invocation. |
| Dirty in bundled portfolio audit | 22 | At least one hard finding in that audit invocation. |

The eight reported clean products are `cells/rust`, `email/cpp`, `email/net`, `pdf/go`,
`pdf/java`, `pdf/python`, `slides/java`, and `words/net`. This is a dated audit result, not a
permanent certification.

## Candidate structure and content calibration

Across the 30 eligible candidates:

| Metric | Min | Median | P75 | Max | Interpretation |
|---|---:|---:|---:|---:|---|
| Words | 1,244 | 3,297.5 | 4,518.5 | 12,427 | Product depth varies by 10×; length is not quality. |
| H2 sections | 11 | 12 | 12 | 14 | Information architecture is stable without being byte-identical. |
| Non-Mermaid fenced blocks | 7 | 11.5 | 14.75 | Examples are common, but count tracks product surface. |
| Code lines in fences | 55 | 128 | 171.5 | Enough detail for real workflows; not a minimum target. |
| Mermaid blocks | 1 | 1 | 1 | 1 | Uniform Aspose presentation convention. |
| Preamble badge images | 2 | 3.5 | 4 | 5 | Verified trust-signal pattern, not a universal badge quota. |
| Markdown links | 19 | 27.5 | 32.5 | Consistent navigation/resources/CTA density. |
| Table-row lines | 16 | 196 | 271.25 | API/reference depth varies dramatically. |

Every eligible candidate has Navigation, At a Glance, Key Capabilities, Installation, Quick
Start, Additional Examples, API Reference, Documentation & Resources, Scope and Limitations,
Development and Testing, and License. All 30 contain exactly one Mermaid block. Dependencies is
present in only **21/30**, even though the current skill/reference documents now make it required;
the portfolio audit reports 11 `required_sections` findings across 11 products. This is direct
evidence that documented policy, candidate shape, and dated clean state must be measured
separately.

Platform variation is substantial:

- Python: 12 products; median 2,867 words and 12.5 fenced blocks; Dependencies 9/12.
- .NET: 6 products; median 3,658.5 words; Dependencies 5/6.
- C++: 4 products; median 3,210 words; Dependencies 2/4.
- Java: 4 products; median 4,239.5 words with a 12,427-word maximum; Dependencies 3/4.
- Go: 2 products; 1,973 and 7,335 words; Dependencies 1/2.
- Rust: 1 eligible product; 3,376 words; Dependencies present.
- TypeScript: 1 eligible product (`3d/typescript`); 2,584 words; Dependencies absent. The separate
  `cells/typescript` candidate is excluded from the denominator.

Family-level data is in `CANDIDATE_METRICS.json`. Clean examples span `email/net` at 1,866 words
and `pdf/java` at 12,427 words. Conversely, candidates of many different sizes are dirty. That
breaks any defensible assumption that matching Aspose length or table density predicts quality.

## Reconciliation evidence

The canonical eligible tree contains these available ledgers:

| Ledger | Products with file | Entries | Main dispositions |
|---|---:|---:|---|
| Content | 30/30 | 1,462 | 290 verbatim, 734 reframed, 5 corrected, 433 excluded |
| Structure | 25/30 | 145 | 59 verbatim, 67 reframed, 19 excluded |
| Code examples | 18/30 | 463 | 130 verbatim, 139 reframed, 1 corrected, 1 relocated, 192 excluded |
| Badges | 20/30 | 40 | 29 preserved, 9 superseded, 2 excluded |

The important mechanism is not the disposition count. It is the join:
`old extracted unit → verified source meaning → disposition → candidate target span`. The audit's
largest current hard-finding totals are 427 content-coverage, 383 excerpt-to-extraction, 210 API
table completeness, 138 code-example coverage, 106 evidence resolution, 32 structural coverage,
and 28 badge coverage. These failures show why a ledger existing—or containing many rows—cannot
stand in for reconciliation correctness.

Four `verification_failed` rows in `slides/python` are legitimate negative findings attached to
excluded fabricated material. They demonstrate another important rule: a failed verification is
not automatically bad when it proves why an old/invented claim must be removed. It is unacceptable
when failed material is retained, when the excerpt was never really extracted, or when the failure
is used as acceptance evidence.

## Verification freshness and publication state

All 30 eligible candidates have `last-verified.json`, and their timestamps are only 12.45–13.42
hours old at the end of the bundle day. Yet only **18/30 markers match the current candidate
SHA-256**. The 12 mismatches are `3d/java`, `3d/python`, `3d/typescript`, `barcode/python`,
`pdf/cpp`, `pdf/go`, `pdf/net`, `pdf/python`, `slides/java`, `slides/net`, `slides/python`, and
`words/net`. A recent timestamp without exact-byte equality is not quality evidence.

The portfolio-audit artifact labels 13 products `published`. Recomputing the implementation's
actual `.strip()` equality against the bundled clone-cache README snapshots yields 12 matches:
`cells/go`, `cells/java`, `cells/net`, `cells/rust`, `email/cpp`, `email/net`, `font/python`,
`pdf/go`, `pdf/net`, `slides/cpp`, `words/net`, and `words/python`. Five products disagree between
the dated audit flag and the currently bundled candidate/snapshot pair. Raw byte equality is only
4/30 because terminal whitespace/newline differences are intentionally ignored by the pipeline.
This is not proof that either side is live GitHub state; it proves the bundle is not an atomic
portfolio snapshot and reinforces the need to bind every acceptance claim to exact hashes.

## Stable reusable quality policy

These qualities transfer directly to the optimizer, independent of product brand:

1. Current source and manifest truth outrank old README prose and model confidence.
2. Install commands, dependency classes, public API reachability, examples, formats, limitations,
   links, and license statements each receive purpose-built verification.
3. Every old content, structure, code, badge, and meaningful-media unit receives an evidenced
   disposition; exclusions are first-class and can be the correct result.
4. The README is organized around a reader journey: orientation, capabilities, installation,
   dependencies, first success, deeper examples/reference, limitations, development, resources,
   license.
5. Examples are proportionate and distinct; large API tables are made navigable/collapsible.
6. Public prose excludes internal process narration and private evidence paths.
7. Checks distinguish hard correctness from advisory editorial judgment.
8. A clean claim is exact-candidate-bound, check-complete, review-complete, and time-scoped.

## Aspose-specific conventions that should not become optimizer policy

- Aspose product naming, `products.aspose.org` banner destinations, Enterprise Edition wording and
  placement, and Aspose-domain allow/deny lists.
- The exact Mermaid `Starting Points → Product → Capabilities → Outputs` graph and the requirement
  for exactly one graph in every README.
- Exact section names/order, fixed MIT sentence, and the observed 2–5 preamble badges.
- Exact anchor text, platform naming, diagram geometry/token limits, and family-specific format
  casing tables.
- Portfolio word, example, link, or table-count distributions.

The optimizer should implement equivalent *jobs* and evidence guarantees using its existing
composition machinery, not copy brand text or add a second architecture.

## How to compare a sealed optimizer output

1. Seal repository SHA, old README SHA, selected knowledge/fact hashes, policy/check version, model
   configuration, and candidate SHA.
2. Run the 30 criteria against that exact candidate. Record one point only when its required
   artifact resolves and shares the candidate/input bindings.
3. Apply hard disqualifiers before interpreting the subtotal. Blocking skip/error/fail is not a
   partial pass.
4. Compare omissions and claims to the product's own evidence envelope. Use Aspose distributions
   only to detect suspicious under- or overproduction, never as score thresholds.
5. For old READMEs, require all four disposition classes and candidate-span reconciliation. For a
   README-only repository, treat the README itself as the primary knowledge source and prove
   non-applicability rather than inventing code facts.
6. For unavailable toolchains, preserve a named blocked outcome and constrain claims to what static
   and source inspection actually proves. No unavailable toolchain turns a blocking check into a
   pass.
7. Require independent factual and presentation review with bounded repair/fallback for malformed
   or truncated model output.
8. Re-run from the sealed inputs. Accept `30/30` only if replay preserves the required bindings and
   all 30 criteria remain proven.

## Bottom line

Aspose's strongest lesson is evidence-directed editorial judgment, not a template or a size target.
Its candidates consistently provide a rich reader flow, but the bundle simultaneously exposes
large reconciliation debt and stale candidate-verification joins. The optimizer can be equal or
better by preserving the reader-facing strengths while making item-level truth, complete check
coverage, reviewer fallback, and exact-byte acceptance fail closed.
