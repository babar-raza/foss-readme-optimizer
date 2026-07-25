# Build-vs-adopt audit: custom machinery vs. maintained libraries

Taskcard `RPOC-002`, sprint `FULL-REGISTRY-README-POC-RESET-001`. Companion to
`full-registry-readme-poc-recon.md` (`RPOC-001`). Ledger:
`plans/investigations/control/full-registry-readme-poc-taskcards.yaml`.

Scope: every area named in the sprint charter as requiring a build-vs-adopt review. Findings below
are grounded in direct reads of `pyproject.toml`, `requirements-lock.txt`, `plans/master.md`'s
Decision Ledger, and `src/` — not inference from documentation.

## Method

For each area: what's actually used today (file:line/dependency version), then a recommendation
using the sprint charter's five-way taxonomy (`KEEP_CURRENT`, `WRAP_WITH_PROVEN_LIBRARY`,
`MIGRATE_INCREMENTALLY`, `REPLACE_BEFORE_POC`, `DEFER_REPLACEMENT`), with the one-paragraph
justification the charter requires.

## 1. Agent orchestration / task graph

**Current state:** split by a documented decision, not unexamined custom code. Decision Ledger #27
(`plans/master.md`) evaluated LangGraph, Pydantic AI, and the OpenAI Agents SDK for the *core*
supervisor loop and rejected all three (state-schema ownership, zero new runtime dependency for the
part that owns durable evidence/state) — then a same-entry addendum adopted **LangGraph 1.2.9**
(locked in `requirements-lock.txt`, alongside `langgraph-checkpoint 4.1.1`, `langgraph-prebuilt
1.1.0`, `langchain-core 1.4.9`), scoped explicitly to specialist subgraph composition (Wave 6-8). 9
of 10 files under `src/readme_agent/specialists/` build a `langgraph.graph.StateGraph(DomainStateV1)`
— e.g. `readme_presentation.py`'s 601-line render→verify→commit→record graph. The core supervisor
(`supervisor/loop.py`, ~4,036 lines across 20 files in `supervisor/`) has zero LangGraph/LangChain
imports.

**Recommendation: `KEEP_CURRENT`.** This is exactly the outcome a build-vs-adopt review should
produce — a real library adopted where it fits (bounded per-specialist graphs with clear
start/end/state), custom code kept where the library's opinions (state ownership, checkpointing
model) would have fought this project's own durable-state/evidence requirements. The new independent
reviewer specialist (`RPOC-022`) should follow the same pattern (a new LangGraph node), not invent a
third orchestration layer.

## 2. Markdown parsing / document operations

**Current state:** `markdown-it-py 4.2.0` is a real, used dependency — but narrowly: only
`document_structure.py` (57 lines) uses it, for heading detection via `MarkdownIt("commonmark")`. All
actual README mutation is custom regex/span-based bounded operations (~2,268 lines across 18 files
under `readme/`: `document_renderer.py`, `markers.py`, `document_operations.py`, `document_plan.py`,
etc.). `mistune` and `marko` are present in the lockfile only as unused transitive dependencies — zero
imports anywhere in `src/`.

**Recommendation: `KEEP_CURRENT`.** The bounded-span design is a better fit for this project's
"surgical, fact-backed" requirement (`RDM-004`) than free-form AST rewriting would be — a full AST
rewrite risks losing exactly the byte-level provenance (source spans, hash-checked ownership) the
verification pipeline depends on. Revisit only if document operations grow complex enough that regex
fragility becomes a real defect source (not observed yet).

## 3. GitHub API integration

**Current state:** custom, raw `requests`. Decision #28 (`plans/master.md`) explicitly chose this
over `PyGithub`, on the record as revisable if write volume/pagination complexity grows.
`github_api/client.py` (183 lines, read-only, custom pagination + dual rate-limit handling) and
`github_api/write_client.py` (76 lines, write verbs, deliberately isolated for authorization
boundaries) are the only two call sites. Repo cloning shells out to the real `git` binary
(`gitsafety/clone.py`) — no GitPython/pygit2.

**Recommendation: `KEEP_CURRENT`.** Already a documented decision with a stated revisit trigger that
hasn't fired. The read/write client split is itself a security-relevant design choice
(`AUTH-004`-adjacent credential isolation) that a generic library wrapper would need to preserve
explicitly anyway — adopting `PyGithub` now would mean re-deriving that isolation inside a
third-party abstraction, not simplifying anything.

## 4. Retry / HTTP resilience

