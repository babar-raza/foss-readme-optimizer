# Plan Governance

`plans/master.md` is the single executable spec for this project. It always describes the
**current** intended state — never a journal of how the design got here. This file is the thin
process that keeps it that way, and it also defines how machinery artifacts (investigation
tools, evidence, reports, tags) are named and organized. It changes rarely; if you're tempted
to add a project fact here, it belongs in `master.md` instead.

## Rules

1. **One state, not a history.** `master.md` never contains "first pass / corrected again /
   deeper pass" narrative. If a decision changed, the spec shows the *current* decision only —
   the previous one is deleted from the spec body, not left alongside it for a reader to
   reconcile. The *why it changed* goes in the Changelog (last section of `master.md`), one
   terse, dated entry.
2. **Fixed section order.** New material is added *inside* the section it belongs to. New
   section types are appended only at the end of this list, never interleaved:
   `Mission → Status → Decision Ledger → Architecture → Registry & Policy Config →
   Validator Registry → LLM Contract → CI & Safety → Reference Data → Build Checklist →
   Verification Checklist → Changelog`.
   (Amended 2026-07-18: `Mission` added at the front — the business goal and division of
   responsibility the whole spec serves belongs before the engineering state, and is the one
   justified exception to append-at-end.)
3. **Surgical edits.** A new requirement is applied by editing the specific section(s) it
   affects, in place. Never append a new section that restates the whole plan with corrections
   layered on top of the old one.
4. **The Decision Ledger is append-only in numbering, revisable in content — nothing in it is
   locked.** Every entry is a *current working position*, open to revision at any stage through
   this procedure; the numbers exist for stable cross-referencing (requirements, phases,
   evidence), not to signal immutability, and are never reused. Superseding decision #6 means
   editing entry #6's text in place and adding one Changelog line — not adding a new "#18
   supersedes #6."
5. **Status and Build Checklist must be accurate at every commit.** A phase is checked off only
   when it's actually done, not when it's designed. Don't narrate — a checklist, not prose.
