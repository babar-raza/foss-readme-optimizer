# Upstream issues — Aspose.TeX FOSS for Python

Verified: 2026-08-02 against https://github.com/aspose-tex-foss/Aspose.TeX-FOSS-for-Python

## Package fails to import entirely — systemic indentation corruption
- **Severity**: BLOCKING
- **Evidence**: `import aspose_tex` raises a real `IndentationError`. Root cause: 35 of the 45 `.py` files under `src/aspose_tex/` have every block body indented to exactly one space regardless of true nesting depth — confirmed byte-for-byte at the git blob level (baked into the committed source, not a checkout/tooling artifact; confirmed by building a sibling product, `aspose_pdf_python`, clean at 118/118 files with identical tooling). Example: `IndentationError: expected an indented block after 'for' statement on line 65` in `_input/catcode.py`. Consequently, 67 of 69 test modules fail to collect under `pytest` for the identical reason.
- **Impact**: literally none of the documented Python examples in this README can currently execute against this source snapshot.
- **Not fixable here because**: reconstructing correct indentation for 35 files' worth of logic from a uniformly-flattened state is not recoverable by inspection or guesswork — it requires the upstream maintainer to restore the original source (e.g. from pre-corruption history). The README's code examples were statically verified accurate against the real (non-executing) source's class/method signatures, so they describe the intended API correctly — they just cannot run until this is fixed upstream.
