# Approved README Tweaks + Straight-Line Runner — Implementation Spec

Product-owner-approved changes to the presentation output, verified against the
codebase at review snapshot (HEAD `e8f4de70`, state 790). Apply in the order given.
Every change is scoped; anything not named here is out of scope under POC-FREEZE.md.

---

## Tweak 1 — Compact Mermaid layout (optimize visually, never strip information)

**Owner code:** `src/readme_agent/readme/header_visual_mermaid.py` (renderer),
`src/readme_agent/readme/presentation_contract.py` (constants),
`src/readme_agent/readme/header_visual_validation.py` (validator).

**Requirement:** the same nodes and the same one-edge product→capabilities and
capabilities→outputs topology, rendered shorter. Do not reduce node count to save
space; reduce vertical height.

Changes:
1. Capability column count becomes adaptive: `ceil(n_capabilities / 3)` rows per
   column, i.e. up to **3 columns** when 7+ capabilities exist (currently fixed at 2).
   Keep the invisible `~~~` vertical ordering trick per column.
2. Inputs and Outputs subgraphs render their nodes in `direction LR` rows (wide,
   not tall) when they contain 3+ nodes.
3. Lower `PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS` from 52 to **36**. Labels that
   exceed it are shortened by deterministic rules first (drop "files", drop
   repeated product name, "conversion" → "→"), and only then by the existing
   safe-label fallback. Information moves to the Key Capabilities bullets — it is
   never deleted from the README.
4. Validator: assert rendered mermaid block ≤ **40 lines** and no capability column
   taller than 4 nodes. This is a build failure, not an LLM instruction.

**Explicitly forbidden:** removing inputs/outputs nodes, collapsing capabilities
into fewer nodes, or putting the graph inside `<details>`.

---

## Tweak 2 — Enforced brief-then-collapse for long sections

**Owner code:** `src/readme_agent/readme/presentation_lint_structure.py` (add
validator), `src/readme_agent/readme/document_examples.py` and the composition
prompts in `src/readme_agent/llm/generation_prompts.py` (produce the shape).

**Requirement:** these sections MUST consist of a short always-visible brief
followed by ONE `<details>` block containing everything else:

| Section | Max always-visible content lines (after heading, before `<details>`) |
|---|---|
| Key Capabilities | 6 bullet lines |
| Additional Examples | 3 lines |
| API Reference | 4 lines |
| Development and Testing | 3 lines |
| Scope and Limitations | 5 lines |

