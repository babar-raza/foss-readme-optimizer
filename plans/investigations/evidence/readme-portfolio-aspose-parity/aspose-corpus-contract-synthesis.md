# Aspose.org `repo-presenter-regen-full` corpus — the proven README contract

Source: all 31 candidates under `D:\onedrive\Documents\GitHub\aspose.org\reports\repo-presenter-regen-full`
(3d×4, barcode×1, cells×7, email×3, font×1, html×1, note×1, page×1, pdf×5, slides×4, tex×1, words×2),
read in full by parallel research agents on 2026-08-17. This is the operational quality bar the
product owner wants this repo's local README portfolio to match.

## 1. The fixed template (enforced, not incidental)

Every one of the 31 candidates uses the **same section skeleton in the same order**, with only two
conditionally-present sections:

1. `# <Product>` (H1 title)
2. Badge row (one line, directly under H1)
3. Banner image (own line, directly under badges, before any prose) — clickable, links to
   `https://products.aspose.org/<family>/<platform>/`
4. Intro paragraph (2-4 sentences: what/license/language, then a concrete capability/differentiator
   sentence, occasionally a third sentence for a standout feature)
5. `## Navigation` — a bullet list of `[Heading](#anchor)` links to every H2 below
6. `## At a Glance` — one Mermaid `flowchart TD`: `StartingPoints --> PRODUCT --> Capabilities --> Outputs`,
   `Capabilities` split into two side-by-side sub-subgraphs (`capl`/`capr`) when there are enough nodes
7. `## Key Capabilities` — flat bullets, each a dense, identifier-heavy sentence naming real
   classes/methods in backticks; no marketing adjectives
8. `## Installation` — package-manager command if published, otherwise an honest "not yet published,
   install from source" with git-clone/build commands; NEVER a install command that would fail
9. `## Dependencies` *(present only when there's something real to disclose — omitted for platforms
   with zero external deps)* — up to 4 subheadings: Required Package Dependencies, Optional
   Dependencies, Native and System Requirements, Development Dependencies. "No required third-party
   package dependencies." is stated explicitly as its own sentence, never left implicit.
10. `## Quick Start` — one or two complete, runnable snippets, each with a one-sentence task lead-in
11. `## Additional Examples` — one flagship example shown open, the rest inside
    `<details><summary>View Additional Examples</summary>`
12. `## API Reference` — one-sentence intro naming the entry point and the **exact verified type
    count** ("196 public types"), then `<details><summary>View the Supported/Full/Complete API
    Surface</summary>` wrapping per-module `Class | Description` tables (Classes, Interfaces/Structs,
    Enumerations) followed by a hand-curated "Detailed Member Reference" of method signatures grouped
    by task area
13. `## Documentation & Resources` — bold-linked bullets (getting-started guide, how-to/FAQ, full API
    reference, contributor guide, security policy, changelog, "open an issue")
14. `## Scope and Limitations` — specific, mechanism-level bullets (never vague hedging), each citing
    the exact class/method/exception involved; closes with **exactly one** Enterprise-upsell sentence:
    *"These limitations don't apply to [Enterprise Edition link], which adds X, Y, Z."*
15. `## Development and Testing` — real build/test commands, named test files/frameworks
16. `## License` — fixed MIT boilerplate paragraph, plus a second sentence for any bundled
    non-MIT-licensed asset (fonts, etc.)

`## Project Structure` appears only for two candidates (cells/go, cells/java) as a directory tree —
present when the repo's own structure is worth documenting, not a fixed template slot.

## 2. The verification/provenance methodology

Every candidate directory carries sidecar evidence files that are the *real* mechanism behind the
quality bar, not just the README itself:

- `badge-dispositions.json` — one row per badge, `action: preserved|excluded`, each verified against
  a real source file (`go.mod`, `LICENSE`, a CI workflow file, `pyproject.toml`). Registry-version
  badges (NuGet/PyPI/Maven/crates.io/npm) appear **only** when the package is genuinely published —
  confirmed by a live registry check, never fabricated for an unpublished package.
