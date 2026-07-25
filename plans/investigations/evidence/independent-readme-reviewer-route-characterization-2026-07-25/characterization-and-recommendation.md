# Independent README-Reviewer Job — LLM Route Characterization

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> taskcard: `RPOC-020` (`C:\Users\prora\.claude\plans\executive-verdict-the-swirling-adleman.md`
> Part B.2 Phase 2 Lane V) · method: `plans/investigations/tools/probe_independent_review_route.py`
> — live calls against real `llm.professionalize.com` traffic, reusing
> `plans/investigations/tools/probe_llm_gateway.py`'s established methodology (live N-trial
> reliability, the gateway's own `usage.prompt_tokens` as ground truth for context size, a
> mid-context needle to prove real reading rather than assumed reading) but targeting THIS job's
> actual shape · raw output:
> `plans/investigations/evidence/independent-readme-reviewer-route-characterization-2026-07-25/probe-results.json`
> (redacted, two full live runs overwritten in place — the second run is the corrected/final one,
> see "Deviations" below)

## Why this doc exists

The project is about to add a new LLM job: an independent README-quality reviewer that reads
grounding facts + repository context + a candidate README and returns one of 5 structured verdicts
(`ACCEPT` / `REJECT_REPAIRABLE` / `BLOCKED_FACT_CONFLICT` / `BLOCKED_MISSING_EVIDENCE` /
`SYSTEM_FAILURE`) with nested per-criterion reasoning. This is a genuinely different job shape from
every job already routed in `env.py::JOB_MODEL_ROUTING` — those are either short single-paragraph
phrase-ups (`relationship_explained`) or narrow forced-tool-call choices among an
already-vetted menu (`supervisor_planning`, `specialist_selection`, `prose_quality_check`,
`repair_capability_selection`). None of them exercise long-context freeform-JSON quality judgment,
which is what this job needs. Per this project's own stated discipline (no model-tier guessing
without live evidence — `LLM-016`/`LLM-018`, `llm-gateway-characterization.md`'s own "not model-name
folklore" framing), this doc is that live evidence for the new job specifically, not an assumption
carried over from the existing routing table.

## Connectivity check (per the taskcard's own instruction, run before anything else)

`README_AGENT_LLM_BASE_URL`/`README_AGENT_LLM_API_KEY` do not exist as literal names in this
project — the real precedence chain is `env.py::llm_base_url()` (`LLM_BASE_URL` >
`GPT_OSS_ENDPOINT` > `https://llm.professionalize.com/v1`) and `env.py::llm_api_key()`
(`LLM_API_KEY` > `PROFESSIONALIZE_API_KEY` > `GPT_OSS_API_KEY`). In this environment,
`GPT_OSS_ENDPOINT` and all three API-key env vars are set. A minimal `GET /models` call before any
other work returned **HTTP 200** in 1.62s with the expected 7-model inventory (see below) — the
gateway is live and reachable, so this proceeded as a real characterization run, not a
`BLOCKED_INFRA_EXTERNAL` report.

## Model inventory (live `GET /models`, both runs identical)

`qwen3-next` · `experimental` · `gpt-oss` · `recommended` · `qwen3-embedding-8b` ·
`Qwen2.5-VL-7B` · `stable-diffusion-3.5-large` — unchanged from
`llm-gateway-characterization.md`'s original inventory.

## Alias identity check (new — not run by the prior characterization)

Before assuming `recommended`/`experimental` were extra distinct candidates, both were probed with
an identical deterministic (`temperature=0`) prompt alongside the two named chat models, and their
raw output text diffed against each named model's output (same technique both live runs):

| Model | Output | Matches |
|---|---|---|
| `qwen3-next` | `"OK7419"` | — |
| `experimental` | `"OK7419"` | **identical to `qwen3-next`** |
| `gpt-oss` | `""` (empty) | — |
| `recommended` | `""` (empty) | **identical to `gpt-oss`** |

