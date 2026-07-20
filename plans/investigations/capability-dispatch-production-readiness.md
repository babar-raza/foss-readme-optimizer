# Capability Dispatch Production Readiness — root-cause assessment ahead of Wave 5

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: direct source inspection of `src/readme_agent/capabilities/` (`schema.py`,
> `registry.py`, `dispatcher.py`, `inspect_repository.py`, `detect_readme_gaps.py`,
> `check_install_path.py`, `profile_repository.py`) and `llm/live_client.py`/`fixture_client.py`/
> `client.py`; full re-read of `plans/investigations/agentic-loop-proof.md`,
> `capability-dispatch-robustness.md`, `runtime-framework-evaluation.md`, and
> `llm-gateway-characterization.md`, including their cited probe scripts under
> `plans/investigations/tools/`; a full audit of every `plans/requirements.md` requirement in the
> `AGT-/CAP-/RUN-/ORC-/VER-/GAP-/MEM-/SCL-/ECO-/ONB-` ID ranges. No new live calls were made — this
> is a synthesis and design document, not a new probe.

## Why this exists

`readme-agent`'s target architecture (`plans/master.md` decision #26) is an autonomous,
capability-driven control plane meant to run repeatedly and unattended from GitHub Actions
(decision #26(f), Wave 5's supervisor). Before that supervisor is built, this document asks the
production question directly: **what, in the capability-dispatch mechanism built so far (Wave 2),
would actually break consistency across repeated real runs — and is any of it a symptom of a
deeper, structural gap rather than something a local patch fixes?**

**Framing that shapes every finding below**: `src/readme_agent/capabilities/` has **zero
production callers today** — not imported by `orchestrator.py`, `cli.py`, or `commands.py`
(confirmed by grep, no matches). Every reliability number that exists anywhere in this project's
evidence base comes from hand-run, single-session investigation probes — not production
telemetry. Everything below is therefore **preemptive hardening ahead of Wave 5**, not incident
response, and every claim is scoped to that honestly.

## Symptoms, root causes, structural weaknesses

### Symptoms (surface-level, already partly visible in existing evidence)

- At `temperature=0.0`, an open-ended capability-selection instruction converges deterministically
  on the same capability across all 3 trials rather than exploring the menu
  (`capability-dispatch-robustness.md`, dimension 2).
- `gpt-oss` returned only one of two tool calls a single prompt plausibly wanted, despite scoring
  5/5 on single-step tool calls (`llm-gateway-characterization.md` L7 — see the correction below;
  this is thinner evidence than the doc's wording implies).
- A 3-round `agentic-loop-proof.md` trial failed to converge within its round budget; its evidence
  was overwritten by a later 4-round run rather than root-caused as a distinct data point.

### Root causes

1. **Zero retry or idempotency logic exists anywhere on the tool-calling dispatch path.**
   `dispatcher.py`'s `dispatch_tool_call()` is a pure, synchronous, one-call-in/one-result-out
   function (lines 31-85) with no retry wrapper. Every call site that has ever exercised it —
   `tests/integration/test_capabilities_live.py`, and the investigation probes
   (`prove_agentic_loop.py`, `probe_capability_dispatch_robustness.py`) — issues a raw
   `requests.post(...)` with no retry logic of its own. The only retry code in this codebase,
   `llm/live_client.py`'s bounded retry (max 2, backoff, connection errors/timeouts/429/5xx only),
   belongs to the older single-paragraph `relationship_explained` job and is never reached by the
   tool-calling path. A transient network blip during dispatch today becomes a hard failure with
   no recovery — which is itself a form of "breaks consistency across reruns," not merely an
   availability nuisance: identical inputs can produce success or hard-failure purely as a
   function of network timing.
2. **No production wiring exists**, so no reliability number reflects real unattended conditions —
   concurrency, cold starts, sustained load, or a multi-repository registry run. All existing
   evidence is sequential, single-session, single-repo, single-gateway-target.
3. **Capability-selection prompt text is not governed as data.** No file exists under `prompts/`
   for capability selection; the only prompt text that has ever been used lives inline in
   throwaway investigation scripts (`prove_agentic_loop.py`, `probe_capability_dispatch_robustness.py`),
   with slightly different wording between them. This repo has an established, *working* fix for
   exactly this class of problem — see "What to preserve and reuse" below — it simply hasn't been
   applied yet to a prompt that doesn't exist in production yet.
4. **The diagnosed cause of the temp=0 convergence (greedy decoding on a vague instruction) was
   recorded as a "non-defect observation" with a proposed fix — "situationally specific per-turn
   prompts" — that was never built into any shipped code.** The finding is correct; nothing acts
   on it yet.
5. **Every sample size in the evidence base is small and narrow.** N=1 (`agentic-loop-proof.md`),
   N=3 per cell (`capability-dispatch-robustness.md`), N=5/N=10 (`llm-gateway-characterization.md`)
   — all sequential, single-session, single-repo, zero concurrency. Not enough to rule out a
   low-frequency failure mode or session-to-session drift on the gateway operator's side.
6. **Exactly-once / safe-retry effect application has zero requirement coverage.** Audited every
   requirement in the `AGT-/CAP-/RUN-/ORC-/VER-/GAP-/MEM-/SCL-/ECO-/ONB-` ranges: `MEM-002`'s
   compare-and-swap covers *concurrent conflicting writers*; `VER-003`'s fingerprint cache covers
   *repeated full-run convergence*. Neither covers a `gated_effector` capability whose effect
   partially lands before an ephemeral GitHub Actions runner dies mid-job and the job is retried.
   No `EFF-*` or equivalent ID existed before this document (confirmed by grep — zero matches for
   `EFF-`, `idempotency_inputs`, `retry_policy`, `exactly.once` in `requirements.md`).

### Structural weaknesses (deeper than root causes — not locally patchable)

1. **Reliability properties (retry, replanning, exactly-once) are currently nobody's
   responsibility.** The dispatcher is deliberately stateless — correctly, per
   `AGENTS.md`'s "orchestration wires, never implements" — but that means these properties must be
   designed once, centrally, *before* Wave 5's supervisor is built, or they will be bolted on ad
   hoc per capability as effector capabilities are added one at a time.
2. **No production-shaped regression harness exists for live dispatcher behavior.** The
   investigation probes are one-off scripts producing a markdown snapshot each time they're
   hand-run, not a scheduled, trend-tracked suite. `Phase 18`'s `golden-set-monitor.yml` (not yet
   built) already exists as a *planned* answer to exactly this gap for the old single-LLM-job
   pipeline (weekly dry-run against a real pilot, tracked in `history/run-history.jsonl`) — nothing
   equivalent is planned yet for the tool-calling path. Reuse opportunity, not a new invention.
3. **The hash-coupling/versioning model was scoped to one fixed job and has no equivalent yet for
   multi-turn, multi-prompt agentic planning.** `generation_schema_version` (decision #15) bumps on
   prompt/template changes for the renderer's owned-span contract; there's no analogous concept
   yet for "the capability-selection prompt changed."
4. **Exactly-once effect semantics is an unwritten requirement, not a missed implementation** —
   nothing can be "done" against a criterion that was never specified.

## What to preserve and reuse (evidence-backed — do not touch)

- **The deterministic/agentic split itself.** `dispatcher.py` proves, in order: parse arguments as
  JSON → registry lookup → **permission check** (line 58, keyed off `manifest.side_effect_class`,
  never off anything the LLM claims in `arguments`) → required-argument check → execute. A
  malformed or adversarial tool-call argument cannot bypass the permission gate because the gate
  never reads `arguments` at all. Proven against the real, unmodified `check_install_path`
  manifest by `tests/unit/test_capability_dispatcher.py`, not a mock. This is the single most
  important safety property in the system and it is implemented correctly today.
- **The build-once, read-only, module-level registry** (`registry.py`'s `_MANIFESTS, _EXECUTORS`,
  built once at import time from four modules including the new `profile_repository`). No mutable
  shared state, rebuilds identically on every process start — exactly right for ephemeral GitHub
  Actions runners, and the template any future state design should follow.
- **Decision #27** (no third-party agent framework, one-capability-per-turn native tool-calling).
  Nothing in this document argues for reversing it; `gpt-oss`'s parallel-call weakness, even
  properly caveated (below), if anything reinforces staying single-call-per-turn.
- **The never-trust-the-LLM's-own-claims posture** (decision #6) — capability-gap recording on an
  unknown `capability_id` extends this cleanly into the tool-calling path.
- **The just-built hash-coupled-prompt pattern in `llm/prompts.py`** (closes `GOV-016`, confirmed
  `IMPLEMENTED` during this document's own investigation): prompt text now lives in
  `prompts/relationship_explained/{system,user}.txt`, loaded via `_load_asset()`, with
  `prompt_content_hash()` folding the loaded file content into the generation hash so an edited
  prompt file forces regeneration instead of silently reusing a stale one. **This is the concrete
  pattern a future capability-selection prompt should mirror directly** — root cause 3 above no
  longer needs a new mechanism invented, only this one applied once such a prompt exists in
  production.

## Correction: the `gpt-oss` parallel-tool-calling finding is a single trial, not a reliability finding

Verified directly against the primary source: `plans/investigations/tools/probe_llm_gateway.py`,
lines 366-399. The parallel-call probe is a `for model in chat_models:` loop that sends **exactly
one** prompt per model (`PARALLEL_PROMPT`) and records whether both expected tool names appear in
that **one** response. There is no repeated-trial loop for this dimension anywhere in the script,
and `capability-dispatch-robustness.md`'s dimension 4 tested single-tool `gpt-oss` dispatch
reliability (3 trials) — not parallel calling.

`llm-gateway-characterization.md`'s L7 finding — *"Parallel tool-calling is unreliable and
model-dependent"* — is therefore written with more confidence than N=1 supports. "`gpt-oss`
returned only one of the two" means: in that single API call, the response contained 1 tool call
instead of 2. This is currently indistinguishable from a one-off sampling/routing/gateway hiccup
versus a systematic model limitation. This is a documentation-accuracy defect, corrected directly
in `llm-gateway-characterization.md`'s L7 row as part of this same change (not deferred) — see
that file's L7 entry for the corrected text.

**Why this doesn't currently endanger anything**: decision #27's one-capability-per-turn design
doesn't depend on resolving this question either way — single-call-per-turn is already proven 5/5
for *both* models (L6). No existing decision needs to change; the finding's *wording* needed
correcting, and the open question needs a properly designed follow-up (specified below) before
anything is ever built that depends on the answer.

## Design: idempotency-key ledger + permission-gated retry ("Effect Ledger")

### What "consistency across reruns" means operationally

Given the same repository state and the same policy/facts inputs, repeated pipeline invocations
must converge to the same accepted outcome, and transient infrastructure failure must never change
the final state — an effect is either safely retried to the same conclusion, or it cleanly fails
closed. Two distinct problems hide inside "add retry":

1. **Availability** (today's actual gap) — no retry anywhere on the tool-calling path. A transient
   blip causes a hard failure a retry would have fixed. This alone causes *unavailability*, not
   *inconsistency*.
2. **Idempotency** (the harder, more important problem) — once retries exist, a capability that
   isn't provably safe to repeat can apply an effect twice, apply it differently, or leave final
   state dependent on how many times a step happened to run. **This is what actually breaks
   consistency across reruns**, and solving problem 1 without solving problem 2 makes consistency
   *worse*, not better — retrying a non-idempotent effect is more dangerous than never retrying.

### The schema already reserved space for this — extend it, don't replace it

`src/readme_agent/capabilities/schema.py:87-93` — `CapabilityManifest` already declares
`cache_policy`, `idempotency_inputs: list[str]`, `retry_policy: str | None`, and
`evidence_outputs: list[str]`, with the field-population-policy docstring stating: *"Not yet
meaningful — Wave 5 owns cache/fingerprint reuse (decision #26(d)) and evidence-writing
integration; no retry policy is built beyond whatever the wrapped function already does."* This
design specifies real semantics for fields already reserved for exactly this problem — directly
extending, not duplicating, the pattern this project already uses for the renderer path
(`facts_hash`/decision #11, persistent `work_dir`/decision #12, the `idempotency` validator
rule/decision #16).

Retry/idempotency safety must key off **`side_effect_class`** (`schema.py:36-41`, the 4-value
ordered scale `read_only_local < read_only_network < local_write < remote_write`), not
`execution_type`'s `"gated_effector"` value — the actual blast radius of a capability is whatever
`side_effect_class` it declares.

### The mechanism

1. **Idempotency key** = deterministic hash of `(capability_id, canonicalized arguments,
   idempotency_inputs-selected fields, run scope)` — directly analogous to `facts_hash`: same
   inputs → same key → same decision about whether to act again. `idempotency_inputs` (already a
   field) becomes "which argument fields participate in the key," populated per capability at
   registration time — mirroring `facts_hash`'s deliberate exclusion of `gap_report` (decision
   #11): which inputs count is a documented per-case choice, never "hash everything."
2. **Two-phase apply for anything at `side_effect_class >= local_write`**: write an "intent" record
   before executing (`runs/evidence/{run_id}/effect_intents/{idempotency_key}.json`,
   `status=pending`), using the same atomic `.tmp` + `os.replace` pattern `evidence/writer.py`
   already implements. Execute. On success, atomically flip to `status=applied` with a fingerprint
   of the actual effect (e.g. commit SHA) recorded into `evidence_outputs`. On any resume, the
   dispatcher checks for an existing record **first**: `applied` → skip, return the recorded result
   (generalizes the existing `idempotency` validator rule, decision #16, from "regeneration" to
   "any effect"); `pending` after a crash → do **not** blindly re-execute.
3. **Reconciliation is the genuinely hard, unavoidable part.** A `pending` record after a crash
   cannot always be resolved from local state alone for an external system like GitHub. Each
   `gated_effector` capability's manifest must declare a cheap "does this effect already exist?"
   check (e.g. "does a commit with this exact diff already exist on this branch") as part of its
   contract. The ledger makes the *protocol* uniform; it does not make each effector's
   reconciliation check trivial to write — that is real, per-capability engineering work.
4. **Retry safety enforced by construction, not convention.** Repurpose `retry_policy`'s
   currently-`None` string into a small enum (`"auto"` / `"none"` / `"idempotent_only"`) such that
   a future retry wrapper is **structurally inert** for any capability at `side_effect_class >=
   local_write` unless it declares `retry_policy="idempotent_only"` *and* has a working
   reconciliation check. Read-only capabilities (today's only four) default to freely
   auto-retryable, since re-observing reality is safe by definition. This removes the danger of
   "retry without idempotency" by making it unrepresentable in the schema, rather than relying on
   code review to catch a future capability author forgetting to gate it.
5. **Exhausted-retry path reuses the existing gap-recording mechanism.** When backoff is
   exhausted, record a new `DispatchResult` outcome (`"exhausted_retries"`, alongside the current
   `{executed, rejected_unknown_capability, rejected_permission_denied,
   rejected_invalid_arguments, execution_error}` set) and emit a `CapabilityGap`-shaped record for
   Wave 8's verifier/human attention — reusing the never-silently-skip pattern (`CAP-003`/
   `GAP-001`) already proven for unknown-capability dispatch, instead of inventing a second
   reporting mechanism.

### Build-time constraint (decision #30, "prefer proven tools")

Before hand-building the idempotency-key ledger described above, Wave 4's own governed
state-backend evaluation (`MEM-003`) should be checked for an off-the-shelf idempotency/dedup
primitive worth reusing, consistent with decision #30. This design is deliberately backend-agnostic
(it only assumes atomic-write-and-read-back, which `evidence/writer.py` already provides locally)
so it does not pre-empt that evaluation — it specifies the *contract*, not a commitment to a
bespoke storage mechanism.

## Limit → mitigation

| Limit | Mitigation |
|---|---|
| Reliability evidence is N≤18, single-session, sequential, single-repo | Numeric calibration gate: N≥20 trials per (model, capability) pair across ≥3 separate sessions/days, promoted from a hand-run script into a `tests/integration/` `live`-marked suite so it's rerunnable identically. Wave 5 should not depend on the dispatcher for unattended planning until this suite has run green for a defined number of consecutive scheduled executions. |
| Retry without idempotency is dangerous | Solved by construction (mechanism point 4) — not accepted as residual risk. |
| A scheduled regression suite is only as useful as someone watching it | Wire the suite's result into an actual gate the production system reads (an N-of-M failure threshold flips a checked config value, or fails the scheduled workflow loudly enough to block a dependent step) — mirrors a circuit breaker, not a dashboard. |
| Gateway behavior under concurrent/sustained load is untested | A bounded local concurrency test (fire N=5 simultaneous live tool-calling requests, observe latency/error-rate/correctness degradation) requires nothing beyond what already exists (`requests` + a thread pool) — testable, belongs in the same `live`-marked suite as the calibration protocol. What remains genuinely untestable from here is the gateway operator's internal infrastructure behavior (routing, backend scaling) — a narrower residual than "concurrency is untestable." |
| `qwen3-next`'s true reliability at scale is unproven | Every real production dispatch, once wired in, should log the gateway's per-request `id` and `created` fields into evidence (already named in `llm-gateway-characterization.md` as "the best available drift signals") — turning ordinary production traffic into passive, ongoing calibration data. |
| `gpt-oss` parallel-call reliability is unknown | See correction above: N≥10 trials per model across ≥2 separate sessions before "unreliable" is asserted as a model property; carries `RESEARCH-GATED` status until run; no current decision depends on the answer. |

## What I'm not confident about

- Whether `qwen3-next`'s observed 100% success rate across every investigation dimension will hold
  at production scale — the sample is real but small. This should be read as "no evidence of a
  problem," not "proven reliable."
- Whether the gateway operator's infrastructure (`llm.professionalize.com`) has rate limits,
  session limits, or routing behavior that only surfaces under sustained/concurrent load — no
  document addresses this, and it cannot be tested from static source inspection.
- Whether a new `EFF-*` requirement group (as filed alongside this document) versus extending
  `MEM-*` is the "right" governance call — a style judgment for whoever runs the governance
  procedure, not a correctness question this document can settle.

## Related

`plans/investigations/agentic-loop-proof.md`, `capability-dispatch-robustness.md`,
`runtime-framework-evaluation.md`, `llm-gateway-characterization.md` (L7 corrected alongside this
document); `plans/master.md` decisions #6, #11, #12, #15, #16, #26, #27, #30; `plans/requirements.md`
`EFF-*` (new), `MEM-002`/`MEM-003`, `VER-003`, `GOV-016` (closed precedent for the prompt-hash-
coupling pattern).
