# RDM-030 — API reference descriptions are name-derived and can collide across unrelated types

## Status

**Fixed, two independent collision mechanisms.** Mechanism 1 (empty-suffix
family-name fallback colliding with an explicit-prefix sibling, e.g.
`PdfFont`/`Font`) is fixed in `verified_template_api_text.py::role_sentence()`
and covered by a unit regression
(`test_family_fallback_no_longer_collides_with_an_explicit_prefix_sibling`).
Mechanism 2 (two genuinely distinct source classes whose names differ *only*
by letter case, e.g. `ID`/`Id` in `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`)
is a separate defect found while live-verifying mechanism 1's fix against the
real .NET repository -- the sentence-level fix did not clear that repo's
identical-looking blocker, because the collision there is not in
`role_sentence()`'s per-name suffix logic at all: both names fall through to
the fully generic fallback, and while their *rendered* text already differs
("Represents an ID..." vs "Represents an Id..."), `presentation_template.py`'s
duplicate check casefolds before comparing, so the two still collide there.
Fixed in `verified_template_api_reference.py` (see "Second collision
mechanism" below), with its own unit regression
(`test_case_only_class_name_collision_gets_distinct_descriptions`,
`tests/unit/test_verified_template_api_reference_disambiguation.py`).
Both fixes are committed (`e654a706e`) and live-verified: the "API reference
contains duplicated descriptions" error no longer reproduces against
`aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET` -- see "Live re-verification"
below.

Both fixes touch `presentation/verified_*.py` modules
(`document_templates.py::DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`/`_GLOBS`),
invalidating every repository's cached composition plan portfolio-wide --
accepted as normal per the mission's repair-once/rerun-failed-only design,
not deferred this time since both fixes are narrow, evidenced, and tested.

## Symptom

`aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` at revision
`099e70a8b309fdd6ce349607dd589dfde96f2989` fails identically across two
separate fleet runs today (`fleet-final2-20260826.log`,
`portfolio-proof-fleet-20260826.log`):

```
specialist_failed:readme_presentation:ERROR:execution_error:
ValueError: compiled verified presentation is invalid: API reference contains duplicated descriptions
```

## Root cause

Confirmed live: the Type/Description table's per-type description is
**algorithmically synthesized from the type's own name, never read from its
real Javadoc**, despite `ProductFactsV2`'s `api.public_surface` fact already
carrying distinct, real Javadoc `description` text per type (verified by
loading the real facts JSON directly -- `PdfFont`: "Abstract base class for
all PDF font types (ISO 32000-1:2008, section 9.5)."; `Font`: "Represents a
font used in PDF documents." -- two genuinely different sentences that are
never consulted). `grep` for `item.get("description")` across
`src/readme_agent/presentation/` returns nothing.

Render path: `presentation_template.py`'s duplicate check validates rows from
`api_reference_markdown()`
(`presentation/verified_template_api_reference.py`), whose `_namespace_table()`
calls `describe_api_export()`
(`presentation/verified_template_api_descriptions.py`), which for a type with
no exception/enum/function special case falls to `role_sentence(name, module,
family)` (`presentation/verified_template_api_text.py:132-146`).

`role_sentence()`'s `_ROLE_SUFFIXES` table maps a name SUFFIX to a sentence
template with a `{subject}` placeholder, filled from
`name.removesuffix(suffix)` -- or, when that strip leaves an EMPTY string, a
fallback to `public_noun(family)`. Two independent types collide when one
type's suffix-stripped prefix and another (unrelated) type's family-name
fallback both canonicalize to the same noun:

- `PdfFont`: strip `"Font"` suffix -> `"Pdf"` -> `public_noun("Pdf")` = `"PDF"`.
- `Font`: strip `"Font"` suffix -> `""` (empty) -> falls back to
  `public_noun(family)`; `family="pdf"` -> `public_noun("pdf")` = `"PDF"`.

Both resolve `subject="PDF"` by coincidence, producing the byte-identical
sentence `"Represents a PDF font through the Aspose.PDF API."` for two
unrelated real Java types. Verified directly: `role_sentence('Font',
'Enumerations', 'pdf')` and `role_sentence('PdfFont', 'Core API', 'pdf')`
both return that exact string.

A related, narrower case is already handled: `verified_template_api_text.py`
lines 114-129 fix a type whose bare name equals its own suffix (a "font font"
self-collision), but that fix does not cover this cross-type collision, where
the FAMILY name's canonicalization coincides with a DIFFERENT type's explicit
prefix.

## Correct repair direction

Two independent, compatible options: (a) prefer the real, already-collected
Javadoc `description` from `api.public_surface` over the name-derived
template whenever it exists and is non-generic, matching what the fact
already carries; and/or (b) make the empty-suffix fallback in
`role_sentence()` distinguish itself from a same-family type's explicit
prefix (e.g., include the bare type name itself in the sentence rather than
only the canonicalized family noun) so the two paths cannot coincidentally
converge on identical text.

## Mechanism 1 fix

`role_sentence()`'s empty-suffix fallback (`verified_template_api_text.py`)
changed from falling back to `public_noun(family)` (which a same-family
explicit-prefix sibling can independently derive too) to the fixed word
`"base"`, which no real prefix-derived subject can ever equal. Verified live
against `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`: this alone did **not**
clear the repository's blocker, because a second, unrelated collision was
still present (see below) -- an important reminder that a live fleet retry,
not just the direct unit reproduction, is what actually proves a fix.

## Second collision mechanism (`ID` vs `Id`, case-only)

Live re-verification against the real `aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET`
facts snapshot after mechanism 1's fix still failed with the identical error.
Rendering `api_reference_markdown()` directly against the newest facts
snapshot and grouping all 660 rendered rows by casefolded description text
found exactly one remaining duplicate group: `['ID', 'Id']`, description
`"represents an id in the public core api for aspose.pdf."`

`ID` and `Id` are two real, distinct, differently-documented .NET classes
(`ID` declares `ToPdf`/`Accept`/`ToString`; `Id` declares a constructor plus
`Original`/`Modified` properties). Neither name matches any
`_ROLE_SUFFIXES` entry, so both fall through to `role_sentence()`'s fully
generic bottom fallback. Their *rendered* sentences already differ ("Represents
an ID..." vs "Represents an Id...") -- `public_noun()`/
`canonicalize_abbreviations()` were **not** the cause here, unlike the initial
hypothesis; that canonicalization is deliberately case-insensitive for
abbreviation casing consistency and is correct, shared logic used throughout
visitor-facing text. The actual cause is
`presentation_template.py`'s duplicate-descriptions check (`descriptions = [...
.casefold() for ...]`), which treats the two rows as identical once casefolded.

Fixed at the rendering layer, not in `role_sentence()` itself (which has no
visibility into sibling types to know a collision is even happening):
`verified_template_api_reference.py` now assembles every namespace's rows
before final markdown rendering, and `_disambiguate_duplicate_descriptions()`
detects any group of rows that still collide after casefolding and appends
each colliding row's own distinguishing (non-inherited, self-declared) member
names -- real, meaningful, casefold-safe content, e.g. `"... Declares
`ToPdf`, `Accept`."` vs `"... Declares `Original`, `Modified`."` A second pass
appends a plain ordinal tag to any group that (in some far more contrived case)
would still collide after the member-name pass, guaranteeing the invariant
holds regardless of edge cases. Only rows that actually collide are touched;
verified the full 660-row .NET reference now renders 660 unique descriptions.

## Live re-verification (2026-08-27, both fixes committed)

`readme-agent portfolio-proof --mode fleet --retry-blocked --only
"aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET"` against commit `e654a706e`
(both fixes landed) no longer reproduces the "API reference contains
duplicated descriptions" error anywhere in its blocking reasons. The
repository now advances past presentation compilation entirely into the
`presentation_plan` review stage, where it hits a different, later,
unrelated set of findings (13 claim-accountability blocks,
`code_fence_spacing`, ten `format_direction_contradiction` findings for PDF
input role / JSON output role, one `claim_grounding_negative_fact`) --
confirming the fix, not just plausibly explaining the symptom. Those new
findings are a separate defect, not yet investigated here.

## Why mechanism 1's fix alone was not sufficient, and why both are now fixed together

Both defects independently match `document_templates.py`'s
`presentation/verified_*.py` glob, so both were deferred together in the
initial write-up above. Once mechanism 1 was implemented and *live-verified*
(not just unit-tested) against the real blocking repository, the residual
failure surfaced mechanism 2 directly -- so both are fixed and tested in the
same pass rather than incurring a second portfolio-wide cache invalidation
later.
