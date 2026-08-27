# RDM-029 — compose stage drops vendor-README boilerplate without authoring a resolution

## Status

Fixed (commit `16faa1358`) once the `fleet-final2-20260826.log` portfolio pass
had finished and the document-contract cache-invalidation cost was safe to
pay. Live-verified against `aspose-cells-foss/Aspose.Cells-FOSS-for-Go`, one
of the six originally-affected repositories: blocking source claims dropped
from 7 to 4 on a fresh, fully-reprocessed run
(`runs/logs/rdm029-verify-cells-go-20260826.log`) -- a real, measured, partial
improvement, not full resolution. The repository remains blocked on
*separate* issues the fix does not address: the LLM-composed candidate's own
freely-generated prose still independently asserts unsupported CSV/ZIP/XML
format claims (not carried over from dropped source spans -- a content-
generation quality issue, not a source-claim-resolution gap), plus unrelated
`code_fence_spacing`/`semantic_duplicate`/`claim_grounding_negative_fact`
findings. Confirms the fix works exactly as designed for its actual scope
(dropped, unresolved *source* claims) without overclaiming it as a full
unblock for any given repository.

## Root-cause writeup (superseded by the fix above; retained for context)

Root-caused via targeted investigation of the fleet run's most repeated blocker
signature. The fix touches `claim_accountability_helpers.py`/
`document_validation.py`, both matched by `document_templates.py`'s
`DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`, which invalidates every cached
composition plan portfolio-wide -- unsafe to edit while the `fleet-final2-
20260826.log` portfolio pass was actively in flight. Also a genuinely sized
design task (why resolution-authoring omits specific dropped spans), not a
one-line patch.

## Symptom

`local_poc portfolio` fleet pass, 2026-08-26: repeated across at least six
repositories in at least three ecosystems (Python: aspose-page-foss,
aspose-pdf-foss; .NET: aspose-pdf-foss, aspose-cells-foss, aspose-slides-foss,
aspose-words-foss):

```
specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:
['claim accountability has N blocking claim(s): source:claim:<id>:<hash>, ...']
```

`escalation_alert` confirms these are not transient: the same repos show
`'readme_presentation' has failed <4 to 30> consecutive runs for the same
reason ('presentation_plan')` -- no self-healing across repeated fleet passes.

## Root cause

`validate_claim_accountability_map()`
(`readme/claim_accountability_validation.py:444-453`, surfaced via
`document_validation.py:576-581`) marks every source/candidate claim
`currently_accountable=False` ("blocking") unless it is backed by an accepted
fact, a configured standard, an explicit `SourceClaimResolutionV1`, or an
LLM-corroborated disposition (`claim_accountability_helpers.py::
expected_disposition()`, lines 98-314). This gate is working exactly as
fail-closed design intends.

