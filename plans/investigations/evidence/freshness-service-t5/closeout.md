# T5 — deterministic pilot skeleton (cells/python)

**Status: SUBSTANTIAL PROGRESS, not COMPLETE.** Recorded honestly — the card's own closeout bar
("full battery green + byte-identical double run") is only partly met: the double-run proof is
real and complete; a real, tested, verified fix landed for the disposition-ledger `target`
defect (`disposition_ledger_errors` 13 → 7 on the real pilot, see below), but the overall
candidate is still `deterministic_verdict: reject` due to two separate, unaddressed defects
(protected-content losses, claim-accountability gaps) — "full battery green" is not yet reached.
`GC-03` (G3 close) correctly stays blocked until all of this is resolved.

## What is genuinely done and verified

- **Real target, real network access, real clone**: `aspose-cells-foss/Aspose.Cells-FOSS-for-
  Python` confirmed real and clonable (`git ls-remote`); resolved at `main` @
  `26c3bd1633e84b91c0f6fad1fd353662fd61fb54`. Run via `readme-agent poc --repo
  aspose-cells-foss/Aspose.Cells-FOSS-for-Python` — the sanctioned local-candidate-generation
  tool for this repo (per standing project convention: no contract edits, no new machinery).
- **Byte-identical double run — PROVEN, twice over**: two independent CLI invocations produced
  byte-identical `README.md` (`sha256
  2e6579ea89c1a06ede70928e564c1f352584a88467b56dd66a46d39bd618a6f3` both times); run 2's stdout
  ("reusing hash-bound composition plan") and `noop.json` (`new_provider_call_count: 0`,
  `llm_accounting_status: "EXACT"`, `verdict: "RENDER_REPRODUCIBLE"`) independently confirm zero
  new LLM calls on the second run. Full details + exact commands: `run-log.md`.
- **Docker isolation machinery proven live**: the diagnostic `poc` path does not reach it (its
  `verified_example_present` check is a static substring match, confirmed by reading
  `document_validation.py:411` before claiming otherwise — never assumed). The full canonical
  `supervise` transaction reaches it but did not complete in available session time (see below).
  In its place, `tests/security/test_isolated_execution_docker_live.py` (normally excluded,
  `@pytest.mark.live`) was run explicitly and **passed 2/2** against a real pinned Alpine image
  with real container start/cleanup — genuine, live proof the capability works in this
  environment, short of a cells/python-specific Docker-verified run.

## What is NOT done, and why (honest, not fabricated)

**"Full battery green" was not achieved.** The real `validation.json` from both runs reports
`deterministic_verdict: "reject"` with concrete, real reasons:

- **9 blocking claim-accountability gaps** (`claim_accountability_complete: false`).
- **9 unauthorized protected-content losses** (`technical_terminology:*` fragment IDs).
- **A structurally invalid disposition ledger**: 13 of the original README's units (its H1 and
  effectively every H2 section) are `VERIFIED_MERGED`/`SUPERSEDED` in `dispositions.json` but
  carry an empty `target` field, which the ledger validator correctly flags as "retained unit
  without candidate destination" for all 13.

These are **real defects in the existing (pre-T5), soon-to-be-retired LLM/agentic composer
path** (`readme/agentic_composition.py` and friends) — the "old composer path" this entire plan
already designates a fallback, explicitly scheduled to retire at `T12` once the new deterministic
+ gateway-DAG pipeline (`T6`-`T8`) replaces it. T5's own card scope is a **pilot skeleton**, not
a mandate to debug and fix the pre-existing composer's disposition-ledger/claim-accountability
wiring — that repair is out of proportion to "skeleton," touches shared, heavily-consumed
machinery no lane in this plan currently owns, and duplicates work that rightfully belongs to
later cards (`T7D` dispositions, `TP-11A` preservation core) once the new pipeline exists to
receive the fix. Recorded here as a genuine, disclosed finding — not fixed, not hidden, not
force-passed.

