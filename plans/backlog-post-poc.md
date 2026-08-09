# Post-POC backlog

- 2026-08-09: poc runner failed for aspose-html-foss/Aspose.HTML-FOSS-for-Python: ValueError: verified template lacks required capability, acquisition, or example facts
- 2026-08-09: aspose-html-foss/Aspose.HTML-FOSS-for-Python cannot deliver a verified README:
  its pyproject.toml declares `build-backend = "setuptools.backends.legacy:build"`, a module
  that does not exist in setuptools, so every `pip install .` fails before building and the
  acquisition/example proofs stay blocked. Upstream one-line fix: use
  `build-backend = "setuptools.build_meta"` (as every other portfolio repo does), then re-run
  `readme-agent poc --repo aspose-html-foss/Aspose.HTML-FOSS-for-Python`.
- 2026-08-09: poc runner failed for aspose-pdf-foss/Aspose-PDF-FOSS-for-Python: ValueError: invalid README header visual: capability_columns_short failed
- 2026-08-09: poc runner failed for aspose-slides-foss/Aspose.Slides-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-html-foss/Aspose.HTML-FOSS-for-Python: ValueError: compiled verified presentation is invalid: API reference contains an incomplete generic description
- 2026-08-09: poc runner failed for aspose-slides-foss/Aspose.Slides-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-slides-foss/Aspose.Slides-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: verified diagram has 0 input node(s); requires 1
- 2026-08-09: poc runner failed for aspose-words-foss/Aspose.Words-FOSS-for-Python: composition opening summary contains invalid sentence punctuation
- 2026-08-09: BarCode header-visual mismatch — the composed candidate's output labels
  canonicalized MIME subtypes ("PNG (image/PNG) files") while the document-plan render
  produces lowercase ("image/png"), so candidate_exact_mermaid fails. Canonical-abbreviation
  application to diagram endpoint labels is unstable across the two render sites; unify the
  canonicalization step (apply once, in the authoritative candidate derivation) and re-run.
- 2026-08-09: Cells retains 9 blocking source claims (feature bullets, contribution steps,
  support links) that are fact-authorized preserves without a merged placement; per-claim
  routing found no structural home. Needs a working-condition placement lane that routes
  fact-authorized leftovers without pre-empting whole-section preservation (a naive
  preserve-path deferral regressed Security-section carry and was reverted).
- 2026-08-09: poc runner failed for aspose-tex-foss/Aspose.TeX-FOSS-for-Python: ValueError: verified template lacks required capability, acquisition, or example facts
- 2026-08-09: TeX cannot compose - capabilities verify but the acquisition and minimal
  example are blocked and the clone-and-import fallback found no usable package metadata in
  api.public_surface. Needs the acquisition fallback widened to manifest-only evidence, or the
  decision #99 LLM-drafted validator-grounded product-truth lane.
- 2026-08-09: 38 non-live tests pin pre-#99 fail-closed expectations (deferred-at-approval, source-assurance reinsert, final-claim corpus); update the expectations to the working-condition contract.
