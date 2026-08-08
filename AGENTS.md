# AGENTS.md

Guidance for AI coding agents working in this repository. Humans welcome too.

## What this project is

`readme-agent` is the target of an autonomous, capability-driven repository-presentation system
(`plans/master.md` decision #26): understand a product repository, decide which GitHub
presentation surfaces are relevant, and keep them credible and repository-specific — with the
Aspose FOSS portfolio as the first deployed profile, not the ceiling of what it addresses.

**What's actually shipped today** is the first capability surface, not the whole target system: a
deterministic engine that audits Aspose FOSS GitHub READMEs for four specific promotional elements
(license mention, `products.*.org` link, `products.*.com` link, FOSS-vs-commercial relationship
explanation) and renders a bounded fix for only what's missing — never rewriting existing
content, never pushing to a real remote. Python 3.11+, `src/` layout, hatchling build.

Read these before making non-trivial changes:

- `docs/architecture.md` — pipeline order, module map, and the *why* behind the design
  (the single owned span, `facts_hash` exclusions, persistent work clone for idempotency).
- `docs/safety-model.md` — the two named safety properties (push-blocking, allow-list).
- `docs/policy-authoring.md` — how to enable a repo or add a policy profile (config-only, no code).
- `plans/master.md` — current architecture, decisions, sequencing, and rollout; see "Spec
  governance" below.

Authority is resolved by subject: `plans/idea.md` owns product outcome and intent;
`plans/requirements.md` and its typed `plans/requirements/catalog.jsonl` own obligations and
acceptance; `plans/master.md` and `plans/decisions/catalog.jsonl` own architecture, decisions,
sequence, and rollout; `plans/GOVERNANCE.md` and this file own editing, safety, execution, and
coordination; the Level-8 mission graph is the sole active machine-readable task graph; its hashed
deferred-task catalog preserves future task records without making them executable; durable
supervisor state alone owns live claims, transitions, and runtime status. Codex plans, roadmap,
status, reports, audits, and handovers are derived guidance/evidence only.

## Setup and everyday commands

**All Python work goes through the repo-root virtualenv at `.venv/` — no exceptions.** Never
install packages into the system/global Python, never create a second venv elsewhere, and never
run bare `pip`/`pytest`/`ruff`/`mypy` that might resolve to an interpreter outside `.venv/`.
If `.venv/` is missing, recreate it with `python -m venv .venv` (Python 3.11+) and reinstall.

The unambiguous form works from any shell without activation — prefer it:

```bash
.venv/Scripts/python -m pip install -e ".[dev]"   # install with dev tools (pytest, ruff, mypy)

.venv/Scripts/python -m ruff check .              # lint
.venv/Scripts/python -m ruff format --check .     # format check (use `format .` to fix)
.venv/Scripts/python -m mypy src                  # type check (src only)
.venv/Scripts/python scripts/governance/run_full_pytest.py  # optimized complete non-live gate

.venv/Scripts/readme-agent preflight              # GitHub + LLM connectivity, fail-closed
.venv/Scripts/readme-agent run --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java --mode dry_run
```

(`Scripts/` is the Windows layout this repo uses; on Linux/macOS the same venv convention is
`.venv/bin/`.) Activating instead (`.venv\Scripts\Activate.ps1` in PowerShell,
`source .venv/Scripts/activate` in Git Bash) is fine too — then the bare commands above are safe.

## Coordinator-led execution and standing command authority

Codex remains the accountable coordinator and sole operator. The coordinator exclusively owns
shared governance/state files, integration, task transitions, commits, closure, and aggregate
evidence. Multi-agent execution is adaptive, not a required five-role ceremony. Calibration and
shared-code repair run serially; an independent non-authoring verifier remains mandatory at
acceptance. After one complete repository transaction proves isolation, repository workers may run
only on disjoint repositories and scale from two to at most three workers beside the coordinator.

Before delegation, the coordinator assigns one disjoint repository/path lease and concrete
plan-bound deliverable. A worker edits only leased non-shared paths, reports exact outputs and
focused checks, and has no closure, transition, commit, shared-state, plan, integration, or effect
authority. No two agents write the same path. Documentation/state synchronization is deterministic
by default; a documentation worker is proposal-only when semantic reconciliation is genuinely
needed. If disjoint ownership or transaction stability is unavailable, execute serially.

Create `runs/multi-agent/<task-id>/execution-plan.json` only when delegation occurs. Record each
active worker's objective, exclusive paths, focused checks, and evidence destination; do not record
inactive ceremonial roles. Overlapping leases, missing active-lane evidence, or a verifier that
authored the implementation fail closeout. Measure serial/parallel wall time, coordination, cache
contention, duplicate work, and repair rate; reduce concurrency below 1.5x gain or above 25%
coordination overhead.

Before starting a long test, proof builder, supervisor campaign, build, or workflow reproduction,
inspect repository-owned processes. The coordinator grants the top-level command lease: lane-local
focused tests run only when their resources are isolated, while the bounded complete non-live
runner and integration/proof campaigns remain serialized. Descendants remain attributable to their
owning command and terminate with it on cancellation. Production repository concurrency is
exercised only through runtime leases, deduplication, isolation, and serialized aggregation.

The user has granted standing authority to run every safe, plan-bound command available in the
current environment. Execute repository reads, network inspection, `.venv` operations, formatting,
tests, isolated Docker/`act` work at the appropriate gate, Codex-owned process management, evidence
generation, and control-repository edits/commits without asking for conversational approval. If a
command fails, diagnose it and exhaust safe in-scope alternatives. Ask only when progress genuinely
requires unavailable external authority, credentials, infrastructure, a manual UI action, or an
explicitly gated external effect. Command access does not authorize product-repository writes,
destructive history changes, secret disclosure, or deletion of non-disposable user data.

CI (`.github/workflows/ci.yml`) runs exactly: `ruff check`, `ruff format --check`, `mypy src`,
and the bounded complete non-live runner on Python 3.11/3.12/3.13. Focused pytest stays serial by
default; `scripts/governance/run_full_pytest.py` selects the complete inventory with at most four
workers, disables worker restarts, records an inventory-bound receipt, and fails on leaked local
Python/pytest/Git-credential descendants. All four gates must pass before a change is done.

## Testing conventions

- Tests live in `tests/unit/`, `tests/integration/`, `tests/security/`.
- Tests needing real network/secrets are marked `@pytest.mark.live` and are **excluded by
  default** (`addopts = "-m 'not live'"` in `pyproject.toml`). Run them explicitly with
  `pytest -m live` only when you have real credentials and intend to.
- LLM-dependent logic is tested against `llm/fixture_client.py`, not the live client. Don't add
  a test that silently requires a live LLM without the `live` marker.
- `tests/fixtures/readmes/real_audit_2026-07-17/` holds real-world README snapshots the gap
  detector was derived from — treat them as immutable evidence, not editable fixtures.
- Safety properties are *proven* by tests (e.g.
  `tests/unit/test_gitsafety.py::TestHookActuallyBlocksARealPush` does a real push against a
  local bare repo and asserts it fails). If you touch `gitsafety/`, these tests are the contract.

## Code style

- Ruff: line length 100, target py311, rules `E, F, I, UP, B`. Ruff also owns formatting.
- Type hints throughout; `mypy` runs on `src/` with `ignore_missing_imports = true`.
- Modern syntax: `X | None` over `Optional[X]`, builtin generics (`list[str]`).
- Errors are typed: raise subclasses of `ReadmeAgentError` (`src/readme_agent/errors.py`) with
  the appropriate `exit_code`; the CLI maps them to stderr + exit code centrally in `cli.py`.
- Module docstrings are one line stating responsibility; comments explain constraints, not
  mechanics. Match the existing density.
- **No monoliths** (binding rules: `plans/GOVERNANCE.md`, "Code organization"): one module per
  responsibility; extensible families grow by adding a file + one registry entry
  (`validation/rules/`, `ecosystems/registry.py` are the patterns), never an `if/elif` chain;
  orchestration wires but never implements; depend on public seams, not `_`-private helpers,
  with no upward or cyclic imports; and when a change would push a non-wiring module past
  ~300 lines or add a second concern, split first — tests split along the same line.

## Commit attribution

Every commit that includes work performed by an AI coding agent must carry a `Co-Authored-By:`
git trailer identifying that agent, appended to the commit message body (not the summary line).
Claude Code already does this automatically — visible throughout this repo's history as
`Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Codex does not add this on its own and
must add it explicitly on every commit it authors or materially contributes to:

```
Co-Authored-By: Codex <noreply@openai.com>
```

If more than one agent contributed to the same commit, include one `Co-Authored-By:` trailer per
agent, so history accurately reflects who did the work regardless of which agent's session ran
`git commit`.

## Safety invariants — never weaken these

Two named safety properties from `docs/safety-model.md`. Any change that touches them needs the
corresponding tests to still pass *and* still be meaningful:

1. **Push-blocking.** Work clones get their push remote set to `DISABLED` and a pre-push hook
   that unconditionally exits 1 (`gitsafety/neuter.py`, `gitsafety/hooks.py`).
   `verify_push_blocked()` proves both from `git remote -v` and hook contents — never by
   attempting a real push. This tool must never issue a git/GitHub write verb against a real
   remote, even though its tokens could.
2. **The allow-list.** `data/products.json` is the only list of repos the tool may touch. A repo
   missing from it is always a hard `NotAllowlistedError`, for any operation. Beyond that, the
   gate splits by intent (decision #40): read-only capabilities (`profile_repository`,
   `get_product_facts`, `detect_readme_gaps`, `classify_upstream_change`,
   `inspect_repository`/`orchestrator.inspect_repo()`, and `supervise_repo()`'s own entry gate)
   call `registry.loader.require_listed()` — `mode` is irrelevant, since `mode: "disabled"` means
   push access to that org hasn't been verified yet, not that the repo is off-limits to read.
   Anything write/push-capable calls `registry.loader.is_permitted()` /
   `orchestrator.require_permitted()` instead, which still hard-blocks on `mode: "disabled"`; a
   `local_write`/`remote_write` capability dispatched through the supervisor is independently
   re-checked against `mode == "full"` at dispatch time
   (`supervisor/loop.py::_dispatch_and_record()`), since the supervisor's own entry gate no longer
   implies it. Never add a code path that reaches the network for a repo before the check that
   matches what it's about to do with that repo.

Related non-negotiables:

- Evidence written under `runs/` goes through `evidence/redaction.py` — secrets (tokens, API
  keys) must never appear in evidence files. `tests/security/test_no_secrets_in_evidence.py`
  guards this.
- Within the legacy deterministic `generate`/`run` renderer path specifically, the LLM is called
  **only** when `relationship_explained` is a gap; every other element of that path renders
  deterministically from `config/policies/*.yml`. Don't route deterministic content through the
  LLM. **This no longer describes the system's only LLM job** — `env.py::JOB_MODEL_ROUTING` routes
  several distinct live jobs today (`relationship_explained`, `supervisor_planning`,
  `specialist_selection`, `prose_quality_check`, `repair_capability_selection`,
  `presentation_standard_compliance`, `visual_asset_accuracy`), each chosen from live-tested
  gateway behavior per `plans/investigations/llm-gateway-characterization.md`, not one fixed job.
  The narrow-LLM-surface discipline still applies per job (reach for the LLM only where judgment
  cannot be expressed as a rule), it just no longer means "exactly one job in the whole system."
- Rendered content stays inside the one owned marker span (`readme/markers.py`); the tool never
  edits content outside it.
- **Every `data/products.json` entry has equal inclusion in the dynamic denominator and evidence
  obligations.** Dependency-ready execution follows `data/platform_priorities.json`; registry file
  order and `mode` are not priority signals. The allow-list's `mode` field
  (`full`/`dry_run`/`disabled`) gates product write/push-capable access, not relevance or local
  verification. Portfolio surveys, fact gathering, policy/validator design, and live read-only
  capabilities cover the whole runtime-loaded registry. The canonical `local_poc` may produce
  revision-addressed local and control-repository artifacts for every allow-listed repository
  regardless of `mode`, while push blocking and zero-effect validation prove that no product remote
  is written. Product effects remain separately gated by `mode`, complete Gate-B acceptance,
  authorization, and the fresh what/why/where rule. See decisions #24/#40 and `PIL-011`.

## Handling issues found outside the current task

If you discover an issue, gap, or improvement opportunity that does **not** block the task you're
currently doing, log it as a new row with status `BACKLOG` (open) in `plans/requirements.md`, in
the section matching its topic — do not fix it as unrequested scope creep, and do not silently
drop it. If the issue **does** block the current task's correctness, safety, or acceptance, fix it
first, before considering the task done. See `GOV-014` (`plans/master.md` decision #29).

## Blocked means classify, then fix — not stop

A terminal `BLOCKED` supervisor outcome is acceptable as-is only when it's `infra_external`: a
genuine infrastructure or external-authority condition (an LLM/gateway outage, a legitimate
concurrent lock holder, a human-gated onboarding/authorization/mode boundary, a missing
permission). Every other `BLOCKED` — a wiring bug, a build-it gap, a planner defect, an ambiguous
dispatch failure — is `agent_fixable`: don't accept it as final, appoint an agent to triage and fix
it, and continue execution once it's resolved. `SuperviseResult`/`ConvergenceOutcome`/`Task` all
carry a `blocked_category` field for exactly this; **an unclassified block defaults to
`agent_fixable`**, never silently "understandable" by omission. See `GOV-028`
(`plans/GOVERNANCE.md` rule 13, `plans/master.md` decision #77, `AGT-009`/`AGT-010`).

## Prefer battle-tested tools over hand-rolling

Before building any new functionality, actively research, evaluate, and select an existing
library, stdlib facility, framework, or a real reference implementation from a sibling proven
system (e.g. aspose.org) that already solves the problem, and build on it — don't default to
writing bespoke logic. More battle-tested tooling means less hand-rolled code to maintain and less
time troubleshooting home-grown logic later. This is a strong default, not an absolute ban:
hand-rolling stays allowed in a special circumstance, but only behind an explicit, reasoned
Decision Ledger entry that names the proven option considered and why it wasn't used — never as a
silent default choice. See `GOV-015` (`plans/master.md` decision #30, `plans/GOVERNANCE.md`
rule 8).

## Investigate before overwriting

Before overwriting, replacing, deleting, or discarding existing content in this repository — a
file, a Decision Ledger entry, a requirement row, an evidence artifact, uncommitted work, or git
state (`checkout`/`restore`/`reset`/`clean`, a force-push, editing a fixture to make a test pass)
— read what is there and check its recent history (`git log`/`git blame`) first, and confirm the
change is safe or intended. If the existing content turns out to matter, preserve it, migrate it,
or pause and ask — never silently clobber it. See `GOV-017` (`plans/master.md` decision #31,
`plans/GOVERNANCE.md` rule 9).

## Prove it in production

A change is not done because `pytest -q` passes. Before marking a requirement `IMPLEMENTED` or
checking off a Build Checklist line, demonstrate it end-to-end against real, production-like
conditions matched to what it claims — the real registry repos, a live LLM/gateway call, a real
`act` reproduction of the actual CI workflow. Unit tests and mocked fixtures narrow what can go
wrong; they are not the acceptance bar by themselves. Real proof happens read-only or dry-run,
under the push-blocking and allow-list safety properties above. At this stage, proving something
"in production" never itself commits or pushes anything to the actual product repos — this rule
does not grant that on its own.

**Nothing gets pushed to a product repo without an explicit what/why/where confirmation.** No
requirement's proof, no capability (including any future `gated_effector`), and no agent — human or
AI — commits or pushes to a managed remote without the user's separate, explicit, per-instance
approval. Before asking for it, state unambiguously: **what** will be pushed (the exact
commit/diff/content), **why**, and **where** (exact repository, branch, remote). A standing or
implied yes from earlier in the session never substitutes — get a fresh confirmation of that exact
statement every time. See `GOV-018` (`plans/master.md` decision #33, `plans/GOVERNANCE.md`
rule 10).

## Full-registry POC scope and gate ordering

Per `plans/idea.md`'s "README POC Readiness and Ordered Delivery Gates" section and
`plans/master.md` decisions #78/#85/#88:

- **Every repo in `data/products.json` is part of the POC.** The POC is the full registry, not a
  sample of it — the count is computed at runtime (`len()` over the file's current entries), never
  hard-coded into a plan, a report, or a status claim. A result covering only some of the registry
  is a development batch or partial result and must be labeled as one, never presented as "the
  POC."
- **Trusted execution is suspended; trusted assets are preserved.**
  `trusted_readme_transform` evidence remains explicitly `README_INHERITED` and may contribute
  compatible implementation, tests, cache/retry/lease controls, workflow/staging transport, and
  lessons. Its remaining goals are non-executable and it cannot regain effect authority
  automatically. `verified_repository_presentation` is both the active path and ultimate goal.
  Trusted evidence, verdicts, and PRs never satisfy verified facts, Gate A, Gate C, or maturity.
- **The checked-in registry is not by itself proof of source completeness.** Before trusted T1 or
  verified Gate A freezes its denominator, use an organization-compliant credential and paginated
  all-visibility enumeration for every explicit authorized source. Retain public, private,
  internal, archived, unmatched, ambiguous, inaccessible, renamed, and transferred observations;
  reconcile by stable provider identity; and bind the complete `RegistryRevisionV1`. A source
  failure, stale scan, unexplained observation, or pending intake blocks completeness while
  unrelated admitted work may continue. New product repositories are admitted only as
  disabled/read-only and receive one durable preflight; every exclusion is evidence-backed and
  discovery authority never implies write authority.
- **A strong existing README uses the assurance-appropriate acceptance standard.** In trusted mode
  it may fast-path through complete README-derived fact/span accountability, deterministic
  validation, independent quality/fidelity review, empty patch, and no-op. In verified mode validate its
  inherited claims, facts, and protected content; deterministic assessment may then produce a
  byte-identical candidate and empty patch, but independent agent approval and no-op proof remain
  mandatory.
- **Verified Python is the immediate complete-platform POC.** Finish the current Aspose.3D FOSS for
  Python calibration README, then rebuild Note, qualify Page/PDF, and complete every dynamically
  admitted Python repository. Only after the Python platform closes may current .NET and Java
  vertical slices run; remaining-platform and Gate-A work follows the governed dependency and
  platform order. No product effect occurs in these local stages. Continue source-complete
  discovery and the verified Gate A/B/C sequence afterwards. For every verified entry, capture the
  current
  default-branch revision and exact README bytes, then preserve reviewable local artifacts for the
  original, verified facts, decision/operation plan, enhanced candidate, diff, deterministic
  validation, independent agentic verdict, and no-op rerun. Read-only GitHub access needed to
  obtain evidence is allowed; `local_poc` must not perform a remote write.
- **Dynamic/agentic capability selection is mandatory for the canonical local path.**
  `commands_supervision.py` forces the specialist-selection and repair-planner clients whenever
  `--execution-profile local_poc` is active; `--enable-dynamic-planning` remains an explicit
  compatibility opt-in for other profiles. Do not mistake the compatibility flag's default for
  the canonical local profile's behavior.
- **A bounded verified canary is explicit partial proof, never Gate A.** A graph-selected
  repository can run through the same fail-closed `local_poc` runtime with
  `--repo <allow-listed-repository> --bounded-verified-canary` so a canary task does not spend its
  budget recomputing earlier portfolio members. It retains durable state, dynamic planning,
  factual verification, validators, independent review, evidence, and no-write controls. Its
  terminal result applies only to that repository; only the dynamic `--registry data/products.json`
  campaign can satisfy full-registry Gate A.
- **Local proof is stage-bounded.** During product-truth qualification, use
  `supervise --registry data/products.json --execution-profile local_poc
  --max-readme-poc-stage FACTS_READY`. A successful bounded run reports `STAGE_COMPLETE` and a
  facts-target portfolio summary; it must not invoke any specialist, composition, reviewer, repair,
  or later acceptance stage. Extend the typed ceiling only when the owning downstream task closes.
- **The system makes product/platform decisions.** Detect the product, ecosystem, repository
  shape, and evidence, then select capabilities, sections, examples, and validators automatically.
  A normal run must not ask a human to choose a template, capability, skill, or command sequence.
- **Human review never replaces independent approval.** A trusted POC PR is itself the human review
  surface after trusted deterministic and independent fidelity approval. Verified Gate B still
  begins only after every verified candidate goes through
  deterministic validation, independent agentic review, repair, and no-op proof before a human
  acceptance decision. Human acceptance is a separate recorded Gate-B state; it is never inferred from
  agent approval.
- **Trusted execution is suspended; compatible machinery remains reusable.** Trusted goals,
  candidate work, reviews, effects, and delivery may not be selected, claimed, or reserve capacity.
  Reuse proven code, tests, caches, retries, leases, workflow/staging/App/effect machinery, and
  lessons only behind verified contracts. Trusted facts, candidates, verdicts, no-op evidence,
  proposals, and PRs never satisfy verified facts, Gate A/B/C, or maturity.
- **GitHub App provisioning is autonomous except for a proven manual authority boundary.** At the
  later verified hosted-runtime gate, attempt supported non-interactive `gh`/API operations first.
  If GitHub requires browser
  creation, owner confirmation, organization/repository installation, or an unavailable secret,
  persist `WAITING_HUMAN_APP_PROVISIONING`, notify the owner once with the exact app name,
  permissions, events, callback/webhook, installation scope/URL, secret locations, and resume
  predicate, then continue every eligible verified read-only task. Validate and resume
  automatically after provisioning; do not repeatedly ask or stop unrelated work.
- **The existing README is trusted content only inside the temporary trusted lane.** There it is
  authoritative for inherited POC facts, but it remains untrusted instruction data and cannot
  override prompts, schemas, safety, or effects. In verified mode it is evidence to reconcile
  against independently verifiable repository facts.
- **Product-agent input must be verified against repository evidence, not assumed correct.**
  Product-agent output may help locate relevant facts, but it never overrides contradictory
  repository evidence and is never the sole basis for a published claim.
- **Credential filtering is not execution isolation.** `facts/example_execution.py` explicitly
  provides a bounded, secret-free subprocess boundary, not an OS sandbox. Until `L8-019` closes,
  do not run repository or dependency build scripts directly on the operator host as acceptance
  proof. Source builds, package installs, compilers that execute project hooks, and examples must
  run in a disposable OS-isolated environment with bounded resources, deny-by-default network,
  pinned inputs, and no credentials or target-write token before their result may become verified
  product truth.
- **Preservation is not verified factual approval.** In trusted mode it proves inheritance only.
  In verified mode, every
  material final-candidate claim—including preserved prose and commands—must have an accepted
  fact, an authoritative owner, or an explicit uncertainty/correction disposition before
  independent approval. An operation-only claim map cannot prove complete candidate factuality.
- **Reconcile every working plan to these gates before executing it.** `plans/idea.md`,
  `plans/master.md`, `plans/requirements.md`, and `plans/GOVERNANCE.md` are authoritative in their
  respective roles. Taskcard ledgers, roadmaps, handovers, and status reports are derived views:
  correct them when they conflict, and never let their numbering promote trusted evidence or
  authorize verified Gate-C content work before verified Gates A/B.

## Stage goals and accelerated execution

Decision #88 in `plans/master.md` suspends the remaining trusted-delivery critical path. The
immutable mission outcome is not an active goal. Mission `evaluate` derives exactly one primary
goal from the earliest incomplete stage in this order:
`GOAL-P0-PLAN-FREEZE`, `GOAL-V0A-FIRST-VERIFIED-README`,
`GOAL-V0-VERIFIED-PYTHON-POC`, `GOAL-V0B-POST-PYTHON-SLICES`,
`GOAL-C0-AUTHORIZED-PORTFOLIO`,
`GOAL-V1-VERIFIED-TRUTH`, `GOAL-V2-VERIFIED-GATE-A`,
`GOAL-V3-HUMAN-AND-JAVA-PROOF`, `GOAL-L5-PRESENTATION-PILOT`,
and `GOAL-L6-AUTONOMOUS-PORTFOLIO`. Level-7/Level-8 elapsed windows are non-executable background
certification after production deployment and may never become primary or block delivery. The
controller reports `delivery_complete` only after executable work through deployable Level 6 and
`certification_complete` only after the Level-7/8 observations and audits close. Full
`mission_complete` requires both; delivery completion is never a Level-7/8 claim. The
controller also derives zero or more `concurrent_goal_ids` only for
dependency-ready, read-only, assurance-isolated work admitted by the primary capacity policy. It
advances only on current evidence, withdraws invalid concurrency, and reactivates the earliest
affected goal after regression, invalidation, or denominator growth. Only a goal with
`execution_required: true` may become primary. T0/TP/T0R/T1/T2/T3 remain inspectable but cannot be
selected. Safety, autonomy, authorization, factuality, idempotency, and evidence are always-on
acceptance invariants, not competing goals.

Always execute the durable graph-selected task and its declared contribution. A target breach
means record the first failing boundary and make the smallest permanent repair; it never
authorizes a new plan/controller, unrelated abstraction, reduced acceptance, or report-only
closure.

Within those goals, the binding platform priority is **Python, .NET, Java, C++, TypeScript, Rust,
Go**. `data/platform_priorities.json` is the fail-closed machine-readable source, and the canonical
portfolio runtime must load it rather than inherit registry file order. When multiple
representative, repair, cohort, review, publication, or rollout items are dependency-ready,
exhaust the earlier platform before the later one. Preserve valid cached work; do not redo
completed stages to manufacture historical ordering. If an earlier platform is genuinely blocked
by unavailable external authority or infrastructure, record that block and continue to the next
platform. Never skip an earlier platform because its defect is merely difficult or agent-fixable.
This priority never overrides graph dependencies, an unexpired claim, safety, the dynamic
denominator, or per-repository proof. Unknown future ecosystems follow the configured platforms
in stable registry order until the user assigns them a priority.

Portfolio reuse follows `validated source README + applicable family evidence + applicable
ecosystem evidence + repository-specific delta`. Shared evidence must be content-addressed and
repository-bound before rendering; coordinates, APIs, examples, limitations, license, workflows,
and inherited claims remain per-repository proof. Use one repository lane for the current
Aspose.3D Python end-to-end slice. After its complete lifecycle, promotion, recovery, cache, and
serialized-aggregation proof passes, the sole supervisor may use two representative and later at
most three isolated Python workers with separate leases/state/evidence and serialized aggregation.
Current .NET/Java slices follow the
complete Python platform. Follow the graph's seven-campaign mapping and one closure evidence package
per campaign. Run the pending optimized complete non-live suite on current committed HEAD before the
first slice, then at Python-platform and Gate-A closure, plus only a declared later repository-wide
gate or typed P0 exception; do not revive micro-fix evidence churn.

The completed historical small goals remain in durable state. The current executable sequence is
`DELIVERY-PY-PDF-CURRENT` → `DELIVERY-PY-PAGE-CURRENT` →
`DELIVERY-PY-NOTE-CURRENT` → `DELIVERY-PY-3D-CURRENT` →
`DELIVERY-PY-REMAINING-COHORT` → `DELIVERY-POST-PYTHON-DOTNET-JAVA`. These are typed execution
focuses on durable taskcards, not a second controller. Mission `status` prints the exact current
focus and repository scope.

Every top-level bounded verified canary MUST pass the active `--mission-task-id` and
`--mission-observer`. The runtime rejects a repository outside that task's focus, graph drift, a
missing/expired/foreign claim, or an exhausted approach budget before clone, preflight, or LLM work.
Never run a bounded canary around this guard. Nonblocking findings are recorded for later and do not
expand the current task. Once deterministic and independent acceptance plus no-op proof exist, show
the README before starting a broad suite or another repository.

One finalized repository is the first verified README, all current Python repositories are the
Python platform POC, and the full admitted registry is Gate A. Smaller numerators are partial only.
Two ineffective attempts with one approach fingerprint or
15 minutes without material narrowing prohibit another equivalent attempt. Before a third
approach, record a first-principles review and change the causal owner, pipeline boundary,
mechanism, or dependency-ready sequence. Presentation versions are immutable per transaction but
the design remains agile: a typed component delta invalidates only affected sections/facts/review;
non-critical newer presentation versions leave prior accepted READMEs valid with
`VALID_UPDATE_AVAILABLE`.

## Each wave reconciles the previous wave first

Before a material plan or route change, classify user input as goal, constraint, preference,
hypothesis, tactic, or authorization. Goals, constraints, and authorization bind; hypotheses and
tactics still require technical evaluation. Check reuse, invalidation, critical-path,
infrastructure timing, factuality, safety, and smaller alternatives. Challenge an inefficient or
conflicting tactic with evidence and a recommendation; do not ask about routine commands or
agent-fixable implementation. Two equivalent failed attempts or 15 minutes without material
narrowing prohibit another equivalent attempt and require first-principles causal and sequencing
review.

Before starting a new wave's work, check the immediately preceding wave's actual delivered state —
its code, tests, and evidence — against `plans/master.md` (that wave's Decision Ledger entry,
Status, Build Checklist line) and `plans/requirements.md` (every requirement row it touches). Don't
assume a prior Changelog entry got it right. If a status overclaims (`IMPLEMENTED` without the
evidence `GOV-007`/`GOV-018` require, a Build Checklist line checked off with a gap still open),
correct it — downgrade the status, or log the gap as `BACKLOG` per `GOV-014` — before extending the
affected surface with new-wave work. Record that this check ran (and what it found, if anything) in
the new wave's own Build Checklist entry or opening session narrative; a wave started without that
record is incomplete. This is distinct from `GOV-010`'s existing phase-close review — that reviews
the wave that just finished, this gates the one about to start. See `GOV-022`
(`plans/master.md` decision #43, `plans/GOVERNANCE.md` rule 11).

## The agentic–deterministic blend

The system is deliberately both agentic and deterministic, with a hard boundary (Decision #26
in `plans/master.md`, requirement NFR-013). Decision #26 was revised 2026-07-18 to broaden the
LLM's role from one fixed job to planning/interpretation/coordination/repair across a capability
registry — but the split itself, and every rule below, is unchanged and still binding. When
building any feature, apply the doctrine:

- **Default deterministic.** Control flow, safety gates, detection, rendering, validation, and
  anything derivable from config/facts is plain code. Reach for the LLM only where judgment
  cannot be expressed as a rule (today's shipped engine: exactly one job, the relationship
  paragraph; the target architecture broadens this to planning/coordination through the
  capability-contract model, not through ad hoc new jobs bolted onto the fixed pipeline).
- **Agentic output is a proposal or a structured `capability_action`, never a direct effect.**
  Every LLM result passes deterministic gates before it touches anything: strict schema,
  referential-integrity cross-checks, the always-run validator registry, canonical-URL
  substitution, permission-class checks.
- **Reproducibility via hashed inputs and fingerprints.** Identical facts/policy/prompt inputs
  must never re-invoke the LLM or re-trigger capability selection (idempotency); nondeterminism
  stays contained to the single generation/selection step and is recorded in evidence.
- **Keep the agentic layer swappable and empirically characterized.** Fixture client and live
  client share one contract, so the deterministic harness is provable offline; never write logic
  that only works against the live model. Route by job from live-tested gateway behavior, not
  model-name folklore — see `plans/investigations/llm-gateway-characterization.md`.
- **No human selects a capability, skill, or command during a normal run.** Capability discovery
  and selection are automatic; humans review proposals and authorize gated effects, they do not
  operate the pipeline by hand.

## Extending the runtime

Forward governance for the target architecture (decision #26). The capability registry landed in
Wave 2 (`src/readme_agent/capabilities/`: `schema.py`, `registry.py`, `dispatcher.py`) and has since
grown to 22 registered capabilities across Waves 2-8, including two real mutating ones:
`commit_readme_write` (`local_write`, Wave 7g) and `open_presentation_pr` (`remote_write`, decisions
#51-52) — the latter live-proven with a real, independently-verified, open PR against
`aspose-cells-foss/Aspose.Cells-FOSS-for-Java`. The supervisor/task graph named
in rule 3 below landed in Wave 5 (decision #36, `src/readme_agent/supervisor/`,
`readme-agent supervise --repo ...`). Per requirement `L8-002` (`plans/requirements.md`,
`IMPLEMENTED`), `supervise` is now the **sole production runtime**: `generate`, `run`, and
`run-registry` are read-only/compatibility façades routed through the same capability registry,
authorization, effect ledger, independent verifier, and terminal classifier, and must not retain
an alternate mutation path — not "additive alongside an untouched pipeline." These rules are now
current, binding guidance for new capability work, not a future contingency:

1. New functionality is exposed as a registered capability with a typed manifest (inputs,
   outputs, permissions, side-effect class), not an ad hoc function call.
2. Capabilities must be automatically discoverable by the runtime — no capability that requires a
   human to remember to invoke it by name.
3. The runtime (supervisor/task graph), not the developer, decides which capability runs for a
   given repository and goal.
4. Deterministic operations stay deterministic — a new capability defaults to a deterministic
   tool; the LLM is reached for only where judgment cannot be expressed as a rule.
5. Repository-specific `if` branches in shared runtime code are prohibited unless a documented
   standard requires them — a one-off special case belongs in registry/policy data, not code.
6. An unsupported repository pattern produces a `CapabilityGap` record with evidence; it is never
   silently skipped or ignored.
7. Capability implementations ship with tests and evidence, mirrored per "Testing conventions"
   above — same rule as every other module.
8. Investigation prototypes (`plans/investigations/tools/`) are never production capabilities —
   they inform design; production capabilities live in `src/readme_agent/` per "Repo layout."
9. All work passes through the official state, evidence, permission, and verification systems —
   no capability writes an effect outside the allow-list (#4) and push-blocking controls.
10. No completion claim is valid without independent verification — the capability that authored
    a proposal is never the sole authority accepting it (decision #26(c)).
11. Authoritative documents (`plans/master.md`, `plans/requirements.md`, this file,
    `plans/GOVERNANCE.md`) stay synchronized with what's actually built — `GOV-004`/`GOV-005`.
12. No duplicate or overlapping capability without a documented reason — check the registry
    before adding a new one that does roughly what an existing one does.
13. Specialist/multi-agent domain isolation (Wave 6-8) is enforced by `dispatcher.py`'s
    `allowed_domains`/`caller_domain` check — data-driven, registry-validated, and required
    regardless of which composition framework (LangGraph, decision #27) is in use. A framework's
    per-node tool-offer scoping reduces wrong-tool-call *rate*; it is ordinary orchestration-code
    wiring, not a sandboxed guarantee, and is **never** the security boundary itself (decision
    #34, `CAP-006`). Wave 8's `VER-001` independent-verifier guarantee depends on this directly.
14. No capability may declare `side_effect_class` at `local_write` or `remote_write` without
    `idempotency_inputs` and `retry_policy` — enforced at registry build time (decision #26
    addendum, `EFF-001`'s registration-time gate). This is a live, active gate today — both real
    mutating capabilities (`commit_readme_write`, `open_presentation_pr`) satisfy it, and it fails
    closed at import time for any future one that doesn't.

## Repo layout — what goes where

The full, binding placement rules are in `plans/GOVERNANCE.md`, "Repository layout: what goes
where". The short version every agent must follow:

- The repo root is a **closed set** — never create a new root file or directory without first
  amending that governance section.
- Production code → `src/readme_agent/` only (update the module map in `docs/architecture.md`
  when adding a module). Operator/agent tooling → `scripts/<category>/` (e.g.
  `scripts/retrofits/` for one-shot transformations), never imported by `src/`.
- Tests mirror the code: `tests/unit/test_<module>.py` offline by default; network tests →
  `tests/integration/` with the `live` marker; safety-property proofs → `tests/security/`.
- `runs/` is disposable runtime state (baseline/work clones, evidence), gitignored — never
  commit it, never hand-edit clones inside it as if they were source. Nothing generated at
  runtime lands anywhere else.
- Scratch (session scratchpad / OS temp) is for disposable *data* only. **Never write a script
  or tool to a temp path** — temp dies with the session and the work is lost. Any executable
  that acts on this repo is written in its repo home from the first line
  (`scripts/<category>/`, `plans/investigations/tools/`), and a one-shot script stays
  committed after running as the record of what it did — "delete after use" is not a thing
  here.
- `config/policies/*.yml` + `data/*.json` are the config surface. Enabling a new repo is a
  config change, not a code change — follow `docs/policy-authoring.md`. Every `data/` file has
  an ownership section in `data/README.md`; add one when adding a file.
- `logs/` holds the dated history for `plans/master.md`/`requirements.md`/`GOVERNANCE.md` — index
  at `logs/README.md`, daily shards `logs/<YYYY-MM-DD>.md`. Freely, immediately agent-appendable;
  the one place in this layout with no edit-confirmation gate.
- LLM prompt assets (any format — text, YAML/JSON state machines) → `prompts/<task>/`, loaded
  only by `src/readme_agent/llm/`. Fill-and-match templates (README spans etc.) →
  `templates/<surface>/`, loaded only by the owning module. Never author prompt/template content
  as a string literal in any executable file — not `src/`, not `scripts/`, not anywhere code
  lives; see `prompts/README.md` and `templates/README.md`, including the hash-coupling rule for
  changes.
- Adding an ecosystem beyond Maven means a new module in `ecosystems/` registered in
  `ecosystems/registry.py`.
- Secrets come from the environment (see `.env.example` for names and precedence). Never commit
  `.env` / `.secrets`, and never hardcode tokens or endpoints.

## Spec governance

`plans/master.md` owns the **current** architecture, decisions, sequence, and rollout — no
design-history narrative; that lives in `logs/` (index `logs/README.md`, daily
shards `logs/<YYYY-MM-DD>.md`), merged from `master.md`'s and `requirements.md`'s former inline
Changelogs. When a change alters a decision, edit the affected section(s) surgically, update
Status/Build Checklist if needed, and append one dated entry to `logs/`, not inline.

**`master.md` is freely editable and does not require a separate approval gate.** Update any section whenever needed to keep the plan accurate, complete, and aligned with the current work. There is no requirement to announce the intended sections or obtain fresh, edit-specific permission before proceeding. A standing session authorization is sufficient, and the push-confirmation rule does not apply to edits of `master.md`.

`logs/` is also freely editable; append relevant execution records and evidence as needed.

The full rules are defined in `plans/GOVERNANCE.md`; follow them for all edits under `plans/`, with `master.md` explicitly treated as an actively maintained planning document rather than a gated artifact.

## Naming: machinery artifacts

Every file, directory, function, store key, or cross-reference tag you create for the
machinery (investigation tools, evidence, reports, fixtures) must be self-explanatory — the
name alone states what the artifact is or demonstrates. Enumerated names (`proof1`, `proof2`,
`S1`, `run2`, `case-a`, …) and vague names (`temp`, `misc`, `final`, …) are disallowed; those
are examples, not the full list — anything that fails the self-explanatory test is out.
Structured IDs (e.g. `FACT-001`) are allowed only when defined in a canonical inventory file.
Full rules, including organization and retrofit-on-touch: `plans/GOVERNANCE.md`, "Machinery
artifacts: naming and organization".

## Version bumps

The package version lives in both `pyproject.toml` and `src/readme_agent/__about__.py`
(`__version__`, served by `readme-agent --version`). Keep them in sync.
