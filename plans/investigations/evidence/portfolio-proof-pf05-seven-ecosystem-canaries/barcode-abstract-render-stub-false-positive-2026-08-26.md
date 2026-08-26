# PF05-PYSTUB-001 — an `@abstractmethod` interface declaration is misclassified as a broken stub

## Status

Root-caused with source-level verification. Not repaired: both files involved
are contract-bound (`curated_python_api_ast.py` is a fact-verification-contract
file; `claim_map_capability_validation.py` matches the
`readme/claim_*.py` document-contract glob), so the fix batches rather than
lands mid-pass.

## Symptom

`aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python` blocks with:

```
template.section.api_method_index.claim:61:c6d415b148d0cc08:api.public_surface:
capability wording for unimplemented member 'render'
```

## Root cause

`Barcode.render()` (`src/aspose_barcode_foss/result.py:27`) is a real, fully
implemented public method -- it merges render options, resolves the symbology
profile, and delegates to a concrete renderer. Concrete implementations also
exist in `SvgRenderer.render()`, `PngRenderer.render()`, and
`PdfRenderer.render()`.

The member `claim_map_capability_validation.py` is actually flagging is a
*different* class's method of the same bare name:
`Renderer.render()` in `_internal/renderers/base.py` is declared
`@abstractmethod` on an `ABC`, with the standard Python convention body
`raise NotImplementedError`. `curated_python_api_ast.py::member_is_implemented()`
treats any method whose body is exactly a `raise NotImplemented*/NotSupported*`
call as an unimplemented stub (line 174-186) -- correct for a genuinely broken
implementation, but with no exception for an `@abstractmethod` declaration,
which raises for an entirely different, intentional reason: it must never be
called directly, because the ABC machinery prevents instantiating `Renderer`
itself and every real call goes through a concrete override.

`claim_map_capability_validation.py::_mentions_stub_member()` then matches the
candidate's bare, unqualified "render() method" text against this
`implemented=False` member without disambiguating which class's `render` the
candidate prose actually refers to, so `Barcode.render()`'s real, working
capability gets rejected on the strength of an unrelated abstract interface
declaration that happens to share its name.

This is the Python analogue of `CORE-038` (the C++ empty-body-stub detector
flagging a constructor whose real work lives in its member-initializer list):
a structurally-empty-looking body is not evidence of a missing capability when
the emptiness is required by the language's own interface-declaration idiom.

## Repair direction

Either narrows the false-positive path:

1. `member_is_implemented()` should not resolve `False` for a method decorated
   `@abstractmethod` purely on body shape -- an abstract declaration is a
   different semantic category from an incomplete implementation, and
   resolving it to `None` (unresolved) rather than `False` would be consistent
   with the module's own stated "absence of evidence is never a negative
   signal" contract.
2. `_mentions_stub_member()` should be class/qualified-name-aware rather than
   matching on the bare method name alone, so a stub finding on one class's
   member never disqualifies capability wording about a different class's
   member of the same name.

Either alone would resolve this case; (1) is the smaller, more general fix.

## Why it was not fixed here

`curated_python_api_ast.py` is inside the fact-verification contract
(`facts/verification_contract.py`), and `claim_map_capability_validation.py`
matches the document-contract's `readme/claim_*.py` glob. A fleet pass was in
flight when this was found.
