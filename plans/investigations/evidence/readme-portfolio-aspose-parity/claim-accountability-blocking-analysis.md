# Claim-accountability blocking: why 11/33 portfolio repos block, and what would actually close it

Investigated 2026-08-17 while GitHub's API outage blocked live portfolio verification (a
GitHub-independent investigation: uses only local clone caches under `runs/baseline/` and
`runs/readme-poc/` already on disk).

**Update 2026-08-18: option 2 below (the bounded LLM-verification alternative acceptance path) is
now implemented, tested, and hygiene-clean — explicitly authorized by the operator ("at aspose.org
nothing is blocked... I am assuming you would solve all problems as well").** See "Implementation
status, 2026-08-18" near the end of this document for exactly what exists, what's proven, and what
remains before it closes a single real portfolio repo's blocking claims.

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

## A second, distinct example: an entirely missing fact *type*, not missing phrases

Investigated `aspose-page-foss/Aspose.Page-FOSS-for-Python`'s single blocking claim (the smallest
blocking-claim count in the portfolio, a good candidate to check whether it's cheaply closeable):
*"No required third-party package dependencies."* Traced the same way — this claim asserts an
**absence** (zero required deps), but every dependency-related fact this repo's pipeline produces
(`curated_python_dependencies.py::python_capability_dependencies`, and the T4 `aspose.
capability_dependencies` field) only ever lists *optional* distributions actually found via import
scanning; nothing anywhere computes and asserts "the manifest's required-dependencies list was
checked and is empty." `visitor_fact_render_view` returns `None` for both dependency-related
fields on this repo — no phrase-rendering view is registered for either at all, so even if the
absence fact existed, wiring would still be needed.

This is a third, distinct kind of gap from the other two documented here: not "verified data
exists but isn't wired" (`api.public_surface`'s fix), not "the claim's own descriptive prose can
never be mechanically reconstructed" (the `generate()` example above) — this is a genuinely
**missing fact type**: nothing in this codebase currently represents "we checked the manifest and
confirmed zero required runtime dependencies" as a fact at all.

Checked how common this exact sentence is across the portfolio before treating it as a one-off:
`grep -rl "No required third-party package dependencies" runs/readme-poc/*/*/source/README.md`
finds it verbatim in **6 repos' cached source READMEs** (`email/net`, `email/cpp`, `email/python`,
`font/python`, `note/python`, `page/python`) — a real, recurring pattern, not specific to one
product. A bounded new detector (parse `pyproject.toml`'s `dependencies`/`[tool.poetry.
dependencies]` or the equivalent per-ecosystem manifest field, assert emptiness, wire a phrase
view) would plausibly help multiple repos at once.

**Deliberately not implemented this session.** It's a real, well-scoped, safely-testable addition
(new detector + fact field + phrase view + unit tests, all exercisable without GitHub, the same
pattern as today's `detect_api_public_surface` fix) — but it's still new fact-schema surface, and
shipping it without a chance to verify it against the full real pipeline before this session likely
ends (GitHub's outage blocks that) risks exactly the kind of half-verified change this project's
own conventions and today's `--bounded-verified-canary` rule exist to prevent. Recorded here as a
concretely scoped next task, not attempted blind.

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

## Addendum: the *other* blocker category (`BLOCKED_MISSING_EVIDENCE`, 15/33 repos) is different

Investigated the same session, same GitHub-independent method. Traced `classify_product_truth`
(`facts/acceptance_contract.py:314-355`) directly against a real blocked repo
(`aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, local clone cache): six of the sixteen
`REQUIRED_PRODUCT_FIELDS` come back `verification_state=missing` — `product.audience`,
`product.problems_solved`, `product.capabilities`, `product.formats`, `example.minimal`,
`product.limitations`. These are the fields that need product-level interpretation, not manifest
parsing (install coordinates, license, platforms all resolve fine for the same repo).

**This is not a structural per-language gap like `api.public_surface` was.** A real, existing,
already-registered capability already exists to produce exactly these fields for any ecosystem:
`capabilities/draft_product_truth.py` (`RPOC-033`) — an LLM-assisted drafting-plus-gating loop,
explicitly designed to be ecosystem-general (`facts/local_verification.py`'s "real per-ecosystem
verifier" for `example.minimal`, not a Python-only path). `missing` (not `blocked` or
`unverified`) is the state a field has *before this capability has ever run for it*, not after it
tried and failed.

The most likely explanation for why 15 non-Python repos show `missing` here while the 4 Python
repos that reached `AGENT_APPROVED` don't: those Python repos already have a persisted,
previously-drafted `product_truth` from earlier work in this project's history (Python was worked
first, per the plan-synthesis's own account of this project's history), while the non-Python repos
simply haven't been advanced through this drafting stage yet. Confirming this precisely would
require actually running the capability against one of them — which, like the `--bounded-verified-
canary` path itself, goes through the supervisor and fails closed on the same GitHub preflight
check currently blocked by today's outage. Not attempted as a workaround (would violate the
verification-workflow rule added today, AGENTS.md rule 15) — flagged as the first thing to try
once GitHub recovers, ahead of any new code: a clean, full-time-budget portfolio run may close a
meaningful fraction of this category on its own, with zero new engineering.

## Scope of impact

