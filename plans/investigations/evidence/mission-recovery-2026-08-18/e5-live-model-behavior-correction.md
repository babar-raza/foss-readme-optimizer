# E5 correction: the live model does not naturally choose `excluded_with_reason` for note's claim

## What was claimed vs what is actually true

`e5-slice1-real-target-validation.md` validated `corroborate_claim_disposition()` directly with
a **hand-constructed** `llm_result` dict simulating the intended `unverifiable_fixture_dependency`
verdict — it correctly proved the deterministic corroboration logic accepts that shape when
offered. It did NOT prove, and should not have been read as proving, that the live `qwen3-next`
model actually produces that classification for this claim. The post-merge note canary
(`note-canary-post-merge.log`) shows the real claim **still blocking** after the merge — this
correction traces exactly why.

## Live reproduction (2026-08-18, real candidate, real model, zero fabrication)

Called `default_claim_disposition_client()` directly against note's REAL blocking claim
(`source:claim:4781:0d4d28fef68b38fd`, the Quick Start code block) and note's REAL rendered
candidate (`runs/readme-poc/aspose-note-foss__.../diagnostics/blocked-candidate.md` — the
diagnostics persistence added earlier this session made this possible). (A first attempt
mistakenly passed the SOURCE README as the candidate, which trivially "matched itself" —
methodological error, discarded, not reported as a result.)

**The model's real verdict**: `verified_against_source`, citing `examples/export_pdf.py`, with
a long reasoning paragraph that — read carefully — admits the exact quote is NOT present
("the original sentence's specific title access pattern... is not present in the candidate")
while still asserting the claim is "genuinely... verified." Deterministic corroboration
correctly refuses this (`corroborated: False`) because the cited file does not contain the
claim text verbatim — **the safety property held exactly as designed.**

**The model never attempted `excluded_with_reason` / `unverifiable_fixture_dependency` at all**,
despite the prompt (version 2) explicitly documenting that predicate for exactly this shape of
claim (a fixture the isolated verifier cannot assume exists).

## Why this matters

1. **The corroboration/fail-closed safety property is proven working on a real adversarial
   case** — the model produced a plausible-sounding but factually loose justification, and
   the deterministic check caught it. This is exactly the intended defense.
2. **The E5 design's assumption that the model will naturally reach for the new predicate is
   NOT confirmed** — it needs either explicit few-shot guidance, a more directive system
   prompt for exactly this claim shape (fixture-dependent code block), or a different closure
   mechanism entirely (e.g., Lane B: ensure the composed candidate contains a VERIFIED example
   using the identical fixture/API pattern, closing the claim via `verified_obligation_
   replacement` instead of the LLM path).
3. **Determinism note**: this is a second real data point (after the temp-0 tool-argument
   nondeterminism probe) that qwen3-next's classification choice among multiple plausible
   options is not something today's prompt reliably steers — worth folding into the probe
   evidence as a qualitative finding alongside the quantitative byte-nondeterminism result.

## Disposition

Not fixed this session (would require prompt engineering + a live-response evaluation loop,
genuinely separate scope from slice 1's deterministic corroboration work, which is real and
correctly landed). Recorded honestly per the mission's own standard: "do not approve a
candidate merely because it passed the optimizer's own validators" applies equally to not
declaring a fix complete because its corroboration layer passed a hand-constructed test.

**Corrected status**: E5 slice 1 (README-circularity fix, excluded_with_reason mechanism,
shared ratchet) is real, tested, and safely inert-until-chosen. It has NOT yet closed note's
residual blocking claim in live practice. The S1 residue map's Lane C item stays open;
Lane A and Lane B (confirmed closing barcode/font/slides' Development-H3 and property-slot
claims respectively) remain the higher-confidence closure path for the bulk of the residue.
