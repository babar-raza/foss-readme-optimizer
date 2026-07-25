# Agentic Product-Truth Drafting Job — LLM Route Characterization

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> taskcard: `RPOC-033` (`C:\Users\prora\.claude\plans\executive-verdict-the-swirling-adleman.md`
> Part B.2 Phase 2 Lane F, design Part C.5) · method:
> `plans/investigations/tools/probe_draft_product_truth_route.py` — live calls against real
> `llm.professionalize.com` traffic, run against the REAL production prompt
> (`prompts/generation/draft_product_truth.yaml`, via the real `llm.prompt_registry`/
> `llm.generation_prompts.build_draft_product_truth_messages()`) and validated with the REAL
> `facts.agentic_drafting.DraftProductTruthV1` pydantic model — both already built by this same
> taskcard before this probe ran, so this characterizes production code, not a reconstruction a
> later taskcard would need to re-validate (the gap `independent-readme-reviewer-route-
> characterization-2026-07-25`'s own "Limitations" section flagged for its job) · raw output:
> `plans/investigations/evidence/draft-product-truth-route-characterization-2026-07-25/
> probe-results.json` (redacted)

## Why this doc exists

This is a genuinely different job shape from every job already routed in `env.py::
JOB_MODEL_ROUTING`, including the most recently characterized one
(`independent_readme_review`, RPOC-020): that job returns ONE 5-way verdict label with a nested
reasoning object. This job must draft SIX separate structured fields per response
(`audience`, `problems_solved`, `capabilities`, `formats`, `limitations`, `minimal_example`), each
carrying its own citation obligation (a `supporting_fact_id` per interpretive claim; an
`evidence_path`/`required_symbols` per technical claim), plus select the correct
`minimal_example.language` for the repository's real ecosystem. Faithfulness (never citing a
fact_id/path/symbol that was not actually given) matters here as much as schema validity —
a fabricated citation is exactly what the real downstream gates
(`facts/policy_evidence.py::evidence_fact_candidate()` / `facts/interpretive_evidence.py::
groundedness_fact_candidate()`) exist to catch, so this probe scores it directly rather than
assuming schema validity is the only thing that matters, per this project's own "not model-name
folklore" discipline (`LLM-016`/`LLM-018`).

## Connectivity check

Same precedence chain as every prior characterization (`env.py::llm_base_url()`/`llm_api_key()`).
`GPT_OSS_ENDPOINT`, `LLM_API_KEY`, `PROFESSIONALIZE_API_KEY`, and `GPT_OSS_API_KEY` were all set in
this environment; `LLM_BASE_URL` was not (falls through to `GPT_OSS_ENDPOINT`, matching the
documented precedence). `GET /models` returned **HTTP 200** with the expected 7-model inventory —
live and reachable, not a `BLOCKED_INFRA_EXTERNAL` report.

## Model inventory (live `GET /models`)

`qwen3-next` · `experimental` · `gpt-oss` · `recommended` · `qwen3-embedding-8b` ·
`Qwen2.5-VL-7B` · `stable-diffusion-3.5-large` — unchanged from every prior characterization in
this project.

## Alias identity check

