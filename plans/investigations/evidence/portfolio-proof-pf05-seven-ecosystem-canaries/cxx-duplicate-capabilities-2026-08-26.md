# PF05-CXX-DUPLICATE-001 — Key Capabilities is composed twice

## Status

Root-caused, **not** repaired. The repair is a design decision in shared
presentation composition that affects every repository, so it is recorded here
rather than attempted as a fourth same-session change to shared machinery.

## Symptom

The C++ canary (`aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` @
`9f852d0ff1cfdad2d661556d6b87a8eff8c063a2`) stops in `presentation_plan` with:

```
presentation.semantic_duplicate.7f247683b2ff: Capability information is repeated across competing visitor sections.
public_quality.malformed_low_information_prose.6bec24bc9114: Capability information is repeated across competing visitor sections.
public_quality.contradiction_capability_symbol.4fdfcf7f20cc: `DateTime` is described as available in one section and explicitly unsupported or unimplemented in another.
```

## Root cause

The candidate's single `## Key Capabilities` section contains **two complete
capability lists** in two different renderings:

**Block A** — LLM-authored cluster, rendered by
`presentation/section_authoring_overlay.py::authored_unit_markdown()` as
`- **{heading}** - {text}` (em dash, no backticks):

```
- **Read and write cell values and formulas** - Use Cell.PutValue() to insert strings, ...
- **Apply cell styles** - Retrieve and apply a Style object via Cell.GetStyle() ...
- **Merge cell ranges and apply number formats** - Create merged regions with Cells.Merge() ...
```

**Block B** — the *source README's own* Key Capabilities bullets, preserved
verbatim (colon, backticked symbols, ~95-column wrapping):

```
- **Read and write cell values and formulas**: `Cell.PutValue()` accepts strings, integers,
  doubles, bools, and `DateTime`; `Cell.GetValue()` returns a variant-typed `CellValue`, and ...
```

