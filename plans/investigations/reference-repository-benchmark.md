# Reference-Repository Benchmark — What Leading FOSS Actually Does

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md`
> artifact_role: analysis_or_evidence_only
> Method: `gh api` (GET-only) + WebFetch against real, live repository pages and READMEs.
> Sponsor-specified references: n8n-io/n8n (GitHub), nuget.org/packages/Aspose.Cells.
> Self-selected additional references (domain analogues facing the *identical* open-core /
> commercial-upsell tension Aspose FOSS does): iText (AGPL + commercial, PDF, closest possible
> structural analogue), EPPlus (Polyform Noncommercial + commercial, .NET Excel — same platform
> as one of our own products), SheetJS (Community + Pro, JS spreadsheets). Plus one no-tension
> baseline: Apache PDFBox (pure ASF open source, no commercial edition at all), to see what
> "purely professional" looks like with zero promotional pressure.
> Evidence: `evidence/reference-repository-benchmark/`.

## Why this matters before touching the plan again

The sponsor's request is explicit: study real leading FOSS presentation *before* revising next
steps, because the plan's goal is right but its approach may not be the best way to get there.
This document is that study. It also resolves a factual question the sponsor raised —
"use a tab interface to display Readme, Code of Conduct, License, Contribution, Security" — by
checking what GitHub actually does, rather than assuming a feature needs to be built.

## Finding 0 (resolves the "tab interface" question): GitHub already builds this — for free

Confirmed by direct inspection of github.com/n8n-io/n8n: below the repo header, GitHub shows a
**native quick-link row** to README / Code of Conduct / Contributing / License / Security —
automatically, whenever those files exist **and are recognized** (same signal our
`community/profile` API check already reads). n8n has this (100% community health: README,
Code of Conduct, Contributing, License all recognized). Apache PDFBox has a partial version of
it (Code of Conduct + Security shown; Contributing isn't a standalone file so it doesn't get a
quick-link, and its guidance lives inline in the README instead).

**Our own `cells-java` pilot — one of two repos this system has actually written to — sits at
37% community health: only README is recognized. No LICENSE, no CODE_OF_CONDUCT, no
CONTRIBUTING.** This is not a UI the central agent needs to design or build. It is a
consequence of recognized-file *presence*, which this survey already flagged as the single
highest-leverage, lowest-risk community-file target (portfolio survey finding PF-3: license
recognition fails for 28% of the registry, `cells` family worst of all). **Fixing file presence
IS building the tab interface** — there is nothing else to design here.

## Finding 1: placement varies; tone and singularity do not — this is the real constraint

Six sources, five with an actual commercial edition to communicate. Placement was **not**
unanimous — but tone, framing, and repetition were, and that turns out to be the load-bearing
constraint, not position:

| Repo | Where commercial mention appears | Exact tone |
|---|---|---|
| **n8n** | `## License` section, near the end | Factual: "Enterprise Licenses available for additional features and support" — one sentence, a `mailto:` link, no adjectives |
| **iText** *(AGPL + commercial, PDF — closest analogue)* | `### Licensing`, the last section in the file | Legal/practical: explains AGPL is real open source but "free ≠ gratis," and the commercial license exists so companies that can't comply with AGPL's copyleft have an out. "Contact Sales" — one plain link, zero marketing language |
| **EPPlus** *(Polyform Noncommercial + commercial, .NET Excel — same platform as Aspose.Cells)* | The **very first** content section (`## License`, right after badges — no prose description precedes it at all) | Factual license-mechanics statement: "will require a commercial license to be used in a commercial business... can be purchased at [link]." Immediately followed by **symmetrical, neutral code instructions for configuring either tier** — reads as configuration docs, not a pitch |
| **SheetJS** *(Community + Pro, JS spreadsheets)* | Second paragraph, directly under the opening description, **no separate heading** | Capability-extension framing: "CE does X. [SheetJS Pro] offers solutions beyond data processing: …" — one sentence, hyperlinked product name, feature list, no pricing/CTA. Appears exactly once, never repeated in a dedicated pricing section |
| **NuGet Aspose.Cells page** *(different platform, sponsor-specified)* | Footer badges + a "Try Aspose.Cells Plugins" cross-sell block, **after** a dense features/formats/examples/system-requirements body | "Subtly promotes related commercial offerings without aggressive advertising" |
| **Apache PDFBox** *(no-tension baseline)* | N/A — no commercial edition exists | Confirms the restrained tone isn't an artifact of Apache-style projects; it's just what "no promotional pressure" looks like |