- `structure-dispositions.json` — every old-README H2/H3 block gets a disposition:
  `merged_reframed`, `merged_verbatim`, or `excluded` (with a reasoned `excluded_reason`, usually
  "already covered by Key Capabilities bullet N").
- `content-dispositions.json` — per-sentence/bullet ledger with `verification.evidence_ref` pointing
  at an exact source file, `classification` (mechanism explanation vs. branding/positioning), and
  `target_section`.
- `code-example-dispositions.json` — per-code-block ledger, `api_call_fingerprint` (exact API calls
  used), disposition, and `excluded_reason` when a snippet is dropped as redundant.
- `upstream-issues.md` — every stale, false, or broken claim found in the *old* README, classified
  BLOCKING / FUNCTIONAL-DEFECT / INFORMATIONAL, each with a source citation. Confirmed corrected
  claims are never carried into the new candidate; several genuinely broken things (a Rust crate with
  no published version, a TypeScript `package.json` entry point that doesn't exist, a Go
  `examples/go.mod` with an invalid pseudo-version) are disclosed **in the README's own Scope and
  Limitations**, not hidden — this repo's own "working-condition presentation" policy is the same
  instinct, just enforced less consistently across our candidates today.

**Numeric claims are independently counted, never inherited.** Python/Slides corrects an old
README's "60+ transitions" to the real, counted 57. Go/Cells corrects a stale "Go 1.18+" badge to
1.24 by reading `go.mod` directly. This discipline — re-verify every quantitative or capability claim
against current source rather than trust the prior README — is applied uniformly across all 31
candidates.

## 3. Cross-cutting rules worth encoding as checks

- Banner is a **clickable image link** to the `.org` marketing page, always positioned directly below
  badges and above the intro paragraph — never before badges, never merged into the intro.
- Enterprise upsell is **exactly one sentence**, **only** at the end of Scope and Limitations, and
  **always** phrased as a direct resolution of the limitations just listed ("these limitations don't
  apply to X, which adds Y") — never a separate marketing section, never appearing twice.
- `<details>` is reserved for genuinely large reference content (secondary examples, the full API
  table) — Key Capabilities, Quick Start, and Scope and Limitations always stay fully visible.
- A positive "no dependencies" claim is stated as its own explicit sentence/subsection, never implied
  by omission — this repo's own presentation-lint rule set already partially encodes this
  (`check_dependency_claims`-style checks exist in the T3 aspose_checks bridge wired earlier this
  session).
- Format/platform coverage is folded into the mermaid diagram and Key Capabilities prose, not a
  separate table, in every candidate reviewed.

## 4. The dominant structural gap versus this repo's current pipeline

The single biggest quality delta is the **API Reference section**. Every one of the 31 aspose.org
candidates has a real, verified `## API Reference` — one or more `Class | Description` tables (often
100-600+ rows) plus a hand-curated Detailed Member Reference, built from genuine static analysis of
the target repository's public surface (reflection for .NET/Java, `go/doc`-style extraction for Go,
header parsing for C++, `rustdoc`-shaped extraction for Rust, TS compiler API for TypeScript, AST
parsing for Python).

This repo's own fact pipeline only extracts `api.public_surface` for **Python**
(`src/readme_agent/facts/curated_readme_evidence.py:108`, `python_public_surface`). There is no
equivalent detector for any other platform. Confirmed live via `grep -rn "api.public_surface"
src/readme_agent/facts/`: exactly one producer, Python-only.

Concretely, this means:

- `presentation/verified_source_detail_routing.py::_api_reference_available()` returns `False` for
  every non-Python repo (no `api.public_surface` fact exists to check), so any original-README
  content classified with the `api_public_surface` obligation has no canonical destination —
  `route_source_detail_blocks` raises `ValueError("valuable source detail has no canonical
  presentation destination: ...")`. Observed live on `aspose-cells-foss/Aspose.Cells-FOSS-for-.NET`
  during the 2026-08-17 portfolio run. The exception is already caught one layer up (the specialist
  retries once, then reports a normal `BLOCKED` outcome, not a process crash), but the root cause is
  the missing detector, not a routing bug — the routing code is behaving correctly given no real
  API-surface evidence to route against.
- Candidates that DO reach `CONVERGED_PROPOSAL_READY` in this repo's pipeline today (3D-Python,
  PDF-Python, Slides-Python, Words-Python — all Python) never had this obligation fail, precisely
  because Python is the one platform with a real detector.

**This is the primary, honest reason the local portfolio currently produces 4-5/33 candidates instead
of parity with aspose.org's full-coverage corpus.** Closing it requires building per-language
API-surface extraction (5-6 new detectors: .NET/Java/C++/Go/Rust/TypeScript), which is a substantial,
multi-detector engineering effort — correctly out of scope for a single hardening pass, and flagged
here as the concrete next-step work item rather than attempted as a quick patch.

## 5. Cross-reference: the plan's own account (`aspose-plan-synthesis.md`)

A separate agent read the full ~18,434-line Aspose.org skill-development plan
(`C:\Users\prora\.claude\plans\d-users-prora-onedrive-documents-github-humble-tome.md`) and the real
implementation it describes, and wrote a 710-line synthesis to `aspose-plan-synthesis.md` in this
same directory. Two corrections/additions to keep in mind alongside this document:

- **Composition is LLM-driven, not template-rendered.** There is no template engine or prompt file
  anywhere in the real Aspose.org architecture — a script computes a deterministic `facts/
  factpack.json` and runs ~92 deterministic `check_*` gates; a composing agent (a Claude session)
  reads the factpack plus skill-doc composition guidance and writes `readme.md` directly via
  Read/Edit/Write, with no intermediate rendering step. This repo's own pipeline is comparatively
  more template/deterministic-composition-driven (`presentation/verified_template_*.py`), with LLM
  calls scoped narrowly (e.g. the single `relationship_explained` call observed live during this
  session's Note-Python repro). That architectural difference — not just the missing API-surface
  detectors — is part of why aspose.org's prose reads more naturally/richly composed.
- **Disposition-ledger coverage is NOT actually portfolio-wide in aspose.org's real, live product
  tree** (`reports/repo-presenter/`, 30 products) — only 2 of 30 have structure/badge-disposition
  files and only 1 of 30 has a code-example-disposition file; the plan's own later missions
  (MT047/MT048) disclose this as open, deferred work. The rich disposition coverage this session's
  corpus-inspection agents found across most of the 31 `repo-presenter-regen-full` candidates
  reflects that tree's specific purpose (a full, deliberately-thorough regeneration comparison
  exercise), not aspose.org's steady-state production norm. Do not treat "every candidate needs full
  disposition JSON" as an already-proven aspose.org requirement to match — it's closer to their own
  aspirational target too.
- **LLM-composition idempotency is explicitly never claimed by aspose.org** — only the deterministic
  facts/checks layer is proven byte-identical on rerun. Worth keeping in mind when judging this
  repo's own NO_OP_PROVEN bar.

## 6. Secondary, smaller gaps (worth closing opportunistically)

- No disposition-ledger equivalent (badge/structure/content/code-example JSON) is written by this
  repo's pipeline today — our `composition_lineage`/provenance system covers the same *correctness*
  guarantee (exact byte-level source attribution) but doesn't produce the same *legible* per-unit
  audit trail a human reviewer gets from aspose.org's sidecar files.
- No `upstream-issues.md`-equivalent artifact is emitted per repo (this repo's "log per-repo
  UPSTREAM-DEFECTS.md" working-condition-presentation policy already calls for this; it isn't
  consistently wired to the T3/T4 aspose check bridge yet).
