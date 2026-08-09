# GOLDEN SAMPLE — README.golden.md annotations

`README.golden.md` is the product-owner-approved target output, built from the real
Aspose.Page Python candidate (revision `dac5d70e`) with all four approved tweaks
physically applied. It is the reference for EVERY generated README. When a rule in
TWEAKS-AND-RUNNER-SPEC.md and this sample seem to disagree, the sample wins for shape
and the spec wins for thresholds. `dispositions.golden.json` is the matching target
shape for the per-repo disposition ledger.

## What to imitate, section by section

**Header block (lines 1–6).** H1 = canonical product name. Badge row unchanged.
Banner IMMEDIATELY after the badge row, before the opening paragraph:
`![<Canonical Product Name>](https://products.aspose.org/media/{family}/{platform}/banner-readme.png)`
— family slug from `data/families.json`, platform key from the registry. Alt text is
the canonical product name. If the build-time existence check fails, the banner line
is simply absent — never a broken image.

**At a Glance (Mermaid).** 32 source lines (ceiling: 40). Same information as the
old 42-line version — six capabilities, two inputs, three outputs, identical
topology — but: THREE capability columns of ≤2 nodes (adaptive: ceil(n/3) rows),
labels ≤36 chars ("PS/EPS to PDF", not "PS/EPS to PDF conversion"), single-line
`A ~~~ B` chaining, no decorative blank lines. Compactness came from layout and
label economy, ZERO nodes were removed. That trade — information to the bullets,
height out of the graph — is the whole tweak.

**Key Capabilities.** Six bullets, all visible — exactly at the 6-bullet visibility
ceiling, so no `<details>` needed. A repo with more than six (PDF has 12) shows the
six most important and folds the rest into one details block. Every bullet keeps its
"Available through the public `X` API" attribution.

**Installation.** Demonstrates a clean tweak-4 merge: the source README's
"install optional dependencies by scenario" framing is preserved (it was good), but
deduplicated and restructured to target style. Note what is NOT here: the previous
candidate's duplicated optional-dep lines and stray blank lines inside details.
Sloppy whitespace is a validation failure.

**Additional Examples.** Brief (2 lines, ceiling 3) NAMES the workflows inside,
then ONE details block. Two tweak-4 lessons live here:
1. The MCP-server workflow from the source README is a proper `### Host the MCP
   Server` example — the previous candidate dumped it into a second details block
   inside API Reference. Source content goes to its correct target-structure home.
2. `### Example Results` keeps the source's image captions as prose ("An XPS
   document converted to PDF, rendered here as PNG:"). The previous candidate
   dropped the captions silently. Nothing is dropped silently — that is the rule.
   Note the caption prose was also REWRITTEN (source said "that is converted than
   to PNG") — preserve information, not typos.

**API Reference.** Brief states the counts and headline namespaces (4 lines,
ceiling 4), then ONE details block with the full namespace tables. Exactly one
details block per section — never two.

**Scope and Limitations.** The previous candidate showed 10 raw internal error
strings. Golden form: a 2-line human summary of what the limitations concern, the
10 specifics rewritten as readable sentences inside details, then the
Enterprise Edition paragraph (visible, never folded — it is a contract element).

**Development and Testing.** Already-correct brief+details shape, kept as-is:
counts in the brief, resources folded.

**License.** Contract's MIT prose. Unchanged.

## Global rules the sample embodies

- Every H2 from the contract's section order, no new sections, no renames.
- One `<details>` block maximum per section; brief always above it; brief is a
  real summary (counts, names), never "click to expand".
- No emoji, no comments in code blocks, no process narration, no duplicate
  sections, no dangling fragments, normalized blank lines (max one consecutive).
- "Enterprise Edition" is the only name for the commercial product.
- Every fact, URL, coordinate, and count comes from deterministic evidence —
  the sample's numbers (134 exports, 41 namespaces, 66 test files) are
  fact-machinery output, not prose to copy.

## Per-repo variation

Product name, banner family/platform, capabilities, examples, API tables,
limitations, and counts vary per repository — the SHAPE above does not. A README
whose shape matches this sample and whose dispositions.json shows zero silent
drops is a passing candidate.
