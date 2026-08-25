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
