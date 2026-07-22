# foss-readme-optimizer — Master Plan

Governed by `plans/GOVERNANCE.md`. This file is the current execution plan and decision ledger —
not a history of how it was written. Nothing in it is locked at this stage: every decision is a
current working position, revisable through the governance procedure (edit in place + one dated
`logs/` entry). See `logs/README.md` for the record of how decisions evolved. **Editing this file
requires the GOVERNANCE.md rule 12 gate**: state which section(s) you intend to change and why,
and get the user's fresh, explicit go-ahead before the edit — `logs/` itself and
`plans/requirements.md` are unaffected.

**Normative requirements:** [`plans/requirements.md`](requirements.md) is the authoritative,
complete register of what the system must do, must not do, and how each requirement is accepted.
This master plan defines why, architecture direction, sequencing, current status, and rollout.
Both documents must be updated together whenever scope, obligations, ownership, or acceptance
criteria change (decision #25).

## Mission

Source: "GitHub Readme Agent – 2026.07.17" and its
2026-07-18 follow-up comments. Owner: Babar Raza.

- **Outcome hierarchy: credibility first, referral value second.** The business goal remains
  consistent, measurable traffic from github.com to aspose.org and aspose.com, but traffic is not
  pursued by placing promotional links before the product has earned attention. The repository
  must first help an external developer understand and trust the FOSS product. Relevant Aspose
  links then provide context, support, and a commercial path without dominating the page.
  **Initial success metric: ≥ 10 visitors per week from github.com to aspose.org**, measured via
  the weekly "aspose.org Top 50 Sources" report and the
  `utm_campaign=foss-readme-optimizer` tag on eligible links. Phase 20 must test whether this
  target is realistic and define the coverage and timing needed to reach it (decision #20).
- **Product first, promotion second** (2026-07-18 sponsor guidance): a visitor should quickly
  understand what the library does, which problem it solves, what it supports, how to install and
  use it, and whether it is maintained. Aspose.org, Aspose.com, and commercial-product links must
  appear only where they add useful context. n8n, other leading FOSS repositories, and Aspose's
  strongest nuget.org pages are quality references to study, not layouts or templates to copy.
- **The GitHub page is not one fully editable "profile."** The plan distinguishes repository
  files, API/settings-managed fields, manual UI-only settings, product-agent-owned publishing
  surfaces, and GitHub-generated information. The agent must never claim direct control over
  contributors, language percentages, stars, forks, activity, or GitHub's layout. It may only
  audit those surfaces and investigate unexpected results (decisions #19 and #23).
- **Central repository-presentation agent, not a generic README rewriter.** Individual product
  agents remain the authoritative source for features, supported formats, installation,
  APIs, examples, packages, and release changes. The central agent improves how verified facts
  are presented, manages the presentation surfaces it is authorized to manage, audits the rest,
  and protects strong content from later automated regressions (decisions #18, #21, and #22).
- **Target architecture: an autonomous, capability-driven GitHub-runner system** (2026-07-18
  sponsor directive, `AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001`), not a fixed deterministic
  script or a manually-operated skills system. The mission is understanding heterogeneous product
  repositories — starting with the Aspose FOSS portfolio as the first deployed profile, not the
  ceiling of what the engine can address — dynamically selecting registered capabilities,
  coordinating specialized analysis and execution, and maintaining credible, repository-specific
  presentation across every authorized GitHub surface, running primarily from GitHub Actions with
  no human selecting a prompt, skill, command, or next action during a normal run. The Phase 0–21
  engine described in Status/Architecture below is the current, proven implementation and the
  first capability surface this target runtime will wrap — see Decision #26 for the precise
  architectural doctrine this supersedes and what is preserved.
- **Per-repository tailoring.** Each repository is improved for its own product, audience,
  maturity, ecosystem, and capabilities. Shared standards define quality and safety; they do not
  force one common README structure or prose template. However, for consistent branding and presentation, we have to follow some set of layouts.
- **Pilot first.** Apply the new standard to the three existing engineering pilots as a small,
  varied group: blank-slate, partial-gap, and already-populated cases. Scale beyond them only
  after the product-first presentation, ownership boundaries, safety gates, and measurement
  approach are independently verified (decision #24).

## Status

**Phases 0–15 done**, committed locally (commit `4adbaaf`), proven live against the real repos:
173 tests passing (unit + `@pytest.mark.live` integration + security), ruff/mypy clean.
`readme-agent run` has actually been executed against `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`
(real LLM call, real local commit, push blocked, idempotent on rerun),
`aspose-3d-foss/Aspose.3D-FOSS-for-Java` (correctly zero-touched), and
`aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` (deterministic one-line fix, zero LLM calls), plus
`run-registry` and the allow-list block proof.

**2026-07-18 re-scope and control-boundary correction**: the sponsor's follow-up guidance
retires the callout-after-H1 placement shipped in Phases 0–15 and expands the goal from closing
four README link gaps to improving credible product presentation across the controllable parts of
a GitHub repository. Today's follow-up discussion also corrects an important overreach: the agent
cannot design or populate every element visible on GitHub. README and community files are
repository content; description, homepage, and topics are API/settings-managed; the social
preview is a separate manual UI setting unless GitHub adds a documented API; releases and
packages remain product-agent-owned; contributors, languages, activity, stars, and forks are
GitHub-generated and audit-only.

The shipped engine core — allow-list, git safety, deterministic inspection, gap detection,
validation, evidence, redaction, and idempotency — remains valid and is preserved. Its current
four-element README policy is retained as proven Phase 0–15 functionality, but it is no longer the
definition of a professional repository. Phase 21 (21a–21d) has retired the promotional callout,
added a product-first README presentation report, and added two hard validator gates
(`product_first_opening`, `commercial_mention_discipline`) implementing decision #9. Because
nothing has been pushed, the retired callout existed only in local work clones; the orchestrator
now migrates any already-materialized callout span away on its next run. The section-aware change
plan that preserves product-specific facts while improving in-section wording (21e) remains a
proposal-only design, not yet built — see Build Checklist. The Aspose.3D FOSS for Python README
discussed by the sponsor was produced by lexchou's bot, not this agent, and remains evidence of why
a central quality standard is needed — not an example of that standard.

**Not yet done** — see Build Checklist for the full list: `act` local CI simulation (Phase 16),
adversarial review (Phase 17), durability controls (Phase 18), insertion corpus (Phase 19),
traffic homework and the product-facts schema freeze (Phase 20 — presentation standard and
GitHub control mapping are now delivered, see Reference Data), the section-aware change plan
(Phase 21e — 21a–21d are done, see above), API-managed fields and audits (Phase 22), community
files (Phase 23), README and social-preview visuals (Phase 24), publishing integration and drift
protection (Phase 25), pilot evaluation before wider rollout (Phase 26), and sprint Waves 3–9
(see below).

[`plans/requirements.md`](requirements.md) is the normative requirements companion to this
file. `docs/architecture.md`, `docs/safety-model.md`, `docs/policy-authoring.md`,
`docs/presentation-standard.md`, and `docs/github-surface-control.md` are implementation-level
companions. The requirements document defines **what** is required, this master plan defines
**why and when**, and the implementation documents define **how**. They must remain mutually
consistent.

**2026-07-18 — sprint reset** (`AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001`, sponsor directive):
narrow README-phrase-rule and single-ecosystem feature expansion is superseded by the Wave-based
capability track below, not merely paused — Wave 0's doc repair (this plan trio + `AGENTS.md`
corrected to the autonomous-capability-driven doctrine) is done, so that prerequisite is satisfied
and the Wave track is the active track going forward. See Decision #26 for the corrected
architecture doctrine. This governed plan trio and `AGENTS.md` already existed (in progress,
uncommitted) before this reset; nothing here was rebuilt from scratch. No "select a
skill/command" requirement exists anywhere in this repo to remove.
`plans/investigations/llm-gateway-characterization.md` already empirically characterizes
`llm.professionalize.com` (model inventory, context limits, structured-output reliability,
model-routing recommendation) — folded into Decision #26 below rather than redone.

**Sprint waves: 5 of 9 done** (Waves 0–5; see Build Checklist's "Sprint waves" subsection for
per-wave detail and Decisions #26–36 for the governing architecture choices). **Wave 6 is done**:
rescoped (decision #37: "product agent" is an organizational label, not a real cooperating system --
no handoff schema is built; Wave 6 is now "upstream-change watch and reconciliation"), its
prerequisite correctness fix built and unit-proven (decision #38: `orchestrator.generate_repo()`'s
durable-skip fast path was permanently blind to real upstream README changes on the actual production
runner topology -- root-caused and fixed, sequenced standalone ahead of Wave 6's own feature work per
user directive), and its remaining feature work built and **live-proven against real pilots**
(decision #39: `get_product_facts`/`classify_upstream_change` capabilities, the `readme_reconciliation`
LangGraph specialist, the specialist registry, `supervisor.loop.supervise_repo()`'s new registry-driven
convergence tier, the first CI entry point for `supervise`). Unlike the committed Phase 0–15 baseline,
this sprint work — plus the Phase 18/20/21a–21d work above — sits **uncommitted** in the working tree;
the last real commit is still `4adbaaf`. Current verified baseline (2026-07-19, after decision #39):
`pytest -q` → 437 passed (up from 396 before decisions #38/#39), 15 deselected (`live` — Wave 5's
`test_effect_ledger_live.py`/`test_supervisor_live.py` have run for real with explicit confirmation,
per `GOVERNANCE.md` rule 10, and pass (4/4: pending→applied, crash-between-
pending-and-applied-survives-a-fresh-backend-instance, real multi-round `pdf/java` convergence,
real durable zero-planning-call second call); like every other `live`-marked test from prior
waves, they stay excluded from default `pytest -q`. Rediscovered the documented `OPS-009` local
push-credential prerequisite mid-run for the third time this project (`git push` hangs silently and
indefinitely without it) — caught within minutes this time, not an hour, since the fix is now a
one-line reflex, not a fresh diagnosis; `ruff check .`, `ruff format --check .`, and `mypy src` all
clean; `act workflow_dispatch -W .github/workflows/readme-agent-run.yml` has run for real too (`Job
succeeded`, Wave 4). **decision #39's real-gateway live proof, 2026-07-19**: `readme-agent supervise
--repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java --durable-state` run for real (with the `OPS-009`
credential workaround, removed immediately after) — a real gateway planner dispatched
`inspect_repository` -> `detect_readme_gaps` -> `get_product_facts` and correctly stopped once every
gap and product fact was known; the `readme_reconciliation` specialist ran first (as designed, before
the planner loop), recording a real `DomainStateV1(accepted_status="FIRST_OBSERVATION")` entry
alongside a real `SupervisorStateV1` write in the *same* durable record — confirmed by reading the
record back, proving decision #38's multi-producer coexistence fix under a genuine second producer,
not just a fake backend. An immediate rerun correctly short-circuited via the coarse tier with zero
planning calls. `readme-agent-supervise.yml`'s own `act workflow_dispatch` reproduction also ran for
real (against the now-converged `cells/java` state) — `Job succeeded`. Nothing was pushed to either
target repo (`aspose-pdf-foss`/`aspose-cells-foss`) at any point — only to this project's own
`refs/readme-agent-state/...` ref, per the user's explicit instruction.

**Updated baseline (2026-07-20, after decision #40)**: `pytest -q` → 451 passed (up from 437),
15 deselected (`live`, unchanged); `ruff check .`, `ruff format --check .`, `mypy src` all clean.
See the Changelog's matching 2026-07-20 entry for what changed (mode-gate split, the
`aspose-page-foss` profiling-latency fix, and the `GOV-014` compliance sweep).

**Wave 7 (7a-7h) closed in full on 2026-07-20** (see the Changelog's own tail for the full,
sub-wave-by-sub-wave record, ending in a consolidated final live-proof pass) -- `CAP-006`/
`MEM-004` reached `IMPLEMENTED`, `AGT-005` reached `PARTIAL` with substantially extended evidence.
**Sprint waves: Wave 8 closed in full on 2026-07-21** (decision #42, 8a-8e; see the Changelog's own
tail for the full record). Two immediate corrections landed first (an unconditional `org_repo`
override closing a planner-trust gap in `supervisor/loop.py`, and a `--local` git identity set on
every work clone, closing a real gap where no shipped CI workflow configures one), then Wave
8a-8d -- see decision #42 for the full design (including the two independent-review passes that
corrected the first-round design before any of it shipped). **8e's live-proof pass closed for
real, 2026-07-21**: a direct before/after comparison of the verify gate against a real pilot
(`aspose-cells-foss/...Java`, both accept and reject paths, including a real local git commit,
never pushed), plus the explicit "full `data/products.json` pilot" ask -- all 25 registry entries
run through `supervise --durable-state` in a single verified-clean pass, all reaching
`CONVERGED_NO_CHANGE`, the 3 non-`disabled` entries each recording all 9 real domains with zero
collision. `VER-001`/`VER-002` → `IMPLEMENTED`. A real `disabled_mode` failure-escalation
carve-out gap was found live during this pass and fixed (`state/domain_state.py`); a new `BACKLOG`
row (`VER-004`, durable-skip masking stale compliance) and `VER-005` (the coarse shortcut's
blindness to partial per-domain recording failure) were found and logged, not fixed, out of scope
for this pass. Getting a trustworthy full-registry result took three attempts -- a push-URL
misconfiguration on this project's own repo and a `TaskStop`-didn't-kill-the-child-process race
between two concurrent instances, both found and fixed rather than hidden -- see the matching
Changelog entries for the full, honest record. `pytest -q` → 622 passed, 16 deselected (`live`,
unchanged) as of 2026-07-21's close; `ruff check .`, `ruff format --check .`, `mypy src` all clean.

**Wave-entry reconciliation gate adopted (decision #43)**, and the Changelog relocated to `logs/`
with `master.md` gated behind explicit per-instance edit confirmation (decision #44) -- both now
binding process, not narrated further here per rule 6. **Production-hardening reconciliation for
the autonomous supervisor loop (decision #45, 2026-07-21)**: an external review named seven
previously-unlogged LLM-gateway-usage gaps; reconciled and corrected a real measurement-script bug
(the "~96k-token" context-ceiling claim was invalid; the real, live-proven ceiling is ~71,069
tokens). A corrected ten-part hardening design was recorded, but **remains entirely `BACKLOG`/
`PARTIAL`, not built** -- decision #45 was a docs-only pass, and its own wave-sequencing
recommendation (a new foundational sub-wave prepended to Wave 9, renumbering `9a`-`9f` to `9b`-`9g`)
has not been actioned; Wave 9's own detailed design lives outside this repository.

**2026-07-22 -- master-plan structural-integrity incident and formal anchoring of the full-project
truth audit (decision #46)**. A concurrent agent session appended ten foreign, misplaced sections
to this file without the decision-#44 edit-confirmation gate; triaged and removed (four claims
were already tracked, one was factually wrong). A mechanical backstop replaces the prose-only rule
going forward: `scripts/governance/validate_plan_structure.py`, wired as both a local pre-commit
hook and a required CI step, checking `master.md`'s section order, `requirements.md`'s row
validity, `logs/` index consistency, and specialist/module-map completeness -- `GOV-009` moves
toward `IMPLEMENTED` once both mechanisms are proven running (see Build Checklist). Separately, an
independent "full-project truth audit" the same day
(`plans/investigations/full-project-truth-audit-2026-07-22.md`) delivered this project's most
thorough external verdict to date: **`NOT PRESENTABLE`**, a Level-3 proof-of-concept (scores:
overall 3/8, presentation intelligence 3/8, autonomous runtime 3/8, reliability 2/8, pilot
readiness 2/8, production readiness 1/8). It independently confirmed, by different means, several
of this project's own known gaps (a fresh, clean `pytest -q` run -- re-verified again just now,
directly, at **834 passed, 18 deselected**, superseding every earlier count in this section -- and
live `gh api` confirmation that the acting identity has `push=true`/`admin=true` on all three
enabled pilot repositories, resolving the previously-open fork-vs-direct-branch question in favor
of direct branch/PR access) and named genuinely new gaps this project had not yet logged: no
`remote_write`/PR-lifecycle capability exists at all (`PIL-014`); durable state failure is
currently best-effort, not fail-closed (`RUN-005`); no durable, deduplicating trigger-intake queue
exists (`RUN-006`); no health/backlog observability surface exists (`RUN-007`); the three enabled
pilots are all Java, so "heterogeneous" would currently be a false claim about them (`PIL-012`);
and no committed, independently-reproducible three-repository acceptance bundle exists (`PIL-013`).
**This project adopts that audit's drastic-action recommendation as its current position**: freeze
new specialist/domain abstractions until `AUD-001`-`007` close; retain the registry, safety model,
state/CAS primitives, deterministic rendering, validators, and supervisor (all independently
confirmed sound); use `supervise` as the sole pilot path and label `run` compatibility-only for the
duration of the pilot, without deleting or rewriting either path until parity/migration evidence
exists; replace closure-by-unit-test with a real `PIL-013` lifecycle bundle as the pilot acceptance
bar. **Wave 9 has not started.**

**2026-07-22, same-day follow-up (decisions #47, #48)**: a third concurrent session shipped a real,
tested supervise-time registry drift self-heal (`CORE-033`, decision #47). Separately, this
project's own Phase 13 machinery-audit findings (F3, F4) were closed: the effect-ledger lock now
revalidates holder identity before its terminal write (`EFF-005`, decision #48), and the verifier-
accept gate moved from a plain string comparison to a re-derivable token
(`commit_readme_write.py::precheck()`, also decision #48) — both proven by new tests, not just
argued fixed. `pytest -q` → 851 passed, 3 failed (unrelated to this work -- see below), 18
deselected. `ruff check .`, `ruff format --check .`, `mypy src` all clean. **A separate, fourth
concurrent session broadened `data/products.json` from 3 to 25 non-`disabled` entries** (still only
2 `mode: "full"` -- the original 3-pilot write/dry-run boundary is unchanged); 3 pre-existing
`test_registry_loader.py` tests hardcoding "exactly 3 enabled" broke as a result. **User confirmed
2026-07-22 the broadening is intentional** (consistent with decision #24/`PIL-011`'s existing
"research/dev scope is the full registry" position) -- the 3 tests were rewritten to assert the
real invariant (enabled == every non-`disabled` entry, computed fresh from the file) instead of a
point-in-time count, so they cannot drift out of sync the next time the registry legitimately grows
again; the original 3-pilot subset is still asserted as a floor. Full suite re-verified green after
the fix: `pytest -q` → 867 passed, 18 deselected, 0 failed (557s).

**2026-07-22, same-day continuation (decisions #49, #50)**: a concurrent session's registry-
onboarding push (`ONB-004`, `scaffold-policy` CLI) and clone-reliability redesign (`SCL-009`,
probe-validated `clone_baseline()`) landed alongside this session's own plan-file-hardening
execution — `GOV-022`'s mechanical wave-reconciliation check, `VER-001`'s replay-closing nonce
(`TC-28`), `SCL-006`'s bounded specialist retry (`TC-19`), `AGT-006`'s deterministic termination
backstop (`TC-18`), the pre-commit hook now also gating on ruff/mypy (`TC-30`), and TC-01's
remaining push to `origin/main`, now complete. Both sessions independently found and fixed the
same `test_specialists.py` clone-staleness bug by the same mechanism before either read the
other's work — reconciled, not duplicated, in decision #50. Fresh, real, this-session-verified
full suite: `pytest -q` → **919 passed, 0 failed, 18 deselected** (421s). Wave 9 (the heterogeneous
portfolio proof) has still not started; `TC-08` (the remote-write PR-opener capability) is now the
single remaining blocker to a live 3-repo presentation proof, with all four of its prerequisites
closed.

**2026-07-22, same-day continuation (decision #51)**: `TC-08` built -- `open_presentation_pr`, the
one real `remote_write` capability this project registers, plus its own dedicated, never-neutered
clone/remote path and write-verb GitHub API layer. Unit-proven (17 new tests, including real local
git clone/branch/push mechanics against a bare-repo stand-in), not yet live-proven -- a real PR
against a real pilot needs its own separate, explicit confirmation before the retrofit script that
would open one is ever run. Full suite: `pytest -q` → **938 passed, 0 failed, 18 deselected**
(287s). This is now, genuinely, the last built prerequisite before `TC-13`'s own live 3-repo proof
-- what remains is proving it live, not building anything further.

## Decision Ledger

Current working positions, not locked commitments (see GOVERNANCE.md rule 4). Any entry can be
revised at any stage by editing its text in place and adding one Changelog line. Numbers are
stable identifiers for cross-referencing (requirements, phases, evidence) and are never reused —
that is the only permanence they carry; text is always the decision as it stands today.

1. **Generic engine, Aspose is the first policy profile.** Zero Aspose-specific logic or naming
   inside `src/readme_agent/`. Aspose-specific facts live only in `data/products.json` and
   `config/policies/*.yml`.
2. **Package name `readme_agent`** (`src/readme_agent/`, CLI `readme-agent <verb>`).
3. **License: hold off.** No `LICENSE` file yet; `README.md` states this explicitly.
4. **`data/products.json` is the hard allow-list.** Only orgs/repos listed there are ones the agent
   is ever permitted to touch at all, for any operation, read or write, checked before any network
   or git operation. Revised by decision #40 (2026-07-20): the gate then splits by intent — a
   read-only capability (`side_effect_class` `read_only_local`/`read_only_network`) is gated by
   `registry/loader.py`'s `require_listed()`, which only checks presence in the file; a
   write/push-capable operation (the render+commit pipeline, or a `local_write`/`remote_write`
   capability) is gated by `is_permitted()`/`require_permitted()`, which additionally requires a
   non-`"disabled"` `mode`. Originally this document read "with a non-`disabled` mode" as part of
   the base gate itself, which decision #40 found was over-broad: `mode: "disabled"` was never
   meant to mean "excluded from analysis," only "push access unverified" — see decision #40 for the
   full reasoning and the safety companion that keeps write access exactly as strict as it always
   was.
5. **Missing/undetected license soft-degrades, never hard-blocks.** When `license/auditor.py`
   can't determine a license (GitHub API `null` and no classifiable LICENSE file text), the
   `license_mentioned` element is treated as a real gap to close, not a reason to refuse to
   operate on the repo.
6. **`referential_integrity` is a hard validator gate.** The LLM's self-reported claims
   (`claims.license_name`, `claims.commercial_link_url`) are never trusted at face value anywhere
   in this design — always cross-checked against ground truth and the actual rendered output.
7. **Policy schema uses concrete, independently checkable elements.** The shipped
   `schema_version: 2` policy retains the four proven README elements
   (`license_mentioned`, `products_org_link`, `products_com_link`,
   `relationship_explained`) because yesterday's implementation and evidence depend on them.
   They are compatibility and referral checks, not the complete quality definition. Phase 20
   defines a product-first presentation standard; Phase 21 adds README quality dimensions; Phase
   22 introduces `schema_version: 3` for controllable repository fields. GitHub-generated and
   product-agent-owned surfaces are represented as audit evidence, never as editable required
   elements.
8. **LLM surface area is narrow, fact-bound, and validated per job.** The shipped system has
   exactly one LLM job: writing `relationship_explained` only when that element is missing. URLs,
   license facts, and other known values remain deterministic. Planned jobs are separate and
   independently gated: a repository description, product-first README presentation proposals,
   and product visual concepts. Every factual claim must come from the product-facts contract or
   repository evidence; self-reported claims are never trusted; generated visuals cannot imply
   unsupported capabilities. Social-preview upload is not an LLM job — it is a delivery channel
   for an approved asset (decisions #22 and #23). This entry describes the current shipped
   engine's LLM scope accurately and remains true as a record of what's built; it is no longer the
   ceiling on future LLM jobs. The target architecture (decision #26) governs new LLM jobs through
   the capability-contract model — typed manifest, permission class, deterministic pre/post gates
   — not through this fixed enumeration.
9. **Product-first README; no promotional callout after the H1.** The former `callout` span is
   retired: Phase 21 removed it from the renderer and `upsert_span`, and migrates it out of
   existing work clones on next run (`markers.py`'s `remove_span` still recognizes the legacy name
   for exactly this cleanup). The README opening must explain the product before any commercial
   mention — now an ERROR-severity validator gate (`product_first_opening`). Evidence
   from six real leading-FOSS/dual-license reference repositories (`docs/presentation-standard.md`
   dimension 10) shows commercial-mention *placement* is not uniform across leading FOSS — two of
   four dual-licensed projects studied mention their paid tier near the top, not only at the end —
   but *tone, density, and singularity* are: exactly one mention, in factual or
   capability-extension language (never adjectives, pricing tables, or a call-to-action button),
   appearing either as a short closing-section paragraph or as one sentence directly under the
   opening product description. The existing end-of-file `resources` span satisfies this as a
   backward-compatible mechanism for genuinely missing license and relationship links, but its
   presence does not make a README professionally complete, and its density must stay at the
   shipped renderer's current two-link-plus-one-paragraph level — not the denser, multi-subsection
   pattern in the bot-authored `aspose-3d-foss/…Java` Resources section (decision #10), which
   exceeds what any reference source studied does. Phase 21a's `READMEPresentationReport` reports
   (read-only) on the opening explanation, audience/ecosystem statement, installation-path
   resolution, runnable example presence, and heading-level consistency per
   `docs/presentation-standard.md`. The section-aware *change plan* that would act on those
   findings — restructuring or improving wording within existing sections while preserving
   verified product facts — is 21e, deferred: it needs `change_boundary`'s byte-identical-outside-
   spans contract to evolve first, so it ships as a structured, evidenced proposal a human applies,
   never an automated rewrite, and never a generic-template replacement.
10. **Registry pilot roles**: `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` = `mode: full`
    (blank-slate value proof — real LLM call, real local commit). `aspose-3d-foss/Aspose.3D-FOSS-for-Java`
    = `mode: full` (zero-gap engineering proof: all four elements present, agent must produce
    zero changes). Caveat recorded 2026-07-18: the 3d READMEs were authored by lexchou's bot and
    per the sponsor do **not** represent the intended quality standard — they remain the
    zero-gap *detection* proof, not the content quality bar (that bar comes from the Phase 20
    n8n/nuget study). `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` = `mode: dry_run` (partial-gap
    proof — missing only `.org`, fixed deterministically with zero LLM calls). All other
    registry entries = `mode: disabled`.
11. **`facts_hash` excludes `gap_report`.** `gap_report` is *derived from* README content this
    tool itself rewrites; including it in the hash used to decide "should I regenerate" is
    circular — rendering closes gaps, which changes gap_report, which would make the hash unable
    to ever match itself again. `facts_hash` covers only inputs independent of our own writes:
    repo metadata, detected license, policy content hash, generation schema version. (Found via
    the orchestrator's idempotency test during implementation — see Changelog 2026-07-17.)
12. **`paths.work_dir()` is stable per `org/repo`, not per run-id.** Since this tool never
    pushes, a persistent local work clone is the only place "run twice, second run makes zero LLM
    calls" can be real — a fresh work clone every run would make idempotency fictional. Baseline
    clones and evidence remain per-run-scoped (baseline: always fresh, for accurate comparison;
    evidence: run-id-scoped, an accumulating audit trail).
13. **`gap_detector`'s domain checks are generic**, not hardcoded to `aspose.org`/`aspose.com`:
    `products\.[a-z0-9-]+\.(org|com)`. Real Aspose data matches this as a strict subset, so the
    ground-truth fixture corpus is unaffected; this is what decision #1 (generic engine) actually
    requires in code, not just in module naming. (Found via a synthetic orchestrator test using a
    non-Aspose fake domain — see Changelog 2026-07-17.)
14. **Git clone determinism is pinned per-invocation**, not left to the ambient environment:
    every clone/fetch in `gitsafety/clone.py` runs as `git -c core.autocrlf=false -c core.eol=lf
    ...`. Removes the specific, known source of cross-platform (Windows dev / Linux CI) byte
    differences.
15. **`generation_schema_version`** is part of the facts-hash inputs and must be bumped whenever
    `llm/prompts.py` or `readme/renderer.py`'s owned-span contract changes. A CI tripwire test
    (`tests/unit/test_generation_schema_version.py`) compares each file's content hash against
    the last recorded version bump and fails if either changed without one — intentionally
    fail-closed even for a purely cosmetic edit.
16. **All 10 validator rules run on every `generate`/`validate` invocation**, including the
    idempotent (hash-matches) and zero-gap paths. Idempotency only ever decides whether the LLM
    gets called, never whether validation runs — a hash match whose existing spans now fail
    validation against current policy is reported as `STALE_NONCOMPLIANT`, not silently folded
    into `COMPLIANT_NO_CHANGE`. Regenerating in that case requires explicit `--force-regenerate`.
17. **Product understanding, not promotional-link prominence, is the presentation goal.**
    The shipped `prominence` rule is retained at WARNING severity for Phase 0–15 compatibility; it
    must not be used to move commercial links to the top. Phase 21c adds the actual enforcement as
    two ERROR-severity rules: `product_first_opening` (fails if any commercial link precedes the
    product-description sentence) and `commercial_mention_discipline` (fails on multiple
    list-item-formatted commercial links, promotional/CTA language, or wrong placement). Together
    they check whether the README explains the product before promotion and avoids burying
    critical developer information under promotional density. A promotional link that is
    technically present but naturally placed is not a defect; an opening dominated by promotion is.
18. **Central repository-presentation agent with bounded editorial authority.** Product
    agents own the technical source of truth: supported capabilities and formats, installation,
    APIs, examples, package coordinates, and release changes. The central agent may reorganize
    and improve the presentation of those verified facts, but it may not invent, remove, broaden,
    or silently reinterpret them. Ambiguous technical content becomes a product-agent feedback
    item, not an LLM guess.

19. **Every visible surface has an explicit control class.**
    - **Repository-file managed:** README, embedded images, LICENSE, CONTRIBUTING,
      CODE_OF_CONDUCT, SECURITY, SUPPORT, issue/PR templates, and other approved files. Changes
      are prepared in push-blocked work clones.
    - **GitHub API/settings managed:** repository description, homepage/website, topics, and
      explicitly approved feature settings. Changes are dry-run proposals by default and require
      an apply gate with the necessary permissions.
    - **Manual UI managed:** repository social-preview upload. The agent may prepare and validate
      the asset and instructions, but no automated write is claimed without a documented API.
    - **Product-agent owned:** releases, packages, package publishing, and release-specific
      technical facts. The central agent audits presentation and linkage and sends findings to the
      owning product agent.
    - **GitHub generated:** contributors, languages, activity, stars, forks, counts, and GitHub's
      layout/tabs. The agent may audit and explain anomalies but must never present these as fields
      it can directly set.

20. **Success metric: ≥10 visitors/week from github.com to aspose.org, subordinate to trust and
    product quality.** The target is measured through the weekly aspose.org source report and
    approved UTM-tagged links. Phase 20 must establish feasibility, baseline views, expected
    click-through, required repository coverage, and timing. The traffic target never justifies
    promotional placement that harms credibility, and production rollout requires both quality
    acceptance and a credible measurement plan.

21. **Drift protection is part of the publishing lifecycle, not a one-time cleanup.** Product
    agents continue changing products and READMEs. The central agent must run after or alongside
    those publishing workflows, compare managed presentation surfaces with the accepted baseline,
    and detect removed markers, lost sections, weakened prose, stale visuals, broken links, and
    generic overwrites. It proposes evidence-backed repairs through the normal safety gates and
    never silently reverts another agent's change.

22. **Product-facts and change-handoff contract.** Before the central agent edits product-facing
    content, it must have a provenance-bearing input from the product agent or repository
    inspection containing at least: product identity, audience, supported capabilities and
    formats, installation/package coordinates, minimal verified example, documentation links,
    current release information, and known limitations. Each claim in proposed prose must map to
    one of these facts. Missing facts produce a report for the product agent; they do not become
    placeholders or invented marketing copy.

23. **README product illustration and GitHub social preview are separate surfaces.** A product
    illustration embedded in README is a repository file and can help visitors understand the
    product on the repository page. A social-preview image appears when the repository link is
    shared externally and is uploaded through repository settings; it is not the README hero and
    does not replace one. Phase 24 may generate a shared visual concept, but each output has its
    own dimensions, validation, delivery path, and approval.

24. **Pilot and rollout contract.** The three enabled repositories remain the initial engineering
    pilot because they represent blank-slate, partial-gap, and already-populated conditions.
    They are not three templates to clone. Each receives a repository-specific proposal based on
    its product facts. Wider rollout is blocked until: the three pilots pass deterministic and
    independent review; no unsupported GitHub-control claims remain; product-agent ownership is
    respected; later product updates do not erase the improvements; and the sponsor accepts the
    quality standard and pilot output.
    **Research/development scope is the full registry, not the pilot set (clarified
    2026-07-19).** The "three enabled repositories" language above governs *write/rollout* scope
    only — which repositories the system is currently permitted to execute `generate`/apply
    against. It does not narrow *research or development* scope: every entry in
    `data/products.json`, active or `disabled`, carries equal precedence and must be included in
    portfolio surveys, fact-gathering, validator/policy design, and any other investigation or
    development task — the 2026-07-18 portfolio survey (Reference Data below) already does this
    in practice, surveying all 25 entries rather than just the 3 enabled ones; this entry makes
    that scope binding rather than incidental. End-to-end execution checks remain scoped to the
    three Java pilots (`aspose-3d-foss`, `aspose-cells-foss`, `aspose-pdf-foss`, all
    `platform: java`) specifically *because* they are the only entries with a non-`disabled`
    `mode` in `data/products.json` today — an access constraint on what can actually be run
    end-to-end, not a signal that the other 22 registry entries matter less.

25. **Requirements specification and bidirectional traceability.**
    [`plans/requirements.md`](requirements.md) is the authoritative register of business,
    functional, safety, quality, integration, rollout, and governance requirements. Requirement
    IDs are stable (never reused) and must carry status, priority, acceptance evidence, and
    decision/phase traceability. This master plan remains the execution sequence and decision
    ledger.
    Any change to scope, obligations, ownership, acceptance criteria, architecture direction, or
    rollout must update both documents in the same commit or change set. Requirements are never
    silently deleted; they are deprecated or superseded with history. A future CI check must
    validate unique IDs and bidirectional traceability.

26. **Autonomous capability-driven control plane is the architectural doctrine, running
    primarily from GitHub Actions.** The system replaces a fixed deterministic pipeline with a
    runtime that discovers repository structure, automatically selects from a registered set of
    capabilities, and lets the LLM plan, interpret, coordinate, and repair — while every fact,
    mutation, validation, evidence record, and rollback stays deterministic and gated. What
    changed and what didn't, precisely:
    (a) the LLM's role is broadened from one narrow job (decision #8's shipped scope) to owning
    interpretation, planning, capability selection, replanning, and repair judgment — but it
    still never executes an effect directly; every proposed `capability_action` is dispatched,
    permission-checked, and validated by deterministic code before anything happens;
    (b) deterministic components retain exclusive ownership of git operations, API calls,
    manifest/package-registry parsing, schema/URL/Markdown validation, hashing, state
    persistence, permission/allow-list enforcement, secret redaction, evidence writing, and
    rollback — the LLM is never trusted to guess a fact a tool can extract;
    (c) agentic output is always a proposal or a structured `capability_action`, never a direct
    effect — it takes effect only after deterministic gates: strict schema, referential
    integrity (#6), the always-run validator registry (#16), permission-class checks (unchanged
    from the prior doctrine);
    (d) reproducibility comes from hashed inputs and per-capability fingerprints (#11, #15) —
    identical inputs never re-trigger generation or re-selection; nondeterminism stays contained
    and is recorded in evidence (unchanged);
    (e) the agentic layer is swappable and empirically characterized, not assumed — model
    routing is chosen per job from live-tested gateway behavior (see
    `plans/investigations/llm-gateway-characterization.md`: `qwen3-next` for structured/planning
    work, `gpt-oss` avoided for instruction-critical steps since it never recovered a needle at
    any context size tested and scored 1/10 on structured-output validity, `qwen3-embedding-8b`
    for similarity/template-clone detection), not model-name folklore;
    (f) no human selects a capability, skill, or command during a normal run — capability
    discovery and selection are automatic; humans review proposals and authorize gated effects,
    they do not operate the pipeline by hand;
    (g) every effect stays behind the allow-list (#4) and push-blocking safety controls
    (unchanged).
    This supersedes the "narrow agentic edge" framing this entry previously carried: the
    deterministic/agentic split itself was correct and is retained in (b)–(d) above; what was
    wrong was scoping the LLM to a single job on a fixed pipeline forever — that was the first
    implementation's boundary, not the architecture's ceiling. (Revised 2026-07-18, sponsor
    directive `AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001` — see Changelog.)
    **Exactly-once effect application is required before Wave 5's supervisor may drive the
    dispatcher unattended** (added 2026-07-19, capability-dispatch production-readiness
    assessment): (d)'s reproducibility-via-fingerprints covers *re-generation*, not what happens
    when a `gated_effector` capability's effect partially lands before an ephemeral GitHub Actions
    runner dies mid-job and the same job is retried — a real gap with, until now, zero requirement
    coverage (`MEM-002` covers concurrent writers, `VER-003` covers full-run convergence, neither
    covers a crash-then-retry of a single effect). New `EFF-*` (`plans/requirements.md` §19)
    specifies an idempotency-key ledger extending the existing `facts_hash`/decision #11 pattern to
    effects, with retry made structurally inert for any capability above `read_only_network`
    unless it declares itself safely retryable — detail lives in
    `plans/investigations/capability-dispatch-production-readiness.md`, not repeated here. No
    `gated_effector` capability exists yet, so this is accepted ahead of need, per decision #30:
    check Wave 4's state-backend evaluation (`MEM-003`) for a reusable primitive before
    hand-building one.
    **`EFF-001`'s registration-time half is now implemented, and the blocking dependency is named
    explicitly** (added 2026-07-19, specialist-domain-isolation production-readiness pass): the
    prior paragraph traced `EFF-*` to "Wave 5" generically, but the actual forcing function is
    **Wave 7** — the first wave that plausibly registers a `local_write`/`remote_write` capability;
    Wave 5's supervisor never registers a capability at all. `capabilities/registry.py::_build()`
    now rejects, at import time, any manifest at `side_effect_class >= local_write` missing
    `idempotency_inputs` or `retry_policy` — a no-op today (no such manifest exists) that forecloses
    the realistic failure mode ahead of need: GitHub Actions' ordinary "re-run failed jobs" button
    firing a `remote_write` capability a second time with no idempotency check, producing a
    duplicate effect on a real, public repository. **No capability at `side_effect_class >=
    local_write` may be registered before `EFF-001` reaches `IMPLEMENTED`** — the two-phase-apply
    and structurally-inert-retry portions of `EFF-001`/`EFF-002`/`EFF-003` remain `PLANNED`, owned
    by Wave 5's dispatcher-retry-wrapper work; only the registration-time declaration gate is built.
    See `plans/investigations/specialist-domain-isolation-production-readiness.md`.

27. **Runtime task-graph/dispatcher: extend the existing orchestrator, no new agent framework —
    native tool-calling is the structured-action mechanism.** Wave 1 (sprint Tasks 9–14) live-
    tested `llm.professionalize.com`'s native OpenAI-style tool-calling (`tools`/`tool_choice`)
    and found it reliable for both chat models — `qwen3-next` 5/5 and, surprisingly, `gpt-oss`
    also 5/5 for single-step tool calls despite scoring only 1/10 on freeform structured JSON
    (decision #26(e); full findings L6–L8 in `plans/investigations/llm-gateway-characterization.md`).
    Parallel tool-calling was observed once per model — `qwen3-next` returned both calls,
    `gpt-oss` returned only one (`probe_llm_gateway.py:366-399`, a single trial per model, not a
    repeated-trial result; corrected 2026-07-19, see decision #26's added point below and
    `plans/investigations/capability-dispatch-production-readiness.md`) — so this remains
    `RESEARCH-GATED`, not a characterized model weakness. The task-graph/dispatcher design
    requests one capability per planning turn as the portable baseline regardless: L6's 5/5
    single-step result for both models already justifies it without needing the parallel-call
    question resolved either way. Evaluated three third-party runtime frameworks against the sprint's own
    Section 17 criteria (`plans/investigations/runtime-framework-evaluation.md`): LangGraph,
    Pydantic AI, and OpenAI Agents SDK are all confirmed gateway-compatible (custom
    `base_url`/Chat Completions), so gateway fit does not decide this. The decision instead turns
    on state-schema ownership (`ORC-001` already specifies the target task-state enum; adopting
    a framework's own checkpoint/state model would import a second, foreign schema Wave 4's own
    governed backend evaluation — `MEM-*`, sprint Task 6.2 — should decide on its own merits, not
    inherit as a side effect), zero new runtime dependency (`pydantic>=2.0` already ships), and
    full reuse of the existing `LLMClient` Protocol/`fixture_client.py` test pattern without a
    framework-specific adapter layer. **Chosen: extend `src/readme_agent/orchestrator.py`'s
    successor with an explicit, typed (pydantic) task-graph/dispatcher module built directly on
    the proven `requests`-based live client pattern, using native tool-calling per L6/L7 as the
    structured-action dispatch mechanism (sprint Task 4.3) rather than freeform-JSON prompting.**
    One loop iteration (`observe → plan → execute → observe → replan`) was proven live against
    the real `pdf/java` pilot and a 3-capability spike menu — full trace and dispatcher-gate
    behavior in `plans/investigations/agentic-loop-proof.md` — satisfying `AGT-002`'s acceptance
    bar. This is a Decision Ledger entry, not a permanent lock-in: revisable in Wave 4 if
    hand-rolled durable checkpointing across ephemeral GitHub runners proves harder than expected,
    or in Wave 7+ if subgraph/specialist-role composition outgrows plain function composition.
    Neither the Wave 2 `CapabilityManifest`/registry nor the Wave 5 production supervisor is built
    by this decision — it only settles what they will be built on. (Added 2026-07-18, sponsor
    directive `AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001` Wave 1 — see Changelog.)
    **The "Wave 7+... subgraph/specialist-role composition" trigger above is resolved** (added
    2026-07-19, user directive to decide and document ahead of Wave 7 rather than when its queue
    position arrives): `plans/investigations/runtime-framework-evaluation.md`'s own scoring already
    found plain function composition the one weak row in an otherwise-favorable comparison —
    "Strongest native fit — this is LangGraph's core design center" for LangGraph specifically,
    against "less mature graph model" (Pydantic AI) and an "off-label escape hatch" gateway fit
    (OpenAI Agents SDK). **Decision: LangGraph is adopted, scoped to Wave 6-8 specialist/subgraph
    composition only.** Wave 5's core supervisor/task-graph above is unchanged — none of that
    reasoning (typed state on `ORC-001`'s schema, zero new dependency, GitHub Actions lightness,
    direct evidence-writer integration) was about subgraph/specialist composition, and the
    evaluation found it correct on every other row. LangGraph becomes a library the Wave 5
    supervisor calls into for the specialist layer, not the top-level state/evidence owner — Wave
    4's state backend and the evidence-writer pipeline are untouched. **LangGraph's per-node tool
    binding is a request-time reliability/UX layer, not the enforcement boundary**: it is ordinary
    orchestration-code wiring (a copy-paste bug in graph construction, a stale tool list, or a
    hand-authored call straight into `dispatch_tool_call` all silently bypass it), not a sandboxed
    guarantee. Decision #34 is the actual, dispatch-side enforcement boundary for specialist domain
    isolation — orthogonal to, and required regardless of, this framework choice. See
    `plans/investigations/specialist-domain-isolation-production-readiness.md`.

28. **GitHub API access stays raw `requests`, not PyGithub — now an explicit decision, not an
    implicit default.** An independent review (2026-07-19) flagged that `preflight/github_check.py`
    (`GET /user`, `GET /repos/{org_repo}`) and `scripts/update_products_registry.py`'s org-scan
    (`GET /orgs/{org}/repos`, paginated) both hand-roll HTTP calls against `api.github.com`
    instead of using a maintained client library, and that this choice — unlike decision #27's
    framework evaluation — had never been recorded anywhere. Reviewed on its merits, not
    rubber-stamped: the exposure is small (three read-only endpoint shapes total, across two
    files) and already field-proven — the registry-scan workflow has run live against all 26 real
    orgs (Build Checklist, Phase 18). The review's own audit found this consistent with the
    project's demonstrated minimal-dependency stance elsewhere (git via the real binary, Maven
    Central via direct `requests`, GitHub Actions marketplace actions over hand-rolled PR
    creation) and convention #4 (`[[conventions-and-feedback]]`: "framework/tool selection must
    follow defined coordination requirements, never precede them" — three narrow read-only
    endpoints do not need an object-relational API client). One genuine, narrow gap the review
    prompted a direct look for: `_paginate`'s 403 handler only read `X-RateLimit-Reset` (the
    *primary/core* rate limit), not `Retry-After` (how GitHub signals the *secondary/abuse-
    detection* limit, which can fire with core quota still remaining) — fixed same-day
    (`_rate_limit_wait_seconds()`, `scripts/update_products_registry.py`), with unit coverage
    added for a branch that had none before (`tests/unit/test_update_products_registry.py::TestRateLimitWaitSeconds`).
    **Decision: keep raw `requests`; adopt PyGithub only if a future surface needs write
    operations, mutation-heavy pagination, or enough additional endpoints that hand-rolling stops
    being the smaller amount of code** — revisable the same way #27 is, on a documented trigger,
    not by default drift. (Added 2026-07-19, in response to an independent review conducted before
    Wave 3 — see Changelog.)

29. **Backlog discipline for issues found outside current task scope.** An agent (human or AI)
    working in this repository that discovers an issue, gap, or improvement opportunity that does
    **not** block the task it is currently doing MUST log it as a new requirement row with status
    `BACKLOG` (open) in `plans/requirements.md`, in the section matching its topic — never fix it
    inline as unrequested scope creep, and never silently drop it. An issue that **does** block the
    current task's correctness, safety, or acceptance MUST be fixed first, before the task is
    considered done; backlog logging is not a substitute for fixing a real blocker. A `BACKLOG` row
    is triaged later, by a human or a subsequent task, into `PLANNED` (accepted, with real
    acceptance criteria added) or `DEPRECATED` (rejected, with reason) — `GOV-003`'s no-silent-
    deletion rule applies to `BACKLOG` rows exactly as it does to any other requirement. See
    `GOV-014` in `plans/requirements.md` for the normative statement. (Added 2026-07-19, user
    directive.)

30. **Hand-rolling everything instead of using battle-tested tools is discouraged — GOVERNANCE.md
    rule 8.** Prompted by a direct user question ("use proven battle tested tools for
    everything... it is in governance, right?") that was, at the time, correctly answered "no" —
    checked directly (`grep -rn -i "battle.tested" plans/ AGENTS.md README.md`), no such rule
    existed; decisions #27 and #28 had each independently evaluated and rejected a proven option
    with real reasons, but no written policy made that evaluate-and-justify step mandatory. Now
    written down (`GOVERNANCE.md` rule 8): before building any new functionality, an agent MUST
    actively research, evaluate, and select an existing library, stdlib facility, framework, or a
    real reference implementation from a sibling proven system first, and build on it — hand-
    rolling is a discouraged default, not an absolute ban; it remains allowed as a special
    circumstance, but only behind the same explicit, reasoned Decision Ledger entry #27/#28 already
    met, never a silent default choice. First real application, same day: Wave 3's `ecosystems/`
    platform parsers (Java/Gradle, Python, .NET, TypeScript, Go, C++) are adapted from
    `D:\onedrive\Documents\GitHub\aspose.org\scripts\pipeline\extraction\package_manifest.py` —
    real, currently-running code, already tuned against the same Aspose FOSS repo corpus this
    project targets (per the user: "aspose.org's solutions are custom built on the repos we are
    working on") — rather than hand-written from scratch. This includes a direct reversal: an
    earlier plan draft for the same wave proposed rewriting `ecosystems/maven.py` from regex to
    `xml.etree.ElementTree`, reasoning in the abstract that a real parser beats regex-over-XML.
    Once the actual proven reference was found, it turned out to use regex too, consistently,
    across every format including XML, with the same documented `<parent>`-block limitation
    `maven.py` already carries — so the ElementTree rewrite would have been *new, field-untested*
    code diverging from the proven source, not an application of this rule but a violation of it.
    Reversed before implementation, per direct user confirmation, with an explicit caveat
    carried forward into Wave 3's own regression/live-test requirements: "prioritize robustness
    over ease of reuse if you have to" — adapted code still needs this project's own tests
    against this project's own real repos, not a free pass because the source is proven
    elsewhere. See `plans/requirements.md`'s `GOV-015` and the Reference Data table's new
    aspose.org row. **Broadened same day**, direct user follow-up ("hand-rolling everything instead
    of using battle tested tools is prohibited... the agent must be able to research, select,
    incorporate and build upon battle tested tools instead of hand-rolling everything... more tools
    means less hand-rolled code and less troubleshooting"; then clarified further: "must be
    discouraged but allowed in special circumstances") — scope widened from "new
    parsing/protocol/integration code" to any new functionality, and the duty made active
    (research/select/incorporate/build-upon) rather than a check performed only when already about
    to write bespoke code. (Added 2026-07-19, user directive.)

31. **Investigate before overwriting — GOVERNANCE.md rule 9.** An agent (human or AI) working in
    this repository MUST investigate a file, Decision Ledger entry, requirement row, evidence
    artifact, or git state before overwriting, replacing, deleting, or discarding it: read what
    is there, check its recent history (`git log`/`git blame`), and confirm the change is safe or
    intended before applying it. If the investigation shows the existing content matters, it is
    preserved, migrated, or the task pauses for user input — never silently clobbered. This
    generalizes the never-silently-delete disciplines already binding on specific artifact
    classes (`GOV-002`/`GOV-003` for the Decision Ledger and requirements; the
    `tests/fixtures/` immutable-snapshot rule; `GOVERNANCE.md`'s no-orphan-artifacts rule) into
    one explicit, repo-wide rule that also covers artifact classes with no prior rule of their
    own. See `plans/requirements.md`'s `GOV-017` for the normative statement. (Added 2026-07-19,
    user directive.)

32. **Durable runner state backend: one git ref per `org_repo` on this project's own remote —
    not a shared branch, not an external database (Wave 4, `MEM-*`/`RUN-001`).** `RUN-001` (P0)
    forbids depending on a local persistent clone (decision #12) as durable state in production;
    a GitHub Actions runner wipes `runs/work/` after every job. A first draft put every repo's
    accepted state on one shared branch and relied on git's non-fast-forward push rejection as
    the compare-and-swap check — but that rejection is scoped to the branch ref as a whole, not
    to an individual file inside it, so two *unrelated* repos' concurrent writes would falsely
    conflict: whichever pushed second would be told `stale` even though nothing about its own
    repo's state changed, a false positive on exactly the safety signal `MEM-002` ("per-repository
    lease/lock and compare-and-swap... a concurrent update MUST yield `STALE_INPUT`") exists to
    produce. **Reversed to one dedicated git ref per `org_repo`**
    (`refs/readme-agent-state/{org}__{repo}`, locks at
    `refs/readme-agent-state/locks/{org}__{repo}`) so CAS granularity matches the actual unit of
    concurrency (one repo): unrelated repos literally cannot collide, because they are different
    refs. Implemented via git plumbing (`hash-object`/`mktree`/`commit-tree`/`push <sha>:<ref>`),
    deliberately no working-tree checkout per write — that would reintroduce the same
    local-clone-as-durable-state antipattern `RUN-001` forbids, just renamed. An external database
    or object store was evaluated and rejected outright, not deferred: new
    infrastructure/cost/credential surface for a portfolio where per-repo state is a few KB is
    disproportionate (`GOVERNANCE.md` rule 8). Not a permanent lock-in — revisit if per-repo write
    volume/concurrency outgrows what `git push` against this repo's own remote can absorb,
    per-repo state stops being "a few KB", or a real cross-repo query/dashboard need emerges that a
    flat per-ref blob store can't serve, mirroring decisions #27/#28's revisit-trigger pattern.
    `CapabilityOutputCacheEntry.fingerprint` (`state/schema.py`) is deliberately the same value
    `EFF-001` (`plans/investigations/capability-dispatch-production-readiness.md`) calls an
    idempotency key — Wave 5's `gated_effector` idempotency-key ledger should reuse this backend
    rather than hand-building a second one, per that investigation's own build-time constraint.
    (Added 2026-07-19, sponsor directive `AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001` Wave 4 — see
    Changelog.)

33. **Prove it in production — GOVERNANCE.md rule 10.** Prompted by a direct user instruction
    ("prove it in production... make it a rule in governance") naming a discipline this project
    had already practiced repeatedly but never written down: every phase in this project's own
    Changelog only closes out against a real, live target — the three enabled pilots re-run end to
    end (Phase 13, Wave 3's full-registry survey), a real `act` reproduction of
    `readme-agent-run.yml` (`RUN-003`), a live `qwen3-next` capability call through the production
    dispatcher (Wave 2) — never unit tests or mocked fixtures alone. `GOV-007` already required
    "objective tests or evidence" before a requirement is marked `IMPLEMENTED`; it did not say that
    evidence must be a live, real-world demonstration rather than a mock. Now written down
    (`GOVERNANCE.md` rule 10, new `GOV-018`): a requirement or Build Checklist line is not accepted
    as done on unit-test evidence alone — it needs a real, production-like demonstration matched to
    what it claims (real repos, a live LLM/gateway call, a real CI reproduction). This does not
    touch the pilot posture: "production" means real data/systems exercised under the existing
    push-blocking and allow-list safety properties, read-only or dry-run. At this stage it does not
    mean committing or pushing anything to the actual product repos as a side effect of proving a
    requirement — any real write to a managed remote still requires the user's separate, explicit
    approval each time; this decision grants no such approval on its own. Clarified same-day, in
    response to a direct follow-up ("prove it on production does not mean pushing anything to the
    product repos at this stage. it should need explicit approval from the user") after the first
    draft of this rule read as a blanket, permanent prohibition rather than an approval gate — the
    distinction matters because a future stage may add real writes, and the rule must default to
    "ask first," not "impossible forever."

    **Sharpened further, same day**: a follow-up user directive ("make sure nothing gets pushed to
    product repos unless explictly confirmed with what is going to be pushed, why and where
    explictly without any confusion") spells out what "the user's separate, explicit approval"
    from the paragraph above must actually contain. It is not a bare yes/no — the confirmation
    obtained before any push MUST name, unambiguously: **what** is being pushed (the exact
    commit/diff/content), **why** (the reason/purpose), and **where** (the exact repository,
    branch, and remote). This applies to every would-be pusher this project's governance reaches —
    an agent (human or AI) working in the repo directly, and any future `gated_effector` capability
    — with no exception for a standing or implied consent from earlier in a session. (Added
    2026-07-19, user directive.)

34. **Specialist domain-invocation enforcement: a second, orthogonal axis on `CapabilityManifest`,
    checked dispatcher-side — not a proven authorization library, not framework tool-scoping
    alone.** Prompted by direct user instruction to treat "independent agents, each in their own
    domain" as a production problem and to test hand-rolling against real proven-tool alternatives
    before accepting it, the same discipline decision #27 already applied to the composition
    question. Root cause: `capabilities/dispatcher.py` has always checked exactly one axis
    (`side_effect_class`, blast radius) because until Wave 6 there was only ever one caller to
    authorize — this is a missing schema dimension, not a dispatcher defect (`dispatcher.py`
    correctly implements what its schema modeled). Researched, with verified maintenance status,
    real current authorization/access-control libraries: Oso (deprecated Dec 2023), py-abac and
    Vakt (both years-stale), OPA (no official embedded-Python path — only a sidecar/daemon process
    or an unofficial WASM bridge, reintroducing exactly the infrastructure surface this project has
    already avoided elsewhere), Cedar/`cedarpy` (actively released, but unofficial single-maintainer
    native-code machinery built for multi-tenant SaaS resource authorization — the same
    disproportion shape as decision #28's PyGithub rejection). Casbin (`pycasbin`) is the one real,
    actively-maintained, architecturally-fitting candidate — pure Python, two tiny deps, a built-in
    "RBAC with domains" model — and was still rejected: it would duplicate the domain-permission
    data across two representations (the existing pydantic `CapabilityManifest`, already the single
    source of truth, vs. Casbin's own policy files) to re-derive a check that's already one line
    against typed data in hand, mirroring decision #27's own reasoning for rejecting a framework at
    the Wave 5 core-loop layer. **Decision: extend the hand-rolled pattern.**
    `CapabilityManifest.allowed_domains: list[str]` (additive; empty = unscoped, the unchanged
    meaning for all four capabilities shipped through Wave 4); `capabilities/domains.py::KNOWN_DOMAINS`
    (a registered set, not a closed `Literal` — the specialist list grows wave-by-wave); `registry.py`
    validates domain membership at build time and enforces a fail-closed sunset (once more than one
    domain is registered, a mutating manifest with no `allowed_domains` is rejected — the engineered
    expiry of the "insecure by default" window, `GOVERNANCE.md` rule 5); `dispatcher.py::dispatch_tool_call`
    gains a `caller_domain` parameter, supplied only by deterministic graph-wiring code, never by
    anything the LLM outputs, and a `rejected_domain_denied` outcome. **This dispatcher check, not
    whatever tools a framework (LangGraph, decision #27) happens to offer a specialist's LLM, is the
    actual enforcement boundary** — it is the one point every call path must cross regardless of
    which graph node or wiring bug produced it. Wave 8's `VER-001` (independent verifier) depends on
    this directly: if isolation were convention-only, a wiring bug could silently hand the verifier
    the same mutating access as the capability it's supposed to be checking. **Falsifiable revisit
    trigger**: hierarchy (a domain inheriting another's capabilities), wildcard/pattern-based
    grants, or externally-supplied/runtime-editable policy would flip this to Casbin specifically —
    the only candidate that cleared the architecture and maintenance bar. Implemented and tested
    this pass (`CAP-006`, `PARTIAL` — mechanism built, real domain population is Wave 6's job, per
    `GOV-018`'s live-proof bar); zero existing test modified for behavioral reasons. See
    `plans/investigations/specialist-domain-isolation-production-readiness.md`. (Added 2026-07-19,
    user directive.)

35. **Multi-writer durable state: per-domain schema on the existing git-ref backend — not a
    different coordination primitive.** Same production-problem framing as decision #34, applied to
    `state/schema.py::RunStateV1`. Root cause, confirmed directly against `git_backend.py::save()`:
    it is a whole-blob replace under one tree path, and `RunStateV1`'s `accepted_facts_hash`/
    `accepted_status` are singular scalars — both correct when there was one producer per repo per
    run. Once Wave 6+ specialists each produce their own accepted result within one run against the
    same `org_repo` record, two specialists writing that record either false-positive collide on the
    CAS check or silently clobber each other's result — the same bug class decision #32 already
    found and fixed once (CAS granularity coarser than the real concurrency unit), reappearing one
    layer further down. Verified directly against git's own wire-protocol documentation before
    proposing a fix: `git mktree` genuinely supports multiple blob entries per tree, but
    non-fast-forward rejection is scoped to the ref as a whole, not to any path inside it — a
    multi-blob tree does not, by itself, buy finer-than-ref conflict detection, so a retry step is
    unavoidable regardless of tree shape. Researched GitHub-native and external alternatives before
    concluding this is a schema fix, not a tool swap: the Contents API is the same branch-HEAD-serialized
    granularity as raw git, wrapped in HTTP, with no capability gain (corroborated by two independent
    community bug reports of cross-file SHA-mismatch 409s on concurrent writes, flagged as
    circumstantial, not an explicit GitHub statement); Issues/Discussions have no conditional-write
    support per GitHub's own docs; Actions cache is immutable-once-written, wrong shape entirely.
    S3/DynamoDB conditional writes are genuinely finer-grained in isolation — the one candidate
    technically superior to git's ref-level granularity — but reopen exactly the infrastructure/
    credential surface decision #32 already, explicitly rejected; none of #32's own named revisit
    triggers (state stops being "a few KB," write volume outgrows `git push`, a cross-repo query
    need emerges) are met by this problem. **Decision: `state/schema.py` gains `DomainStateV1` and
    `RunStateV1.domain_states: dict[str, DomainStateV1]`** (additive; the existing flat fields are
    not deprecated — they remain whatever a single top-level producer writes; `domain_states` is
    what Wave 6+ specialists write into independently). `state/domain_state.py::save_domain()`
    composes the already-existing, already-live-tested `acquire_lock`/`release_lock` lease
    (`MEM-002`) as the primary serialization mechanism, with the version-CAS retry as a correctness
    backstop for the lease-expiry edge case (a lease is a timeout, not a hard mutex) — always
    re-patching onto a freshly reloaded copy so another domain's already-accepted result is carried
    forward, never overwritten. No change to `GitStateBackend.save()`'s signature or whole-blob-replace
    mechanics. Verdict, stated precisely: proven primitive (git's ref-update CAS), right granularity
    (per-`org_repo`, unchanged from decision #32), payload shape needed to grow — not a
    build-vs-adopt tool decision in the sense first feared. Documented, not built: an optional
    multi-blob tree layout for per-domain audit clarity, logged as very likely unnecessary
    complexity at Wave 7's actual scale (7 named specialists, record still "a few KB"). Implemented
    and tested this pass (`MEM-004`, `PARTIAL` — schema and helper built and unit-tested against a
    fake backend; the live, multi-specialist proof is Wave 6's job, per `GOV-018`). See
    `plans/investigations/specialist-domain-isolation-production-readiness.md`. (Added 2026-07-19,
    user directive.)

36. **Wave 5: production supervisor built on plain pydantic + function composition (unchanged
    from decision #27), effect safety built and proven ahead of the first real mutating
    capability.** `capabilities/schema.py::CapabilityGap`'s own docstring already named this wave
    correctly: "the first wave with a 'run'." Built `src/readme_agent/supervisor/` (`task.py`'s
    `TaskGraph` — `ORC-001`'s exact task-state set, two independent cycle checks, a `SUPERSEDED`
    dedup rule that is what actually makes convergence decidable; `convergence.py`'s `AGT-004`
    stop conditions; `repair.py`'s `ORC-002`/`VER-002` failure classification; `loop.py`'s
    `supervise_repo()`, promoting Wave 1's spike), `llm/planner_client.py` (a new, thin
    Live/Fixture client pair — `LLMClient` cannot carry a tool-calling response, it hardcodes a
    no-`tools` payload and a strict single-job schema), and `capabilities/effect_ledger.py`
    (`EFF-002`/`EFF-003`, dispatch-tier per this ledger's own earlier "Wave 5's
    dispatcher-retry-wrapper work" phrasing — usable by any future caller of `dispatch_tool_call`,
    not supervisor-specific). New CLI `supervise` verb, additive alongside `run`/`run-registry`.

    **A real conflict between a user confirmation and an already-recorded same-day decision was
    surfaced and resolved, not silently picked either way.** The user initially confirmed
    registering `generate_repo()` as Wave 5's first `local_write` capability — directly
    contradicting this ledger's own decision #26 addendum ("Wave 5's supervisor never registers a
    capability at all; Wave 7 is the actual blocking dependency"). Brought back rather than
    overridden silently in either direction. Resolution: the apparent conflict dissolves once two
    questions are separated — *which wave registers a real mutating capability* (Wave 7, this
    ledger's existing answer, unchanged) from *which wave builds and proves the duplicate-effect
    safety mechanism* (now, precisely because it is safety-critical — the same lesson decision #34
    already drew about access-control fields differing from performance fields — and because
    deferring the mechanism itself, not just a capability, to Wave 7 would make Wave 7 the first
    time it is ever stress-tested, a worse risk position than proving it early against a
    controlled subject). `generate_repo()` was independently confirmed a poor `EFF-002` test
    subject regardless: its idempotency key (`facts_hash`) is derived mid-pipeline, not a call
    argument, so it cannot be computed pre-dispatch the way the ledger requires.

    **A genuine design flaw in the cited prior investigation was found and corrected before any
    code was written**, not discovered live: `capability-dispatch-production-readiness.md`'s own
    two-phase-apply proposal stored the pending/applied intent record in local evidence-dir JSON
    (`runs/evidence/{run_id}/effect_intents/...`) — exactly the storage decision #32 built
    `GitStateBackend` to stop depending on. A pending record there would have been lost on the
    precise "runner dies mid-effect, retried on a fresh runner" scenario `EFF-002` exists to
    survive. Corrected to a durable git-backed record (`CapabilityOutputCacheEntry.status`,
    reusing the exact lock-primary/CAS-backstop pattern `state/domain_state.py::save_domain()`
    already proved live) before implementation began.

    Several real bugs were found and fixed via direct testing during this pass, honestly recorded
    rather than smoothed over: a premature-convergence design (checking graph emptiness at the top
    of every turn) stopped the loop after the deterministic bootstrap alone, *never consulting the
    planner* — found via a manual smoke test before any unit test existed, fixed by splitting
    convergence into a per-turn bound check and a stop-once-the-planner-says-so classification;
    `TaskGraph.ready_tasks()` originally required a dependency to reach `PASSED`, which would have
    permanently stranded every repair task (whose sole dependency is the `FAILED` task it
    repairs); `_dispatch_and_record()` returned nothing and callers kept referencing a stale
    pre-dispatch object; a repair task's own outcome was not propagated back to its caller; the
    planner's own explicit stop left the run's final status uncomputed; `acquire_lock()` returning
    "held by someone else" was being silently ignored rather than respected. A dead-code branch
    (`effect_ledger.py`'s originally-planned `retry_refused` outcome) was found unreachable — a
    failed dispatch always leaves the ledger entry `pending`, which unconditionally intercepts
    before any `retry_policy` check could run — and removed; `EFF-003`'s real enforcement point is
    one layer up, in `repair.py`'s decision whether to even *propose* a retry.

    Full requirement-status detail (`AGT-*`/`ORC-*`/`VER-*`/`GAP-*`/`EFF-*`/`MEM-001`) lives in
    `plans/requirements.md` §§ AGT/EFF/ORC/VER/GAP/MEM, not repeated here. Live proof
    (`tests/integration/test_effect_ledger_live.py`, `test_supervisor_live.py`) written, run only
    with explicit confirmation (`GOVERNANCE.md` rule 10). (Added 2026-07-19, sponsor directive
    `AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001` Wave 5 — see Changelog.)

37. **"Product agent" is an organizational label, not a real cooperating system — Wave 6 rescoped
    accordingly.** Prompted by a direct user question, during Wave 6 scoping, about what
    "product agent" actually refers to and a statement that no such agent exists to integrate with.
    Checked exhaustively before accepting that premise: every occurrence of "product agent" across
    decisions #18/19/21/22, `plans/requirements.md` (`OWN-004/009/010/013`, `FACT-001`, `DOC-006`),
    and every investigation artifact using the phrase
    (`full-surface-current-state.md`, `reconciliation_prototype.py`, `overwrite_lab.py`,
    `release-package-handoff-finding.json`) — none describe an implemented or even fully specified
    API, webhook, or schema with a real receiving counterparty. `overwrite_lab.py` simulates a
    "product agent" purely as a commit-author label (`git config user.name "Product Agent (lab)"`)
    on a plain local git write; the one "response" evidence artifact its companion prototype produces
    is literally labeled `"evidence": "product-agent ticket ACME-1234 (simulated)"`. `FACT-001`
    already defines its required input as coming "from repository inspection, an owning product
    agent, **or both**" — repository inspection alone was already sufficient; a cooperating agent
    was never mandatory. `DOC-006` (the schema that would formalize a real handoff contract) remains
    `RESEARCH-GATED`, and the requirements document's own Open Research Question #4 says point-blank
    the schema is "still open." **Conclusion: "product agent" has always meant, and continues to
    mean, "whoever or whatever currently maintains a product repository's technical facts and
    README/release/package content in practice"** — evidenced concretely as human maintainers
    pushing real commits (`full-surface-current-state.md`'s contributor data:
    `babar-raza`, `laurence-chen`, etc.) — never a distinct, addressable software system this project
    integrates with. This does not weaken decisions #18/19/21/22's substantive content (ownership
    boundaries, the product-facts field list, drift-protection obligations all remain correct and
    binding); it corrects only the implicit assumption that a cooperating counterparty exists to
    exchange a "handoff schema" with. **Wave 6 is rescoped accordingly**: the original bullet
    ("Product-agent integration: handoff schema, full-overwrite reconciliation, affected-surface
    planning, `workflow_call`/dispatch wiring") is replaced with "upstream-change watch and
    reconciliation" — this project watches for real upstream repository changes itself (via its own
    polling/detection, decision #38) and sources facts from its own already-built product inventory
    (`data/products.json` + `config/policies/*.yml`) and capability system, rather than waiting on
    or designing for a handoff from a system that does not exist. (Added 2026-07-19, user directive.)

38. **Durable-skip fast path was blind to real upstream README changes on the actual production
    runner topology — found, root-caused, and fixed ahead of the rest of Wave 6.** Surfaced while
    designing Wave 6's "watch upstream, trigger work" mechanism and treating it as a production
    problem rather than a feature request: `orchestrator.generate_repo()`'s durable-state fast path
    (`durable_skip`, Wave 4) required only `durable_state.accepted_facts_hash == facts_hash` before
    skipping validation entirely (`results = []`, blindly copying `durable_state.accepted_status`).
    `facts_hash` deliberately excludes README content (decision #11 — manifest/license/policy/
    prompt/schema-version only), and `existing is None` (no local marker) is the *normal* case on a
    fresh GitHub Actions runner, not the exception (`RUN-001`'s own design note: the marker never
    survives a fresh runner, and this project never pushes its own marker upstream, so the real
    repo's README never carries it either). **Net effect, verified directly against the existing
    regression test**
    (`test_fresh_runner_with_no_local_marker_skips_using_durable_state_alone`, which only ever
    exercised an *unchanged* source across two simulated fresh runners): on the exact topology this
    project runs on, once a repo's facts_hash-relevant inputs stabilize (typically after the first
    successful run), the system became **permanently blind to real upstream README edits, no matter
    how many times it reruns** — the precise problem Wave 6 exists to solve, defeated by an existing
    fast path built for a different concern (avoiding redundant LLM calls). A related, structural
    finding: the project has accumulated five independently-invented "did anything change" signals
    across five waves (`facts_hash`/`embedded_hash` — Phase 7-8; `durable_state.accepted_facts_hash`
    + CAS — Wave 4; `SupervisorStateV1.last_observed_upstream_revision` — Wave 5; this fix's content
    fingerprint — now) with no shared primitive and no prior end-to-end trace of how they interact —
    exactly how a hash designed to exclude README content ended up gating whether README content
    gets checked at all. Rejected fixes, considered and discarded before implementation: a blind
    `git fetch && reset --hard` on every call (would discard the uncommitted rendered span
    `test_second_run_is_idempotent_zero_llm_calls` depends on for decision #12's zero-LLM-calls
    guarantee); gating on `SupervisorStateV1.last_observed_upstream_revision`'s whole-repo commit SHA
    instead (too coarse — forces a rebuild/re-check on any unrelated upstream commit, e.g. a CI badge
    bump, and that field already has its own, different, correct purpose); populating
    `RepositoryFacts.commit_sha` for real (it is already one of `facts.py::_HASH_FIELDS` — a real,
    ever-changing commit SHA would change `facts_hash` on *every* upstream commit including ones
    irrelevant to README content, a straight regression of decision #12's guarantee, not a fix).
    **Decision: one canonical content-level fingerprint**, `readme/facts.py::
    compute_tracked_content_hash()` (README + LICENSE + community files — `CONTRIBUTING`/
    `CODE_OF_CONDUCT`/`SECURITY`/`SUPPORT`, decision #19's repository-file-managed class — via a new
    `FileInventory.community_paths`), computed from the baseline clone (always fresh already, zero
    extra clone cost) and required to also match (new field, `RunStateV1.
    upstream_content_fingerprint_at_accept`, additive/pydantic-safe for existing durable records)
    before `durable_skip` is allowed to fire; `_ensure_work_clone`'s local reuse is gated on the same
    fingerprint via a sidecar file sibling to (never inside) the work clone. Never reimplemented a
    second time — this is the one function both this fix and Wave 6's forthcoming
    `readme_reconciliation` specialist compare against. **A second, live (not merely forward-looking)
    bug was found and fixed in the same pass**: `orchestrator._record_accepted_state()` constructed a
    brand-new `RunStateV1(...)` on every write, silently dropping `domain_states`/`supervisor_state`
    — and `supervisor_state` is already written *today* by `supervisor/loop.py`'s
    `_record_supervisor_state()` (Wave 5), so any `org_repo` where both `supervise` and `run`/
    `generate --durable-state` are invoked already had `run` silently erase `supervise`'s recorded
    state on its very next call, in already-shipped code. Fixed via `model_copy(update={...})` on the
    current record (mirroring the pattern `save_domain()`/`_record_supervisor_state()` already use
    correctly), so both slots survive every write from this function too. **Sequenced deliberately
    as its own standalone fix, not bundled into Wave 6's feature work**, per direct user instruction:
    it corrects already-"proven" Wave 0-15/Wave 4 behavior under an existing, evidenced guarantee
    (`RUN-001`), so it is verified in isolation before Wave 6's specialist registry/LangGraph work is
    built on top of it. **Implemented and tested this pass**: `pytest -q` → 408 passed (up from 396),
    12 new tests including the concrete regression proof
    (`test_fresh_runner_with_changed_upstream_content_does_not_blindly_skip` — same
    two-separate-runner-directories shape as the existing fresh-runner test, but with a real upstream
    README edit between calls, asserting the second call now re-examines and re-renders instead of
    trusting stale history) and the state-preservation proof
    (`test_record_accepted_state_preserves_domain_states_and_supervisor_state`); `ruff check .`,
    `ruff format --check .`, `mypy src` all clean. Live re-proof against a real pilot remains pending
    explicit user confirmation (`GOVERNANCE.md` rule 10), the same discipline that already gated
    Wave 5's `test_effect_ledger_live.py`/`test_supervisor_live.py` before they were run for real.
    Structural weakness noted, not fixed here: two independent orchestration entry points
    (`generate_repo()`/`run` and `supervise_repo()`) still maintain separate "is this repo current"
    state at different granularities with no shared source of truth — traced through concretely and
    found *bounded* (worst case a redundant planning turn or capability call, not an incorrect
    action) rather than actively harmful, so not merged here; logged as a `BACKLOG` row rather than
    silently accepted as fine. (Added 2026-07-19, user directive — "treat this as a production
    problem.")

39. **First LangGraph specialist, routed through the Wave 5 supervisor — executes decision #27's
    Wave 6 commitment for real.** `langgraph>=1.0` added to `pyproject.toml` as a real dependency for
    the first time; decision #27's addendum committed to this in Wave 6-8, but it was never actually
    installed or used until this pass (confirmed absent from `pyproject.toml` before this change).
    The `readme_reconciliation` domain's specialist logic (`src/readme_agent/specialists/
    readme_reconciliation.py`) is a two-node `langgraph.graph.StateGraph` (`classify` -> `record`)
    whose **state is `DomainStateV1` used directly** — not a new, framework-specific schema, honoring
    decision #27's own stated concern about importing "a second, foreign schema." `org_repo` and the
    durable-state backend are invocation parameters passed via LangGraph's `config["configurable"]`,
    never part of the accepted-state shape. Node `classify` dispatches the new `classify_upstream_
    change` capability (decision #38's `readme/reconciliation.py` classifier, wrapped) via
    `dispatch_tool_call(..., caller_domain=README_RECONCILIATION)` — decision #34's dispatch-side
    domain check is the actual enforcement boundary here, unchanged and untouched by this graph;
    per decision #27's own clarification, "LangGraph's per-node tool binding is a request-time
    reliability/UX layer, not the enforcement boundary." Node `record` persists via the already-proven
    `state/domain_state.py::save_domain()`. `capabilities/domains.py::KNOWN_DOMAINS` gains its first
    real member, `README_RECONCILIATION = "readme_reconciliation"` — one domain does not trip
    `registry.py::_build()`'s `>1 domains` fail-closed sunset, so no existing capability becomes newly
    restricted.

    **`specialists/registry.py` mirrors `capabilities/registry.py`'s already-proven dispatch-table
    pattern** — `SpecialistManifest{domain, name, purpose, run}`, `all_domains()`/`run_domain()` — so
    Wave 7 adding a specialist is a new registration, never a new call site in
    `supervisor/loop.py`. This is the concrete answer to "LangGraph must be usable by later stages":
    the registry, not a hand-wired call, is what makes that true.

    **`supervisor/loop.py::supervise_repo()` gains a second, finer-grained convergence tier**, run
    *before* the existing coarse `is_fresh()` check's caller-visible short-circuit but *after* it
    fails to trigger (i.e., only when the upstream commit SHA actually changed) — and, critically,
    *before* the supervisor's own per-`org_repo` lock is acquired, since each specialist's own
    `record` step (`save_domain()`) acquires and releases that identical lock internally; holding it
    at the supervisor level first would deadlock. Iterates `specialists.registry.all_domains()`
    (today: one), runs each; if every result is `NO_CHANGE`, returns a new terminal status,
    `CONVERGED_NO_TRACKED_CHANGE` (added to `convergence.py::SuperviseStatus`'s documented vocabulary,
    constructed directly rather than via `final_status()`), records `SupervisorStateV1.
    last_observed_upstream_revision` so the coarse tier catches up on the next call, and stops with
    zero planner/LLM calls — the second convergence tier decision #39 adds, closing the real gap
    where the coarse commit-SHA check alone would force a full replan on *any* upstream commit,
    including ones touching nothing this tool tracks (e.g. a CI badge bump). Anything else feeds every
    specialist's classification into the planner's initial observation, alongside (not instead of) the
    existing `inspect_repository` bootstrap result.

    **A second, real, previously-hidden field gap was found and fixed while building the classifier**:
    `remove_span()` is a no-op once a span is already absent, so a real `OWNED_SPAN_LOST` (a
    maintainer deletes the whole `resources` span, leaving otherwise-identical prose) would otherwise
    silently misclassify as `NO_CHANGE` -- a stripped-content-hash comparison alone cannot distinguish
    "the span was never there" from "the span was just removed." Confirmed live via a failing test
    before the fix (`test_owned_span_content_alone_does_not_count_as_change` initially failed for an
    unrelated reason — a non-hex `facts_hash` fixture value the marker regex correctly rejected —
    caught and fixed before drawing any conclusion from a false negative). Fixed by adding
    `DomainStateV1.owned_span_present_at_accept: bool = False` (additive; generic on the model, any
    domain may use or ignore it, per `DomainStateV1`'s own each-domain-gives-it-meaning convention).

    Also found and fixed, unrelated to the classifier itself: `commands.py::cmd_supervise`'s exit-code
    mapping only recognized `CONVERGED_NO_CHANGE`/`CONVERGED_APPLIED` as success — the new
    `CONVERGED_NO_TRACKED_CHANGE` status would have exited `1` (treated as a CLI failure) despite being
    a fully converged, successful outcome; caught by direct test-writing (`TestSuperviseCommand::
    test_exit_code_matches_status`), fixed before it could surface as a real CI job going red for a
    correct result. New CI entry point `.github/workflows/readme-agent-supervise.yml`
    (`workflow_dispatch` only, no `schedule:` -- deferred per the same "manual dispatch first, prove
    it live, schedule later" decision the user made when this design was first proposed) -- the first
    workflow to invoke `supervise` at all (only `run`/`run-registry` had one before).

    **Implemented and tested this pass**: 437 tests passing (up from 408 after decision #38), new
    files `capabilities/get_product_facts.py`, `capabilities/classify_upstream_change.py`,
    `readme/reconciliation.py`, `specialists/__init__.py`, `specialists/registry.py`,
    `specialists/readme_reconciliation.py`, `.github/workflows/readme-agent-supervise.yml`, plus
    matching unit tests (`test_reconciliation.py`, `test_specialists.py`, new cases in
    `test_capabilities.py`/`test_capability_dispatcher.py`/`test_state_schema.py`/
    `test_supervisor_loop.py`/`test_cli.py`); `ruff check .`, `ruff format --check .`, `mypy src` all
    clean. `CAP-006`/`MEM-004` stay `PARTIAL` per `GOV-018` until a live, real-gateway proof exists
    (not merely unit-proven against a fixture planner) — see the Changelog for the live proof once
    run. (Added 2026-07-19, user directive: "execute phase b, make wave 6 execute e2e... do not push
    to product repos.")

40. **`mode: "disabled"` means push access is unverified, not "excluded from analysis" —
    read-only capabilities run against every registry entry regardless of mode; only the
    write/push path stays gated on `mode == "full"`.** Amends the 2026-07-19 correction recorded
    under decision #4 above ("decision 24/`PIL-011`'s 'regardless of mode' carve-out is about
    analysis *scope*, not a license to bypass [the allow-list] for live capability execution")
    for the read-only-capability case specifically — that correction was right that the *ad-hoc
    research-script* carve-out doesn't extend to production capability dispatch, but wrong to
    conclude from that that `mode: "disabled"` should block reads at all. It exists solely because
    push/full-cycle access to an org hasn't been verified yet (no repo has ever been pushed to by
    this project — decision #4's actual concern), not because the repository itself is somehow
    off-limits to look at. Every capability whose `side_effect_class` is `read_only_local`/
    `read_only_network` (`profile_repository`, `get_product_facts`, `detect_readme_gaps`,
    `classify_upstream_change`, `inspect_repository`/`orchestrator.inspect_repo()`) is gated by a
    new `registry/loader.py::require_listed()` instead of `require_permitted()`/`is_permitted()` —
    presence in `data/products.json` is the read authorization; mode is irrelevant. `supervise_
    repo()`'s own entry gate moves to `require_listed()` too, since most of a supervised run is
    read-only planning. `orchestrator.require_permitted()` and `registry/loader.is_permitted()`/
    `enabled_entries()` are unchanged and still the strict gate for the actual mutating pipeline
    (`generate_repo()`/`run_repo()`'s render+commit path, `run_registry()`'s sweep). Safety
    companion, closing the gap this relaxation would otherwise open: `supervisor/loop.py::
    _dispatch_and_record()` now independently checks `entry.mode == "full"` before dispatching any
    `local_write`/`remote_write` capability — previously `supervise_repo()`'s strict entry gate was
    the *only* place mode was enforced for a write-capable dispatch; relaxing that entry gate to
    `require_listed()` would otherwise have silently let a write-capable capability slip through
    against an unverified repo, which is the one thing decision #4 actually exists to prevent. No
    real `local_write`/`remote_write` capability is registered yet (`capabilities/registry.py`'s
    `_MODULES` are all read-only today), so this is proven by a direct, focused unit test against
    `_dispatch_and_record()` with a fake write-capable manifest, not (yet) an end-to-end proof —
    flagged, not hidden, the same honesty this project applies to every other `PARTIAL` claim.
    Explicitly out of scope: `run_repo()`/`run_registry()` itself still skips disabled entries
    entirely (unchanged); making the full pipeline perform an analysis-only pass for a disabled
    entry (stopping before render/commit) is a further, separable change to `run_repo()`'s internal
    branching, not decided here. §21 decision-ledger coverage: new row for decision 40. (Added
    2026-07-20, user directive: "the mentioned repo and all other repos with mode disabled should
    go through all the processes" — clarifying that `mode: "disabled"` reflects unverified push
    access, not exclusion from read-only processing.)

41. **Wave 7 design: `EFF-001`'s mechanism fixed by decomposition, plus seven agility/reliability
    fixes found by direct code verification and applied before any of the seven new specialist
    domains exist.** Two adversarial review passes against the first Wave 7 draft found it
    reproduced an already-rejected design: decision #36 already recorded that `generate_repo()`'s
    idempotency key (`facts_hash`) is computed mid-pipeline, not a call argument, so it can't be
    supplied pre-dispatch the way the effect ledger requires — the first draft proposed exactly
    this anyway, wrapping the whole pipeline behind one `gated_effector` capability. **Fix,
    implemented this pass**: `orchestrator.py` decomposed at its write boundary into
    `prepare_readme_candidate()` (read-only — clone, gap-detect, conditional LLM call, render,
    validate; returns a `ReadmeCandidate`) and `commit_readme_candidate()` (the one real write:
    persists `final_text` only if it differs from what's on disk, then durable-state write-back
    and evidence) — `generate_repo()` becomes a thin two-call wrapper, proven zero-behavior-change
    by the full pre-existing `test_orchestrator.py` suite passing unmodified. Both functions and
    `record_accepted_readme_state()` (renamed from the former private `_record_accepted_state`)
    are now public, since Wave 7g's specialist needs to call them across a module boundary
    ("depend on public seams, not `_`-private helpers"). `capabilities/render_readme_candidate.py`
    (read-only, unscoped) wraps `prepare_readme_candidate()`; the paired `gated_effector`,
    `commit_readme_write`, is deliberately **not built or registered this pass** — its
    `allowed_domains=["readme_presentation"]` references a domain that doesn't exist in
    `capabilities/domains.py::KNOWN_DOMAINS` until Wave 7g registers it alongside the domain
    itself, and `specialists/registry.py`'s own new completeness gate (below) would otherwise
    immediately flag it as orphaned.

    **The real reconciliation-check hook** (`EFF-001`'s literal remaining gap): `capabilities/
    registry.py` now resolves an optional module-level `reconciliation_check(arguments: dict) ->
    dict | None` the same way `execute` already is, exposed via `get_reconciliation_check()`.
    `effect_ledger.py::dispatch_gated_effect()`'s `pending`-branch (previously: unconditional
    `blocked_pending_reconciliation`) calls it, if registered, before concluding blocked — a
    non-`None` result backfills the stale `pending` record to `applied`, correcting the ledger's
    own audit trail instead of leaving it permanently stuck. Additive and backward-compatible
    (capabilities with no check keep today's exact behavior); proven against a synthetic effector
    (mirroring `EFF-002`'s own original proof), not yet against a real capability — that's Wave 7g's
    job. **Resolves the apparent registration-vs-`IMPLEMENTED` circularity explicitly, not
    silently**: the Build Checklist's "no `local_write`+ before `EFF-001` is `IMPLEMENTED`" gate is
    the already-built registration-time check (`registry.py::_build()`'s idempotency/retry_policy
    validation); `EFF-001`'s own `IMPLEMENTED` status is earned only once Wave 7g live-proves the
    reconciliation hook against `commit_readme_write` — mirroring exactly how `EFF-002`/`EFF-003`
    reached `IMPLEMENTED` via live proof against a synthetic effector first.

    **Seven agility/reliability fixes, each verified directly against the running code rather than
    assumed, applied now because they get measurably harder to retrofit once six more specialists
    exist** — prompted by direct user instruction to treat "adding more independent agents" as a
    production problem: (1) **per-specialist failure isolation** — `supervisor/loop.py`'s
    specialist-tier loop had no try/except; one specialist's unhandled exception aborted the whole
    `supervise_repo()` call before the bootstrap dispatch even started, discarding every other
    specialist's already-computed result (contradicts `SCL-001`'s accepted principle one level
    down). Now isolated: a raising domain gets a visible `DomainStateV1(accepted_status="ERROR",
    details={"error": ...})` and the loop continues. (2) **Domain-aware tool-schema filtering** —
    `registry.all_tool_schemas()` returned every capability unconditionally; the general planner
    (`caller_domain=None`) was offered domain-scoped capabilities it could only get
    `rejected_domain_denied` for, burning a planning turn nondeterministically — a concrete
    mechanism for two identical-repo-state runs converging in a different number of turns. Now
    takes `caller_domain` and filters. (3) **Shared change-detection primitive** —
    `readme_reconciliation`'s classify step was Wave 6's one hand-rolled instance; `state/
    change_detection.py::classify_surface()` extracts its general shape (generic fingerprint
    comparison plus an optional owned-marker concept), `readme/reconciliation.py` refactored onto
    it with zero behavior change, so Wave 7's six new specialists share one tested implementation
    instead of six independent chances to reproduce decision #38's exact bug class. (4)
    **`DomainStateV1.details: dict`** — a generic structured-payload field matching
    `CapabilityOutputCacheEntry.result`/`SupervisorStateV1.task_graph_snapshot`'s existing
    plain-dict convention two models away in the same file; without it, richer specialists
    (metadata's proposed values, a package/release handoff payload) would each invent an
    incompatible workaround. (5) **Domain/specialist registration completeness gate** —
    `specialists/registry.py::_build()` only ever checked one direction (a specialist's domain
    must be known); now asserts `domains.KNOWN_DOMAINS == set(_BY_DOMAIN)`, so a half-registered
    domain fails loudly at import time like every other registration mistake here, instead of
    silently producing a domain that never reports anything. (6) **`--domain` flag on `supervise`**
    — `specialists/registry.py::run_domain()` already let one domain run in isolation at the Python
    level; nothing exposed it operationally. Now a CLI-facing, usable-today version of "trigger
    only the README agent," independent of and well ahead of any future hosting-topology change.
    (7) **Always-written `specialist_results.json` evidence** — specialist-tier findings were
    previously visible only inside the LLM's own conversation content on the full-loop path, and
    not recorded as evidence at all on the `CONVERGED_NO_TRACKED_CHANGE` shortcut path (which
    didn't even generate an `evidence_dir`). Now written on both paths — one canonical place to
    audit every specialist's findings as domain count grows.

    **Specialist process-independence and future MCP-hostability — a design constraint made
    explicit, not new infrastructure.** Raised directly by the user, confirmed not previously
    written down anywhere in this project (checked `AGENTS.md`, this ledger, all of
    `requirements.md`). Two implications, binding on Wave 7's specialists: every specialist gets a
    cheap classify-first node (using the shared primitive above) before doing real work — not new
    architecture, Wave 6's own pattern made binding across all seven new domains instead of
    staying a one-off; and every `SpecialistManifest.run` binding stays narrow
    (`(org_repo, backend) -> DomainStateV1`, no hidden coupling to another specialist's internals
    beyond the durable backend), so swapping one specialist's implementation for a remote/MCP call
    later touches only that one registration entry. **No MCP server or remote-hosting code is
    built by this decision.** That work is named explicitly as a future **Wave 10 — "Specialist
    process-independence and MCP-hosted deployment,"** added to the Build Checklist after Wave 9,
    with a concrete trigger (not "someday"): Waves 7-9 complete, `AGT-005` has real multi-specialist
    evidence, and Wave 9's controlled rollout produces *measured* operational cost from running the
    full in-process supervisor for a narrow check — at which point decision #27 is revisited
    specifically for the specialist-hosting question (its core supervisor-loop reasoning is
    otherwise unaffected) and the official MCP Python SDK is evaluated per `GOV-015` before
    hand-rolling a protocol implementation. Neither Wave 8 (verification/repair) nor Wave 9
    (portfolio proof/rollout) is about deployment topology, so neither absorbs this work either.

    **`AGT-005`'s evidence ceiling corrected for decision #40's dependency**: earlier Wave 7
    planning capped `AGT-005`'s achievable evidence at the 3 previously-enabled pilots. Decision
    #40's `require_listed()` change means every read-only specialist (five of Wave 7's seven new
    domains) becomes live-testable against all 25 registry entries instead of 3, once Wave 7's own
    specialists exist to test — a materially stronger evidence base than this project could
    previously offer for that requirement. The one real mutating specialist (Wave 7g) stays capped
    to the registry's `mode: "full"` entries by decision #40's own new mode gate — the correct,
    intentional safety boundary, not a coverage gap to work around.

    Sequencing: 7a (this pass) does all of the above, before any of the seven specialist domains
    are built, since every later sub-wave depends on these fixes and none of them depend on any
    later sub-wave. 43 new tests (480 passed, up from 437, 15 deselected unchanged); `ruff check .`,
    `ruff format --check .`, `mypy src` all clean. §21 decision-ledger coverage: new row for
    decision 41. (Added 2026-07-20, user directive: "treat adding more independent agents as a
    production problem... fix it before we reach that point... smooth out every wrinkle that could
    affect our future direction.")

42. **Wave 8 design: independent verifier (`VER-001`/`VER-002`), built through two rounds after an
    external whole-system review and two independent adversarial passes each found real defects the
    first design would have shipped.** Mid-design, the user shared a large external review of the
    whole project (verdict: "structural redirection required"). Rather than accept it wholesale, each
    checkable claim was verified against the actual repo, not the review's own extracted archive
    (self-disclosed to exclude `.git`/`.github`/`runs/`): three of its seven P0 claims were refuted by
    direct evidence (a stale "548 passed/3 failed" test count -- the real run was 551 passed, 0
    failed; a `facts_hash`-collision scenario already prevented by `commit_sha` inclusion; a
    "governance blocks autonomous state persistence" claim contradicted by every "managed remote"
    reference in `AGENTS.md`/`GOVERNANCE.md`/this file being scoped to product repos, never this
    project's own state ref), two were already-tracked, deliberate positions in this project's own
    history (not new discoveries), and two were confirmed real and previously untracked. Per user
    direction, the two confirmed findings were fixed immediately, standalone, ahead of Wave 8 itself:

    - **`org_repo` trust gap**: `supervisor/loop.py`'s planner-dispatch path used
      `arguments.setdefault("org_repo", org_repo)`, which only fills the trusted active repo when the
      planner's own tool-call JSON omits one -- a planner-supplied `org_repo` (hallucination,
      injected content, a plain mistake) would silently win instead. Fixed to an unconditional
      override (`arguments["org_repo"] = org_repo`); regression test proves a fixture planner
      supplying a different, unlisted `org_repo` still dispatches against the real active repo.
    - **CI git-identity gap**: neither shipped workflow (`readme-agent-run.yml`/`readme-agent-
      supervise.yml`) configures a git commit identity anywhere; every real-commit proof recorded in
      this project's history ran on a machine that already had one set globally, never confirmed
      against a genuinely fresh, hosted runner (which has none). Fixed by setting a `--local` (never
      `--global`) identity on every work clone in `gitsafety/clone.py::create_work_clone()`;
      regression test proves a real commit succeeds with zero ambient global/system git config
      visible (a scratch `HOME`/`GIT_CONFIG_NOSYSTEM` override).

    A first-round Wave 8 design (a two-facet `independent_verification` domain: an in-graph
    pre-apply gate for the one real write, plus a post-hoc cross-domain auditor) was directionally
    right but unverified against the actual mechanics it builds on. Per explicit direction to "treat
    this as a production problem" -- this project's own established standard, decision #41's own two
    adversarial review passes -- two independent reviewers with no shared context (one fact-checking
    every claim against the real code, one adversarially hunting for rerun-consistency failures) were
    run against it. **Both found defects serious enough that the first-round design, if built as
    written, would have crashed on every single run, not a rare edge case**:

    - `DomainStateV1.details` has no LangGraph merge reducer (a plain, un-annotated `dict` field, so
      a node's returned `details` fully REPLACES the field, last-write-wins) -- invisible with every
      existing two-or-three-node specialist graph (at most one node writes `details` before the next
      reads it), but the first design to need three sequential nodes to all see accumulating keys. A
      naively-written verify node between `render` and `commit` would have erased `render_result`
      before `commit`'s own `assert render_result is not None` ever ran, on the accept path, every
      run. Fixed with a shared helper, `state/domain_state.py::merge_details()`, not a blanket
      reducer (which would let large transient payloads like `render_result`'s full candidate text
      silently survive into the durably-persisted record forever -- confirmed a second time as a
      real, live regression during Wave 8b's own build, caught by a dedicated test before it shipped,
      not assumed fixed by the helper's mere existence).
    - `effect_ledger.py::dispatch_gated_effect()` writes a `pending` ledger entry BEFORE
      `dispatch_tool_call()`'s own cheap checks (unknown capability, permission/domain denied,
      missing argument) run -- a pre-existing latent defect in the Wave 5 ledger itself (`EFF-002`),
      not introduced by this wave, but the new `verification_verdict` argument is exactly the kind of
      caller mistake most likely to trigger it, converting a clean rejection into a permanently stuck
      `blocked_pending_reconciliation` record. Fixed with a new, optional `precheck(arguments) ->
      str | None` hook (`capabilities/registry.py` resolves it the same attribute-based way
      `reconciliation_check` already is), checked before any lock/pending-write -- a structural fix
      to the shared ledger, not a one-off patch, logged as `EFF-004`.
    - Nothing in this codebase bounded *repeated* failures across reruns (`check_repair_exhausted()`
      only bounds turns *within* one run) -- a bug in the verifier itself would fail closed correctly
      (no bad write) but not safely (a real LLM cost, repeated forever, indistinguishable from
      one-off noise). Fixed with `DomainStateV1.consecutive_failure_count`/`last_failure_reason` +
      `record_failure_or_reset()`, wired into `readme_presentation` (the one domain that writes)
      via a new `save_domain_with_failure_tracking()` -- explicitly *not* retrofitted into the other
      eight specialists this pass (a real, deliberately deferred follow-up, not silently claimed
      done). A named, required carve-out: 22/25 real registry entries have no `policy_profile`
      configured (confirmed by direct inspection of `data/products.json`), so `get_product_facts`-
      dependent domains `ERROR` every run, forever, by design -- `_classify_error_reason()`
      recognizes this by content (`"missing_policy_profile"`), not just the `"ERROR:"` prefix's own
      outcome-class segment, so it never falsely escalates.

    **Architecture, built on the corrected mechanics**: one domain, `independent_verification`
    (`capabilities/domains.py`'s ninth), one specialist module, two facets -- (8b) an in-graph
    pre-apply gate: a new capability `verify_readme_candidate` (`execution_type="validator"`, unused
    since `CAP-004`), dispatched by a new `_verify_node` in `readme_presentation`'s own graph (now
    `render -> verify -> commit -> record`) under `caller_domain=independent_verification`, distinct
    from that module's own `render`/`commit` nodes' `readme_presentation` domain -- the one
    deliberate exception to "one module, one domain identity" in this codebase, made a real boundary
    (not a convention) by `commit_readme_write`'s new required `verification_verdict` argument, so a
    wiring bug that skips the verify node fails closed (a missing-argument `execution_error`), never
    silently bypassed; (8c) a post-hoc cross-domain auditor, structurally identical to `cross_surface_
    validation`, extended with evidence-completeness (`verification/completeness.py`, data-driven
    per-domain expected-key table sourced from each capability's own `produced_outputs`),
    requirement mapping (a new `CapabilityManifest.requirement_ids` field, populated for three
    capabilities with an unambiguous domain attribution this pass -- `commit_readme_write`/`verify_
    readme_candidate` map to `readme_presentation`, where their real-run outcome actually lives, not
    their own `allowed_domains`, a data-driven override table, not conditional logic;
    `classify_upstream_change` maps to its own `allowed_domains`), adversarial cross-domain checks (a
    second-order check on `cross_surface_validation`'s own `inconsistencies`), and failure-escalation
    visibility. (8d) Wires the auditor's findings into the planner conversation, a distinct
    `escalation_alert` decision when a domain crosses a threshold (3, an explicit tunable with no
    operational evidence yet), and a run-level evidence-completeness gate (`_assert_evidence_
    complete()`, structural not semantic -- an empty task graph on the shortcut path is correct,
    honest content, not missing evidence) closing the exact class of gap decision #41 already found
    once. `MEM-005` (Wave 7's own logged finding) folded into 8a's foundational sub-wave, honestly
    narrower than its full description: closes the "sibling never successfully recorded" case, not
    the deeper "hard-failed mid-run" case, which would need threading this run's in-memory specialist
    results through the generic `run_domain()` dispatch signature -- a larger, more invasive change
    left open, not silently claimed closed.

    **Honestly unmet, not fabricated**: `VER-001`/`VER-002` reach `PARTIAL`, not `IMPLEMENTED` --
    `GOV-018` requires live proof, and none has run yet (deferred to a consolidated pass alongside
    Wave 9's own full-registry proof and the explicit "full `products.json` pilot" ask, the same
    "one credential dance, not one per sub-wave" precedent Wave 7b-7e already established). The
    CLI path (`orchestrator.run_repo()`, still live via `readme-agent run --mode full`) commits with
    zero verification step -- `VER-001`'s guarantee covers the `supervise`-path specialist only; this
    is a second, independent, real entry point to the same effect, named explicitly rather than
    implied closed (tracked as a new `BACKLOG` row, a sibling to the already-logged `ORC-004`). 620
    tests passing (up from 551 before both the immediate corrections and Wave 8 itself); `ruff check
    .`, `ruff format --check .`, `mypy src` all clean. §21 decision-ledger coverage: new row for
    decision 42. (2026-07-21, user directive: "treat this as a deeper production problem" following
    the external review; both adversarial-review passes and all fixes above were user-directed.)

43. **Wave-entry reconciliation gate — GOVERNANCE.md rule 11.** Prompted by direct user
    instruction: "Establish that each wave of work first check previous wave's work to match them
    with the master and requirements." This project's own history already shows the cost of
    skipping this: Wave 8's design (decision #42) needed a late, ad hoc external review plus two
    independent adversarial passes to catch defects (`DomainStateV1.details`'s missing merge
    reducer, `dispatch_gated_effect()`'s pending-write-before-validation ordering bug) that
    reconciling against the actual prior-wave code earlier would have surfaced sooner; separately,
    the §21 decision-ledger coverage table has accumulated real gaps at wave boundaries purely
    because nothing forced a check at the point a new wave started (`GOV-019`: decision 32 never
    got a row; `GOV-020`: decisions 36–39 never did either — both found by accident, during
    unrelated tasks, not by a standing check). Codified now: before Wave 9 (next) or any future
    wave begins, the immediately preceding wave's actual delivered state — its code, tests, and
    evidence — is checked against `plans/master.md` (that wave's Decision Ledger entry, Status,
    Build Checklist line) and `plans/requirements.md` (every requirement row it touches), not
    assumed correct because a prior Changelog entry said so. This is distinct from `GOV-010`'s
    existing "review requirements when a phase closes" — that is a review obligation on the
    closing wave; this is an entry gate on the *next* wave, and it names exactly what must match
    (Decision Ledger, Status, Build Checklist, requirement rows), not "review" left open-ended. Any
    overclaim found (a status marked done without the evidence `GOV-007`/`GOV-018` require, a
    Build Checklist line checked with a gap still open) is corrected — downgraded, or logged as
    `BACKLOG` per `GOV-014` — before the new wave extends the affected surface. See `GOV-022`.
    First application is Wave 9 itself, which must open by reconciling Wave 8's `PARTIAL`
    `VER-001`/`VER-002` (live proof still deferred), the CLI zero-verification-step gap already
    logged as a `BACKLOG` sibling to `ORC-004`, and the `GOV-019`/`GOV-020` coverage gaps, before
    any Wave 9 code is written. (Added 2026-07-21, user directive.)

44. **Changelog relocated to `logs/`; `master.md` edits now require explicit per-instance
    confirmation.** `master.md` had grown to 3,761 lines, the large majority (1,451) pure
    historical narrative — the Changelog — that GOVERNANCE.md rule 1 already says doesn't belong
    in a document meant to describe only the *current* state. `requirements.md`'s own 660-line
    Changelog had the identical problem and cross-referenced this one constantly. Both relocated
    verbatim into a new root-level `logs/` directory: a small, stable index (`logs/README.md`)
    plus dated shard files (`logs/<YYYY-MM-DD>.md`, one per day — five today, 2026-07-17 through
    2026-07-21), each carrying its own local index table (date, source, decision refs,
    requirement-ID refs, wave/phase refs, one-line summary) so an entry is reachable by any
    identifier this project already uses, not just by reading the whole file top to bottom.
    Neither document lost any content — the relocation script
    (`scripts/retrofits/relocate_changelogs_to_logs_dir.py`) asserts every original entry's text is
    reproduced exactly once (modulo a source tag) before writing anything. A follow-up retrofit
    (`scripts/retrofits/split_logs_shard_into_daily_files.py`) later split the initial monthly
    shard into daily ones after a blind-agent compliance test found it already 3x over its own
    size guidance — see `logs/2026-07-21.md`.
    Going forward, `master.md` is gated rather than freely agent-editable: any edit requires the
    same explicit, per-instance user confirmation already required for pushes (GOVERNANCE.md
    rule 12, `GOV-023`); `logs/` stays freely, immediately appendable with no gate, since absorbing
    routine history writes is its whole purpose. `requirements.md`'s own editing procedure is
    unchanged — only its Changelog section moved. (2026-07-21, user directive.)

45. **Production-hardening reconciliation for the autonomous supervisor loop — why seven LLM-gateway-usage gaps went unlogged, a corrected 10-part target design, and a probe-script bug found and fixed live.** An external analysis (not authored by this project) reviewed how the `supervise` loop actually uses `llm.professionalize.com` versus its own aspirational description and named seven gaps (G1–G7: hardcoded/unhashed supervisor prompt; a shallow planner dossier; deterministic-not-agentic specialist selection; blind-retry-only repair; a deterministic-not-LLM verifier; unwired `qwen3-embedding-8b`; no agentic-loop golden-set). Reconciled against the live text of this ledger, `requirements.md`, and `GOVERNANCE.md` before designing anything (per rule 11's own reconciliation discipline, applied here proactively rather than only at a wave boundary): G3 was already tracked (`ORC-003`, `PARTIAL`); the other six were genuinely unlogged, each falling in the same class of seam GOV-019/GOV-020 already named — a review pass scoped to *correctness* (Wave 7's reliability review, Wave 8's two adversarial passes) never asked whether the *mechanism itself* was sufficient, and the one 2026-07-19 assessment that did produce `GOV-016`/`LLM-016` from `llm-gateway-characterization.md` swept that document only partially, missing its embedding-model recommendation entirely.

    A full research → design → adversarial-review pipeline followed (three research passes over the real execution flow, the governance documents, and the gateway's own evidence; one design pass; one independent adversarial-review pass, mirroring decision #42's own two-pass precedent). The adversarial pass found two defects serious enough to change the design before anything was written down, both personally re-verified against the code/evidence before being accepted: (1) the proposed lock-race fix (`SCL-005`) would have leaked a new run-scoped lock for its full ~900s lease on the `CONVERGED_NO_TRACKED_CHANGE` shortcut path — confirmed directly: that shortcut (`supervisor/loop.py`) returns *before* today's existing lock is ever acquired, so a naive widening that didn't also cover it would introduce a worse race than the one it fixed; (2) the "~96k-token proven-safe context ceiling" the design's token-budget item leaned on (`llm-gateway-characterization.md` L1) was traced to `plans/investigations/tools/probe_llm_gateway.py:157` and found to rest on a real, one-line bug — a fixed-length filler string whose repeat count never scaled with the ladder variable before slicing, so every rung from 2k to 96k "approx tokens" silently sent the same ~1,400 real tokens. The script was fixed and re-run live against the real gateway this session (not deferred): `qwen3-next`'s real, proven ceiling is ~71,069 tokens with perfect needle recall; `gpt-oss` fails needle recall at every real size tested, including the smallest (~1,494 tokens); a new multi-turn conversation-growth probe measured a realistic dossier-shaped planner turn at 639→686 real tokens across one tool-call round trip — three orders of magnitude below the proven ceiling. Full results: `plans/investigations/llm-gateway-context-ceiling-corrected.md` (supersedes L1). `LLM-018`/`LLM-019` track the correction; `LLM-018` also found the resulting "1/10" `gpt-oss` structured-output figure is itself misreported in four sites (real evidence: 0.4, and a second independent run this session measured 0.8 — a swing large enough that neither number should be trusted in isolation without the N≥20/≥3-session follow-up this project's own investigations already recommended).

    User pushback on the first design draft was itself substantive, not rubber-stamped: (a) "why not [dynamic specialist selection / CI concurrency groups]?" prompted a second investigation, not a restated deferral — reading `specialists/github_generated_surface_audit.py`'s own docstring found that classify-first nodes pay their live GitHub API cost *unconditionally*, before classification, so the cheap gate saves a duplicate record, not the network call; the evidence-backed fix is a cheap, already-proven SHA probe (`gitsafety/clone.py::remote_head_sha()`, already wired into `profile_repository`, not into `supervise_repo()`) short-circuiting before the clone even happens, not an LLM judgment call about which audits to skip — the latter stays rejected, but with a named, falsifiable revisit trigger (`ORC-006`), not a silent one-line dismissal, matching decision #28/#33/#41's own pattern; (b) dislike of flat `.txt` prompt storage led to a categorical, schema-validated replacement reusing this project's own most-established idiom (a `PromptManifest` Pydantic model + an eagerly-validated registry, mirroring `capabilities/schema.py`+`registry.py` and `specialists/registry.py` exactly) rather than a bespoke new pattern, migrating `relationship_explained` into the same mechanism so only one prompt-governance posture exists going forward (`GOV-024`); (c) "probe before writing anything" about the token budget is what surfaced the script bug above, rather than letting a design ship on unvalidated evidence.

    **Corrected 10-part target design** (full text in the requirements rows below; not restated in full here per this document's own "current state, not narrative" scope): (1) prompt governance — categorical YAML `PromptManifest` + registry, not `.txt` (`GOV-024`); (2) dossier summarization with a token budget sized off real `usage.prompt_tokens`, not a guessed constant or `tiktoken` (`AGT-008`); (3) CI fan-out (`SCL-008`) plus the SHA-probe short-circuit (`ORC-006`) plus a preflight-and-evidence-write-on-failure fix; (4) the corrected two-lock-ref design plus a shared GitHub Actions `concurrency:` group (`SCL-005`, extended); (5) repair/verifier depth rejected with a falsifiable trigger, not an untriggered close (`VER-006`); (6) `qwen3-embedding-8b` wired into a batch job only, never the per-run planner loop (`LLM-017`); (7) an agentic-loop golden-set (`OPS-011`), also the measurement source for `ORC-006`'s and `VER-006`'s own revisit triggers; (8) a `policy_profile` coverage report + scaffolding CLI, shortening not eliminating human authoring (`ONB-004`); (9) model-routing guidance unchanged in substance, corrected on the two evidence points above.

    **Wave-sequencing recommendation, not yet actioned**: fold the corrected hardening items (1–4 above) into a new foundational sub-wave prepended to Wave 9's already-designed `9a`–`9f` sequence (renumbering the existing `9a`→`9b` … `9f`→`9g`, new hardening work becomes the new `9a`), matching the established `7a`/`8a` "foundational sub-wave" precedent rather than an invented decimal "Wave 8.5" — the adversarial review flagged decimal numbering as contradicting this project's own twice-used convention. This requires a corresponding edit to Wave 9's own separate design file (outside this repo), not made in this pass. Items 6–8 and the CI-fan-out portion of item 3 remain a later **Wave 11** (not reusing "Wave 10," already reserved by decision #41 for MCP-hosted deployment topology, a different axis, trigger not yet fired).

    **Docs-only pass, per user's explicit choice**: no code changes beyond the one live, credentialed probe fix-and-rerun above (a side-effect-bounded, one-time action explicitly requested to ground a number in fact rather than assumption) and this ledger/requirements entry itself. All nine implementation items remain `BACKLOG`/`PARTIAL`, not `IMPLEMENTED` — this entry documents the design and its evidence, per `GOV-018`, not a claim that any of it is built. (2026-07-21, user directive: reconcile the external review, design a production-grade autonomous system, and probe the gateway for facts rather than assumptions before documenting a token budget; per-instance `GOV-023` confirmation obtained before this edit, scoped exactly to this entry plus its §21 coverage row.)

46. **Master-plan structural-integrity incident and the mechanical fix that replaces prose-only governance; formal anchor for the 2026-07-22 full-project truth audit.** A concurrent agent session — working without GOV-023's edit-confirmation gate — appended ten foreign top-level sections (`Plan Forensics` through `Execution Readiness Certification`) directly after `## Changelog`, violating rule 2's fixed section order. Triaged claim-by-claim: four substantive claims were already tracked (`GOV-009`; `OWN-014`/`SURF-005`/`VAL-009`/`SAFE-010`/`NFR-008`; `DOC-007`; decision #43/`GOV-022`); one ("`VER-004` evidence unimplemented") was factually wrong — `VER-004` reached `IMPLEMENTED` 2026-07-21 with live self-heal proof. The foreign sections were removed; their one legitimate underlying concern — "no automated integrity check for plan mutations" — is exactly what this decision builds.

    Two mechanical backstops replace the prose-only rule: (1) a local pre-commit hook (`scripts/governance/validate_plan_structure.py`) rejecting a commit that breaks `master.md`'s section order, `requirements.md`'s ID/Status/Priority validity, `logs/` index consistency, or specialist/module-map completeness against `docs/architecture.md`, catching this incident's exact shape before a commit can complete; (2) the same script as a required CI step, backstopping a hook-bypassed or hookless commit. `GOV-009` (`PLANNED` since early in this project) is what this actually builds, not a new parallel requirement.

    Separately, and independently, a concurrent "full-project truth audit" the same day (`plans/investigations/full-project-truth-audit-2026-07-22.md`) produced the most thorough independent verdict this project has received: `NOT PRESENTABLE`, Level-3 POC (scores: overall 3/8, presentation intelligence 3/8, autonomous runtime 3/8, reliability 2/8, pilot readiness 2/8, production readiness 1/8). It independently re-derived several of this project's own known gaps by different means (a real, clean `pytest -q` run of 824 passed/18 deselected in 410.22s, confirming the master Status section's 622-test snapshot is stale; a live `gh api` check confirming `push=true`/`admin=true` on all three enabled pilot repositories — `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`, `aspose-3d-foss/Aspose.3D-FOSS-for-Java`, `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` — resolving, for these three, the previously-open question of whether the acting identity needs a fork-based write path: it does not, direct branch/PR access is confirmed) and named several genuinely new ones this project had not yet logged: no `remote_write`/PR-lifecycle capability exists at all (`PIL-014`); durable state failure is currently best-effort, not fail-closed (`RUN-005`); no durable, deduplicating trigger-intake queue exists (`RUN-006`); no health/backlog observability surface exists (`RUN-007`); the three enabled pilots are all Java, so calling them "heterogeneous" would be a false claim (`PIL-012`); and no committed, independently-reproducible three-repository acceptance bundle exists (`PIL-013`). Its own added `requirements.md` rows for these (`PIL-012`–`014`, `RUN-005`–`007`) correctly cited their real originating decisions (`10`/`19`/`24`/`26`/`32`/`33`) plus the investigation report by name — an initial read of this entry drafted here mistakenly claimed these six rows cited "Decision 45" and needed correcting; re-verified directly against the file and found false before publishing, and struck rather than left standing. Only `SCL-008` cites decision #45, and correctly (`SCL-008` is explicitly item (3) of decision #45's design). This entry (#46) is added to those six rows' traceability columns as a supplementary cross-reference — since it is now this project's formal anchor for the 2026-07-22 audit's findings — not as a replacement for an incorrect citation, since none existed.

    That audit's own drastic-action recommendation is adopted here as this project's current position, not merely noted: freeze new specialist/domain abstractions until `AUD-001`–`007` close; retain the registry, safety model, state/CAS primitives, deterministic rendering, validators, and supervisor — all independently confirmed sound by this project's own prior decisions and by this external audit; use `supervise` as the sole pilot path and label `run` compatibility-only during the pilot (do not delete or rewrite either path until parity/migration evidence exists — a lighter-weight interim step than a full pipeline unification, adopted first); replace closure-by-unit-test with a real `PIL-013` lifecycle bundle as the pilot acceptance bar. Given at least two concurrent sessions were found actively editing these same plan files today: `git status`/`git diff` were re-checked immediately before this entry was written, not just at session start, per this entry's own precedent for future sessions doing the same. (2026-07-22, user directive.)

47. **Supervise-time registry drift self-heal (`CORE-033`).** Built the same day, by a third concurrent session, independently of this entry: `src/readme_agent/registry/self_heal.py`, wired into `commands.py::cmd_supervise()` ahead of preflight/allow-list gates, closes the window where a repo GitHub added since the last weekly `update-products-registry.yml` scan is invisible to `data/products.json` until that cron runs. Fail-open (never blocks supervision; every failure degrades to a `SKIPPED_*` result), fail-closed on the write itself (every merged entry re-validated against `ProductEntry` before the file is replaced; new entries always land `mode: "disabled"`, never auto-enabled), throttled via a TTL marker so a sequential portfolio pass scans GitHub once, not once per repo. Not this project's own end-to-end write-cycle safety net -- `data/products.json` is config-as-data, not a target-repo surface, so this correctly sits outside capability dispatch and the effect ledger entirely, per its own module docstring. Tests: `tests/unit/test_registry_self_heal.py`, `tests/unit/test_cli.py`. This entry exists to give the module's own already-shipped `(CORE-033, decision #47)` citation a real Decision Ledger record to point to -- it referenced this number before either this entry or `requirements.md`'s own `CORE-033` row (traced to decision #40) anticipated it; `CORE-033`'s own traceability is unchanged (decision #40 is still its origin), this decision is this specific self-heal mechanism's own record. (2026-07-22.)

    Addendum, from the session that built the mechanism (the "third concurrent session" above),
    completing this record: (a) **trigger** — `aspose-words-foss/Aspose.Words-FOSS-for-.NET`
    published upstream 2026-07-21 and absent from `data/products.json`; the user directed the
    onboarding sprint to "also be healing", i.e. make registry drift a self-healed class at
    runtime rather than hand-running the refresh script once. That repo's heal is the mechanism's
    live acceptance proof. (b) **Requirement-ID collision resolved** — the requirement row for
    this mechanism is **`CORE-034`** (the module's original `CORE-033` citation collided with
    decision #40's read/write gate-split row, exactly the dangling reference this entry flagged);
    module, wiring, workflows, and tests now cite `(CORE-034, decision #47)`, and `CORE-034`
    flips to `IMPLEMENTED` only on the live Words/.NET proof per `GOV-018`. (c) **One discovery
    implementation** — the script's discovery/merge core moved to
    `src/readme_agent/registry/discovery.py` (GOVERNANCE placement rule 2), the CLI became the
    thin wrapper `scripts/data-refresh/update_products_registry.py` (the registry row's own
    "move to `data-refresh/` when next touched"), invariant tests migrated name-intact to
    `tests/unit/test_registry_discovery.py`; the heal caps GitHub 403 waits at 60s via
    `RegistryScanRateLimited` where the cron wrapper keeps wait-forever semantics — without the
    cap, "fail-open" would silently sleep out a rate-limit reset inside supervise.
    (d) **CI wiring** — `readme-agent-supervise.yml` surfaces a healed `data/products.json` as a
    PR on the SAME branch as the weekly cron (`chore/update-products-registry`) so runtime-heal
    and cron diffs dedupe into one open PR, never a push to `main` (`OPS-008` posture);
    `readme-agent-portfolio.yml`'s matrix jobs run `--no-registry-heal` with one dedicated
    `heal-registry` job per pass. (e) **Named honestly** — this widens *read*-eligibility: a
    healed entry becomes `require_listed()`-eligible (decision #40's read gate) immediately,
    without PR review, bounded by the human-curated `data/families.json` org list and the FOSS
    naming regexes; the write surface is unchanged (`disabled` until a human follows
    `docs/policy-authoring.md`), and `ONB-001`'s regex-robustness limitation is deliberately
    unchanged. (2026-07-22, user directive; per-instance `GOV-023` confirmation obtained via the
    approved sprint plan, scoped exactly to this addendum plus the `CORE-034`/`CORE-023`/
    `CORE-032`/`OPS-005`/`ONB-004` requirement-row updates.)

48. **Effect-ledger lock holder-identity revalidation (`EFF-005`), and the verifier-accept gate's move from a literal string comparison to a re-derivable token (TC-15).** Two independent hardening fixes this same session, both closing gaps Phase 13's own adversarial machinery audit found (F3, F4) — building on decision #46 rather than restating it. `capabilities/effect_ledger.py::dispatch_gated_effect()` now calls the new `StateBackend.lock_still_held(lock)` (implemented in `state/git_backend.py` by re-fetching the lock ref and comparing `holder_id`) immediately before its terminal `applied` write; a lease that outlived `LOCK_LEASE_SECONDS` and was legitimately reclaimed by a second runner now leaves the ledger record `pending` rather than dishonestly recording sole authorship — proven by `tests/unit/test_effect_ledger.py::TestDispatchGatedEffectLockRevalidation` (a slow-effector-outlives-its-lease scenario, not just argued in prose). Separately, `commit_readme_write.py::precheck()`'s `verification_verdict` check is no longer a plain `== "accept"` string comparison — `verification/checks.py::compute_verification_token()` derives a value from `org_repo`/`facts_hash`/`fresh_fingerprint` that only `specialists/readme_presentation.py::_verify_node` computes, and only after a real accept for that exact candidate; `precheck()` re-derives and compares. `tests/unit/test_capabilities.py::test_precheck_rejects_a_hardcoded_accept_literal` proves the exact F3 regression (a hand-authored or wiring-bug call typing the literal `"accept"`) is now rejected. Both named honestly, not oversold: same-process consistency checks against an accidental wiring bug, not cryptographic secrets or a defense against a deliberately adversarial caller — `compute_verification_token()`'s own docstring states this plainly. Also this session (TC-16/17/23, Phase 13 §13.4 Pillars A/C): `audit_package_release_surfaces.py` sorts releases by `published_at` before selecting "latest" (`SCL-007` → `IMPLEMENTED`); a real, registered `stop` capability (`capabilities/stop.py`) lets `supervisor/loop.py` distinguish an explicit stop intent from an unrecognized/hallucinated capability name in telemetry (`AGT-006`); and `SupervisorStateV1.in_flight_run_id`/`in_flight_domains`, written before the specialist loop begins and cleared by the next normal completing write, close `VER-005`'s residual process/runner-kill blind spot via the new `effective_domain_coverage_complete()` helper. `PRL-002`'s state shape (`OpenProposalV1`, `state/schema.py`) is added ahead of the `remote_write` capability that will populate it (`TC-08`, not yet built — this entry's own hardening work, plus `TC-06`'s new `PRL-*` requirement rows, are explicitly sequenced to precede it, per Phase 13/14's own reasoning about why skipping them compounds into a live duplicate-write hazard). (2026-07-22.)

49. **Production-hardening pass: a policy-profile fabrication incident found and fixed with real
    verification tooling (`ONB-004`), and the within-run clone-redundancy root cause behind a live
    timeout, fixed structurally (`SCL-009`).** Triggered by two problems surfacing during the
    previous sprint's live proof of `CORE-034`'s Words/.NET self-heal: 4 failing
    `test_registry_loader.py` tests, and a 300s baseline-clone timeout on that same newly-published
    repo. Investigated thoroughly per explicit user direction to treat both as production problems,
    not local patches — separating symptom from root cause in each case.

    **Registry-readiness incident.** The 4 failing tests turned out to be *correct*: a concurrent
    session had already flipped 22 entries `disabled`→`dry_run` (found committed to `main`, not
    merely a working-tree experiment — the user separately confirmed this broadening is intentional
    per decision #24/`PIL-011`, and a sibling session rewrote the count-pinned tests to a drift-proof
    invariant), but a *further*, still-uncommitted session had then mass-generated 22
    `config/policies/*.yml` files by pattern substitution to fill the resulting null `ecosystem`/
    `policy_profile` fields. Direct inspection found this violated `docs/policy-authoring.md`'s own
    written rule (never construct a link by string-formatting family/platform) and decision #4's
    business-facts posture: every profile carried an identical, copy-pasted `MIT` license and a
    `products.aspose.org` URL guessed from the family/platform pattern — and `data/aspose_com_links.json`
    had **zero** `.org` entries anywhere to verify against. Live-checking all 25 non-disabled
    entries confirmed 9 of the 22 guessed `.com` platform URLs were genuinely wrong (Aspose's real
    site uses a combined `-net`/`-cpp` slug for several Python bindings, or has no platform-specific
    page at all for two families) — not a hypothetical risk, a real, if not-yet-shipped, fabrication.

    Fixed by building the verification this project always needed rather than reverting the
    broadening: `src/readme_agent/registry/policy_facts.py::verify_repo_facts()` — GitHub's own
    license classifier plus a README-text fallback (matching the `aspose-cells-foss.yml` pilot's own
    established ground-truth-from-README precedent) for the license; a real HTTP GET, never a
    guess, for every `.org`/`.com` URL at family and platform depth. All 25 profiles were corrected
    against it (9 `.com` URLs fixed; every license independently reconfirmed MIT — none were
    actually false, but none had been genuinely checked either); `data/aspose_com_links.json` gained
    a real `products.aspose.org` surface (11 families/25 platforms, live-probed, explicitly labeled
    registry-scoped rather than claiming the `.com` surface's full 293-link coverage) plus corrected
    3 stale/added 2 real `.com` platform entries found along the way. `readme-agent scaffold-policy`
    (new CLI) and `scripts/data-refresh/policy_profile_coverage_report.py` are the durable form of
    this fix — `ONB-004`'s own long-designed-not-built scaffolding, finally built, using the same
    verification module so no future profile can repeat this mistake. A new hard regression control
    (`test_every_non_disabled_entry_has_ecosystem_and_policy_profile_configured`,
    `test_registry_loader.py`) makes the original triggering condition — a mode flip with no profile
    behind it — a loud CI failure permanently, not a silent per-cycle `ERROR:missing_policy_profile`.
    `aspose-words-foss/Aspose.Words-FOSS-for-.NET` — this whole investigation's own trigger repo —
    was scaffolded, fully verified with zero unverifiable fields, and wired to `mode: "dry_run"` as
    the live proof; the remaining backlog (5 entries: `cells/go`, `cells/rust`, `html/python`,
    `pdf/cpp`, `pdf/python`) is unchanged `disabled`, needing a human to run `scaffold-policy` and
    review the result — `ONB-004` is `PARTIAL`, not `IMPLEMENTED`, on that basis, stated plainly.

    **Clone-reliability redesign.** Tracing why the Words/.NET clone timed out found the fixed 300s
    ceiling was a symptom, not the cause: `clone_baseline()` unconditionally force-clones on every
    call, and every one of ~7-9 stateless capabilities dispatched within a single `supervise_repo()`
    run calls it independently for the same repository (decision #26(b): capabilities share no
    per-run repo view by design) — one run was paying for the identical clone roughly 9-17 times
    over the network, each an independent roll against `SCL-004`'s own already-measured 158s-1004s
    clone-time variance for the identical repo. This is what actually breaks consistency across
    reruns (more redundant clones raise the odds that at least one draws the long tail), and it
    hides a latent correctness gap too: nothing guaranteed all ~9 clones observed the same upstream
    commit if a push landed mid-run. Preserved unchanged: the push-blocked clone model, the
    `--depth 1` convention, decision #40's read/write gate split, the git-tree-API profiling path
    (`SCL-004`) as a *future*, not this-pass, generalization target (bigger, riskier, unproven for
    non-manifest reads — named explicitly, not silently skipped).

    Redesigned (`SCL-009`, new row): an in-process memo in `clone.py` collapses the ~7-9
    within-run re-clones to one real clone. The first version of this design invalidated the memo
    via a call added inside `supervise_repo()` right before its own top-level clone — reasoning
    that "a run is one `supervise_repo()` call, not one process." That reasoning was itself
    incomplete: a live full-suite run the same session found two more pre-existing
    `test_specialists.py` tests broken by the same class of staleness
    (`test_upstream_edit_between_runs_is_upstream_changed`,
    `test_a_success_after_failures_resets_the_counter`), each calling a specialist's own `run()`
    directly, twice, in one process — a *different* top-level entry point the invalidate-only-in-
    `supervise_repo()` design never covered, and there is no bounded list of such entry points to
    exhaustively invalidate at (a concurrent session, working from that same intermediate state,
    independently found and patched these two tests at the TEST layer instead — an autouse
    `_clean_clone_memo` fixture plus explicit `reset_clone_memo()` calls between each test's two
    `run()` invocations, `tests/unit/test_specialists.py`; harmless, and left in place as
    additional defense-in-depth, but superseded as the mechanism of correctness by the fix below).

    Corrected to the actual final design: `clone_baseline()` validates its own memo against a
    cheap `remote_head_sha()` probe (a `git ls-remote`, ~1-15s — this project's own decision
    #40/ORC-006 freshness-probe pattern, reused rather than reinvented) instead of trusting it for
    an entire process's lifetime. This makes every caller correct automatically — `supervise_repo()`,
    every specialist's `run()`, any future entry point — with zero invalidation bookkeeping
    anywhere; `invalidate_baseline_clone()` was removed as unnecessary. The honest cost: reuse
    isn't free (a network probe, not a memory read), but ~1-15s per reuse is a small price against
    the ~150-1000s a redundant full clone cost, and it is a self-verifying design rather than one
    that depends on every present and future caller remembering to invalidate correctly. `env.py::
    git_clone_timeout_seconds()` makes the timeout tunable (default raised 300s→600s,
    evidence-informed, not a guarantee against the measured tail); a bounded, transient-only retry
    (2 attempts, 5s/15s backoff, real errors like "not found" fail fast, never retried); and
    `supervise_repo()` catches its own clone's `GitSafetyError` and returns a `BLOCKED`
    `SuperviseResult` with a written evidence bundle, instead of an uncaught abort with none.

    Both fixes are live-tested, not merely unit-proven: the words/net onboarding above and the
    clone redesign were exercised together against the real trigger repo; the full unit suite
    (including the two previously-broken `test_specialists.py` tests, passing without needing
    their own test-layer patch to be the thing making them pass) was re-run clean after the
    correction. (2026-07-22, user directive: "make all repos ready for processing" plus an
    explicit request to treat the clone timeout as a production problem — separate symptoms from
    root causes, propose a durable design, call out tradeoffs and limits honestly rather than
    claim more confidence than the evidence supports.)

50. **Plan-file hardening executed against the Claude-Code plan's own Phase 17 taskcard register: GOV-022 mechanical wave-reconciliation, a run-scoped verification-token nonce, a graduated convergence shortcut, a deterministic termination backstop, a hardened pre-commit gate, and TC-01's remaining push — plus an independent duplicate finding of decision #49's own test-staleness bug.** Executed concurrently with, and only discovering afterward, decision #49's own extensive registry-onboarding/clone-reliability work above — reconciled against it directly, not overwritten. **TC-14 remainder** (`GOV-022`): `scripts/governance/validate_plan_structure.py::check_wave_reconciliation_gate()` fails the pre-commit hook/CI if a Build Checklist wave item flips `[ ]` → `[x]` in the same change with no matching `logs/*.md` Wave/Phase entry — diff-aware (compares the working copy against `git show HEAD:plans/master.md`) so Waves 0-8 are never retroactively flagged; proven by 9 new tests in the first-ever test file for this script (`tests/unit/test_validate_plan_structure.py`), which also adds smoke coverage for the 4 pre-existing checks that had none. **TC-30**: the pre-commit hook now also runs `ruff check`/`ruff format --check`/`mypy src` (all sub-second) — the full `pytest` suite is deliberately excluded (a ~9-minute hook would get bypassed with `--no-verify` as routine, defeating "disallow from the start"; it remains a required CI step instead). **TC-28** (`VER-001` hardening): `compute_verification_token()` gains a `nonce` argument, minted once per `_verify_node` call and threaded through `commit_readme_write`'s new `verification_nonce` argument — closes the one gap TC-15/decision #48 named honestly but left open (a token minted in one run being replayable into a later, separate run for content that hashes the same way); proven by `test_precheck_rejects_a_token_computed_with_a_different_nonce` plus 3 new direct unit tests on the function itself. **TC-19** (`SCL-006` → `PARTIAL`, Phase 13 §13.4 Pillar C.2): a domain reporting an `ERROR:`-prefixed status now gets one immediate re-classify retry before the `CONVERGED_NO_TRACKED_CHANGE` shortcut's `all(...)` check runs, isolating one transient flake instead of unconditionally falling through to the full planner loop; records a `specialist_retry` decision noting recovery. **TC-18** (`AGT-006` further progress, Pillar A.2): `NO_PROGRESS_TURN_LIMIT` (3) ends a run deterministically via `final_status()` once a turn's task is `SUPERSEDED` or `BLOCKED` for 3 consecutive turns, rather than burning every turn toward `max_turns`/`repair_exhausted` — proven for both the duplicate-call and the unknown-capability-hallucination shape (the latter correctly lands on `PARTIAL_WITH_CAPABILITY_GAP`, never `BLOCKED: repair_exhausted`). **TC-29**: reviewed `golden_set/` (harness.py/aggregation.py/scenarios.py, `OPS-011`) — real, tested (18 fixture-only tests, `FixturePlannerClient`, never live), but scoped to planner capability-selection scoring and durable-state metric aggregation, not the README-content-drift weekly-replay Pillar D/TC-22 originally envisioned; TC-22 stays `not_attempted` for its own original scope. **TC-01 remainder**: the 3 commits from decisions #46-48 (`f85b9b2`/`acc824e`/`b3954d5`) pushed to `origin/main` for real (verified `git status` shows zero ahead/behind) — a real, live `git-credential-manager.exe` hang on the first attempt (killed, retried with `GIT_TERMINAL_PROMPT=0` + `gh auth git-credential`) is a second corroborating data point for `OPS-009`. **Independently duplicated part of decision #49's own finding**: before reading #49, this session separately found and fixed the identical `test_specialists.py` staleness bug via the identical mechanism (an autouse `_clean_clone_memo` fixture plus explicit `reset_clone_memo()` calls between each affected test's two `run()` calls) — left in place per #49's own characterization ("harmless... additional defense-in-depth"), not removed, since #49's deeper probe-based redesign supersedes it as the actual mechanism of correctness without conflicting with it. **A separate, one-off flake investigated and NOT fixed as a code bug**: `test_gitsafety.py` + `test_supervisor_loop.py` run together showed 9 assertion failures once, then passed 79/79 clean on an immediate identical rerun — `tasklist`/`Get-CimInstance Win32_Process` at the time showed substantial unrelated concurrent load on this machine (live daemons from two other, unrelated repositories, plus another concurrent `readme_agent.cli supervise --durable-state` process against a real pilot) — logged as new evidence on the already-existing `OPS-010` row, not re-investigated further since it did not reproduce a second time. A pre-existing, unrelated mypy error found in `gitsafety/clone.py` (a `CompletedProcess | None` narrowing mypy can't prove from `range()`'s non-emptiness, on the pre-redesign version of that file) fixed with an `assert`. Fresh full-suite run after all of the above, this session's own final verification: `pytest -q` → **919 passed, 0 failed, 18 deselected** (421s); `ruff check .`, `ruff format --check .`, `mypy src`, and `scripts/governance/validate_plan_structure.py` all clean. Not done this pass, still open: TC-02 (token rotation, human-only), TC-08 (the PR-opener capability itself — now genuinely unblocked, all four prerequisites closed), TC-09/TC-13 (blocked on TC-08), TC-20 (deliberately deferred per its own taskcard), TC-21/TC-22's own live-gateway measurement (no `LLM_BASE_URL`/`LLM_API_KEY` in this environment). (2026-07-22.)

51. **TC-08 built: `open_presentation_pr`, the one real `remote_write` capability this project registers (`PRL-001/002/004/007/008`).** Pairs with `render_readme_candidate`/`commit_readme_write` exactly the way those two already pair with each other -- takes an already-rendered, already-independently-verified candidate directly, never re-renders, never re-verifies. New `github_api/write_client.py` (deliberately separate from `client.py`, which stays read-only by its own explicit, pre-existing convention -- a design refinement over this plan's own earlier draft, which had proposed adding write methods to `client.py` itself): `find_open_pr()`/`create_pull_request()`. New `paths.pr_work_dir()` + `gitsafety.clone.create_pr_clone()`/`push_branch()` (`PRL-007`): the one clone in this codebase deliberately never neutered, structurally separate from `paths.work_dir()`/`create_work_clone()` -- the token travels via a per-invocation `http.extraheader`, never written to the remote URL or any persisted config. Branch name is deterministic (`readme-agent/presentation-update-{facts_hash[:12]}`, `PRL-001`): `find_open_pr()` checked before ever cloning or pushing anything, and again via `reconciliation_check()` for the effect ledger's own `EFF-001` lifecycle; `precheck()` reuses `compute_verification_token()` unchanged (TC-15/TC-28's own hardening, inherited for free). Gated on `entry.mode == "full"` inside `execute()` itself, matching `commit_readme_write`'s own established pattern -- today that's exactly the 2 confirmed pilots already trusted for real local commits, no new registry concept invented. `EFF-005`'s lock-holder-identity revalidation (`PRL-008`) is inherited for free through the same `dispatch_gated_effect()` path every mutating capability already goes through. Proven by 17 new tests (`tests/unit/test_open_presentation_pr.py`): the GitHub API layer mocked, but `create_pr_clone()`/`push_branch()` exercised for real against a local bare repo standing in for the GitHub remote (proves the clone is genuinely never neutered and a real branch actually lands, not just that the functions were called), plus `execute()`'s own orchestration (mode gate, existing-PR short-circuit, argument threading) with those two layers monkeypatched. **Deliberately not wired into any specialist's automatic dispatch path this pass** -- building and proving the capability was TC-08's own scope; deciding when the autonomous loop should call it is a separate design decision, not silently made here. Reachable today only via a direct `caller_domain=readme_presentation` dispatch, exercised by the new `scripts/retrofits/prove_open_presentation_pr_live.py` (real render → real verify → real `dispatch_gated_effect()` against the real `GitStateBackend`, refuses to run at all without an explicit `--confirm-real-pr` flag on top of whatever confirmation gated running it in the first place). Full suite: `pytest -q` → **938 passed, 0 failed, 18 deselected** (287s); `ruff check .`, `ruff format --check .`, `mypy src`, `scripts/governance/validate_plan_structure.py` all clean. **Not yet live-proven**: the retrofit script above has not been run against a real pilot yet -- that is a separate, explicitly-confirmed action (`GOV-018`), not implied by this decision. **Credited, not authored by this pass**: a concurrent session further hardened `OPS-009` while this capability was being built -- `gitsafety/_git.py::GIT_SAFETY_ENV` gains `GCM_INTERACTIVE=never` alongside the existing `GIT_TERMINAL_PROMPT=0`, closing the specific gap this session's own `git push` hit directly (a *configured* credential helper, `git-credential-manager`, ignores `GIT_TERMINAL_PROMPT` entirely and hangs in its own interactive flow regardless) -- merged into every `run_git()` call, including this decision's own `push_branch()`, for free. (2026-07-22.)

## Architecture

### Pipeline order

```
allow-list check (data/products.json, decision #4)
  -> preflight (GitHub read + LLM /models, both fail-closed)
  -> git safety (clone baseline fresh, clone/reuse work clone, neuter push, install pre-push
     hook, verify — decisions #12, #14)
  -> inspect (git metadata, file inventory, ecosystem manifest parse)
  -> gap-detect (scan the *whole* README, not just our own marker span)
  -> facts + facts_hash (decision #11)
  -> decide: skip (zero gaps, or hash-matches-and-still-valid) vs regenerate (decision #16)
  -> LLM call *only* if relationship_explained is a gap (decision #8)
  -> render missing elements into the one owned `resources` span (decision #9, Phase 21b)
  -> validate (10 deterministic rules, always run — decision #16)
  -> evidence (redacted, atomic writes)
  -> commit locally if mode=full and status=GENERATED (never pushed)
```

Phases 21+ reuse the common orchestration stages — allow-list, inspect, compare, propose,
validate, evidence, and gated apply — but they do **not** pretend every surface has the same write
mechanism. Repository files use the push-blocked git path; API/settings fields use dry-run
proposals and an explicit remote-write gate; manual UI surfaces produce validated assets and
operator instructions; product-agent-owned surfaces produce handoff findings; GitHub-generated
surfaces produce audit evidence only. Audit-only findings never enter a renderer.

### Marker format

One pair, one owned span: `<!-- readme-agent:resources hash="sha256:<hex>" schema="2" -->` … `<!--
readme-agent:resources:end -->`. Phase 21b retired the `readme-agent:callout` pair from
`upsert_span()` — it can no longer be created. `readme/markers.py`'s `remove_span()` permanently
keeps recognizing the legacy `"callout"` name (not a transitional shim to delete later): the
orchestrator calls it unconditionally on every run so any work clone still holding a
pre-Phase-21 callout span gets it stripped on its next run, regardless of whether that run
otherwise skips or regenerates. `remove_span()` is the exact inverse of `upsert_span()`'s insertion
(including the blank-line separators it adds), which is what makes the `change_boundary` validator
rule a fixed trim-and-compare rather than a heuristic diff: strip the owned span (plus any legacy
callout) from the current README and confirm what's left is byte-identical to the baseline.

### Runtime layout

`paths.py` resolution: env var `README_AGENT_RUNS_DIR` if set, else `Path.cwd() / "runs"` —
purely `cwd`-relative so local dev and a GitHub Actions runner (checkout puts `cwd` at repo root)
behave identically.

```
runs/baseline/{org}__{repo}/     # pristine clone, read-only reference, re-cloned fresh every run
runs/work/{org}__{repo}/         # mutable clone, STABLE across runs (decision #12) -- never pushes
runs/evidence/{run_id}/          # manifest.json, facts.json, llm_request/response.json, block.md,
                                  #   diff.patch, validation_report.json, sha256sums.txt
```
`{org}__{repo}` (double underscore) keeps names filesystem-safe/identical on Windows and Linux.
`runs/` is git-ignored (matches aspose.org's own `.gitignore` convention: plain `/runs/`, not a
dotfile).

### Module responsibilities

| Module | Responsibility | Notes |
|---|---|---|
| `registry/loader.py`, `registry/models.py` | Load+validate `data/products.json` + policies; `is_permitted()` allow-list gate | pydantic `ProductEntry`, `PolicyProfile` |
| `preflight/*` | GitHub read-check + LLM `/models` check, fail-closed | run before any clone/generation |
| `inspection/*` | git metadata + generic multi-manifest file inventory (`FileInventory.manifest_paths: dict[str, Path]`, Wave 3) from a clone; no LLM | case-insensitive LICENSE/README matching; manifest detection is data-driven from `ecosystems.registry.known_manifest_globs()`, not hardcoded to one filename |
| `ecosystems/java.py` (Maven `pom.xml` or Gradle `build.gradle`), `ecosystems/python.py`, `ecosystems/dotnet.py`, `ecosystems/typescript.py`, `ecosystems/go.py`, `ecosystems/cpp.py`, `ecosystems/registry.py` | Parse each platform's manifest (identity fields; Java also extracts `runtime_min_version`); dispatch by platform string, keyed to match `ProductEntry.platform`'s vocabulary | Wave 3: six real adapters (was one, `"maven"` only), all adapted from aspose.org's proven `scripts/pipeline/extraction/package_manifest.py` (GOVERNANCE.md rule 8, decision #30) — proves `ECO-002`'s "new adapter = new registry entry, never a new call site" with real second-through-sixth entries |
| `ecosystems/resolver.py` | Live install-path resolution against the real package registry, dispatched by platform string (Phase 21d) | only `"java"` implemented (Maven Central search API; renamed from `"maven"` in Wave 3 to match the registry rename); opt-in via `--check-install`, never a default; same never-a-default pattern as `links/validator.py` |
| `profile/schema.py`, `profile/detector.py` | `RepositoryProfile`/`DetectedEcosystem` (Wave 3, `ECO-001`/`ECO-003`); `build_profile()` — one `file_inventory.scan()` call, one `DetectedEcosystem` per detected platform, unresolved manifest-shaped files recorded not guessed | built on the same generalized `inspection`/`ecosystems` detection above, not a second parallel scanner; exposed as the `profile_repository` capability |
| `readme/gap_detector.py` | Scans the **entire README** for each of the 4 required elements; produces `GapReport` (per-element bool + evidence excerpt) | the module the rest of the pipeline hinges on; calibrated against 14 real READMEs (see Reference Data) |
| `readme/markers.py` | The one owned README span (`resources`); find/insert/remove, exact-inverse round-trip | see Marker format above; `remove_span` permanently also recognizes the legacy `callout` name for migration cleanup |
| `readme/facts.py` | `RepositoryFacts`, `compute_facts_hash()` (decision #11); sole permitted input to `llm/prompts.py`'s `build_prompt()` | `sha256_text()` CRLF-normalizes before hashing; `generation_schema_version` at `"3"` since Phase 21b's owned-span contract change |
| `readme/renderer.py` | Purely additive; renders only missing elements into the one `resources` span; substitutes policy's canonical URLs, never LLM-supplied ones | |
| `readme/presentation_report.py` | Read-only `READMEPresentationReport` (Phase 21a): opening explanation, audience/ecosystem statement, install-path resolution (via `ecosystems/resolver.py` if opted in), runnable example, heading-level consistency | never gates a run by itself; surfaced through `inspect`/`report` |
| `llm/prompts.py` | `build_prompt(facts: RepositoryFacts, policy: PolicyProfile) -> list[dict]` — no other parameters, mechanically enforced by `tests/unit/test_prompt_hash_coupling.py` | invoked only when `relationship_explained` is a gap |
| `llm/live_client.py`, `llm/fixture_client.py`, `llm/schema.py`, `llm/client.py` | Strict-schema client (live + fixture behind one `LLMClient` Protocol); bounded retry | see LLM Contract |
| `validation/registry.py`, `validation/rules/*` | 10 deterministic checks, always run (decision #16) | see Validator Registry; Phase 21c added `product_first_opening` and `commercial_mention_discipline`, both ERROR severity |
| `license/auditor.py` | License facts from GitHub API + LICENSE file content classification; never crashes on null | decision #5 |
| `links/validator.py` | HTTPS/domain checks; optional live HEAD/GET reachability, opt-in only, WARNING severity | never a default hard gate |
| `gitsafety/clone.py`, `neuter.py`, `hooks.py`, `verify.py`, `_git.py` | Baseline/work clone (toplevel-mismatch guard, pinned determinism — decision #14), push-neuter, pre-push hook, independent verification | see CI & Safety |
| `evidence/writer.py`, `evidence/redaction.py` | Atomic writes (`.tmp` + `os.replace`), `sha256_file()` (CRLF-normalized), redaction (verbatim secret-pattern regex + exact live-secret-value masking) | `unified_diff()` uses `difflib`, deliberately not `git diff` |
| `orchestrator.py` | Wires everything into `generate_repo`, `run_repo`, `run_registry`, `inspect_repo`, `report`, `validate_repo` | the one place that knows the full pipeline order |
| `cli.py`, `commands.py` | argparse subparsers; thin command handlers over `orchestrator.py` | exit codes: `0` pass, `1` validation/policy failure, `2` usage/config error, `3` preflight/git-safety/allow-list failure |

### Repository presentation control matrix (scope added 2026-07-18 — decisions #18–#24)

| Surface | Control class | What the agent may do | Delivery |
|---|---|---|---|
| README content and structure | Repository-file managed | Audit the full README; make surgical, fact-backed presentation changes; retain the proven `resources` span where needed; never apply a generic full rewrite | Push-blocked work clone, diff, validation, evidence |
| README product illustration/hero | Repository-file managed | Generate or prepare a product-specific visual, validate dimensions/alt text/claims, embed through a relative path | Push-blocked work clone |
| Repository description (About) | API/settings managed | Draft from verified product facts; validate length, clarity, and unsupported claims | `PATCH /repos/{org}/{repo}`, dry-run first, explicit apply gate |
| Homepage/website | API/settings managed | Propose the canonical useful destination from policy | Same gated repository update endpoint |
| Topics | API/settings managed | Propose relevant product, format, language, and ecosystem topics; reject keyword stuffing | `PUT /repos/{org}/{repo}/topics`, dry-run first |
| Community files and templates | Repository-file managed | Audit/create/improve approved files; GitHub decides how it surfaces their tabs and links | Push-blocked work clone |
| Social-preview image | Manual UI managed | Prepare the approved social-sharing asset and upload instructions; do not claim API automation without a documented endpoint | Repository Settings UI |
| Releases and packages | Product-agent owned | Audit availability, naming, links, descriptions, and consistency; send actionable findings to the publishing owner | Report/handoff only |
| Contributors and languages | GitHub generated | Audit unexpected output and investigate underlying repository history/files; never set values | Evidence only |
| Stars, forks, watchers, activity, counts, GitHub tabs/layout | GitHub generated | Observe for context only; never treat as editable metadata or quality gates | Evidence only |

GitHub automatically surfaces recognized community files in supported places such as the
repository overview, community profile, contribution flow, and sidebar. The exact tabs, links,
layout, and placement are controlled by GitHub and may change. The agent controls only the files
and their quality.

The common control flow is:

`classify surface -> inspect authoritative source -> detect a real gap -> create proposal only if
authorized -> validate claims and change boundary -> write evidence -> apply through the surface's
allowed gate`.

No renderer or write path may exist for a GitHub-generated or product-agent-owned surface.

## Registry & Policy Config

### `data/products.json` — the allow-list

Base is the exact, verbatim 25 entries from Aspose's own registry (11 families, 6 platforms, 11
GitHub orgs `aspose-{family}-foss`) — every `family`/`platform`/`repo_name`/`repo_url`/
`clone_url`/`active`/`discovered_via`/`overrides` field copied as-is, so the file stays literally
re-syncable from upstream. As of Phase 18 this re-sync is automated (see `data/families.json`
subsection below) rather than a manual copy. Three additive fields layer this project's own
operational meaning on top without touching the upstream-shaped fields:

```json
{
  "family": "cells", "platform": "java", "repo_name": "Aspose.Cells-FOSS-for-Java",
  "repo_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
  "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.git",
  "active": true, "discovered_via": "github",
  "mode": "full", "ecosystem": "maven", "policy_profile": "aspose-cells-foss"
}
```
`mode` is `"full"` / `"dry_run"` / `"disabled"` (decision #4, #10). `ecosystem`/`policy_profile`
are `null` for disabled entries. Expanding *coverage* (what the agent may act on) always means a
human flipping `mode` + setting `ecosystem`/`policy_profile` on an existing entry, per
`docs/policy-authoring.md` — never something automation decides, even though automation may now
add the entry itself (see below).

### `data/families.json` + `scripts/update_products_registry.py` — automated discovery (Phase 18)

`data/families.json` lists all 26 Aspose FOSS families and their GitHub org
(`aspose-{family}-foss`) — a discovery seed list, not an allow-list; being listed grants no
permission. `scripts/update_products_registry.py` scans every org via the read-only GitHub REST
API, classifies repos by the `Aspose.{Family}-FOSS-for-{Platform}` naming convention, and merges
results into `data/products.json`: newly discovered `(family, platform)` pairs are always added
with `mode: "disabled"`; existing entries only have upstream-shaped fields refreshed, never
`mode`/`ecosystem`/`policy_profile`; nothing is ever deleted. `.github/workflows/
update-products-registry.yml` runs this weekly plus on `workflow_dispatch`, opening a PR (never
pushing to `main`) via `peter-evans/create-pull-request` if the registry changed. This supersedes
the originally planned local-checkout-copy approach (`sync_products_registry.py` against a live
`D:\onedrive\Documents\GitHub\aspose.org` clone) with a self-contained live-API scan that works
the same way in CI as it does locally, and layers automatic discovery on top of the allow-list
decision (#4) instead of just a manual copy.

### `config/policies/<profile>.yml`

One file per `policy_profile`, per *product* not per *org* (links are product-specific even
though profiles share `block` boilerplate — that duplication across today's 3 files is accepted
debt, not worth a config-inheritance system at this scale):

```yaml
schema_version: 2
policy_profile: aspose-3d-foss
required_elements:
  license_mentioned:
    detected_license: MIT              # cross-checked against license/auditor.py; never invented
  products_org_link:
    url: "https://products.aspose.org/3d/java/"
    family_url: "https://products.aspose.org/3d/"
    label: "Aspose.3D FOSS for Java"
  products_com_link:
    url: "https://products.aspose.com/3d/java/"
    family_url: "https://products.aspose.com/3d"
    label: "Aspose.3D for Java"
    utm: { utm_source: github, utm_medium: readme, utm_campaign: foss-readme-optimizer }
  relationship_explained:
    min_sentences: 2
    talking_points: [open_source_scope, commercial_upgrade_path]
secondary_links:      # best-effort, tracked for coverage, never a hard gate
  [docs.aspose.org, docs.aspose.com, reference.aspose.com, releases.aspose.com,
   blog.aspose.org, kb.aspose.org, forum.aspose.com]
block:
  word_limit: { min: 20, max: 120 }     # applies only to LLM-authored relationship prose
  prohibited_terms: ["guarantee", "100%", "best in the world", "free forever", "no bugs"]
  link_whitelist_domains:
    [products.aspose.com, docs.aspose.com, reference.aspose.com, releases.aspose.com,
     products.aspose.org, docs.aspose.org, kb.aspose.org, blog.aspose.org, forum.aspose.com]
```

**Planned extension (`schema_version: 3`, Phases 20–24)**: policies gain explicit,
per-surface contracts rather than a single "repository profile" object:

- `product_facts`: provenance references, audience, capabilities, formats, package/install facts,
  verified example, documentation, release facts, and limitations (decision #22);
- `readme_presentation`: required visitor questions, allowed section operations, visual
  requirements, and product-before-promotion checks;
- `repo_description`, `homepage`, and `topics`: API-managed proposal and validation rules;
- `community_files`: required files, accepted organization defaults, and quality checks;
- `readme_visual` and `social_preview`: separate asset contracts and delivery modes;
- `audit_only`: releases/packages ownership plus GitHub-generated observations, with no renderer.

Every surface declares `control_class`, `owner`, `proposal_mode`, `apply_gate`, and validators.
The Phase 20 control matrix is the authority for these values.

## Validator Registry

All 10 rules always run (decision #16). All are hard `ERROR`-severity gates except `prominence`
(`WARNING`, decision #17):

| Rule | Checks |
|---|---|
| `word_count` | LLM-authored relationship prose only, within policy's `word_limit` |
| `prohibited_terms` | Flat phrase list, word-boundary, case-insensitive, against content rendered *this run* only |
| `link_whitelist` | Every link in content rendered this run resolves to a whitelisted domain |
| `change_boundary` | Strip all owned spans from current README → must equal baseline exactly |
| `talking_points` | Cross-checks LLM's self-reported `talking_points_covered` against a deterministic keyword heuristic on the actual prose — self-report never trusted alone |
| `referential_integrity` | LLM's claimed license/URLs must match ground truth and the actual rendered output (decision #6) |
| `idempotency` | Re-derived `facts_hash` matches the hash embedded in the existing span, when one exists |
| `prominence` | WARNING only — required element present but outside the prominent zone (decision #17) |
| `product_first_opening` (Phase 21c) | ERROR — fails if any commercial link precedes the README's product-description sentence; checks the *whole* current README text, not just content rendered this run |
| `commercial_mention_discipline` (Phase 21c) | ERROR — fails on ≥2 list-item-formatted commercial links, promotional/CTA/pricing language near a mention, or a mention outside the two evidenced acceptable positions (decision #9); also checks the *whole* current README text |

## LLM Contract

Adapted (not imported) from aspose.org's `professionalize_client.py` / `llm_registry.yaml` —
exact request/response shape and defaults, independent implementation and package boundary (see
Reference Data for why no literal cross-repo import).

- Base URL: `LLM_BASE_URL` > `GPT_OSS_ENDPOINT`. Key: `LLM_API_KEY` > `PROFESSIONALIZE_API_KEY` >
  `GPT_OSS_API_KEY`.
- `POST {base}/chat/completions`, `Authorization: Bearer <key>`, payload
  `{"messages": [...], "model": "gpt-oss", "temperature": 0.0, "max_tokens": 8000}`, response at
  `choices[0].message.content`.
- Bounded retry (max 2, only on connection errors/timeouts/429/502/503/504 — never on other 4xx
  or local schema-validation failures, since retrying a malformed response risks silently
  accepting a second, differently-wrong one). `LLM_MODEL` always re-validated against the live
  `/models` list by preflight before use.
- Strict response schema (`LLMBlockResponse`) — scope narrowed to exactly what decision #8
  requires:
  ```json
  {
    "relationship_paragraph": "prose only, no marker comments, no raw URLs the model invents",
    "talking_points_covered": ["open_source_scope", "commercial_upgrade_path"],
    "claims": { "license_name": "MIT", "commercial_link_url": "https://products.aspose.com/3d/java/" }
  }
  ```
- `[unverified]` at time of writing, needs empirical re-confirmation if the gateway changes: the
  live response echoes back the requested `model` string but has no separate model-version
  identifier; `id` (per-request) and `created` (timestamp) are the best available drift signals
  for Phase 18's monitoring work.

## CI & Safety

Two independent, named safety properties (`docs/safety-model.md` has the full detail):

1. **Push-blocking** — `git remote set-url --push origin DISABLED` (`gitsafety/neuter.py`) +
   an unconditional-exit-1 pre-push hook (`gitsafety/hooks.py`), verified by re-deriving proof
   from `git remote -v` and the hook file's actual contents (`gitsafety/verify.py`), never by
   attempting a real push. Proven against a real local `git push` attempt in
   `tests/unit/test_gitsafety.py::TestHookActuallyBlocksARealPush`.
2. **The allow-list** — decision #4.

**`ci.yml`** — path-filtered `push`/`pull_request` on `main`, `permissions: contents: read`.
Must pass with zero real secrets (works on fork PRs): default `pytest -q -m "not live"`
(fixture-only); `@pytest.mark.live` tests excluded by default. Python 3.11–3.13 matrix.
`ruff check` + `ruff format --check` + `mypy src` + `pytest`.

**`readme-agent-run.yml`** — `workflow_dispatch` only, `permissions: contents: read`, one
`run:` step (`readme-agent run --repo ... --mode dry_run`). The `mode` input's `choice` options
list **only** `dry_run` — no way to select `full` through the workflow at all. Uploads
`runs/evidence/` as a build artifact. Seed for future GitHub-App-based production automation, not
that automation itself.

**`golden-set-monitor.yml`** (Phase 18, not yet built) — `schedule` (weekly) +
`workflow_dispatch`, runs `cells/java` specifically (the pilot that actually calls the live LLM —
`3d/java` never does, by design, so it can't surface model drift) in `dry_run`, **hard-coded at
the workflow level** regardless of `data/products.json`, so a scheduled trigger structurally
cannot escalate to `full`. Appends one line to git-tracked `history/run-history.jsonl`.
Observability, not prevention — only has value if someone periodically looks at it.

**`.github/dependabot.yml`** (Phase 18, not yet built) — standard GitHub-native lockfile-refresh
PRs, not hand-rolled automation.

### Secrets & public-repo hygiene

`.env.example` documents `GH_TOKEN`/`GITHUB_PAT`, `LLM_BASE_URL`/`LLM_API_KEY` with
`PROFESSIONALIZE_API_KEY`/`GPT_OSS_*` fallbacks, `LLM_MODEL`. `evidence/redaction.py` masks exact
matches of live secret values before anything is written under `runs/evidence/`. Two-layer
secret-scan test (`tests/security/test_no_secrets_in_evidence.py`): deterministic (synthetic
fake-secret value, always runs in CI) + opportunistic (if real secret env vars are set, assert
their literal values never appear anywhere under `runs/evidence/**` after a fixture-mode
`generate` run — meaningfully exercised on this dev machine, not a no-op here).

## Reference Data

### Why no literal cross-repo import from aspose.org

`AGENTS.md` + `scripts/pipeline/PIPELINE.md` require new scripts *inside* `scripts/pipeline/` to
use a repo-relative `sys.path` bootstrap header tied to that repo's fixed directory depth, and to
register in `scripts/pipeline/config/registry.yaml` + `metrics_callsite_registry.yaml`,
CI-enforced there. That tooling has no reach outside its own repo checkout, but importing the
modules directly would still couple this project to that non-portable sys.path scheme and an LLM
client whose retry/error semantics are designed for their router layer, not ours. Adapting the
proven contract while keeping independent package boundaries is the correct middle ground.

### Patterns adapted from aspose.org

| Source (aspose.org) | Adapted into | What was kept |
|---|---|---|
| `data/products.json` | `data/products.json` | Verbatim base schema + all 25 real entries |
| `scripts/pipeline/config/llm_registry.yaml` + `commands/ops/professionalize_client.py` | `llm/live_client.py` | Exact request/response shape and defaults — see LLM Contract |
| `commands/ops/session_ledger.py` | `evidence/writer.py`'s `generate_run_id()` | `{UTC timestamp}-{secrets.token_hex(2)}` format |
| `commands/ops/cleanroom_manifest.py` | `evidence/writer.py`, `readme/facts.py` | `sha256_text`/`sha256_file` (CRLF-normalized), atomic `.tmp` + `os.replace` write |
| `commands/ops/metrics_schema.py` | `evidence/redaction.py` | Verbatim secret-pattern regex (`sk-`/`ghp_`/`ghu_`/`AIzaSy`/`Bearer <token>`/`?api_key=` etc.) |
| `scripts/pipeline/core/clone_cache.py` | `gitsafety/clone.py` | Toplevel-mismatch guard before any destructive git op |
| `scripts/pipeline/extraction/package_manifest.py`'s `_parse_java_manifest` | `ecosystems/java.py` (renamed from `maven.py`, Wave 3) | Regex-based pom.xml parsing, including its known parent-block caveat (documented, not silently inherited); Wave 3 additionally ported the source's `build.gradle` fallback and compiler-version extraction, absent from the original adaptation |
| `scripts/pipeline/extraction/package_manifest.py`'s `_parse_python_manifest`/`_parse_dotnet_manifest`/`_parse_js_manifest`/`_parse_go_manifest`/`_parse_cpp_manifest` | `ecosystems/python.py`/`dotnet.py`/`typescript.py`/`go.py`/`cpp.py` (Wave 3) | Regex/stdlib (`tomllib`/`json`) field-extraction approach per platform, including each function's documented caveats (`.csproj` first-of-20-shallowest-path, `cpp.py` first-`add_library`-only, etc.); Python's `canonical_package` namespace-package heuristic kept as an intentionally Aspose-specific convenience, not generalized |
| `.actrc`, `.env.act.example` | repo root | Copied verbatim |
| `.github/workflows/launch-dashboard.yml` | `readme-agent-run.yml` | Thin-orchestration shape (path-filtered/`workflow_dispatch`, minimal `permissions:`, one `run:` step) |
| `.gitignore` convention | `.gitignore` | Plain `/runs/`, not a dotfile |
| `commands/ops/fetch_aspose_com_targets.py` + `data/aspose_com_targets.json` (20 MB, 80k URLs) | `scripts/fetch_aspose_com_links.py` + `data/aspose_com_links.json` (34 KB) | Sitemap fetch (recursive, EN-only), URL normalize/classify, HEAD→GET verify, and the `-1`-unverified governance guard; trimmed to family + platform depth only for the 4 surfaces, plus blog category roots the source stores nowhere (see below) |
| `scripts/pipeline/lib/forbidden_claims_check.py` | **not reused** | Solves a different problem (capability claims against a ground-truth API-surface knowledge base this project doesn't have); `prohibited_terms` only needs a flat phrase list |

**Confirmed absent in aspose.org** (this project's push-blocking is genuinely novel, not
adapted): no neutered-remote or pre-push-hook pattern exists anywhere in that repo.

### aspose.com link database — `data/aspose_com_links.json`

Known-valid aspose.com URLs at exactly the two depths this project links to: family
(`products.aspose.com/words/`) and platform (`products.aspose.com/words/python-net/`), for the
four content surfaces (products, docs, reference, kb), plus blog.aspose.com category roots.
Every stored entry carries the live-verified `http_status`; consumers must treat only 200 as
linkable (`-1` = unverified, per the governance guard inherited from the source script).

Populated by `scripts/fetch_aspose_com_links.py` (on demand — the source repo has no scheduler
either; refresh is operator-run when aspose.com content changes):

- `--from-source <aspose.org>/data/aspose_com_targets.json` — offline trim of the source DB.
  Platform keys are re-derived from the *actual* URL path (the source canonicalizes
  `words/python-net` under a `words/python` key; we keep real path segments).
- default live mode — products/reference/kb/blog sitemaps + a synthesized family×platform
  candidate grid (docs.aspose.com has no usable sitemap; sitemaps also omit variant platform
  URLs the source repo patched in by hand), all HEAD→GET verified.

Facts this encoding depends on (verified live 2026-07-18): blog.aspose.com has no
family/platform landing pages — posts live at `/<category>/<slug>/` and the canonical category
page for every category is `/categories/aspose.<category>-product-family/` (the short
`/<category>/` form is a redirect alias that 404s for about half the categories); blog
categories are the 26 family slugs plus `total`.

### GitHub surface controls verified from official documentation (2026-07-18)

These facts constrain Phase 20 and prevent the plan from treating the visible repository page as
one editable profile:

- The repository update API supports `description` and `homepage`; topics use the separate
  "replace all repository topics" endpoint:
  <https://docs.github.com/en/rest/repos/repos> and
  <https://docs.github.com/en/rest/repos/repos#replace-all-repository-topics>.
- GitHub recognizes community files and surfaces them in supported locations, but GitHub owns the
  interface. For example, a recognized `CONTRIBUTING.md` can appear in the repository overview,
  sidebar, contribution page, and issue/PR flows:
  <https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors>.
- The community profile API reports recognized README, license, code of conduct, contributing,
  and template files; it does not grant control over GitHub's layout:
  <https://docs.github.com/en/rest/metrics/community>.
- GitHub's documented social-preview workflow is an upload under repository Settings. No
  automated endpoint is assumed unless Phase 20 finds a current, documented API:
  <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview>.
- Repository languages are calculated from repository files and exposed for reading. Contributors,
  stars, forks, and activity likewise reflect repository history and user activity rather than
  editable presentation fields:
  <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-repository-languages>.

### README gap audit (2026-07-17) — the empirical basis for the 4-element policy schema

14 real READMEs fetched live from GitHub (`gh api repos/{org}/{repo}/readme`), spanning 8 of 11
product families in the registry:

| Repo | License mentioned | `products.aspose.org` | `products.aspose.com` | Relationship explained | Notes |
|---|---|---|---|---|---|
| 3d/Java | Yes (strong) | Yes | Yes | Yes | All four elements present (bot-authored — see caveat below) |
| 3d/Python | Yes (strong) | Yes | Yes | Yes | All four elements present, same bot template |
| cells/Java | Yes (weak) | No | No | No | Blank slate |
| cells/TypeScript | Yes (weak) | No | No | No | Blank slate |
| pdf/Java | Yes (strong) | **No** | Yes (x2) | Yes | Half-fixed: missing org link + secondary domains |
| pdf/Go | Yes (strong) | **No** | Yes (buried at line 1890/1890) | Weak/borderline | Present but not prominent |
| barcode/Python | Yes | No | No | No | Zero promotional content |
| email/Python | **No** | No | No | No | Worst case — license itself unmentioned |
| slides/Java | Yes | No | No | No | Zero promotional content |
| words/Python | Yes | No | No | Partial (links to a GitHub sibling, not a commercial domain) | Doesn't route traffic anywhere useful |
| font/Python | Yes | No | No | No | Zero promotional content |
| note/Python | Yes | No | Yes (4 URLs) | Yes | Second-best — still missing `.org` |
| tex/Python | Yes | No | No | No | Zero promotional content |
| page/Python | Yes | No | No | No | Zero promotional content |

`products.aspose.org/{family}` was absent in 12 of 14 repos with zero exceptions outside the 3d
family — the single most universal gap, and the reason `products_org_link`/`products_com_link`
are checked independently (decision #7) rather than as "any commercial link." `pdf/Go`'s buried
link is the reason `prominence` exists (decision #17). Fixtures frozen at
`tests/fixtures/readmes/real_audit_2026-07-17/*.md`; `tests/unit/test_gap_detector.py` asserts
`gap_detector`'s output matches this table exactly, repo by repo.

**Caveat (recorded 2026-07-18)**: the 3d rows were authored by lexchou's bot, and the sponsor
has stated they do **not** represent the intended quality standard. This table remains the
ground truth for *element presence* (what `gap_detector` measures); the content *quality* bar
comes from the Phase 20 research corpus below, not from any current Aspose FOSS README.

### Portfolio survey (2026-07-18) — visitor-experience evidence across all 25 registry repos

Live GET-only survey of every `data/products.json` entry (not just the 3 enabled pilots),
scored on a deterministic visitor-experience heuristic (product clarity, trust signals, install
path, example, docs/support links — see `plans/investigations/full-registry-portfolio-survey.md`
for method and full data). Headline: **the shipped 4-element gap check and real visitor
experience are decoupled** — `aspose-3d-foss/…Java` (4-element compliant) scores 6/8;
`cells-python` and `pdf-java` (fail 3–4 of 4 elements) score 8/8, the portfolio ceiling. Other
findings: ecosystem-manifest parsers exist for 1 of 6 platforms (Java/Maven only) — 21 of 25
repos (84%), including all 10 Python repos, have no deterministic fact extraction today; 7 of 25
repos (28%), all of the `cells` family plus `3d-typescript` and `words-python`, have real
LICENSE content GitHub does not recognize; no repo in the portfolio shows a commercial link
before product explanation; `cells-java`'s README instructs a Maven Central dependency
(`org.aspose:aspose-cells-foss`) with zero results on Central (verified live). **Corrected and
broadened, 2026-07-18, once `ecosystems/resolver.py` (Phase 21d) existed to check it live for
all three enabled pilots, not just `cells-java`**: `aspose-3d-foss` and `aspose-pdf-foss` are
*also* zero-result on Maven Central (`org.aspose:aspose-3d-foss`, `org.aspose:aspose-pdf-foss`).
This is not an isolated `cells-java` defect — it is systemic across every enabled pilot, and by
extension plausibly the whole registry: none of these FOSS artifacts appear to be published to
Maven Central yet, regardless of README quality otherwise. `RDM-007`'s acceptance evidence
reflects this (`PARTIAL`, not `IMPLEMENTED` — the resolver correctly *detects* the problem, it
does not and cannot fix a registry publication gap).

### Reference-repository benchmark (2026-07-18) — leading-FOSS presentation patterns

Six real, live sources studied for `docs/presentation-standard.md` (`DOC-003`): n8n and the
NuGet Aspose.Cells page (sponsor-specified), plus iText, EPPlus, and SheetJS (open-core /
dual-license projects facing the identical commercial-upsell tension Aspose FOSS does) and
Apache PDFBox (pure-OSS, no-tension baseline). Full quotes and method:
`plans/investigations/reference-repository-benchmark.md`. Key findings: GitHub's community
quick-link row (README/CoC/Contributing/License/Security) is a native feature triggered by
recognized-file presence, confirmed live on `n8n-io/n8n` — no UI work is needed to get it, only
file presence (see `docs/github-surface-control.md`); commercial-mention placement varies across
real leading-FOSS projects (2 of 4 dual-licensed sources studied mention it near the top, not
only at the end) but tone/density/singularity do not (see decision #9); GitHub Packages is
empty (0) across every reference project studied despite all having real external distribution;
community-file completeness does not correlate with popularity (SheetJS, 36.3k stars, has
almost none recognized).

### Research and control corpus (Phase 20 — required before Phases 21+ development)

Per the sponsoring post's direction to do the homework, three research deliverables gate the
new work. The normative obligations they must satisfy are maintained separately in
[`plans/requirements.md`](requirements.md), which must be reviewed and updated alongside these
research outputs. **Status (2026-07-18): deliverables 1 and 2 are complete; deliverable 3 remains
open, blocked on analytics access this environment does not have.**

1. **Product-presentation standard** → `docs/presentation-standard.md` — **delivered**. Studied
   `n8n-io/n8n`, four additional leading FOSS/dual-license repositories (iText, EPPlus, SheetJS,
   Apache PDFBox — exceeding the required 2–3), and the NuGet Aspose.Cells page. Defines the ten
   required principles (product clarity, audience fit, trust signals, installation path, verified
   examples, navigation, visual usefulness, contribution readiness, maintenance signals, natural
   commercial context), first-screen/first-minute/first-install criteria, the
   illustration-vs-social-preview distinction, a ten-point Phase-21 review checklist, and three
   deliberately different reference patterns by product type.

2. **GitHub control and ownership matrix** → `docs/github-surface-control.md` — **delivered**.
   Every visible surface verified against current official GitHub documentation and classified
   into the five control classes, with permission, endpoint/file/UI location, dry-run/apply
   behavior, rollback method, and evidence recorded. Confirms live (on `n8n-io/n8n` and
   `apache/pdfbox`) that GitHub's community quick-link row is automatic, driven by recognized-file
   presence — no UI work needed. Confirms description/homepage/topics endpoints, social-preview
   UI-only status, and GitHub Packages as unused (0) across every reference project studied.

3. **Traffic-feasibility homework** → a numbered answer to whether ≥10 visitors/week from
   github.com to aspose.org is achievable, when, and how. **Not delivered** — requires weekly
   aspose.org source-report access and GitHub Traffic API views/uniques for the pilots, neither
   available from this environment. Remaining scope, unchanged:
   - Inputs: weekly aspose.org source baseline, GitHub traffic views/uniques for the pilots,
     placement-specific click-through assumptions, and repository-coverage math.
   - Separate useful product traffic from raw clicks; track whether visitors reach relevant
     product/docs pages and whether the changes harm README clarity.
   - Define the minimum pilot observation period and the evidence needed before scaling.
   - The answer may revise the target if the baseline proves it unrealistic; it must not alter the
     product-first rule to chase the number.

## Build Checklist

### Sprint waves (`AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001`)

Tracks the sponsor-directive sprint (decision #26) separately from the Phase list below, which
predates it and remains the shipped-engine track. See the Changelog entries dated 2026-07-18 for
full detail on each wave; this checklist gives at-a-glance status only.

- [x] Wave 0 — Doctrine correction, truthful green baseline restored, `AGT-*`/`CAP-*`/`RUN-*`/
      `ECO-*`/`ONB-*`/`MEM-*`/`ORC-*`/`VER-*`/`GAP-*`/`SCL-*` requirement groups seeded
      (`PLANNED`), project identity corrected (`README.md`, `pyproject.toml`,
      `docs/architecture.md`, `AGENTS.md`, `GOVERNANCE.md`). No runtime code — decision #26.
- [x] Wave 1 — Gateway tool-calling spike (L6–L8), runtime framework evaluation and choice
      (decision #27, extend the orchestrator, no new framework), one live
      observe→plan→execute→observe→replan loop iteration proven (`AGT-002` → `PARTIAL`). No
      production capability registry or supervisor yet — spike-only, lives in
      `plans/investigations/`.
- [x] Wave 2 — Capability foundation: `CapabilityManifest`/`CapabilityGap` schema
      (`src/readme_agent/capabilities/schema.py`), capability registry (`registry.py`,
      mirrors `ecosystems/registry.py`'s dispatch-table pattern), permission-aware dispatcher
      (`dispatcher.py`), three existing safe modules exposed as real capabilities
      (`inspect_repository.py`, `detect_readme_gaps.py`, `check_install_path.py` — all
      `read_only_local`/`read_only_network`, no mutating capability yet), capability-gap records
      on unknown-`capability_id` dispatch. Live-proven end to end
      (`tests/integration/test_capabilities_live.py`), 22 new offline unit tests. Repository-
      profile compatibility filtering (`CAP-002`'s second clause) stays open until Wave 3's
      `RepositoryProfile` exists to filter against. **Extended 2026-07-19** with the
      domain-invocation axis and the `EFF-001` registration gate — see decision #34, `CAP-006`.
- [x] Wave 3 — Heterogeneous repository profiling: `RepositoryProfile` schema (`profile/schema.py`),
      generic multi-manifest inventory (`inspection/file_inventory.py`'s `manifest_paths`,
      data-driven from `ecosystems.registry.known_manifest_globs()`), six real platform parsers
      (Java — Maven or Gradle, Python, .NET, TypeScript, Go, C++) adapted from aspose.org's
      proven `package_manifest.py` (decision #30), `profile_repository` capability, live-proven
      against the real `pdf/java` pilot through the real dispatcher. `data/products.json`'s three
      real Java entries migrated `ecosystem: "maven"` → `"java"` in the same change (byte-for-byte
      regression-proven against all three real pilots — see Changelog). Governance additions:
      GOVERNANCE.md rule 8 + decision #30 ("prefer proven tools"), `GOV-015`, a `BACKLOG` row for
      the previously-unlogged prominence bug (`VAL-018`, decision #29/`GOV-014`). Hardened same
      day against all 25 real registry entries (not just the 3 pilots): found and fixed a real
      crash (Python's flat `packages = [...]` config shape) and a systemic detection gap (every
      `.NET` repo's manifest lives in a subdirectory, missed by a root-only check) — see the
      matching Changelog entry and
      `plans/investigations/full-registry-ecosystem-detection-survey.md`.
- [x] Wave 4 — Durable runner state: `state/schema.py` (`RunStateV1`,
      `CapabilityOutputCacheEntry`), backend-independent `state/backend.py` (`StateBackend`
      Protocol, `MEM-003`), the real backend `state/git_backend.py` — one git ref per `org_repo`
      on this project's own remote, not a shared branch (decision #32, reassessed after a first
      draft's granularity mismatch would have produced false-positive `STALE_INPUT` across
      unrelated repos), locks + reclaim-after-lease-expiry, all via git plumbing with no
      per-write working-tree checkout. Wired into `orchestrator.generate_repo()` additively
      alongside the existing local-work-clone check (decision #12 unchanged), opt-in via CLI
      `--durable-state` (mirrors `--check-install`'s never-a-default convention);
      `readme-agent-run.yml` updated with job-level `contents: write` and passes the flag.
      `CapabilityOutputCacheEntry.fingerprint` deliberately doubles as `EFF-001`'s idempotency
      key for Wave 5 to reuse. New tests: `test_state_schema.py`, `test_state_backend.py` (fake
      backend proves the CAS/lock contract), `test_orchestrator.py`'s simulated-fresh-runner
      case (two separate working directories sharing one durable backend — the concrete
      regression test for `RUN-001`), `tests/integration/test_state_git_backend_live.py`
      (`@pytest.mark.live`, run with explicit confirmation, 4/4 passed after fixing a real bug
      found live — `gitsafety/_git.py`'s text-mode stdin write silently corrupted `mktree`'s
      tree-entry paths on Windows; see Changelog). **`RUN-003` closed same day**: a real `act`
      reproduction of `readme-agent-run.yml` (`Job succeeded` on the third attempt) found and
      fixed two more real bugs — durable-state read/write-back are now best-effort (never abort
      the run, mirrors `check_install`'s convention) and `upload-artifact`'s name is sanitized
      (`inputs.repo_key`'s `/` is invalid there) — `RUN-001` → `IMPLEMENTED`; see Changelog.
      **Extended 2026-07-19** with `DomainStateV1`/`RunStateV1.domain_states` and
      `state/domain_state.py::save_domain()` — see decision #35, `MEM-004`.
- [x] Wave 5 — Autonomous planning: production supervisor, task graph, dynamic capability
      selection, replanning, failure classification, repair-task creation, convergence status
      (decision #36). `src/readme_agent/supervisor/` (`task.py`/`convergence.py`/`repair.py`/
      `loop.py`), `llm/planner_client.py`, `capabilities/effect_ledger.py` (`EFF-002`/`003`). New
      CLI `supervise` verb, additive alongside `run`/`run-registry`. `AGT-001`/`003`/`004`,
      `ORC-001`, `GAP-001`/`002`, `EFF-003` → `IMPLEMENTED` on unit proof alone (deterministic
      code-path properties, `GOVERNANCE.md` rule 10's "matched to what it claims"). 52 new tests
      (396 passed, up from 335). **Live-proven 2026-07-19**: `test_effect_ledger_live.py` (2/2) and
      `test_supervisor_live.py` (2/2) run for real with explicit confirmation, against the real
      `pdf/java` pilot and this project's own remote — `AGT-002`, `MEM-001`, `EFF-002`, `VER-003` →
      `IMPLEMENTED`; `EFF-001`, `ORC-002`/`003`, `VER-002` stay `PARTIAL` (each has a real remaining
      gap the live run didn't close: `EFF-001`/no real mutating capability yet blocked on Wave 7;
      `ORC-002`/`VER-002`/live pilot never actually failed, so the repair path stayed unit-proven
      only; `ORC-003`/no real specialist roles exist yet, also Wave 7). Rediscovered the documented
      `OPS-009` local push-credential hang mid-run; fixed by applying the known one-time fix, and
      added the same `OPS-009` docstring pointer to `test_supervisor_live.py` that
      `test_state_git_backend_live.py` already carried. See decision #36 and `requirements.md`'s
      Changelog for the resolved planning-time conflict, the corrected effect-ledger storage
      design, and the bugs found via direct testing.
- [x] Wave 6 — Upstream-change watch and reconciliation (rescoped, decision #37: "product agent" is
      an organizational label, not a real cooperating system -- no handoff schema is built). All
      code built, unit-proven, and live-proven this pass (decisions #38/#39) — see the Changelog's
      2026-07-19 "live proof" entry for the real `supervise`/`act` runs against `cells/java`.
  - [x] Prerequisite correctness fix (decision #38): `orchestrator.py`'s durable-skip fast path no
        longer blind to real upstream content changes (`compute_tracked_content_hash` +
        `RunStateV1.upstream_content_fingerprint_at_accept`); `_record_accepted_state()` no longer
        silently drops `domain_states`/`supervisor_state` on every write. Unit-proven (408 tests, up
        from 396); the specific durable-skip fingerprint-mismatch branch stays unit-only (safely
        unreproducible live without a real upstream edit to a product repo) — the multi-producer
        coexistence half of the fix is live-proven (see below).
  - [x] `get_product_facts` capability exposing the existing product inventory
        (`data/products.json` + `config/policies/*.yml` + live repository profiling, mandatory
        both, per user direction) as a read-only fact source. Live-proven: the real gateway planner
        selected and dispatched it against `cells/java`.
  - [x] Reconciliation classifier + `classify_upstream_change` capability, the first capability
        scoped to a real domain (`readme_reconciliation`, decision #34/`CAP-006`). Live-proven: the
        specialist dispatched it for real, correctly scoped, recording `FIRST_OBSERVATION`.
  - [x] Specialist registry (`src/readme_agent/specialists/`, mirrors `capabilities/registry.py`'s
        pattern) + `langgraph` adopted for real for the first time, executing decision #27's Wave
        6-8 commitment. Each specialist's own accepted result writes into `RunStateV1.domain_states`
        via `save_domain()` (decision #35, `MEM-004`). Live-proven against a real remote.
  - [x] `supervisor/loop.py::supervise_repo()` gains a registry-driven second convergence tier
        (`CONVERGED_NO_TRACKED_CHANGE`) ahead of the existing coarse commit-SHA check. The coarse
        tier itself was live-exercised (immediate rerun, zero planning calls); the fine-grained
        tier's own `NO_CHANGE`-only short-circuit stays unit-proven (needs a real "commit changed,
        tracked content didn't" scenario this session's runs never happened to hit).
  - [x] `readme-agent-supervise.yml` (`workflow_dispatch` only, schedule still deferred pending
        further live history) — the first CI entry point for `supervise`. Its own `act` reproduction
        ran for real (`Job succeeded`) against `cells/java`.
  - [x] Full-registry hardening pass (2026-07-20, user directive), mirroring Wave 3's own survey
        discipline: `compute_tracked_content_hash`/`readme.reconciliation.classify`/community-file
        detection run read-only against all 25 real registry entries regardless of mode (decision
        24/`PIL-011`) — 25/25 clean, zero bugs found, zero code changes needed. All 3 enabled
        pilots now have a real, live `supervise --durable-state` run recorded (`3d/java` newly
        added this pass — the real planner dispatched 5 of 6 registered capabilities in one run).
        See `plans/investigations/full-registry-wave6-survey.md`.
- [x] Wave 7 — Repository-presentation specialists (README, metadata, community files, visuals,
      package/release auditor, GitHub-generated-surface auditor, cross-surface validator),
      LangGraph-scoped (decision #27) with dispatcher-enforced domain isolation (decision #34,
      `CAP-006`). No specialist may declare `side_effect_class >= local_write` until `EFF-001`
      reaches `IMPLEMENTED` (decision #26 addendum). Decomposed by risk, mirroring Phase 21's
      a-e decomposition — see decision #41 for the full design and the production-reliability/
      agility findings that shaped it.
  - [x] 7a — Eight foundational fixes, before any of the seven specialist domains exist: the
        `EFF-001` render/commit decomposition (`orchestrator.py::ReadmeCandidate`/
        `prepare_readme_candidate()`/`commit_readme_candidate()`, `capabilities/
        render_readme_candidate.py`, a registered `reconciliation_check` hook in
        `capabilities/registry.py`/`effect_ledger.py`) plus seven agility/reliability fixes found
        by direct code verification, not assumed: per-specialist failure isolation in
        `supervisor/loop.py`'s specialist tier, domain-aware filtering on
        `registry.all_tool_schemas(caller_domain=)`, a shared change-detection primitive
        (`state/change_detection.py::classify_surface()`, `readme/reconciliation.py` refactored
        onto it with zero behavior change), `DomainStateV1.details` (generic structured-payload
        field), a domain/specialist registration completeness gate
        (`specialists/registry.py::_build()`), a `--domain` flag on the `supervise` CLI verb, and
        an always-written `specialist_results.json` evidence artifact. 43 new tests (480 passed,
        up from 437, 15 deselected unchanged); `ruff check .`, `ruff format --check .`, `mypy src`
        all clean; the full existing test_orchestrator.py suite passed unmodified, proving the
        `generate_repo()` refactor changed nothing observable.
  - [x] 7b — GitHub-generated-surface auditor (domain 2) + shared GitHub API client module
        (`github_api/client.py`, extending `scripts/update_products_registry.py`'s live-proven
        pagination/rate-limit pattern). Class E, audit-only forever (`OWN-005`/`OWN-012`).
        `len(KNOWN_DOMAINS) > 1` is real for the first time. 7 new tests (487 passed, up from 480);
        two new cross-domain-denial tests proving `CAP-006`'s denial path against *both* real
        domains (not just one repeated capability); a `TestMultiDomainCoexistence` class proving
        both domains' `DomainStateV1` entries coexist without collision in one run, against a fake
        backend. **Live-proven against the real `pdf/java` pilot** (no `--durable-state`): the real
        gateway planner correctly dispatched `render_readme_candidate` (7a's new capability)
        alongside the existing tool menu and converged; the specialist tier (both domains) ran
        against the real repo with no failure-isolation warning surfacing, evidence the new
        capability's real GitHub API calls succeeded. **Still open, not yet proven live**: the
        durable git-backed multi-domain persistence proof itself (`--durable-state`, requiring the
        `OPS-009` push-credential workaround) — deferred to a consolidated live-proof pass once
        more specialists exist, rather than repeating the credential dance per sub-wave. `CAP-006`/
        `MEM-004` stay `PARTIAL` until that pass.
  - [x] 7c — Package/release auditor (domain 3) + narrow one-way `HandoffFindingV1`
        (`github_api/client.py::list_releases()`, `capabilities/audit_package_release_surfaces.py`,
        `specialists/package_release_audit.py` — reuses the existing, unscoped `check_install_path`
        for package resolution rather than duplicating `ecosystems/resolver.py` logic). Class D,
        audit/handoff only (`OWN-004`/`OWN-013`) — `OWN-004`/`OWN-012` now `IMPLEMENTED`, `OWN-013`
        stays `PARTIAL` (no real receiving system for the handoff loop, per decision #37). New
        `BACKLOG` row `GOV-021` for the surface-model doc's stale bidirectional-handoff framing.
        11 new tests (498 passed, up from 487). **Live-proven against the real `pdf/java` pilot**:
        all three specialists (readme, GitHub-surface, package/release) ran together against real
        data with no failure-isolation warning.
  - [x] 7d — Metadata specialist (domain 4), dry-run proposal only
        (`capabilities/propose_metadata_changes.py`, `specialists/metadata_presentation.py` --
        dispatches the existing unscoped `get_product_facts` plus the new domain-scoped proposal
        capability; proposes description/homepage/topics only where a field is currently missing,
        never second-guesses an existing value; no GitHub API PATCH exists anywhere). `accepted_
        status` deliberately stays the generic change/no-change verdict even when a proposal is
        unaddressed, so the convergence shortcut still fires correctly on an otherwise-unchanged
        rerun -- the proposal itself always stays visible in `details`. 9 new tests (507 passed,
        up from 498). **Live-proven against the real `pdf/java` pilot**: all 5 real capabilities
        the planner needed ran correctly; the planner itself twice failed to emit a clean stop
        signal after gathering everything it needed (new `BACKLOG` row `AGT-006`, confirmed
        unrelated to Wave 7's own additions -- the general planner's tool set was unchanged from
        7b/7c's cleanly-converging runs). `AGT-005` gets its first real evidence from this same
        live-proof.
  - [x] 7e — Community-files specialist (domain 5), audit + prepared content only
        (`github_api/client.py::get_community_profile()`, `capabilities/audit_community_files.py`,
        `specialists/community_files_presentation.py` -- correlates local LICENSE/CONTRIBUTING/
        CODE_OF_CONDUCT/SECURITY/SUPPORT presence, via the already-proven `inspection.
        file_inventory.scan()`, against GitHub's Community Profile API recognition; prepares real,
        proven-source candidate content -- the unmodified Contributor Covenant v2.1 -- only for a
        missing `CODE_OF_CONDUCT.md`, deliberately never fabricating a template for the other
        three, since no equally canonical source exists for them). Class 1, a real eventual write
        path exists, but this wave stops at audit + prepare -- no write into any work clone, since
        7g owns this project's first real `local_write` capability, not a second one registered
        here. `SURF-007` -> `PARTIAL` (was `PLANNED`). 8 new tests (515 passed, up from 507).
        **Live-proven across 6 real registry repos spanning 5 families/platforms**, including
        `mode: "disabled"` entries (confirming decision #40's `require_listed()` reachability fix
        in practice): reproduced the exact, previously-documented `docs/github-surface-control.md`
        PF-3 finding live on `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`
        (`presence_recognition_gaps: ["LICENSE"]`) and found a second, independent instance on
        `aspose-words-foss/Aspose.Words-FOSS-for-Python`.
  - [x] 7f — Cross-surface validator (domain 6) + `depends_on` specialist-ordering fix
        (`specialists/cross_surface_validation.py` -- no capability of its own, reads sibling
        domains' already-recorded `DomainStateV1` entries directly via `backend.load()`; today's
        one real comparison is `readme_reconciliation`'s new `details["license_claim"]`
        (`classify_upstream_change.py`'s regex classifier over the README's own text) against
        `community_files_presentation`'s new `details["detected_license"]` (reuses `license.
        auditor.detect_license()`, GitHub's SPDX classification first, LICENSE-file-content
        fallback) -- both minimal, additive enrichments of two already-shipped specialists, not a
        new business-logic capability. `SpecialistManifest.depends_on` (new field) + a build-time
        ordering gate in `specialists/registry.py::_build()` turn "registered last sees siblings'
        this-run state" from an unstated assumption into an enforced invariant. Degrades honestly
        with no durable-state backend (a fixed fingerprint, empty `inconsistencies`, never a
        fabricated comparison) -- `OWN-011`'s "multi-specialist surface collision... currently
        undetected" gap gets a first, narrow, real mitigation instance (stays `PLANNED`, not
        `IMPLEMENTED`: this is one specific fact pair, not the general mechanism that row
        describes). 11 new tests (526 passed, up from 515); full-tree `ruff check .`,
        `ruff format --check .`, `mypy src` all clean. **Live-proven**: a real local git repo with
        a deliberately introduced README-vs-LICENSE mismatch produces a real `inconsistencies`
        finding through the unmocked comparison logic (only the Community Profile API network call
        is mocked); the full 6-domain specialist tier runs clean end-to-end against 3 real registry
        pilots (`pdf/java`, `cells/java`, `3d/java`) with the new domain's honest no-backend degrade
        confirmed live. The genuine backend-driven sibling-comparison proof against real registry
        data (needing `--durable-state`/the `OPS-009` credential workaround) stays deferred to the
        consolidated final live-proof pass, same precedent as 7b-7e.
  - [x] 7g — README presentation specialist (domain 7) — the one real mutating capability
        (`commit_readme_write`, registered together with the `readme_presentation` domain);
        closes `EFF-001` → `IMPLEMENTED` on live proof. Three-node graph (`render` -> `commit` ->
        `record`, `specialists/readme_presentation.py`) -- `render` dispatches the existing
        `render_readme_candidate`; `commit` dispatches the new `commit_readme_write` via
        `dispatch_gated_effect()`, only when `needs_write` and only with a real durable backend
        (no ledger without one -- refuses to mutate rather than mutate unsafely, an honest
        `details["note"]` degrade otherwise). `orchestrator.commit_generated_readme()` extracted
        unchanged from `run_repo()`'s own inline git-add/commit logic (zero behavior change,
        proven by `TestRunModeFullCommitsLocally` passing unmodified) so both the CLI path and the
        new capability call the identical real-commit logic. **Corrected two plan assumptions
        during build, not silently followed**: (1) the `mode == "full"` gate does NOT come free
        from `supervisor/loop.py::_dispatch_and_record()`'s own check, since `commit_readme_write`
        is domain-scoped and that check only runs on the general planner's dispatch path, which
        can never reach a domain-scoped capability -- the gate is checked inside
        `commit_generated_readme()`/the capability itself instead, protecting every real caller
        regardless of dispatch path; (2) `commit_readme_write` stays fully stateless (decision
        #26(b)) -- `record_accepted_readme_state()` (unifying `ORC-004`'s two ledgers) is called by
        the specialist's own `commit` node, not inside the capability, matching every other
        specialist's `record` node being the sole durable-state writer. 15 new tests (541 passed,
        up from 526); full-tree `ruff check .`, `ruff format --check .`, `mypy src` all clean.
        **Live-proven for real, with the user's explicit go-ahead for the `--durable-state`
        push** (the OPS-009 local git-credential workaround, applied and removed immediately
        after): a real local git commit landed in `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`'s
        local work clone (`f1a4117 readme-agent: close promotional gaps (11407c2e0372)`, real live
        LLM call), confirmed never pushed (`git remote -v` shows `origin` push URL `DISABLED`); a
        rerun converged cleanly to `NO_CHANGE`/no duplicate commit; and the real crash-recovery
        path was proven by flipping the real ledger's `commit_readme_write` entry back to
        `pending` (simulating a crash between the real commit and the ledger's own applied-write)
        and confirming `dispatch_gated_effect()` reconciled it to `applied` without re-executing
        or re-writing the README a second time.
  - [x] 7h — Visuals specialist (domain 8), prepare-only; embed-write into README.md deferred
        (`capabilities/prepare_visual_asset.py` -- the first capability to use `execution_type=
        "manual_delivery_preparation"`, declared since the Wave 2 sprint but unused until now;
        `specialists/visual_preparation.py`). Validates an existing image asset (dimensions/
        format/size via Pillow, a new dependency per `GOV-015`) if one exists, or prepares a real,
        freshly-generated candidate banner from the pilot's own product facts if none does --
        confirmed live via a real GitHub code search that zero image assets exist across the
        sampled registry pilots, so the generated-candidate path is the common case this wave, not
        a rare fallback. `alt_text` and `license_status` are always real (never placeholders):
        derived from real product facts, and honestly distinguishing "generated, no licensing
        concern" from "existing asset found, human review required" rather than guessing at
        provenance. `SURF-010`/`SURF-011` → `PARTIAL` (both were `PLANNED`). Never embeds into
        `README.md` -- the same real precedent the plan named going in: `readme/markers.py`'s
        retired `callout` span's confirmed link-duplication bug. 9 new tests (550 passed, up
        from 541); full-tree `ruff check .`, `ruff format --check .`, `mypy src` all clean.
        **Live-proven against 3 real registry pilots** (`pdf/java`, `cells/java`, `3d/java`): each
        correctly found no existing asset and prepared a real candidate banner from that pilot's
        actual family/platform facts, with real dimension/format/size validation -- no write
        attempted anywhere, matching this sub-wave's own explicit scope. **Closes Wave 7's Build
        Checklist entirely -- 7a through 7h all shipped, each individually live-proven per its own
        stated scope.** At the time this line was first checked off, `CAP-006`/`MEM-004` still
        stayed `PARTIAL` pending a real multi-domain write under a real `GitStateBackend` in one
        live run -- closed for real in the same session's consolidated final live-proof pass (see
        that Changelog entry and both rows' own updated text): both are now `IMPLEMENTED`.
- [x] Wave 8 — Verification and repair: independent verifier (LangGraph-scoped, decision #27;
      domain-isolated from the capabilities it verifies, decision #34 — `VER-001`'s guarantee
      depends on this), adversarial checks, requirement mapping, repair loops, rerun convergence,
      evidence completeness gates. Design in decision #42, including two independent-review passes
      that corrected the first-round design before any of it shipped. Two immediate corrections
      landed first, standalone (an `org_repo` planner-trust fix in `supervisor/loop.py`; a
      `--local` git identity on every work clone in `gitsafety/clone.py`) — see decision #42.
  - [x] 8a — Foundational: `state/domain_state.py::merge_details()`/`record_failure_or_reset()`/
        `save_domain_with_failure_tracking()`, `DomainStateV1.consecutive_failure_count`/
        `last_failure_reason`, `SupervisorStateV1.control_plane_fingerprint` +
        `supervisor/convergence.py::compute_control_plane_fingerprint()` (closes the coarse
        `is_fresh()` blindness to a policy/prompt/capability-version change with no new upstream
        commit), `supervisor/repair.py::classify_verification()`, the new `verification/` package
        (`schema.py`/`checks.py`/`completeness.py`), the `precheck()` mechanism (`capabilities/
        dispatcher.py`'s new `rejected_precondition_failed` outcome, `registry.py` resolution,
        `effect_ledger.py` calling it before any pending write — `EFF-004`), `MEM-005`'s
        `stale_sibling_data` fix in `cross_surface_validation.py`, and a `requirement_ids` drift
        test against `plans/investigations/tools/extract_requirements.py`'s own proven regex.
  - [x] 8b — The `independent_verification` domain (ninth), `verify_readme_candidate` capability
        (first real use of `execution_type="validator"` since `CAP-004`), `readme_presentation`'s
        graph extended to `render -> verify -> commit -> record`, `commit_readme_write`'s new
        required `verification_verdict` argument + `precheck()` — the literal, strongest reading
        of `VER-001` for the one real write this project has. Found and fixed the already-known
        defect (a `BLOCKED_VALIDATION_FAILED` candidate durably accepted unconditionally) as its
        own concrete regression target, proven with a real, unmocked invalid render.
  - [x] 8c — `independent_verification` extended with evidence completeness across every other
        domain, requirement mapping (`CapabilityManifest.requirement_ids`, populated for three
        capabilities with an unambiguous domain attribution), adversarial cross-domain checks (a
        second-order check on `cross_surface_validation`'s own `inconsistencies`), and
        failure-escalation visibility.
  - [x] 8d — Failure-escalation counting wired into `readme_presentation` (the one domain that
        writes; the other eight specialists are a named, deferred follow-up, not silently claimed
        done), the auditor's findings surfaced in the planner conversation, a distinct
        `escalation_alert` decision when a domain crosses the threshold, and a run-level
        evidence-completeness gate (`_assert_evidence_complete()`).
  - [x] 8e — Consolidated live-proof pass (deferred here per the same "one credential dance, not
        one per sub-wave" precedent Wave 7b-7e established): the 8b accept/reject gate against a
        real `mode: "full"` pilot, the 9-domain coexistence proof, and the explicit "full
        `data/products.json` pilot" ask — read-only/audit-scoped machinery exercised against all 25
        real registry entries regardless of mode (decision #24/`PIL-011`), the one real write
        exercised only against the 2 `mode: "full"` entries (the unchanged access constraint named
        in `AGENTS.md` — never described as proof of 25 real commits). `VER-001`/`VER-002` reach
        `IMPLEMENTED` only once this runs (`GOV-018`). **Closed for real, 2026-07-21** (see the two
        matching Changelog entries): the 8b accept/reject gate proven live via a direct before/after
        comparison against a real pilot (`aspose-cells-foss/...Java`), and all 25 registry entries
        run through `supervise --durable-state` in a single verified-clean pass (25/25
        `CONVERGED_NO_CHANGE`, the 3 non-`disabled` entries each recording all 9 real domains with
        zero collision). `VER-001`/`VER-002` → `IMPLEMENTED`. Getting there took three attempts (a
        push-URL misconfiguration on this project's own repo, then a `TaskStop`-didn't-kill-the-
        child-process race between two concurrent instances), both found and fixed rather than
        hidden; a real `disabled_mode` escalation-carve-out gap found live and fixed along the way
        (`state/domain_state.py`); a new `BACKLOG` row (`VER-005`) for a structural interaction
        between the coarse freshness shortcut and partial per-domain recording failure, found but
        not fixed this pass.
- [ ] Wave 9 — Heterogeneous portfolio proof (JVM, .NET, Python, JS/TS, Go, C/C++, multi-ecosystem,
      unknown/synthetic repository, full portfolio dry run, controlled rollout plan).

### Phases (shipped-engine track, predates the sprint reset)

- [x] Phase 0 — Scaffolding (`pyproject.toml`, `.gitignore`, `paths.py`, `errors.py`, CLI
      `--version`, `ci.yml` green on a trivial test)
- [x] Phase 1 — `data/products.json` + 3 policy files + `registry/loader.py`
- [x] Phase 2 — Preflight
- [x] Phase 3 — Git safety (clone/neuter/hook/verify, proven against a real `git push` attempt)
- [x] Phase 4 — Inspection + `ecosystems/maven.py`
- [x] Phase 5 — LLM client (fixture + live); empirically confirmed no separate model-version
      field beyond the requested `model` string
- [x] Phase 6 — `readme/gap_detector.py`, calibrated against the 14-repo audit corpus
- [x] Phase 7 — Markers/facts/renderer, `test_prompt_hash_coupling.py`
- [x] Phase 8 — `generate`/`run` orchestrator control flow, `--force-regenerate`
- [x] Phase 9 — Validation registry, all 8 rules, `STALE_NONCOMPLIANT` fixture
- [x] Phase 10 — License auditor + link validator
- [x] Phase 11 — Evidence writer + redaction + two-layer secret-scan test
- [x] Phase 12 — CLI completion, all 7 subcommands, exit codes
- [x] Phase 13 — `run` end-to-end on both `mode: full` pilots, proven against real repos
- [x] Phase 14 — `run-registry` including `pdf/java` `dry_run` partial-gap proof
- [x] Phase 15 — Docs (`architecture.md`, `safety-model.md`, `policy-authoring.md`) +
      `readme-agent-run.yml`
- [x] Requirements baseline (2026-07-18; governance artifact, not a new implementation
      phase) — created `plans/requirements.md` with permanent requirement IDs, implementation
      status, priority, acceptance evidence, decision/phase traceability, and document-sync rules.
- [ ] Phase 16:
  - [x] Install `act` (winget `nektos.act`, with explicit user sign-off — asked first per the
        system-package-change rule; used to prove the Phase 18 registry-update workflow below)
  - [ ] `act workflow_dispatch -W .github/workflows/readme-agent-run.yml --input
        repo_key=aspose-3d-foss/Aspose.3D-FOSS-for-Java` end-to-end
- [ ] Phase 17 — Adversarial fixture review: prompt-injection content in repo files,
      schema/policy-violating LLM fixtures, hand-corrupted markers, malformed/missing README,
      non-UTF8 content
- [ ] Phase 18 (Tier 2):
  - [x] `data/families.json` + `scripts/update_products_registry.py` (live GitHub-API discovery,
        not the local-checkout copy originally planned) + `.github/workflows/
        update-products-registry.yml` (weekly + `workflow_dispatch`, PR-only, never pushes to
        `main`) — unit-tested (merge/classify/schema-validation), live-`--dry-run` proven against
        real orgs, `act -n` structural dry-run passes, and a full containerized `act` run proved
        the scan step end-to-end against all 26 real orgs (see Verification Checklist for the
        PR-step caveat, which is a local-checkout artifact, not a workflow defect)
  - [ ] Dependency lockfile + `.github/dependabot.yml`
  - [ ] `golden-set-monitor.yml` + `evidence/run_history.py` + `history/run-history.jsonl`
- [ ] Phase 19 (Tier 3) — Insertion-point regression corpus for the ~11 registry repos not
      already captured in `tests/fixtures/readmes/real_audit_2026-07-17/` (mostly .NET entries)
- [ ] Phase 20 (research and requirements control — **required before Phases 21+**):
  - [x] `docs/presentation-standard.md` — n8n, four additional leading FOSS/dual-license
        repositories, and the NuGet Aspose.Cells page studied; principles, review criteria, and
        differentiated reference patterns delivered, not a template (see Reference Data)
  - [x] `docs/github-surface-control.md` — every surface verified against official GitHub
        documentation plus live confirmation across six reference repos and the full registry
        (see Reference Data)
  - [ ] Numbered traffic-feasibility study — blocked: no aspose.org referral-report or GitHub
        Traffic API access from this environment
  - [ ] Freeze the product-facts contract (`DOC-006`) — not started
  - [ ] Automated requirements traceability check (`GOV-009`) for unique IDs, required fields,
        valid references, and master-plan/requirements consistency — not started
- [ ] Phase 21 — Product-first README audit and rework. Decomposed by risk, per the approved
      design in the investigation history record's "Phase 21 design proposal" section. Not
      Phase 21's job (belongs to Phases 23/24/25 instead, to keep the five-control-class boundary
      clean): license-recognition-as-a-community-file fact, visual usefulness, and no-fact-lost
      drift protection.
  - [x] 21a — `READMEPresentationReport` (`readme/presentation_report.py`): read-only diagnostic
        covering opening explanation, audience/ecosystem statement, install-path resolution,
        runnable-example presence, heading-level consistency; wired into `inspect_repo`; never
        gates a run by itself
  - [x] 21b — Callout retirement: `renderer.py`/`markers.py` merged to the one `resources` span;
        `upsert_span` no longer accepts `"callout"`; orchestrator migrates any already-materialized
        callout span out of a work clone unconditionally on next run; `GENERATION_SCHEMA_VERSION`
        bumped to `"3"`
  - [x] 21c — Two new ERROR-severity validator rules implementing decision #9/`BIZ-001`/`RDM-002`/
        `VAL-006`: `product_first_opening`, `commercial_mention_discipline`; both check the whole
        current README text, not just newly-rendered content; both verified against real pilot
        evidence (`pdf/java`'s legitimate 2×`.com`-mention README) before shipping to avoid a
        false-positive
  - [x] 21d — `ecosystems/resolver.py`: live install-path resolution, Maven Central implemented
        first, opt-in only (never a default hard gate, matching `links/validator.py`'s pattern);
        wired into `inspect_repo` and exposed as the `inspect` verb's `--check-install` CLI flag
  - [ ] 21e — Section-aware change plan (product explanation, audience/problem, installation,
        capabilities, verified example, navigation, visuals, maintenance/contribution signals,
        natural link placement): deferred, design-only. Ships as a structured, evidenced
        *proposal* a human applies — `change_boundary`'s byte-identical-outside-spans contract
        needs its own scoped evolution first before any in-section auto-apply is safe
  - [x] Re-run all three pilot proofs (`cells/java`, `3d/java`, `pdf/java`) end to end against
        21a–21d — live, against the real GitHub repos, not synthetic fixtures. Results:
        `cells/java` → `GENERATED`, committed locally (evidence `20260718-165448-0a06`); all
        ERROR-severity rules pass. `3d/java` → `STALE_NONCOMPLIANT`, zero LLM calls, block
        untouched (evidence `20260718-165516-1729`) — the expected, accepted behavior change:
        its bot-authored resources section (3 list-item-formatted commercial links) now fails
        `commercial_mention_discipline`, exactly as decision #9 requires; needs a manual trim to
        the evidenced one-paragraph density before it can pass again. `pdf/java` → `GENERATED`,
        dry-run (evidence `20260718-165558-c33e`) — its real, pre-existing legacy `callout` span
        (uncommitted, from before this session's Phase 21 work) was migrated away live, proving
        the migration step against genuine on-disk pre-Phase-21 state, not just a synthetic test.
        This re-proof run surfaced and led to fixing two real, previously-undetected orchestrator
        bugs — see the Changelog entry below and `RDM-001`'s/`VAL-002`'s evidence.
- [ ] Phase 22 — API/settings-managed fields plus audit-only reports: description, homepage, and
      topics audit/dry-run proposals; explicit permission and apply gate before any remote write;
      releases/packages handoff report to product agents; GitHub-generated surfaces recorded as
      observations only. Implement policy `schema_version: 3`.
- [ ] Phase 23 — Community files and GitHub-recognized supporting content: detect presence and
      quality of LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, issue templates, and
      PR templates as policy requires. Prepare changes in push-blocked clones and verify GitHub
      recognition through the community-profile API where available; never claim control over
      GitHub's tabs or layout.
- [ ] Phase 24 — Visuals as two separate deliverables: product-specific README illustration/hero
      embedded as a repository asset, and a social-preview asset prepared for manual Settings UI
      upload. Validate factual accuracy, accessibility/alt text, dimensions, file size, licensing,
      repository fit, and idempotent asset naming. No decorative image is accepted unless it helps
      explain the product.
- [ ] Phase 25 — Product-agent integration and drift protection: define the machine-readable facts
      and change-handoff contract; run the presentation audit after product publishing; detect
      later overwrites, stale facts, broken links, removed visuals/files, and generic regressions;
      route technical discrepancies back to the owning product agent and presentation repairs
      through normal evidence and apply gates.
- [ ] Phase 26 — Pilot evaluation and controlled rollout: independently review the three pilots,
      compare before/after developer comprehension and repository quality, prove no unsupported
      GitHub writes exist, confirm updates survive a simulated product-agent refresh, collect the
      initial traffic baseline, obtain sponsor acceptance, and only then enable additional
      registry entries in small waves.
- [ ] Not evaluated yet: `readme-agent validate`'s "fully offline against a prior evidence dir"
      design point — current implementation re-derives from the work clone instead of reloading a
      historical evidence bundle (a known, documented simplification, not a bug)

## Verification Checklist

- [x] `pytest -q -m "not live"` green locally and in `ci.yml`
- [x] `readme-agent preflight` against real live env — all 3 enabled repos `HTTP 200`, selected
      LLM model live
- [x] Allow-list proof — unlisted and `disabled` repos both yield `BLOCKED_NOT_ALLOWLISTED`, no
      clone/network call
- [x] Push-block proof — `verify_push_blocked()` output inspected directly, plus a real `git
      push` attempt against a real local bare repo confirmed blocked
- [x] Idempotency proof — `cells/java` `mode: full` run twice: second run `COMPLIANT_NO_CHANGE`,
      zero LLM calls, zero new diff
- [x] Secret-leak test — both deterministic and opportunistic layers pass
- [x] Gap-detection accuracy proof — `gap_detector` output matches the 14-repo audit table exactly
- [x] False-positive-avoidance proof — `3d/java` `mode: full` produces zero gaps, zero LLM calls,
      zero changes, zero commit, on the real repo
- [x] Partial-gap precision proof — `pdf/java` detects exactly `products_org_link`, zero LLM
      calls, diff contains only the new `.org` link
- [x] Value-proof — `cells/java` `mode: full` renders both spans, exactly one LLM call, human
      review of the actual rendered prose against the real existing README
- [x] Compliance-vs-idempotency proof — tightening `word_limit` after generation yields
      `STALE_NONCOMPLIANT`, zero LLM calls, block untouched; `--force-regenerate` overrides
- [x] Facts↔prompt coupling proof — `test_prompt_hash_coupling.py` signature + per-field checks
- [x] Clone determinism proof — pinned `-c core.autocrlf=false -c core.eol=lf` verified in
      `gitsafety` tests
- [x] Version-tripwire proof — editing `prompts.py`/`renderer.py` without bumping
      `generation_schema_version` fails the tripwire test
- [ ] `act workflow_dispatch -W readme-agent-run.yml` end-to-end (blocked on Phase 16)
- [x] `act -n` structural dry-run of `update-products-registry.yml` passes (all steps validate,
      job succeeds)
- [x] `act workflow_dispatch -W update-products-registry.yml` full containerized run: checkout,
      `setup-python`, `pip install -e .`, and the scan step all succeeded — live-scanned all 26
      real orgs (one, `aspose-imaging-foss`, 404s: the org doesn't currently exist on GitHub;
      the per-org `try/except` logged a `WARN` and continued, proving the fail-soft design under
      a real fault, not just a fixture), matched 31 repos, wrote 31 entries (6 new) inside the
      container. The final `create-pull-request` step then failed — but only because the local
      dev checkout's `main` (commit `4adbaaf`) is ahead of/diverged from the actual GitHub
      remote's `main` (`fd36cc4`), so the action's `git reset --hard origin/main` +
      `git stash pop` hit real merge conflicts against files this session added. This is an
      artifact of testing against a real remote from an uncommitted local working copy, not a
      defect in the workflow — it would run cleanly in real CI, where checkout always starts from
      the actual current remote `main` with no local drift. Confirmed the host repo was
      completely unaffected throughout (`git status`/`git log`/`git diff data/products.json` all
      clean before and after — `act` copies the repo into the container via `docker cp`, it does
      not touch the host working tree)
- [x] `scripts/update_products_registry.py` round-trip proof — live `--dry-run` against
      `aspose-3d-foss`/`aspose-cells-foss`/`aspose-pdf-foss` correctly preserved the three
      non-`disabled` entries' `mode`/`ecosystem`/`policy_profile` unchanged while refreshing
      upstream fields and adding newly discovered repos (e.g. `Aspose.Cells-FOSS-for-Go`) as
      `disabled`; a second live run scanning all 26 real orgs reproduced this against the full
      registry; `tests/unit/test_update_products_registry.py` covers merge/classify/schema
      validation without live network
- [ ] `golden-set-monitor.yml` manual-trigger proof (blocked on Phase 18)
- [x] Requirements baseline exists at `plans/requirements.md`, links back to this plan, and
      covers ledger decisions #1–#25 and Phases 0–26 with stable IDs and acceptance evidence
- [ ] Automated requirements traceability check passes: unique IDs, valid statuses/priorities,
      required acceptance fields, valid decision/phase references, and no orphan master-plan
      obligation or orphan requirement
- [ ] Phase 20 deliverables delivered and accepted:
  - [x] `docs/presentation-standard.md` delivered, evidenced against `DOC-003`/`DOC-004`
  - [x] `docs/github-surface-control.md` delivered, evidenced against `DOC-005`
  - [ ] Product-facts contract frozen
  - [ ] Numbered traffic-feasibility study delivered
  - [ ] Sponsor review/acceptance of the two delivered documents recorded
- [ ] Control-boundary proof: each surface is classified; no renderer/write path exists for
      contributors, languages, stars, forks, activity, GitHub layout, releases, or packages
- [ ] GitHub recognition proof: community files are detected correctly, while tests and docs make
      clear that GitHub — not the agent — decides where and how they are surfaced
- [x] Post-rework pilot proofs re-pass with no `callout` span; each README explains the product
      before promotion; diffs preserve verified technical facts and are not template clones.
      Verified live against all three real registry repos (2026-07-18): zero `readme-agent:callout`
      markers remain in any of the three work clones; `product_first_opening` passes for all
      three. "Re-pass" means each produces the correct, evidenced outcome for its actual
      state, not that every rule passes for every repo — `3d/java`'s `STALE_NONCOMPLIANT` result
      (its bot-authored resources section fails `commercial_mention_discipline`) is the intended,
      correct signal per decision #9, not a defect. See Build Checklist for evidence run IDs.
- [ ] Product-fact provenance proof: every changed technical claim maps to repository evidence or
      a product-agent handoff; missing facts produce findings rather than invented copy
- [ ] API-managed dry run produces correct description/homepage/topics proposals with zero actual
      writes; the apply gate requires explicit authorized action
- [ ] Visual separation proof: README illustration is embedded and validated independently from
      the separately prepared social-preview asset and UI instructions
- [ ] Publishing-integration proof: a simulated product-agent README refresh triggers drift
      detection and an evidence-backed proposal without silent revert
- [ ] Independent pilot review accepts all three repository-specific outcomes and confirms they
      were tailored rather than copied from n8n, NuGet, or one another
- [ ] Weekly github.com→aspose.org referrals are tracked against the ≥10/week target after approved
      improvements land, together with README-quality and destination-relevance checks

## Changelog

Full history relocated to `logs/` (2026-07-21, index at `logs/README.md`). New entries are
appended there, not here — see GOVERNANCE.md rule 6 and rule 12.

