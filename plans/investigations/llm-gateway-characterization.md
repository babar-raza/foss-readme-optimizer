# LLM Gateway Characterization — llm.professionalize.com

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: `tools/probe_llm_gateway.py` — live GET /models, chat context ladder w/ end-needle, N-trial structured-output, embeddings cosine on known README pairs, native tool-calling (single-step, multi-step, parallel), all against real `llm.professionalize.com` traffic

## Model inventory (live `/models`)

`qwen3-next` · `gpt-oss` · `qwen3-embedding-8b` · `Qwen2.5-VL-7B` (vision) ·
`stable-diffusion-3.5-large` (image gen) · aliases `experimental`, `recommended`.

## Findings

| # | Finding | Evidence | Design consequence |
|---|---|---|---|
| L1 | **Context is NOT small** for the qwen models: ~96k-token prompts accepted with perfect end-of-prompt needle recall (`qwen3-next`, `Qwen2.5-VL-7B`, all 6 ladder steps). | ctx ladder, needle_found=true at 96k | Whole-README prompts are feasible; retrieval/chunking is an optimization, not a necessity. The prior "small context" assumption is **disconfirmed for qwen3-next** — the weakness lives elsewhere. |
| L2 | **`gpt-oss` — the engine's current default — is the unreliable model**: needle never recovered even at ~2k tokens (instruction not followed at any size); structured-output valid rate **1/10** (unterminated strings, missing delimiters); ~5s latency vs ~2s for qwen3-next. | ctx ladder needle=false ×6; structured trials 1/10 | **Do not use `gpt-oss` for structured output or instruction-critical steps.** Roadmap card: per-job model routing; default structured model → `qwen3-next`. The shipped engine survives gpt-oss only because its one job is a prose paragraph behind Pydantic validation + retry. |
| L3 | **`qwen3-next` is reliable for structured output**: 5/5 schema-valid JSON, no code fences, ~2.2s. `Qwen2.5-VL-7B` also 5/5. | structured trials | Structured jobs (drift classification assist, desired-model deltas, description drafting) target qwen3-next with schema validation as backstop. |
| L4 | **Embeddings are fit for template/similarity detection**: `qwen3-embedding-8b`, 4096 dims; known same-bot-template pair `3d-java~3d-python` = **0.788** (highest); unrelated pairs 0.45–0.55. Clean margin. | cosine matrix | Generic-template overwrite (INT-008), template-clone (VAL-016), and generic-prose (RDM-020) detection use embeddings + threshold (~0.75 same-template ballpark; calibrate on full 14-README corpus in roadmap), not chat-model judgment. |
| L5 | **Vision + image generation exist on the same gateway** (`Qwen2.5-VL-7B`, `stable-diffusion-3.5-large`). | /models | Phase-24 visual pipeline (generate via SD, validate claims/alt-text via VL) can stay on this gateway — no new vendor. Roadmap note only; out of sprint scope. |
| L6 | **Native OpenAI-style tool-calling (`tools`/`tool_choice="auto"`) is supported and reliable for both chat models — including `gpt-oss`**: `qwen3-next` 5/5 correct single-step tool call with valid-JSON arguments; `gpt-oss` also **5/5**, despite scoring only 1/10 on freeform structured JSON (L2). Multi-step works for both: a synthetic tool-result message fed back produces a coherent final text answer, not a repeated/garbled tool call. `Qwen2.5-VL-7B` (vision model) fails every trial (0/5, hard request failure) — it does not support the `tools` param at all. | tool_calling_single_step, tool_calling_multi_step probes | **This is the single most important Wave 1 finding.** The gateway's constrained tool-call decoding path is far more reliable than its freeform-JSON path, even for the otherwise-unreliable `gpt-oss`. Any structured-action protocol (sprint Task 4.3) should be encoded as a tool call, not as a freeform-JSON-in-prose instruction — it inherits this reliability instead of L2's 1/10 failure mode. Native tool-calling is therefore a viable primary path on this gateway, not just a fallback-only design. `Qwen2.5-VL-7B` stays vision-only (per L5), never a planning/tool-calling route. |
| L7 | **Parallel tool-calling: single-trial observation, not yet a characterized reliability finding.** One prompt, sent once per model (`probe_llm_gateway.py:366-399` — a `for model in chat_models` loop, no repeated-trial dimension): `qwen3-next` returned both tool calls in that one response (2/2 within the single call); `gpt-oss` returned only one of the two (1/2 within its single call); the vision model failed outright. **Correction (2026-07-19, see `plans/investigations/capability-dispatch-production-readiness.md`): this is N=1 per model, not a repeated-trial result** — currently indistinguishable from a one-off sampling/routing hiccup versus a systematic `gpt-oss` limitation. Status: `RESEARCH-GATED`, pending a properly designed follow-up (N≥10 trials per model, across ≥2 separate sessions) before "unreliable" is asserted as a model property. | tool_calling_parallel probe, N=1/model | No current design decision depends on resolving this — decision #27's one-capability-per-turn baseline is already justified by L6 (5/5 for both models on single-step calls) independent of the parallel-call question. Do not cite this row as a characterized `gpt-oss` weakness until the N≥10/≥2-session follow-up runs; `qwen3-next`'s parallel capability remains a latency optimization to opportunistically exploit later, not something to design the loop around now. |
| L8 | **Tool-calling latency matches plain chat latency** (~1.6–2.4s per call for both chat models, single- or multi-step) — no meaningful tool-calling tax observed. | latency_s fields across probes 5–7 | The L4 "~2s/call, batch per surface, not per line" budget from Wave 0 stands unchanged for a tool-calling-based loop; no separate latency budget needed for the structured-action path. |

## Revised weak-LLM design rules (evidence-backed)

1. Route by job: structured/instruction-critical → `qwen3-next`; prose → `qwen3-next` (prefer) or `gpt-oss` w/ validation; similarity → `qwen3-embedding-8b`; visuals (future) → SD + VL; **planning/capability-selection → native tool-calling on either chat model (L6), one capability per turn (L7)**.
2. Keep every model output behind schema validation + referential-integrity cross-checks (unchanged — this is what already saves the engine from gpt-oss). For tool calls specifically: validate `arguments` as JSON and the `capability_id`/function name against the known registry before dispatch — the model's own tool-call framing is reliable (L6) but is never trusted as an authorization decision by itself (matches decision #26(c)).
3. Generation cache keyed by fingerprint remains mandatory (temp-0 ≠ byte-stable; and L2 shows model choice may change → cache pins accepted output).
4. Latency budget ~2s/call (qwen3-next) permits per-surface calls but not per-line calls; batch prompts per surface. Unchanged for tool-calling (L8).
5. Structured-action dispatch (sprint Task 4.3) is implemented as a native tool call, not a freeform-JSON prose instruction (L6) — one capability offered/selected per planning turn (L7), never assuming multi-call-per-turn works on every routed model.

## Deviation from plan

Probe used N=5 trials for qwen models (N=10 only for gpt-oss, the suspect) instead of N=10
everywhere — cost-bounded; qwen results were 5/5 with zero variance. Full N=10 calibration can
ride the roadmap's validator-calibration card if needed. The Wave 1 tool-calling extension
(probes 5–7) reused this same N=5 budget and did not add rate-limit/error-behavior fuzzing —
out of scope for a spike per the sprint plan; nothing in `AGT-002`'s acceptance bar needs it.