Sampled blocking-claim text across the run logs: claim counts per repo range from 1
(`aspose-page-foss/Aspose.Page-FOSS-for-Python`) to 70
(`aspose-words-foss/Aspose.Words-FOSS-for-.NET`) — the smaller counts (1-4 claims) look like good
near-term candidates for option 1 above; the larger counts likely reflect either genuinely dense,
highly-narrative original READMEs, or a systemic phrase-coverage gap worth its own focused
investigation before assuming option 2 is required everywhere.

## Implementation status, 2026-08-18

Built after direct study of the real aspose.org mechanism this document's own "What aspose.org
actually does differently" section pointed at:
`D:\onedrive\...\aspose.org\reports\repo-presenter\barcode\python\content-dispositions.json` — the
real, live disposition ledger for the exact repo/blocking-claim example above. Reading it directly
corrected the earlier assumption that aspose.org's LLM independently judges each old-README unit
against raw facts; it actually reconciles each unit against the **already-composed candidate text**
(and, for genuinely new details, real repository source) — `unit_id: u0009` there is the literal
counterpart of this repo's blocking `generate()` claim, classified `redundant_with_existing`
because the candidate's own Key Capabilities prose already said the same thing in different words.

**What exists now (option 2, complete and unit-tested):**
- `prompts/verification/claim_disposition_check.yaml` — new governed prompt, forced tool call
  (`report_claim_disposition`), four-way classification (`redundant_with_candidate` /
  `verified_against_source` / `narrative_filler` / `unverifiable`).
- `src/readme_agent/llm/claim_disposition_prompts.py` — tool schema + message builder.
- `src/readme_agent/verification/claim_disposition.py` — the corroboration layer, mirroring
  `verification/prose_quality.py`'s exact "additive, never trusted at face value" shape: a
  `redundant_with_candidate` verdict is only accepted if its quoted evidence is found verbatim in
  the real candidate text; a `verified_against_source` verdict only if the cited file genuinely
  exists inside the repository clone (path-escape-checked) and the quoted evidence is found
  verbatim in that file's real content; anything uncorroborated is downgraded to `unverifiable`
  before it can affect anything.
- `src/readme_agent/readme/claim_accountability_llm_disposition.py` — the real entry point/owner,
  constructs the live client the same way `capabilities/verify_prose_quality.py` does.
- `readme/claim_accountability_models.py` — new `"llm_verified_disposition"`
  `ExpectedClaimDisposition` value and `ClaimDispositionRecordV1` (mirrors
  `content-dispositions.json`'s own shape: classification, evidence_type, evidence_ref,
  evidence_quote, reasoning, corroborated).
- `readme/claim_accountability_helpers.py::expected_disposition()` — one new, low-priority
  fallback branch (`llm_disposition_corroborated: bool = False`), tried only after every existing
  mechanical path (fact-variant coverage, structured coordinates, candidate-policy shells,
  configured standards) has already failed — never loosens or bypasses any of them.
- `readme/claim_accountability.py::build_readme_claim_accountability_map()` — two new optional
  parameters, `llm_disposition_client`/`repository_root`. Omitting either (the default) reproduces
  today's exact existing behavior byte-for-byte; every existing caller in the codebase does not
  pass them, so **this is currently 100% inert in the live pipeline** (see "Not yet done" below).

**Proven, not assumed:** `tests/unit/test_claim_accountability_llm_disposition.py` builds a claim
structurally identical in kind to the real barcode-python `generate()` example (a "canonical or
alias... generic entry point" sentence no mechanical binder can cover) through the real
`build_readme_claim_accountability_map()` and shows all three required properties hold: (1) without
a client, the claim stays blocking (`currently_accountable=False`) — unchanged from today; (2) with
a client returning a corroborated verdict, the same claim becomes accountable
(`expected_disposition == "llm_verified_disposition"`); (3) with a client returning an
**uncorroborated** verdict (a hallucinated quote that never appears in the candidate), the claim
stays blocking regardless — the safety property that makes this an additive fallback, not a
loosening. `tests/unit/test_verification_claim_disposition.py` covers the corroboration layer
directly (redundant/verified/filler/unverifiable, plus a path-traversal-escape rejection test).
Full unit suite confirmed identical to the pre-existing baseline afterward — zero regressions.

**Not yet done (deliberately, explicit next step, not attempted blind):**
1. No caller in the live candidate-rendering pipeline (`document_renderer.py`,
   `presentation/verified_template_document.py`, `readme/document_plan_finalizer.py`,
   `supervisor/loop.py`) constructs and passes a real `llm_disposition_client`/`repository_root`
   yet. Doing so is a real behavior/cost change (every future candidate build could attempt one
   more LLM call per still-unaccounted claim) that deserves its own deliberate activation, not a
   silent default flipped mid-implementation.
2. No `review/claim-dispositions.json` evidence artifact is written yet (the disposition ledger,
   mirroring aspose.org's `content-dispositions.json` file-per-repo convention) — needed once this
   is live, both for audit and so `claim_accountability_validation.py`'s independent validator can
   re-corroborate (not re-judge) each accepted verdict against the *current* candidate/source
   before trusting it, the same "who verifies the verifier" pattern this module itself already
   applies once, at construction time.
3. Not yet run against a real portfolio repo end-to-end (would require step 1). The barcode-python
   `generate()`/pytest-dependency claims documented above are the natural first live proof once
   step 1 lands — they're the exact motivating example, already traced start to finish here.