6. **Changelog entries are one line, and live in `logs/`, not inline.** `- [tag] **YYYY-MM-DD** —
   <what changed> — <one-clause why>.` Full design rationale for a decision lives as a short
   inline note next to that decision in the spec itself (Architecture / Decision Ledger), not in
   the Changelog. (Amended 2026-07-21: Changelog content relocated out of `master.md`/
   `requirements.md`, which had grown a combined ~2,100 lines of pure historical narrative, into
   an indexed, dated-shard `logs/` directory — see `logs/README.md` and Decision #44.)
7. **Reference Data is data, not narrative.** Empirical findings (e.g. the README audit table),
   adopted external patterns (e.g. the aspose.org reuse table) live here as tables/facts. If a
   finding changes an architectural decision, the decision moves to its proper section
   (Architecture / Decision Ledger); Reference Data keeps only the supporting evidence.
8. **Hand-rolling everything instead of using battle-tested tools is discouraged, not just for
   parsing/protocol/integration code.** Before building any new functionality, an agent MUST
   actively research, evaluate, and select an existing library, stdlib facility, framework, or a
   real reference implementation from a sibling proven system (e.g. aspose.org) that already
   solves the problem, and build on it rather than defaulting to bespoke logic. More battle-tested
   tooling in the dependency graph means less hand-rolled code to maintain and less time spent
   troubleshooting home-grown logic later — that tradeoff, not aesthetic preference, is why this
   is the default. This is a strong default, not an absolute ban: hand-rolling remains allowed in
   a special circumstance, but only as an explicit, reasoned Decision Ledger entry made at the
   same bar decisions #27/#28 already met — never a silent default choice made without that
   justification. (Rule broadened 2026-07-19, user directive — Decision #30 revised in place;
   originally scoped to parsing/protocol/integration code only.)
9. **Investigate before overwriting.** Before an agent (human or AI) overwrites, replaces,
   deletes, or discards existing content in this repository — a file, a Decision Ledger entry, a
   requirement row, an evidence artifact, uncommitted work, or git state (`checkout`/`restore`/
   `reset`/`clean`, a force-push, editing a fixture to make a test pass) — it MUST first
   investigate what is there and why: read the current content, check its recent history
   (`git log`/`git blame`), and confirm the change is safe or intended. The investigation is not
   optional ceremony; its finding drives the action. If the existing content turns out to matter,
   it is preserved, migrated, or the task pauses for user input — never silently clobbered. This
   does not create a new exception to `GOV-002`/`GOV-003` (the Decision Ledger and requirement
   rows are already never silently deleted) — it generalizes the same discipline to every
   artifact class, including ones with no dedicated anti-deletion rule of their own. (Added
   2026-07-19, user directive — see Decision #31.)
10. **Prove it in production — real conditions are the acceptance bar, not unit tests alone.** A
    requirement is not `IMPLEMENTED`, and a Build Checklist line is not checked off, on unit-test
    or mocked-fixture evidence by itself. It must also be demonstrated end-to-end against real,
    production-like conditions matched to what it claims — the real registry repos, a live
    LLM/gateway call, a real `act` reproduction of the actual CI workflow — the same bar every
    phase in this project's own Changelog has already been held to (the pilot re-proofs, the
    `RUN-003` `act` reproduction, Wave 2's live capability call through the production dispatcher).
    "Production" here means real data and real systems exercised read-only or dry-run, under this
    project's existing push-blocking and allow-list safety properties. At this stage it never
    means committing or pushing anything to the actual product repos as a side effect of proving
    a requirement — this rule does not authorize that on its own. Where no live target exists yet
    for a capability, its status stays short of `IMPLEMENTED` (`PLANNED`/`PARTIAL`/spike evidence
    only) until that proof exists. This sharpens `GOV-007`'s acceptance-evidence bar — it does not
    relax it.

    **Nothing is ever pushed to a product repo without an explicit, unambiguous confirmation of
    what/why/where.** No requirement's proof, no capability (including any future `gated_effector`),
    and no agent — human or AI — commits or pushes to a managed remote without the user's separate,
    explicit, per-instance approval. That approval must be preceded by a statement naming, with no
    room for confusion: **what** will be pushed (the exact commit/diff/content), **why** (the
    reason/purpose), and **where** (the exact repository, branch, and remote). General, implied, or
    standing consent — including consent given earlier in the same session for a different push —
    never substitutes for this; each push gets its own explicit what/why/where confirmation.
    Proving something "in production" is never itself that approval. (Added 2026-07-19, user
    directive — see Decision #33.)
11. **Each wave first reconciles the previous wave against the spec, before building on it.**
    Before a new wave's work begins, check the immediately preceding wave's actual delivered
    state — its code, tests, and evidence — against what `plans/master.md` (that wave's Decision
    Ledger entry, Status, Build Checklist line) and `plans/requirements.md` (every requirement row
    it touches) currently claim. This is not the periodic requirements review `GOV-010` already
    requires when a phase closes — it is an entry gate on the *next* wave, and it names exactly
    what must match: Decision Ledger, Status, Build Checklist, requirement rows, not "review" left
    open-ended. A status that overclaims (`IMPLEMENTED` without the evidence `GOV-007`/`GOV-018`
    require, a Build Checklist line checked off with a gap still open) is corrected — downgraded,
    or the gap logged as `BACKLOG` per `GOV-014` — before the new wave extends the affected
    surface. The new wave's own Build Checklist entry or opening session narrative records that
    this check ran and what, if anything, it found; a wave opened with no record of this check is
    incomplete, not merely undocumented. (Added 2026-07-21, user directive — see Decision #43.)
12. **`master.md` is gated, not open to routine edits.** No agent edits any section of `master.md`
    as an implicit side effect of ordinary session work. Before making any edit to it, the agent
    states — in the same turn, before the edit — which section(s) it intends to change and why,
    and proceeds only on the user's fresh, explicit go-ahead for that specific edit; a standing or
    implied yes from earlier in the session does not count, the same discipline rule 10 already
    requires for pushes. `logs/` is exempt from this gate — any agent may append to it freely,
    with no confirmation step, since absorbing frequent low-ceremony history writes is exactly
    what it exists for. `plans/requirements.md` is also unaffected — its own editing procedure
    (`GOV-004`/`GOV-005`) is unchanged; only its Changelog section moved. (Added 2026-07-21, user
    directive — see Decision #44, `GOV-023`.)

## Applying a new requirement (the actual procedure)

1. Identify which section(s) the requirement changes. If none exist yet, it's new — add it to
   the correct section per the fixed order above, don't create a new top-level section for it
   unless it's a genuinely new category of concern.
2. Edit that section's content directly to the new current truth.
3. If a ledger decision is reversed or refined, edit its entry in place.
4. Update Status / Build Checklist if the change affects what's done vs. pending.
5. Append one Changelog line.
6. Do not touch unrelated sections. A surgical edit should produce a small, reviewable diff, not
   a rewrite of the file.

## Machinery artifacts: naming and organization

These rules govern every artifact the project's machinery creates or consumes — investigation
tools, the evidence they emit, reports, control inventories, fixtures — and every name used to
refer to one: file and directory names, function names, evidence-store keys, and
cross-reference tags in reports/CSVs/manifests.

### Naming rules

1. **Every name is self-explanatory.** The name alone must state what the artifact *is* or
   *demonstrates*, in words, without opening it or consulting the tool that produced it.
   `push-block-hook-verification.json`, not `proof3.json`; `settings-drift-reconvergence`, not
   `proof2-settings`.
2. **Enumerated names are disallowed.** `proof1`, `proof2`, `S1`, `T3`, `run2`, `case-a`,
   `test4` — and anything of the same shape: a generic noun plus a sequence position — are
   banned everywhere the previous paragraph reaches (files, dirs, functions, store keys, tags).
   These are examples, not an exhaustive blocklist; the test is rule 1, and a number or letter
   suffix is never what makes a name pass it. Sequence position is not meaning: if order
   matters, it is recorded inside a manifest or report, never encoded in the name.
3. **Vague names are equally disallowed.** `temp`, `misc`, `data`, `output`, `final`, `new`,
   `old`, `backup` (and compounds like `final2`, `new-copy`) fail rule 1 the same way
   enumerations do.
4. **Defined identifiers are the one exception.** A structured ID (e.g. requirement ID
   `FACT-001`) may be used as a tag only if it is defined in exactly one canonical inventory
   file that maps it to its full description (today: `investigations/control/
   normalized-requirements-inventory.yaml`), and every use resolves there. An ID invented
   ad hoc inside a tool, report, or filename with no canonical definition is an enumerated
   name and banned by rule 2.
5. **Composite names follow the existing fixture convention**: kebab-case words;
   `__` separates org from repo, `--` separates subject from facet
   (`aspose-3d-foss__Aspose.3D-FOSS-for-Java--releases.json` pattern in
   `investigations/evidence/github-fixtures/`).

### Organization rules

6. **Fixed homes.** Investigation reports are `investigations/<topic>.md`. Tools are
   `investigations/tools/<what-it-does>.py`. Evidence is
   `investigations/evidence/<investigation-slug>/<self-explanatory-name>.<ext>`, one
   subdirectory per investigation, named after the investigation — never after the run order.
   Control data (inventories, ledgers, coverage) lives in `investigations/control/`. Project log
   shards are `logs/<YYYY-MM-DD>.md`, one per day, indexed from `logs/README.md` (see "Repository
   layout" below
   and rule 6 above).
7. **Traceability both ways.** Every evidence directory is produced by an identifiable tool and
   cited by at least one report; the report references evidence by its real filename. A rename
   is therefore always a three-way change (tool + evidence + every citing report/manifest),
   done together in one commit.
8. **No orphan artifacts.** An evidence file no report cites, or a tool whose output nothing
   consumes, is deleted — not kept "just in case." The evidence tree is an audit trail, not a
   scratch space. This rule is **not** license to keep working tools out of the repo: a
   one-shot script that transformed the repo is not an orphan — it is the executable record of
   that transformation and lives in `scripts/retrofits/` (see "Repository layout", placement
   rule 5). Orphan means *unconsumed and unreferenced*, not *no longer scheduled to run*.
9. **Retrofit on touch.** Pre-existing names that violate these rules are renamed (per rule 7,
   all references together) the next time the machinery that produces or cites them is
   otherwise modified. New artifacts comply from creation, with no grandfathering.

## Repository layout: what goes where

Binding for every agent (human or AI) that creates a file anywhere in this repository. The
repository root is a **closed set**: these directories, plus the project-level root files
(`README.md`, `AGENTS.md`, `pyproject.toml`, `.gitignore`, the `.env*`/`.secrets`/`.actrc`
examples). Nothing else appears at root.

| Location | What belongs there |
|---|---|
| `src/readme_agent/` | All production code — importable, packaged, reached via the `readme-agent` CLI. One module per responsibility, reflected in the module map in `docs/architecture.md`. |
| `tests/unit/` | Default-CI tests, offline, one `test_<module>.py` per `src` module it covers. |
| `tests/integration/` | Tests needing real network/secrets — every one carries `@pytest.mark.live`. |
| `tests/security/` | Tests that prove a safety property (secret redaction, push-blocking adjuncts). |
| `tests/fixtures/` | Committed test inputs. Real-world snapshots (e.g. `readmes/real_audit_*/`) are immutable evidence — never edited to make a test pass. |
| `scripts/` | Operator-run and agent-authored tooling, organized into self-explanatory subcategories: `scripts/<category>/<what_it_does>.py`. Today's categories: `retrofits/` (one-shot repo transformations — written here *before* running, kept afterward as the executable record of what was done); recurring maintenance utilities (registry refresh, link DB build) get a category like `data-refresh/` when next touched. Standalone; never imported by `src/`. |
| `config/policies/` | One YAML policy profile per product (`docs/policy-authoring.md`). |
| `data/` | Config-as-data JSON (registry, link database). Every file here has a section in `data/README.md` stating what it is, who/what produces it, and how it's refreshed. |
| `prompts/` | Every prompt asset used with the LLM gateway (`llm.professionalize.com`) — system/user prompt text, few-shot blocks, and structured artifacts (YAML/JSON state machines, conversation flows). Any format; names and subcategories self-explanatory per the naming rules. Loaded only by `src/readme_agent/llm/`; see `prompts/README.md`. |
| `templates/` | Every fill-and-match template — the README owned-span skeleton (resources) and any other skeleton this project fills in or matches against. Any format. Loaded only by the owning `src/` module; see `templates/README.md`. |
| `docs/` | Durable human-facing documentation of the *current* system. |
| `plans/` | The spec (`master.md`, `requirements.md`), this file, and `investigations/` (governed by "Machinery artifacts" above). |
| `logs/` | Dated historical narrative for the plan trio (`master.md`/`requirements.md`/`GOVERNANCE.md`) — index at `logs/README.md`, daily shards `logs/<YYYY-MM-DD>.md`. The one row in this table exempt from rule 12's `master.md` edit-confirmation gate — freely, immediately agent-appendable. |
| `runs/` | Disposable runtime state (clones, evidence), written only via `src/readme_agent/paths.py`. Gitignored; never committed. |
| `.github/workflows/` | CI and scheduled automation. |

### Placement rules

1. **One home per file, chosen from the table.** If a new file genuinely fits no row, amend
   this section first (one new row or one edited row, plus a Changelog line in `master.md`),
   then create the file. Never invent a directory ad hoc and leave the governance behind.
2. **Production logic lives only in `src/readme_agent/`.** A `scripts/` utility that production
   code starts to need gets moved into `src/` behind the CLI, not imported across the
   boundary. Adding a `src` module means updating the module map in `docs/architecture.md` in
   the same change.
3. **Every behavior change lands with its test in the mirrored location** — `src` module →
   `tests/unit/test_<module>.py`; needs-network → `tests/integration/` with the `live` marker;
   proves-a-safety-property → `tests/security/`.
4. **Runtime output is never committed.** Anything generated while the tool runs goes under
   `runs/` (via `paths.py`) and stays gitignored. Investigation machinery output goes under
   `plans/investigations/evidence/<investigation-slug>/` and *is* committed — that's the audit
   trail. Nothing generated ever lands at root, in `src/`, or in `tests/`.
5. **Scratch never enters the repo — and tooling never lives in scratch.** The session
   scratchpad / OS temp dir is for disposable *data* only: intermediate outputs, downloads,
   previews. Any *executable* an agent authors to act on this repo — a retrofit, a migration, a
   probe whose logic matters — is written in its repo home (`scripts/<category>/`,
   `plans/investigations/tools/`) from the first line, never in a temp path. Temp paths die
   with the session, and with them the record of what was done to the repo and how. A
   "one-shot, delete after use" script is not an exception: it runs from `scripts/retrofits/`
   and stays there afterward. If disposable *data* in scratch turns out to matter, it is
   promoted deliberately into its proper home (with a self-explanatory name), not left where
   it fell.
6. **Byproducts are gitignored in the same commit that introduces them.** A new tool that
   emits a cache/artifact (`__pycache__/`, coverage files, `.egg-info/`) adds the pattern to
   `.gitignore` alongside the tool.
7. **Docs have one home each**: how the system behaves now → `docs/`; intended state and
   decisions → `plans/master.md`; investigation findings and their evidence →
   `plans/investigations/`; data-file ownership → `data/README.md`; prompt-asset ownership →
   `prompts/README.md`; template ownership → `templates/README.md`; agent working rules →
   `AGENTS.md`. State a fact in its one home and link to it from the others — never restate
   it in two places to drift apart.
8. **Regenerable files declare their producer.** Any committed file a tool can regenerate
   (`data/*.json`, evidence manifests) must record or document what produced it (provenance
   block or `data/README.md` section), so "hand-edit or re-run the producer?" always has an
   answer.
9. **Prompt and template content is data, not code.** `prompts/` is the only home for LLM prompt
   content — system/user prompt text, few-shot blocks, structured prompt artifacts — and
   `templates/` the only home for fill-and-match template content. Neither ever exists as a
   string literal inside an executable file: not `src/`, not `scripts/`, not anywhere else a
   `.py` (or other code) file lives. "Loaded from `prompts/`/`templates/` at runtime" is the only
   allowed shape; a prompt string typed inline in a module is a governance violation the moment
   it's written, not just a style preference. Only the owning `src/` module loads them (`llm/`
   for prompts, the rendering/matching module for templates); nothing else reads these
   directories directly. Existing embedded content (the prompt text in
   `src/readme_agent/llm/prompts.py`, the span skeletons in `src/readme_agent/readme/renderer.py`)
   migrates on next substantive touch — and migration must preserve the determinism contract:
   loaded prompt/template file content joins the hash-coupled generation inputs (the same regime
   `tests/unit/test_prompt_hash_coupling.py` enforces for in-code prompts today), so a changed
   file changes the hash, never silently reuses a stale generation.

## Code organization: no monoliths

Refactoring stays cheap only while every piece is small enough to move. These rules keep the
codebase in the shape it already has (largest file: the wiring module at ~330 lines; typical
module well under 150) and are binding for all agents.

1. **One module, one responsibility.** If describing a module honestly requires "and", it gets
   split. The module map in `docs/architecture.md` is the ledger — a new responsibility is a
   new module (and a new map row), not a new region of an existing file.
2. **Extensible families are registries — one implementation per file.** The canonical
   patterns already in the tree: `validation/rules/` (one rule per file, composed by the
   ordered tuple in `validation/registry.py`) and `ecosystems/registry.py` (dispatch table;
   its own docstring: "new ecosystems are new entries, not new call sites"). Extending a
   family means adding a file plus one registry entry — never growing an `if/elif` chain,
   never fattening an existing implementation with a second variant.
3. **Orchestration wires, never implements.** `cli.py` parses, `commands.py` maps,
   `orchestrator.py` composes subsystem calls. Domain logic lives in the subsystem that owns
   it, where it can be tested and refactored in isolation. The wiring module is the only file
   permitted to be the largest; when *logic* (not wiring) accumulates there, it moves down
   into a subsystem in the same change.
4. **Depend on seams, not internals.** Cross-subsystem imports target the other module's
   public surface; `_`-prefixed helpers are private to their module. Imports flow one way:
   subsystems never import `orchestrator`/`commands`/`cli`, and no import cycles, ever.
5. **Split before you extend.** Size is a smell, not a quota: when a change would push a
   non-wiring module past roughly the current ceiling (~300 lines) or add a second concern, the
   split happens *first*, as part of that change — with the mirrored test file splitting along
   the same line (placement rule 3). "I'll split it later" is how monoliths happen; later
   never has a natural trigger.

## Capability and agentic-component lifecycle (forward governance)

Policy for the target architecture (`plans/master.md` decision #26). These are the rules the
detailed schemas (capability manifest, task/state/evidence schemas — `plans/master.md`'s sprint
Task 3.1 and Wave 2/4) must satisfy once built; this section does not define those schemas
itself, it binds what they're allowed to look like.

Applies to every capability, tool, agent role, prompt, model route, repository archetype,
ecosystem/package-manager adapter, state schema, evidence schema, permission class, and effector:

1. **Registration before use.** Nothing in this family is reachable by the runtime until it is
   registered with a typed manifest/contract. An unregistered capability is not a shortcut, it's
   a bug — the same spirit as `data/products.json`'s allow-list (decision #4) applied to
   capabilities instead of repositories.
2. **No silent duplicates.** A new capability that does roughly what an existing one does needs a
   documented reason (supersession, a genuinely different permission class, a different
   archetype it targets) — checked against the registry before it's added, the same discipline
   "Code organization: no monoliths" already applies to modules.
3. **Deprecation and migration before removal.** Nothing in this family is deleted outright; it's
   marked deprecated with a documented replacement and a migration path, mirroring how
   `plans/requirements.md`'s `DEPRECATED` status works for requirements (`GOV-003`'s spirit
   extended to runtime components).
4. **Capability-gap proposals go through independent review.** A capability generated in
   response to a detected gap is never executed unreviewed in the same production run that
   detected the gap (sprint Task 3.4) — the same author-is-not-verifier principle
   `plans/requirements.md`'s `VER-001` states for ordinary proposals.
5. **Permission classes are explicit and minimal.** Every effector declares the narrowest
   permission class it actually needs; nothing defaults to a broader class "in case it's needed
   later."
6. **State and evidence schemas are versioned.** A breaking change to a state or evidence schema
   bumps its version rather than silently reinterpreting old records — the same discipline
   `generation_schema_version` already enforces for the shipped engine's owned-span contract
   (decision #15).
7. **Specialist/agent domain boundaries are enforced structurally, never by convention alone.**
   A composition framework's per-node tool-offer scoping (e.g. LangGraph) is a request-time
   reliability/UX layer, not a security boundary — it is ordinary orchestration-code wiring that a
   graph-construction bug, a stale tool list, or a hand-authored call can silently bypass. The
   actual boundary is a dispatch-side check keyed off registered, typed data (a manifest's
   declared domain scope and a caller-supplied identity), never off which tool schemas an LLM
   happened to be shown. See `AGENTS.md` rule 13, `plans/master.md` decision #34. (Added
   2026-07-19, user directive.)
