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
- `plans/master.md` — the single executable spec; see "Spec governance" below.

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
.venv/Scripts/python -m pytest -q                 # unit + security; live tests excluded

.venv/Scripts/readme-agent preflight              # GitHub + LLM connectivity, fail-closed
.venv/Scripts/readme-agent run --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java --mode dry_run
```

(`Scripts/` is the Windows layout this repo uses; on Linux/macOS the same venv convention is
`.venv/bin/`.) Activating instead (`.venv\Scripts\Activate.ps1` in PowerShell,
`source .venv/Scripts/activate` in Git Bash) is fine too — then the bare commands above are safe.

CI (`.github/workflows/ci.yml`) runs exactly: `ruff check`, `ruff format --check`, `mypy src`,
`pytest -q` on Python 3.11/3.12/3.13. All four must pass locally before you consider a change done.

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
- The LLM is called **only** when `relationship_explained` is a gap; every other element renders
  deterministically from `config/policies/*.yml`. Don't route deterministic content through the LLM.
- Rendered content stays inside the one owned marker span (`readme/markers.py`); the tool never
  edits content outside it.
- **Every `data/products.json` entry has equal precedence for research and development.** The
  allow-list's `mode` field (`full`/`dry_run`/`disabled`) gates *write/push-capable* access, not
  relevance — a portfolio survey, fact-gathering task, or policy/validator design MUST cover the
  whole registry (all 25 entries as of this writing), never just the enabled ones. As of decision
  #40, this is no longer just an offline-research-script carve-out: live read-only capability
  execution (`profile_repository`, `get_product_facts`, `inspect_repository`, etc., and
  `supervise_repo()` itself) runs against any registered repo regardless of mode too — `mode`
  never meant "irrelevant to look at," only "push access unverified." The exception is
  **end-to-end verification (anything that actually renders/commits)**: that's scoped to the
  three enabled Java pilots (`aspose-3d-foss`, `aspose-cells-foss`, `aspose-pdf-foss`) purely
  because they're the only `mode: "full"`/`"dry_run"` entries this tool can currently write
  through — an access constraint, not a priority signal. See `plans/master.md` decisions #24/#40
  and `PIL-011` in `plans/requirements.md`.

## Handling issues found outside the current task

If you discover an issue, gap, or improvement opportunity that does **not** block the task you're
currently doing, log it as a new row with status `BACKLOG` (open) in `plans/requirements.md`, in
the section matching its topic — do not fix it as unrequested scope creep, and do not silently
drop it. If the issue **does** block the current task's correctness, safety, or acceptance, fix it
first, before considering the task done. See `GOV-014` (`plans/master.md` decision #29).

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

## Each wave reconciles the previous wave first

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
Wave 2 (`src/readme_agent/capabilities/`: `schema.py`, `registry.py`, `dispatcher.py`, four
read-only capabilities registered, no mutating capability yet). The supervisor/task graph named
in rule 3 below landed in Wave 5 (decision #36, `src/readme_agent/supervisor/`,
`readme-agent supervise --repo ...`) — additive alongside the untouched `generate`/`run`/
`run-registry` pipeline, not a replacement for it. These rules are now current, binding guidance
for new capability work, not a future contingency:

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
    addendum, `EFF-001`'s registration-time gate). This is a no-op until the first mutating
    capability is registered; it exists so that gate can never be silently skipped later.

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

`plans/master.md` is the single executable spec and always describes the **current** intended
state — no design-history narrative; that lives in `logs/` (index `logs/README.md`, daily
shards `logs/<YYYY-MM-DD>.md`), merged from `master.md`'s and `requirements.md`'s former inline
Changelogs. When a change alters a decision, edit the affected section(s) surgically, update
Status/Build Checklist if needed, and append one dated entry to `logs/`, not inline.

**`master.md` is gated, not freely editable.** Before changing any of its sections, state which
section(s) and why, and proceed only on the user's fresh, explicit go-ahead for that specific edit
— a standing session yes doesn't count, the same discipline as the push-confirmation rule above.
`logs/` has no such gate — append to it freely. See `GOV-023` (`plans/master.md` decision #44,
`plans/GOVERNANCE.md` rule 12).

The full rules are in `plans/GOVERNANCE.md`; follow them for any edit to `plans/`.

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