**The real, evidenced constraint is not "must be at the end of the file."** Two of four
dual-licensed projects mention the paid tier near the top. What is genuinely unanimous across
all five: **exactly one mention, factual/mechanical framing (never adjectives, never a CTA
button, never a pricing table), and — where a product description exists — the description
comes first.** This still validates decision #9 (retire the promotional *banner* immediately
after H1, which none of these do) but corrects an over-narrow reading of it: the plan should
constrain **tone, density, and singularity**, not force one fixed section position.

**EPPlus is also a cautionary counter-example, not just a data point.** It has no "what does
this product do" prose anywhere in the README — it jumps from badges straight into licensing
mechanics. That is real behavior from an actively maintained, 2,000+-star library, and it is
exactly the outcome `BIZ-002`/`RDM-005` (visitor understands the product without hunting) exists
to prevent. **"Leading" and "well-known" do not automatically mean "good README"** — which is
precisely why the sponsor's instruction to consult multiple examples rather than treat one as
gold standard was the right call; n8n alone would have suggested end-of-file placement is the
whole rule, and it isn't.

### A concrete internal contrast this exposes

`aspose-3d-foss/…Java`'s current Resources section (bot-authored by a third party, already
flagged in `plans/master.md` decision #10 as "not the quality standard") is positioned
correctly (end of file) but is **structurally denser and more promotional than any reference
studied**: two fully-linked subsections ("free & open source" — 5 links, "commercial On-Premise
edition" — 5 links) plus a third "Community & support" subsection — 12 outbound links total in
one closing block. Compare iText's single paragraph with one link. **Placement was never the
only variable; density and tone matter as much as position**, and this is now evidenced, not
just asserted.

By contrast, **the shipped tool's own renderer** (`readme/renderer.py`, driven by
`config/policies/*.yml`) already outputs something much closer to the iText pattern: two
canonical links (org + com, one line each) plus one short LLM-authored paragraph — no link farm.
**This is a point in the current implementation's favor** worth explicitly preserving rather
than "improving" toward more links.

## Finding 2: the "top right corner" list is GitHub's native sidebar, not README content

The sponsor's list — description, product link, tags, releases, packages, contributors,
languages — maps exactly onto GitHub's native "About" sidebar, confirmed directly on n8n's live
page:

> Description → Website link → 20 topics → Releases (725, latest tagged) → Packages (0) →
> Contributors (present) → Languages bar (TypeScript 91.5%, Vue 7.0%, …)

None of this is README content. All of it is populated from: repo `description`/`homepage`
(class B, API/settings), `topics` (class B), Releases (class D, product-agent owned — though
for n8n, unlike Aspose, the same team owns both open and commercial editions), **Packages**
(class E/generated — and notably **empty/0 for n8n, iText, and PDFBox alike**: none of the
massive, mature reference projects studied actually publish through GitHub's native Packages
feature; they all publish externally — npm, Maven Central, NuGet — and let README badges/links
carry that information instead), Contributors and Languages (class E, generated, audit-only).

**This is exact, independent confirmation that the five-control-class model this investigation
already built (`docs/repository-presentation-surface-model.md`) is the right decomposition** —
GitHub's own UI literally separates these surfaces the same way. No redesign needed here; this
finding *validates* rather than *changes* that part of the plan.

**Correction to the sponsor's literal ask**: "list all possible packages" should not be read as
"populate GitHub Packages" — that isn't the convention even leading projects follow. It should
be read as **ensure the README's install section correctly names and links the real external
package registry** (Maven Central / NuGet / PyPI / npm) — which is exactly what the earlier
portfolio survey's `cells-java` finding (README instructs a Maven Central dependency that
doesn't exist on Central) already flagged as a real, live defect. This reframes that finding as
directly serving the sponsor's "list all possible packages" goal, not a side issue.

## Finding 3: hero/product image — validated, and technically already possible

n8n leads with a banner image before any text, then a second in-README screenshot. The sponsor
independently asked for "an AI image agent to draw an image for the product." The earlier LLM
gateway characterization (`llm-gateway-characterization.md`, finding L5) already confirmed
`stable-diffusion-3.5-large` and a vision model (`Qwen2.5-VL-7B`, usable for factual-accuracy
review of a generated image against product facts) are hosted on the same gateway — **no new
vendor or integration is required**, only the Phase-24 visual pipeline work already scoped in
the roadmap. This finding elevates that work's priority rather than changing its design.

## Finding 4: community-file discipline is inconsistent even among high-star projects