**Full canonical Docker-verified run not completed.** `supervise --repo ... --execution-profile
local_dry_run` did not finish within available session time (terminated, no output). `--execution
-profile local_poc` (the CLI's own named full-coverage profile) requires `--registry
data/products.json` — a whole-30+-product portfolio run, disproportionate for a single-repo
pilot and not attempted for that reason.

## Investigated: is the disposition-ledger `target` defect a small, bounded fix?

A first pass (research delegated, not yet verified firsthand) suggested yes: `build_source_
disposition_ledger` (`commands_poc.py:96-205`) hardcodes `"target": ""` at line 181 regardless
of disposition, while a `ReadmeDocumentPlanV1.composition_ledger` field
(`readme/document_plan.py:266`) with exact source-to-candidate byte-span placements
(`ExactSourcePlacementV1.structural_role`, e.g. `"h2:Installation"`) appeared to sit one field
away, unread.

**Direct verification (reading the actual code paths, not trusting the first pass) found this
was too optimistic.** `composition_ledger: ReadmeCompositionLedgerV1 | None = None` defaults to
`None`, and grepping confirms `document_renderer.py` — the module `build_readme_document_
candidate` lives in, which is exactly what `idea_candidate.py::prepare_idea_fidelity_candidate`
(the function `commands_poc.py::_compose` calls) uses — **never sets it**. The real builder,
`composition_lineage.py::build_composition_ledger`, is only called from `document_plan_
finalizer.py` and `presentation/verified_template_document.py` — a **different** finalization
path than the one the diagnostic `poc` runner exercises. So `composition_ledger` is always
`None` on this code path; there is no unread byte-span data sitting nearby to consume.

A byte-accurate `target` genuinely does not exist anywhere in this run's data for the majority
of units (the ones disposed via `claim_accountability` records): `ReadmeClaimAccountabilityV1`
(`claim_accountability_models.py`) stores only the *source*-side byte span
(`source_byte_start/end`, `survives_in_candidate: bool`); the candidate-side span is computed
transiently inside `_source_claim_has_candidate_placement`
(`claim_accountability.py:145-163`) and **discarded before being stored anywhere**. A correct
fix requires either (a) extending `ReadmeClaimAccountabilityV1` to retain that candidate-side
span — a change to shared, validated, heavily-consumed claim-accountability machinery, not a
localized one — or (b) wiring `build_composition_ledger()` into the `document_renderer.py`/
`idea_candidate.py` path, with unassessed effects on other consumers of that plan.

A cheaper heuristic (match each unit's own heading text against the candidate's real H2
headings, confirmed present: `## Navigation`, `## Installation`, `## API Reference`, etc.) was
considered and **deliberately rejected**: the real candidate is missing an `## At a Glance` H2
entirely (its content was apparently folded elsewhere), yet that exact unit is disposed
`VERIFIED_MERGED` — a same-name-heading heuristic would leave it unresolved (correctly, by
accident) for that one case, but would produce a plausible-looking-yet-unverified `target` label
for every other unit, exactly the kind of "looks fixed but isn't semantically accurate" shortcut
this session's own discipline rejects. **Not implemented.**

## Third-round correction: empirical verification supersedes both prior static-analysis guesses

Static code reading alone produced two successive wrong conclusions above (first "small fix,"
then "claim_accountability is always None on this path"). Rather than trust a third round of
static tracing, the actual `render` dict was inspected directly (a small, throwaway diagnostic
script monkeypatching `build_source_disposition_ledger` to print its real inputs, run against
the same hash-bound cached plan — zero new LLM calls, not repo-committed):

- `readme_document_plan.claim_accountability` **is populated** — 137 real claim records, by
  `expected_disposition`: `accepted_fact` 76, `verified_obligation_replacement` 20,
  `presentation_policy_correction` 13, `unjustified_loss` 9, `configured_standard` 9,
  `verified_equivalence` 8, `deferred_verification` 2.
- A separate, ALSO-real, top-level `render["claim_map"]` (72 entries,
  `ReadmeClaimMapV1`, not the same type) carries genuine **candidate-side** byte positions
  (`byte_start`/`byte_end`, `coordinate_space: "candidate_utf8"`), keyed by `fact_id` — a
  namespace shared with `claim_accountability` records' `accepted_fact_ids`. **12 of the 13
  distinct fact IDs referenced by `accepted_fact`-disposed records resolve in this cross-
  reference** — a real, groundable path for that bucket (the largest, 76 of 137 records).
- `equivalent_candidate_claims` (the field that would ground `verified_equivalence` records
  directly) is populated in **zero of the 8** `verified_equivalence` records for this real run —
  the structured-equivalence machinery that fills it is wired to `composition_ledger`
  (confirmed absent on this path, see above), so it's empty here too.
- No grounding path was found for `presentation_policy_correction` (13), `verified_obligation_
  replacement` (20), `configured_standard` (9), or `deferred_verification`/`unjustified_loss`
  (11) — 53 of 137 records, over a third of the total.

**Decision: still not implemented.** The `accepted_fact` cross-reference is real and would let
`target` be computed correctly for a genuine subset of units — but building it requires new
logic (byte-range block aggregation per unit, mapping a resolved candidate byte position to its
containing H2 section, honest partial-coverage handling for the remaining ~40% of records with
no grounding found), and — critically — **doing so is very unlikely to flip `disposition_ledger
_valid` to `true` for this run**, since several of the 13 originally-flagged units may depend on
the ungrounded buckets. Implementing a genuinely new, partially-effective feature under
continued time pressure, without being able to confirm it reaches T5's actual completion bar, is
exactly the kind of expanding, uncertain-payoff scope this session's discipline steers away from.
This finding — materially more precise than either prior guess — is left as the documented
starting point for whoever takes on the real fix.

## Fourth check: exactly which of the 13 flagged units would the groundable fix actually resolve?

Rather than leave the payoff as "uncertain," the real `dispositions.json` was cross-checked
directly against the exact 13 flagged unit names:

| Unit | Disposition | Reason (verbatim prefix) |
|---|---|---|
| H1 title | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| Navigation | VERIFIED_MERGED | "policy-owned spans cover the complete claim..." |
| At a Glance | VERIFIED_MERGED | "policy-owned spans cover the complete claim..." |
| Installation | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| Additional Examples | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| Add Data Validation (H3) | VERIFIED_MERGED | "bound to an exact independently accountable candidate claim..." |
| Export to CSV (H3) | VERIFIED_MERGED | "bound to an exact independently accountable candidate claim..." |
| Password-Protect a Workbook (H3) | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| API Reference | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| Documentation & Resources | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| Scope and Limitations | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| Development and Testing | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |
| License | SUPERSEDED | "replaced by a mandatory golden-contract slot..." |

**9 of 13 are `SUPERSEDED` via the golden-contract-slot-replacement reason** (the
`verified_obligation_replacement`/`authoritative_correction` bucket — confirmed ungrounded, no
candidate-side cross-reference found anywhere). **2 of 13 (Navigation, At a Glance) carry the
"policy-owned spans" reason** (`presentation_policy_correction`/`configured_standard` bucket —
also confirmed ungrounded). **Only 2 of 13 (the two H3 examples) show the `accepted_fact`-style
reason** — the one bucket with a real, groundable cross-reference via `claim_map`.

**This confirms, with exact numbers rather than an estimate, that the groundable fix would
resolve at most 2 of the 13 currently-flagged units — the earlier "uncertain payoff" judgment
was correct.** Genuinely fixing this ledger requires resolving the golden-contract-slot and
policy-owned-span buckets (11 of 13), for which no candidate-side location data exists anywhere
in this run's real output. Confirmed not worth implementing the partial `accepted_fact` fix
alone; the real fix is comprehensive candidate-span tracking across all disposition sources, a
properly-scoped card of its own.

## Fifth, final check: is the golden-contract-slot (SUPERSEDED, 9/13) bucket groundable via
`document_plan.operations`?

One more real candidate data source existed and was checked before concluding: `ReadmeDocument
PlanV1.operations` (`document_plan.py:267`), each a `ReadmeDocumentOperationV1` with a `source_
byte_start/end` span and a literal `replacement_text` — the exact same "find the literal
replacement string in the candidate" technique `claim_map.py` itself already uses elsewhere.
Diagnostic: for each of the 20 real `verified_obligation_replacement`/`authoritative_correction`
claim records, find the operation(s) whose source span covers/overlaps the claim's source span,
then check whether that operation's `replacement_text` is findable in the real candidate bytes.

**Result: `operations count: 1`.** The entire candidate is produced by a single, monolithic
`readme.verified-template.compile` operation spanning source bytes `0`–`20006` (the whole
original document) with a `15,775`-byte `replacement_text` (essentially the whole new document
body, `candidate_text` is `15,778` bytes total). Every one of the 20 claims trivially "resolves"
to this one operation — not because a genuine per-section mapping exists, but because there is
only one operation, covering everything. Its `replacement_text` is found in the candidate at
byte 0 for every claim, which reveals *nothing* about where within that block each specific
unit's replacement content actually landed. **This is a real dead end**: the golden-contract
compile step does not track section-level provenance internally at all — it operates as one
whole-document rewrite, not a set of per-section operations. Confirmed via the operation's own
byte-span (matching the whole source) and replacement-text length (matching nearly the whole
candidate), not assumed.

## Correction to the above: `composition_ledger` is NOT "never populated" — that claim was wrong

The paragraph above (and the commit that recorded it) stated `composition_ledger.source_
placements` is "never populated on this path," reasoning from a `grep` of `document_renderer.py`
that found no direct `composition_ledger` assignment. That grep missed a delegation:
`document_renderer.py::build_readme_document_candidate` (line 138) calls `presentation/
verified_template_document.py::build_verified_template_document_candidate` whenever
`facts.content_assurance == "repository_verified"` and an agentic plan is present — both true
for this real run — and *that* function (`verified_template_document.py:154-160`) does call
`build_composition_ledger(...)` with real `compiled.source_placements`.

**Empirically re-checked directly** (not re-grepped): `composition_ledger` **is populated** —
`source_placements` has **5 real entries**, each with genuine, non-fabricated `final_byte_start/
end` candidate-side positions (e.g. `source_byte_start=4207` → `final_byte_start=14464`,
content-hash-verified equal on both ends). `structural_role` is `null` on all 5 (reserved for a
different `placement_basis`, per the schema's own validator), so there's no ready-made heading
label, but the byte positions themselves are real and usable.

**However — cross-checked against the exact 13 flagged units' source byte ranges: zero overlap.**
None of the 5 real placements' `source_byte_start/end` falls inside any of the 13 flagged units'
block ranges. So the earlier practical conclusion (this data source does not ground the 11
ungrounded flagged units) **is still correct** — only the stated reason ("never populated") was
wrong; the accurate reason is "populated, but with too few placements (5, versus 137 claim
records) to cover this run's flagged units." Recorded here rather than left standing as a
factual error in committed evidence, per this session's standing discipline.

**This closes the investigation exhaustively, with a corrected record.** Three genuinely
distinct real candidate data sources were checked — `composition_ledger.source_placements`
(real, populated, but 0/13 flagged-unit overlap for this run), `equivalent_candidate_claims`
(populated in 0 of 8 eligible records), and `document_plan.operations` (exists, but is a single
whole-document operation with no internal section structure) — and none provides usable,
per-section candidate-location data for the 11 of 13 flagged units outside the `accepted_fact`
bucket, on this specific run. A genuine, general fix requires the compile step to emit
substantially more complete per-section placement data (or equivalent structured provenance) —
a real feature addition to the composition mechanism, not data that merely needs to be threaded
through from an existing, already-sufficient source.

## Why, architecturally: `source_placements` is not a "hasn't been wired up yet" gap

Tracing `build_verified_template_compilation` (`presentation/verified_template_runtime.py:63-
159`) end to end: the compiled candidate is built by `compile_repository_presentation` (freshly
generating template-driven prose from `ProductFactsV2`, the great majority of the document's
bytes), then `compose_verified_source_preservation` (`verified_source_policy_application.py`)
splices back in the *specific, narrow* spans of the **original** README that are authorized to
survive verbatim. `composition.source_placements` — the 5 real entries found above — comes from
*that splice-back step alone*. It is not a general "every unit's candidate location" registry;
by construction it only covers verbatim-preserved source bytes. Freshly-generated,
template-compiled content (the `SUPERSEDED`/"golden-contract-slot" bucket, 9 of the 13 flagged
units, and the bulk of the document) was never copied from source at all, so there is no
"placement" for it to have — not a bug, a category the concept doesn't apply to.

**This confirms the earlier verdict with real understanding of the mechanism, not just an
absence of data found by searching**: a genuine fix needs a *different kind of tracking* than
`source_placements` provides — a slot-to-candidate-byte-range map from the template compiler
itself (`compile_repository_presentation`, `presentation/template_compiler.py`), recording which
compiled slot occupies which candidate bytes and which original units it replaces.

## Assessed implementation directly (not just conceptually) — a real, additional complication found

`compile_repository_presentation` (`template_compiler.py:74-112`) does build each slot's content
as one discrete, identifiable block (`blocks.append(f"## {contract.headings[slot]}\n\n{body}")`,
line 106) joined with a fixed `"\n\n"` separator — a byte-range-tracking sibling function
(compute each block's position via `.find()` in the joined output, in order) is genuinely
implementable without touching the existing function's behavior at all.

**But that only gives spans in the *freshly-template-compiled* candidate — not the *final* one.**
`compose_verified_source_preservation` (`presentation/verified_source_preservation.py:60-`)
runs afterward and, for preserved source sections, explicitly **inserts** blocks whose heading
is `not in block_by_identity` (line 99: `if heading_identity(section.title) not in
block_by_identity`) — i.e. it adds *new* H2 blocks for headings the compiler's output doesn't
already contain, rather than substituting equal-length bytes within an existing slot. An
insertion shifts every byte position after it. So a slot-span map computed against the
pre-preservation candidate would **not** be valid against the actual final candidate
(`render["final_text"]`) without also accounting for every insertion's effect on downstream
offsets — a second, distinct piece of correctness work, not merely "thread the data through."

**Revised decision: implemented, using a different technique that sidesteps the coordinate-shift
problem entirely.** Byte *offsets* computed at the pre-insertion stage are invalid after
insertion — but a *substring search* against the actual final candidate is not, since `.find()`
re-locates content wherever it ends up regardless of what happened in between (the same safe
pattern `claim_map.py` already uses for `operation.replacement_text`). So instead of tracking
byte offsets, a new sibling function tracks each slot's exact compiled **block text**
("`## Heading\n\nBody`"), computed once at compile time, then looked up by substring search
against the real final candidate at ledger-build time — no offset arithmetic, no coordinate
systems to reconcile.

### What was built (real, tested, verified against the live pilot)

- `presentation/template_compiler.py::compiled_slot_blocks()` (new, additive-only — the existing
  `compile_repository_presentation` is untouched, verified via `git diff`): returns each included
  slot's exact compiled block text, keyed by heading.
- `VerifiedTemplateCompilationV1` (`verified_template_runtime.py`) and `ReadmeDocumentPlanV1`
  (`readme/document_plan.py`) each gain a new, additive, defaulted field
  (`compiled_slot_blocks: dict[str, str] = Field(default_factory=dict)`) threaded through
  `build_verified_template_compilation` → `build_verified_template_document_candidate`.
- `commands_poc.py::build_source_disposition_ledger`: for any unit disposed `VERIFIED_MERGED`/
  `SUPERSEDED`, look up its heading in `compiled_slot_blocks` and confirm the exact block text is
  present in the real final candidate before setting `target` — grounded proof, never a guess.

**First attempt had a real bug, found and fixed via direct debugging, not assumed correct**: the
extracted source heading label carries its literal markdown prefix (`"## Installation"`), while
`compiled_slot_blocks` is keyed by the bare contract heading (`"Installation"`) — a plain string
mismatch, fixed with `heading.lstrip("#").strip()`, confirmed via a monkeypatched live pilot
re-run showing the exact before/after.

**Verified against the real pilot (`aspose-cells-foss/Aspose.Cells-FOSS-for-Python`)**:
`disposition_ledger_errors` dropped from **13 to 7** — Installation, Additional Examples, API
Reference, Scope and Limitations, Development and Testing, and License now correctly resolve
their `target`, each proven by real substring match against the compiler's own output (evidence:
`validation-after-fix.json`, `dispositions-after-fix.json`). The remaining 7 have individually
understood, legitimate reasons untouched by this fix: H1/Navigation are fixed, non-slot blocks
(not part of the per-slot loop this fix targets); the 3 H3 examples are sub-headings nested
*within* the (now-resolved) Additional Examples slot, not their own top-level slots; "At a
Glance" genuinely was not included in this compilation; "Documentation & Resources" (source
spelling, with `&`) does not match the contract's canonical "Documentation and Resources" (with
"and") — a real, different, disclosed finding (a spelling divergence between the source README
and the template contract), not something this fix should paper over with a fuzzy match.

