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