| Repo | Stars | Community health | Quick-link row shows |
|---|--:|--:|---|
| n8n | 197k | 100% | README, CoC, Contributing, License |
| iText | (large) | high | README, CoC, Contributing, License, Security |
| Apache PDFBox | 3.1k | partial | CoC, Security (Contributing is inline in the README, not a standalone file) |
| EPPlus | 2.0k | 75% | Contributing, Security (no CODE_OF_CONDUCT.md) |
| SheetJS | 36.3k | low | **only** README + LICENSE recognized — no CoC/Contributing/issue-or-PR-template quick-links at all |
| `aspose-cells-foss/…Java` *(our own enabled pilot)* | 2 | **37%** | **README only** |

**Popularity does not predict community-file completeness** — SheetJS has 36k stars and almost
no recognized community files. This tempers how much weight "match what leading projects do
100%" should carry: the achievable, high-value target is not universal full compliance, it's
closing the specific gap that actually blocks the sponsor's "tab interface" ask — **license
recognition**, which is the one file every single reference project (including the two weakest,
SheetJS and EPPlus-minus-CoC) got right, and which `cells-java` and 6 other registry repos did
not (portfolio survey finding PF-3).

## Finding 5: GitHub Packages is universally unused — external registries are the real signal

Confirmed empty (`0`) across every reference studied — n8n, iText, EPPlus, SheetJS, PDFBox —
despite all being mature, widely-distributed libraries. **Not one leading project studied
uses GitHub's native Packages feature**; all publish externally (npm, Maven Central, NuGet) and
communicate that entirely through README badges and install instructions. This independently
confirms Finding 2's reframing of "list all possible packages" below.

## What should change in the plan's next steps (recommendation — not yet applied)

1. **Specify the commercial mention as a tone/density/singularity constraint, not a fixed
   section position.** The evidenced rule: if a product description exists, it comes first;
   the commercial edition is named **exactly once**, in **factual/mechanical language** (license
   terms, capability extension — never adjectives, pricing tables, or CTA buttons), as **either**
   a short closing-section paragraph (n8n/iText style) **or** one sentence directly under the
   opening description (SheetJS style) — both are evidenced as acceptable; a promotional banner
   immediately after H1 (the retired callout) and a repeated/multi-section link farm (the current
   `3d-java` bot-authored pattern) are the two evidenced anti-patterns. This should replace an
   over-narrow "always at the end" rule in whatever presentation-policy design comes next, and the
   shipped renderer's current two-link-plus-one-paragraph output should be kept as the density
   baseline — it already matches the restrained end of what leading projects do.
2. **Explicitly require the opening product-description paragraph, evidenced by both a positive
   and negative case.** n8n/iText/PDFBox/SheetJS all lead with one; EPPlus — a real, actively
   maintained, 2,000-star library — skips it entirely and jumps straight to licensing, and that
   is exactly the failure mode `BIZ-002`/`RDM-005` exist to prevent. This should be written as a
   non-negotiable, evidenced by counter-example, not merely asserted from principle.
3. **Community-file presence/recognition (`SURF-007`) is confirmed as the correct mechanism for
   the sponsor's "tab interface" ask** — no new UI-design work should be scoped for it. But
   target **license recognition first, not full four-file compliance** — it's the one file every
   reference project got right regardless of overall community-health score (even the two
   weakest, SheetJS and EPPlus, have it), and it's the specific, already-quantified portfolio
   gap (PF-3, 28% of the registry, `cells-java` included).
4. **"List all possible packages" should be scoped as install-path/package-registry-badge
   accuracy in the README**, not GitHub-native Packages population — confirmed by zero adoption
   across all five reference projects with real distribution (n8n, iText, EPPlus, SheetJS,
   PDFBox). Ties directly to the already-flagged `cells-java` broken-Maven-Central-install
   finding from the portfolio survey.
5. **Hero/product illustration work (Phase 24) is validated by both the sponsor's ask and a
   real leading-FOSS pattern (n8n)** — the technical path (SD 3.5 + VL for review) is already
   characterized; no design change, but this raises its relative priority.
6. **No change is needed to the five-control-class model** — it was independently confirmed by
   how GitHub itself separates these surfaces on a real, live repo page.
7. **Do not treat community-file health as a percentage target to maximize uniformly.** SheetJS
   (36k stars) and EPPlus (missing CODE_OF_CONDUCT) show that even leading projects are
   inconsistent here; chase the specific highest-value file (license) over blanket compliance.

## Method limitations

WebFetch renders pages through an intermediate summarization model, not a raw screenshot —
structural claims (section order, sidebar contents) were cross-checked against `gh api` JSON
where possible (n8n) but for repos surveyed by sub-agents (iText, EPPlus, SheetJS, PDFBox) the
report relies on the agent's WebFetch read of the live page and could miss elements a human
skim would catch (e.g. a contributor count that failed to render). Findings here are about
**pattern and placement**, which is robust to that limitation; exact pixel/element positions
are not verified beyond what's quoted.
