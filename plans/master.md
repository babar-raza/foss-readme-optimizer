# foss-readme-optimizer — Master Plan

Governed by `plans/GOVERNANCE.md`. This file is the current execution plan and decision ledger —
not a history of how it was written. Nothing in it is locked at this stage: every decision is a
current working position, revisable through the governance procedure (edit in place + one
Changelog line). See the Changelog (last section) for the record of how decisions evolved.

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
4. **`data/products.json` is the hard allow-list.** Only orgs/repos listed there, with a
   non-`"disabled"` `mode`, are ones the agent is ever permitted to operate on
   (`registry/loader.py`'s `is_permitted()`), checked before any network or git operation.
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
- [ ] Wave 7 — Repository-presentation specialists (README, metadata, community files, visuals,
      package/release auditor, GitHub-generated-surface auditor, cross-surface validator),
      LangGraph-scoped (decision #27) with dispatcher-enforced domain isolation (decision #34,
      `CAP-006`). No specialist may declare `side_effect_class >= local_write` until `EFF-001`
      reaches `IMPLEMENTED` (decision #26 addendum).
- [ ] Wave 8 — Verification and repair: independent verifier (LangGraph-scoped, decision #27;
      domain-isolated from the capabilities it verifies, decision #34 — `VER-001`'s guarantee
      depends on this), adversarial checks, requirement mapping, repair loops, rerun convergence,
      evidence completeness gates.
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

- **2026-07-17** — Initial plan drafted for a from-scratch POC, assuming no reusable code existed
  (the referenced aspose.org monorepo wasn't found on the machine's expected path).
- **2026-07-17** — Found aspose.org at a second OneDrive mount point the first search missed.
  Rewrote the plan to adapt real, verified patterns (LLM client, secret redaction, atomic
  writes, clone safety guard) instead of writing everything from scratch; confirmed why no
  literal cross-repo import is appropriate (see Reference Data).
  User correction: `data/products.json` is a hard allow-list, not just configuration — added as
  decision #4.
  Deep "Consistency & Determinism" self-review before any code was written: identified that the
  original single-block design couldn't represent partial compliance, that idempotency needed to
  be decoupled from policy-compliance checking, and that several determinism gaps (git config,
  prompt/facts coupling, schema versioning) needed mechanical enforcement, not just convention —
  became decisions #11, #14, #15, #16.
  User directive: the actual mission is closing four specific, named promotional gaps, not
  generating a generic block — ran a live 14-repo README audit to ground the policy schema in
  evidence instead of assumption; became decisions #7, #8, #9, #10, #17 and the Reference Data
  audit table.
- **2026-07-17** — Implemented Phases 0–15. Found and fixed two real bugs via testing, not
  inspection: `gap_detector`'s domain regex was accidentally hardcoded to `aspose.org`/
  `aspose.com` (violated decision #1) — fixed to a generic pattern, became decision #13.
  `facts_hash` originally included `gap_report`, which is circular since rendering changes
  gap_report — fixed by excluding it, became decision #11. `paths.work_dir()` had to become
  stable per `org/repo` (not per run-id) for idempotency across separate CLI invocations to be
  real — became decision #12. Proved the full pipeline end-to-end against the three real target
  repos (Phases 13–14). Wrote `docs/architecture.md`/`safety-model.md`/`policy-authoring.md` and
  `readme-agent-run.yml` (Phase 15). Committed locally as `4adbaaf`.
- **2026-07-17** — Copied this plan into the repo at `plans/master.md` (previously only in the
  local Claude plans directory).
- **2026-07-17** — Restructured this file under `plans/GOVERNANCE.md`'s thin process: collapsed
  the three sequential design passes (original draft → aspose.org-adapted rewrite →
  consistency/audit-driven redesign) into the single current-state spec above, moved the
  implementation-time bug fixes into the decision ledger, converted the phase list and
  verification list into checked/unchecked checklists reflecting actual status, and compressed
  the narrative history into this Changelog. No architectural content changed — this was a
  format-only restructuring per the new governance contract.
- **2026-07-18** — Re-scoped per the sponsoring post and its follow-up comments ("GitHub Readme Agent – 2026.07.17"): added the Mission section (business goal, ≥10
  visitors/week metric, product-first principle, division of labor with product agents);
  retired the callout-after-H1 placement as "shameless promotion" (decision #9 edited in place,
  #17 remediation retargeted); expanded scope from README gap-closing to a central
  repository-presentation agent (decisions #18–#21 added; managed-vs-audit-only surface split;
  drift protection); corrected the 3d reference framing — those READMEs were lexchou's bot's
  output, not the quality standard (decision #10 and the audit table edited); added the
  required-before-development research corpus (n8n + leading FOSS + nuget.org study, traffic
  feasibility homework) and Phases 20–25 to the Build Checklist. GOVERNANCE.md amended to place
  `Mission` first in the fixed section order.

- **2026-07-18 — control-boundary and ownership correction** — Updated the re-scoped plan after
  the follow-up review of the proposed response. Removed the claim that the agent can control the
  complete GitHub repository view. Replaced the managed/audit-only split with five explicit
  control classes; separated README illustration from social preview; made GitHub-rendered
  community tabs explicit; retained releases/packages under product-agent ownership; made
  contributors/languages/stars/forks/activity audit-only; added the product-facts handoff
  contract, section-aware product-first README review, publishing integration, and a gated pilot
  evaluation phase. All completed Phase 0–15 implementation, evidence, tests, and standing safety
  decisions from 2026-07-17 remain intact.

- **2026-07-18 — requirements baseline and document-control hardening** — Added
  `plans/requirements.md` as the complete normative register, linked bidirectionally with this
  master plan. Added permanent requirement IDs, status and priority, objective acceptance
  evidence, decision/phase coverage, and explicit rules requiring both documents to change
  together. Added decision #25, a completed requirements-baseline checklist item, and a
  Phase-20 CI traceability requirement. Yesterday's completed Phases 0–15 and today's re-scoped
  product-first/control-boundary decisions remain unchanged; the new document separates the
  requirements contract from the execution narrative so neither has to carry both roles.
- **2026-07-18** — Renamed "Locked Decisions" to "Decision Ledger" across GOVERNANCE.md,
  master.md, and requirements.md — nothing is locked at this stage; every decision is a current
  working position, revisable through the governance procedure, and the numbers are stable
  cross-reference identifiers only. No decision content changed.
- **2026-07-18** — Added `data/aspose_com_links.json` + `scripts/fetch_aspose_com_links.py`
  (adapted from aspose.org's backlink target map, trimmed to family/platform depth + blog
  category roots) — rendered `products.*.com` links must come from a verified link DB, not be
  guessed.
- **2026-07-18 — automated registry discovery (Phase 18 slice).** Added `data/families.json` (26
  Aspose FOSS families → `aspose-{family}-foss` GitHub orgs, cross-checked against aspose.org's
  own `data/families.json` and `update_product_registry.py`'s org list), `scripts/
  update_products_registry.py` (live read-only GitHub-API scan + safety-preserving merge — see
  decision #4 and the Registry & Policy Config section above), `.github/workflows/
  update-products-registry.yml` (weekly + `workflow_dispatch`, PR-only), and `data/README.md`
  (usage doc for agents). Supersedes the originally planned local-`aspose.org`-checkout sync
  approach with a self-contained live scan. Installed `act` (winget `nektos.act`, user sign-off
  obtained first) to test locally: `act -n` structural dry-run passed; a full containerized run
  proved the scan step end-to-end against all 26 real orgs (one, `aspose-imaging-foss`, doesn't
  currently exist on GitHub — confirmed independently via `gh api`/`gh search repos`; the per-org
  fail-soft handling logged a warning and continued, a real proof of that design, not just a
  fixture). The final PR-creation step failed only because the local dev checkout has diverged
  from its actual GitHub remote (expected when testing a "commit and open a PR" action against an
  uncommitted local working copy, not a workflow defect); the host repository was verified
  unaffected throughout. `plans/requirements.md` CORE-023/OPS-005 moved `PLANNED` →
  `IMPLEMENTED` (text corrected to match; see that document's Changelog); added CORE-032,
  OPS-007, OPS-008.
- **2026-07-18** — GOVERNANCE.md gained two binding sections: "Machinery artifacts: naming and
  organization" (self-explanatory names everywhere; enumerated/vague names like `proof1`/`S1`/
  `temp` disallowed; retrofit-on-touch) and "Repository layout: what goes where" (closed root
  set, per-directory placement table, scratch-never-enters-the-repo) — user directive after
  `proof1`-style names appeared in the investigations machinery; summarized in `AGENTS.md`.
- **2026-07-18** — Governance amended: agent-authored executables never live in session
  scratchpads/temp paths (work would die with the session) — they are written under
  `scripts/<category>/` from the first line; new `scripts/retrofits/` category holds one-shot
  transformation scripts, kept after running as the executable record ("no orphan artifacts"
  clarified to not mean "delete used one-shots"). Two retrofit scripts authored in a session
  scratchpad were rescued into `scripts/retrofits/` (`retire_superseded_plan_references.py`,
  `normalize_taskcard_vocabulary.py`) — user directive after seeing agents write tools to temp
  paths.
- **2026-07-18** — Layout governance gained two root directories: `prompts/` (all LLM-gateway
  prompt assets, any format including YAML/JSON state machines; loaded only by
  `src/readme_agent/llm/`) and `templates/` (all fill-and-match templates, e.g. README
  owned-span skeletons; loaded only by the owning module) — new placement rule 9: prompt/
  template content is data, never `src/` string literals; embedded content migrates on touch
  and loaded file content joins the hash-coupled generation inputs (preserving the
  `test_prompt_hash_coupling.py` determinism contract). Both dirs created with ownership
  READMEs; user directive.
- **2026-07-18** — GOVERNANCE.md gained "Code organization: no monoliths": one module per
  responsibility (module map as ledger), registry-pattern growth (file + entry, no if/elif
  chains), orchestration-wires-never-implements, public-seams-only imports (no upward/cyclic),
  split-before-extend at the ~300-line/second-concern smell — codifies the shape the codebase
  already has so refactoring stays cheap; user directive.
- **2026-07-18** — Added Decision #26 (agentic–deterministic blend as architectural doctrine:
  deterministic core, narrow agentic edge, proposal-only LLM output behind deterministic gates,
  hashed-input reproducibility, swappable agentic layer, deterministic-by-default for new
  capability) + requirements.md NFR-013 and coverage row — user directive naming the existing
  practice (#4, #6, #8, #11, #15, #16) as an explicit, binding principle.
- **2026-07-18 — Phase 20 presentation/control research delivered.** Live-surveyed all 25
  registry repositories (not just the 3 enabled pilots) and studied six real reference
  repositories (n8n, NuGet Aspose.Cells, iText, EPPlus, SheetJS, Apache PDFBox — the latter three
  self-selected as direct open-core/dual-license analogues to Aspose's own FOSS-to-commercial
  relationship). Delivered `docs/presentation-standard.md` and `docs/github-surface-control.md`
  (`DOC-003/004/005`, `RDM-019` → `IMPLEMENTED`). Corrected decision #9: the evidenced
  commercial-mention constraint is tone/density/singularity, not fixed end-of-file placement —
  two of four dual-licensed references studied mention their paid tier near the top. Confirmed
  GitHub's community-file quick-link row is a native, automatic feature requiring no UI work,
  only recognized-file presence — license recognition (28% of the registry fails it, all of the
  `cells` family) is now the identified highest-priority community-file target. Confirmed GitHub
  Packages is unused by every reference project studied; the sponsor's "list all possible
  packages" is correctly served by install-path accuracy, not GitHub-native Packages population.
  Traffic-feasibility study (`DOC-007`) remains open — no analytics access available. Evidence:
  `plans/investigations/full-registry-portfolio-survey.md`,
  `plans/investigations/reference-repository-benchmark.md`.
- **2026-07-18 — Phase 21a–21d built and landed.** `readme/presentation_report.py`
  (`READMEPresentationReport`, wired into `inspect_repo`); callout retired from
  `renderer.py`/`markers.py` (one `resources` span only, `GENERATION_SCHEMA_VERSION` → `"3"`,
  orchestrator migrates any already-materialized callout span out of a work clone unconditionally
  on next run); two new ERROR-severity validator rules (`product_first_opening`,
  `commercial_mention_discipline`, now 10 rules total) implementing decision #9/`BIZ-001`/
  `RDM-002`/`VAL-006` — verified against real pilot evidence (`pdf/java`'s legitimate
  2×`.com`-mention README) before shipping, to rule out a false positive the initial raw-count
  design would have produced; `ecosystems/resolver.py` (Maven Central live resolution, opt-in),
  exposed as the `inspect` verb's `--check-install` flag. 21e (section-aware change-plan
  auto-apply) stays design-only, deferred pending `change_boundary`'s own scoped evolution.
  Decisions #9, #16, #17 and the Architecture/Module-responsibilities/Validator-Registry sections
  updated from future tense to reflect the shipped state; stale two-owned-spans language corrected
  in `docs/architecture.md`, `AGENTS.md`, `templates/README.md`, `plans/GOVERNANCE.md`. Full suite
  clean: `ruff check`, `ruff format --check`, `mypy src`, `pytest -m "not live"` (215 passed).
  Pilot re-proof against the new code (`cells/java`, `3d/java`, `pdf/java`) not yet run — remains
  open in the Build Checklist. User directive: "design phase 21 and sync the plan," with two
  explicit decisions — `commercial_mention_discipline` ships at ERROR severity from the start
  (accepting `3d/java`'s next full run reports `BLOCKED_VALIDATION_FAILED`, not a regression to
  work around), and code ships this session rather than design-only.
- **2026-07-18 — Pilot re-proof found and fixed two real, pre-existing `orchestrator.py` bugs;
  all three pilots re-run live against the real repos.** Re-running `cells/java` with
  `--force-regenerate` (needed because the `GENERATION_SCHEMA_VERSION` bump to `"3"` made its
  existing embedded hash stale) exposed two genuine correctness defects that predate Phase 21 —
  latent since the very first `full`-mode force-regenerate this project ever ran, just never
  exercised until this re-proof:
  1. **Link-dropping on re-render.** `render_gap_report` was based on `gap_report` (computed from
     `current_text`, which includes the resources span about to be replaced) — so any element
     whose *only* evidence was inside that span (e.g. `cells/java`'s org/com links, present only
     because a prior full render put them there) was silently dropped the moment any *other*
     element needed re-rendering, because `upsert_span` replaces the whole span and
     `render_missing_elements` only includes currently-flagged gaps. Fixed: the render branch now
     re-detects gaps against the span-stripped text (`remove_span(current_text, "resources")`),
     so anything only the span was carrying is correctly re-flagged and re-included. The *skip*
     decision deliberately still uses the span-inclusive `gap_report` — decision #16's
     hash-mismatch-alone-never-auto-regenerates property is unchanged.
  2. **Spurious idempotency failure after a successful re-render.** `_validate`'s
     `ValidationContext.embedded_hash` was a closure over the *pre-render* hash captured before
     the skip/render decision — so validating a just-rendered `new_text` (which embeds a
     brand-new span with today's `facts_hash`) still compared against the old, stale value,
     making `idempotency` fail on every legitimate re-render of an already-spanned repo. Fixed:
     `_validate` now re-derives the embedded hash from whatever `readme_text` it was actually
     asked to validate.
  Both fixed with a regression test each in `tests/unit/test_orchestrator.py`
  (`TestStaleNoncompliantAndForceRegenerate::test_force_regenerate_preserves_previously_rendered_links`,
  `::test_force_regenerate_of_a_stale_hash_render_does_not_spuriously_fail_idempotency`) —
  each independently verified to fail on the pre-fix code and pass on the fixed code before
  being kept. A third, smaller bug was also found and fixed live: the CLI crashed
  (`UnicodeEncodeError`) printing `inspect`'s output for `3d/java` on a native Windows console
  (cp1252) because the real README contains an emoji; `cli.py`'s `main()` now reconfigures
  stdout/stderr to UTF-8 with `errors="replace"`. With all three fixed, all three real pilots
  were re-run live end to end — see the Build Checklist's Phase 21 pilot-re-proof line and the
  Verification Checklist for evidence run IDs and results, including the corrected, broadened
  Maven Central finding (Reference Data: all three enabled pilots, not just `cells/java`, are
  zero-result). Full suite after all fixes: `ruff check`, `ruff format --check`, `mypy src`,
  `pytest -m "not live"` (218 passed, up from 213 before this session's Phase 21 work).
- **2026-07-18 — Wave 0 of the autonomous-repository-presenter reset
  (`AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001`, sponsor directive).** Corrected the governing
  architecture doctrine from "deterministic core, narrow agentic edge" to "autonomous
  capability-driven control plane running primarily from GitHub Actions" — decision #26 rewritten
  in place (same number, per `GOVERNANCE.md` rule 4; text quoted above), decision #8 amended with
  a forward pointer instead of being rewritten (it still accurately describes the shipped engine's
  current LLM scope). `plans/requirements.md`'s `NFR-013` mirrors this change; ten new
  requirement-ID groups (`AGT-*`, `CAP-*`, `RUN-*`, `ECO-*`, `ONB-*`, `MEM-*`, `ORC-*`, `VER-*`,
  `GAP-*`, `SCL-*`) added there as a lean, all-`PLANNED` starter set — full detail lands
  incrementally as each later wave actually builds the thing a requirement describes, per
  `GOV-007`. Corrected project identity in `README.md`, `pyproject.toml`, and a new "Target
  architecture" lead section in `docs/architecture.md`; extended (not rewrote)
  `AGENTS.md`'s agentic–deterministic section and added a new "Extending the runtime" section
  stating the capability-first extension principles; added a new "Capability and agentic-component
  lifecycle" section to `GOVERNANCE.md` stating forward lifecycle rules (registration,
  deprecation/migration, capability-gap review, no silent duplicates) without yet defining the
  detailed schemas — those are Wave 2 (`plans/master.md`'s own sprint doc, Task 3.1). Verified
  before starting: no "select a skill/command" requirement existed anywhere in this repo to
  remove (sprint Task 1.3, not applicable here); `plans/investigations/
  llm-gateway-characterization.md` already empirically characterizes `llm.professionalize.com`
  (live model inventory, context-limit ladder, structured-output reliability per model), so
  decision #26(e)'s model-routing claim is evidence-backed, not reopened research. Also restored a
  fully truthful green baseline (sprint Task 0.3): fixed 41 pre-existing `ruff` violations (mostly
  `E501`, one `E741` ambiguous name, one `B905` missing `zip(strict=)`) confined to
  `plans/investigations/tools/*.py` — these were failing `ruff check .`, the exact command
  `.github/workflows/ci.yml` runs, even though `ruff check src tests` was already clean; no
  behavior change, these are read-only analysis scripts. Full suite after this wave: `ruff check
  .`, `ruff format --check .`, `mypy src` all clean; `pytest -q` → 220 passed, 3 deselected
  (`live`) — unchanged from before this wave, confirming no production behavior was touched.
  **What Wave 0 explicitly does not do** (left open for their own later, separately-planned
  waves): no capability registry/schema, no supervisor/task-graph runtime, no durable-state
  backend, no GitHub Actions runner redesign, no new ecosystem adapters, no package/CLI rename
  (`readme_agent`/`readme-agent` unchanged — decision #2; the `repository-presenter` rename
  remains a separately governed proposal), and none of the 15 new `docs/*.md` deliverables the
  sprint's Section 22 lists for later waves (each belongs with the wave that builds the thing it
  documents, not created empty ahead of time).
- **2026-07-18 — Wave 1 of the autonomous-repository-presenter reset (gateway tool-calling spike,
  runtime framework choice, one proven loop iteration).** Extended
  `plans/investigations/tools/probe_llm_gateway.py` (same file, established one-tool convention)
  with three new live probes — native single-step tool-calling, multi-step tool use, and parallel
  tool-call reliability — and folded the results into `llm-gateway-characterization.md` as
  findings L6–L8. Headline finding: native tool-calling is reliable for **both** chat models,
  including `gpt-oss` (5/5 single-step, despite its 1/10 freeform-JSON rate from L2) — the
  gateway's constrained tool-call decoding path is materially more reliable than asking it for
  freeform JSON. Parallel tool-calling works only for `qwen3-next`. Evaluated LangGraph, Pydantic
  AI, and OpenAI Agents SDK against live PyPI metadata and current docs (not assumed) in the new
  `plans/investigations/runtime-framework-evaluation.md`; recorded the decision — extend the
  existing orchestrator with a hand-rolled, typed task-graph/dispatcher, no new runtime framework
  — as Decision Ledger entry #27 (never renumbering #26). Built
  `plans/investigations/tools/prove_agentic_loop.py` and ran it live against the real,
  allow-listed `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` pilot: a 4-round
  observe→plan→execute→observe→replan loop using native tool-calling as the structured-action
  mechanism, wrapping three already-existing read-only functions (`inspect_repo`,
  `gap_detector.detect`, the opt-in Maven Central resolver) plus a `stop_and_report` convergence
  signal — full trace in `plans/investigations/agentic-loop-proof.md`. The model called each
  capability exactly once in a sensible order, never requested an unregistered or duplicate
  capability, and its final convergence summary correctly synthesized all three real results
  (independently reproducing this project's own known `pdf/java` finding — missing only the
  `.org` link — through the new mechanism, not the shipped deterministic pipeline). This satisfies
  `AGT-002`'s acceptance bar. First run used the planned `max_rounds=3` and consumed the entire
  budget on the 3 real capabilities with none left for `stop_and_report`; bumped to `max_rounds=4`
  and reran for the clean convergence trace kept as evidence (documented as a deviation, not a
  design defect). No `src/` files were touched this wave — `ruff check .`, `ruff format --check
  .`, `mypy src`, and `pytest -q` (220 passed, 3 deselected) are unchanged from Wave 0.
  **What Wave 1 explicitly does not do**: no `CapabilityManifest`/registry (Wave 2), no
  production supervisor or replanning-after-failure (Wave 5), no durable state (Wave 4), no
  adversarial/negative-control testing of the dispatcher gates (exercised structurally, not
  attacked). `plans/requirements.md`'s `AGT-002` moves `PLANNED` → `PARTIAL` with these three new
  investigation docs as its acceptance evidence; `CAP-004`, `ORC-001`, and the rest of §19 remain
  untouched, out of scope this wave.
- **2026-07-18 — Wave 2: capability foundation, first real production capability code.** New
  package `src/readme_agent/capabilities/`, mirroring two proven patterns exactly rather than
  inventing new ones: the "one implementation per file, composed by a dispatch table" shape
  already used by `validation/rules/`+`validation/registry.py` and `ecosystems/registry.py`
  ("new entries, not new call sites"), and `registry/models.py`/`llm/schema.py`'s pydantic-typed-
  contract style. `schema.py` defines `CapabilityManifest` (every field the sprint's Section 7
  Task 3.1 lists — populated where genuinely known today, left `None`/empty with a one-line
  "which wave gives this real meaning" note otherwise, so no later wave needs a breaking schema
  change) and `CapabilityGap` (`CAP-003`/`GAP-001` — an explicit record, never a silent skip; its
  `GAP-002` final-run-status integration is left to Wave 5, which is the first wave with a
  "run"). A new, minimal `PermissionClass` enum (`read_only_local`/`read_only_network`/
  `local_write`/`remote_write`, GOVERNANCE.md rule 5's "explicit and minimal") is reused for both
  `required_permissions` and `side_effect_class` rather than two near-duplicate enums.
  `registry.py` builds a `capability_id → (manifest, executor)` table at import time, raising
  `ConfigError` on any duplicate ID (GOVERNANCE rule 2). Three capabilities registered — the same
  three functions Wave 1's spike wrapped, now with real manifests: `inspect_repository`,
  `detect_readme_gaps` (`read_only_local`), `check_install_path` (`read_only_network` — the one
  capability whose permission class is actually observable in a test). `dispatcher.py` promotes
  Wave 1 spike's proven inline dispatch loop into reusable code implementing sprint Task 4.2:
  parses an OpenAI tool-call dict, rejects unknown `capability_id`s as a `CapabilityGap` (not a
  silent no-op), rejects a `side_effect_class` outside the caller's `allowed_permissions`, rejects
  missing required arguments, and turns any wrapped-function exception into a typed
  `execution_error` outcome rather than a crash — a bad request is data the caller inspects, never
  unrestricted execution reaching the model. 22 new offline unit tests
  (`tests/unit/test_capabilities.py`, `tests/unit/test_capability_dispatcher.py`, all
  monkeypatched, no real clone/network) plus one live integration test
  (`tests/integration/test_capabilities_live.py`, `@pytest.mark.live`) proving the real registry
  and dispatcher — not a spike script — work end to end against the real gateway and the real
  `pdf/java` pilot: a live `qwen3-next` tool call for `inspect_repository` dispatched successfully
  through the production code path. Full suite: `ruff check .`, `ruff format --check .`, `mypy
  src` all clean (69 source files now, up from 62); `pytest -q` → 242 passed, 4 deselected
  (`live`), up from 220/3 — the `+1` deselected is the new live capabilities test, correctly
  excluded from default CI. **What Wave 2 explicitly does not do**: no `RepositoryProfile`/
  archetype model (Wave 3) — the schema's archetype/language/build-system/registry fields exist
  but stay empty for these three capabilities; no durable state or run-level evidence writing for
  capability calls (Wave 4/5); no production supervisor or task graph (Wave 5) — the live test
  proves one dispatch, not a loop; no cache/fingerprint reuse or retry policy beyond what the
  wrapped functions already have; no mutating capability (`local_write`/`remote_write`) exists
  yet, so the dispatcher's permission gate has not been exercised against a real write attempt,
  only proven to correctly refuse one in tests.
- **2026-07-19** — Decision 24 clarified in place (no renumbering): research/development tasks
  (portfolio surveys, fact-gathering, policy/validator design, gap analysis, etc.) MUST cover
  every `data/products.json` entry with equal precedence regardless of `mode`; only end-to-end
  execution is scoped to the three enabled Java pilots, and only because they are the sole
  non-`disabled` entries today — an access constraint, not a precedence signal. Mirrored as
  `PIL-011` in `plans/requirements.md`.
- **2026-07-19 — Response to an independent review conducted before Wave 3.** The review audited
  the codebase's battle-tested-library-vs-bespoke-code footprint and found strong adherence
  everywhere except one already-reasoned exception (decision #27) and one implicit,
  never-recorded choice: raw `requests` over PyGithub for the three read-only GitHub API endpoint
  shapes in `preflight/github_check.py` and `scripts/update_products_registry.py`. It also warned
  that Wave 2's live LLM evidence was thin (N=1 trials, happy-path only) relative to the risk of
  testing mostly against mocks and only lightly against real model variability. Three concrete
  actions taken, not just acknowledged:
  1. **Decision #28 added** (never renumbering #27): keep raw `requests` — the exposure is small
     and already field-proven against all 26 real orgs — but recorded explicitly instead of left
     implicit, with a documented trigger for revisiting it (write operations, mutation-heavy
     pagination, or enough added endpoints that hand-rolling stops being the smaller amount of
     code).
  2. **A real, narrow gap the review prompted a direct look for was found and fixed**:
     `scripts/update_products_registry.py`'s `_paginate` only read `X-RateLimit-Reset` (the
     primary/core rate limit) on a 403, not `Retry-After` (how GitHub signals the
     secondary/abuse-detection limit, which can fire with core quota still remaining). Fixed via
     `_rate_limit_wait_seconds()`, checking `Retry-After` first; added
     `tests/unit/test_update_products_registry.py::TestRateLimitWaitSeconds` (3 cases), a branch
     that had zero coverage before.
  3. **A live robustness campaign against the real, unmodified capability dispatcher** — not the
     mocked unit tests — directly answering the thin-live-evidence warning:
     `plans/investigations/tools/probe_capability_dispatch_robustness.py` ran 18 additional live
     calls across four dimensions (multi-trial consistency per capability, a full 3-tool menu
     under an open-ended instruction, an instruction with no good tool match, and `gpt-oss` — the
     shipped engine's actual default model, not yet run through the production dispatcher before
     this). **18/18 succeeded**; the two safety-relevant behaviors (correct capability selection,
     correct abstention when no tool fits) both held under real model output. One non-defect
     observation worth carrying into Wave 5: at `temperature=0.0`, an open-ended instruction
     converges deterministically on one capability rather than exploring the menu — a real
     planner needs situationally specific instructions per turn, not vague ones. Full findings
     and evidence: `plans/investigations/capability-dispatch-robustness.md`. **Conclusion: no
     basis to reverse decision #27** — the newest, most complex piece of the system now has
     broader live evidence behind it, and nothing surfaced a dispatcher defect; the sample size
     (18 live calls) is still small relative to production scale, so a larger-N calibration is
     flagged as the right next increment before Wave 5, not before Wave 3. Full suite after all
     three actions: `ruff check .`, `ruff format --check .`, `mypy src` clean (69 source files,
     unchanged — this response touched `scripts/`, `tests/`, and `plans/`, no new `src/` module);
     `pytest -q` → 245 passed (up 3 for `TestRateLimitWaitSeconds`), 6 deselected (live,
     unchanged).
- **2026-07-19 — Backlog discipline (decision 29).** Added a `BACKLOG` requirement status and
  `GOV-014` in `plans/requirements.md`: an agent that finds a non-blocking issue outside its
  current task MUST log it as an open `BACKLOG` requirement row rather than scope-creeping into an
  unrequested fix or silently dropping it; an issue that blocks the current task MUST be fixed
  first. `AGENTS.md` summarizes the working rule. User directive.
- **2026-07-19 — Status section corrected against the Decision Ledger/Build Checklist it had
  drifted from.** Fixed a self-contradiction (Phase 21 listed as both done-except-21e and fully
  not-yet-done), replaced a stale 2026-07-18 test-baseline snapshot with the current one (245
  passed, 6 deselected), reworded the "frozen until this document repair lands" clause now that
  Wave 0 is done, and added the Wave 0–9 sprint status (2 of 9 done) that `Status` never
  mentioned. `AGENTS.md`'s "Extending the runtime" intro updated the same way (Wave 2 already
  landed, not a future contingency). Found while answering a status query. User directive.
- **2026-07-19 — Wave 3: heterogeneous repository profiling, built by adapting aspose.org's
  proven manifest extraction, not writing it from scratch.** Replanned twice before
  implementation, both times on user pushback with real substance, not just process: (1) the
  first plan built `RepositoryProfile` as a second, parallel manifest scanner beside the existing
  one-ecosystem-only `inspection/file_inventory.py`/`ecosystems/registry.py` — rejected;
  generalized the existing detection instead (`FileInventory.pom_path` → `manifest_paths:
  dict[str, Path]`, data-driven from a new `ecosystems.registry.known_manifest_globs()`), so
  `profile/` reads the same single source of truth the shipped pipeline now also uses. (2) A
  direct question — "use proven battle-tested tools... it is in governance, right?" — was
  answered honestly (checked: it wasn't) and then acted on: formalized as GOVERNANCE.md rule 8 +
  decision #30, and its first real application found and adapted aspose.org's actual, currently-
  running `scripts/pipeline/extraction/package_manifest.py` (`D:\onedrive\Documents\GitHub\
  aspose.org`) instead of hand-writing new parsers — six real platforms (Java: pom.xml *or*
  build.gradle; Python; .NET; TypeScript; Go; C++), all stdlib-only. This reversed an
  intermediate decision to rewrite `ecosystems/maven.py` from regex to `xml.etree.ElementTree`:
  once the actual proven reference was found, it turned out to use regex too, with the same
  `<parent>`-block limitation `maven.py` already documented — kept as-is, not reopened.
  `ecosystems/maven.py` renamed `java.py` (Gradle fallback + `runtime_min_version` added, ported
  from the same source). Registry dispatch keys renamed to match `ProductEntry.platform`'s real
  vocabulary (`"maven"` → `"java"`, plus `"python"`/`"net"`/`"typescript"`/`"go"`/`"cpp"`) —
  `data/products.json`'s three real Java entries and `ecosystems/resolver.py`'s Maven Central
  dispatch key migrated in the same change (the resolver rename was a real bug caught by testing
  `check_install_path` after the fact, not planned — fixed before it shipped). Byte-for-byte
  regression proof against all three real pilots: `manifest` dict changed only by gaining a
  genuinely new fact (`runtime_min_version`, since the real pom.xml files do carry
  `maven.compiler.*` properties); `gap_report`, rendered content, and `diff.patch` unchanged;
  zero LLM calls; zero new commits. `cells/java` and `pdf/java` correctly flip
  `COMPLIANT_NO_CHANGE` → `STALE_NONCOMPLIANT` because `facts_hash` includes the whole manifest
  dict and a genuinely new fact changed it — the `idempotency` rule catching this is decision
  #15's "fail-closed even for a purely cosmetic edit" working as designed, not a regression;
  `3d/java` unchanged (same pre-existing `commercial_mention_discipline` failure). New
  `profile_repository` capability, live-proven through the real dispatcher against the real
  `pdf/java` pilot (not the disabled Python entry originally planned — decision #4's allow-list
  is a hard, unconditional gate on every real clone/git operation; decision 24/`PIL-011`'s
  "regardless of mode" carve-out is about analysis *scope*, not a license to bypass it for live
  capability execution — corrected before implementing, not after). Also: a `BACKLOG` row
  (`VAL-018`) for the prominence render-then-rerun bug found during Wave 2's verification, which
  had been reported in chat and a deferral confirmed but never actually logged as decision
  #29/`GOV-014` requires — a real compliance gap, fixed in passing. Full suite: `ruff check .`,
  `ruff format --check .`, `mypy src` clean (78 source files, up from 69); `pytest -q` → 282
  passed, 7 deselected (`live` — one more than before, the new `profile_repository` live test).
  **What Wave 3 explicitly does not do**: no live package-registry resolution for the five new
  platforms (PyPI/npm/NuGet — `ecosystems/resolver.py` stays Maven-only opt-in); no monorepo/
  multi-package-root detection (single top-level manifest scan only); no live verification of the
  five new platforms against a *real* non-Java repo (only synthetic fixtures — blocked by
  decision #4, since no non-Java registry entry is enabled; a stated, honest limitation);
  `ONB-001`/`ONB-003` untouched (no new discovery source needed); the prominence bug itself
  remains unfixed, only properly logged.
- **2026-07-19 — Investigate before overwriting (decision 31).** New `GOVERNANCE.md` rule 9 and
  `plans/requirements.md`'s `GOV-017`: an agent (human or AI) MUST investigate a file, Decision
  Ledger entry, requirement row, evidence artifact, or git state — read it, check its history —
  before overwriting, replacing, deleting, or discarding it, and preserve/migrate/pause for user
  input rather than silently clobber it when the investigation shows the content matters. This
  generalizes disciplines that already existed for specific artifact classes (`GOV-002`/`GOV-003`,
  the fixtures immutable-snapshot rule, no-orphan-artifacts) into one repo-wide rule. §21
  decision-ledger coverage: new row for decision 31 → `GOV-017`. `AGENTS.md` carries the
  working-rule summary. User directive.
- **2026-07-19 — Wave 3 hardening: full-registry (all 25 real repos) ecosystem-detection survey
  found and fixed 2 real bugs.** User directive: use every `data/products.json` entry, not just
  the 3 enabled pilots, to prove/validate/tweak/harden Wave 3. New investigation
  (`plans/investigations/full-registry-ecosystem-detection-survey.md` +
  `tools/survey_full_registry_ecosystem_detection.py`, read-only `clone_baseline()` against all
  25 entries regardless of mode, decision 24/`PIL-011`'s research-scope carve-out) surfaced two
  genuine defects synthetic fixtures hadn't: (1) a crash —
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Python`'s `pyproject.toml` uses the flat
  `[tool.setuptools] packages = [...]` shape, not the nested `packages.find.include` shape the
  aspose.org-adapted code assumed unconditionally; fixed in `ecosystems/python.py` to check both.
  (2) A systemic 100%-miss detection gap — every real `.NET` repo in the registry (5/5) plus one
  `cpp` repo puts its manifest in a subdirectory (`src/<Project>/*.csproj`,
  `<Project>/CMakeLists.txt`), but `inspection/file_inventory.py`'s `_find_manifest_paths()`
  only ever checked the repo root; fixed with a single bounded `os.walk` (not one `rglob` per
  pattern — would have multiplied the exact latency problem the survey's own timing data
  exposed on a ~1 GB real repo) skipping common noise directories. A confirming rerun: 25/25
  repos profile without a crash, 0 missed detections (was 1 crash + 6 misses). Regression-proven
  against the 3 real enabled Java pilots — byte-identical `facts_hash`/`manifest`/`gap_report`/
  `validation_report.json`/`diff.patch`, zero new commits, zero LLM calls — since
  `file_inventory.py`'s rewrite is load-bearing for the shipped pipeline too, not just the new
  profiling capability. 4 new regression tests, one per real failure mode found. Full suite:
  `ruff check .`, `ruff format --check .`, `mypy src` clean; `pytest -q` → 286 passed (up from
  282), 7 deselected, unchanged. **What did not improve**: `aspose-page-foss` (~1 GB, 2500+
  files) still takes ~175–185s to profile — the single-walk redesign still must traverse the
  whole tree for a single-ecosystem repo, since most registered ecosystems' patterns never
  resolve; a documented, open item, not fixed this pass (no current caller needs a hard latency
  bound yet). `ecosystems/resolver.py`'s live resolution stays Maven-only, untested against the
  newly-detected platforms — an existing, unreopened Wave 3 scope boundary.
- **2026-07-19 — Reconciled `NFR-012` with the Decision #26 doctrine; new `LLM-015`/`LLM-016`;
  new `BACKLOG` row `GOV-016`.** User-directed root-cause review of why agentic/LLM-driven work
  keeps deferring to later waves found that `NFR-012` ("SHOULD minimize LLM calls... wherever
  possible," `plans/requirements.md` §15) was never updated when `NFR-013` was rewritten during
  Wave 0's doctrine correction — a live, `PLANNED` requirement directly contradicting the
  corrected doctrine sat two lines away from it unreconciled. Decision 8's own prose already says
  it's "no longer the ceiling on future LLM jobs," but the requirement row citing it was never
  touched. `NFR-012` reworded in place: scoped to *redundant* calls only (identical inputs must
  not re-trigger generation/selection — `NFR-001`/idempotency), explicit that it MUST NOT be read
  as minimizing legitimate judgment/planning/coordination usage; traceability now cites Decisions
  8 and 26. New `LLM-015` (P2, `PLANNED`): every run's evidence/report MUST record LLM gateway
  call count and the triggering job/capability — the usage-visibility forcing function the sponsor
  asked for (gateway calls are free; usage should be measured, not avoided). Two `BACKLOG` rows
  per decision 29/`GOV-014` from the same review (non-blocking, not fixed inline): `LLM-016` —
  `env.py:6`'s `DEFAULT_LLM_MODEL="gpt-oss"` default contradicts
  `llm-gateway-characterization.md`'s own finding that `gpt-oss` is unreliable (1/10) for the
  freeform job it's used for; `GOV-016` — `llm/prompts.py`'s prompt is still inline, grandfathered
  against the `prompts/`-only rule. §21 decision-ledger coverage in `requirements.md` updated
  under decision 26 (doctrine enforcement, not a new decision). Whether Wave 3 (or an earlier
  wave) should also carry a hard minimum-LLM-usage acceptance gate, versus tracking-only, remains
  an open question for the sponsor — not decided by this entry. User directive.
- **2026-07-19 — `LLM-015`/`LLM-016`/`GOV-016` implemented (closes the doctrine-enforcement
  review above).** Sponsor confirmed tracking-only, no hard wave gate. `env.py` gained
  `JOB_MODEL_ROUTING`/`llm_model_for_job()` (env override > per-job table > default);
  `relationship_explained` now routes to `qwen3-next`, and `DEFAULT_LLM_MODEL`'s bare fallback
  changed from `gpt-oss` to `qwen3-next` too (Decision 26(e): prefer it generally for
  instruction-critical/structured work). The prompt migrated to
  `prompts/relationship_explained/{system,user}.txt` (`string.Template`, not `.format()` — the
  response-shape example contains literal JSON braces `.format()` would choke on);
  `llm/prompts.py::prompt_content_hash()` hashes the loaded assets into a new
  `RepositoryFacts.prompt_content_hash` field joining `facts_hash`, so an edited prompt file
  forces regeneration automatically — the mechanism `prompts/README.md` rule 3 promised but the
  embedded-string version structurally couldn't deliver. `GENERATION_SCHEMA_VERSION` bumped
  `3`→`4` (a real `build_prompt()` implementation change) and the version-tripwire snapshot
  regenerated. `evidence/writer.py::write_evidence()` gained a required `llm_calls: list[str]`
  parameter written into `manifest.json` as `llm_call_count`/`llm_calls` — surfaced for free by
  the existing `readme-agent report <run_id>` command; `GenerateResult.llm_calls` added alongside
  the existing `llm_called` bool, surfaced in `cmd_generate`'s stdout. New tests:
  `tests/unit/test_env.py`, `tests/unit/test_llm_prompts.py`; extended `test_readme_facts.py`,
  `test_prompt_hash_coupling.py`, `test_evidence_writer.py`, `test_orchestrator.py`,
  `test_preflight.py` (two `gpt-oss`→`qwen3-next` default-model assertions),
  `tests/security/test_no_secrets_in_evidence.py` (fixture project root now also materializes
  `prompts/relationship_explained/`, matching the existing cwd-relative-config test pattern this
  file already used for `config/policies/`). Also discovered mid-fix, unrelated to any of this:
  another concurrent session was live-editing this same file and `requirements.md` (Wave 3/3-
  hardening) throughout — confirmed with the user before continuing, no conflicting edits
  occurred (append-only Changelog writes, disjoint from the Decision Ledger/requirement-row edits
  the other session was making). Full suite: `ruff check .`, `ruff format --check .`, `mypy src`
  clean; `pytest -q` → 296 passed (up from 286), 7 deselected, unchanged. User directive.
- **2026-07-19 — Capability-dispatch production-readiness assessment.** New
  `plans/investigations/capability-dispatch-production-readiness.md`: root-causes what would break
  consistency across reruns in the capability dispatcher (Wave 2, still zero production callers)
  ahead of Wave 5 wiring it into a supervisor — separates the availability gap (no retry on the
  tool-calling path) from the harder idempotency gap (nothing makes it safe to retry a future
  `gated_effector` effect), and specifies an idempotency-key ledger extending decision #11's
  `facts_hash` pattern (detail added to decision #26 above; new `EFF-*` requirements in
  `plans/requirements.md` §19). Also corrected an overstated finding found via direct primary-
  source inspection: `probe_llm_gateway.py:366-399` shows the "`gpt-oss` drops one of two parallel
  tool calls" claim rests on a single trial per model, not a repeated-trial result — fixed in
  place in decision #27 above and in `llm-gateway-characterization.md`'s L7 row, downgraded to
  `RESEARCH-GATED` pending a specified N≥10/≥2-session follow-up; no existing decision depended on
  the original wording. Reassessed against current system state three times before this edit
  (`GOV-017`) — Wave 3, decisions #30/#31, and the `LLM-015`/`LLM-016`/`GOV-016` implementation all
  landed *during* this task's own investigation; none of them touched the capability dispatcher,
  `requirements.md`'s `EFF`-adjacent rows, or the gateway-characterization doc, so this task's two
  core findings were unaffected by that concurrent work. User directive.
- **2026-07-19 — Wave 4: durable runner state (decision #32).** `RUN-001`/`MEM-001`/`MEM-002` →
  `PARTIAL`, `MEM-003` → `IMPLEMENTED`. Re-verified `we-are-not-as-piped-naur.md` and the
  just-executed `capability-dispatch-production-readiness.md` immediately before designing:
  confirmed only remediation step 6 (first non-deterministic capability) remains, logged as new
  `BACKLOG` row `CAP-005`; confirmed `EFF-001`/`002` name this wave's backend evaluation directly
  and designed `CapabilityOutputCacheEntry.fingerprint` to double as `EFF-001`'s idempotency key
  for Wave 5. A first backend draft (one shared git branch, every repo's state as separate files)
  was reassessed and reversed before implementation — a shared branch's non-fast-forward CAS is
  scoped to the whole ref, so unrelated repos' writes would have falsely conflicted, contradicting
  `MEM-002`'s actual per-repository concurrency unit — reversed to one dedicated git ref per
  `org_repo` (`refs/readme-agent-state/{org}__{repo}`). New `src/readme_agent/state/` (`schema.py`,
  `backend.py`'s `StateBackend` Protocol, `git_backend.py`'s `GitStateBackend` — git plumbing
  only, no per-write working-tree checkout); wired into `orchestrator.generate_repo()` additively
  (`state_backend=None` default, every existing caller unaffected), opt-in via new CLI
  `--durable-state` (mirrors `--check-install`); `readme-agent-run.yml` gained job-level
  `contents: write` and passes the flag by default. New tests: `test_state_schema.py`,
  `test_state_backend.py` (fake backend proves the CAS/lock contract, including the
  cross-repo-no-false-conflict property), `test_orchestrator.py::TestDurableStateFreshRunner`
  (two independent runner directories sharing one durable backend — the concrete `RUN-001`
  regression test), `test_state_git_backend_live.py` (`@pytest.mark.live`, written, not yet run —
  needs explicit confirmation before pushing to this project's own remote). Full suite: `ruff
  check .`, `ruff format --check .`, `mypy src` clean; `pytest -q` → 312 passed (up from 296), 11
  deselected (up from 7). User directive.
- **2026-07-19 — Wave 4 live proof: real bug found and fixed; `MEM-002` → `IMPLEMENTED`.** User
  confirmed running the live push test against this project's own remote. First run: 1/4 passed;
  every `mktree`-touching test failed with `path 'state.json' does not exist`. Root-caused
  directly: `git ls-tree` on the pushed commit showed the stored path as `"state.json\r"` --
  `subprocess.run(text=True, input=...)` translates `\n` to `os.linesep` (`\r\n` on Windows) on
  the *write* side too, corrupting `git_backend.py`'s `mktree` input before it reached git. Fixed
  in `gitsafety/_git.py::run_git()`: stdin is now piped as raw UTF-8 bytes when `input_text` is
  given, bypassing text-mode's stdin encoding entirely; every other caller (`input_text=None`)
  unaffected. Second run: 3/4 passed; the lock-reclaim test's own 1-second patched lease was
  shorter than a real `acquire_lock()` round-trip (~2-5s observed) -- a test-timing bug, not a
  backend bug -- widened to 8s. Third run: 4/4 passed. A real Windows-only bug no offline/fixture
  test could have caught -- exactly the reason this project's convention is to actually run live
  tests, not trust the mock alone. Local push auth used a temporary, repo-scoped
  `http.https://github.com/.extraheader` from the already-present `GH_TOKEN` (Git Credential
  Manager's interactive flow hangs non-interactively), removed immediately after; no stray
  `refs/readme-agent-state/*` refs left on `origin` at any point (each test's own `finally`
  cleanup ran even on failure). `MEM-002` → `IMPLEMENTED`; `RUN-001`/`MEM-001` stay `PARTIAL` -- the
  backend is live-proven, but no actual GitHub Actions runner run has been observed (`RUN-003`'s
  `act` reproduction remains `PLANNED`). Full suite re-clean: `ruff check .`, `ruff format
  --check .`, `mypy src`, `pytest -q` → 312 passed, unchanged. User directive.
- **2026-07-19 — RUN-003 closed via a real `act` reproduction; two real bugs found and fixed;
  `RUN-001` → `IMPLEMENTED`.** User asked to prove Wave 4 both in isolation and in the pipeline,
  then to attempt `RUN-003` specifically. Pipeline-level A/B/C proof on the real blank-slate pilot
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` (`--mode dry_run`) first: clean slate +
  `--durable-state` (1 LLM call, establishes state) -> `runs/` wiped + `--durable-state` (0 LLM
  calls, work clone confirmed to carry zero markers, last commit = original upstream commit) ->
  same wipe without the flag (1 LLM call again, the exact pre-Wave-4 defect reproduced on demand).
  Real LLM output inspected for quality per user request, not just call counts: all 10 validators
  passed. Then `act workflow_dispatch -W .github/workflows/readme-agent-run.yml` against Docker
  Desktop. Confirmed `act`'s checkout uses `docker cp` of the actual local working tree (container
  `git log` showed local HEAD `4adbaaf`, not the stale `origin/main`), so this genuinely exercised
  Wave 4's real code. First run: durable state was correctly read and recognized (fresh work
  clone, zero LLM calls, confirmed by inspecting the still-running container directly) but the
  write-back then failed -- `actions/checkout@v4`'s `persist-credentials` did not set
  `http.extraheader` under `act`'s local-copy checkout path (confirmed absent by direct
  inspection), and the failure was uncaught, aborting the whole run and losing the evidence bundle
  for work that had already succeeded. Fixed: `orchestrator.py`'s durable-state read and
  `_record_accepted_state`'s write-back are now both best-effort, mirroring `inspect_repo`'s
  `check_install` "opt-in enhancement never fails the command" convention -- new regression test
  `test_unreachable_state_backend_does_not_abort_the_run`. Second run: the CLI step succeeded with
  the warning printed as designed, but `upload-artifact` failed -- `readme-agent-run.yml` used
  `inputs.repo_key` ("org/repo") directly as the artifact name, which the GitHub Actions API
  rejects (`/` is invalid); a real, pre-existing bug, unrelated to Wave 4, only surfaced because
  this was the first time the workflow had ever actually been run. Fixed with a shell step
  sanitizing to this project's own `{org}__{repo}` convention. Third run: `Job succeeded`, end to
  end. One purely `act`-specific (not production) gap hit and worked around: `upload-artifact`
  needs `ACTIONS_RUNTIME_TOKEN`, which only a genuine GitHub-hosted runner provides for free --
  `act --artifact-server-path` emulates it locally, now defaulted in `.actrc`. `RUN-001`/`RUN-003`
  -> `IMPLEMENTED` (`requirements.md`). Full suite re-clean: `ruff check .`, `ruff format
  --check .`, `mypy src`, `pytest -q` -> 313 passed (up from 312), 11 deselected, unchanged. User
  directive.
- **2026-07-19 — Prove it in production (decision 33).** New `GOV-018`: a requirement or Build
  Checklist line MUST NOT be marked done on unit-test or mocked-fixture evidence alone — it needs a
  real, production-like demonstration matched to what it claims (real repos, a live LLM/gateway
  call, a real CI reproduction), exercised read-only/dry-run under the existing push-blocking and
  allow-list safety properties. Sharpens `GOV-007`'s acceptance bar; codifies the discipline this
  project's own Changelog already shows in every phase closeout (pilot re-proofs, the `RUN-003`
  `act` reproduction, Wave 2's live capability call). `AGENTS.md` carries the working-rule summary.
  User directive.
- **2026-07-19 — Prove it in production clarified: not a permanent push ban, an approval gate.**
  Direct user follow-up: "prove it on production does not mean pushing anything to the product
  repos at this stage. it should need explicit approval from the user." The same-day first draft of
  decision 33/`GOV-018` had worded the production-vs-push distinction as "that stays forbidden
  regardless of how proven a change is" — read as a blanket, permanent prohibition. Corrected in
  `GOVERNANCE.md` rule 10, decision 33, `GOV-018`, and `AGENTS.md`: at this stage, proving a
  requirement "in production" never itself authorizes committing or pushing to the actual product
  repos as a side effect; any real write to a managed remote still requires the user's separate,
  explicit approval each time. This is the existing pilot posture's default, not a new restriction
  — the correction is to state it as an approval gate rather than an outright ban, since a future
  stage may add real writes under that same gate. User directive.
- **2026-07-19 — Decision 30/`GOV-015`/GOVERNANCE.md rule 8 broadened: any new functionality, not
  just parsing/protocol/integration code.** Direct user follow-up: "hand-rolling everything instead
  of using battle tested tools is prohibited. The agent must be able to research, select,
  incorporate and build upon battle tested tools instead of handrolling everything. It is related
  to more tools means, lest handroled code and less troubleshooting" — then clarified further: "It
  must be discourged but allowed in special circumstances." Widened the rule's scope from its
  original "new parsing/protocol/integration code" framing to any new functionality, and made the
  duty active (research/select/incorporate/build-upon an existing tool) rather than a check
  performed only when already about to write bespoke code. Kept the existing discouraged-not-banned
  shape unchanged: a deviation still needs the same explicit, reasoned Decision Ledger entry
  #27/#28 already met — this was already how #30 worked, the broadening is scope, not the escape
  hatch. User directive.
- **2026-07-19 — Specialist domain-isolation, root-caused as a production problem: two new
  decisions, one code retrofit ahead of Wave 6.** Third pass on "independent agents, each in their
  own domain." First pass treated it as one question ("which framework?") and stopped at a
  documentation-only addendum — rejected as symptom-level. Second pass root-caused four gaps
  (domain/permission enforcement, per-domain durable state, `EFF-*`-as-a-gate, repo-surface
  ownership) but designed hand-rolled fixes for the first two without testing that choice against
  real alternatives — rejected again, inconsistent with having separately adopted a proven
  framework (LangGraph, decision #27's addendum) for specialist composition. This pass supplied the
  missing evidence: two independent desk-research passes evaluated real, current authorization
  libraries (Oso, Casbin, Cedar, OPA, py-abac, Vakt) and durable multi-writer state-coordination
  primitives (GitHub Contents/Issues/Discussions/Checks APIs, S3/DynamoDB conditional writes,
  SQLite-as-blob-content) against this project's actual constraints, verified via primary sources
  (release dates, git's own wire-protocol documentation) rather than asserted from memory. Verdict:
  **decision #34** (domain-invocation enforcement) and **decision #35** (multi-writer durable
  state) both extend the hand-rolled pattern — every real proven alternative either was abandoned,
  needed a sidecar process, imported disproportionate machinery, or reopened infrastructure decision
  #32 already rejected — while decision #27's LangGraph adoption for composition stands unchanged.
  Two of three sub-decisions came back "extend," one came back "adopt" — evaluated independently,
  not from a blanket preference either direction. Full evidence:
  `plans/investigations/specialist-domain-isolation-production-readiness.md` (new). **Shipped as
  code this pass, not deferred**: `capabilities/domains.py` (new), `schema.py`'s `allowed_domains`
  field, `registry.py`'s domain-membership/fail-closed-sunset/`EFF-001`-registration checks,
  `dispatcher.py`'s `caller_domain` parameter and `rejected_domain_denied` outcome; `state/schema.py`'s
  `DomainStateV1`/`RunStateV1.domain_states`, `state/domain_state.py::save_domain()` (composes the
  already-existing `acquire_lock`/`release_lock` lease as primary serialization, version-CAS as a
  lease-expiry backstop). All additive — zero existing manifest, call site, or test needed a
  behavioral change; 23 new tests, 335 passed / 11 deselected (up from 312/11), full suite green.
  New `CAP-006`/`MEM-004` (both `PARTIAL` per `GOV-018` — mechanism built and unit-tested, real
  domain population and live multi-specialist proof are Wave 6's job); `EFF-001` `PLANNED` →
  `PARTIAL`; `AGT-002`/`OWN-011`/`ORC-003` evidence text extended; new `BACKLOG` row `AGT-005`
  (multi-specialist reliability is unmeasured — only N=1, single-planner evidence exists). Also
  found and fixed a real gap discovered mid-pass, not designed around: `dispatcher.py`'s permission
  check already existed and was correct for blast radius, but `CapabilityManifest` had no caller-
  identity axis at all — confirmed a missing schema dimension, not a dispatcher defect, before
  proposing a fix. Explicitly deferred, logged not silently dropped: repo-surface/file-ownership
  generalization beyond `markers.py`'s single span (`OWN-011`, Wave 7's real specialist-to-surface
  mapping doesn't exist yet); a live, N>1, multi-specialist reliability proof (`AGT-005`);
  sequential-vs-parallel specialist dispatch policy (noted against `ORC-003`, not decided — no
  supervisor exists yet to enforce it either way). User directive.
- **2026-07-19 — Live-test push-credential hang found, root-caused, and worked around; new
  `OPS-009` (`BACKLOG`).** Live-verifying decisions #34/#35 above surfaced a real, separate gap:
  `git push` inside `test_state_git_backend_live.py` hung silently for ~35 minutes, zero output,
  before being diagnosed — `GH_TOKEN` being present does not by itself wire git's push
  authentication, and the hang sits inside git's own credential resolution, outside both
  `run_git()`'s 120s subprocess timeout and pytest's own reporting (confirmed via a bounded,
  reproducible `git push` probe under a hard shell timeout: silent, no-output failure). Fixed for
  this session with a temporary `http.https://github.com/.extraheader` built from `GH_TOKEN`,
  removed immediately after; all 8 live tests (`test_capabilities_live.py`'s 4 plus
  `test_state_git_backend_live.py`'s 4) then passed. Not a CI gap — `actions/checkout` wires the
  runner token automatically, matching why `RUN-003`'s `act` reproduction never hit this. Documented
  as a prerequisite directly in the test file's docstring; `OPS-009` (`plans/requirements.md`) logs
  that no scripted/automatic fix exists yet, per decision #29. User directive.
- **2026-07-19 — Wave 5: production supervisor, task graph, effect-safety ledger (decision #36).**
  Built `src/readme_agent/supervisor/` (task graph with `ORC-001`'s exact states + two independent
  cycle checks + `SUPERSEDED` dedup; `AGT-004`'s four stop conditions; `ORC-002`/`VER-002` failure
  classification and auto-repair; `supervise_repo()`, promoting Wave 1's spike), `llm/planner_client.py`
  (new Live/Fixture pair -- `LLMClient` can't carry a tool-calling response), and
  `capabilities/effect_ledger.py` (`EFF-002`/`003`, dispatch-tier). New CLI `supervise` verb,
  additive alongside `run`/`run-registry`. A real conflict between a user confirmation and an
  already-recorded same-day decision (register `generate_repo()` now vs. decision #26's "Wave 5
  never registers a capability") was surfaced and resolved by separating "which wave registers a
  capability" (Wave 7, unchanged) from "which wave proves the safety mechanism" (now, via a
  synthetic effector) rather than silently picked either way. A genuine flaw in the cited prior
  investigation's own design (storing the pending/applied intent record in local evidence JSON --
  exactly what `GitStateBackend` exists to replace) was found and corrected before any code was
  written. Several real bugs found via direct testing, not live: a premature-convergence design
  that stopped the loop after the bootstrap alone without ever consulting the planner (found via a
  manual smoke test); `ready_tasks()` requiring `PASSED` instead of any terminal state, which
  would have permanently stranded every repair task; stale task references after `mark()` (which
  returns a new object, not a mutation); a repair task's own outcome not propagating to its
  caller; the planner's explicit stop leaving the final status uncomputed; a held lock being
  silently ignored instead of respected; a dead-code `retry_refused` branch removed once its real
  enforcement point (`repair.py`, one layer up) was identified. `AGT-001`/`003`/`004`, `ORC-001`,
  `GAP-001`/`002`, `EFF-003` -> `IMPLEMENTED`; `AGT-002`, `MEM-001`, `EFF-001`/`002`, `ORC-002`/`003`,
  `VER-002`/`003` -> `PARTIAL` (unit-proven, live proof written -- `test_effect_ledger_live.py`,
  `test_supervisor_live.py` -- pending explicit confirmation per `GOVERNANCE.md` rule 10). Full
  suite: `ruff check .`, `ruff format --check .`, `mypy src` clean; `pytest -q` -> 396 passed (up
  from 335), 15 deselected. User directive.
- **2026-07-19 — GOVERNANCE.md rule 10 / decision 33 / `GOV-018` sharpened: explicit push
  confirmation must state what/why/where.** Direct user follow-up, prompted directly by the
  `test_effect_ledger_live.py`/`test_supervisor_live.py` live proofs above sitting in `PARTIAL`
  pending exactly this confirmation: "make sure nothing gets pushed to product repos unless
  explictly confirmed with what is going to be pushed, why and where explictly without any
  confusion." Decision 33 already required "the user's separate, explicit approval each time" for
  any real write to a managed remote; this spells out what that approval must actually contain so
  it can never be satisfied by a bare yes. Before any push (by an agent working the repo directly,
  or by any future `gated_effector` capability), the confirmation obtained from the user MUST name,
  unambiguously: **what** is being pushed (the exact commit/diff/content), **why**, and **where**
  (exact repository, branch, remote). Standing or implied consent from earlier in a session does
  not satisfy this — every push gets its own fresh what/why/where confirmation. No code change; a
  governance-text sharpening applied ahead of `EFF-001`/`002`'s live proofs actually reaching a
  real push decision. User directive.
- **2026-07-19 — Wave 5 live proofs run for real; `AGT-002`/`MEM-001`/`EFF-002`/`VER-003` →
  `IMPLEMENTED`.** User confirmed running both live test files (what/why/where stated per the
  rule above: disposable `refs/readme-agent-state/...` state on this project's own remote for
  `test_effect_ledger_live.py`; a real dry-run `supervise_repo()` call against the allow-listed
  `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` pilot plus its accepted durable state, left behind on
  this project's own remote per Wave 4's precedent, for `test_supervisor_live.py`; neither touches
  a target repo's actual remote). Both files, 4/4 tests, passed. **Real cost paid to a known,
  already-documented gap**: the first attempt hung silently for ~66 minutes with zero output before
  being diagnosed and killed — the exact `OPS-009` local push-credential prerequisite
  `test_state_git_backend_live.py`'s docstring already recorded from earlier the same day, not
  re-checked before running. Fixed with the documented one-time `GH_TOKEN`-into-`http.extraheader`
  procedure, unset again immediately after; `test_supervisor_live.py`'s docstring now carries the
  same `OPS-009` pointer so the next run doesn't repeat the cost. `plans/requirements.md` updated:
  `AGT-002`, `MEM-001`, `EFF-002`, `VER-003` → `IMPLEMENTED` (each row's own literal acceptance
  text is now live-proven, not just unit-proven). `EFF-001`, `ORC-002`, `ORC-003`, `VER-002` stay
  `PARTIAL` — the live run against a healthy `pdf/java` pilot never actually failed, so the repair/
  replan path itself remains proven only at unit level (monkeypatched), and `EFF-001`/`ORC-003`
  remain genuinely blocked on Wave 7 registering a real capability/specialist roles, not on any
  live-proof gap. Full suite unaffected (documentation-only + two docstring edits): `pytest -q` →
  396 passed, 15 deselected; `ruff check .`, `ruff format --check .`, `mypy src` clean. User
  directive ("execute the wave 5 e2e" → live-test confirmation).
- **2026-07-19 — Wave 6 rescoped (decision #37); durable-skip drift-blindness found and fixed ahead
  of it, sequenced standalone (decision #38).** Began as a correction to Wave 6's "product-agent
  integration: handoff schema" framing after direct user pushback ("we do not have access to [a
  product agent]... we will be watching for changes done to readme and consider that signal as
  upstream triggers... we have built our own product inventory and capability system, we will use it
  as well"). Exhaustive search confirmed "product agent" has always been an organizational label
  (decision #37) — Wave 6 is rewritten as "upstream-change watch and reconciliation." An earlier
  draft of the rescoped plan mistakenly dropped `langgraph` entirely while correcting this framing;
  caught by direct user follow-up ("I do not find a reference of langgraph, which I believed was
  scheduled for wave 6") — decision #27's addendum already commits `langgraph` to Wave 6-8, confirmed
  absent from `pyproject.toml`, restored into the design (routed through the Wave 5 supervisor per
  the user's explicit choice, matching decision #27's literal "supervisor calls into it" wording —
  design only, not yet built this pass).

  **Treated as a production problem, per direct user instruction, rather than accepted as a feature
  gap**: a deeper pass reading further into `orchestrator.py` than either of the two prior design
  passes found that `generate_repo()`'s durable-state fast path (`durable_skip`, Wave 4) required
  only `facts_hash` equality — and `facts_hash` deliberately excludes README content (decision #11).
  Verified directly against the existing regression test
  (`test_fresh_runner_with_no_local_marker_skips_using_durable_state_alone`, which only ever
  exercised *unchanged* content): on the actual production runner topology (`existing is None` is
  the normal case on a fresh GitHub Actions runner, not the exception, per `RUN-001`), this made the
  system **permanently blind to real upstream README edits once a repo's facts stabilized** — the
  precise problem Wave 6 exists to solve, defeated by existing, already-"proven" Wave 4 code. A
  second, structural finding: five independently-invented "did anything change" signals had
  accumulated across five waves with no shared primitive and no prior end-to-end trace of their
  interaction — exactly how this gap went unnoticed. A third, separately live bug was found in the
  same function: `_record_accepted_state()` silently dropped `domain_states`/`supervisor_state` on
  every write, already destructive today for any `org_repo` where both `supervise` and `run` are
  invoked (Wave 5's `supervisor_state` already gets written; `run`'s next call was already erasing
  it). Per direct user instruction, this fix was sequenced as its own standalone change, verified in
  isolation before Wave 6's remaining feature work (specialist registry, LangGraph, supervisor
  integration) is built on top of it — see decision #38 for the full root-cause analysis, rejected
  alternatives, and fix. **Implemented and tested this pass**: `readme/facts.py::
  compute_tracked_content_hash()` (new, canonical), `inspection/file_inventory.py::
  FileInventory.community_paths` (new), `RunStateV1.upstream_content_fingerprint_at_accept` (new,
  additive), `orchestrator.py`'s `_ensure_work_clone`/`generate_repo`/`_record_accepted_state` all
  updated. 12 new tests (408 passed, up from 396, 15 deselected unchanged) including the concrete
  regression proof (`test_fresh_runner_with_changed_upstream_content_does_not_blindly_skip`) and the
  state-preservation proof
  (`test_record_accepted_state_preserves_domain_states_and_supervisor_state`); `ruff check .`,
  `ruff format --check .`, `mypy src` all clean. Live re-proof against the real `pdf/java` pilot
  remains pending explicit user confirmation (`GOVERNANCE.md` rule 10). Wave 6's remaining feature
  work (`get_product_facts`, the reconciliation classifier, the specialist registry, `langgraph`,
  `supervisor/loop.py`'s registry-driven second convergence tier, the `readme-agent-supervise.yml`
  workflow) is designed but not yet implemented this pass. User directive throughout ("treat this as
  a production problem... reassess the system carefully and identify the underlying causes").
- **2026-07-19 — Wave 6's remaining feature work built (decision #39): first real LangGraph
  specialist, routed through the Wave 5 supervisor.** Executes decision #27's Wave 6-8 commitment for
  the first time (`langgraph>=1.0` added to `pyproject.toml`, confirmed previously absent). New:
  `capabilities/get_product_facts.py` (combines the product inventory + live repository profiling,
  both sources mandatory per user direction), `readme/reconciliation.py` (the drift classifier,
  promoted from the investigation prototype -- `FIRST_OBSERVATION`/`NO_CHANGE`/`UPSTREAM_CHANGED`/
  `OWNED_SPAN_LOST`/`MIXED_CHANGE`), `capabilities/classify_upstream_change.py` (the first capability
  scoped to a real domain, `README_RECONCILIATION`), `specialists/readme_reconciliation.py` (the
  two-node `classify`->`record` `StateGraph`, state is `DomainStateV1` directly), `specialists/
  registry.py` (mirrors `capabilities/registry.py`'s dispatch-table pattern -- `all_domains()`/
  `run_domain()`, so Wave 7 adding a specialist is a registration, never a `supervisor/loop.py` edit).
  `supervisor/loop.py::supervise_repo()` gains the registry-driven second convergence tier
  (`CONVERGED_NO_TRACKED_CHANGE`), run before the supervisor's own lock is acquired (each specialist's
  `record` step acquires that same lock internally -- holding it first would deadlock, caught during
  design, not live). New `.github/workflows/readme-agent-supervise.yml` (`workflow_dispatch` only).

  **Two real bugs found and fixed via direct testing, not live, before either could surface as a
  false negative or a false CI failure**: (1) a test written to prove `OWNED_SPAN_LOST` detection
  initially failed with the wrong diagnosis (`UPSTREAM_CHANGED` instead of `NO_CHANGE` for an
  unrelated fixture, traced to a non-hex `facts_hash` value the real marker regex correctly rejects)
  -- caught and fixed before concluding anything about the classifier itself; the real, underlying
  need this surfaced was genuine: `remove_span()` is a no-op once a span is already absent, so
  stripped-hash comparison alone cannot distinguish "never had a span" from "span was just removed" --
  fixed by adding `DomainStateV1.owned_span_present_at_accept: bool = False` (additive). (2)
  `commands.py::cmd_supervise`'s exit-code mapping only recognized the two pre-existing converged
  statuses -- the new `CONVERGED_NO_TRACKED_CHANGE` would have exited `1` (a false CI failure for a
  fully successful, converged run), caught by writing `TestSuperviseCommand::
  test_exit_code_matches_status` before this could ship silently broken.

  29 new tests across `test_reconciliation.py` (new), `test_specialists.py` (new), and new cases in
  `test_capabilities.py`, `test_capability_dispatcher.py`, `test_state_schema.py`,
  `test_supervisor_loop.py`, `test_cli.py` -- `pytest -q` → 437 passed (up from 408), 15 deselected
  unchanged; `ruff check .`, `ruff format --check .`, `mypy src` all clean. `CAP-006`/`MEM-004` stay
  `PARTIAL` per `GOV-018` -- unit-proven against a fixture planner and a real local git repo, not yet
  against a real gateway/real pilot. User directive ("execute phase b, make wave 6 execute e2e...
  continue, however do not push to anything to product repos").
- **2026-07-19 — Wave 6 live-proven for real: `supervise`/`readme-agent-supervise.yml` against
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`, no push to any product repo.** Same-day follow-up to
  decision #39's unit-proven build, per the user's explicit go-ahead. First attempt
  (`readme-agent supervise --repo aspose-pdf-foss/Aspose.PDF-FOSS-for-Java --durable-state`) converged
  immediately via the pre-existing coarse tier (real prior state from Wave 5's own live proof) --
  correct, but exercised none of this pass's new code. Second attempt, against
  `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` (confirmed to have no prior `supervisor_state`),
  hung silently with zero output -- the exact, already-documented `OPS-009` git-push-credential gap,
  recognized from its signature within minutes this time (a near-zero-CPU `git` process, not a
  network stall) rather than the ~66-minute cold diagnosis Wave 5 needed. Applied the documented
  one-time fix (`GH_TOKEN` -> `http.https://github.com/.extraheader`, removed immediately after);
  retried successfully. Real gateway planner dispatched `inspect_repository` -> `detect_readme_gaps`
  -> `get_product_facts` and correctly stopped, having identified all three real README gaps
  (`products_org_link`, `products_com_link`, `relationship_explained`) against the real policy facts.
  The `readme_reconciliation` specialist ran first, as designed (before the planner loop, not as a
  planner-chosen tool call) -- confirmed by reading the durable record back afterward:
  `domain_states["readme_reconciliation"]` (`accepted_status="FIRST_OBSERVATION"`) and
  `supervisor_state` (`last_status="CONVERGED_NO_CHANGE"`) both present in the *same* record, proving
  decision #38's multi-producer coexistence fix under a real second producer, not a fake backend. An
  immediate rerun correctly short-circuited via the coarse tier, zero planning calls, no push needed.
  `act workflow_dispatch -W .github/workflows/readme-agent-supervise.yml --input
  repo_key=aspose-cells-foss/Aspose.Cells-FOSS-for-Java` then reproduced the same outcome inside a
  real container end to end -- `pip install -e .` (including `langgraph` for the first time),
  `Job succeeded`. One minor, pre-existing (not introduced this pass) cosmetic gap noted, not fixed:
  the coarse-tier short-circuit path returns before `write_evidence_bundle` ever runs, so
  `upload-artifact` correctly finds nothing to upload on a converged-with-no-work run -- a `PLANNED`,
  non-blocking backlog candidate if it ever proves confusing in real CI history, not logged as a
  numbered row here since it predates this pass's own scope. **Nothing was pushed to
  `aspose-pdf-foss` or `aspose-cells-foss` at any point** -- only to this project's own
  `refs/readme-agent-state/...` ref, exactly as instructed. `CAP-006`/`FACT-001`/`MEM-004`'s
  requirements.md rows updated with this live evidence (still `PARTIAL`: the domain-*denial* path and
  genuine two-domain collision both still need Wave 7's second domain/specialist to prove live). User
  directive ("execute phase b, make wave 6 execute e2e... do not push to anything to product repos").
- **2026-07-20 — Full-registry Wave 6 hardening pass: 25/25 clean, zero bugs found; third enabled
  pilot (`3d/java`) live-proven.** User directive to test Wave 6's new code against every repo in
  `data/products.json`, verify results, and tweak the process where needed — mirroring the discipline
  Wave 3 already applied to the ecosystem parsers. New `tools/survey_full_registry_wave6_
  reconciliation.py` (structurally mirrors Wave 3's own survey script, decision #30/`GOV-015` reuse,
  not reinvented), read-only `clone_baseline()` against all 25 real entries regardless of mode
  (decision 24/`PIL-011`), running `file_inventory.scan()`, `compute_tracked_content_hash()`,
  `readme.reconciliation.classify()`, and `profile.detector.build_profile()` against each. Result:
  25/25 surveyed without a crash, every fingerprint a valid 64-char SHA-256 digest, every ecosystem
  detection matched its declared platform, community files correctly found in exactly the 3 repos
  that have them. One reported `has_license_file=False`
  (`aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`) verified directly against the real clone as a
  genuine gap in that repo's own root, not a detection miss — decision #5's soft-degrade already
  covers this correctly. **No code change was needed as a result of this survey** — stated plainly,
  not rounded down to make a more dramatic story. Separately, completed live `supervise
  --durable-state` coverage of all 3 enabled pilots by running the one not yet exercised with Wave 6
  code, `aspose-3d-foss/Aspose.3D-FOSS-for-Java`: the real gateway planner dispatched 5 of 6
  registered capabilities in one run (`inspect_repository`, `profile_repository`,
  `get_product_facts`, `detect_readme_gaps`, `check_install_path`) and converged correctly; the
  `readme_reconciliation` specialist ran first as designed, recording a real `domain_states` entry
  alongside `supervisor_state` in the same durable record — decision #38's multi-producer
  coexistence fix now proven against all 3 enabled pilots, not one. `OPS-009`'s credential workaround
  applied and removed correctly, recognized within minutes this time. Nothing pushed to any product
  repo. Honest limits restated, not glossed over: `get_product_facts`'s policy-dependent output is
  still only proven for 3 repos (the other 22 have no `policy_profile`); the classifier's
  non-`FIRST_OBSERVATION` branches remain proven live for only one repo (this survey exercises only
  `FIRST_OBSERVATION`, by construction — no durable state is ever supplied); `aspose-page-foss`'s
  large-repo profiling latency (~258s this run) is unchanged, already-documented, still open; the
  domain-denial and multi-domain-collision paths remain unit-only, still gated on Wave 7. Full detail:
  `plans/investigations/full-registry-wave6-survey.md`. User directive.
