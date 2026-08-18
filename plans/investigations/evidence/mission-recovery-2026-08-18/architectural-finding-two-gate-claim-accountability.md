# Architectural finding: two claim-accountability gates, only one is LLM-assisted

Discovered live 2026-08-19 while investigating why note-python stayed blocked after the
fixture-existence fix (`04ad3e669`) despite `claim_conflicts=0` at the presentation-plan stage.

## The two gates

1. **`presentation_plan` (first gate)**, in `specialists/readme_presentation.py`: builds the
   document plan with `llm_disposition_client`/`repository_root`/`disposition_ratchet_path` all
   supplied — claim accountability here CAN use the LLM-disposition fallback (E5) and the
   ratchet.
2. **`factuality_rejected` (second, independent gate)**, `specialists/readme_factuality.py::
   evaluate_candidate_factuality()`: **rebuilds the document plan a second time, from scratch,
   via the same `build_readme_document_candidate()` — but never passes
   `llm_disposition_client`, `repository_root`, or `disposition_ratchet_path` at all.** This is
   deliberate, matching VER-001's "independent verification never trusts the model's own
   say-so" principle: it re-derives claim accountability using ONLY the mechanical
   `_covered_by_fact_variants` check, with zero LLM involvement.

**Consequence, confirmed live**: a claim accepted only through the LLM-disposition path (E5)
passes gate 1 but is re-derived as unaccounted-for at gate 2, every time, by design — E5 alone
can never fully unblock a repository. Only a claim that survives the MECHANICAL check — because
the underlying assertion is actually, textually present in the rendered candidate — clears both
gates.

## Confirms exactly what was already observed, now explained

- **page-python** (Lane A, pure deterministic rendering): reached full `CONVERGED_PROPOSAL_
  READY`/`AGENT_APPROVED`. The Dependencies sentence is now literally rendered in the
  candidate, so the mechanical check at gate 2 finds it — no LLM needed at either gate.
- **barcode-python** (E5, LLM disposition): blocking count fell 2→1 at gate 1, but the
  repository never reached full approval. The `pytest`/`ruff` claim's disposition is a
  classification decision, not new candidate text — gate 2 never sees it as accounted for.
- **note-python** (this session's fixture-existence fix, also LLM disposition): identical
  pattern. `claim_conflicts=0` at gate 1, `protected_losses=1` at gate 2 citing the exact same
  claim id (`0d4d28fef68b38fd`) the fix "closed."

## The real aspose.org lesson, restated more precisely

Lesson 1 (existence-only fixture evidence) and lesson 2 (API-shape evidence) are both real and
correctly implemented — but they were framed as fixing "claim disposition," when the deeper
aspose.org lesson is architectural: **aspose.org's disposition IS the render.** There is no
separate "trust an LLM classification without the candidate text actually changing" step in
their pipeline — when a unit is `merged_reframed`, the reframed text is what ships in
`readme.md`. Disposition and composition are the same act, not a composition pass followed by a
free-floating LLM approval of already-fixed text.

Our architecture split them: compose deterministically (or via a constrained tool call), THEN
separately ask an LLM whether an unbound claim's ORIGINAL WORDING is accounted for by the
candidate that already exists. That split is exactly why an accepted disposition can leave the
underlying gate-2 mechanical check unsatisfied — the disposition never fed back into what got
rendered.

## What this means for the engineering queue (revised)

- **E5 (LLM disposition) is real, useful, and should stay** — but its value is narrower than
  originally framed: it is a **first-gate triage/narrowing tool** (proves which claims a human
  or a later deterministic pass should focus on) and a **quality signal** (reduces noisy
  first-gate blocking so genuine deterministic-fix targets are visible), not a standalone
  closure mechanism. Its live wins (barcode, note gate 1) are real narrowing, not full closure —
  correctly re-documented here rather than left implying more than they delivered.
- **Lane A/B-style fixes (make the claim's assertion literally present in the rendered
  candidate) are the only mechanism that closes a repository completely.** This reframes the
  S1 residue map's priority: Lane A (Dependencies H3 rendering) and Lane B (API Method Index
  properties, and now — by the same logic — Key-Capabilities composition richness) are not one
  option among several; they are the ONLY path to full closure for any claim currently only
  passing via E5.
- **Concretely for note-python**: the SimpleTable.one Quick Start example needs to be actually
  composed into the candidate (verbatim or reframed, aspose.org-style) — not merely have its
  disposition accepted by an LLM — for the repository to reach `AGENT_APPROVED`. This is
  Lane C's real completion condition, not "accept the claim's disposition."
- **Concretely for barcode-python's u0017 claim** (the API-surface-evidence lane currently in
  flight): the same caveat applies. If that lane closes gate 1 the same way E5 did, it will
  need a companion Lane-B-style composition change (render a Key-Capabilities bullet whose text
  genuinely contains the claim's asserted content) to also clear gate 2 — flagged for the
  worktree agent's own verification once it reports back, and for whoever picks this up next if
  it doesn't close gate 2 on its own.

## Diagnostics added to make this investigable going forward

`_persist_blocked_factuality_diagnostics()` (commit `bd1052529`) persists
`runs/readme-poc/<repo>/diagnostics/blocked-factuality.json` on every gate-2 rejection, sibling
of the existing gate-1 `blocked-presentation-plan.json` — this investigation was only possible
because that diagnostic now exists; before it, the only trail was a durable-state field that
rotates out with the next trigger-lifecycle transition.
