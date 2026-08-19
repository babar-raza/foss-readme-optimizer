# README Candidate Quality Rubric — 30 Points

## Purpose and scoring rule

This rubric compares a sealed optimizer candidate with the *quality mechanisms* demonstrated by
the bundled Aspose README-refresh portfolio. It does not reward copying Aspose wording, branding,
length, table volume, or the number of examples. Each criterion is worth one point and requires
the named evidence. Score only the candidate and evidence produced from the same sealed input
revision.

Use three outcomes per criterion:

- **1 — proven:** the criterion is satisfied and the required evidence is present and candidate-bound.
- **0 — not proven:** it fails, is missing, is stale, or a required check was skipped/errored.
- **N/A is not a free point:** use the explicit README-only/unavailable-toolchain rules below. A
  truthful, evidence-backed non-applicability may satisfy the criterion; silent absence cannot.

A numerical score is diagnostic. A candidate is accepted as `30/30` only if it earns all points
and has no hard disqualifier.

## Hard disqualifiers

Any one of these makes the candidate ineligible for acceptance regardless of its numeric subtotal:

1. A material unsupported or contradicted claim about installation, dependencies, API, formats,
   behavior, licensing, security, or compatibility.
2. A command/example that is presented as working but imports/calls a nonexistent surface or is
   known not to run in the stated environment.
3. A blocking check that failed, skipped, or errored; a parser/reviewer failure treated as approval;
   or an evidence artifact containing an error envelope while promotion continues.
4. Candidate bytes do not match the SHA reviewed and verified, or input source/knowledge revisions
   are not pinned.
5. A verified old-README fact, structural unit, code example, badge, or meaningful image is silently
   dropped when an old README exists.
6. Internal process/evidence paths, private audit narration, credentials, or forbidden implementation
   details leak into public README prose.

## A. Truth and installability — 8 points

| # | Criterion | One point requires | Evidence |
|---|---|---|---|
| 1 | Material-claim grounding | Every material claim maps to current source, manifest, registry, or approved public documentation; contradictions are resolved against source. | Claim-to-fact ledger with source path/symbol/line or structured fact ID, plus contradiction report. |
| 2 | Installation truth | Commands match the actual publication state, package name, import root, supported version, and source-install path. No registry guess. | Manifest/registry snapshot and command verification record. |
| 3 | Dependency truth | Required, optional, development, native/system, and proprietary-runtime classes are not conflated; verified zero is explicit. | Parsed manifest snapshot or source-honest non-applicability record. |
| 4 | API surface truth | Named public types/members exist and are reachable through the public entry path; stubs and inherited dispatch traps are not presented as working. | API inventory plus reachability/source trace for each named surface. |
| 5 | Example truth | Every shipped example has a named verification outcome. Runtime-dependent behavior is not asserted from syntax or symbol existence alone. | Per-example ledger: run/pass, or bounded blocked-with-reason plus static/source checks and no unproved runtime promise. |
| 6 | API-reference integrity | Reference content is useful, deduplicated, scoped to public/reachable APIs, and complete for its declared scope. | Declared scope, inventory comparison, missing/extra/duplicate report. |
| 7 | Limitations honesty | Important missing, partial, pre-alpha, stubbed, or unsupported behavior is stated plainly; no invented “no known limitations.” | Negative/source evidence and limitation-to-fact mapping. |
| 8 | Link, format, and license accuracy | Product/docs/license links resolve to intended targets; format names/casing and license statements match evidence. | Link/anchor report, format corroboration, license-file check. |

## B. Preservation and reconciliation — 5 points

| # | Criterion | One point requires | Evidence |
|---|---|---|---|
| 9 | Content-unit accounting | Every factual/mechanism unit extracted from the old README is merged verbatim, reframed, corrected, or excluded for a true reason. | Complete content-disposition ledger; excerpt must match actual extraction. |
| 10 | Structural accounting | Trees, command-only sections, tables, and other non-prose structures are preserved/reframed/excluded explicitly. | Complete structure-disposition ledger. |
| 11 | Code-example accounting | Every old code block has a disposition and the claimed target is traceable in the candidate. | Complete code-example ledger and fingerprints. |
| 12 | Badge/media accounting | Old badges and meaningful images are preserved, superseded, corrected, or excluded with verified rationale; duplicates are removed. | Badge/media ledger and target/category checks. |
| 13 | Reconciliation integrity | Every kept unit resolves to its claimed candidate span; every exclusion has evidence; no duplicate merge, fabricated excerpt, or coverage-by-count shortcut. | Candidate-span reconciliation report with zero unresolved/error rows. |

## C. Reader utility — 7 points

