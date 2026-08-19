# Phase-2 finding: the T3 check battery is far more complete than assumed, with a precise 11-check gap

Follow-up to `2026-08-19-vendored-scripts-gap.md`, which found the vendored
`src/readme_agent/vendored_asposeorg/**` tree had drifted from live upstream but stopped at
detection. This note corrects an assumption from that earlier pass and quantifies the gap
precisely for one concrete piece of it.

## Correction: the check battery is thoroughly ported, not a gap

Initial assumption (wrong, corrected by direct inspection): that most of aspose.org's
deterministic validation logic was unported. Direct check:
`readme_agent.validation.aspose_checks.load_check_registry()` returns **89 entries** —
every single `check_*` function defined in our vendored `readme_refresh_checks.py`, with zero
omissions (`T3`'s own docstring already said this: "wraps every `check_*` function... derived
mechanically from the vendored module's own docstring"). Confirmed live-wired, not just
registered-and-unused: `readme/document_validation.py` and
`validation/aspose_checks_bridge.py` both call into this registry as part of the real candidate
validation path. This is a large, genuine `REUSE_CURRENT` win for the Phase-2 dependency-closure
matrix — the deterministic quality-gate layer (badge checks, dependency checks, diagram checks,
content-disposition checks, the whole `check_process_narration_smells`/
`check_section_intro_no_meta_narration` prose-narration family, etc.) did not need reinventing.

## The precise gap: upstream has grown to 100 checks; we have 89

Direct name-set diff (`grep '^def check_'` on both files, upstream `readme_refresh_checks.py`
vs. our vendored copy):

```
upstream: 100 check_* functions
vendored:  89 check_* functions
vendored ⊂ upstream (zero checks exist in our copy that aren't in upstream — a clean subset,
confirming staleness, not divergence/corruption)
```

**11 checks exist upstream that our vendored copy has never picked up:**

- `check_code_example_excluded_reason_citation_too_narrow`
- `check_content_unit_redundant_claim_verifiable`
- `check_dependency_development_claim_not_in_manifest`
- `check_diagram_from_scratch_capability_labeled`
- `check_diagram_label_geometry`
- `check_frozen_blocks_unchanged`
- `check_image_content_unit_excluded_reason_verified` (referenced by name in the live skill's
  own prose, `skills/readme-refresh.md` §MT051, as a tripwire for wrongly excluding real
  screenshot content — directly relevant, see below)
- `check_issue_draft_rejection_list`
- `check_no_internal_details_leaked_into_issue_draft`
- `check_no_upstream_issue_leaked_into_install_or_quickstart`
- `check_scope_compliance`

Not yet individually read/triaged (each needs its own read to classify whether it's applicable
to this system's scope — several look tied to aspose.org's own `upstream_issue_workflow.py`,
which we deliberately never vendored at all, e.g. `check_no_internal_details_leaked_into_issue_
draft`/`check_issue_draft_rejection_list`).

**One checked directly, and it's not a quick port**: `check_frozen_blocks_unchanged` (MT056)
looked like a generically valuable candidate on its name alone, but its real implementation
depends on aspose.org's "acceptance-registry" state machine (`declare-scope`/`accept-blocks`/
`converge-verify`, tracking per-block `CONVERGED`/`FROZEN_ACCEPTED` status across regeneration
passes so a surgical re-run can prove it touched only the declared scope) — a whole stateful
workflow concept this system has no equivalent for at all (our own accept/reject model is
candidate-level with content-addressed caching, not per-block). Porting this check meaningfully
means porting that supporting state machine first — `ADAPT_FOR_QWEN`-scale work, not a
mechanical `PORT_FROM_ASPOSE` drop-in. The other 10 are unchecked; do not assume any of them are
quick either without reading each one's real dependencies the same way.

## Disposition

Detection + precise scoping only, matching the same discipline as the sibling drift note — not
attempting triage-and-port here. Each of the 11 needs: (1) read its real upstream implementation
and docstring, (2) classify `PORT_FROM_ASPOSE` / `ADAPT_FOR_QWEN` / `UNRELATED` (issue-workflow-
specific ones are likely `UNRELATED`, since this system has no issue-drafting capability),
(3) for anything `PORT_FROM_ASPOSE`/`ADAPT_FOR_QWEN`, port following the same registration
pattern `load_check_registry()` already uses (fully mechanical — adding a function to the
vendored file and refreshing the vendored copy is sufficient; no `T3` wiring changes needed
since it derives its registry from the module automatically).

## Separately confirmed: the LLM-facing composition guidance is a distinct, NOT-yet-addressed layer

Reading `skills/readme-refresh.md` §Steps directly (not previously read in full this session)
surfaced a large body of prose-composition guidance that is architecturally different from the
`check_*` battery above and not mechanically portable the same way: "mandatory tone-exemplar
reading" before composing, the "Regeneration Comparison Protocol," the Enterprise Edition
anchor-text contract, and roughly a dozen more MT-numbered incident rules (MT030/031/034/039/
043/044/046/051/053/056...), each a specific, dated, narratively-justified composition rule for
the *human/LLM composing the prose*, not a deterministic post-hoc check. These map to Phase 4's
"bounded editorial decisions" and prompt-contract territory
(`prompts/generation/*.yaml`), not to the validator layer — genuinely separate porting work,
larger in scope than the check-battery gap above, not started this session. `font/python`'s own
`check_section_intro_no_meta_narration` history (MT046, 2026-08-15, already in our 89) is a live
example of exactly this class of rule already having been ported at least once before — a real,
working precedent for how this second category of work would proceed, not a hypothetical.
