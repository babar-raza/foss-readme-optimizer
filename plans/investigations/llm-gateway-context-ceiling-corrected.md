# LLM Gateway Context-Ceiling — Corrected (supersedes L1's ~96k-token claim)

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: `tools/probe_llm_gateway.py` (corrected 2026-07-21) — live GET /models, chat context
> ladder w/ end-needle (filler-scaling bug fixed), a new multi-turn tool-calling
> conversation-growth probe, N-trial structured-output, embeddings cosine, native tool-calling
> (single-step, multi-step, parallel) — all against real `llm.professionalize.com` traffic

## Why this doc exists

`llm-gateway-characterization.md`'s finding L1 ("~96k-token prompts accepted with perfect
end-of-prompt needle recall") was traced to its source script this session and found to rest on
a bug, not a valid measurement. `probe_llm_gateway.py`'s context-ladder filler was built as
`("lorem ipsum dolor sit amet " * 200)[: approx_tok * 4 - 400]` — a **fixed** ~5,600-character
source string, sliced to a target length that was almost always longer than the source itself.
Python slicing past a string's actual length is a no-op, so **every ladder rung from 2,000 to
96,000 "approx tokens" sent nearly the same ~1,400-real-token filler**, six times, under six
different labels. This exactly explains why the original evidence file's own `usage.prompt_tokens`
stayed flat at ~1,031–1,032 across the whole ladder — a one-line script bug, not a gateway quirk,
not evidence of anything at 96k tokens. `LLM-019` (`plans/requirements.md`) tracks this
correction; this doc is the corrected replacement evidence for `L1`.

