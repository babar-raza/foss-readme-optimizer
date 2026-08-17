# Claim-accountability blocking: why 11/33 portfolio repos block, and what would actually close it

Investigated 2026-08-17 while GitHub's API outage blocked live portfolio verification (a
GitHub-independent investigation: uses only local clone caches under `runs/baseline/` and
`runs/readme-poc/` already on disk).

## The mechanism, traced to source

`document_validation.py`'s `claim_accountability_complete` check fails whenever
`plan.claim_accountability.blocking_claim_ids` is non-empty (`document_validation.py:520-544`).
A claim becomes "blocking" when nothing in `readme/source_claim_fact_binding.py` can bind it to a
verified fact. Traced the binding algorithm itself
(`source_claim_fact_binding.py::_covered_by_fact_variants`, lines 225-248):

- Every accepted fact is rendered into a set of normalized text "variants" (phrases).
- A claim is accepted **only if every substantive character of its normalized text can be
  covered by concatenated substring matches** against those variants (line 247-248: any
  uncovered alphanumeric remainder rejects the whole claim).

This is a whole-claim, character-level coverage requirement — not "does a fact support this
claim's gist," but "can this claim's literal text be reconstructed, span by span, from known
fact phrases."

## Concretely, on a real repo

`aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python`'s two real blocking claims (source revision
`06eca5c01e13ed6d59a640f1cf330c1c5a57d151`, cached locally):

- `claim:2626:...`: *"Select any symbology by name — canonical or alias — through the generic
  `generate()` (`generate(symbology, data)`) entry point, independent of the specific class."*
  Obligation: `major_capabilities` (routable, `disposition: preserve`).
- `claim:3930:...`: *"`pytest` >=8.0 and `ruff` >=0.15.7 — used only by the test suite and linter,
  never required to install or use the library."*
  Obligation: `dependency_requirements` (also routable, also `disposition: preserve`).

Both have a real, valid presentation destination — routing is not the problem (this is the
opposite failure mode from the `api.public_surface` gap fixed earlier today). Confirmed the
underlying fact **does exist**: `curated_python_public_surface.py`'s real AST extractor captures
module-level functions, not just classes, and `generate` is genuinely present in the extracted
`functions` list for this repo (verified directly: `'generate' in json.dumps(value)` is `True`).

The claim still blocks because the extracted fact is just the function's **name and signature** —
the AST extractor has no fact phrase for "canonical or alias," "generic," or "independent of the
specific class." Those are the original human author's own explanatory framing, not something a
signature-level extractor produces. The claim's literal text can never be fully covered by
concatenated fact-phrase substrings, no matter how much more of the *same kind* of data is
extracted, because the gap isn't missing data — it's a category mismatch between what static
extraction produces (names, types, signatures) and what descriptive README prose says (behavioral
explanation in the author's own words).

## This is not the same class of problem as the API-surface gap

The `api.public_surface` fix (this session, `detect_api_public_surface`) closed a real hole where
verified data existed (aspose.org's own `scout.py` extraction) but was never wired to the fact
pipeline at all. This is different: the claim-accountability gate is working exactly as designed,
correctly declining to certify prose it cannot mechanically re-derive from known facts. It is not
a bug to patch; loosening it is a genuine, safety-relevant design decision, not a quick fix.

## What aspose.org actually does differently here (per the plan/corpus research)

Aspose.org's own skill does **not** require whole-claim substring coverage against pre-extracted
phrases. Per `aspose-plan-synthesis.md`, their composing agent (an LLM session) reads the source
directly and makes a judgment call per claim, recorded in a human-legible disposition ledger
(`content-dispositions.json`: `verification.evidence_ref` pointing at the exact source file/line,
`classification`, `disposition`) — closer to "an agent verified this against source and left an
audit trail" than "this exact string is mechanically reconstructable from prior extraction."
Their skill doc's own Anti-Overclaim rules and ~92 deterministic `check_*` functions catch the
agent's mistakes *after* composition, rather than gating composition itself on mechanical
substring coverage beforehand.

## What would actually move the needle (not attempted this session — genuine design decision)

1. **Richer fact phrases, bounded to what's true.** Extracting docstrings verbatim as additional
   fact phrases (the AST extractor already reads `doc` fields — see the `api_surface.json` entries
   inspected earlier today, e.g. `"doc": "Represents a collection..."`) would close claims whose
   prose happens to echo the real docstring, without loosening the coverage requirement's actual
   guarantee. This is a real, bounded engineering task, not a design change.
2. **An aspose.org-style bounded LLM verification step**, recorded with the same rigor
   `content-dispositions.json` uses (evidence_ref, disposition, reasoning), as an explicit
   alternative acceptance path alongside (not instead of) the current mechanical one. This is the
   change that would close the *category* of gap the barcode-python example shows, not just one
   claim — but it is exactly the kind of decision the mission's own standing constraint ("LLM must
   not invent facts") means this repo should not make unilaterally during a background debugging
   session. Flagging it here as the real next design question, not attempting it.
3. **Partial-candidate delivery** (produce and surface the parts of a candidate that *are* fully
   accountable, with the specific blocking claims named and withheld, rather than an all-or-
   nothing `BLOCKED` outcome) is a smaller, more mechanical change and the one most consistent with
   this repo's existing "no unauthorized content loss, always disclose the gap" posture — but
   still changes what counts as an acceptable delivered candidate, so it belongs as a reviewed
   decision, not a silent behavior change.

## Scope of impact

Sampled blocking-claim text across the run logs: claim counts per repo range from 1
(`aspose-page-foss/Aspose.Page-FOSS-for-Python`) to 70
(`aspose-words-foss/Aspose.Words-FOSS-for-.NET`) — the smaller counts (1-4 claims) look like good
near-term candidates for option 1 above; the larger counts likely reflect either genuinely dense,
highly-narrative original READMEs, or a systemic phrase-coverage gap worth its own focused
investigation before assuming option 2 is required everywhere.
