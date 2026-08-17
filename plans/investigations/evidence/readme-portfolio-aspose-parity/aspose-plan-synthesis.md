# Aspose.org `/readme-refresh` skill — plan synthesis for foss-readme-optimizer parity

**Source plan** (read in full, sequentially, 18,434 lines, offset 1 → 18434):
`C:\Users\prora\.claude\plans\d-users-prora-onedrive-documents-github-humble-tome.md`

**Source implementation** (verified directly against the real filesystem/git, not inferred from the
plan's prose): `D:\onedrive\Documents\GitHub\aspose.org\`, specifically:
- `skills/readme-refresh.md` (925 lines, S-120)
- `scripts/pipeline/commands/foss/readme_refresh_run.py` (2,919 lines — the CLI/state machine)
- `scripts/pipeline/commands/foss/readme_refresh_checks.py` (7,897 lines, 92 real `check_*` functions)
- `scripts/pipeline/commands/foss/dependency_extract.py` (new, ~43KB, 7 per-ecosystem extractors)
- `scripts/pipeline/tests/test_readme_refresh_run.py` (103 tests), `test_readme_refresh_checks.py`
  (605 tests), `test_dependency_extract.py`
- `reports/repo-presenter/{family}/{platform}/*` (30 real products — the sole canonical candidate
  tree) and `reports/repo-presenter-regen-full/{family}/{platform}/*` (a parallel, explicitly-scoped
  clean-room comparison tree, gitignored, not a competing production path)

The plan is a single continuously-amended Plan-Mode document spanning **51 numbered
missions/incidents** (MT015 through MT051) and a **104-item taskcard register** (TC-HARDEN-01
through TC-HARDEN-104), accreted over 2026-08-01 through 2026-08-16/17. It documents both the
*design* and the *real execution history* of a skill called `/readme-refresh` (S-120) that
generates production-grade README.md candidates for Aspose's ~31 FOSS product repos — the exact
artifact class `foss-readme-optimizer`'s own `runs/readme-poc/...` candidates are trying to match.

---

## 1. Final current requirements (latest state, plan accretes over time — latest wins)

As of the plan's final entries (MT051, 2026-08-16), the skill's requirements are:

- **Scope per run**: one `{family}/{platform}` product. Produces `readme.md` +
  `upstream-issues.md` + `content-dispositions.json` (+ increasingly, but not yet portfolio-wide:
  `structure-dispositions.json`, `badge-dispositions.json`, `code-example-dispositions.json`).
- **State machine**: `CREATED → INPUTS_PINNED → PLANNED → VERIFYING_EXAMPLES → AWAITING_REVIEW →
  APPROVED → PUSHING → PUSHED`, `BLOCKED` re-enterable from `INPUTS_PINNED/PLANNED/
  VERIFYING_EXAMPLES/PUSHING`, `ABANDONED` terminal from any non-terminal state.
- **Division of labor** (explicit, load-bearing): the *script* (`readme_refresh_run.py`) never
  writes README prose — it computes a deterministic `facts/factpack.json` and runs deterministic
  checks; the *agent* composes `readme.md` directly from the factpack. This is stated in the
  module's own docstring and is unchanged across the entire plan's history.
- **Every candidate must pass ~92 deterministic checks** (see §10) before human review, split into
  hard gates (block the state transition) and heuristics (non-blocking judgment prompts).
- **Every push is human-gated**: `AWAITING_REVIEW` is a hard stop; `approve` requires an explicit,
  fresh instruction each time; the skill "must never call `approve` on its own initiative."
- **Mandatory `## Dependencies` section** (MT041, 2026-08-14): every candidate must have a real,
  manifest-derived dependency section (Required/Optional/Native-and-System/Development
  subsections), placed after Installation, before Quick Start.
- **Mandatory portfolio-wide banner + homepage link + Enterprise Edition link**, both
  mechanically verified (never guessed) — see §8/§9.
- **Prose-quality is a durable *process*, not a mechanical guarantee**: mandatory tone-exemplar
  reading (2–3 real sibling candidates, for voice) before composing, a positive rubric, and a
  Regeneration Comparison Protocol — explicitly disclosed as *not* mechanically certifiable
  ("reads naturally" stays a human judgment call, forever).
- **New-product/new-language onboarding must work without manual intervention** (MT035, 2026-08-12,
  directly triggered by "new platforms and products will be added soon... treat it as a production
  problem") — this reshaped large parts of the check suite to fail *safely* (named findings, not
  raw crashes or silent false-clean passes) on a product with no clone cache / no reference-site
  page yet.

---

## 2. Superseded and abandoned decisions

- **Template A/B/C bake-off** (original plan) — superseded 2026-08-03 the moment the user pointed
  at a real, already-produced artifact instead: `foss-readme-optimizer`'s own
  `runs/readme-poc/aspose-note-foss__Aspose.Note-FOSS-for-Python/.../golden-review-v1/README.md`.
  **This is the one place foss-readme-optimizer's own prior output was explicitly reused as the
  template seed for the Aspose.org skill** — worth knowing for parity purposes: the "golden
  sample" shape this whole plan converged on and hardened for 51 incidents *originated* in
  foss-readme-optimizer's own output, then diverged heavily from it.
- **The original At-a-Glance Mermaid diagram model** — individually per-node-wired edges
  (`I1 --- PRODUCT --- C1 --- O1`, etc.) — was fully replaced 2026-08-08 (Eleventh incident/MT024)
  by a flat, edge-free chain: `StartingPoints? → PRODUCT → Capabilities → Outputs`. The old model
  is now a *hard-gate violation* (`check_diagram_shape` rejects any `extra_edges`). This reversal
  was itself later found (Thirtieth incident/MT040, 2026-08-14) to be the actual fix for a real,
  reproduced GitHub-rendering "text clipping" bug — the old wired model triggered a real upstream
  `mermaid.js` converging-edge rendering defect; the new flat model structurally cannot trigger it.
- **Draft-mode PRs** — retired 2026-08-10 (MT032). Every PR now opens ready-for-review
  (`gh pr create` without `--draft`) because none of the target repos have branch protection or a
  second reviewer; draft mode was pure friction.
- **"Human clicks the merge button" as the merge mechanism** — superseded 2026-08-11, same
  incident-day, after the human clicked the default "Create a merge commit" button instead of
  "Squash and merge" on `3d/java`'s PR #2, producing a generic wrapper commit with no co-author
  trailer. Reversed to: the **agent** runs `gh pr merge --squash --delete-branch` on the human's
  explicit per-PR go-ahead. Further corrected 2026-08-13 (Twenty-Third incident): the bare command
  form must never be used — always pass explicit `--subject`/`--body`, because `gh pr merge
  --squash`'s own default message construction silently appends a **redundant**
  `Co-authored-by:` trailer for the human operator (who is already the real primary author via
  git's native metadata) — this exact defect shipped twice (`3d/typescript`, `cells/cpp`) before
  being caught and fixed at the root.
- **The "Enterprise Edition anchor names the implementation bridge language" contract** — adopted
  same-day 2026-08-14 (Thirty-Third incident/MT043: `[Aspose.Cells for Python via Java —
  Enterprise Edition]`) then **reversed the same day** (Thirty-Fourth incident/MT044) after the
  user stated "you have made a mess" — a public README must **never** expose *how* one platform
  is implemented through another (no "via Java", "backed by", "wrapper around", "binding to",
  anywhere: anchors, prose, tables, badges, footnotes). The corrected, permanent rule: anchor
  names only the normalized **public platform** (`python-java`/`python-net` → "Python"); a
  compound/bridge URL is used as the destination but never described as such. This is one of the
  plan's most explicit "we built the wrong thing, on purpose, then un-built it same-day" reversals
  — 9 already-composed candidates had already shipped the now-forbidden wording and had to be
  stripped.
- **"C++ is registry-less"** — corrected 2026-08-04: `cells/cpp` genuinely publishes to NuGet
  (`Aspose.Cells.Cpp.FOSS`); C++ install-sourcing now checks NuGet before falling back to
  build-from-source, exactly like .NET.
- **`data/api_reference_class_exclusions.json`'s single "excluded" semantic** — attempted for
  `note/python`'s 2 legitimately-kept-and-disclosed internal classes (MT048), found to collide
  with `check_api_reference_table_completeness`'s *opposite* interpretation of "excluded" (which
  assumes "excluded" means "must never appear in the table," correct for `font/python`'s
  remove-it shape, wrong for `note/python`'s keep-it-disclosed shape) — the addition was
  **reverted live**, not force-fit. Recorded as a deferred schema-design gap, not solved.
- **Two design agents' full-schema vs. "no stored graph at all" bet for capability-dependency
  edges** (2026-08-06) — the lighter, no-storage bet was explicitly disproven by its own advocate
  agent (instructed to defend it past its merits, reported instead that it wasn't adequate) —
  superseded by a minimal stored-JSON design (`data/diagram_capability_dependencies.json`), not
  the heavier agent's full schema either.

---

## 3. Problems discovered during real executions, and fixes (the highest-value content)

This is the plan's dominant mode: dozens of real, source-verified incidents, each following the
same shape (trigger → verified findings → root cause → fix → regression tests → retroactive
sweep). The most load-bearing, reusable lessons:

- **Fabricated/hallucinated capability claims are the single most-repeated defect class across the
  entire plan** — found in diagram nodes (`barcode/python`'s GS1 mode, `3d/net`'s Watermark
  encode/decode both `throw NotImplementedException`), in prose (`cells/cpp`'s false "stub-only"
  AutoFilter claim — the *inverse*, an under-claim, is equally wrong), in API-reference member
  lists (75 fixes across 21/30 products in one 2026-08-05 sweep — combined `ClassA`/`ClassB`
  bullets silently listing only one side's real members), and in dependency prose (`cells/rust`
  claimed "no external runtime... is needed" while depending on 7 real Cargo.toml crates).
  **Standing rule derived from this**: never trust "the old README said so," never trust a prior
  sweep's "no findings," always re-verify against real, current source — this exact discipline is
  invoked by name in nearly every later incident.
- **A real fix, correct once, is never durable unless it becomes (a) written skill-doc guidance
  AND (b) a mechanical check** — named explicitly as a recurring structural weakness at least 6
  times (diagram composition rules, Key Capabilities structure, badge floors, API Reference
  collapse, compound-excerpt drops, image preservation). Each time: an agent fixes something once
  by hand or judgment; a *later*, independent regeneration pass (often a "clean-room" pass with no
  memory of the earlier fix) silently reproduces the exact same defect. **This is the single most
  important structural lesson in the whole plan** for any team building a similar skill.
- **Checks silently go dark for the exact state a new/first-time product starts in.**
  `check_api_reference_classes_exist_in_reference_site` (the strongest anti-hallucination hard
  gate) had a bug where `if reference_class_names or clone_cache_usable:` skipped verification
  entirely — and thus passed cleanly — when *both* sources were absent, i.e. exactly a brand-new
  product's guaranteed starting state (MT035/TC-HARDEN-31, "the single most consequential finding
  of the whole audit"). Contrast: `check_diagram_verified_format_claims`'s 2-of-3-signal design
  gets this right *by construction* (2 of 3 signals are structurally forced False for a new
  product, so it arithmetically cannot pass a fabrication). **Rule extracted**: every hard gate
  consuming an optional/absent data source needs its own explicit, tested "what happens when this
  is completely missing" case — never inferred from its populated-data behavior.
- **Even structured, checked-in "ground truth" data is independently unreliable — repeatedly, not
  once.** `formats.md` (Twelfth incident/MT025-Phase-0c): stale directional flags, missing rows
  for a product's own primary format, spurious junk rows, self-contradiction against the file's
  own prose. `data/package_registry.json` (TC-HARDEN-32): found wrong *in both directions* for
  already-shipped products (`words/net`'s `published: false` stale; `email/net`'s package-name
  casing wrong). `keywords/{family}.json` (MT037): every platform entry for `cells/python`,
  `cells/rust`, `cells/typescript` is contaminated with `.NET`/`C#` keyword phrases regardless of
  the real platform. `content/reference.aspose.org/.../_index.md`: contains a raw, un-stripped
  Python docstring artifact (`r"""`) even in a "grade A" file, and separately (`3d/java`) has 11
  stale rows citing classes that no longer exist in the real source. **Standing design pattern
  this produced**: never hard-gate on a single structured source alone — either corroborate with
  ≥2 independent signals (the format-claims 2-of-3 model) or downgrade to heuristic once live
  evidence proves the source fallible (the package-registry downgrade).
- **A "reconciliation" mechanism and a "does the fresh composition meet a floor" mechanism are two
  different things, and only the first has reliably been built each time a new visible element was
  added.** Named explicitly as the fourth confirmed instance of the same shape (MT042, badge
  floors) after the Enterprise link (MT034), the banner-homepage link (TC-HARDEN-27), and
  Installation-vs-registry accuracy (TC-HARDEN-32). Each time: a reconciliation check correctly
  answers "did we lose something that was in the old README" but nothing answers "does this
  freshly-composed candidate meet a real, verifiable floor" when the old README had *nothing* to
  reconcile against (e.g. `cells/typescript`'s old README had zero badges → the composing agent
  shipped exactly one badge, License-only, and every check passed cleanly).
- **Concurrent-session `.git/index` staleness is a live, repeatedly-recurring hazard** (referenced
  throughout as `[[concurrent_session_git_races]]`, "ST-021"). At least 3 separate incidents found
  the shared index holding a massively stale, already-reverted snapshot of files this session was
  actively editing — a plain `git commit` at that moment would have silently reverted real,
  already-pushed work to a days-old baseline. **Standing mitigation**: never use `git commit`
  directly on this repo's own tracked files for this skill — always use the isolated-temp-index
  `git_plumb_commit.py` path (or manual `git write-tree`/`commit-tree`/`update-ref` plumbing),
  which reads from `HEAD`'s tree, never the corrupted real index. `git stash` is explicitly
  banned for the same reason (it can pop an unrelated concurrent session's stash).
- **A registered, tested, documented skill can be completely bypassed by the real production
  process for weeks** (Nineteenth incident/MT033, "deep production audit"). Direct evidence: zero
  `reports/readme_refresh_runs/` run directories existed on disk at audit time despite ~30
  products' worth of real work; two fully-built, fully-tested hard gates
  (`check_only_mermaid_block_changed`, `check_only_sections_changed`) were never once called from
  `readme_refresh_run.py`; 14 of ~19 relevant commits were mis-trailered to a *different* skill ID
  (S-99); `verify_examples`'s default runner reported `TOOLCHAIN-UNAVAILABLE` for literally every
  code block, unconditionally, for every language — a real, honest no-op that had never been
  fixed. **This produced the plan's Gate Contract rule 5 and Anti-Overclaim rule 7**: "a gate
  being real, tested, and correctly implemented is not the same as being reachable from the real
  production path" and "a skill being registered is not the same as a skill being used." Verified
  directly this session (§13) that this specific gap has since been closed: `_candidate_readme_
  path()` is now the single shared path every real state transition uses, and `reports/
  readme_refresh_runs/` is now populated with real run evidence.
- **A single compound excerpt can silently drop one of several bundled facts past a "does at
  least one token match" check** (Thirty-Ninth incident/MT049) — `note/python`'s `u0020`
  disposition bundled 3 genuinely distinct facts under one shared `salient_tokens` list; the real
  candidate only ever carried the first fact forward, and the check passed because *some* token
  matched *somewhere*. Fixed by splitting excerpts into per-sentence groups and requiring every
  group that owns a token to have *that* token (not just any token from the whole excerpt) match.
  A portfolio-wide read-only sweep with the fixed check found **39 more entries across 8
  products** with the same silent-partial-drop shape (not fixed — logged as deferred remediation).
- **`## Installation`/`## Quick Start` were deliberately exempted from the main upstream-issue-leak
  hard gate** (because ordinary specificity there legitimately overlaps upstream-issues.md's own
  evidence) **— which left those two sections with zero hard-gate leak protection at all**
  (Fortieth incident/MT050). `html/python`'s Installation section regressed into full forensic
  narration (exact broken build-backend string, exact error message, "every variant fails
  identically") with nothing blocking it. Fixed with a narrow, purpose-built companion detector
  requiring **both** (a) 2+ concurring upstream-issue fingerprint tokens **and** (b) a match
  against a small, high-precision diagnostic-narration phrase list — deliberately *not* reusing
  the broad phrase list, which would have false-positived on legitimate Installation specificity.
- **A disposition's own `unit_id` is a pure position-based counter, not a content hash** — editing
  earlier content shifts every later unit's ID, silently mis-mapping disposition entries to the
  wrong excerpt (MT030 Phase 2, recurring; formally closed for good in Thirty-Eighth
  incident/MT048 via `check_content_unit_excerpt_matches_extraction`, which re-validates every
  disposition's stored excerpt against a fresh live extraction). **A live portfolio dry-run with
  this new gate found only 2 of 30 products clean** — the other 28 show real, non-theoretical
  disposition-file drift, logged as the single largest deferred-remediation item the plan
  currently carries.

---

## 4. Portfolio-wide invariants (apply to every candidate regardless of family/platform)

- **Every candidate must pass the full deterministic check battery** (92 real functions as of
  2026-08-17) before `AWAITING_REVIEW`; hard-gate failures block the transition, heuristics never
  do (Gate Contract rule 1).
- **No process/investigation-log narration anywhere in the README** — hedging ("at the time of
  writing"), verification-report narration ("passes cleanly", "was verified"), self-referential
  "reproduced from its own README" framing, "(per...)" audit-trail citations, meta-commentary
  about the README's own generation/pipeline, and (later, generalized, MT039/MT046) narrating the
  *document's own organizational choices* ("grouped by real module rather than by workflow
  label") or internal source-file facts ("`instancing.py` alone is the largest module").
- **No internal-artifact citation of any kind** — `upstream-issues.md`, `content-dispositions.
  json`, `.clone_cache`, `knowledge/.../merged`, `reports/repo-presenter*` must never be named or
  paraphrased in public README text (`_INTERNAL_LABEL_PATTERNS`, unconditional hard gate).
- **Genuine upstream defects live exclusively in `upstream-issues.md`, never in the README body**
  — a plain, non-forensic pointer sentence is allowed when a real workaround exists; forensic
  detail (exact error text, exact counts, reproduction steps) is banned from the README in every
  section, not just near an obvious "Known issue" callout.
- **Never drop original-README content without a verified reason** — every link/claim/file
  reference in the old upstream README must be carried forward (verified accurate) or explicitly
  logged with a real reason in `content-dispositions.json`; "the old README had it" is also never
  sufficient to *include* something without independent re-verification (cuts both directions).
- **No fabricated capability, ever** — a diagram node, a Key Capabilities bullet, an API-reference
  member, or a dependency claim must be independently verified against real, current source before
  shipping; this is the plan's own named "single worst defect class."
- **Exactly one Enterprise Edition mention, confined to Scope and Limitations**, using verified
  target-resolution data (never a guessed slug), family-neutral or platform-name-only anchor text,
  never exposing implementation-bridge details anywhere in the document.
- **`forum.aspose.com` and any `*.aspose.app` subdomain are permanently, hard-gate-banned links**
  — a standing policy decision, not a content gap.
- **License section is a byte-fixed template** (linked or unlinked variant only) — never free-form
  prose, mechanically enforced (`check_license_section_matches_template`, not just the link-target
  check).
- **Banner image is mandatory, links to the verified `products.aspose.org/{family}/{platform}/`
  homepage when that page is confirmed to exist locally, otherwise stays unlinked** — never a
  guessed link.
- **A badge row must contain License (when available) plus at least one more badge from
  {package_version, language_version, ci_build_status, contributor_count}** — never mandates a
  *specific* second category (multiple legitimate editorial choices exist across the real
  portfolio); `contributor_count` is the always-available safety net.
- **`## Dependencies` is a required section** (after Installation, before Quick Start) with a
  fixed 4-subsection template and a hard ban on unqualified absolute dependency-free claims
  ("no external dependencies", "dependency-free", bare "no external runtime" with no scope
  qualifier).
- **Idempotency/section-isolation**: a scoped edit must touch only its declared section(s)
  (`check_only_sections_changed`), and re-running the deterministic machinery against identical
  input must produce byte-identical output — explicitly *not* claimed for fresh LLM prose
  composition itself, only for the deterministic checking/extraction layer.

---

## 5. Platform-specific rules

- **Per-language dependency-manifest parsing** (7 real ecosystems, `dependency_extract.py`):
  Rust (`Cargo.toml` via `tomllib`, `[dev-dependencies]` never leaks into Required, `[target.
  'cfg(...)'.dependencies]` → `platform_condition`), Python (`pyproject.toml` PEP 621, `setup.py`-
  only is **never** `exec()`'d — raises with a named override escape hatch instead), .NET
  (shortest-path `.csproj` selection, `PackageReference` in attribute or child-element form), Java
  (`pom.xml`, default-namespace stripping required or `.//dependency` silently returns zero,
  `<scope>test</scope>` → dev-only, `<dependencyManagement>` excluded — it's defaults, not real
  deps), Go (`go.mod`, `// indirect`-commented `require` lines excluded — never leak transitive
  deps), npm/TypeScript (`package.json`, `optionalDependencies` → optional), C++ (checks for
  `CMakeLists.txt`/`vcpkg.json`/`conanfile.*` at root and one level down; genuine absence →
  `applicable: false` with a real, verified reason, never an error).
- **Per-language `verify_examples` runners**: only Python has a real one
  (`--python-runner`, opt-in, real disposable venv + real `pip install`/editable-clone-install +
  real execution). The other 6 languages (Java/.NET/Go/Rust/C++/TypeScript) remain an honest stub
  returning `TOOLCHAIN-UNAVAILABLE` for every block, unconditionally — explicitly disclosed as
  unfinished work, not silently smoothed over, throughout the plan's later half.
- **Per-language class-source discovery for member-accuracy checks**: originally hardcoded to 9
  extensions (`.py .java .cs .go .rs .cpp .hpp .h .ts .c`), widened (TC-HARDEN-34) to include
  `.php`, `.kt`/`.kts`, `.rb`, `.swift` — a deliberate, bounded widening, not open-ended.
- **C++ install sourcing**: NOT registry-less (corrected 2026-08-04) — check
  `data/package_registry.json`/live NuGet before falling back to build-from-source.
- **Go install sourcing**: no live registry check needed — Go modules are decentralized; read
  `go.mod`'s module path and check for a real semver git tag directly in the clone cache.
- **Enterprise-link public-platform normalization**: `backlink_targets.PLATFORM_ALIASES`
  normalizes compound bridge slugs (`python-java`, `python-net`, `go-cpp`, `nodejs-cpp`, etc.) to
  their base platform; `_PLATFORM_DISPLAY_NAMES` renders the human-readable form. This is reused,
  never re-derived per product.
- **Per-language internal-fan-in leak detection** (`_module_internal_fan_in`,
  `_find_top_level_init_exports`): Python-first only (MT047), explicitly deferred for every other
  language; even within Python, found a real bug (MT048) where a 2-level PEP 420 namespace
  package layout (`src/aspose/{family}/__init__.py`) was invisible to a glob assuming a flat
  1-level layout — silently defeated the whole heuristic for `note/python` until fixed.

---

## 6. Product-specific exceptions

- **`cells/typescript`** — formally excluded in `data/registry_exclusions.json`
  (`BLOCKED_REPO_NOT_LAUNCHABLE`) for the internal site-launch pipeline, but a direct user
  instruction to push its README PR was treated as valid, narrower authorization for *that one
  external action* without touching the exclusion file itself.
- **`pdf/cpp`, `pdf/go`** — the only two products classified `hybrid` archetype
  (`data/diagram_archetypes.json`), meaning their diagrams get a 2-line `Starting Points`
  container (`"An existing X document"` / `"Nothing — authored from scratch"`); re-verification of
  this classification is date-stamped and must be refreshed against real current source, not
  blindly date-bumped, whenever the freshness check trips (`check_diagram_hybrid_reverification`).
  **`page/python` was formally added as a third hybrid entry** in MT051 (2026-08-16) after direct
  source verification (`PsDocument.create()`, `XpsDocument.create()`, `PsCanvas`,
  `XpsDocumentBuilder`) — and the from-scratch claim was further proven by *live execution*
  (23/23 real API calls run, round-tripped, and converted to real PDF bytes), not just static
  source reading.
- **`barcode/python`** — the only `generative` archetype (no `Starting Points` container at all;
  "does not read or decode existing barcode images for any symbology").
- **`tex/python`** — the only `compile` archetype (Inputs are caller-authored TeX/LaTeX source,
  not a pre-existing binary format).
- **`3d/typescript`** — the sole product whose `reference.aspose.org` index uses individual `###
  ClassName` headings instead of the table convention every other product uses; required a
  dedicated parser fallback (`_parse_class_heading_module`) rather than being permanently excluded
  from the API-Reference-table system.
- **`words/net`** — the sole product with a real `### Project History` section (MT031), because
  its old README's DOC-format reverse-engineering/WordML→OOXML history was judged genuine,
  checkable product provenance, not marketing narrative — explicitly *not* a portfolio-wide
  template addition; every other product stays without this section unless independently earning
  it the same way.
- **`3d/net`/`3d/python`** — the confirmed source of the plan's real, reproduced GitHub-rendering
  clipping bug (Thirtieth incident/MT040); both had never been migrated to the flat diagram model
  during the 2026-08-11 sweep that fixed their siblings `3d/java`/`3d/typescript`, and both are
  confirmed to have real, currently-visible clipped node text on their live, published READMEs at
  time of the incident.
- **`words/net`, `email/cpp`, `slides/cpp`** — the only products where a specific unpublished-
  package-registry phrasing beyond "has not been published yet" needed a regex widening for
  `check_installation_matches_package_registry`.

---

## 7. Original-README preservation rules

The mechanism evolved substantially over the plan's life; the **final, layered state** (as of
MT047-MT049) is:

1. **Links and H2/H3 headings** — `_old_readme_inventory` extracts every relative link and every
   heading; `check_dropped_content` (hard gate) fails on any that don't reappear (literal
   substring, casefolded/emoji-normalized) in the new candidate — unless a real
   `content-dispositions.json` exists for the product, in which case this downgrades to an
   advisory finding (`dropped_content_uncorrelated`), since the disposition file is the more
   precise, authoritative accounting (TC-HARDEN-04).
2. **Prose-level content units** (MT030) — `extract_old_readme_content_units` segments the old
   README (fenced code stripped first) into paragraph/bullet-sized units; every unit needs an
   explicit `content-dispositions.json` entry: `classification` ∈ `{1_narrative_cta,
   2_mechanism_explanation, 3_branding_positioning, 4_verifiable_history, 5_dependency_claim,
   redundant_with_existing}`, `disposition` ∈ `{merged_verbatim, merged_reframed, corrected,
   excluded}`, `verification.status` ∈ `{verified_against_source, verified_by_corroboration,
   verified_against_manifest, verified_redundant, not_applicable_category_1}`. **Absence of a
   disposition for a real unit is a hard-gate failure**, never a silent default — this is
   deliberately stricter than the archetype-file convention (where absence defaults to
   `transform`).
3. **Category-1 (pure narrative/CTA/origin-story) content is explicitly, permanently out of
   scope** — never merged, by a direct 2026-08-09 user decision — *unless* a mixed unit bundles a
   real, checkable fact with pure tone (MT031: reclassify to the real category, drop only the
   non-checkable hedge, never exclude the whole unit wholesale).
4. **Structural content invisible to the prose extractor** (a directory tree, a badge row, a large
   code example) gets its own sibling extractor + disposition file:
   `extract_old_readme_structural_units` / `structure-dispositions.json` (MT036, the `cells/go`
   mission), `extract_badges`/`badge-dispositions.json` (same mission), `extract_old_readme_code_
   units`/`code-example-dispositions.json` (MT047 — **unconditional**, fixing a real bug where the
   structural extractor skipped a section the moment *any* prose survived alongside a large code
   block, making a section that mixed code + one trailing sentence invisible to *both*
   extractors simultaneously).
5. **A disposition's own evidence must mechanically resolve**, not just be asserted:
   `check_content_unit_evidence_resolves` for clone-cache-path/package-registry-field/docs-
   reference evidence types; `check_content_unit_merged_into_target_section` requires the unit's
   own salient tokens to actually appear in the cited target section (word-overlap fallback when
   no exact quote exists) — **and, since MT049, per-sentence-group**, not whole-excerpt, so a
   compound multi-fact excerpt can't pass on one fact's token while silently dropping another.
6. **A disposition's `unit_id` is position-based and drifts** the moment earlier content is edited
   — `check_content_unit_excerpt_matches_extraction` (MT048) re-validates every entry's stored
   excerpt against a fresh live extraction to catch this; a live sweep found this drift present
   in 28 of 30 products (unremediated, logged as the largest deferred item).
7. **Verify before including cuts both ways** — a carried-forward claim is not exempt from
   verification just because it was already in the old README; version floors, format-support
   claims, and code examples must all be independently re-checked against current real source
   before landing in the new candidate.

---

## 8. Presentation and prose rules

- **Section order** (final template, `_REQUIRED_SECTIONS`): title → badge row → banner image (→
  `### Project History`, H3, optional, product-specific only) → Intro paragraph → Navigation → At
  a Glance (Mermaid) → Key Capabilities → Installation → **Dependencies** → Quick Start →
  Additional Examples → API Reference → Documentation & Resources → Scope and Limitations →
  Development and Testing → License.
- **Badge row**: License (when available) + ≥1 more from {package_version, language_version,
  ci_build_status, contributor_count}; never a specific mandated second category.
- **Banner**: `products.aspose.org/media/{family}/{platform}/banner-readme.png`, placed
  immediately after the badge row; linked to the verified homepage when confirmed to exist,
  otherwise plain/unlinked (never a guessed link, and never the raw GitHub social-preview URL,
  which is a signed, 5-minute-expiring URL — confirmed via JWT decode, not assumption).
- **At a Glance Mermaid diagram**: flat, unwired `StartingPoints? → PRODUCT → Capabilities →
  Outputs` chain, ≤5 capabilities in 1 column / ≥6 in 2 balanced columns, every node/label token
  ≤28 characters (rendering-safety ceiling, MT040), every format claim independently corroborated
  by ≥2 of {formats.md directional flag, prose mention with negation-override, source-evidence
  suffix match} before being trusted — **never** rely on `formats.md` alone. No custom
  `classDef`/color styling (deliberate — default Mermaid theming already reads correctly across
  GitHub light/dark).
- **Key Capabilities**: 4–12 bullets, real backtick-quoted identifiers woven into natural
  sentences (never a bare undifferentiated list), lead with the single most differentiating
  capability (not architecture/plumbing), consolidate near-duplicate single-format bullets into
  one, structural-opening variety required (≥70% identifier-first-opening is a flagged smell), SEO
  keyword phrases woven naturally in 2–4 spots (never bold/backtick-highlighted, capped at 6
  filtered phrases, platform-contamination-filtered), an intro framing sentence (if present) must
  describe real product architecture — never the document's own organizational choices or an
  internal source-file fact (the "would this be true if the README were rewritten from scratch"
  test).
- **Additional Examples**: intro sentence → one flagship example shown directly (not collapsed) →
  `<details><summary>View additional examples</summary>` wrapping everything else, **including**
  any exhaustive example-inventory table (not just the prose walkthroughs).
- **API Reference**: intro sentence must name real, verified hub classes (never a bare type-count
  or namespace wildcard) → module-grouped table mirroring `reference.aspose.org`'s own real
  organization (verbatim structure, rewritable descriptions when the source is filler/truncated/
  has a stripped-example artifact) → `#### Detailed Member Reference` divider → the pre-existing
  curated `` - `ClassName` `` bullet subsections, unchanged. **The entire detail block —
  table and bullets — must sit inside exactly one `<details>` wrap, unconditionally, regardless of
  row/class count** (proven size-independent via `tex/python`'s 11-class table still being
  wrapped).
- **Scope and Limitations**: a bulleted list only (prose paragraphs are a hard-gate failure),
  optional bold category sub-labels only once there are enough items to group (~8+, 3+
  categories), closed by a **separate, non-bulleted, blank-line-delimited standalone paragraph**
  naming the Enterprise Edition upsell with 2–4 concrete capabilities drawn from the bullets above
  it — never merged into a bullet's own wrapped continuation text.
- **Enterprise Edition anchor**: `[Aspose.{Family} for {Public Platform} — Enterprise Edition]
  (url)` for a platform-specific destination, `[Aspose.{Family} — Enterprise Edition](url)` for a
  family-level fallback (used only when no platform-specific page exists at all) — never an
  implementation-bridge qualifier anywhere in the document.
- **License**: byte-fixed template sentence (linked-relative-path or unlinked variant), no
  free-form prose, verified by "starts with" (so real, legitimate extra content like `pdf/go`'s
  bundled third-party font disclosure can still follow).
- **Screenshots/visual proof-of-capability**: preservable via `## Additional Examples`'s own
  subsection pattern (e.g. `### Example Results`); "the template has no section for this" is
  explicitly, permanently banned as an exclusion justification (MT051), given real,
  already-shipped portfolio counter-examples.
- **Headings**: title case everywhere, including `<summary>` text, with one documented exception
  (`glTF`/`GLTF` — a genuine branding-casing conflict with Rule 6, resolved as
  all-caps-in-headings/mixed-case-in-body).

---

## 9. Fact verification and freshness rules

- **Install/package identity**: `data/package_registry.json` first (read-only), then a live
  registry check (PyPI JSON API, NuGet flatcontainer, npm registry, Maven Central metadata, or a
  real `git tag` check for Go) — never invents a specific version/command not backed by one of
  these. Downgraded from an originally-planned hard gate to a heuristic once live evidence proved
  the registry file itself independently wrong in both directions for shipped products.
- **License file**: real, case-sensitive on-disk detection (a 200-character case-insensitive
  substring search for "mit license", widened from an original 20-char exact-prefix match that
  missed real "The MIT License (MIT)..." files) — never assumed, never left for the agent to
  search.
- **Enterprise link target**: `backlink_targets.resolve_backlink()` against the cached
  `data/aspose_com_targets.json` target map, with `data/backlinks/platform_canonical_overrides.
  yaml` consulted first for the narrow, dated, human-curated cases where the cache is known stale
  — never a guessed slug. `target_map_age_days()` surfaces staleness as reduced-confidence
  evidence, never silently treated as fresh.
- **Homepage link**: real, local `content/products.aspose.org/en/{family}/{platform}/_index.md`
  file-existence check (a first-party, same-repo-deploy guarantee, deliberately stronger than the
  Enterprise link's external-site case) — deliberately *not* a live HTTP check by default (cost
  vs. benefit tradeoff, explicitly disclosed as an open question).
- **Format claims in the At-a-Glance diagram**: 2-of-3 multi-signal corroboration
  (`check_diagram_verified_format_claims`) across `formats.md`'s directional flag, prose mention
  (with an "import-only"/"export-only" negation-override), and `api_surface.json`/clone-cache
  source-evidence (directional suffix matching: `Writer`/`SaveOptions`/`Exporter` → export;
  `Reader`/`LoadOptions`/`Importer` → import). Built specifically because `formats.md` alone was
  proven unreliable.
- **API Reference class citations**: every backtick-quoted class name in the curated bullets must
  exist in `reference_api_index` (real, parsed from `reference.aspose.org`'s own `_index.md`) —
  and, since MT031's fix, an absent-both-sources state produces a real, named "verification
  unavailable" finding per cited class rather than a silent pass.
- **Dependency claims**: real, structured parsing of the actual manifest file (never regex-
  guessing) is authoritative; `claims.json` (scout/LLM-derived) is confirmed to be a lossy,
  possibly-differently-timed re-parse of the *same* manifest, not independent data — used only as
  a secondary, non-authoritative corroboration/staleness signal.
- **Code examples**: `verify_examples` state — real for Python only (disposable venv, real
  `pip install`, real execution, honest `RUNTIME-ERROR`/`ACQUIRE-FAILED`/`TOOLCHAIN-UNAVAILABLE`
  classification); every other language is an honest, disclosed no-op stub.
- **Internal-class leak detection**: `_module_internal_fan_in` (does any other file reference this
  class) + `_find_top_level_init_exports` (is it in `__all__`) + `_class_has_exported_subclass_in_
  same_file` (a public exception's private base shouldn't false-positive) — Python-only,
  heuristic-tier, validated against exactly 2 real products' control pairs, explicitly not yet
  portfolio-proven (a full run didn't complete within a timed background window and was stopped).

---

## 10. Validation and certification behavior (the actual gates, not just their names)

- **Two tiers only** (Gate Contract rule 1): `hard_gate: True` blocks the state transition
  (`ingest-candidate`'s `PLANNED → VERIFYING_EXAMPLES`); `hard_gate: False` (heuristic) never
  blocks, only surfaces a finding for the mandatory human/agent judgment pass. No third tier.
- **A gate is not trusted until proven to fail closed** on a deliberately-wrong fixture — required
  for every hard gate added since MT021, without exception, as a committed regression test.
- **A gate is not trusted until run against real portfolio content**, not just synthetic fixtures
  — every single mission in the plan's history found at least one real bug in its own newly-added
  check this way (regex desyncs, false positives on real homonyms, silent no-ops on real edge
  cases) before the check could be trusted.
- **~92 real `check_*` functions** as of 2026-08-17 (the skill doc's own self-reported count
  drifts and is explicitly told to be re-verified via `grep -c "^def check_"` before trusting it —
  confirmed live: doc says 91, real count is 92, a one-function drift the doc itself anticipates).
  Spanning: diagram shape/balance/starting-points/format-purity/verified-claims/hybrid-
  reverification; License link+template; process-narration; dropped-content+internal-labels;
  named-member-accuracy; API-reference-class-existence+table-completeness+no-duplicate-rows+
  generic-description+truncation+stripped-example+detail-collapse; banner-present+links-to-
  homepage; Enterprise-edition-naming+link-resolves+anchor-matches-relationship+no-implementation-
  bridge-disclosure; badge-row-floor+available-fact-not-shown; content/structural/badge/code-
  example-unit disposition-coverage+evidence-resolves+no-duplicate-merge+merged-into-target-
  section+excerpt-matches-extraction; scope-limitations-format; key-capabilities-quality+
  structural-variety+formatting; section-intro-no-meta-narration; dependency-section-completeness
  +unqualified-claims+direct-transitive-confusion+optional/dev-misplacement+scope-claim-evidence+
  version-pin-freshness+native-system-placement+disposition-reconciliation; installation-matches-
  package-registry; upstream-issue-leak (main + Installation/Quick-Start companion); code-example-
  imports-match-source; project-structure-canonical-tree-format; diagram-container-duplicates-
  capability; format-name-casing; cross-product-citation; heading-title-case; section-isolation
  (`check_only_sections_changed`, `check_only_mermaid_block_changed`).
- **Certification is per-product, not portfolio-wide by default** — `readme_refresh_run.py
  audit-portfolio` (built MT035/TC-HARDEN-05) is the real, registered, tested tool for running the
  full battery against every product's *already-existing* candidate on demand; there is **no
  automated recurring/CI trigger** for this — a deliberate, disclosed, deferred decision, since
  `reports/` is entirely gitignored so GitHub CI structurally cannot see this content at all.
- **A passing gate proves only its own narrow claim** (Anti-Overclaim rule 2) — e.g.
  `check_dropped_content` passing never means surviving content is *accurate*, only that nothing
  known-dropped is missing; a "0 heuristic findings" result means "no contradiction found," never
  "verified correct."

---

## 11. Resume, retry, and recovery behavior

- **`BLOCKED` state** captures `resume_state` (the state to re-enter on `recover`) — reached by any
  caught, named exception (dependency extraction failure, a hard-gate `ingest-candidate` failure,
  a push failure) via a single, reused `_block(manifest, reason) → raise ReadmeRefreshRunError(...)
  from exc` shape (proven at `push()`'s own call site, then reused verbatim for `plan_run`'s
  dependency-extraction failure path in MT041 — "no new BLOCKED sub-mechanism").
- **`recover --reason TEXT`** restores run-owned paths from the pinned base commit **only if
  on-disk bytes still match the validated receipt** — never touches a path it doesn't own.
- **`approve` re-verifies pinned inputs haven't drifted** (clone-cache HEAD unchanged since
  `plan`) — if they have, it forces back to `PLANNED` for re-review rather than approving stale
  content.
- **Every mutating call is checked against `manifest.session_owner`** — a different session
  cannot touch someone else's run (via `--session-id`/`AGENT_SESSION_ID`/`CODEX_THREAD_ID`), and
  one `ACTIVE.json` + `FileLock` per `(family, platform)` prevents two runs owning the same product
  concurrently.
- **`push` sub-steps are independently idempotent/re-checkable** — a `BLOCKED` run during
  `PUSHING` can resume by re-running `push`, which detects an already-existing branch/PR and skips
  redoing it rather than duplicating.
- **`abandon --reason TEXT`** is the standard way to release a product lock after a
  verification-only run that was never meant to push — used repeatedly throughout the plan's
  later half for proof-of-concept/verification-only CLI runs (e.g. the first-ever real
  `start→push --dry-run` chain, TC-HARDEN-13).
- **Deterministic-machinery idempotency is proven, LLM-composition idempotency is explicitly NOT
  claimed** — a recurring, honestly-stated distinction (first made explicit in the Twentieth
  incident/MT034): re-running the extraction/checking layer against identical input must produce
  byte-identical structured output (and repeatedly is proven this way, with real SHA-256 hashes,
  run twice); re-running a fresh LLM composition pass is never claimed to reproduce byte-identical
  prose, and no mechanism in this plan attempts to guarantee it.

---

## 12. The real execution path of the actual skill implementation

Concrete, verified (not inferred) as of 2026-08-17:

- **Skill doc**: `D:\onedrive\Documents\GitHub\aspose.org\skills\readme-refresh.md` (925 lines,
  `id: S-120`, `args: "{family} {platform}"`). Thin CONTRACT-header doc pointing at the backing
  script as canonical — matches the plan's own stated `refresh-product`-style design intent
  exactly. Contains: state-machine diagram, CLI subcommand list, 9-step procedure, composition-
  guidance subsections (tone-exemplar reading + contamination guard; Enterprise-link anchor
  contract; dependency terminology + Claims Policy; SEO-keyword filtering; diagram composition
  rules; banner/homepage-link rules; License template; API-Reference-collapse rule;
  image-preservation rule; a "product facts vs. document structure" general narration-avoidance
  principle), an "Onboarding a new product, platform, or family" section, and an honest,
  self-updating check-function count.
- **Backing script (the state machine)**:
  `scripts/pipeline/commands/foss/readme_refresh_run.py` (2,919 lines). CLI subcommands, confirmed
  live in `main()`: `start, plan, ingest-candidate, recheck, verify-examples, status, verify,
  approve, push, abandon, recover, audit-portfolio`. **Two distinct real path roots**:
  `_run_root(family, platform, run_id)` → `reports/readme_refresh_runs/{family}/{platform}/
  {run_id}/` (per-run evidence: `manifest.json`, `facts/factpack.json`, `checks/result.json`,
  `verification/result.json`, `push/receipt.json`, `events.jsonl`); `_candidate_readme_path
  (family, platform)` → `reports/repo-presenter/{family}/{platform}/readme.md` (the single,
  canonical, run-independent candidate location every state transition actually reads/writes —
  this is the fix TC-HARDEN-13 proved was already correctly wired, contrary to the earlier MT033
  audit's assumption that a new binding needed to be built). Sibling artifacts at the same
  candidate path: `upstream-issues.md`, `content-dispositions.json`, `structure-dispositions.
  json`, `badge-dispositions.json`, `code-example-dispositions.json`.
  `_run_deterministic_checks` (from line 1499) genuinely imports and calls `readme_refresh_checks.
  check_*` functions with real `hard_gate` flags, plus fresh (never-cached) `_detect_*` calls
  (archetype, capability-dependency edges, enterprise link, homepage, license file, SEO keywords,
  dependency snapshot via `dependency_extract.extract_dependencies`, available badges, install
  info) — this is the real factpack-construction + check-wiring layer.
- **Checks module**: `scripts/pipeline/commands/foss/readme_refresh_checks.py` (7,897 lines, 92
  real `check_*` functions, confirmed via `grep -c "^def check_"`). Module docstring explicitly
  documents the two-tier HARD GATE / HEURISTIC model and groups functions by concern (diagram
  checks, content/prose checks, disposition-unit checks for 4 parallel disposition-file families).
- **Dependency-extraction module** (new, MT041): `scripts/pipeline/commands/foss/
  dependency_extract.py` (~43KB) — a deliberately separate sibling module (not folded into either
  file above; not importing the unrelated `package_manifest.py` used by the knowledge-pipeline
  skill, due to different revision-pinning semantics), `DependencyEntry`/`DependencySnapshot`
  TypedDicts, `DependencyExtractionError`, 7 real per-ecosystem extractors, stdlib-only parsing.
- **Prompt/composition location**: there is **no prompt file and no template engine anywhere in
  this architecture** — the module docstring states explicitly "the script does not write README
  prose," and the plan confirms this architecturally at least twice (MT033's audit, MT045's root-
  cause table: "no template engine exists anywhere in this architecture... composition is uniform
  free-text generation from a shared factpack"). The composing **agent** (a Claude session, inside
  or outside a sub-agent dispatch) reads `facts/factpack.json` plus the skill doc's own
  composition-guidance prose and writes `reports/repo-presenter/{family}/{platform}/readme.md`
  directly via `Read`/`Edit`/`Write` tool calls — there is no intermediate rendering step.
- **Data sources actually read** (confirmed real, on-disk): `data/products.json`,
  `data/registry_exclusions.json`, `data/families.json`, `data/package_registry.json`,
  `data/diagram_archetypes.json`, `data/diagram_capability_dependencies.json`,
  `data/api_reference_class_exclusions.json`, `data/backlinks/platform_canonical_overrides.yaml`,
  `data/aspose_com_targets.json`, `keywords/{family}.json`. **`data/dependency_overrides.json`
  is documented (both in the skill doc and in `plan_run`'s own error message) as the escape hatch
  for an unparseable manifest, but does not exist on disk** — a real, currently-open gap between
  documented and actual state.
- **Test suites**: `scripts/pipeline/tests/test_readme_refresh_run.py` (103 tests),
  `test_readme_refresh_checks.py` (605 tests), `test_dependency_extract.py` — all real, all
  passing per the plan's own final closure notes (698/698 scoped as of MT051).
- **Evidence on disk**: `reports/readme_refresh_runs/` exists and is populated (real run
  directories under `3d/`, `barcode/`, `cells/`, `email/`, `note/`) — contradicting the earlier
  MT033 finding that it was entirely empty; this gap has since been closed by real use.
  `reports/repo-presenter/` has all 30 real product subfolders; only 2 of 30 have
  `structure-dispositions.json`/`badge-dispositions.json` and only 1 of 30 has
  `code-example-dispositions.json` — the newest disposition-file requirements substantially
  outpace actual portfolio coverage.

---

## 13. Divergences between the plan's stated design and what the real implementation actually does

- **"reports/readme_refresh_runs/ does not exist" (MT033, 2026-08-11) is now false.** It exists
  and is populated with real run evidence. This was the plan's own headline finding at the time
  ("the registered skill has never once been the actual mechanism producing real work") and has
  since been substantively closed by real use — confirmed directly on disk, not merely claimed in
  the plan's later prose.
- **The plan's own repeatedly-stated "two parallel candidate trees, no canonical answer" framing
  is more alarming than the code actually is.** At the *code* level there is exactly one canonical
  answer: `_candidate_readme_path()` only ever resolves to `reports/repo-presenter/`. The second
  tree, `reports/repo-presenter-regen-full/`, has its own `_briefing.md` explicitly framing it as
  a sandboxed, read-restricted clean-room comparison exercise ("you must NOT read [the shipped
  candidate] until you are completely done"), not a competing production path — the "which tree
  wins" ambiguity the plan repeatedly flags (MT047 §"Open, disclosed question") is real at the
  *content-currency* level (both trees get real edits, and it's easy for a reader of the plan to
  assume genuine architectural ambiguity) but not at the code-path level.
- **`data/dependency_overrides.json` is real, load-bearing documentation (both in `skills/
  readme-refresh.md` and in `plan_run`'s own live error-message text) for a file that does not
  exist.** Any product whose manifest is genuinely unparseable-without-execution today would
  `BLOCKED` and the documented recovery path ("add a verified entry to `data/
  dependency_overrides.json`, then `recover`") would fail until someone creates the file for the
  first time.
- **The skill doc's self-reported function count is stale by exactly the margin it warns about.**
  `verified: 2026-08-16` header says "91 `check_*` functions... re-verify before trusting this
  number again" — the real, live count is 92. This is not a defect exactly (the doc anticipates
  drift and tells the reader how to check), but it means **any count cited in the plan's own prose
  for a given date should be treated as a lower bound, not a current fact**, when read after that
  date.
- **The plan's claim that "structure-dispositions.json / badge-dispositions.json /
  code-example-dispositions.json" are now hard-gate-enforced portfolio-wide requirements
  substantially overstates actual coverage.** The check functions are real and wired
  (`check_structural_unit_disposition_coverage`, `check_badge_disposition_coverage`,
  `check_code_example_disposition_coverage`, etc.) but only 2 of 30 products have the structural/
  badge files and only 1 of 30 has the code-example file. Running `audit-portfolio` today against
  the other 27–29 products would very likely produce real hard-gate failures for a requirement
  that was never actually satisfied for them — this is explicitly disclosed inside the plan itself
  (MT047/MT048's own "deferred remediation inventory," the largest items the plan currently
  carries) but is easy to miss if a reader samples only the plan's "CLOSED" mission headlines
  rather than each mission's own "Not done in this pass" disclosure.
- **Everything from MT041 onward (2026-08-14 through 2026-08-16, roughly the last third of the
  plan) is real, committed-adjacent, but was — as of the plan's own last entries — still staged/
  uncommitted in the working tree**, by explicit, repeated instruction ("do not commit," "do not
  run the full background test suite"). The live git check this session confirms this is *still*
  true right now: `readme_refresh_checks.py`, `readme_refresh_run.py`, `dependency_extract.py`,
  and `skills/readme-refresh.md` all show live uncommitted diffs (`git diff --stat HEAD`: 7 files,
  +400/-17) on top of the last real commit (`53ec79230b`, 2026-08-16 13:51). A reader treating the
  plan's "CLOSED" mission language as equivalent to "landed and durable" should instead check git
  status directly — closure in this plan means "the taskcard's own acceptance criteria were met
  this session," not "committed."
- **The plan's own prose is, by its own repeated admission, not reliable evidence that a
  component is wired in — this is stated as a formal rule (Anti-Overclaim rule 8) after being
  proven wrong twice** (the 2026-08-04 Enterprise-link note named the right infrastructure but the
  code never consumed it until MT034; the 2026-08-04 License-template rule was stated in prose but
  the check only ever verified the link target, not the prose, until MT044/MT045-adjacent work).
  **This is the single most important meta-lesson for reading this plan or any similarly-shaped
  one**: a rule described in the plan's narrative text is a design intent, not proof of
  implementation — always cross-check against the real, current `check_*` function list and its
  live wiring in `_run_deterministic_checks`, which is exactly what this synthesis's own §12 did.