The script was fixed (scale the filler's repeat count to the target size *before* slicing) and
re-run live, once, against the real gateway on 2026-07-21. Raw output:
`plans/investigations/evidence/llm-probe/probe-results.json` (overwrites the prior, bugged file —
the prior numbers are superseded, not separately preserved, since they were never valid).

## Corrected findings

| # | Finding | Evidence | Design consequence |
|---|---|---|---|
| L1′ | **`qwen3-next`'s real, proven-safe context ceiling is ~71,069 tokens** (the top rung actually tested — the "96,000 approx_tokens" label undershot real 96k tokens because this filler's true ratio is ~5.35 chars/token, not the assumed 4), with perfect end-of-prompt needle recall at every real size tested (1,439 / 5,884 / 11,810 / 23,663 / 47,365 / 71,069 tokens, all `needle_found: true`). Latency scaled from 1.6s to 5.0s across that range — real, meaningfully increasing, not flat. **Untested above ~71k real tokens** — no claim is made about behavior beyond this. | `context_ladder.qwen3-next`, corrected probe | Whole-README, whole-dossier prompts remain feasible with very large headroom over any realistic planner payload (see L-multi-turn below) — but "96k" must never be cited again; the validated figure is **~71k, and only up to there**. Any future need to test genuinely higher must extend the ladder's labels well past 96,000 (e.g. to ~130,000) to actually reach a real 96k-token prompt with this filler's true ratio. |
| L2′ | **`gpt-oss` fails needle recall at every size tested, including the smallest (~1,494 real tokens)** — confirmed, now on genuinely-scaled real prompts, not the previous accidentally-fixed-size ones. This is a real, size-independent instruction-following weakness, not a context-length limitation — the original L2 conclusion happened to be directionally right, but was previously only demonstrated at one real size (~1,031 tokens) repeated under six different labels, not across an actual range. | `context_ladder.gpt-oss`, corrected probe | Reinforces: never route instruction-critical/structured work to `gpt-oss` regardless of prompt size — this is now demonstrated across a real 1.5k–71k token range, not just one untested point repeated six times. |
| L-VL | **New, incidental finding**: `Qwen2.5-VL-7B` (the vision model, not used for planning) hit a real `ContextWindowExceededError` (HTTP 400, `litellm.ContextWindowExceededError`) at the 96,000-label rung, after succeeding at 47,365 real tokens — its real ceiling sits somewhere in between, exact value unmeasured (the failing request was rejected before a token count was returned). Not load-bearing for this project (VL is never routed for planning/tool-calling per `llm-gateway-characterization.md` L5/L6), noted for completeness only. | `context_ladder.Qwen2.5-VL-7B` | No design consequence — VL stays out of scope for planning. |
| L-multi-turn | **New finding, closing the "does a real multi-turn planner conversation actually grow large?" gap L1 never answered**: a synthetic but realistically-shaped supervisor dossier (system prompt + a turn-0 user message embedding a bootstrap result + 9 specialist status entries + one domain's full verification findings, ~640 tokens as actually measured) was sent through a real tool-calling round trip. `qwen3-next`: turn 1 = **639** prompt tokens (1 tool call emitted), turn 2 = **686** prompt tokens (0 tool calls — model stopped) — a **47-token** real growth for one full tool-call/tool-result round trip. `gpt-oss`: turn 1 = **454** prompt tokens, 0 tool calls (did not attempt a tool call for this same prompt, unlike `qwen3-next` — a real, previously-unobserved behavioral difference between the two models for identical input). | `multi_turn_conversation_growth`, corrected probe | A real dossier-shaped planner turn costs **hundreds, not tens-of-thousands, of tokens** — three orders of magnitude below the proven-safe ~71k ceiling (L1′). This is strong evidence that **a hard token-budget circuit-breaker is a safety net for a pathological case, not a routinely-binding constraint** for dossiers shaped like today's specialist outputs. It does **not** by itself prove a much larger real registry entry (e.g. a specialist with many release/handoff findings, or a very long README diff) stays small — only that the *baseline* shape does. `AGT-007`'s dossier design should still enforce a budget (defense in depth, cheap to keep), but should size it as a generous multiple of typical turns (e.g. an order of magnitude over what's observed here), not as a fraction of the (now-corrected, still-large) ceiling. |
| L-structured-variance | **New finding**: this run's `gpt-oss` structured-output valid rate was **8/10** (`valid_rate: 0.8`), materially different from the original probe's `4/10` (already known to be misreported as "1/10" in this project's docs, per `LLM-018`). Two independent single-session N=10 runs of the identical prompt against the identical model produced 0.4 and 0.8 — a **0.4 swing**, not noise-level variance. | `structured_output.gpt-oss` this run vs. prior evidence file | Confirms, with a second independent data point, the adversarial review's and the original investigation's own recommended gate: **N=10-per-session is not enough to characterize `gpt-oss`'s structured-output reliability** — a stable rate needs N≥20 trials across ≥3 separate sessions/days before being treated as a routing input. Since `gpt-oss` is not routed to any structured job today regardless (`env.py::JOB_MODEL_ROUTING`), this doesn't change current behavior, but it further disqualifies `gpt-oss` from ever being considered a structured-output fallback without that follow-up — the number swings too much run-to-run to trust either 0.4 or 0.8 in isolation. |

## Revised design rule (supersedes `llm-gateway-characterization.md` rule 4's implicit "~96k budget")

Budget the planner dossier off the gateway's own `usage.prompt_tokens`, returned free on every
live call, rather than any hard-coded ceiling-derived constant or a client-side tokenizer
estimate (`tiktoken` would in any case tokenize for OpenAI's own vocabulary, not whatever
`qwen3-next` actually uses server-side). Given L-multi-turn's real measurement (hundreds of
tokens per turn) sits roughly three orders of magnitude below L1′'s proven ~71k ceiling, an
operational budget with generous headroom (e.g. an order of magnitude above observed real usage)
is appropriate as a circuit breaker, not as a routinely-approached limit — the corrected evidence
does not support treating context size as this design's binding constraint.

## Deviation from plan

The probe script's fix and re-run happened as a single, one-time live pass (not a full
N≥20/≥3-session calibration campaign — that remains open per the `gpt-oss` structured-output
variance finding above, tracked as part of `LLM-018`/`LLM-019`'s own follow-up, not repeated here).
`Qwen2.5-VL-7B`'s exact real ceiling was not pinned down (the failing request never returned a
token count) — left as an open, non-blocking detail since VL is out of scope for planning.
