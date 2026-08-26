# RDM-030 — API reference descriptions are name-derived and can collide across unrelated types

## Status

Root-caused with a live, direct reproduction against the real product facts.
Not repaired: the fix touches a `presentation/verified_*.py` module
(`document_templates.py::DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`/`_GLOBS`),
invalidating every repository's cached composition plan portfolio-wide --
unsafe while the `fleet-final2-20260826` portfolio pass is actively in flight.

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

## Why it was not fixed here

`verified_template_api_descriptions.py`/`verified_template_api_text.py`/
`verified_template_api_reference.py` all match
`document_templates.py::DOCUMENT_CONTRACT_IMPLEMENTATION_PATHS`'s
`presentation/verified_*.py` glob, so editing any of them invalidates every
repository's cached composition plan portfolio-wide -- unsafe mid-fleet-pass.
Choosing between the two repair directions above is also a real design
decision (prefer real Javadoc text vs. harden the synthesis fallback, or
both), not a one-line patch.