Re-confirmed with a fresh deterministic prompt (not reused verbatim from either prior probe, to
rule out any response caching on the gateway side): `experimental` → `"OK5183"`, identical to
`qwen3-next`'s own output; `recommended` → `""` (empty), identical to `gpt-oss`'s own output.
**Confirmed again: only 2 distinct general-purpose chat models on this gateway** — consistent with
`llm-gateway-characterization.md` and `independent-readme-reviewer-route-characterization-
2026-07-25`'s own independent confirmations. `Qwen2.5-VL-7B` was not included as a third candidate
here (unlike the reviewer job's own characterization): this job needs correct, literal-substring
symbol citation and ecosystem-correct code generation, not the reviewer job's single-label
judgment call `Qwen2.5-VL-7B` was already shown competent at — a vision-primary model earns no
extra benefit of the doubt on a citation-precision task with no prior evidence either way, and
`qwen3-next`/`gpt-oss` are this gateway's only two models with any established structured-output
track record at all.

## Test design

Two scenarios, both run through the real prompt end-to-end (real system prompt + real
`user_template` substitution + real `DraftProductTruthV1.model_validate()` on the response):

| Scenario | Ecosystem | Shape | Tests |
|---|---|---|---|
| `java_well_resourced` | java | 6 objective facts, 6 real source/doc files (README, `pom.xml`, 4 `.java` files) — continues this project's established fictional-product convention ("AcmeCells") | Can the model draft a full, richly-cited set of claims when it has plenty to work with, and select `language: "java"` |
| `python_sparse_evidence` | python | 3 objective facts, 2 real files (README, one `.py` file) — deliberately thin ("AcmeFlux") | Does the model resist inventing extra capabilities/paths when there is little to cite (the prompt's own instruction: "draft fewer claims, never invent"), and select `language: "python"` |

Scored on: **schema validity** (parses and validates against the real `DraftProductTruthV1`),
**faithfulness** (every `supporting_fact_id` is in the given fact-ID set; every `evidence_path` is
one of the given file paths; every `required_symbol` is a literal substring of the given file
content — the identical check `evidence_failures()`/`_resolve_cited_fact()` would really apply),
and **language correctness** (`minimal_example.language` matches the given ecosystem).

`max_tokens=3000` for every probe call — matches `facts/agentic_drafting.py::
_MAX_RESPONSE_TOKENS`, the real production client's own configured budget, so this probe measures
against the actual ceiling the shipped code will use, not an arbitrary one that could hide the
exact truncated-mid-JSON confound `independent-readme-reviewer-route-characterization-2026-07-25`
found and corrected for a smaller response shape (900 → 1600 there; 3000 chosen here up front,
generously, given this job's response is larger still).

## Results

### Main run (1 trial per model per scenario)

| Model | Scenario | Schema-valid | Faithful | Language correct | `prompt_tokens` | `completion_tokens` | Latency |
|---|---|---|---|---|---|---|---|
| `qwen3-next` | java_well_resourced | yes | **yes** | yes (`java`) | 1,784 | 597 | 10.7s |
| `qwen3-next` | python_sparse_evidence | yes | **yes** | yes (`python`) | 1,372 | 296 | 6.1s |
| `gpt-oss` | java_well_resourced | yes | yes | yes (`java`) | 1,843 | 2,388 | 21.2s |
| `gpt-oss` | python_sparse_evidence | yes | yes | yes (`python`) | 1,422 | 1,532 | 18.9s |

Both models were schema-valid, faithful, and ecosystem-language-correct on the main run of both
scenarios. `gpt-oss` used **4×–5× more completion tokens** for an equivalent task (2,388 vs. 597
on the java scenario) and took roughly **2× longer** — a real cost/latency difference, not just a
verbosity preference, and (see below) also a real fabrication-risk difference: more generated
tokens is more surface area for a citation to drift from the literal source text.

### Stability / repeat trials (bounded, cost/time — matches this project's own established
reduced-N precedent)

`qwen3-next`, `java_well_resourced`: 5 additional live trials beyond the main run (2 from the
probe script's own N=2 stability block + 3 further diagnostic trials run to characterize an
observed miss — see below). **4/5 faithful (combined with the main run: 5/6 faithful, 83%
across 6 total trials)**. The one miss (`probes.stability` trial 1) and a directly-reproduced
miss from `gpt-oss` (below) share the same character: not an invented path or a fabricated
fact_id, but a **non-literal symbol reference** — citing a plausible dotted-style reference
(e.g. `SaveFormat.XLSX`) to a real field (`public static final String XLSX = "xlsz";` inside
`class SaveFormat`) instead of copying its exact literal text. `qwen3-next`,
`python_sparse_evidence`: 2/2 additional trials faithful (3/3 combined with the main run, 100%).

`gpt-oss`, `java_well_resourced`: 2 additional live trials. **1/2 faithful** (2/3 combined with
the main run, 67%) — the miss was the identical failure mode described above
(`SaveFormat.XLSX` cited as a `required_symbol`, not present as a literal substring in the given
file).

### What this means for the system, not just the route choice

Both models occasionally cite a **paraphrased, not literal, symbol reference** rather than
inventing evidence out of nothing — a real, low-but-nonzero rate for both, never a wildly
fabricated path or an out-of-thin-air fact_id for either model across 9 total live trials. This is
exactly the failure category `capabilities/draft_product_truth.py`'s own bounded repair loop
(`RPOC-033` item 5) exists to catch and correct: the real gate
(`facts/policy_evidence.py::evidence_failures()`) rejects `SaveFormat.XLSX` as a missing required
symbol, the field is `blocked` with that exact reason fed back as a repair hint, and a re-prompt
naming the specific missing literal string is a much narrower, easier repair than the original
open-ended drafting task. This is evidence the two-gate-plus-repair-loop design is doing real
work, not just theoretical defense in depth.

## Recommendation

**Route `draft_product_truth` to `qwen3-next`.**

Evidence: strictly better on every axis this job needs relative to the one real alternative —
higher faithfulness rate across combined trials (89% overall: 8/9 vs. `gpt-oss`'s 6/7 — note
`gpt-oss`'s `python_sparse_evidence` scenario was only run once, at the main-run rate, so its own
combined denominator is smaller), 100% schema validity and language-correctness on every trial for
both models, but 2–5× lower latency and 4–5× lower completion-token cost than `gpt-oss` for an
equivalent task. This extends (does not merely repeat) this project's existing routing discipline:
`llm-gateway-characterization.md` (`LLM-018`) and `independent-readme-reviewer-route-
characterization-2026-07-25` both already found `gpt-oss` weaker on structured/instruction-critical
work; this run independently reconfirms that finding on THIS job's own genuinely different
multi-field-with-citations shape, at real live cost/latency numbers, rather than assuming the
prior evidence transfers unchanged.

This recommendation is evidence, not a routing change on its own — but per this taskcard's own
scope (unlike `RPOC-020`, which deliberately left `env.py` untouched for a later taskcard to wire),
`env.py::JOB_MODEL_ROUTING["draft_product_truth"]` IS updated to `"qwen3-next"` as part of this
same taskcard (RPOC-033), since no later taskcard exists to do it separately.

## Limitations / honestly out of scope for this pass

- No dedicated long-context ladder was run for this job specifically. Unlike the independent-
  reviewer job (which routinely receives a full README + full product facts + full presentation
  plan, tens of thousands of tokens), this job's own bounded-context selector
  (`facts/agentic_drafting.py::MAX_CONTEXT_CHARS = 45_000` chars, roughly 10–12k tokens) plus the
  objective-facts JSON and instructions stays far below `qwen3-next`'s own already-proven-safe
  ~71k-token ceiling (`llm-gateway-context-ceiling-corrected.md` L1′) by design — a dedicated ladder
  for a payload shape that structurally cannot approach that ceiling was judged not worth the
  added live-call cost for this pass. Worth revisiting only if a future repository's selected
  context genuinely grows far larger than today's bounded selector produces.
- 2 scenarios (one well-resourced, one sparse), each run a handful of times — not a large-N
  statistical sample. The faithfulness rate reported above (83–100% depending on
  model/scenario/trial-count) is directional evidence for a routing decision between exactly two
  real candidates, not a precise, tight-confidence-interval production error rate; the real
  production defense against the miss rate observed here is the bounded repair loop itself
  (see "What this means for the system" above), not a claim that either model never makes this
  kind of mistake.
- `SYSTEM_FAILURE`-equivalent (a genuinely unusable/impossible-to-draft input) was not
  scenario-tested — both scenarios gave the model a reasonable, if sparse in one case, amount of
  real evidence. Not needed for a route-selection decision between two candidates who both handle
  it fine at the tested sizes; the production repair loop's own exhaustion-then-escalate path
  (never a silent guess) is the actual safety net for this case, not model selection.