Three headings are byte-identical across the two blocks ("Read and write cell
values and formulas", "Apply cell styles", "Merge cell ranges and apply number
formats").

Both halves are individually *correct*, which is why no earlier gate caught it:

- `presentation/verified_template_draft.py:503` already does the right thing --
  `capability_text = authored_capabilities.markdown` **replaces** the
  deterministic capability rows rather than appending to them. The duplication
  is not draft-level.
- The source bullets are legitimately preserved: their claim-accountability
  dispositions are `accepted_fact` with `survives_in_candidate = True` (five of
  nine; the other four are `presentation_policy_correction`, dropped). They are
  fact-bound and true, so preservation is correct in isolation.

The defect is that nothing reconciles the two producers: surviving inherited
capability bullets and a newly authored capability cluster can both land in the
same section, covering the same capabilities.

## Why the `DateTime` finding is entangled with this

The contradiction's "available" side is at candidate offset 5415-5507 -- inside
**Block B**, i.e. inherited source text (`` `Cell.PutValue()` accepts ... `DateTime` ``).
Its "unsupported" side is `- `DateTime` is not implemented in this FOSS package.`
under Scope and Limitations > API Member Gaps.

That negative claim is the already-logged **`CORE-038`** false positive: the
vendored C++ empty-body-stub detector does not recognize a constructor whose
work lives in its member-initializer list, so it reports the fully-implemented
`Aspose.Cells.Foss.Cpp/src/DateTime.cpp:77` as an unimplemented stub. The
*source* README is right and the detector is wrong -- see
`cxx-datetime-stub-false-positive-2026-08-25.md`.

Note that Block A also mentions DateTime, but as plain text ("bools, or DateTime
values") rather than the backticked `` `DateTime` `` symbol the exact-symbol
check keys on. So removing Block B alone could incidentally silence this
finding **without** fixing `CORE-038` -- the false limitation claim would remain
in the fact graph and would keep contradicting any future backticked mention.
Do not treat a duplicate-composition fix as having resolved `CORE-038`.

## Candidate repair directions (not chosen)

1. Suppress the authored capability cluster when inherited capability bullets
   survive for the same section, deferring to fact-bound source wording.
2. Suppress surviving source bullets whose headings the authored cluster already
   covers, keeping one reconciled list.
3. Reconcile by heading at composition time, merging the two into a single list.

Option 2 or 3 preserves the authored cluster's ability to add capabilities the
source omitted (Block B carries "Create or load `.xlsx` workbooks", which Block A
lacks), so a naive "drop the authored cluster" fix would lose coverage. Whichever
is chosen must keep every surviving source bullet's claim accountability intact:
these bullets are currently `accepted_fact`/`survives=True`, and dropping them
without a disposition would reintroduce `unjustified_loss`.

## Reproduction

```
.venv/Scripts/readme-agent supervise --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp \
  --bounded-verified-canary --no-registry-heal --execution-profile local_poc \
  --mission-task-id L8-PF-05-SEVEN-ECOSYSTEM-CANARIES --mission-observer <agent>
```

Evidence: `runs/readme-poc/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/diagnostics/blocked-presentation-plan.json`
(finding spans and per-claim dispositions) and `.../diagnostics/blocked-candidate.md`
(the rendered duplicate section).

## Note on the escalation alert

The same run emitted:

```
escalation_alert: 'readme_presentation' has failed 3 consecutive runs for the
same reason ('presentation_plan') -- human attention needed
```

The counter keys on the coarse specialist/stage pair, not on the findings, so it
fired despite genuine narrowing across those three runs: 4 findings (link +
2 claim-accountability + duplicate/DateTime) → 3 → 3, with blocking
claim-accountability claims going 2 → 0. Treat it as a prompt to change tactic
on this boundary, which is what this write-up does, rather than as evidence that
the last three runs made no progress.

## Exact mechanism (traced 2026-08-26, supersedes the "candidate repair directions" above)

The duplicate is produced by verified source-detail routing, not by the draft or by a
missing disclosure wrapper:

1. `verified_template_draft.py:503` replaces the deterministic capability rows with the
   authored cluster, correctly. Block A is that cluster.
2. `verified_source_preservation.py:239-262` then routes surviving source capability
   blocks into their canonical destination and splices them in. The composition ledger
   names them exactly:
   `source.canonical-detail.key-capabilities.view-detailed-capabilities.0000..0004`
   (`placement_basis: composer_inserted_exact`). Block B is those placements.
3. `verified_source_detail_presentation.source_detail_presentation()` returns
   `leading=""`/`trailing=""` for this slot because `Key Capabilities` is in
   `contract.invariants.always_visible_slots`. That is **correct** and required by
   idea.md l.77-83 ("all selected core capabilities ... remain visible") -- the missing
   `<details>` is intended behaviour, not the bug.

So both lists render flat and visibly in one section, which is the
`presentation.semantic_duplicate` / `malformed_low_information_prose` finding, and
violates idea.md l.85 "Competing sections may not repeat the same capability inventory."

Note this is also why `apply_verified_source_density()` does not fold the section: its
`_source_owned(body_start, body_end, source_placements)` guard requires the *whole* body
to be source-owned, and this body is mixed authored + placed. Folding would be the wrong
fix regardless -- it would hide capabilities idea.md requires to stay visible.

### The repair, per idea.md

Source capability blocks whose capability the authored cluster already covers must not be
routed into the slot at all; each must instead carry exactly one disposition (idea.md
l.86, "maps exactly once"). Source tone and prose structure are explicitly not
preservation obligations, and the template owns organization, so the authored cluster
keeps the section.

Two hard constraints on the implementation:

- **Coverage.** A capability present only in the source -- here
  "Create or load `.xlsx` workbooks", which Block A lacks -- must still be preserved or
  improved in the authored cluster, or carry an explicit justified omission. Silent loss
  violates idea.md l.86.
- **Accountability.** These source claims are currently `accepted_fact` with
  `survives_in_candidate = True`. Ceasing to place a block flips it to not-surviving, so
  it needs a disposition in the same change or it reappears as `unjustified_loss` -- the
  same failure class that blocked this canary before the development-commands repair.

## Scope narrowed by the .NET receipt (2026-08-26)

`aspose-3d-foss/Aspose.3D-FOSS-for-.NET` reached `CONVERGED_PROPOSAL_READY` /
`AGENT_APPROVED` on its first attempt under the same code, with no
`semantic_duplicate`, no `malformed_low_information_prose`, and no
`preserve disposition lost a source claim` error.

So the duplicate-capability defect is **not** portfolio-wide. It depends on the
source README shape -- specifically a source `## Key Capabilities` section whose
bold bullet titles the authored cluster also produces. .NET's source does not
present that collision; C++'s does.

This is the concrete cost of having skipped PF05's declared order
(`FIRST_BOUNDARY_ALL_7` before `REPAIR_SHARED_ONCE`): the reverted attempt at
`verified_source_preservation.py` was a change to shared composition machinery
aimed at what is currently evidenced as a single-repository symptom. Any repair
must be re-justified against the full receipt set once the remaining ecosystems
(java, typescript, rust, go) have reported, and must not weaken the
`preserve`-disposition guard that correctly rejected the first attempt.

## The correct repair layer, located (2026-08-26)

The architecture already contains the mechanism this repair needs:
`verified_source_claim_matching.fact_bound_capability_candidate_claims()`, reached
from `equivalent_source_claim_resolution()`. Critically,
`resolve_source_claims()` tries that equivalence **before** the
`preserve`-disposition raise, so a source capability bullet that resolves as
`verified_equivalence` needs no verbatim placement and produces no duplicate.
This is the layer the reverted composition-layer attempt should have used.

Measured against the real C++ data:

- the duplicated source bullet **does** bind `product.capabilities`
  (`_complete_claim_fact_binding` returns it), and
- the candidate **does** carry capability provenance citing the same fact, in
  both forms:
  - `template.section-authoring.key_capabilities.01.00/.01/.02` (the authored cluster)
  - `template.section.key_capabilities.claim:0:... / :271:... / :514:...`
- yet `fact_bound_capability_candidate_claims(...)` returns **0 matches**.

So the blocker is not provenance prefix and not fact citation. It is one of the
narrower conditions inside the matcher -- most plausibly
`capability_discriminators()` / `_coordinates_complete_for_required_facts()`:
the inherited bullet carries identifier discriminators (`Cell.PutValue()`,
`CellValue`, `DateTime`) that the authored rewording does not reproduce, so the
matcher declines to call the two claims equivalent.

If that is confirmed, the matcher is **behaving correctly** and the real finding
is editorial rather than mechanical: the authored cluster is less
identifier-precise than the maintainer's own bullet, and idea.md l.307-316
("reuse wherever validation permits", "regeneration convenience is never a
reason to discard valuable curated information") favours the source wording in
exactly that case. The repair would then be to prefer the fact-bound source
bullets for this section and skip the authored cluster -- the option ruled out
earlier on an l.322 reading that, on closer inspection, governs the candidate as
a whole rather than requiring every section to be model-authored.

Next step: instrument `fact_bound_capability_candidate_claims` on this exact
pair to identify which condition rejects it, then choose between (a) making the
authored cluster preserve the source's discriminators, or (b) preferring the
source bullets for this section. Do not weaken the matcher itself; its precision
is what prevents a lossy reword from being accepted as equivalent.

## Why equivalence cannot resolve this, measured (2026-08-26)

Four attempts, each rejected by a different real invariant. Recorded so the next
attempt does not repeat them:

1. **Composition layer** -- declining to place the routed block. Rejected by
   `resolve_source_claims`: a `preserve`-dispositioned claim must survive
   byte-exact or carry an exact fact-bound replacement.
2. **Required-facts narrowing** -- excluding incidental fields from
   `_capability_equivalence_fact_ids`, mirroring the documented
   `_limitation_equivalence_fact_ids` precedent. This *did* fix the fact-id gate
   (`required_source_fact_ids.issubset(...)` went False -> True) but did not
   resolve the match, so it was reverted rather than shipped unproven.
3. **Document withholding** -- dropping the authored `key_capabilities` outcome
   before the draft and provenance see it. Rejected because the
   section-authoring document is checksum-bound to the plan:
   "section-authoring document is absent or differs from the plan binding".
4. **Coordinates** -- the actual barrier, and not relaxable.

The decisive measurement, on the real C++ pair:

```
required fields        : ['product.capabilities']     (after narrowing)
required coordinates   : 1   -> product.capabilities /items/e98ef500be51ad93
candidate coordinates  : 0
fact subset            : True
coords cover           : False
```

The inherited bullet binds an **exact capability list item**; the authored
rewording binds **no coordinate at all**. `_coordinates_cover` demands exact
coordinate identity, and the sibling limitation docstring states the principle
plainly: "the exact list coordinate remains mandatory". Relaxing it would let any
sufficiently similar prose claim equivalence with a specific verified capability
-- precisely the lossy-reword acceptance the matcher exists to prevent.

**Conclusion: equivalence is the wrong instrument here.** A reworded authored
cluster can never prove coordinate-level equivalence with a maintainer bullet, so
as long as both are produced, one must be preserved verbatim and the duplicate is
structural.

The remaining viable repair is to not produce both, decided **before** section
authoring runs -- the authoring request for `key_capabilities` should be skipped
when the source's own bullets already bind capability coordinates the rewrite
cannot. That is upstream of the hash-bound document, so it avoids invariant (3),
and it needs no change to the matcher, so it avoids weakening (4).

`verified_source_capability_precedence.py` already implements the decision
predicate (`authored_cluster_loses_source_facts`) with tests against real canary
data; only its wiring point still needs to move upstream of authoring.
