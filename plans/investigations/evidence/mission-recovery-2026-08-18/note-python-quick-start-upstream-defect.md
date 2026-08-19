# note-python's real Quick Start example has a genuine upstream defect

Found live during Lane E's canary (`mission-recovery/lane-e-targeted-example-verification`,
merged `f5446bbed`), while proving out the targeted runtime-verification mechanism
(`curated_python_evidence._runtime_verify_quick_start_examples`) against a real clone of
note-python and the real `testfiles/SimpleTable.one` fixture.

## What was tested

The blocking claim `source:claim:...:0d4d28fef68b38fd`'s exact quoted code, copied
character-for-character from note-python's real README:

```python
from aspose.note import Document

doc = Document("SimpleTable.one")
print(doc.DisplayName)
for page in doc:
    print(page.Title.TitleText.Text)
```

## What happened

`doc = Document("SimpleTable.one")` and `print(doc.DisplayName)` execute correctly against the
real fixture (prints `SimpleTable`) — the fixture-staging fix (Lane C, `8611c15c5`) works as
intended. The loop crashes:

```
AttributeError: 'NoneType' object has no attribute 'TitleText'
```

`page.Title` is `None` for at least one page produced by iterating `doc` over the real
`testfiles/SimpleTable.one` fixture. This is not a bug in this repository's pipeline — a guarded
variant (`if page.Title is not None:`) against the identical fixture passed with
`SOURCE_BUILD_VERIFIED`/`truth_eligible=True`, proving the verification machinery itself is
correct. The defect is in the README's own advertised example: it doesn't handle a real,
observable `None` case that the documented workflow (`for page in doc: print(page.Title.TitleText.Text)`)
does not guard against.

## Consequence for this repository's pipeline

Because `_runtime_verify_quick_start_examples` only promotes an example on a genuine successful
proof, it correctly refused to promote this exact block — this is fail-closed working as
designed, not a gap. Claim `0d4d28fef68b38fd` remains legitimately unaccounted for until either:
- note-python's upstream README is corrected (out of scope — no target-repository writes during
  this mission), or
- a differently-scoped resolution accepts the claim's assertion (that the example exists and
  demonstrates opening `SimpleTable.one`) without requiring the exact crashing loop body to
  verify byte-for-byte — a disposition-layer question, not a rendering one, and out of scope for
  this finding.

## Where this belongs going forward

This is exactly the kind of finding `runs/share/poc/<org_repo>/UPSTREAM-DEFECTS.md` is designed
to record (see the working-condition-presentation convention) — but that file is a generated
pipeline artifact, produced by an actual `readme-agent poc` run against note-python, not
something to hand-author. This document preserves the finding in the durable evidence trail
until/unless a future poc run against note-python regenerates and captures it there natively.