**3 new tests** (`tests/unit/test_template_compiler_slot_blocks.py`), all passing, proving
`compiled_slot_blocks` matches the real compiler's output, omits non-included slots, and never
alters `compile_repository_presentation`'s own behavior (byte-identical output before/after).
Adding fields to `ReadmeDocumentPlanV1`/`VerifiedTemplateCompilationV1` legitimately shifted 4
pre-existing TB-01-style plan-hash characterization constants (`test_agentic_readme_
composition.py`, `test_readme_composition_characterization.py` ×3) — confirmed via the same
`DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS` mechanism already encountered once this session for
T10, re-baselined with the fresh values, all other characterization hashes (source/facts/
assessment/candidate bytes) unchanged. **Full governed suite: 3,911 passed, 1 skipped, 0
failed** (up from 3,908 before this fix — the delta is exactly the 3 new tests).

**Still not COMPLETE**: even with this real fix, the overall candidate remains
`deterministic_verdict: reject` — 9 unauthorized protected-content losses and 9 blocking
claim-accountability gaps are separate, independent defects this fix does not address (and
which were never in scope for the disposition-ledger investigation). "Full battery green"
requires resolving those too, which is real, separate, unstarted work.

## Downstream effect

`GC-03` (Gate G3 close) requires **both** `T14` (COMPLETE) and `T5` COMPLETE — it stays blocked.
The genuine fix is real but larger than a pilot-skeleton card's scope: extend candidate-side
span tracking in the claim-accountability model (touches shared, validated machinery) or wire
the existing `build_composition_ledger()` into the diagnostic composition path — both warrant
their own scoped card with dedicated tests, not a rushed patch inside T5.