**Finding: `experimental` is an alias for `qwen3-next`, `recommended` is an alias for `gpt-oss`.**
There are only **2 distinct general-purpose chat models** on this gateway, not 4 — confirmed
empirically rather than assumed. A third genuinely distinct chat-capable model does exist,
`Qwen2.5-VL-7B` (vision-primary, but usable for pure-text freeform JSON per the original
characterization's L3), and was included as the third candidate below to satisfy a real ≥2-3-model
comparison rather than stopping at 2 once the aliases were ruled out.

## Test design

A fictional Java library, "AcmeCells" (continuing this project's own established fictional-product
convention from `probe_llm_gateway.py`'s `SCHEMA_PROMPT`), with a rich, internally-consistent,
independently-checkable fact set (capabilities, explicitly-unsupported formats, explicit
limitations, verified Maven acquisition, license, verified minimal example — the full JSON is
inline in the probe script's `GROUNDING_FACTS`). Four candidate READMEs were written against this
same fact set, each designed to force one specific verdict a careful human reviewer would give:

| Scenario | Design | Expected verdict |
|---|---|---|
| `well_grounded_specific` | Every claim traceable to a grounding fact; no invention | `ACCEPT` |
| `generic_template_overpromotion` | Marketing fluff ("blazing-fast", "enterprise-grade"), zero product specifics, nothing actually false | `REJECT_REPAIRABLE` |
| `fact_conflict` | Claims `.xls`/VBA/pivot-table support and `pip install` — all directly contradicted by the grounding facts | `BLOCKED_FACT_CONFLICT` |
| `missing_evidence` | Specific, checkable claims (50,000 rows/sec, 200 enterprise customers, 2GB streaming) that no grounding fact supports or refutes | `BLOCKED_MISSING_EVIDENCE` |

Each model was given the identical strict-JSON verdict-schema instructions (5-way taxonomy +
nested `reasoning` object with `product_specificity`/`overpromotion_check`/`readability`/
`generic_template_symptoms`/`fact_conflicts[]`/`missing_evidence[]`, matching the shape the charter
(`executive-verdict-the-swirling-adleman.md` C.4) describes for the real reviewer) and scored on
both **schema validity** (parses, has the right keys/types) and **verdict correctness** (matches
the scenario's expected verdict).

A fifth, long-context scenario reused `well_grounded_specific` but padded with ~20-22k real tokens
of thematically-consistent (not lorem-ipsum) synthetic repository context — a formulas-doc excerpt
covering all 40 named functions plus a generated multi-entry changelog — with a unique needle
sentence (`GLYPH-40217`) embedded 55% through the padding. The prompt asked the model to both
return the verdict AND echo the needle's exact value in a `context_check` field, directly testing
whether long-context judgment quality survives, not just whether the needle is found.

**Deviation from plan (mid-investigation correction, documented openly, matching this project's own
precedent in `llm-gateway-context-ceiling-corrected.md`):** the first live run used
`max_tokens=900` for the discrimination probe. `gpt-oss` produced longer reasoning arrays than
`qwen3-next` and 2/4 of its responses were truncated mid-JSON by that budget (real content, cut off
before the closing brace — not garbled text). This was a budget confound, not a fair
apples-to-apples comparison, so `max_tokens` was raised to 1600 for a second, final live run before
drawing any conclusion. **The numbers below are from the second (corrected) run only** —
`probe-results.json` was overwritten in place by the corrected run, same convention as the prior
context-ceiling correction.

## Results (corrected run, `max_tokens=1600`)

### Discrimination (4 scenarios × 3 models, all values from raw JSON)

| Model | Schema-valid | Verdict-correct | Miss detail |
|---|---|---|---|
| **`qwen3-next`** | **4/4 (100%)** | **4/4 (100%)** | none |
| `gpt-oss` | 4/4 (100%) | 3/4 (75%) | `generic_template_overpromotion` → called `BLOCKED_FACT_CONFLICT` (expected `REJECT_REPAIRABLE`) |
| `Qwen2.5-VL-7B` | 4/4 (100%) | 3/4 (75%) | `missing_evidence` → called `REJECT_REPAIRABLE` (expected `BLOCKED_MISSING_EVIDENCE`) |

**`gpt-oss`'s miss, in its own words** (raw `fact_conflicts` entry): it treated the generic
candidate's vague phrase *"Effortlessly handle any spreadsheet workflow"* as an implicit claim of
universal format support, then flagged that inference as a `BLOCKED_FACT_CONFLICT` against the
pivot-table/`.xls`/`.ods` limitations. Defensible as an inference chain, but over-strict relative to
the actual text — the README never explicitly claimed `.xls`/pivot-table support, it was just vague.
This is a **false-escalation risk**: `gpt-oss` reads more aggressively into marketing vagueness than
the ground truth calls for, which for a gate deciding `BLOCKED` vs. `REJECT_REPAIRABLE` (a much
more severe outcome — `BLOCKED` implies a hard stop, not just "needs a rewrite") is the wrong
direction to be wrong in.

**`Qwen2.5-VL-7B`'s miss, in its own words**: it correctly identified and listed all 3 real
missing-evidence claims (the raw `missing_evidence[]` array is fully correct — same content
`qwen3-next` and `gpt-oss` both produced), but assigned the wrong *top-level verdict label*
(`REJECT_REPAIRABLE` instead of `BLOCKED_MISSING_EVIDENCE`) despite its own populated evidence
array implying the stricter verdict. A taxonomy-application error, not a comprehension error — it
understood the content, mismapped it to the wrong bucket.

### Long-context (well-grounded scenario, ~21-22k real prompt tokens, all 3 models)

| Model | `usage.prompt_tokens` | Schema-valid | Verdict | Needle recalled |
|---|---|---|---|---|
| `qwen3-next` | 22,152 | yes | `ACCEPT` (correct) | yes |
| `gpt-oss` | 21,006 | yes | `ACCEPT` (correct) | yes |
| `Qwen2.5-VL-7B` | 22,152 | yes | `ACCEPT` (correct) | yes |

All three handled this specific long-context payload correctly. This is real signal that context
length alone is not what separates the models on this job — the discrimination misses above happen
at ~900-1000 tokens, nowhere near any context ceiling.

### Stability (`qwen3-next` only, N=3 repeat of the long-context call, bounded per this project's
own cost-bounded-N precedent for a model already showing zero variance)

3/3 trials: schema-valid, verdict stable (`ACCEPT` all three times), needle recalled all three
times (`prompt_tokens=22,152` identical every trial — deterministic at `temperature=0`, matching
the original characterization's own observation for this model).

## Recommendation

**Route the new independent-review job to `qwen3-next`.**

Evidence: `qwen3-next` is the only model of the three tested with a clean sheet across every axis
this job actually needs — 100% schema validity, 100% verdict correctness on a real 4-way
discrimination test (including catching a genuine fact conflict, a genuine missing-evidence case,
and correctly NOT escalating a merely-generic-but-not-false README to a blocked verdict), correct
and needle-verified long-context handling at ~22k real tokens, and 3/3 stable repeats. `gpt-oss`
and `Qwen2.5-VL-7B` each made one real, distinct judgment error at ordinary (~1k token) prompt
size — not a context-length problem, a quality-judgment problem, and this job's whole purpose is
quality judgment. This also extends (does not merely repeat) this project's existing routing
discipline: prior evidence (`llm-gateway-characterization.md` L2/L3, `LLM-018`) already disqualified
`gpt-oss` from structured/instruction-critical jobs based on short, generic prompts; this run
independently reconfirms that disqualification on THIS job's actual long-context, quality-judgment
shape rather than assuming the old evidence transfers unchanged.

This recommendation is evidence, not a routing change — `env.py::JOB_MODEL_ROUTING` is intentionally
**not** touched by this taskcard (`RPOC-020`); wiring the route is `RPOC-021`/`RPOC-022`'s job once
the actual reviewer prompt/specialist exist.

## Limitations / honestly out of scope for this pass

- Single fictional product, single long-context payload size (~21-22k tokens) — not a sweep across
  payload sizes the way `llm-gateway-context-ceiling-corrected.md`'s ladder was; if the real job's
  grounding-fact + repo-excerpt payload turns out to regularly exceed ~40-70k tokens, a follow-up
  ladder specific to this job's prompt shape is warranted before full production trust, same
  caveat this project already applies to `qwen3-next`'s proven-safe ~71k ceiling (`L1′`).
- Discrimination scenarios are 1 trial each per model, not N-repeated (cost/time-bounded, same
  precedent as the original characterization's reduced-N deviation) — the two misses found
  (`gpt-oss`, `Qwen2.5-VL-7B`) are each a single observation, not yet a measured rate. Given
  `qwen3-next` is the clear recommendation regardless, a repeat-trial campaign for the two
  non-recommended models was not run — it would not change the routing decision.
- `SYSTEM_FAILURE` (the 5th verdict) was not scenario-tested — none of the 4 discrimination
  scenarios were designed to make review genuinely impossible. Worth a dedicated scenario when
  `RPOC-021`'s real prompt is authored, but not something this route-selection pass needed to
  resolve first.
- All three candidates were tested through this project's own probe harness, not through the real
  `prompts/verification/independent_readme_review.yaml` prompt (doesn't exist yet — that's
  `RPOC-021`). The verdict schema used here is a faithful reconstruction of the charter's
  description (C.4), not the final prompt text; RPOC-021/022 should re-validate against the real
  prompt once written, though no result here suggests that would change which model wins.