The brief must be a real summary (counts, headline items, one-sentence scope) —
the current API Reference brief ("documents 735 public API entries across 19
namespaces...") is the model to follow. The current Key Capabilities section
(12 visible bullets in the PDF candidate) is the failure to fix: first 6 bullets
visible, remainder inside the existing `<details>` block.

Enforcement is deterministic: a new lint rule counts visible lines per designated
section and fails the candidate if exceeded. Add a post-composition normalization
pass that mechanically moves overflow bullets into the details block, so an LLM
that writes too much gets corrected rather than re-prompted.

---

## Tweak 3 — Brand banner under the badge row

**Product-owner override of Phase 21 / decision #9's retired "callout" span.**
That decision retired a *promotional link block* after the H1. This banner is a
brand image, part of the portfolio brand shell (like the badge row), not a
promotional link, and the product owner has explicitly ruled it in. Record one
line in the log citing this spec; do not reopen the decision ledger (frozen).

**Owner code:** `src/readme_agent/readme/header_visual.py` /
`header_badges.py` (render), `header_visual_validation.py` (validate),
`data/families.json` (family slug source).

Placement and form — directly after the badge row, before the opening paragraph:

```markdown
![{Canonical Product Name}](https://products.aspose.org/media/{family}/{platform}/banner-readme.png)
```

- `{family}` = the `family` slug from `data/families.json` matched by the repo's
  `github_org` (e.g. `aspose-page-foss` → `page`).
- `{platform}` = lowercase platform key already used in the registry (`python`,
  `net`, `java`, ... — confirm the exact vocabulary against `data/products.json`
  entries; use the registry's spelling, do not invent one).
- Alt text = the complete canonical product name (existing identity rule applies).
- **Existence check is deterministic and build-time:** HTTP HEAD (GET fallback)
  the URL during composition; on non-200, omit the banner entirely and record a
  one-line note in the run output. Never ship a possibly-broken image. Cache the
  check per family/platform per run.
- The banner is part of the deterministic header — the LLM never sees or writes
  this URL (existing "LLM never supplies URLs" invariant covers it).
- Validator: at most one banner image, exact host/path prefix
  `https://products.aspose.org/media/`, positioned between badges and opening.

---

## Tweak 4 — Verify-then-merge existing source README content

**Requirement (product owner, verbatim intent):** anything already present in the
source README must be verified against the product repository, and the verified
information must be preserved and reused in the generated README — reframed,
restructured, and rewritten to match the target structure and prose style, then
cleanly merged. The goal is preservation of existing information, not
regeneration from facts alone.

**Owner code:** `src/readme_agent/readme/agentic_composition_inputs.py` (source
content enters composition input), `src/readme_agent/llm/generation_prompts.py`
(merge instruction), `src/readme_agent/readme/assessment_claims.py` +
`claim_accountability_*.py` (disposition accounting),
`src/readme_agent/readme/verified_preservation_composition.py` (zero-provider
path must obey the same rule).

Mechanism — three parts:

1. **Source claim inventory (deterministic).** Parse the source README into
   claim-bearing units (headings, sentences with factual content, code blocks,
   links, tables). The existing markdown-it token machinery and
   `source_claim_obligations.py` are the substrate — extend, don't rebuild.
2. **Verification and disposition (existing fact machinery).** Each unit gets
   exactly one disposition, recorded in the run output:
   - `VERIFIED_MERGED` — supported by repo evidence; content reworded/restructured
     into the target section. Default outcome; this list should dominate.
   - `SUPERSEDED` — same information now stated more accurately by a fact-backed
     claim (e.g. corrected version number). Old wording dropped, information kept.
   - `UNVERIFIABLE_DROPPED` — contradicts repo evidence or cannot be grounded.
     Requires a one-line reason.
   - `NON_CONTENT` — boilerplate, old badge rows, generator artifacts.
3. **Composition instruction (prompt layer).** The composition prompt receives the
   verified source units as first-class input with the instruction: preserve and
   reuse this information, rewriting to target structure and prose style; do not
   invent replacements for content that exists and verifies.

**Acceptance rule (deterministic):** a candidate fails validation if any source
unit lacks a disposition, or if the `UNVERIFIABLE_DROPPED` + `NON_CONTENT` share
exceeds 40% of claim-bearing units without per-unit reasons. Silent dropping is
the bug this tweak exists to kill.

---

## Straight-Line Runner (`readme-agent poc`)

**New file:** `src/readme_agent/commands_poc.py`, wired as a `poc` subcommand in
`cli.py`. Roughly 200 lines. It composes EXISTING tested functions — facts
extraction, composition, deterministic validation, independent review, no-op
check — in a plain sequential call chain. It must NOT import or consult:
mission graph, durable claims, `mission_execution_guard`, execution focus,
approach budgets, canaries, campaign/trusted-cohort modules.

Behavior per repo:

```
readme-agent poc --repo <org/repo>            # one repo
readme-agent poc --all-python                 # every python repo in products.json
```

1. Snapshot the repo at its current default-branch revision (existing snapshot
   machinery, push-neutered clone, local_poc profile).
2. Facts: reuse a cached checksum-valid ProductFactsV2 for this revision if
   present; otherwise extract fresh.
3. Compose candidate with Tweaks 1–4 applied. Reuse cached stages only when
   revision AND tweak-config hash match (tweaks change output — stale caches
   composed without them must not satisfy this run).
4. Deterministic validation (existing validator registry + the new validators
   from Tweaks 1–4).
5. One independent LLM review pass + at most one repair cycle (existing review
   capability). Second review failure → write the candidate anyway, marked
   `REVIEW_OPEN`, and continue. POC shows output; it does not gate on perfection.
6. No-op check: immediately re-run composition against the same snapshot and
   assert zero diff and zero additional LLM calls (existing idempotency
   machinery).
7. Write to `runs/share/poc/<org__repo>/`: `README.md`, `dispositions.json`
   (Tweak 4 output), `validation.json`, `noop.json`. Print the file path.

Failure policy per POC-FREEZE.md: smallest causal fix, one retry, then skip and
continue. The runner never touches the mission graph or durable state — its only
outputs are files under `runs/share/poc/` and the local work clones.

## Order of operations

1. Commit POC-FREEZE.md at repo root.
2. Implement Tweaks 1–3 (deterministic, testable offline with existing fixtures).
3. Implement the runner; prove it end-to-end on ONE repo (Page — smallest at 636
   lines, freshest cache) and show the product owner the README before touching
   anything else.
4. Product owner eyeballs Page. Feedback applied. Then Tweak 4 (the deep one) —
   verify on Page again.
5. Run the remaining 11 Python repos. Show each README as it completes — do not
   batch-and-hide.