**Current state:** `tenacity 9.1.4` underneath a real custom policy layer (`retry.py`, 185 lines):
`RetryPolicyV1` (pydantic), a per-operation-class policy table (`github_read`, `llm_call`,
`state_cas`, `clone`, `package_registry`, `github_write`), and GitHub-specific `Retry-After`/
`X-RateLimit-Reset` disambiguation, all wrapping tenacity's `Retrying`/`stop_after_attempt`/
`wait_random_exponential` rather than reimplementing them.

**Recommendation: `KEEP_CURRENT`.** This is the charter's own §9.2 selection rule in its clearest
form: a proven library doing the generic retry mechanics, custom code adding only the
domain-specific policy. Nothing to change.

## 5. Structured LLM output / tool-calling

**Current state:** fully custom, no library. `LiveLLMClient.generate()` (`llm/live_client.py`, 122
lines) does raw `requests.post` against an OpenAI-Chat-Completions-shaped endpoint, manually strips an
optional ` ```json ` fence with a regex, `json.loads()`s the result, then validates against a pydantic
model — catching `ValidationError` and converting to `LLMError`. No `instructor`/`pydantic-ai`/
`outlines` anywhere in dependencies or `src/`.

**Recommendation: `WRAP_WITH_PROVEN_LIBRARY` — but scoped to new work, not a retrofit.** The two new
LLM jobs this sprint adds (`RPOC-020`'s independent reviewer, `RPOC-033`'s fact drafter) are
meaningfully more complex structured-output tasks than the existing single-paragraph
`relationship_explained` job — multi-field drafts with citations, or a 5-way verdict with structured
rejection reasons. A structured-output library (e.g. `instructor`) would reduce brittle-parsing
failure modes (a malformed fence, a truncated JSON object) for exactly these two new jobs. Do **not**
retrofit the existing single-paragraph job — low complexity, working today, no defect history cited
anywhere in `plans/requirements.md` or `logs/`. If adopted, scope it to the two new call sites only;
re-evaluate broader adoption after they're proven.

## 6. State / checkpointing

**Current state:** fully custom, git + content-addressed storage (~2,752 lines across 16 files under
`state/`). `langgraph-checkpoint` is present only as an unused transitive dependency of `langgraph` —
zero references to `langgraph.checkpoint`/`MemorySaver` anywhere in `src/`; the specialist
`StateGraph`s run with no checkpointer supplied.

**Recommendation: `KEEP_CURRENT`.** The durable-state-via-git design is load-bearing for this
project's audit/evidence requirements (every state transition is a real git object, inspectable by
any standard tool, durable across process restarts without a database dependency) in a way a generic
in-memory or file-based checkpointer wouldn't replace without reintroducing the exact evidence-gap
problem this design was built to close. No defect or maintenance-burden evidence anywhere in this
project's history suggests otherwise.

## 7. Observability / tracing

**Current state:** none wired in. `langsmith` and `opentelemetry`-family packages are absent from
direct dependencies (langsmith exists only as a transitive `langchain-core` dependency); no
`LANGCHAIN_TRACING_V2`/`LANGSMITH_*`/OTel env vars or imports anywhere in the repo. All observability
today is custom structured JSON evidence (`RunManifestV3`, `supervisor/evidence.py`), not distributed
tracing (no spans/exporters/collectors).

**Recommendation: `DEFER_REPLACEMENT`.** Real tracing matters more once Wave 2's restartable Actions
runtime and the eventual 30/90-day production windows are live and need cross-run/cross-service
correlation — not a Gate A (local-proof) requirement. Revisit at Wave 2, not in this sprint.

## Summary table

| Area | Recommendation |
|---|---|
| Agent orchestration | `KEEP_CURRENT` |
| Markdown parsing | `KEEP_CURRENT` |
| GitHub API | `KEEP_CURRENT` |
| Retry/HTTP | `KEEP_CURRENT` |
| Structured LLM output | `WRAP_WITH_PROVEN_LIBRARY` (new call sites only: `RPOC-020`/`RPOC-033`) |
| State/checkpointing | `KEEP_CURRENT` |
| Observability | `DEFER_REPLACEMENT` (revisit at Wave 2) |

**Net effect on this sprint's plan:** no taskcard in Part B of the execution plan needs to change.
Every area already reviewed lands on keeping the current design; the one actionable recommendation
(structured-output library for the two new LLM jobs) is additive scope inside `RPOC-021`/`RPOC-033`,
not a prerequisite blocking them — noted there for whoever executes those taskcards, not required
before Phase 2 can start.
