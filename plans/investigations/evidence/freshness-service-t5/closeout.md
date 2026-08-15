# T5 — deterministic pilot skeleton (cells/python)

**Status: SUBSTANTIAL PROGRESS, not COMPLETE.** Recorded honestly — the card's own closeout bar
("full battery green + byte-identical double run") is only half met: the double-run proof is
real and complete; the battery did **not** go green, for reasons genuinely outside this card's
scope (see below). `GC-03` (G3 close) correctly stays blocked until this is resolved.

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

## Downstream effect

`GC-03` (Gate G3 close) requires **both** `T14` (COMPLETE) and `T5` COMPLETE — it stays blocked.
The genuine fix is real but larger than a pilot-skeleton card's scope: extend candidate-side
span tracking in the claim-accountability model (touches shared, validated machinery) or wire
the existing `build_composition_ledger()` into the diagnostic composition path — both warrant
their own scoped card with dedicated tests, not a rushed patch inside T5.