| # | Criterion | One point requires | Evidence |
|---|---|---|---|
| 14 | Immediate orientation | Title and opening explain what the project is, who/what it is for, maturity when material, and the central value without process narration. | Reviewer cites the opening span and underlying facts. |
| 15 | Capability overview | A compact, accurate overview makes inputs, major capabilities, and outputs easy to scan. A diagram is optional; if used, every node is verified. | Structural review and node/claim verification where applicable. |
| 16 | Concrete capabilities | Capabilities are specific and source-bound rather than generic marketing bullets; limitations are not hidden. | Capability-to-fact coverage report. |
| 17 | Actionable installation | A user can choose the correct install path and prerequisites without guessing. | Installation check plus dependency snapshot. |
| 18 | Minimal successful start | The shortest honest first-use path is present, ordered, and consistent with installation/import/API truth. | Quick-start verification record. |
| 19 | Proportionate examples | Additional examples cover distinct high-value workflows without repetition or padding; zero examples is acceptable for an evidence-poor README-only repository. | Example-purpose inventory and duplicate/overlap review. |
| 20 | Navigable reference and resources | Readers can find the API scope, development/testing path, documentation, issue tracker, license, and contribution route when they exist. Large details are collapsible or linked. | Link/section inventory and rendering review. |

## D. Presentation quality — 5 points

| # | Criterion | One point requires | Evidence |
|---|---|---|---|
| 21 | Coherent information architecture | Sections are complete, non-duplicative, and ordered around user tasks. Exact Aspose headings/order are not required. | Heading/order and section-job analysis. |
| 22 | Clear public prose | Active, precise, readable prose; no generation/audit narration, unexplained confidence language, or private artifact names. | Prose-hygiene checks plus quality review. |
| 23 | Verified trust signals | License and one other genuinely available trust signal are shown without misleading static/dynamic claims. If only one signal exists, verified scarcity is acceptable. | Availability detector and badge/link verification. |
| 24 | Render and link integrity | Markdown renders; anchors, tables, details, diagrams/images, relative paths, and alt text work. Decorative assets never substitute for content. | Markdown/render/link checks on candidate bytes. |
| 25 | Proportionate depth | Detail follows product complexity and available evidence; no score for word/table/example counts, keyword stuffing, or copying a sibling. | Reviewer compares coverage to source surface and flags both omission and overproduction. |

## E. Candidate-bound process proof — 5 points

| # | Criterion | One point requires | Evidence |
|---|---|---|---|
| 26 | Sealed inputs | Repository SHA, old README SHA, knowledge/corpus hashes, policy/check version, and model configuration are recorded before composition. | Immutable run manifest. |
| 27 | Exact-byte verification | The candidate SHA equals the SHA in check, review, and acceptance artifacts; verification timestamp is meaningful only with that equality. | Candidate hash joins across all artifacts. |
| 28 | Complete fail-closed checks | Every required check reports run/pass/fail/skip/error; all blocking checks ran and passed. | Check-coverage matrix with zero blocking skip/error/fail. |
| 29 | Independent, claim-bound review | Factual and presentation reviews inspect material claims and candidate spans; malformed/truncated model output retries/falls back and can never approve. | Structured reviewer coverage, repair attempts, final parsed result. |
| 30 | Repeatable acceptance | A sealed rerun is deterministic where promised; a no-op proves source/fact/candidate/check/review bindings, not merely byte replay. | Replay manifest, artifact hashes, bounded resource/time record, and no-op proof. |

## README-only repositories

A repository containing only a README is not a license to invent a product. Apply the same rubric
with a narrower evidence envelope:

- Score installation/dependencies/examples/API criteria only when the candidate explicitly records
  verified non-applicability or limits itself to facts present in the README, repository metadata,
  license, and approved public documentation.
- Do not fabricate package names, import roots, manifests, APIs, formats, or runnable examples.
- A compact, honest README can earn full reader-utility and presentation points. It does not lose
  points for lacking code-derived sections when the absence is explicit and verified.
- Old-README accounting still applies: in an otherwise empty repository, that README is the primary
  source and must be reconciled line-by-line/structure-by-structure where material.

## Unavailable toolchains

Unavailable execution infrastructure must be visible, not silently converted to a pass. For a
full point on example truth, each affected example must have a named blocked reason, syntax/static
and source/API verification where possible, and wording that avoids unproved runtime behavior.
If a material claim can only be established by running the unavailable toolchain, omit or qualify
the claim; otherwise criterion 5 is not proven. A blocking check itself may never be skipped merely
because a toolchain is unavailable.

## Calibration guardrails

- The bundle's eligible candidates range from 1,244 to 12,427 words, 7 to 28 non-Mermaid fenced
  blocks, and 16 to 1,086 table-row lines. These are evidence of product variability, not targets.
- All 30 eligible candidates use one Mermaid overview and a common section family. Treat those as
  an Aspose editorial convention; an equivalent scannable structure can score.
- The bundled portfolio audit is **8 clean / 22 dirty**, and only 18/30 `last-verified.json`
  markers match current candidate bytes. Aspose artifacts calibrate mechanisms and reader patterns;
  they are not a blanket gold label.
- The 31st canonical candidate, `cells/typescript`, is excluded by the registry. It is observable
  calibration data but not part of the 30-product acceptance denominator.
