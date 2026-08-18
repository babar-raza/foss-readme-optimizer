# S5 triage: slides-python `unauthorized protected-content loss: technical_terminology:01e835667d2c7cfc`

Resolved to the literal fragment (2026-08-18, offline, zero provider calls): the protected
inline-code span is **`prs.master_theme`** (`markdown:inline_code` in the source README;
recovered by hashing every inline-code span against the fragment digest).

## Mechanism

`facts/protected_content.py` protects every inline-code span as `technical_terminology`.
`readme/document_validation.py` authorizes hiding such a span EXCEPT when its base name
(`master_theme`) is a real member of the extracted API surface and the candidate text never
mentions it — then it is a genuine terminology loss and blocks. So: the slides candidate omits
a real, source-documented API property.

## Why this is a quality defect, not over-blocking

The validator is doing exactly what Decision #104's parity reviews keep finding from the other
side (Q1/Q3: thin capabilities, missing real capabilities like cells' FormulaEvaluator): the
composition drops real API surface the original README taught. The correct fix direction is to
carry the term, not to authorize its loss.

## Next diagnostic (queued; needs the slides composed candidate)

The imported `api_method_index` template slot exists precisely for "members verified in the
current API surface AND already mentioned by the source README's own inline code" — the exact
description of `prs.master_theme`. Hypotheses to check once the portfolio pass's next iteration
persists slides' blocked-plan diagnostics (`runs/readme-poc/aspose-slides-foss__Aspose.Slides-
FOSS-for-Python/diagnostics/`):

1. The slot only admits *methods* (callables) and skips *properties* like `master_theme` —
   extend the slot's member filter to properties.
2. The slot wasn't composed into slides' candidate at all (slot selection/ordering issue).
3. The surface extractor missed `master_theme` (then the validator exception would have hidden
   the loss — ruled out by the block itself, which requires the name IN `api_names`).

Also fix at the same time: slides' remaining 4 blocking claims are the same S1/E5 class as
note/font/email.
