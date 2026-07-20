# Product-presentation standard

What "professionally presented" means for an Aspose FOSS repository, and how to check it.
This is a set of principles extracted from real leading-FOSS and commercial-package
presentation, not a template — repositories differ by product, audience, and maturity, and
this standard is written to be satisfied differently by each of them (decision #9, `BIZ-006`).

## Sources studied

Per `RDM-019`/`DOC-003`, evidence for this standard comes from six real, live sources plus our
own 25-repository registry, read directly rather than assumed:

- **n8n** (github.com/n8n-io/n8n) — sponsor-specified leading FOSS reference; 197k stars, 100%
  GitHub community-health score.
- **Aspose.Cells on NuGet** (nuget.org/packages/Aspose.Cells) — sponsor-specified reference for
  "how a professional Aspose product page looks."
- **iText** (github.com/itext/itext7) — AGPL + commercial dual license, PDF domain: the closest
  real-world structural analogue to Aspose FOSS's own open-source-to-commercial relationship.
- **EPPlus** (github.com/EPPlusSoftware/EPPlus) — Polyform Noncommercial + commercial dual
  license, .NET Excel: same platform as Aspose.Cells for .NET, same commercial tension.
- **SheetJS** (github.com/SheetJS/sheetjs) — free Community Edition + paid Pro tier, JS
  spreadsheets: a third independent instance of the open-core tension, different ecosystem.
- **Apache PDFBox** (github.com/apache/pdfbox) — pure ASF open source, zero commercial upsell:
  a no-promotional-pressure baseline for contrast.
- **This project's own 25-repository registry** (`data/products.json`), surveyed live on GitHub
  and scored against the criteria below, to see where the real portfolio already stands.

Full evidence, method, and exact quotes: `plans/investigations/reference-repository-benchmark.md`
and `plans/investigations/full-registry-portfolio-survey.md`.

**A deliberate methodological point**: no single source was treated as the gold standard.
Checking six meant the standard below reflects what's actually unanimous across leading FOSS,
not one project's idiosyncrasies — and it surfaced at least one leading project (EPPlus) doing
something that should **not** be imitated (see "Product clarity" below).

## The ten dimensions

### 1. Product clarity

**Every source but one leads with a plain-language sentence stating what the product does** —
n8n ("Fair-code platform to build and deploy AI agents and workflows..."), iText ("...allows
you to create, adapt, inspect and maintain PDF documents..."), SheetJS, PDFBox, and the
NuGet Aspose.Cells page all do this in the first paragraph, before anything else.

**Counter-example, deliberately kept**: EPPlus has no such paragraph anywhere in its README —
it jumps from badges straight into licensing terms. This is real behavior from an actively
maintained, 2,000+-star library, and it is exactly the failure this standard exists to prevent
(`BIZ-002`, `RDM-005`). A README that explains licensing before it explains the product fails
this dimension regardless of how well-known the project is.

**Rule**: the opening paragraph names what the product does, using a concrete verb (create,
convert, parse, read, write, generate, render — not "leverage" or "empower"), before any other
content. Portfolio evidence (`full-registry-portfolio-survey.md`) confirms this is already the
norm across the Aspose FOSS registry — 25/25 repos studied have a functional opening sentence.
The gap in this portfolio is not clarity; it's what comes after (below).

### 2. Audience fit

State who the library is for and what situation brings them here, in the same opening block as
the product description — not as a separate exercise. n8n folds this into capability bullets
("Enterprise-Ready AI: Self-host or deploy securely with role-based access..."); iText states
platform scope inline ("It is also available for .NET (C#)"). For Aspose FOSS specifically:
name the language/ecosystem, the file format(s) handled, and the one or two most common tasks
(e.g. "creating, reading, and modifying Excel files" — the actual working `cells-python`
opening) rather than an abstract capability list.

### 3. Trust signals

The strongest evidenced trust signals, in order of how consistently they appear across sources:

1. **A visible, GitHub-recognized license.** Every reference studied has one; SheetJS (weakest
   community-file discipline of the six) and EPPlus (missing CODE_OF_CONDUCT) still both have
   this. Portfolio evidence: 7 of 25 registry repos (28%) fail it, including `cells-java` — see
   dimension 8.
2. **Build/version/package-registry badges** — present in n8n, iText, EPPlus, SheetJS, NuGet
   Aspose.Cells; absent only in PDFBox (which relies on ASF's institutional trust instead — not
   a pattern available to a standalone FOSS repo).
3. **A working install path** that resolves against a real package registry (see dimension 4).
4. **Recent activity** — visible via commit history / release cadence, not something a README
   states about itself.

**Rule**: license visibility is the single highest-leverage trust signal and the one item every
reference source gets right regardless of overall polish — it should be the first community-file
target (see dimension 8), ahead of broader community-health completeness.

### 4. Installation path

Must name the real package coordinates and resolve against the actual registry for that
ecosystem (Maven Central, NuGet, PyPI, npm) — never GitHub's native Packages feature, which is
**empty (0) across every single reference studied** (n8n, iText, EPPlus, SheetJS, PDFBox) despite
all being mature, widely-distributed projects. Leading FOSS publishes externally and lets README
badges/links carry the information.

**Portfolio finding this validates and sharpens**: `cells-java`'s README instructs a Maven
Central `<dependency>` for `org.aspose:aspose-cells-foss`, which returns **zero results** on
Maven Central (verified live, `plans/investigations/full-registry-portfolio-survey.md`,
finding D-2). A perfectly clear, well-written install section is still a trust failure if the
command doesn't work. Installation-path review must include resolving the stated coordinates
against the real registry, not just checking that a section exists.

### 5. Verified examples

At least one runnable code block beyond the install snippet — n8n (`npx n8n` / Docker run),
iText ("Hello PDF!"), the NuGet Aspose.Cells page (four separate C# samples). A features list
without a working example under-delivers relative to every reference studied.

### 6. Navigation

None of the six references force identical section names or order (`RDM-015`) — n8n uses "Key
Capabilities → Quick Start → Resources → Support → License → Contributing"; iText uses "Key
Features → Addons → Getting Started → Hello PDF! → Examples → FAQs → Contributing → Licensing";
EPPlus (minimal, no marketing content) is just "License → License parameters → New features →
Breaking Changes." **What's shared is not structure but sequencing intent**: product
understanding and getting-started content precede reference/contribution/legal content in every
case. Long documents (SheetJS, PDFBox) use `##`/`###` headers consistently so GitHub's own
in-page table of contents works — no custom navigation UI is needed or was found anywhere.

### 7. Visual usefulness

n8n leads with a banner image before any text, plus an in-README product screenshot; iText uses
a centered logo; EPPlus and PDFBox use no imagery at all and are not worse README experiences
for it — visuals help most for products whose value is visual/interactive (workflow builders,
UI tools) and least for libraries whose interface is purely an API. **Rule** (`RDM-017`, already
correctly stated): a product illustration is warranted only when it improves understanding of
the product or workflow — decorative imagery does not satisfy this dimension. For document/data
-processing libraries (Aspose FOSS's actual domain), a small diagram showing input format →
transformation → output format is more useful than a generic hero banner, and this is a
legitimate, product-appropriate divergence from n8n's pattern, not a shortfall.

### 8. Contribution readiness

**Confirmed independently of README content**: GitHub shows a native quick-link row (README /
Code of Conduct / Contributing / License / Security) below the repo header whenever those files
exist *and are recognized* — verified directly on n8n's live page. This is the mechanism behind
what can look like a "professional tabbed profile"; **it requires no UI work, only file
presence and GitHub-recognized placement.**

**Popularity does not predict this.** SheetJS (36.3k stars) has almost no recognized community
files; EPPlus (2,029 stars) is missing CODE_OF_CONDUCT. The achievable target is not
"match n8n's 100%," it's closing the specific highest-value gap:

| Reference | Community health | What GitHub shows |
|---|--:|---|
| n8n | 100% | README, CoC, Contributing, License |
| iText | high | README, CoC, Contributing, License, Security |
| EPPlus | 75% | Contributing, Security (no CoC) |
| SheetJS | low | README, License only |
| `cells-java` (our own enabled pilot) | **37%** | **README only** |

**Rule**: prioritize LICENSE recognition first — it is the one file every reference source gets
right regardless of overall community-health score, and it is the specific, quantified gap in
this registry (7/25 repos, 28%, all of the `cells` family — `plans/investigations/
full-registry-portfolio-survey.md`, finding PF-3). Broader community-file completeness
(CONTRIBUTING, CODE_OF_CONDUCT, SECURITY) is real value but should not be pursued as a uniform
percentage target.

### 9. Maintenance signals

Visible through recent releases and commit activity — none of the references state "actively
maintained" in prose; the signal is structural (a populated Releases sidebar, recent
`pushed_at`). This is GitHub-generated (class E) and audit-only; a README should never claim
maintenance status that the repository's actual activity doesn't support.

### 10. Natural commercial context

The dimension this standard corrects most substantially from the shipped tool's original
assumption. Evidence from all five sources with an actual commercial edition to communicate:

| Source | Where | Tone |
|---|---|---|
| n8n | End (`## License`) | "Enterprise Licenses available for additional features and support" — one sentence, `mailto:` link |
| iText | End (`### Licensing`) | AGPL-vs-commercial legal explanation, "Contact Sales" — one plain link |
| EPPlus | **First** section (no product paragraph precedes it) | Factual license-mechanics statement, symmetrical config instructions for both tiers |
| SheetJS | **Second paragraph**, directly under the opening description | "CE does X. [Pro] offers... beyond that: ..." — capability-extension framing |
| NuGet Aspose.Cells | Footer badges + cross-sell block, after a dense feature/format body | "Subtly promotes... without aggressive advertising" |

**Placement is not the unanimous constraint — tone, density, and singularity are.** Two of four
dual-licensed projects mention the paid tier near the top, not the end. What every source shares:
**exactly one mention**, in **factual or capability-extension language** (never adjectives,
pricing tables, or a call-to-action button), and — where a product description exists — the
product is explained first.

**Rule** (refines decision #9 and `RDM-002`/`RDM-012`): a commercial mention may appear either
as a short closing-section paragraph (n8n/iText pattern) or as one sentence directly under the
opening product description (SheetJS pattern) — both are evidenced as acceptable. It must never
appear as a promotional banner immediately after the H1 (the retired `callout`, correctly
retired) and must never repeat across multiple sections or link lists. **A concrete internal
anti-pattern this standard identifies**: `aspose-3d-foss/…Java`'s existing (bot-authored, not
this tool's output) Resources section — two five-link subsections plus a third "Community &
support" subsection, 12 outbound links in one closing block — is denser and more promotional
than any reference studied, despite correct end-of-file placement. The shipped renderer's
current output (two canonical links, one short paragraph) is closer to the evidenced restrained
baseline and should be preserved as the density ceiling, not expanded toward the 3d/Java pattern.

## First screen, first minute, first successful install (`RDM-019`)

- **First screen** (before scrolling): what the product does, in one sentence with a concrete
  verb, and — from trust signals — a license/build/registry badge row if applicable. This is
  the dimension every reference source treats as non-negotiable except EPPlus (the identified
  counter-example).
- **First minute**: whether it's the right tool — supported formats/capabilities in scannable
  bullets, the target ecosystem/platform stated explicitly, and a working install command
  visible without scrolling past unrelated content.
- **First successful install attempt**: a package-registry coordinate that actually resolves
  (verified, not merely present — dimension 4), followed by one runnable example proving the
  install worked.

## Reference patterns for different product types (not one template)

Deliberately different shapes, evidenced across the sources studied, avoiding `RDM-003`'s
prohibition on a generic full-document template:

1. **Mature, multi-format library** (Aspose.Cells, Aspose.PDF class) — closest to the
   `pdf-java`/`cells-python` pattern already scoring well in the portfolio survey (8/8): badges
   → one-line description → feature categories → install → multiple runnable examples →
   status/roadmap → contributing → license → (optional) one-paragraph commercial mention.
2. **Focused, single-purpose library** (Aspose.Font, Aspose.TeX class) — shorter is correct here;
   forcing the Pattern-1 shape onto a narrow-scope library risks padding. One-line description →
   install → one example → license → commercial mention, with no forced feature-category
   headers the product doesn't have enough surface area to fill.
3. **Dual-license framing when applicable** (any FOSS repo genuinely gated behind a broader
   commercial license, as opposed to a simple "FOSS edition exists alongside a commercial one")
   — iText/EPPlus pattern: explain the license mechanics plainly (why a commercial tier exists,
   what triggers needing it), not as a sales pitch.

None of these are proposed as literal templates to fill in — they are evidenced *shapes*; the
actual section names, order, and depth remain per-repository (`RDM-015`, `BIZ-006`).

## Measurable review criteria for Phase 21

A `READMEPresentationReport` (`VAL-005`) should evaluate, per repository:

1. Opening paragraph explains the product with a concrete verb (dimension 1) — pass/fail.
2. No commercial link or claim appears before the product explanation (dimension 1, `BIZ-001`).
3. Audience/ecosystem/format stated in the opening block (dimension 2).
4. LICENSE is present and GitHub-recognized (dimension 3/8) — the single highest-priority gate.
5. Install command names real package coordinates that resolve against the live registry
   (dimension 4) — not merely "an install section exists."
6. At least one runnable example beyond the install snippet (dimension 5).
7. Section headers use consistent Markdown levels; no forced identical structure across repos
   (dimension 6).
8. If a visual is present, it demonstrates the product's actual input/output/workflow, not
   generic decoration (dimension 7).
9. Commercial mention (if any) appears exactly once, in factual/capability-extension language,
   either as a closing-section paragraph or immediately under the opening description — never as
   a banner, never repeated, never adjective-laden (dimension 10).
10. No verified technical fact, example, or known limitation present before the change is
    missing after it (`BIZ-007`, `FACT-009`).

## Illustration vs. social preview (decision #23)

Confirmed distinct by design and by evidence: a README illustration is repository content
(class A, this standard's dimension 7); GitHub's social-preview image is a separate Settings-UI
upload with no read API (class C, manual UI managed) and was not addressed by any reference
source studied here since it isn't visible in a repository page or README fetch — it remains
scoped to Phase 24's separate asset-contract work (`SURF-010`).

## What this standard does not require

- A fixed section list or order (`RDM-015`).
- Uniform community-file completeness — LICENSE recognition is prioritized over a percentage
  target (dimension 8).
- Hero imagery for every repository — only where it demonstrates actual product behavior
  (dimension 7).
- GitHub Packages population — not the convention any reference source follows (dimension 4).
