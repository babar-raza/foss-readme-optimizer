# Runtime Framework Evaluation — Wave 1

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> inputs: `llm-gateway-characterization.md` findings L1–L8 (live, this repo); live PyPI metadata
> (`pip index versions`, `pypi.org/pypi/<pkg>/json`) fetched during this investigation; WebSearch
> against each framework's current docs for custom-`base_url`/self-hosted-endpoint support.
> decision recorded: `plans/master.md` Decision Ledger entry #27.

## Question

Sprint Wave 1, Tasks 12–13: evaluate at least "existing orchestrator extended with explicit task
graph and capability dispatcher," LangGraph, Pydantic AI, and OpenAI Agents SDK, and choose one,
scored against the sprint's own Section 17 criteria.

## Candidates checked live

All three third-party frameworks were confirmed (via current docs, not assumed from training
data) to support pointing at an arbitrary OpenAI-compatible endpoint over Chat Completions —
i.e. all three *can* talk to `llm.professionalize.com`:

- **LangGraph** (`langgraph` 1.2.9, PyPI, "Production/Stable"): via `ChatOpenAI(base_url=...,
  api_key=...)` from `langchain-core`. 6 unconditional direct dependencies
  (`langchain-core`, `langgraph-checkpoint`, `langgraph-prebuilt`, `langgraph-sdk`, `pydantic`,
  `xxhash`) — but `langchain-core` itself pulls a non-trivial transitive tree.
- **Pydantic AI** (`pydantic-ai` 2.13.0, PyPI): via `OpenAIChatModel` + `OpenAIProvider(base_url=...,
  api_key=...)`; documented pattern for self-hosted vLLM. Default install is
  `pydantic-ai-slim[anthropic,cli,evals,google,logfire,mcp,openai,retries,web]` — 8 extras pulled
  in by default; a scoped install (`pydantic-ai-slim[openai]` only) would cut this materially, but
  isn't what `pip install pydantic-ai` gives you.
- **OpenAI Agents SDK** (`openai-agents` 0.18.3, PyPI, MIT): via `OpenAIChatCompletionsModel` +
  `set_default_openai_api("chat_completions")`, `OPENAI_BASE_URL`/`OPENAI_API_KEY` env vars — an
  explicitly documented escape hatch off the SDK's primary target (OpenAI's newer Responses API).
  7 unconditional direct dependencies (`openai`, `pydantic`, `requests`, `websockets`, `mcp`,
  `griffelib`, `typing-extensions`).
- **Extend the existing orchestrator**: zero new dependencies — `pydantic>=2.0` is already a
  runtime dependency (`pyproject.toml`); a task-graph/dispatcher module is new code, not a new
  package.

None of the three third-party frameworks are disqualified by gateway incompatibility — this
narrows the decision to the non-gateway criteria below, most of which are about this project's
own governance model, not the LLM layer.

## Scoring against sprint Section 17 criteria