Of the 18 blocking-claim IDs observed across the affected repos, 16 are
`source:claim:*` (only 2 are `candidate:claim:*`) -- almost all inherited
claims from each vendor's original README that the compose stage silently
dropped from the FOSS candidate without ever authoring the required
`unjustified_loss`-avoiding resolution (`stage=="source" and
survives_in_candidate is False`, no resolution recorded ->
`claim_accountability_helpers.py:232-247`). Consistent with this, the same
blocked log lines almost always co-occur with
`presentation.format_direction_contradiction` findings ("Accepted product
facts do not authorize output role for PDF/CGM/JPEG/PNG/..."): every
commercial Aspose vendor README describes input/output formats the specific
FOSS edition does not actually support (per that repo's own `product_facts_v2`).
The planner correctly removes that unsupported boilerplate from the candidate,
but for a recurring subset of the removed sentences it never authors the
`verified_omission`/`presentation_policy_correction` resolution the
accountability gate requires to accept the drop as intentional -- a coverage
gap in the composition/resolution-authoring step, not a defect in the gate
that catches it.

## Why no auto-repair

`readme_presentation.py:754-813`: when `presentation_plan["executable"]` is
False (which is where `claim_accountability_complete` lives), the specialist
returns immediately with `ERROR:presentation_plan:blocked:...`. The in-run
repair loop (`repair_attempts`/`_dispatch_regenerate`, lines 973-1021) only
fires for a downstream `prose_quality` flag -- never for a claim-accountability
failure -- so a repo stuck here does not self-heal on a later fleet pass either;
`consecutive_failure_count` persists cross-run in `state/domain_state.py` and
was observed as high as 30 for one repository.

## Correct repair direction

The compose/resolution-authoring stage needs to reliably author a
`verified_omission` (or `presentation_policy_correction`) resolution for every
source claim it drops specifically because that claim describes a format/role
the accepted product facts do not authorize -- not just some of them. That
likely means the resolution-authoring pass needs to check dropped-claim text
against the same `format_direction_contradiction` signal the downstream
presentation lint already computes, rather than relying on the composing LLM
turn to remember to author a resolution for every such drop on its own.

## Precise remaining scope, found via live re-check on `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET` (2026-08-27)

Commit `16faa1358` implemented the format-direction slice of the repair above
in `presentation/verified_source_policy.py::build_verified_source_policy_edits()`,
reusing `directional_fragments()`/`unsupported_format_directions()`. Live
re-verification of `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET` after that fix
(and after the unrelated RDM-030 fix, `runs/logs/rdm030-verify-pdf-net-20260827b.log`)
still shows 13 blocking claims, confirming the fix's own PARTIAL status. A
dedicated read-only investigation of the live source (`runs/readme-poc/
aspose-pdf-foss__Aspose.PDF-FOSS-for-.NET/663783d18ec1c00efbd9b56a0a6ea20e4671d92b/
source/README.md`) against the previewed 10 blocking claim IDs found two
distinct, precise scope gaps in the existing fix, not a new mechanism:

1. **Fenced code is categorically excluded from every edit path in
   `verified_source_policy.py`, including the RDM-029 generator.**
   `build_verified_source_policy_edits()` gates every candidate edit through
   `_visitor_visible()` (lines 56-59), which skips any span overlapping a
   ```` ``` ```` fence -- correctly, since the source-policy editor must never
   silently rewrite a protected code example. But this means a fenced example
   demonstrating an unauthorized format direction (e.g. a ```csharp block
   calling `Document.Open("input.pdf")` to demonstrate signing/extraction/
   annotation/rendering, when this FOSS edition's accepted facts do not
   authorize PDF as an input format) never gets *any* accountability path --
   not a rewritten edit (correctly), but also not the `verified_omission`
   resolution that would let the accountability gate accept its correct
   absence from the candidate. 8 of the 10 previewed blocking claim IDs for
   this repository are exactly this: fenced ```csharp examples, each
   co-occurring with a `presentation.format_direction_contradiction` finding
   for the same format role. The fix needed is not to relax `_visitor_visible`
   (which would let policy edits rewrite protected code), but to add a
   *resolution-authoring* path -- alongside the existing narrow functions in
   `presentation/verified_source_claim_omissions.py`
   (`deferred_withheld_source_resolution`, `deferred_unverified_obligation_
   detail_resolution`, `deferred_unverified_source_example_resolution`,
   `verified_paired_example_intro_resolution`, `governed_source_omission`) --
   that recognizes a claim is a fenced example whose format direction the
   accepted facts do not authorize, and records a `verified_omission`/
   `presentation_policy_correction` `SourceClaimResolutionV1` for it without
   touching the fence's text.
2. **Non-format-direction claim drops are untouched by the existing fix at
   all.** 2 of the 10 previewed IDs are plain dependency prose ("No optional
   third-party package dependencies." / "No development-only third-party
   package dependencies…") with no connection to format direction --
   confirming the coverage gap is broader than the one sub-case RDM-029's fix
   addresses. Not yet investigated further; may need its own resolution
   function or may share a root cause with another already-fixed category
   (`governed_source_omission`'s pattern-matching is the closest existing
   analog but does not currently match this prose).

Both gaps are additive, narrowly scoped (new resolution-authoring functions,
not edits to the accountability gate itself), but represent real, sized
design work -- consistent with keeping this requirement's status `PARTIAL`
rather than closing it. `claim_accountability_validation.py` and
`document_validation.py` (the gate) were NOT touched and do not need to be;
only the resolution-authoring side (`presentation/verified_*.py`,
`readme/claim_*.py` -- both contract-bound globs) would need new code.

## Precise mechanism for gap 1's fenced examples, traced live (2026-08-27)

Traced all 10 of `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`'s previewed
blocking claims through `assess_material_claims()` +
`classify_source_claim_risk()` against the real vendor source text. All 10
share `risk_class="mandatory_fact_resolution"`; 2 (offsets 6918, 7090) have
`obligation_id="dependency_requirements"` (gap 2's plain prose); 8 (offsets
7995, 8366, 8643, 8893, 9215, 10180, 10332, 10544) have
`obligation_id="additional_examples"` -- confirming gap 1's fenced ```csharp
examples are ALL under this one obligation, not `primary_example`.

`resolve_source_claims()` (`verified_source_claim_resolution_engine.py`)
handles `obligation_id == "primary_example"` specially (lines 292-310, calls
`deferred_unverified_source_example_resolution()`), but has **no equivalent
branch for `"additional_examples"`** -- it falls through to the generic
`accepted_obligation_bindings("additional_examples", ...)` check (line
356-372), which is `None` for this repository (no independently-accepted
`additional_examples` obligation exists), then to
`deferred_unverified_obligation_detail_resolution()` (line 396), which
**immediately returns `None`** because `"additional_examples"` is not in its
hardcoded allowed-obligation set (`api_public_surface`, `major_capabilities`,
`product_overview`, `development_commands` only -- confirmed by reading
`verified_source_claim_omissions.py`). With no other applicable branch, the
claim falls to `_raise_unresolved_preserve(preserve_required and
fail_on_unresolved_preserve, claim.claim_id)` with `preserve_required=False`
(a deliberate no-op, not a raise) and the loop `continue`s -- silently
producing **zero** `SourceClaimResolutionV1` for the claim. This is the exact
mechanism, confirmed by direct trace, not inference.

**Naively extending the allowed-obligation set does not work**: even if
`"additional_examples"` were added to
`deferred_unverified_obligation_detail_resolution()`'s allowed set, its
first guard requires `candidate_core_present` (derived from the SAME
`accepted_obligation_bindings("additional_examples", ...)` call that is
already known to return `None` here) -- so it would still return `None` for
exactly the failing case. A working fix needs the same *per-example*
verification rigor `deferred_unverified_source_example_resolution()` already
applies for `primary_example` (does this exact example have a recorded
static/execution verification decision? is its literal input fixture
provably absent from the tree?), not a category-level "is some other example
already accepted" check.

**Confirmed additional scope**: `deferred_unverified_source_example_resolution()`
is Python-fence-specific by construction --
`_python_fence_content()` explicitly rejects any fence whose language tag is
not `py`/`python` (`_python_fence_content('```csharp\n...\n```')` returns
`None`, confirmed live). Generalizing this to cover the real failing case
(.NET/C#) requires handling that ecosystem's fence language and its
verification-fact shape too, not just relaxing the `obligation_id` gate --
likely true for every other ecosystem's `additional_examples` claims as
well. This is real, multi-ecosystem feature work, not a one-line patch;
attempting a rushed version risks a worse failure mode than the current
crash-closed behavior -- silently misclassifying a genuine example as safe
to omit. Not attempted in this pass.

**Precise gap location (traced 2026-08-26, deeper than the original writeup
above):** `presentation/verified_source_policy.py::build_verified_source_policy_edits()`
is the ONLY deterministic generator of `VerifiedSourcePolicyEditV1` spans, which
flow through `presentation/verified_source_policy_application.py::
apply_verified_source_policy()` into `SourceClaimPolicyCorrectionV1` corrections,
which `presentation/verified_source_policy_resolution.py::source_policy_resolution()`
turns into the `SourceClaimResolutionV1` the accountability gate requires --
but `source_policy_resolution()` returns `None` (no resolution) whenever no
correction overlaps the claim's byte span (line 118-119: `if not owned: return
None`). `build_verified_source_policy_edits()` currently only generates edits
for four span kinds: shell-policy boilerplate (`source_shell_policy_spans()`),
Aspose link occurrences, enterprise-edition terminology, and
`public_text_corrections()`. **None of these detect an unsupported
format/role claim** -- there is no fifth generator that scans the source text
for format/role mentions the accepted `ProductFactsV2` doesn't authorize (the
same detection `presentation_lint_structure.py`'s
`format_direction_contradiction` check already performs, just reactively,
after the candidate is built). The fix is additive: a new edit-generator
function in `verified_source_policy.py`, added to the `edits` list inside
`build_verified_source_policy_edits()` alongside the other four, reusing the
existing format/role detection logic rather than reimplementing it. All three
files in this chain (`verified_source_policy.py`,
`verified_source_policy_application.py`, `verified_source_policy_resolution.py`)
match `document_templates.py`'s `presentation/verified_*.py` glob, confirming
the contract-boundedness finding below applies to the whole chain, not only
the entry point.

## Why it was not fixed here

Both files this touches
(`readme/claim_accountability_helpers.py`, `readme/document_validation.py`)
are listed in `document_templates.py::DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`,
so editing either invalidates every repository's cached composition plan
portfolio-wide -- unsafe mid-fleet-pass, per this repo's own established
contract-boundedness discipline. The fix also requires deciding exactly how
resolution-authoring should detect "this drop is a format/role boilerplate
removal" reliably across ecosystems, which is a real design question, not a
mechanical patch.

## A third obligation, and a hint the real root cause is shared and upstream (2026-08-27)

`aspose-font-foss/Aspose.Font-FOSS-for-Python` has the highest recorded
`escalation_alert` streak of any repository in the portfolio (33-34
consecutive `presentation_plan` failures across every fleet pass run this
session) -- the single most persistently-stuck repository, worth tracing
directly. Its one blocking claim (`source:claim:470:...`) traces to a THIRD
obligation: `risk_class="mandatory_fact_resolution"`,
`obligation_id="major_capabilities"` -- a source capability table, not a
fenced example (gap 1) or dependency prose (gap 2).

Unlike gaps 1 and 2, `"major_capabilities"` **is** in
`deferred_unverified_obligation_detail_resolution()`'s allowed-obligation
set, and its capability-specific guard
(`_capability_anchor_matches(claim_text, facts)`) was tested directly
against this claim's real text and the real `product.capabilities` fact
(`['Font format conversion', 'Web font bundle generation', 'Delta inspection
for variable fonts']`) -- **it returns `True`**. That guard is not what is
blocking this claim.

By elimination, the actual blocker must be
`candidate_core_present` -- i.e. `accepted_obligation_bindings
("major_capabilities", facts, candidate_content_provenance)` returning
`None` for the live run, the exact same upstream condition already
identified as the root of gap 1 (`accepted_obligation_bindings
("additional_examples", ...)` also returns `None` there). This raises a
real possibility that gaps 1, 2, and this third case are not three
independent per-obligation gaps at all, but symptoms of **one shared
upstream problem**: `candidate_content_provenance` not carrying a binding
with the right `obligation_provenance_prefixes()`-matching `provenance_id`
for whatever obligation a given dropped claim needs, regardless of which
obligation it is. If true, the highest-leverage fix would be in how
provenance gets recorded during composition (or how it's threaded into
`resolve_source_claims()`), not three separate new
per-obligation resolution functions.

**Not confirmed**: this is a hypothesis from two data points (gap 1's fenced
examples and this major_capabilities case), not a full trace of
`accepted_obligation_bindings()`'s actual runtime inputs for a live run --
that would need instrumenting the real composition pipeline
(`candidate_content_provenance` is intermediate, in-memory pipeline state,
not a persisted artifact this investigation had static access to). Worth
prioritizing over gap 1/2's per-obligation framing if picked up next: trace
whether `candidate_content_provenance` for a live blocked run actually
contains ANY `major_capabilities`- or `additional_examples`-prefixed
bindings at all, before assuming a per-obligation fix is even the right
shape.
