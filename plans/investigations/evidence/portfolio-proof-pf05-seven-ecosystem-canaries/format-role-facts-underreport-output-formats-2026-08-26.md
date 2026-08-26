# PF05-FORMAT-ROLE-001 — Accepted format roles under-report implemented output formats

## Status

Root-caused, **not** repaired. A presentation-layer repair was written, measured
against the real repositories, found to be wrong, and reverted before it shipped
any candidate. The real defect is in fact extraction, which is contract-bound, so
it is recorded here rather than changed mid-portfolio-run.

## Symptom

Three Python candidates fail deterministic validation on
`presentation.format_direction_contradiction`:

- `aspose-3d-foss/Aspose.3D-FOSS-for-Python` — "do not authorize output role for
  OBJ / PDF / COLLADA / FBX", "do not authorize input role for FBX"
- `aspose-note-foss/Aspose.Note-FOSS-for-Python` — "do not authorize output role
  for PDF" (four occurrences)
- `aspose-page-foss/Aspose.Page-FOSS-for-Python` — "do not authorize input role
  for XPS", "do not authorize output role for PDF / JPG"

All three pass independent review with `ACCEPT`. Only the deterministic gate
rejects them.

## What the facts say

`explicit_format_roles(facts)` returns, measured 2026-08-26:

| repository | authorized roles |
| --- | --- |
| 3D Python | `OBJ: input`, `GLTF: input+output`, `STL: input+output`, `3MF: input+output` |
| Note Python | `ONE: input`, `ONENOTE: input` |

Note's `product.formats` is literally `['Input format: Microsoft OneNote (.one)']`
— it records **no output format at all**.

## What the repositories actually implement

This is the decisive measurement, taken against the cloned baselines rather than
against the facts:

`aspose-note-foss/Aspose.Note-FOSS-for-Python`

```
examples/export_pdf.py            doc.Save("out.pdf", SaveFormat.Pdf)
tests/test_aspose_note_compat_smoke.py    self.assertTrue(data.startswith(b"%PDF"))
tests/test_aspose_note_pdf_goldens.py     PDF golden-file comparison
tests/test_aspose_note_save_options.py    self.assertEqual(list(SaveFormat), [SaveFormat.Pdf])
```

PDF is not merely present — it is the **only** member of `SaveFormat`, it has a
worked example, and its output is asserted byte-wise (`%PDF`) and against golden
files. PDF export is the package's single output capability.

`aspose-3d-foss/Aspose.3D-FOSS-for-Python`

```
tests/test_collada_exporter.py            options.file_name = 'test.dae'
aspose/threed/formats/ColladaSaveOptions.py   "Save options for collada"
aspose/threed/formats/fbx/tokenizer.py    FbxTokenizer
tests/test_plugin_system.py               io_service.get_plugin_for_extension('.fbx')
```

COLLADA export has a dedicated exporter test and a save-options type.

**So the candidates are right and the accepted facts are wrong.** These are not
over-claims inherited from the commercial product; they are working, tested
capabilities that `product.formats` fails to record.

## The repair that was tried and reverted

`knowledge_claim_presentation._format_markdown()` was changed to withhold any
imported-knowledge format row whose direction `explicit_format_roles()` does not
authorize, gating on `unsupported_format_directions()` — the same predicate the
lint uses, so producer and check could not disagree.

It made the lint finding disappear, and it is the wrong fix. The reasoning behind
it — "imported knowledge describes the commercial product, so a documented
direction is not evidence this FOSS build implements it" — is sound in general
and false for these three repositories. Applying it would have deleted Note's
only output capability from Note's README while the repository ships a worked
example and golden tests for exactly that capability. That directly violates the
working-condition presentation rule: show verified-working functionality, hide
only the unverifiable.

Reverted in the same session it was written, before any candidate was published
with it. The commit's unrelated half — repairing a stale action-verb assertion —
is independently correct and was kept.

## The actual defect

`product.formats` fact extraction derives format roles from a narrower evidence
set than the repository's verified example and test surface. A format that
appears only as a `SaveFormat` enum member, a `*SaveOptions` type, or an executed
example's output path is not being promoted to an accepted output role.

Both consumers are then wrong together, which is why this looked like a
presentation bug: the candidate row is correct, and
`presentation_lint_format_directions` reports a contradiction that does not exist
in the repository — only in the facts.

## Why it was not fixed here

`format_vocabulary.py` and the `product.formats` collectors are inside the fact
contract (`verification_contract._COMMON_FILES` / `acceptance_contract`). Editing
them changes `local_verification_contract_hash()` for every ecosystem at once and
re-stales every cached fact bundle portfolio-wide (RC1), which is the documented
reason this project has repeatedly invalidated its own output faster than it
produced it. That repair belongs in a deliberate shared-repair slot with a full
re-run behind it, not in the middle of one.

## Correct repair direction

Promote a format to an accepted output role when the repository itself proves the
direction, using evidence the pipeline already collects:

1. a `SaveFormat`/`FileFormat` enum member naming the format,
2. a `*SaveOptions` / `*Exporter` public type for it, or
3. a verified example whose executed output is that format.

Evidence (3) is the strongest and is already gathered for example verification.
Until then these three repositories cannot pass the deterministic gate, and the
candidates — not the facts — are the accurate artifact.
