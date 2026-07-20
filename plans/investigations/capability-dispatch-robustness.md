# Capability Dispatch Robustness — response to independent review (2026-07-19)

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: `tools/probe_capability_dispatch_robustness.py` — 18 live calls against the real
> `llm.professionalize.com` gateway, dispatched through the real, unmodified
> `src/readme_agent/capabilities/registry.py` + `dispatcher.py` (no mocks), targeting the real
> allow-listed `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` pilot, read-only throughout.

## Why this exists

An independent review conducted before starting Wave 3 raised two points:

1. Decision #27 (hand-rolled task-graph/dispatcher instead of LangGraph/Pydantic AI/OpenAI
   Agents SDK) is a real, reasoned deviation from this project's otherwise strong
   battle-tested-library-first pattern — and it's "exactly the newest, most complex piece of the
   system."
2. Wave 2's live proof of that dispatcher was thin: N=1 trial per capability, always a single
   tool offered, always a clean unambiguous instruction, always the routing-recommended model
   (`qwen3-next`). The review's closing warning — paraphrased — was that testing this heavily
   through mocks/fixtures and only lightly against the real LLM understates the chance the
   dispatcher misbehaves under real model variability once it's exercised for real (Wave 3+).

This investigation directly answers point 2 with more live evidence, and point 1 indirectly —
strengthening the evidence base under the newest, riskiest piece rather than reversing it without
new information (see `plans/master.md` decision #27's own text: revisable on a documented trigger,
not by default).

## What was probed, live, through the unmodified production dispatcher

| # | Dimension | Trials | Model(s) |
|---|---|---|---|
| 1 | Multi-trial consistency per capability (was N=1 in Wave 2) | 3 × 3 capabilities = 9 | `qwen3-next` |
| 2 | Full 3-tool menu, open-ended instruction (the model must *choose*, not just comply) | 3 | `qwen3-next` |
| 3 | Instruction with no good tool match (does it over-eagerly force a call?) | 3 | `qwen3-next` |
| 4 | `gpt-oss` — the **shipped engine's actual default model** (`env.DEFAULT_LLM_MODEL`), not yet tested through the production dispatcher before this | 3 | `gpt-oss` |

## Results

**18/18 live calls behaved correctly. Zero dispatch failures, zero malformed tool calls, zero
unexpected rejections.**

- **Dimension 1**: all 9 trials (`inspect_repository`, `detect_readme_gaps`, `check_install_path`
  × 3 each) returned `outcome=executed` with correct, real results matching the values already
  established in `agentic-loop-proof.md` and the Wave 2 verification pass — e.g.
  `inspect_repository` returned `readme_length_chars: 8074` on every one of its 3 trials, byte-
  identical to prior evidence. Latency 1.9–2.2s/call, consistent with L8.
- **Dimension 2**: all 3 trials chose a **valid** capability (`registry.get(name) is not None`)
  and dispatched successfully. **Observation, not a defect**: all 3 trials picked the *same*
  capability (`detect_readme_gaps`) rather than exploring the other two valid options. At
  `temperature=0.0`, greedy decoding on a vague instruction converges to one preferred answer
  every time — it does not organically diversify across a menu. Design consequence for Wave 5:
  a real planner needs situationally specific instructions per planning turn to actually exercise
  different capabilities; a generic "learn what you can" prompt will deterministically favor
  whichever capability the model ranks first, not whichever is most useful for the current gap.
- **Dimension 3**: all 3 trials **correctly called no tool** when given an instruction the
  available capabilities genuinely can't answer (a stock-price question), instead of forcing an
  irrelevant call — the over-eager-tool-use failure mode this dimension was designed to catch did
  not occur in these trials.
- **Dimension 4**: all 3 `gpt-oss` trials returned `outcome=executed` through the real
  dispatcher — confirms `llm-gateway-characterization.md` finding L6 (gpt-oss reliable for
  single-step tool calls despite unreliable freeform JSON) holds through the actual production
  code path, not just the isolated gateway probe.

Full redacted evidence: `plans/investigations/evidence/capability-dispatch-robustness/robustness-results.json`.

## What this does and does not establish

**Does establish**: the dispatcher's happy-path reliability generalizes beyond Wave 2's original
N=1 proof — 18 additional live trials across harder conditions (menu choice, no-match, a second
model) all succeeded. The two safety-relevant behaviors (correct capability selection, correct
tool-call abstention) both held under real model output, not just under my own hand-crafted
adversarial dicts (`tests/unit/test_capability_dispatcher.py`).

**Does not establish**: reliability at scale (18 calls is still a small sample — L2's own finding
that `gpt-oss` fails freeform JSON on roughly 3–4 of 10 trials is a reminder that single-digit
sample sizes can miss real failure rates); behavior under network failure, timeout, or malformed
gateway responses (not induced here — the gateway was healthy throughout); or multi-round
replanning under real failure (Wave 5's job, not reachable with today's single-dispatch,
no-supervisor architecture). If Wave 5 leans on this dispatcher for high-frequency, unattended
planning, a larger-N calibration (matching the gateway probe's own N=10 budget for suspect
models) is the natural next increment before that wave ships, not before Wave 3.

## Decision-relevant conclusion

No basis to reverse decision #27 — the newest, most complex piece of the system now has broader
live evidence behind it than it did in Wave 1/2, and nothing in this pass surfaced a dispatcher
defect. The review's underlying concern (thin live coverage) is addressed for the current scope
(3 capabilities, single-dispatch, no supervisor loop); it should be revisited again with a larger
sample once Wave 5 puts this dispatcher under real repeated/unattended use.
