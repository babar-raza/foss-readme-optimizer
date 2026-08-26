# PF05-BARCODE-CONFLICT-001 — accepted capability and limitation facts directly contradict each other

## Status

Root-caused with source-level verification. Not repaired: the fix belongs in
fact conflict resolution, which is contract-bound, and determining which claim
is true required reading the real encoder source, not a quick presentation-layer
patch.

## Symptom

`aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` fails
`public_quality.contradiction_capability_phrase` (3 findings, all blocking).

## The two facts

```
product.capabilities: "Code 128 generation with automatic optimal Code Set switching."
product.limitations:  "GS1, ECI, bytes / binary input, FNC handling, Code Set A/C,
                        Shift, and code-set switching are unsupported."
                        (source: bootstrap.py:84, _build_code128_known_limitations())
```

Both are independently accepted, verified facts. They are a direct contradiction:
one says Code Set switching is automatic and optimal; the other says code-set
switching -- explicitly including "Code Set A/C" and "Shift" -- is unsupported.

## Ground truth, verified against the real encoder

`src/aspose_barcode_foss/_internal/encoders/code128.py` implements exactly what
the limitation claims is missing:

```
line 260  Build a Code Set A/B inter-set switching codeword plan ... Uses SHIFT
line 319  Build a Code Set A/C inter-set switching codeword plan
line 377  Build a Code Set B/C inter-set switching codeword plan
line 434  Combines A<->B switching (with SHIFT) and Code Set C transitions
line 480  Check for a digit run that warrants switching to Code Set C
```

Code Set A/B/C inter-set switching, including SHIFT, is fully implemented. The
capability claim is true and source-verified.

`bootstrap.py::_build_code128_known_limitations()` returns the limitation as a
**hardcoded string literal**, not something derived by inspecting the encoder.
It is stale: it describes a limitation the repository no longer has.

## Why this was not fixed here

Resolving it correctly requires the fact-conflict layer to prefer the
source-code-verified capability over the unverified hardcoded limitation string
for this specific overlap, which touches fact extraction/conflict resolution --
contract-bound (re-stales every cached fact bundle portfolio-wide).

Weakening `public_quality_contradiction_checks.py` instead (not contract-bound)
was considered and rejected: the check is correct here, and a general relaxation
to let one specific case through is exactly the kind of blanket weakening that
produced the reverted 1ff210e60 mistake earlier this session. The check should
stay exactly as strict; the input facts need to stop contradicting each other.

## Repair direction

When a `product.limitations` fact and a `product.capabilities` fact assert
opposite polarity about the same discriminator-sharing subject, and the
capability fact's source citation includes a real implementation file the
limitation's source does not, the limitation should be re-verified against that
implementation before acceptance -- or flagged `has_unresolved_conflict` so
downstream composition can omit the losing side with a governed disposition
instead of silently emitting a contradiction.