| Criterion | Extend orchestrator | LangGraph | Pydantic AI | OpenAI Agents SDK |
|---|---|---|---|---|
| Gateway compatibility | Native (already proven, decisions #8/#26) | Confirmed via `ChatOpenAI(base_url=...)` | Confirmed via `OpenAIProvider(base_url=...)` | Confirmed, but via an explicit off-label escape hatch (Chat Completions is not its primary target) |
| Native tool calling | Direct use of L6/L7 findings — one capability per turn, either chat model | Built-in tool-calling loop, same underlying gateway behavior | Built-in tool-calling loop, same underlying gateway behavior | Built-in tool-calling loop, same underlying gateway behavior |
| Structured actions | Hand-rolled pydantic schema around the tool-call envelope (Step 3 of this wave already builds this) | LangChain structured-output/tool binding | Pydantic-native structured output (its core selling point) | Pydantic-backed tool schemas |
| Typed state | `pydantic` directly, mapped 1:1 to `ORC-001`'s state enum | LangGraph's own `StateGraph`/`TypedDict`/pydantic state — a second, foreign state model to reconcile with `ORC-001` | Agent-run state is lighter-weight, less opinionated | `Runner`/session state, OpenAI-shaped |
| Durable checkpoints | Not yet — Wave 4's own governed backend evaluation (`MEM-*`, sprint Task 6.2) | Built-in `langgraph-checkpoint` — but its schema is LangGraph's, in tension with this repo's own versioned-state-schema rule (`GOVERNANCE.md` "State and evidence schemas are versioned") and Task 6.2's requirement to evaluate the backend independently | No first-party durable checkpoint story | Session/conversation state, not repo-task-graph shaped |
| Resumability | Designed in from Wave 4, on our own schema | Inherits LangGraph's checkpoint replay model | Would need custom work anyway | Would need custom work anyway |
| Subgraphs / specialist roles | Plain function composition; Wave 5's job, small enough to hand-roll (this wave proves only one node) | Strongest native fit — this is LangGraph's core design center | Multi-agent handoffs supported, less mature graph model | Multi-agent handoffs supported (`Runner`, "agents as tools") |
| Concurrency | `asyncio` or plain sequential; GH Actions runs are already per-repo process-isolated (`SCL-*`), so heavy in-process concurrency is not the bottleneck | Native async graph execution | Native async | Native async |
| GitHub Actions suitability | Trivial — no framework install step | Fine, adds install weight per run | Fine, adds install weight per run (larger default extras) | Fine, adds install weight per run |
| Debugging | Plain Python stack traces, same experience as today's `orchestrator.py` | Own execution/tracing model, added learning curve | Lighter framework surface, closer to plain Python | `Runner` trace model |
| Evidence | Directly wired into the existing bespoke `evidence/writer.py`/redaction pipeline — no adapter needed | Needs a shim from LangGraph's trace format to this repo's evidence schema | Needs a similar shim | Needs a similar shim |
| Testability | Existing `LLMClient` Protocol / `fixture_client.py` reused as-is | Needs a fixture adapter satisfying LangChain's model interface | Needs a fixture adapter satisfying Pydantic AI's model interface | Needs a fixture adapter satisfying the SDK's model interface |
| Dependency weight | None added | Moderate (`langchain-core` transitive tree) | Moderate–heavy by default (8 extras); reducible with a scoped install | Light–moderate (7 direct, MIT) |
| Maintenance / churn risk | Fully governed by this repo's own pace | Fast-moving, has shipped breaking changes across versions historically | Fast-moving (v2.x, `pydantic-ai-slim` split is itself evidence of active churn) | Pre-1.0-feeling API surface (0.18.3), primary target (Responses API) still evolving |
| Windows dev / Linux runners | Already proven (this repo's whole test suite) | No known blocker found | No known blocker found | No known blocker found |
| Lock-in | None beyond `pydantic` (already accepted) | State model, checkpoint format, execution model all become LangGraph's | Lighter lock-in than LangGraph, still a foreign agent-run model | Ties planning/dispatch conceptually to OpenAI's agent-run shape even when talking to a different gateway |

## Decision

**Extend the existing orchestrator with an explicit task-graph/dispatcher module, built on
`pydantic` (already a dependency) — no new runtime framework.** Native tool-calling (L6/L7) is
used directly against the gateway via `requests`, the same way `llm/live_client.py` already talks
to it, rather than through a third-party agent framework's abstraction.

Reasoning, weighted:

1. **Gateway fit is now a wash, not a differentiator.** Before Step 1's live probe, native
   tool-calling reliability was the open question that could have swung this toward a
   framework built around it. L6/L7 close that question: tool-calling works well directly
   against the raw API, so a framework's main structural argument (reliable tool-calling) is
   not something this project is missing.
2. **State-schema ownership matters more here than elsewhere.** `ORC-001` already specifies the
   exact task state enum this system needs. `GOVERNANCE.md`'s capability lifecycle section
   requires versioned state/evidence schemas under this repo's own control. Adopting LangGraph's
   checkpoint format (its strongest feature) means importing a second, foreign state model that
   Wave 4's own governed backend evaluation (`MEM-*`, sprint Task 6.2) would then have to either
   fight or formally adopt — a decision that should be made on its own merits in Wave 4, not
   inherited as a side effect of a Wave 1 framework pick.
3. **Zero new dependency, full reuse of proven testing infrastructure.** `LLMClient` Protocol and
   `fixture_client.py` already give this project fixture-based, network-free tests for every LLM
   call. Any of the three frameworks needs a new adapter layer to satisfy their own model-provider
   interface before existing test patterns apply again.
4. **Matches this project's own established conventions**
   (`[[conventions-and-feedback]]`): minimal dependencies, deterministic/typed code, V1-first
   scope, reuse where compatible but redesign only the boundaries that block the mission — and the
   boundary that's actually blocked (a fixed pipeline with no replanning) is a small, well-scoped
   piece of new code, not a missing capability only a framework can supply.
5. **Revisable, not a lock-in.** Recorded as Decision Ledger entry #27 — explicitly revisitable in
   Wave 4 if hand-rolled durable checkpointing across ephemeral GitHub runners proves harder than
   expected, or in Wave 7+ if subgraph/specialist-role composition outgrows plain function
   composition. Nothing about this wave's proof script (Step 3) is framework-specific enough to
   make switching later expensive.

## What this decision does *not* do

Does not build the Wave 2 `CapabilityManifest`/registry, the Wave 5 production supervisor, or the
Wave 4 durable-state backend. It only settles *what the task-graph/dispatcher is built on* so
those later waves have a foundation to target. Step 3 of this wave proves the chosen approach
works for one loop iteration; it is a spike script in `plans/investigations/tools/`, not the
production module those later waves will build in `src/readme_agent/`.

## Addendum (2026-07-19): the Wave 7+ trigger is resolved — decision #27's own table already had

Point 5's "or in Wave 7+ if subgraph/specialist-role composition outgrows plain function
composition" trigger is no longer open. It didn't need new evaluation — the table above (row
"Subgraphs / specialist roles") already scored exactly this: "Strongest native fit — this is
LangGraph's core design center" for LangGraph, against "less mature graph model" (Pydantic AI) and
an "off-label escape hatch" gateway fit (OpenAI Agents SDK). Every other row in the table favored
extending the orchestrator; this was the one row where it lost. **Decision: LangGraph is adopted,
scoped to Wave 6-8 specialist/subgraph composition only** — Wave 5's core supervisor/task-graph is
unchanged, since none of the reasoning in points 1-4 above (typed state, zero new dependency,
evidence integration, testability) was ever about subgraph/specialist composition specifically.
Recorded as an addendum to Decision Ledger entry #27, `plans/master.md`.

**This resolves *how specialists are composed*, not *how isolation between them is enforced*** —
those are two separate questions this document's own table conflates by naming them in one row.
LangGraph's per-node tool binding is a request-time reliability/UX layer (it reduces the rate of a
specialist's LLM attempting an out-of-domain tool call) — it is ordinary orchestration-code wiring,
not a sandboxed guarantee, and a graph-construction bug or stale tool list silently bypasses it
with no error anywhere. The actual enforcement boundary is Decision #34
(`capabilities/schema.py::CapabilityManifest.allowed_domains` + `dispatcher.py`'s `caller_domain`
check), evaluated separately and independently against real proven authorization libraries (Oso,
Casbin, Cedar, OPA — all rejected on maintenance or fit grounds) before being accepted as a
hand-rolled extension. Full reasoning for both:
`plans/investigations/specialist-domain-isolation-production-readiness.md`.
