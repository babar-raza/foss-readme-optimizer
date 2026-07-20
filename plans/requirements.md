# foss-readme-optimizer — Requirements Specification

Governed by [`plans/GOVERNANCE.md`](GOVERNANCE.md).
Execution sequencing, ledger decisions, implementation status, and historical context are maintained
in the companion [`plans/master.md`](master.md). Nothing here is locked at this stage: every
requirement and decision is a current working position, revisable through the governance procedure.

## 1. Purpose and authority

This document is the complete normative requirements register for `foss-readme-optimizer`.
It defines **what the system must do, must not do, and how each requirement is accepted**.

The document set has four distinct roles:

1. **`plans/requirements.md` — WHAT:** authoritative list of business, functional, safety,
   integration, quality, and governance requirements.
2. **`plans/master.md` — WHY/WHEN:** mission, decision ledger, architecture direction, phases,
   rollout sequence, current status, and changelog.
3. **Implementation documents — HOW:** `docs/architecture.md`, `docs/safety-model.md`,
   `docs/policy-authoring.md`, `docs/presentation-standard.md`, `docs/github-surface-control.md`,
   and future surface-specific design documents.
4. **Code, tests, and evidence — PROOF:** implementation and objective evidence that a requirement
   has been met.

When these documents disagree, the conflict must be resolved explicitly. No requirement may be
silently inferred from implementation, a prompt, a README template, or an earlier discussion.

## 2. Requirement language

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

Requirement statuses:

| Status | Meaning |
|---|---|
| `IMPLEMENTED` | Built and supported by recorded tests/evidence. |
| `PARTIAL` | Some required behavior exists, but the full acceptance criteria are not yet met. |
| `PLANNED` | Accepted requirement scheduled in the master plan but not yet implemented. |
| `RESEARCH-GATED` | Requirement is accepted, but an identified research deliverable must settle implementation details first. |
| `GOVERNANCE` | Always-active process or document-control requirement. |
| `DEPRECATED` | Retained for traceability but no longer applicable; must identify its replacement. |
| `BACKLOG` | A non-blocking issue, gap, or improvement observed during work; logged for future triage, not yet an accepted requirement. Open until triaged to `PLANNED` (accepted) or `DEPRECATED` (rejected, with reason) — never silently deleted (`GOV-003`). |

Priorities:

| Priority | Meaning |
|---|---|
| `P0` | Safety, correctness, or authority boundary. No release may violate it. |
| `P1` | Required for the product-first pilot and production use. |
| `P2` | Required for scale, durability, or operating quality. |
| `P3` | Useful improvement that does not block the first accepted rollout. |

## 3. Requirements governance

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| GOV-001 | P0 | GOVERNANCE | Every normative requirement MUST have a permanent ID in this document. | Requirement-ID uniqueness check passes. | Decision 25 |
| GOV-002 | P0 | GOVERNANCE | Requirement IDs MUST NOT be renumbered or reused. Changed requirements retain their ID and revision history. | Diff review confirms stable IDs. | Decision 25 |
| GOV-003 | P0 | GOVERNANCE | Removed requirements MUST be marked `DEPRECATED` or `SUPERSEDED`; they MUST NOT be silently deleted. | Changelog identifies replacement or reason. | Decision 25 |
| GOV-004 | P0 | GOVERNANCE | Any master-plan decision, phase, architecture change, or accepted stakeholder instruction that changes system obligations MUST update this document in the same commit or change set. | Cross-document traceability check; no orphan decision. | Decision 25 |
| GOV-005 | P0 | GOVERNANCE | Any requirement change that affects sequencing, architecture, ownership, or rollout MUST update `plans/master.md` in the same commit or change set. | Cross-document traceability check; no orphan requirement. | Decision 25 |
| GOV-006 | P1 | GOVERNANCE | Every requirement MUST identify status, priority, acceptance evidence, and master-plan traceability. | Requirements linter passes. | Decision 25 |
| GOV-007 | P1 | GOVERNANCE | A requirement MUST NOT be marked `IMPLEMENTED` until objective tests or evidence satisfy its acceptance criteria. | Evidence reference exists and is reviewable. | Decisions 16, 25 |
| GOV-008 | P1 | GOVERNANCE | Research findings MAY refine implementation details but MUST NOT silently weaken an accepted safety, ownership, or product-first requirement — any such change goes through the governance procedure with a ledger edit and Changelog line. | Decision review records any allowed change. | Decisions 18–24 |
| GOV-009 | P1 | PLANNED | CI MUST validate unique IDs, required fields, valid statuses, valid phase/decision references, and bidirectional master-plan traceability. | `validate_requirements.py` or equivalent passes locally and in CI. | Phase 20 |
| GOV-010 | P1 | GOVERNANCE | The requirements specification MUST be reviewed whenever a phase is closed, a pilot is accepted, or a stakeholder changes scope. | Closeout checklist includes requirements review. | Decision 25 |
| GOV-011 | P1 | GOVERNANCE | The master plan MUST link to this document, and this document MUST link back to the master plan using repository-relative links. | Link validation passes. | Decision 25 |
| GOV-012 | P2 | PLANNED | Generated evidence SHOULD record the requirement IDs exercised by each run or validation report. | Evidence manifest contains `requirements` array. | Phases 21–26 |
| GOV-013 | P1 | GOVERNANCE | The `foss-readme-optimizer` project itself MUST NOT add a `LICENSE` file until a separate ledger decision approves one; its README MUST continue to state the current licensing status accurately. | Repository file audit and master-plan decision review. | Decision 3 |
| GOV-014 | P1 | GOVERNANCE | An agent (human or AI) that discovers an issue, gap, or improvement opportunity that does NOT block the task it is currently doing MUST log it as a new requirement row with status `BACKLOG` in the section matching its topic, rather than fixing it as unrequested scope creep or silently dropping it. An issue that DOES block the current task's correctness, safety, or acceptance MUST be fixed first, before the task is considered done. | New `BACKLOG` rows exist for non-blocking findings; no session narrative or commit message reports a dropped or silently-fixed non-blocking issue without a corresponding row. | Decision 29 |
| GOV-015 | P1 | GOVERNANCE | Before building any new functionality, an agent MUST actively research, evaluate, and select an existing library, stdlib facility, framework, or a real reference implementation from a sibling proven system that already solves the problem, and build on it rather than hand-rolling bespoke logic. Hand-rolling is a discouraged default, not an absolute ban — it is allowed only as a special circumstance, carrying an explicit, reasoned Decision Ledger entry citing the proven option considered and why it was not used. | Decision Ledger entry cites the proven option considered and the reason for the choice made; no new functionality lands with hand-rolled logic and no corresponding justification entry. | Decision 30; GOVERNANCE.md rule 8 |
| GOV-016 | P2 | IMPLEMENTED | `src/readme_agent/llm/prompts.py`'s prompt content for the `relationship_explained` job is still an inline string literal, grandfathered against the `prompts/`-only placement rule (GOVERNANCE.md placement rule 9) pending its "next substantive touch" (retrofit-on-touch). | Migrated to `prompts/relationship_explained/{system,user}.txt`, loaded by `llm/prompts.py::build_prompt()`; `prompt_content_hash()` joins `RepositoryFacts.prompt_content_hash` (determinism contract, rule 3). `tests/unit/test_llm_prompts.py`, `tests/unit/test_prompt_hash_coupling.py`, `tests/unit/test_readme_facts.py`. `GENERATION_SCHEMA_VERSION` bumped `3`→`4`. | GOVERNANCE.md placement rule 9; found during 2026-07-19 agentic-usage assessment |
| GOV-017 | P1 | GOVERNANCE | An agent (human or AI) working in this repository MUST investigate the current content and recent history of a file, Decision Ledger entry, requirement row, evidence artifact, or git state before overwriting, replacing, deleting, or discarding it, and MUST preserve, migrate, or pause for user input when that investigation shows the existing content matters — never silently clobber it. | Session narrative or commit message shows the prior state was checked (content read, `git log`/`git blame` consulted) before a destructive edit landed; no destructive edit lands without evidence of that check. | Decision 31; GOVERNANCE.md rule 9 |
| GOV-018 | P1 | GOVERNANCE | A requirement MUST NOT be marked `IMPLEMENTED`, and a Build Checklist line MUST NOT be checked off, on unit-test or mocked-fixture evidence alone — it MUST also be demonstrated end-to-end against real, production-like conditions matched to what it claims (the real registry repos, a live LLM/gateway call, a real CI reproduction), exercised read-only/dry-run under the existing push-blocking and allow-list safety properties. At this stage, proving a requirement this way MUST NOT itself commit or push anything to the actual product repos. Nothing (no requirement's proof, no capability, no agent — human or AI) MAY commit or push to a managed remote without the user's separate, explicit, per-instance approval, and that approval MUST be preceded by an unambiguous statement of exactly **what** will be pushed (the specific commit/diff/content), **why** (the reason/purpose), and **where** (the exact repository, branch, and remote) — general, implied, or standing consent does not satisfy this; each of the three elements MUST be named with no room for confusion before the push happens. | Changelog/session narrative or an evidence artifact shows a live/real-target run — not only `pytest -q` — before the status change lands, with no commit/push to a managed remote absent a preceding, explicit statement of what/why/where and the user's approval of that exact statement. | Decision 33; GOVERNANCE.md rule 10; sharpens GOV-007 |
| GOV-019 | P2 | BACKLOG | Decision 32 (durable runner-state backend, one git ref per `org_repo`) has no corresponding row in the §21 Decision-ledger coverage table — found while adding decision 33's coverage row, out of scope for that task. | A coverage row for decision 32 exists in §21, citing the `MEM-*`/`RUN-*` requirements it maps to. | Decision 32 |

## 4. Business and product outcomes

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| BIZ-001 | P0 | GOVERNANCE | Repository credibility and developer usefulness MUST take precedence over promotional exposure. | Human review confirms the opening is product-first; no promotional banner precedes product explanation. Now also automatically enforced (Phase 21c): `validation/rules/product_first_opening.py`, `commercial_mention_discipline.py`, both ERROR severity. | Decisions 9, 17, 20 |
| BIZ-002 | P1 | PARTIAL | A visitor SHOULD be able to understand what the product does, who it is for, what it supports, how to start, and whether it is maintained without first following an Aspose promotional link. | Phase-21 presentation report passes the product-understanding criteria. `readme/presentation_report.py` delivers the product/audience/install/example/heading criteria (Phase 21a); "whether it is maintained" (maintenance signals) is out of Phase 21 scope (Phase 23). **Confirmed live, 2026-07-18, via `inspect --check-install` against all three real pilots**: all three pass `explains_product_in_opening`/`states_audience_or_ecosystem`/`has_runnable_example`/`heading_levels_consistent`; all three fail `install_path_resolved` (see RDM-007). Stays `PARTIAL` because maintenance signals remain unaddressed by design, not because the built criteria are unproven. | Phase 21a |
| BIZ-003 | P1 | GOVERNANCE | Links to Aspose.org, Aspose.com, documentation, or commercial products MUST appear only where they provide relevant context or a useful next step. | Link-purpose review and destination validation pass. | Decisions 9, 17, 20 |
| BIZ-004 | P1 | RESEARCH-GATED | The system SHOULD support a credible path to at least 10 weekly visitors from GitHub to Aspose.org, provided the target does not conflict with product trust or quality. | Phase-20 feasibility study and post-rollout measurement. | Decision 20, Phase 20 |
| BIZ-005 | P1 | GOVERNANCE | Raw click volume MUST NOT be treated as success if links are misleading, irrelevant, intrusive, or harmful to README quality. | Metric report includes quality and destination-relevance checks. | Decision 20 |
| BIZ-006 | P1 | PLANNED | Each repository MUST be tailored to its own product, audience, ecosystem, maturity, and capabilities rather than receiving a common prose template. | Independent pilot review confirms materially different, product-appropriate outcomes. | Decisions 18, 24; Phase 26 |
| BIZ-007 | P1 | PLANNED | The system MUST improve presentation without reducing technical accuracy, completeness, maintainability, or usefulness. | Before/after comparison shows no verified fact was lost or broadened. | Decisions 18, 22 |
| BIZ-008 | P2 | PLANNED | The system SHOULD make the relationship between the FOSS product, Aspose.org, and the related commercial product understandable without making the repository feel like an advertisement. | Human and deterministic review of relationship language. | Decisions 7–9, 17 |

## 5. Scope, control, and ownership boundaries

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| OWN-001 | P0 | GOVERNANCE | Every visible GitHub surface MUST be assigned exactly one control class before the system proposes an action. | Surface-control matrix contains one classification per surface. | Decision 19 |
| OWN-002 | P0 | GOVERNANCE | Supported control classes MUST be: repository-file managed, GitHub API/settings managed, manual UI managed, product-agent owned, or GitHub generated. | Schema and documentation enumerate only these classes unless a ledger decision adds another. | Decision 19 |
| OWN-003 | P0 | PLANNED | The system MUST NOT expose a renderer or remote write path for a GitHub-generated surface. | Negative tests prove no write functions for generated surfaces. | Decision 19; Phase 22 |
| OWN-004 | P0 | PLANNED | The system MUST NOT publish, replace, or edit releases, packages, package metadata, or release-specific technical facts owned by product agents. | Audit-only report; no publication credentials or write call path. | Decisions 18, 19 |
| OWN-005 | P0 | GOVERNANCE | Contributors, languages, stars, forks, watchers, activity, counts, tabs, and GitHub page layout MUST be treated as GitHub-generated or GitHub-controlled presentation, not directly editable metadata. | Control-boundary tests and documentation pass. | Decision 19 |
| OWN-006 | P0 | PLANNED | Repository description, homepage, topics, and approved feature settings MAY be proposed only through a dry-run-first, explicitly gated settings workflow. | Dry-run emits proposal/evidence; no remote write without apply gate. | Decision 19; Phase 22 |
| OWN-007 | P0 | PLANNED | Social-preview upload MUST be treated as manual UI managed unless official, current GitHub documentation confirms an authorized write API. | Phase-20 control research and Phase-24 delivery path. | Decisions 19, 23 |
| OWN-008 | P0 | GOVERNANCE | README content, embedded images, community files, and approved templates are repository-file managed and MUST use the push-blocked work-clone workflow until an explicit publication design is separately approved. | Push-block verification and change-boundary evidence. | Decisions 9, 19 |
| OWN-009 | P0 | GOVERNANCE | Product agents remain authoritative for product capabilities, supported formats, installation/package coordinates, APIs, examples, release changes, and package publication. | Product-facts contract identifies source/owner for each field. | Decisions 18, 22 |
| OWN-010 | P0 | PLANNED | Ambiguous or conflicting product facts MUST be returned to the owning product agent as a finding; the central agent MUST NOT guess. | Proposal status is blocked/pending-facts with evidence. | Decisions 18, 22 |
| OWN-011 | P1 | PLANNED | The central agent MAY improve organization, wording, navigation, and presentation only where verified facts and ownership rules permit. | Diff provenance map and change-boundary review. **Multi-specialist risk noted, not designed** (2026-07-19, specialist-domain-isolation pass): `markers.py`'s single-owned-span pattern (`SPAN_NAMES = ("resources",)`) has no generalized concept of "specialist X owns file-region/surface Y" — once Wave 7 introduces multiple specialists with plausibly-overlapping outputs (e.g. a README specialist and a metadata specialist both touching `README.md`), a cross-specialist surface collision is possible and currently undetected by anything except the existing whole-file validators. Deliberately not designed here: Wave 7's real specialist-to-surface mapping doesn't exist yet, and guessing at the mechanism now risks repeating decision #32's first-draft granularity mistake. | Decision 18; Phase 21e (deferred, design-only — needs `change_boundary`'s byte-identical-outside-spans contract to evolve first) |
| OWN-012 | P1 | PLANNED | GitHub-generated surfaces MAY be audited for anomalies, but the audit MUST identify the underlying repository history, files, or GitHub behavior rather than proposing direct field edits. | Audit report names cause and allowed remediation. | Decision 19; Phase 22 |
| OWN-013 | P1 | PLANNED | Releases and package links MAY be checked for availability, naming, linkage, and consistency, but remediation MUST be handed to the product owner. | Product-agent handoff artifact. | Decision 19; Phase 22 |
| OWN-014 | P1 | PLANNED | The system MUST record the required permission and rollback method for every API/settings-managed action. | `github-surface-control.md` and proposal evidence include permission/rollback. | Phase 20, 22 |
| OWN-015 | P1 | PLANNED | The system MUST identify whether an action is local-only, proposal-only, manually applied, or remotely applied. | Every evidence manifest has an action mode. | Phases 21–24 |

## 6. Product-facts and provenance requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| FACT-001 | P0 | PARTIAL | Before changing product-facing content, the system MUST obtain a provenance-bearing product-facts record from repository inspection, an owning product agent, or both. | `capabilities/get_product_facts.py` (2026-07-19, decision #37/#39) combines the product inventory (`data/products.json`+`config/policies/*.yml`) with live repository profiling, both sources every call, with a `source` dict recording provenance per field — `tests/unit/test_capabilities.py::TestGetProductFactsCapability`. **Live-proven 2026-07-19**: the real gateway planner chose and successfully dispatched `get_product_facts` against `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` during a real `supervise --durable-state` run, correctly identifying the README's missing `products_org_link`/`products_com_link`/`relationship_explained` against the real policy facts. `PARTIAL` not `IMPLEMENTED`: not yet an enforced precondition inside `generate_repo()`/the specialist layer, and covers only today's narrow field set (identity, license, links, talking points) — the full decision #22 list (audience, verified example, release info, limitations) stays unbuilt, `DOC-006` still `RESEARCH-GATED`. | Decision 22/37; Phase 20/25; Sprint Wave 6 |
| FACT-002 | P0 | PLANNED | The minimum product-facts record MUST include product identity, audience, supported capabilities, supported formats, installation/package coordinates, a minimal verified example, documentation links, current release information, and known limitations. | Schema validation passes. | Decision 22 |
| FACT-003 | P0 | PLANNED | Every technical claim introduced or materially changed by the central agent MUST map to one or more product-fact IDs or repository evidence locations. | Claim-to-source map has no unmapped claim. | Decisions 18, 22 |
| FACT-004 | P0 | PLANNED | Missing required facts MUST produce a blocking finding or product-agent handoff, not a placeholder, broad marketing statement, or invented capability. | Negative tests and pilot evidence. | Decision 22 |
| FACT-005 | P0 | PLANNED | Conflicting sources MUST be recorded and resolved by an authoritative owner before affected content is changed. | Conflict record and resolution evidence. | Decisions 18, 22 |
| FACT-006 | P1 | PLANNED | Product facts MUST include source type, source location, source revision or retrieval time, owning agent/team, and confidence or verification state. | Schema fields present and validated. | Decision 22; Phase 25 |
| FACT-007 | P1 | PLANNED | Examples presented as working examples MUST be executable or otherwise verified against the referenced package/version. | Example-validation evidence. | Phase 21 |
| FACT-008 | P1 | PLANNED | Release-specific facts MUST be refreshed through the product-agent handoff and MUST NOT be inferred from stale README prose. | Release source and timestamp recorded. | Decisions 18, 22 |
| FACT-009 | P1 | PLANNED | Known limitations MUST be preserved where relevant and MUST NOT be removed merely to make the presentation more attractive. | Before/after fact comparison. | Decisions 18, 22 |
| FACT-010 | P2 | PLANNED | Product-facts changes SHOULD trigger only the presentation sections that depend on the changed facts. | Dependency map and surgical diff evidence. | Decision 21; Phase 25 |

## 7. README presentation requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| RDM-001 | P0 | IMPLEMENTED | The retired promotional `callout` span immediately after the H1 MUST be removed from renderer behavior, markers, validators, fixtures, and pilot work clones. | No callout marker or generated banner remains; tests pass. | Decision 9; Phase 21b. `upsert_span` rejects `"callout"` (`readme/markers.py`); orchestrator migrates any pre-existing callout span out of a work clone unconditionally, even on the skip path (`tests/unit/test_orchestrator.py::TestCalloutMigration`); `readme/renderer.py` has no callout render target (`tests/unit/test_readme_renderer.py`); `tests/unit/test_readme_markers.py::TestCalloutRetired`. **Confirmed live, 2026-07-18, against all three real registry work clones**: `pdf/java` had a genuine pre-Phase-21 legacy callout span (uncommitted, from before this session), migrated away cleanly by this exact code path — zero `readme-agent:callout` markers remain in any of the three work clones after re-running. |
| RDM-002 | P0 | IMPLEMENTED | The README opening MUST explain the product before presenting promotional or commercial links. | Section-order validator and human review pass. | Decisions 9, 17; Phase 21c. `validation/rules/product_first_opening.py` (ERROR severity), `tests/unit/test_validation_rules.py::TestProductFirstOpening`. Human/pilot review not yet performed — see Build Checklist. |
| RDM-003 | P0 | PLANNED | The central agent MUST NOT replace a complete README with a generic full-document template. | Change-boundary and similarity checks pass. | Decisions 9, 18 |
| RDM-004 | P0 | PLANNED | README changes MUST be surgical, fact-backed, and limited to identified presentation gaps. | Gap-to-diff map covers every change. | Decisions 9, 18, 22 |
| RDM-005 | P1 | IMPLEMENTED | The README SHOULD identify the intended developer or use case in clear language. | Presentation report criterion passes. `states_audience_or_ecosystem` in `readme/presentation_report.py`, `tests/unit/test_presentation_report.py::TestDetectPresentation::test_states_ecosystem_when_platform_keyword_present`. Diagnostic only (P1 "SHOULD"), not a validator gate. | Phase 21a |
| RDM-006 | P1 | PARTIAL | The README SHOULD explain the primary problem solved by the product. | Presentation report criterion passes. `explains_product_in_opening`/`product_explanation_offset` checks for a concrete-phrase product description, which is a proxy for "explains the product," not specifically "explains the problem it solves" — the two overlap but aren't identical; no dedicated problem-statement criterion exists yet. | Phase 21a |
| RDM-007 | P1 | PARTIAL | The README MUST provide a usable installation or acquisition path appropriate to the ecosystem. | Install command/steps verified against facts. `install_path_resolved` in `readme/presentation_report.py` via `ecosystems/resolver.py` (Phase 21d) checks the coordinate resolves against the real registry, opt-in (`--check-install`) — but this is diagnostic only, not a validator gate, and only Maven is implemented (Python/`.NET`/etc. resolvers don't exist yet). **Confirmed live, 2026-07-18, against `--check-install`**: all three enabled pilots' Maven coordinates return zero results on Maven Central (`org.aspose:aspose-cells-foss`, `-3d-foss`, `-pdf-foss`) — see the corrected, broadened Reference Data finding in `master.md`. The resolver correctly detects this; it cannot fix a registry-publication gap, which is why this stays `PARTIAL`, not `IMPLEMENTED`. | Phase 21a/21d; FACT-002 |
| RDM-008 | P1 | PLANNED | The README MUST provide a minimal verified first-use example when the product and ecosystem reasonably support one. | Example executes or is independently verified. `has_runnable_example` (Phase 21a) only checks fenced-code-block *presence* (≥2 blocks), not that an example executes or is independently verified against facts — that stronger acceptance bar is not yet built. | Phase 21; FACT-007 |
| RDM-009 | P1 | PLANNED | Supported capabilities and formats MUST be described accurately and at a useful level of detail without unsupported breadth. | Claim-to-source mapping passes. | Decisions 18, 22 |
| RDM-010 | P1 | IMPLEMENTED | Critical developer information MUST not be buried beneath promotional, historical, or secondary material. | Information-order review passes. `validation/rules/commercial_mention_discipline.py` (Phase 21c, ERROR) enforces this mechanically: fails on list-item-formatted commercial-link density or a mention outside the two evidenced acceptable positions. | Decision 17; Phase 21c |
| RDM-011 | P1 | PLANNED | Links MUST have a clear purpose, descriptive label, valid destination, and appropriate placement. | Link validator and purpose review pass. | Decisions 9, 17 |
| RDM-012 | P1 | PLANNED | Aspose.org and Aspose.com links MUST not be inserted merely to satisfy a quota or appear in the first screen without product-context justification. | No quota rule; placement review passes. | Decisions 9, 17, 20 |
| RDM-013 | P1 | IMPLEMENTED | The existing `resources` owned span MAY add genuinely missing license and relationship links near the end of the README. | Existing Phase 0–15 tests and pilot evidence. | Decisions 7–9 |
| RDM-014 | P1 | IMPLEMENTED | Presence of the `resources` span MUST NOT be treated as proof that the README is professionally complete. | Presentation report evaluates full README independently. `readme/presentation_report.py`'s `detect_presentation` runs against the whole README text unconditionally, independent of `resources`-span presence (Phase 21a); `commercial_mention_discipline`/`product_first_opening` (Phase 21c) likewise gate the whole text, which is exactly what surfaces `3d/java`'s existing-but-noncompliant resources section as a new finding. | Decision 9; Phase 21a/21c |
| RDM-015 | P1 | PLANNED | The README SHOULD provide clear navigation for long documents without forcing identical section names or order across repositories. | Repository-specific presentation review. `heading_levels_consistent` (Phase 21a) checks structural consistency only, not navigability. | Decisions 18, 24 |
| RDM-016 | P1 | PLANNED | Contribution, support, license, security, and maintenance information MUST be linked or presented where relevant and available. | Community-file and README cross-link audit. | Phases 21, 23 |
| RDM-017 | P1 | PLANNED | A product illustration MAY be embedded only when it improves understanding of the product or workflow. Decorative imagery alone MUST NOT satisfy a presentation requirement. | Visual usefulness review and alt-text check. | Decision 23; Phase 24 |
| RDM-018 | P1 | PLANNED | Product-specific terminology, package names, APIs, commands, and examples MUST be preserved unless authoritative facts require correction. | Before/after technical-token comparison and provenance. | Decisions 18, 22 |
| RDM-019 | P2 | IMPLEMENTED | The product-presentation standard MUST define what a visitor should understand in the first screen, first minute, and first successful installation attempt. | `docs/presentation-standard.md` §"First screen, first minute, first successful install". | Phase 20 |
| RDM-020 | P2 | PLANNED | The system SHOULD detect generic, repetitive, or mechanically inserted prose that weakens repository credibility. | Drift/quality rule with fixtures. | Decision 21; Phase 25 |
| RDM-021 | P2 | PLANNED | Formatting changes MUST not create broken anchors, malformed Markdown, inaccessible images, or invalid code fences. | Markdown, link, anchor, and code-fence validation passes. | Phases 17, 21, 24 |
| RDM-022 | P2 | PLANNED | README presentation proposals SHOULD explain why each change helps an external developer. | Evidence contains per-change rationale. | Phase 21 |
| RDM-023 | P2 | IMPLEMENTED | Secondary Aspose documentation, reference, release, blog, KB, and forum links MAY be tracked for useful coverage but MUST remain best-effort rather than hard compliance gates. | Policy and validator review. | Registry & Policy Config |

## 8. Repository settings and supporting surfaces

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| SURF-001 | P1 | PLANNED | Repository descriptions MUST be concise, product-specific, fact-backed, and understandable without promotional filler. | Description validator and provenance map pass. | Decisions 8, 19; Phase 22 |
| SURF-002 | P1 | PLANNED | Homepage/website proposals MUST use the most useful canonical destination defined by policy and product context. | URL matches policy and resolves. | Decision 19; Phase 22 |
| SURF-003 | P1 | PLANNED | Topic proposals MUST be relevant to the product, language, formats, and ecosystem and MUST reject keyword stuffing. | Topic policy validator passes. | Decision 19; Phase 22 |
| SURF-004 | P0 | PLANNED | No repository description, homepage, topic, or feature setting may be remotely changed without an explicit authorized apply action. | Dry-run proof and apply-gate negative tests. | Decision 19; Phase 22 |
| SURF-005 | P1 | PLANNED | Settings proposals MUST include before/after values, rationale, permissions, rollback instructions, and evidence. | Proposal schema passes. | Decision 19; Phase 22 |
| SURF-006 | P1 | PLANNED | Community-file requirements MUST be policy-driven per repository; the system MUST NOT create irrelevant files merely to imitate another project. | Policy and pilot review. | Decisions 18, 24; Phase 23 |
| SURF-007 | P1 | PLANNED | Supported community files include LICENSE presence, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORT, issue templates, and PR templates where policy requires them. | Community-profile and file audit. | Phase 23 |
| SURF-008 | P0 | GOVERNANCE | The system MUST distinguish between controlling a community file and controlling where GitHub displays it. | Documentation and tests use correct language. | Decision 19 |
| SURF-009 | P1 | PLANNED | Community-file changes MUST use the same push-blocked, evidence-backed, change-boundary model as README changes. | Git-safety and evidence proof. | Decision 19; Phase 23 |
| SURF-010 | P1 | PLANNED | The README illustration and social-preview asset MUST be produced, validated, approved, and delivered as separate outputs. | Two independent artifact records. | Decision 23; Phase 24 |
| SURF-011 | P1 | PLANNED | Visual assets MUST be factually accurate, accessible, appropriately licensed, product-specific, and free of unsupported claims. | Visual review checklist and provenance. | Decisions 8, 23 |
| SURF-012 | P1 | PLANNED | README visuals MUST use stable repository-relative paths and idempotent file naming. | Re-run produces no duplicate asset or path churn. | Decision 23; Phase 24 |
| SURF-013 | P1 | PLANNED | Social-preview delivery MUST include validated dimensions/file size and operator instructions when manual upload is required. | Asset validation and instructions. | Decisions 19, 23; Phase 24 |
| SURF-014 | P1 | PLANNED | Release/package audits MUST report actionable inconsistencies without changing the owned publishing surface. | Audit and handoff evidence. | Decision 19; Phase 22 |
| SURF-015 | P2 | PLANNED | GitHub-generated language and contributor anomalies SHOULD be investigated through repository contents/history and reported without attempting cosmetic manipulation. | Audit explanation and allowed remediation. | Decision 19; Phase 22 |

## 9. Core engine and registry requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| CORE-001 | P0 | IMPLEMENTED | The engine MUST remain generic; Aspose-specific names and facts MUST reside only in registry and policy data. | Synthetic non-Aspose test and code review. | Decisions 1, 13 |
| CORE-002 | P1 | IMPLEMENTED | The package and CLI name MUST remain `readme_agent` / `readme-agent`. | Package metadata and CLI tests. | Decision 2 |
| CORE-003 | P0 | IMPLEMENTED | `data/products.json` MUST be the hard allow-list checked before network, clone, generation, or settings operations. | Allow-list block proof. | Decision 4 |
| CORE-004 | P0 | IMPLEMENTED | Disabled or unlisted repositories MUST produce a blocked result without a clone or write attempt. | Existing allow-list tests/evidence. | Decision 4 |
| CORE-005 | P1 | IMPLEMENTED | Registry entries MUST support `full`, `dry_run`, and `disabled` modes. | Loader/model tests. | Decision 10 |
| CORE-006 | P1 | IMPLEMENTED | The three enabled repositories MUST retain their blank-slate, zero-gap, and partial-gap engineering pilot roles until the pilot contract is revised by a ledger decision. | Registry and decision review. | Decisions 10, 24 |
| CORE-007 | P0 | IMPLEMENTED | Missing or undetected license information MUST soft-degrade to a real gap rather than crash or hard-block. | License auditor tests. | Decision 5 |
| CORE-008 | P0 | IMPLEMENTED | The engine MUST scan the full README for required elements, not only its owned marker spans. | Gap-detector fixtures. | Phase 6 |
| CORE-009 | P1 | IMPLEMENTED | The four shipped policy elements MUST remain supported for backward compatibility until explicitly deprecated. | Existing tests and policy schema. | Decision 7 |
| CORE-010 | P0 | IMPLEMENTED | Domain detection in generic engine code MUST not be hardcoded to Aspose.org or Aspose.com. | Synthetic-domain test. | Decision 13 |
| CORE-011 | P0 | IMPLEMENTED | `facts_hash` MUST exclude values derived from content the agent itself changes, including `gap_report`. | Idempotency tests. | Decision 11 |
| CORE-012 | P0 | IMPLEMENTED | Work clones MUST be stable per repository; baseline clones and evidence MUST remain run-scoped. | Path and idempotency tests. | Decision 12 |
| CORE-013 | P0 | IMPLEMENTED | Git clone/fetch behavior MUST pin line-ending determinism per invocation. | Git-safety tests. | Decision 14 |
| CORE-014 | P0 | IMPLEMENTED | Generation schema version MUST change whenever prompt or owned-span rendering contracts change. | Version-tripwire test. | Decision 15 |
| CORE-015 | P0 | IMPLEMENTED | Validation MUST run on generation, explicit validation, idempotent, and zero-gap paths. | Existing validation tests. Two real bugs in this exact validation-after-render path found and fixed 2026-07-18 during the Phase 21 live pilot re-proof (force-regenerating `cells/java`): a re-render could silently drop elements whose only evidence was the span being replaced, and `_validate` compared a freshly-rendered span against a stale pre-render hash, failing `idempotency` on every legitimate re-render. Both fixed in `orchestrator.py`; regression tests: `tests/unit/test_orchestrator.py::TestStaleNoncompliantAndForceRegenerate::test_force_regenerate_preserves_previously_rendered_links`/`::test_force_regenerate_of_a_stale_hash_render_does_not_spuriously_fail_idempotency` (each independently confirmed to fail on the pre-fix code). | Decision 16 |
| CORE-016 | P0 | IMPLEMENTED | Hash matching MUST control whether generation is required, not whether validation is required. | `STALE_NONCOMPLIANT` proof. See CORE-015 — the second 2026-07-18 fix corrected a case where this property was violated in the opposite direction (validation spuriously failed after a legitimate, successful regeneration). | Decision 16 |
| CORE-017 | P1 | IMPLEMENTED | Explicit `--force-regenerate` MUST be required to regenerate stale noncompliant owned content. | CLI/orchestrator tests. See CORE-015 for the 2026-07-18 fix ensuring a forced regeneration actually succeeds correctly rather than silently corrupting or spuriously failing. | Decision 16 |
| CORE-018 | P1 | IMPLEMENTED | The renderer MUST use canonical configured URLs rather than model-invented URLs. | Referential-integrity tests. | Decisions 6, 8 |
| CORE-019 | P1 | IMPLEMENTED | Evidence and facts hashing MUST normalize CRLF/LF consistently. | Hash tests. | Decisions 14, 15 |
| CORE-020 | P1 | PLANNED | The engine MUST extend the existing inspect → gap detect → facts → propose/render → validate → evidence flow to new surfaces rather than creating an unrelated second pipeline. | Architecture and integration tests. | Phases 21–24 |
| CORE-021 | P1 | PLANNED | Each new surface MUST have an explicit detector, authority class, proposal/render path if allowed, validators, evidence, and apply gate if remote. | Surface registration tests. | Decision 19 |
| CORE-022 | P1 | PLANNED | A surface classified as product-agent owned or GitHub generated MUST have no write handler. | Registry/schema negative test. | Decision 19 |
| CORE-023 | P2 | IMPLEMENTED | The products registry MUST be kept in sync with the authoritative GitHub orgs (seeded by `data/families.json`) without mutating agent-owned fields (`mode`/`ecosystem`/`policy_profile`). | `scripts/update_products_registry.py` merge-logic unit tests + live `--dry-run` round-trip proof (see `plans/master.md` Verification Checklist). | Phase 18; Decision 4 |
| CORE-024 | P2 | PLANNED | Insertion and presentation behavior MUST be tested against the remaining registry README corpus, including .NET repositories. | Phase-19 corpus results. | Phase 19 |
| CORE-025 | P2 | PLANNED | Historical evidence validation SHOULD support fully offline replay against an evidence directory. | Offline validation design and tests. | Open item in master plan |
| CORE-026 | P1 | IMPLEMENTED | The CLI MUST provide the seven shipped commands: `preflight`, `inspect`, `generate`, `run`, `run-registry`, `report`, and `validate`. | CLI parser and command tests. | Phase 12 |
| CORE-027 | P0 | IMPLEMENTED | CLI exit codes MUST remain: `0` pass, `1` validation/policy failure, `2` usage/config error, and `3` preflight/git-safety/allow-list failure. | CLI tests. | Phase 12 |
| CORE-028 | P0 | IMPLEMENTED | Preflight MUST verify GitHub read access and the configured LLM model before clone or generation and MUST fail closed. | Live and fixture preflight tests. | Phase 2 |
| CORE-029 | P1 | IMPLEMENTED | The shipped ecosystem parser MUST support Maven `pom.xml` product metadata, including BOM-safe reading and known parent-block behavior. | Maven parser fixtures. | Phase 4 |
| CORE-030 | P1 | IMPLEMENTED | The owned `resources` span MUST use versioned begin/end markers containing the facts hash and schema version, and marker removal MUST remain the exact inverse of insertion. | Marker round-trip and change-boundary tests. | Marker format; Decisions 9, 15 |
| CORE-031 | P1 | IMPLEMENTED | Runtime paths MUST honor `README_AGENT_RUNS_DIR` when set and otherwise use repository-root-relative `runs/`, with fresh baseline clones, stable work clones, and run-scoped evidence. | Path tests and runtime inspection. | Runtime layout; Decision 12 |
| CORE-032 | P0 | IMPLEMENTED | Automated registry discovery MUST default every newly discovered `(family, platform)` entry to `mode: "disabled"` and MUST NOT modify `mode`/`ecosystem`/`policy_profile` on any existing entry, regardless of what GitHub reports. | `test_merge_new_entry_defaults_to_disabled`, `test_merge_preserves_owned_fields_on_existing_entry` (`tests/unit/test_update_products_registry.py`). | Decision 4; Phase 18 |

## 10. Operational and workflow requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| OPS-001 | P1 | PLANNED | The dispatched GitHub Actions workflow MUST be reproducible locally with `act` before it is relied on for remote execution. | Phase-16 `act workflow_dispatch` proof. | Phase 16 |
| OPS-002 | P1 | IMPLEMENTED | The ordinary CI workflow MUST run ruff, formatting checks, mypy, and non-live pytest across Python 3.11–3.13. | CI workflow and successful run. | CI & Safety |
| OPS-003 | P1 | IMPLEMENTED | `readme-agent-run.yml` MUST remain manually dispatched, read-only, dry-run only, and upload evidence as a workflow artifact. | Workflow inspection and dry-run execution. | Phase 15/16 |
| OPS-004 | P2 | PLANNED | The golden-set monitor MUST run on a schedule and manual trigger, use the LLM-exercising pilot, remain hard-coded to dry-run, and append stable run history. | Workflow and history proof. | Phase 18 |
| OPS-005 | P2 | IMPLEMENTED | Registry synchronization MUST scan the authoritative GitHub orgs (seeded by `data/families.json`) and prove a no-loss round trip. | `scripts/update_products_registry.py` unit tests + live `--dry-run` proof. | Phase 18 |
| OPS-006 | P2 | PLANNED | Dependency updates MUST be proposed through reviewable Dependabot pull requests rather than silent automation. | Dependabot configuration. | Phase 18 |
| OPS-007 | P1 | IMPLEMENTED | `data/families.json` MUST enumerate the GitHub orgs to scan for registry discovery and MUST NOT itself grant allow-list permission — only `data/products.json` entries with a non-`disabled` `mode`, checked via `registry.loader.is_permitted()`, are ever permitted. | `test_real_families_json_has_26_entries_with_matching_org_convention`, `test_real_families_json_covers_every_org_referenced_by_products_json`. | Decision 4; CORE-003 |
| OPS-008 | P1 | IMPLEMENTED | The scheduled registry-update workflow MUST propose changes via pull request and MUST NOT push directly to the default branch. | `.github/workflows/update-products-registry.yml` uses `peter-evans/create-pull-request`; workflow inspection. | Phase 18 |
| OPS-009 | P2 | BACKLOG | A local (non-CI) run of `tests/integration/test_state_git_backend_live.py` MUST NOT be able to hang silently and indefinitely on an unconfigured `git push` credential -- it should fail fast with a clear error, or the prerequisite should be documented/scripted so it's never hit blind. Found live, 2026-07-19: `git push` to `origin` blocked ~35 minutes with zero output (no credential prompt text, no error) because `GH_TOKEN` being present in the environment does not by itself wire git's push auth -- neither `run_git()`'s 120s subprocess timeout nor pytest catches this, since the hang is inside git's own credential-resolution step. Root-caused and worked around this session (temporary `http.https://github.com/.extraheader` from `GH_TOKEN`, removed after) -- documented as a prerequisite in the test file's own docstring; not yet a scripted/automatic fix. | No fix designed yet -- candidates: a `conftest.py` fixture that configures/tears down the extraheader automatically for `@pytest.mark.live` git tests, or a fast preflight check that fails clearly (e.g. `git ls-remote` against a scratch ref) before the real test body attempts a push. | Found during 2026-07-19 specialist-domain-isolation live-verification pass; no owning wave -- logged per Decision 29 so it isn't silently lost |

## 11. LLM requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| LLM-001 | P0 | IMPLEMENTED | LLM use MUST be limited to jobs that require language generation; deterministic facts and URLs MUST remain deterministic. | Existing job-routing tests. | Decision 8 |
| LLM-002 | P0 | IMPLEMENTED | The shipped relationship paragraph job MUST run only when `relationship_explained` is a detected gap. | Gap/orchestrator tests. | Decision 8 |
| LLM-003 | P0 | IMPLEMENTED | LLM output MUST conform to a strict schema and MUST fail closed on local schema failure. | Schema tests. | LLM contract |
| LLM-004 | P0 | IMPLEMENTED | Model self-reported claims MUST be cross-checked against authoritative facts and rendered output. | Referential-integrity tests. | Decision 6 |
| LLM-005 | P0 | PLANNED | Future README, description, or visual-generation jobs MUST consume only approved product facts and policy inputs. | Prompt signature and provenance tests. | Decisions 8, 22 |
| LLM-006 | P0 | PLANNED | The model MUST NOT invent capabilities, formats, package coordinates, release facts, licenses, support claims, or commercial claims. | Adversarial fixtures and claim validation. | Decisions 6, 8, 22; Phase 17 |
| LLM-007 | P0 | IMPLEMENTED | Retry MUST be bounded and limited to retryable transport/rate/server failures, not schema or non-retryable client errors. | Client tests. | LLM contract |
| LLM-008 | P0 | IMPLEMENTED | The selected model MUST be validated through preflight against the live model list before use. | Live preflight evidence. | Phase 2/5 |
| LLM-009 | P1 | PLANNED | Generated descriptions and prose MUST be validated for clarity, prohibited terms, unsupported claims, product specificity, and duplication. | Phase-21/22 validators. | Decisions 8, 18 |
| LLM-010 | P1 | PLANNED | Generated visual concepts MUST not depict unsupported formats, workflows, integrations, performance, or commercial features. | Visual factual-accuracy review. | Decisions 8, 23 |
| LLM-011 | P1 | PLANNED | Prompt-injection content found in repository files MUST be treated as untrusted data and MUST not override system policy, ownership, or output schema. | Adversarial fixture tests. | Phase 17 |
| LLM-012 | P2 | PLANNED | Model drift SHOULD be monitored through a live golden-set run that cannot escalate to write mode. | Golden-set workflow and history. | Phase 18 |
| LLM-013 | P1 | IMPLEMENTED | LLM endpoint and key selection MUST honor the documented environment-variable precedence without logging secret values. | Client configuration tests and secret scan. | LLM Contract |
| LLM-014 | P1 | IMPLEMENTED | The live client MUST use the documented chat-completions request/response contract and configured model, temperature, and token limit. | Live client tests and recorded redacted request. | LLM Contract |
| LLM-015 | P2 | IMPLEMENTED | Every run's evidence record and human-readable report MUST record LLM gateway call count and which job/capability triggered each call, so usage is auditable and visible rather than silently minimized. | `evidence/writer.py::write_evidence()` writes `llm_call_count`/`llm_calls` into `manifest.json` (surfaced by `readme-agent report`); `GenerateResult.llm_calls` surfaced by `cmd_generate`. `tests/unit/test_evidence_writer.py`, `tests/unit/test_orchestrator.py::TestBlankSlateRepo`. | Decision 26; NFR-012/013 |
| LLM-016 | P2 | IMPLEMENTED | `env.py:6`'s `DEFAULT_LLM_MODEL = "gpt-oss"` is the default for the shipped `relationship_explained` job, but `plans/investigations/llm-gateway-characterization.md` found `gpt-oss` unreliable for freeform structured output (1/10 valid) and recommended `qwen3-next` for instruction-critical/structured jobs; the default was never updated to match. Root fix is per-job model routing (Decision 26(e)), not a single flat default, since future LLM jobs (Wave 6/7) will need the same per-job choice. | `env.py::JOB_MODEL_ROUTING`/`llm_model_for_job()` route `relationship_explained` → `qwen3-next`; `DEFAULT_LLM_MODEL` fallback changed to `qwen3-next` too. `tests/unit/test_env.py`. | Decision 26(e); found during 2026-07-19 agentic-usage assessment |

## 12. Validation and quality gates

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| VAL-001 | P0 | IMPLEMENTED | All shipped validator rules MUST run on every relevant invocation. | Validator-registry tests. | Decision 16 |
| VAL-002 | P0 | IMPLEMENTED | `referential_integrity` MUST remain a hard error gate. | Existing tests. | Decision 6 |
| VAL-003 | P0 | IMPLEMENTED | `change_boundary` MUST prove that content outside owned spans is unchanged for the shipped renderer. | Existing tests. | Validator registry |
| VAL-004 | P0 | IMPLEMENTED | LLM-authored content MUST satisfy configured word-count, prohibited-term, link-whitelist, talking-point, and referential-integrity rules. | Existing tests. | Validator registry |
| VAL-005 | P1 | PARTIAL | Phase-21 README validation MUST evaluate product explanation, audience/problem, installation, verified first use, capability accuracy, navigation, visual usefulness, maintenance/contribution signals, and natural link placement. | `readme_agent.readme.presentation_report.READMEPresentationReport` (`detect_presentation`), `tests/unit/test_presentation_report.py`. Covers, read-only: opening product explanation, audience/ecosystem statement, install-path resolution (`ecosystems/resolver.py`, opt-in), runnable-example presence, heading-level consistency. Does not cover capability accuracy, visual usefulness, or maintenance/contribution signals (out of Phase 21's scope — see master.md's dimension-to-phase table: these belong to Phases 23/24) or natural link placement as an *action* (that's the 21e section-aware change plan, deferred, design-only). | Phase 21a |
| VAL-006 | P0 | IMPLEMENTED | Presentation validation MUST not reward moving promotional links upward. | Negative fixtures and rule review. | Decision 17; Phase 21c. `validation/rules/product_first_opening.py`, `validation/rules/commercial_mention_discipline.py` (both ERROR), `tests/unit/test_validation_rules.py::TestProductFirstOpening`/`TestCommercialMentionDiscipline` — includes a negative fixture modeled on the real `3d/java` bot-authored resources-section finding. |
| VAL-007 | P0 | PLANNED | Every changed factual claim MUST pass provenance validation. | Claim-to-source validator. | Decisions 18, 22 |
| VAL-008 | P0 | PLANNED | Every proposed action MUST pass authority-class validation before a renderer or write operation is selected. | Surface authorization test. | Decision 19 |
| VAL-009 | P0 | PLANNED | API/settings changes MUST pass dry-run, permission, before/after, and rollback validation. | Phase-22 proposal tests. | Decision 19 |
| VAL-010 | P1 | PLANNED | Topics MUST be checked for relevance, duplication, valid format, and keyword stuffing. | Topics validator. | Phase 22 |
| VAL-011 | P1 | PLANNED | Repository descriptions MUST be checked for length, product specificity, clarity, and unsupported claims. | Description validator. | Phase 22 |
| VAL-012 | P1 | PLANNED | Community files MUST be checked for recognized location/name, policy relevance, quality, internal consistency, and broken links. | Phase-23 fixtures. | Phase 23 |
| VAL-013 | P1 | PLANNED | Visuals MUST be checked for dimensions, file size, accessibility, license/provenance, factual accuracy, stable naming, and correct delivery surface. | Phase-24 validator. | Decision 23 |
| VAL-014 | P1 | PLANNED | Markdown, links, anchors, relative asset paths, code fences, and generated files MUST be validated after every presentation change. | Presentation validation suite. | Phases 17, 21, 24 |
| VAL-015 | P1 | PLANNED | A proposal with unresolved product-fact conflicts or missing mandatory facts MUST not pass. | Blocking-status tests. | Decision 22 |
| VAL-016 | P2 | PLANNED | Similarity checks SHOULD detect accidental template cloning across pilot repositories while allowing legitimate shared policy language. | Cross-pilot comparison. | Decision 24; Phase 26 |
| VAL-017 | P2 | PLANNED | Adversarial fixtures MUST cover prompt injection, malformed markers, malformed/missing README, non-UTF8 content, invalid model output, and policy violations. | Phase-17 report. | Phase 17 |
| VAL-018 | P3 | BACKLOG | `validation/rules/prominence.py`'s position check is gated on `ctx.pre_render_gap_report`: an element that is a gap at render time is skipped by the check (deliberately — it's about to be rendered), but on the *next* run that same element is now permanently present, so the check fires for the first time then, not on the run that actually rendered it. Net effect: a freshly-rendered org/com link's burial is never flagged on the run that creates it, only discovered one run later. WARNING-severity only (never blocks `GENERATED`/`COMPLIANT_NO_CHANGE`); found during Wave 2's post-implementation verification pass, confirmed unrelated to Waves 1-3 (`validation/` imports nothing from `ecosystems/`/`inspection/`), deferred per explicit user direction. Not yet triaged into `PLANNED` with real acceptance criteria. | `runs/evidence/20260718-165558-c33e/facts.json` (`products_org_link: false`, pre-render) vs `runs/evidence/20260719-081405-cfdc/facts.json` (`products_org_link: true`, post-render, identical `facts_hash`) — the real pdf/java pilot rerun that surfaced it. | Decision 29; GOV-014 |

## 13. Safety, security, and evidence requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| SAFE-001 | P0 | IMPLEMENTED | Git push MUST be disabled through both a neutered push URL and a blocking pre-push hook. | Existing real push-block proof. | CI & Safety |
| SAFE-002 | P0 | IMPLEMENTED | Push-blocking MUST be independently verified from actual remote and hook contents, not assumed from successful setup calls. | `verify_push_blocked()` evidence. | CI & Safety |
| SAFE-003 | P0 | IMPLEMENTED | The allow-list MUST operate independently from push-blocking. | Separate tests/evidence. | Decision 4 |
| SAFE-004 | P0 | IMPLEMENTED | CI for ordinary pull requests MUST require no real secrets and MUST exclude live tests by default. | Workflow inspection and CI run. | CI & Safety |
| SAFE-005 | P0 | IMPLEMENTED | The manual workflow MUST expose dry-run only and read-only content permissions. | Workflow file test/review. | CI & Safety |
| SAFE-006 | P0 | PLANNED | Scheduled monitoring MUST be structurally unable to escalate to full/write mode. | Workflow-level hard-coded dry-run test. | Phase 18 |
| SAFE-007 | P0 | IMPLEMENTED | Secrets MUST be redacted before any evidence is written. | Deterministic and opportunistic secret-scan tests. | Phase 11 |
| SAFE-008 | P0 | IMPLEMENTED | Evidence writes MUST be atomic. | Writer tests. | Phase 11 |
| SAFE-009 | P0 | IMPLEMENTED | Evidence MUST include facts, request/response where applicable, diff, validation report, manifest, and checksums. | Existing evidence bundle inspection. | Phase 11 |
| SAFE-010 | P0 | PLANNED | Remote settings writes MUST require explicit authorization, necessary permissions, a pre-write snapshot, and a rollback plan. | Phase-22 apply-gate tests. | Decision 19 |
| SAFE-011 | P0 | PLANNED | No manual-UI step may be represented as automatically completed unless evidence of the operator action is supplied. | Delivery status remains `PREPARED_FOR_MANUAL_APPLY`. | Decision 19 |
| SAFE-012 | P0 | PLANNED | The system MUST not silently revert changes made by another product agent. | Drift flow produces proposal/handoff only. | Decision 21 |
| SAFE-013 | P1 | PLANNED | Evidence MUST record surface class, action mode, authoritative source, changed fields/files, validators run, and acceptance status. | Evidence schema. | Phases 21–25 |
| SAFE-014 | P1 | PLANNED | Evidence SHOULD record requirement IDs and decision/phase traceability for the run. | Evidence manifest fields. | GOV-012 |
| SAFE-015 | P1 | PLANNED | Every remote proposal MUST be reproducible from recorded facts, policy, baseline, and tool version. | Replay or deterministic comparison. | Phases 22–26 |
| SAFE-016 | P1 | PLANNED | Generated binary visual assets MUST have checksums and provenance records. | Artifact manifest. | Phase 24 |
| SAFE-017 | P1 | PLANNED | A failed validation MUST block commit/proposal acceptance and identify the failed requirement IDs. | Failure report tests. | GOV-012; Phases 21–24 |
| SAFE-018 | P2 | PLANNED | Dependency versions SHOULD be locked and Dependabot SHOULD maintain them through reviewable PRs. | Lockfile and Dependabot workflow. | Phase 18 |

## 14. Integration and drift-protection requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| INT-001 | P0 | PLANNED | The central agent MUST integrate after or alongside product publishing so presentation can be revalidated after product changes. | Simulated publishing integration proof. | Decision 21; Phase 25 |
| INT-002 | P0 | PLANNED | Drift detection MUST identify removed owned markers, lost required sections, weakened or generic prose, stale facts, stale visuals, broken links, and missing supporting files. | Drift fixture suite. | Decision 21 |
| INT-003 | P0 | PLANNED | Drift detection MUST compare against both current authoritative product facts and the accepted presentation baseline. | Drift evidence includes both comparisons. | Decisions 21, 22 |
| INT-004 | P0 | PLANNED | Detected drift MUST produce evidence and an allowed repair proposal or product-agent handoff; it MUST NOT silently overwrite. | Drift run behavior tests. | Decision 21 |
| INT-005 | P0 | PLANNED | Technical discrepancies MUST be routed to the owning product agent. Presentation-only regressions MAY be repaired through normal central-agent gates. | Classified handoff/proposal evidence. | Decisions 18, 21, 22 |
| INT-006 | P1 | PLANNED | Product-fact changes SHOULD trigger targeted reevaluation of dependent presentation surfaces. | Dependency-driven rerun proof. | FACT-010; Phase 25 |
| INT-007 | P1 | PLANNED | Scheduled re-audits MUST run in dry-run/observe mode and preserve historical results. | Golden-set monitor and history. | Phase 18/25 |
| INT-008 | P1 | PLANNED | The system MUST detect when another agent overwrites high-quality content with a generic template. | Regression fixture and report. | Decision 21 |
| INT-009 | P1 | PLANNED | Drift findings MUST distinguish legitimate product updates from presentation regressions. | Classification tests and human-reviewed fixtures. | Decision 21 |
| INT-010 | P2 | PLANNED | The integration contract SHOULD be machine-readable and versioned. | Product-facts/change-handoff schema version. | Decision 22; Phase 25 |

## 15. Non-functional requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| NFR-001 | P0 | IMPLEMENTED | Runs MUST be deterministic for identical independent inputs, policy, code, and model response fixtures. | Idempotency and hash tests. | Decisions 11–16 |
| NFR-002 | P0 | IMPLEMENTED | A second compliant run MUST make no new diff and no unnecessary LLM call. | Cells/Java idempotency proof. | Decision 12 |
| NFR-003 | P0 | GOVERNANCE | The system MUST fail closed on authority ambiguity, invalid policy, invalid model schema, unsafe git state, missing required permission, or unresolved mandatory facts. | Negative tests. | Decisions 4, 6, 18, 19, 22 |
| NFR-004 | P1 | IMPLEMENTED | The codebase MUST pass supported Python matrix tests, ruff, formatting checks, and mypy. | CI evidence. | Status/CI |
| NFR-005 | P1 | PLANNED | New surface implementations MUST remain modular but use the common pipeline and evidence model. | Architecture review and tests. | CORE-020/021 |
| NFR-006 | P1 | PLANNED | Outputs MUST be understandable to product owners and reviewers, not only machine-readable. | Human-readable reports accompany JSON evidence. | Phases 21–26 |
| NFR-007 | P1 | PLANNED | The system MUST preserve repository-specific character and SHOULD avoid repetitive AI-style prose. | Human review and similarity checks. | Decisions 18, 24 |
| NFR-008 | P1 | PLANNED | Automated changes MUST be reversible through recorded baseline/diff or settings snapshot. | Rollback proof. | Decisions 19, 21 |
| NFR-009 | P1 | PLANNED | The system MUST support Windows development and Linux CI without line-ending drift. | Cross-platform tests. | Decision 14 |
| NFR-010 | P2 | PLANNED | Large registry runs SHOULD isolate per-repository failures so one blocked repository does not corrupt or falsely complete another. | Registry-run failure-isolation tests. | Phase 25/26 |
| NFR-011 | P2 | PLANNED | Reports SHOULD be stable enough for before/after comparisons across runs and releases. | Schema versioning and history tests. | Phase 18/25 |
| NFR-012 | P2 | PLANNED | The system SHOULD avoid *redundant* LLM calls (identical facts/policy/prompt inputs MUST NOT re-trigger generation or re-selection — see `NFR-001`/idempotency) but MUST NOT avoid LLM usage for judgment, planning, interpretation, or coordination where a capability legitimately calls for it. Call volume is tracked (`LLM-015`), not minimized. | Idempotency tests (no duplicate call on unchanged input) plus `LLM-015` call-count evidence. | Decision 8; Decision 26 |
| NFR-013 | P0 | GOVERNANCE | The system MUST remain a deliberate blend of an autonomous, LLM-driven planning/coordination layer and a deterministic execution layer: capability discovery and selection happen automatically (no human selects a capability, skill, or command during a normal run); the LLM plans, interprets, coordinates, and proposes repairs; deterministic tools own facts, mutations, validation, evidence, permissions, and rollback; every agentic proposal or `capability_action` passes deterministic pre-gates (hashed-input/fingerprint skip, permission/allow-list check) and post-gates (schema, referential integrity, the always-run validator registry) before any effect. | Architecture review; capability-dispatch, job-routing, hash-coupling, and validator tests; model-routing evidence in `plans/investigations/llm-gateway-characterization.md`. | Decision 26 |

## 16. Pilot, rollout, and acceptance requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| PIL-001 | P0 | GOVERNANCE | The initial pilot MUST use the three enabled registry repositories representing blank-slate, zero-gap, and partial-gap conditions. | Registry and run list. | Decisions 10, 24 |
| PIL-002 | P0 | PLANNED | The three pilots MUST receive repository-specific proposals, not three instances of one template. | Cross-pilot comparison. | Decision 24 |
| PIL-003 | P0 | PLANNED | No repository beyond the pilot set may be enabled until the Phase-26 rollout gates pass. | Registry modes remain disabled. | Decision 24 |
| PIL-004 | P0 | PLANNED | Each pilot MUST pass deterministic validation, product-fact provenance, ownership/control checks, and independent human/agent review. | Pilot acceptance bundle. | Decision 24; Phase 26 |
| PIL-005 | P0 | PLANNED | The pilot MUST prove that no unsupported GitHub write path or control claim remains. | Control-boundary proof. | Decisions 19, 24 |
| PIL-006 | P0 | PLANNED | The pilot MUST survive a simulated product-agent refresh without silently losing accepted presentation quality. | Publishing-integration proof. | Decisions 21, 24 |
| PIL-007 | P1 | PLANNED | Pilot review MUST compare before/after developer comprehension, installation usability, claim accuracy, link relevance, and presentation quality. | Structured review report. | Phase 26 |
| PIL-008 | P1 | PLANNED | Sponsor acceptance of the quality standard and pilot output MUST be recorded before expansion. | Acceptance record. | Decision 24 |
| PIL-009 | P1 | PLANNED | Wider rollout MUST proceed in small waves with per-wave evidence and stop conditions. | Rollout plan and wave results. | Decision 24 |
| PIL-010 | P2 | PLANNED | A failed pilot SHOULD improve validators, policies, facts contracts, or ownership rules before rerunning rather than receiving an ad hoc one-off patch. | Repair-loop evidence. | Governance; Phase 26 |
| PIL-011 | P0 | GOVERNANCE | Research and development tasks (portfolio surveys, fact-gathering, policy/validator design, gap analysis, and similar) MUST cover every entry in `data/products.json` with equal precedence regardless of `mode`. Only end-to-end execution/verification is scoped to the three enabled Java pilots (PIL-001), and only because they are the sole non-`disabled` entries today — an access constraint, not a precedence claim. | Task/agent instructions and investigation docs cite the full registry, not just the pilot set; e2e evidence states the access reason explicitly. | Decision 24 (clarified 2026-07-19) |

## 17. Measurement requirements

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| MET-001 | P1 | RESEARCH-GATED | Phase 20 MUST establish the current GitHub referral baseline and determine whether ≥10 weekly visitors to Aspose.org is realistic. | Numbered feasibility study. | Decision 20 |
| MET-002 | P1 | RESEARCH-GATED | The feasibility study MUST include pilot repository views/uniques, placement-specific click assumptions, repository-coverage math, timing, and confidence/limitations. | Study completeness review. | Phase 20 |
| MET-003 | P1 | PLANNED | Approved eligible links SHOULD use consistent UTM parameters so referral traffic can be attributed. | Link output and analytics evidence. | Decision 20 |
| MET-004 | P1 | PLANNED | Post-rollout measurement MUST track referral count together with product relevance and README-quality checks. | Weekly report. | Decision 20 |
| MET-005 | P0 | GOVERNANCE | The traffic target MUST NOT override BIZ-001, BIZ-003, RDM-002, or RDM-012. | Decision/requirements conflict check. | Decision 20 |
| MET-006 | P1 | RESEARCH-GATED | Phase 20 MUST define a minimum observation period before rollout decisions are based on traffic. | Feasibility study. | Phase 20 |
| MET-007 | P2 | PLANNED | Pilot and rollout reports SHOULD distinguish direct GitHub referral traffic from other sources and from internal/test clicks where possible. | Analytics methodology. | Decision 20 |
| MET-008 | P2 | PLANNED | The target MAY be revised only through an explicit decision supported by baseline evidence; it MUST NOT be silently changed in code or reports. | Master-plan decision and requirements update. | GOV-004/005 |

## 18. Documentation and research deliverables

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| DOC-001 | P0 | GOVERNANCE | `plans/master.md` MUST link to this requirements specification as the authoritative requirement register. | Link validation. | Decision 25 |
| DOC-002 | P0 | GOVERNANCE | This document MUST link to `plans/master.md` as the execution and decision authority. | Link validation. | Decision 25 |
| DOC-003 | P1 | IMPLEMENTED | `docs/presentation-standard.md` MUST study n8n, 2–3 additional leading FOSS repositories, and strong Aspose NuGet pages for principles rather than templates. | `docs/presentation-standard.md` studies n8n, NuGet Aspose.Cells, and four additional repositories (iText, EPPlus, SheetJS, Apache PDFBox — exceeding the 2–3 minimum); evidence in `plans/investigations/reference-repository-benchmark.md`. | Phase 20 |
| DOC-004 | P1 | IMPLEMENTED | The presentation standard MUST define product clarity, audience fit, trust signals, installation path, verified examples, navigation, visual usefulness, contribution readiness, maintenance signals, and natural commercial context. | `docs/presentation-standard.md` §"The ten dimensions" defines all ten, each with source evidence and a resulting rule. | Phase 20 |
| DOC-005 | P1 | IMPLEMENTED | `docs/github-surface-control.md` MUST verify every control claim against current official GitHub documentation and record class, permission, endpoint/file/UI location, dry-run/apply behavior, rollback, and evidence. | `docs/github-surface-control.md` per-surface table plus live confirmation across six reference repositories and the 25-repository registry. | Phase 20 |
| DOC-006 | P1 | RESEARCH-GATED | The product-facts and change-handoff schema MUST be documented and frozen before Phase-21/25 content work depends on it. | Schema and examples. | Decision 22; Phase 20 |
| DOC-007 | P1 | RESEARCH-GATED | The traffic-feasibility study MUST answer whether the target is achievable, by when, through how many repositories, and under what assumptions. | Numbered study. | Decision 20; Phase 20 |
| DOC-008 | P1 | PLANNED | `docs/architecture.md`, `docs/safety-model.md`, and `docs/policy-authoring.md` MUST be updated when implementation changes make them stale. | Documentation consistency review. | Master-plan status |
| DOC-009 | P1 | PLANNED | Each completed phase MUST update requirement statuses and attach evidence references before closeout. | Phase-close checklist. | GOV-007/010 |
| DOC-010 | P2 | PLANNED | The repository SHOULD include a generated traceability report mapping requirements to decisions, phases, tests, modules, and evidence. | Generated report. | GOV-009/012 |

## 19. Autonomous runtime and capability requirements

Added by the 2026-07-18 sprint reset (`AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001`, decision #26).
This is a lean starter set, not the full detail of every capability the sprint's Waves 1–9
eventually add — each row's full acceptance criteria get sharpened when the wave that builds the
thing it describes actually lands, per `GOV-007` (nothing here may claim `IMPLEMENTED` without
objective evidence). All rows started `PLANNED`; `AGT-002` moved to `PARTIAL` after Wave 1's live
spike proof (see its row) — the rest remain `PLANNED` until their own wave lands.

### AGT — Autonomous planning and agent-runtime behavior

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| AGT-001 | P0 | IMPLEMENTED | The runtime MUST NOT require a human to select a prompt, skill, command, agent, repository type, ecosystem, or next action during a normal run. | Architecture review; no manual-selection code path in the production runtime. `supervisor.loop.supervise_repo()` (Wave 5) selects every capability dynamically via `dispatch_tool_call`/`registry.all_tool_schemas()` — `capability_id` is never hardcoded in the loop itself (the one exception, the deterministic bootstrap task, is a documented, reasoned seed, not a human selecting a next action per-run). | Decision 26; Sprint Wave 5 |
| AGT-002 | P0 | IMPLEMENTED | A supervisor MUST be able to observe repository/task state, form or revise a task graph, execute a capability, observe the result, and replan — without a fixed, unconditional pipeline order. | Supervisor loop test: observe→plan→execute→observe→replan proven end-to-end. **Production supervisor built and live-proven (Wave 5, `src/readme_agent/supervisor/`)**, promoting Wave 1's spike: real task graph with cycle rejection (`ORC-001`), real replanning after a real (monkeypatched) failure with a scoped repair task (`tests/unit/test_supervisor_loop.py::TestRepair`), real durable state via `RunStateV1.supervisor_state`. Unit-proven against the real 4-capability registry + dispatcher with a fixture planner (7 scenarios: happy path, dedup, gap+independent-work, repair, durable no-op rerun, lock contention, turn-bound). **Live-proven 2026-07-19** (`tests/integration/test_supervisor_live.py`, real gateway, real `pdf/java` pilot, real `GitStateBackend`): real multi-round observe→plan→execute→observe against the live registry converges without hitting the repair-exhaustion bug-detector bound. The live pilot never actually failed, so replan-after-failure specifically is still proven only at unit level (monkeypatched) — an honest gap, not claimed as live-proven. **Remaining, non-blocking limitations**: multi-repository operation (single `org_repo` per call only) and multi-specialist fan-out reliability (Wave 7's ~7 independent specialist planning calls per run, entirely unmeasured; see `AGT-005`) — neither is part of this row's literal acceptance text. | Decision 26; Sprint Wave 1 (spike), Wave 5 (production, live-proven 2026-07-19) |
| AGT-003 | P1 | IMPLEMENTED | Every autonomous decision (capability selection, replan, stop/converge/block) MUST be recorded as a concise decision summary in evidence, not only as hidden model reasoning. | Evidence schema field + test. `supervisor.loop.DecisionSummary` (`turn`, `kind`, `detail`) appended for every capability selection, repair, and stop -- written into `runs/evidence/{run_id}/decisions.json`, proven in every `test_supervisor_loop.py` scenario. | Decision 26; Sprint Waves 5/8 |
| AGT-004 | P0 | IMPLEMENTED | The runtime MUST NOT stop on an arbitrary global iteration limit; it stops only on defined convergence, safe-proposal, missing-permission, or genuine-blocker conditions. | Stop-condition tests covering each defined condition. `supervisor/convergence.py`: `final_status()` classifies `CONVERGED_NO_CHANGE`/`CONVERGED_APPLIED`/`PARTIAL_WITH_CAPABILITY_GAP`/`BLOCKED`, called only once the planner's own explicit stop signal fires (never an automatic graph-emptiness check -- an earlier design that checked `is_converged()` at the top of every turn stopped after the bootstrap alone, before ever consulting the planner, found live via a smoke test before it became a design note); `check_repair_exhausted()`'s turn bound is a labeled `BLOCKED("repair_exhausted")` bug detector, proven distinct from a normal stop in `tests/unit/test_convergence.py` and `test_supervisor_loop.py::TestMaxTurns`. | Decision 26; Sprint §9 Task 5.4 |
| AGT-005 | P1 | BACKLOG | Multi-specialist fan-out reliability (Wave 7's ~7 independent specialist planning calls per run) MUST be empirically measured — not assumed from single-planner evidence — before Wave 7 is treated as production-ready. Today's only reliability evidence anywhere in this project is N=1, for one planner (`AGT-002`); per-specialist unreliability could compound multiplicatively across a run, but no measurement exists to size that risk. | A live, N>1, multi-specialist evidence run, mirroring `agentic-loop-proof.md`'s own methodology extended to ≥2 concurrent/sequential specialists. | Found during 2026-07-19 specialist-domain-isolation production-readiness pass; Decision 26; no owning wave assigned yet — logged per Decision 29 so it isn't silently lost, not designed or scheduled here |

### CAP — Capability contracts and discovery

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| CAP-001 | P0 | PARTIAL | Every runtime operation MUST be exposed as a registered capability with a typed manifest (inputs, outputs, permissions, side-effect class) before it is reachable by the supervisor. | Capability-registry schema validation test. **Mechanism built and tested** (`src/readme_agent/capabilities/schema.py`+`registry.py`, `tests/unit/test_capabilities.py`) — three operations registered with full typed manifests; not yet true of "every runtime operation" (most of the shipped engine isn't a capability yet) and there is no supervisor to reach them through (Wave 5). | Decision 26/27; Sprint Wave 2 |
| CAP-002 | P0 | PARTIAL | The capability registry MUST be loaded automatically at runner startup and support enumeration, repository-profile compatibility filtering, and permission-based filtering. | Registry discovery/filter tests. **Enumeration and permission-based filtering built and tested** (`registry.list_all()`/`filter_by()`, loaded automatically at import); loaded at import time, not yet a real "runner startup" (no GitHub Actions entrypoint exists — Wave 3+). Repository-profile compatibility filtering not built — `RepositoryProfile` doesn't exist yet (Wave 3). | Decision 26/27; Sprint Wave 2 |
| CAP-003 | P1 | IMPLEMENTED | A capability need with no compatible match MUST produce an explicit `CapabilityGap` record, not a silent skip. | Gap-record test + negative-control fixture. `tests/unit/test_capability_dispatcher.py::TestDispatchUnknownCapability` — an unknown `capability_id` dispatch produces a populated `CapabilityGap`, never a silent no-op. | Decision 26/27; Sprint §7 Task 3.4 |
| CAP-004 | P1 | IMPLEMENTED | Capability manifests MUST declare an execution type from a closed set (`deterministic_tool`, `agentic_analysis`, `agentic_planning`, `specialist_workflow`, `read_only_audit`, `gated_effector`, `validator`, `manual_delivery_preparation`). | Schema enum validation test. `tests/unit/test_capabilities.py::TestCapabilityManifestSchema::test_invalid_execution_type_rejected` — pydantic `Literal` enforces the closed set. | Decision 26/27; Sprint §7 Task 3.1 |
| CAP-005 | P2 | BACKLOG | At least one non-deterministic capability (`execution_type` other than `deterministic_tool`) should exist, deliberately chosen behind its own Decision Ledger entry, so the registry/dispatcher (Wave 2) and the durable state backend's `capability_outputs`/`EFF-001` fingerprint reuse (Wave 4) have a real non-read-only caller to prove against, not only deterministic wrappers. | No such capability exists yet — all four registered capabilities are `execution_type="deterministic_tool"` (confirmed by direct re-read, 2026-07-19, alongside Wave 4). | `we-are-not-as-piped-naur.md` remediation step 6, confirmed not yet executed and confirmed non-blocking for Wave 4; Decision 26 |
| CAP-006 | P0 | PARTIAL | Each specialist role's (Wave 7) and the independent verifier's (Wave 8) capability-calling scope MUST be structurally restricted to its own domain by the runtime's own manifest/dispatcher mechanism (`allowed_domains`/`caller_domain`) — never enforced only by convention, a shared registry filter, or whatever tool schemas a composition framework happens to offer. | Mechanism built and unit-tested: `capabilities/schema.py::CapabilityManifest.allowed_domains`, `capabilities/domains.py::KNOWN_DOMAINS`, `registry.py::_build()`'s domain-membership and fail-closed-sunset checks, `dispatcher.py::dispatch_tool_call`'s `caller_domain` parameter and `rejected_domain_denied` outcome — `tests/unit/test_capabilities.py::TestRegistryDomainEnforcement`, `tests/unit/test_capability_dispatcher.py::TestDispatchDomainDenied`. **A real first domain now exists** (2026-07-19, decision #39): `README_RECONCILIATION`, scoping `classify_upstream_change` — `test_capability_dispatcher.py::TestDispatchDomainDenied::test_real_classify_upstream_change_manifest_is_domain_scoped_and_gets_denied` proves `rejected_domain_denied` against the real, unmodified registry, not just a synthetic manifest. **Live-proven 2026-07-19** (`readme-agent supervise --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java --durable-state`, real gateway planner, real remote): the `readme_reconciliation` specialist's own dispatch of `classify_upstream_change` with `caller_domain=README_RECONCILIATION` succeeded for real inside the correctly-scoped domain, recording a real `DomainStateV1` entry. `PARTIAL` not `IMPLEMENTED` per `GOV-018`: the *denial* path (a caller outside the allowed domain) is proven only at unit level so far — the live run never attempted a cross-domain violation, since nothing in production is wired to do so yet. | Decision 34; `plans/investigations/specialist-domain-isolation-production-readiness.md`; Sprint Wave 6-8 |

### RUN — GitHub Actions runner execution

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| RUN-001 | P0 | IMPLEMENTED | GitHub Actions MUST be the primary runtime entry point; no normal production run may depend on an interactive session, a local persistent clone as durable state, or a manually resumed plan. | Workflow inspection; a full run reproduced from a fresh runner. **Proven three ways** (Wave 4): unit (`TestDurableStateFreshRunner`, fake backend), live (`test_state_git_backend_live.py`, real push to `origin`, 4/4), and now `RUN-003`'s real `act` reproduction of `readme-agent-run.yml` end to end — `docker cp`-based checkout confirmed to use the actual working tree (`git log` inside the container showed local HEAD, not a stale `origin/main`), the work clone was genuinely fresh (no `readme-agent:resources` marker, last commit = original upstream commit), durable state was read and recognized (zero LLM calls), and the job finished `Job succeeded`. Two real bugs found and fixed by this exact run, not by inspection: (1) a durable-state write-back failure (missing push credentials under `act`'s local-checkout mode) was uncaught and aborted the whole run, losing the evidence bundle for work that had already succeeded — `_record_accepted_state`/its read-side counterpart are now best-effort, matching `inspect_repo`'s `check_install` convention, regression-tested (`test_unreachable_state_backend_does_not_abort_the_run`); (2) `readme-agent-run.yml`'s `upload-artifact` step used `inputs.repo_key` (always "org/repo") directly as the artifact name, which the GitHub Actions API rejects outright (`/` is an invalid character) — sanitized to this project's own `{org}__{repo}` convention via a small shell step. | Decision 26/32; Sprint §3 |
| RUN-002 | P1 | PLANNED | One official runner entry point MUST accept `workflow_call`, `repository_dispatch`, `workflow_dispatch`, and scheduled triggers, all entering the same governed runtime. | Workflow trigger tests / inspection. | Decision 26; Sprint §3.1 |
| RUN-003 | P1 | IMPLEMENTED | Local development MUST be able to reproduce the official GitHub Actions workflow (e.g. via `act`) before it is relied on for remote execution. | `act` reproduction proof. Ran 2026-07-19 (`act workflow_dispatch -W .github/workflows/readme-agent-run.yml`) — first attempt failed twice (the two real bugs above), third attempt: `Job succeeded`. One genuinely `act`-specific (not production) gap hit and worked around: `upload-artifact` needs `ACTIONS_RUNTIME_TOKEN`, which only a real GitHub-hosted runner provides for free — `act`'s `--artifact-server-path` emulates it locally, now defaulted in `.actrc` so future local runs don't need to rediscover this. | Decision 26; OPS-001 |
| RUN-004 | P0 | PARTIAL | `generate_repo()`'s durable-state fast path MUST NOT skip validation on `facts_hash` equality alone; it MUST also require a content-level fingerprint match, since `facts_hash` deliberately excludes README content (decision #11) and — on the real production topology, where `existing is None` is the normal case, not the exception (`RUN-001`) — was otherwise permanently blind to real upstream content changes once a repo's facts stabilized. | `readme/facts.py::compute_tracked_content_hash()` (new, canonical) gates both `orchestrator.py::_ensure_work_clone`'s local reuse and `generate_repo()`'s `durable_skip` decision via the new `RunStateV1.upstream_content_fingerprint_at_accept` field. Regression test `test_fresh_runner_with_changed_upstream_content_does_not_blindly_skip` (`tests/unit/test_orchestrator.py`) proves a real upstream content edit between two simulated fresh-runner calls is now correctly re-examined and re-rendered rather than blindly trusted from stale accepted state; the existing unchanged-content fresh-runner test still passes unmodified. `PARTIAL` not `IMPLEMENTED` per `GOV-018`: unit-proven only, live re-proof against a real pilot pending explicit user confirmation. | Decision 38; Wave 6 prerequisite fix |

### ECO — Ecosystems, build systems, and package managers

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| ECO-001 | P1 | IMPLEMENTED | A `RepositoryProfile` MUST represent multiple languages, build systems, package managers, and registries per repository, not a single `ecosystem` string. | `tests/unit/test_profile.py::TestBuildProfile::test_synthetic_multi_ecosystem_fixture` + `tests/unit/test_inspection.py::TestFileInventoryManifests::test_synthetic_multi_ecosystem_fixture` — both prove two real, simultaneously-present manifests (pom.xml + pyproject.toml) are represented as a list, not collapsed to one string. | Decision 26/30; Sprint §6.3 |
| ECO-002 | P1 | IMPLEMENTED | Adding a new ecosystem adapter MUST be a new registry entry, following the existing `ecosystems/registry.py` dispatch-table pattern, never a new call site or `if/elif` branch. | Proven with real entries, not just code review: `ecosystems/registry.py`'s `_PARSERS`/`known_manifest_globs()` went from one entry (`"maven"`) to six (`java`/`python`/`net`/`typescript`/`go`/`cpp`) with zero call-site changes outside the registry itself — `tests/unit/test_ecosystems.py::TestEcosystemRegistry`. | Decision 26/30; existing registry-pattern convention |
| ECO-003 | P2 | IMPLEMENTED | Every detected ecosystem/manifest/archetype classification MUST carry confidence and evidence, and unresolved classifications MUST be recorded rather than guessed. | `tests/unit/test_profile.py::TestBuildProfile::test_unresolved_manifest_recorded_not_guessed` (a stray `Cargo.toml` is recorded, not silently dropped) and `::test_low_confidence_when_manifest_found_but_nothing_parsed` (confidence reflects whether extraction actually succeeded, not just file presence). | Decision 26/30; Sprint §6.3 |

### ONB — Autonomous repository discovery and onboarding

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| ONB-001 | P1 | PLANNED | Repository discovery MUST NOT rely solely on fixed repository-name regexes; unknown naming MUST NOT cause silent exclusion. | Discovery-source test with a non-matching-name fixture. | Decision 26; Sprint §7.1 |
| ONB-002 | P0 | PARTIAL | A newly discovered repository MUST default to read-only inspection, profiling, and dry-run proposals; write capability requires separate, explicit authorization. | Negative test: no write call path before authorization. **Structurally true today** — every registered capability (`inspect_repository`, `detect_readme_gaps`, `check_install_path`, `profile_repository`) declares `side_effect_class` `read_only_local`/`read_only_network`; no `local_write`/`remote_write` capability exists yet, so there is nothing to authorize. Not yet met: no dedicated negative test asserting this explicitly (it's currently true by absence, not by a proven gate), and no "newly discovered" onboarding flow exists to default anything (`ONB-001`/`ONB-003`, still `PLANNED`). | Decision 26; Sprint §7.2; Decision #4 |
| ONB-003 | P2 | PLANNED | Onboarding state MUST progress through explicit states (`DISCOVERED` through `WRITE_ELIGIBLE`/`BLOCKED_EXTERNAL`), each independently observable in evidence. | State-machine test. | Decision 26; Sprint §7.3 |

### MEM — Durable state and memory

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| MEM-001 | P0 | IMPLEMENTED | Durable run state (task graph, capability outputs, accepted presentation baseline, repair history, capability gaps) MUST survive a new GitHub Actions runner — no required state may live only in an ephemeral runner filesystem or an unretained workflow artifact. | Cross-runner persistence test (simulated fresh runner). **Built, unit-proven, and live-proven** (Wave 4 + Wave 5): `state/schema.py::SupervisorStateV1` (`RunStateV1.supervisor_state`) now carries real `task_graph_snapshot`/`capability_gaps`/`repair_history` content, written by `supervisor.loop.supervise_repo()` on every converged/blocked run — no longer inert reserved fields. `tests/unit/test_orchestrator.py::TestDurableStateFreshRunner` + `test_supervisor_loop.py::TestDurableConvergence` prove survival against a fake backend. **Live-proven 2026-07-19** (`tests/integration/test_supervisor_live.py::test_live_second_call_converges_durably_with_zero_planning_calls`): a second, independent `GitStateBackend()` instance — the same simulated-fresh-runner shape `test_state_git_backend_live.py` established — correctly reads back the real accepted record from the first live run against the real remote. Mid-run resume (`SCL-003`) remains deliberately out of Wave 5's scope — these are terminal-run-end snapshots only, not a gap in this row's own text. | Decision 26/32; Sprint §10 |
| MEM-002 | P0 | IMPLEMENTED | State updates MUST use a per-repository lease/lock and compare-and-swap against the current upstream revision; a concurrent update MUST yield `STALE_INPUT`, not silent corruption. | Concurrency test with two simulated concurrent runs. `state/backend.py`'s `StateBackend.save()` CAS contract + `acquire_lock()`/`release_lock()`; `tests/unit/test_state_backend.py` proves accept/reject and lock reclaim-after-expiry against a fake backend, including that two *different* repos' writes never falsely conflict — the specific failure mode a reversed first-draft design (one shared branch) would have produced (decision #32). **Live-proven for real** (2026-07-19, `test_state_git_backend_live.py`, 4/4 passed): two racing writers to the same repo yield exactly one `saved`/one `stale`; two different repos' concurrent writes never conflict; a lock is correctly held, then correctly reclaimed after its lease expires. `upstream_revision_at_accept` is a real schema field but not yet populated by any caller (no caller resolves the baseline commit SHA yet) — doesn't block the CAS/lock mechanism itself, which is what this row requires. | Decision 26/32; Sprint §10.3 |
| MEM-003 | P1 | IMPLEMENTED | The state backend MUST be exposed behind a backend-independent interface so the chosen backend can be evaluated and swapped without changing callers. | Interface/contract test with at least one real backend implementation. `state/backend.py`'s `StateBackend` Protocol + two implementations (`state/git_backend.py::GitStateBackend`, the real backend; `tests/unit/test_state_backend.py::FakeStateBackend`, proving the contract offline) — `orchestrator.py` depends only on the Protocol, never on `GitStateBackend` directly. | Decision 26/32; Sprint §10.2 |
| MEM-004 | P0 | PARTIAL | `RunStateV1` MUST support independent per-domain accepted-state tracking (Wave 6+ specialists) without a false-positive CAS collision or a silent clobber between two domains writing the same `org_repo` record in one run. | Schema and helper built and unit-tested against a fake backend: `state/schema.py::DomainStateV1`/`RunStateV1.domain_states`, `state/domain_state.py::save_domain()` — `tests/unit/test_state_schema.py::TestRunStateV1DomainStates`, `tests/unit/test_state_backend.py::TestSaveDomain` (proves two domains never collide and a stale-retry never clobbers a concurrent writer's already-accepted result). **A third producer's clobber found and fixed** (decision #38, 2026-07-19): `orchestrator._record_accepted_state()` built a brand-new `RunStateV1(...)` on every write, silently dropping `domain_states`/`supervisor_state` — live today, not merely forward-looking, since `supervisor_state` is already written by `supervisor/loop.py`. Fixed via `model_copy(update={...})`, regression-tested (`test_record_accepted_state_preserves_domain_states_and_supervisor_state`). **A real domain writer now exists** (2026-07-19, decision #39): `specialists/readme_reconciliation.py`'s `record` node writes `domain_states["readme_reconciliation"]` via `save_domain()` on every `supervise_repo()` call where the coarse freshness check doesn't short-circuit first — `test_specialists.py::TestReadmeReconciliationSpecialist` proves this against a real local git repo and a fake backend. **Live-proven 2026-07-19**: a real `supervise --durable-state` run against `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` recorded a real `domain_states["readme_reconciliation"]` entry (`accepted_status="FIRST_OBSERVATION"`) alongside a real `supervisor_state` write in the *same* durable record on this project's own remote — confirmed by loading the record back afterward — proving decision #38's `_record_accepted_state`/`_record_supervisor_state` coexistence fix holds under a real multi-producer write, not just a fake backend. `PARTIAL` not `IMPLEMENTED` per `GOV-018`: still only one domain writer exists — the *collision-between-two-domains* half of this row's text needs Wave 7's second domain to prove live. | Decision 35/38/39; `plans/investigations/specialist-domain-isolation-production-readiness.md`; Sprint Wave 6 |

### EFF — Effect safety and exactly-once application

Added 2026-07-19 by `plans/investigations/capability-dispatch-production-readiness.md`'s
production-readiness assessment: `MEM-002`'s compare-and-swap covers concurrent conflicting
writers and `VER-003`'s fingerprint cache covers repeated full-run convergence, but neither covers
a `gated_effector` capability whose effect partially lands before an ephemeral GitHub Actions
runner dies mid-job and the same job is retried — a real gap with zero prior requirement coverage.
No `gated_effector` capability exists yet (all four registered capabilities today are
`read_only_local`/`read_only_network`), so this group is accepted and specified ahead of need,
per decision #30 ("prefer proven tools"): before hand-building the idempotency-key ledger these
rows describe, check whether Wave 4's own governed state-backend evaluation (`MEM-003`) already
provides a reusable primitive.

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| EFF-001 | P0 | PARTIAL | Every `gated_effector` capability at `side_effect_class >= local_write` MUST declare `idempotency_inputs` and a reconciliation check ("does this effect already exist?") before it may execute against a real remote. | **Both halves implemented and now live-proven for the mechanism** (Wave 5, `capabilities/effect_ledger.py`): registration-time gate (`registry.py::_build()`, unchanged) plus the real two-phase-apply/reconciliation-refusal execution path (`dispatch_gated_effect()`), proven against a synthetic test effector both offline (`tests/unit/test_effect_ledger.py`) and live 2026-07-19 (`tests/integration/test_effect_ledger_live.py`, real `GitStateBackend`, real disposable ref on this project's own remote — matching this row's own "for a test effector" acceptance framing) — a real reconciliation-*check* hook exists (`GatedDispatchResult`'s `blocked_pending_reconciliation` path) but no capability supplies a real one yet (inherently capability-specific, genuinely Wave 7's job). **Still PARTIAL**: this row's literal subject is "every `gated_effector` capability... before it may execute against a real remote" — no such capability is registered yet (all four registered capabilities are read-only), so the mechanism is proven but the requirement's real subject remains vacuously unmet until Wave 7. | Decision 26/30/34; `capability-dispatch-production-readiness.md`; Sprint Wave 5 (apply/retry mechanism, live-proven); **Wave 7 is the actual blocking dependency** — no `local_write`+ capability may register before this reaches `IMPLEMENTED` |
| EFF-002 | P0 | IMPLEMENTED | A `gated_effector` capability whose process is killed after execution but before evidence-write MUST NOT re-apply its effect on retry with the same idempotency key. | Chaos test: truncate execution after `dispatch_tool_call` returns `outcome="executed"` for a test effector, rerun with the same idempotency key, assert single-application via the effector's own side-effect counter, not just the dispatcher's return value. **Built, unit-proven, and live-proven** (Wave 5): `tests/unit/test_effect_ledger.py::TestDispatchGatedEffectCrashRecovery` deterministically interrupts a synthetic effector *after* its side effect but *before* the ledger flips to `applied`, proves a second attempt does not re-increment the effector's own counter. A structural correction was made before implementation: the original design this row's traceability cites proposed storing the pending/applied intent record in local evidence-dir JSON (`runs/evidence/{run_id}/effect_intents/...`) — exactly the storage Wave 4 built `GitStateBackend` to stop depending on, which would have lost the record on the precise crash scenario this row is about. Corrected to the durable git-backed record (`CapabilityOutputCacheEntry.status`) before any code was written. **Live-proven 2026-07-19** (`tests/integration/test_effect_ledger_live.py::test_crash_between_pending_and_applied_survives_a_fresh_backend_instance`): a real crashing effector against a real `GitStateBackend`, resumed by a genuinely separate second backend instance (no shared in-memory state) — the effector's own counter proves it was not re-executed. | Decision 26; `MEM-002` (concurrent-writer analog); `capability-dispatch-production-readiness.md`; Sprint Wave 5 (live-proven) |
| EFF-003 | P1 | IMPLEMENTED | Retry MUST be structurally inert for any capability at `side_effect_class >= local_write` unless it declares `retry_policy="idempotent_only"`. | Unit test asserting a retry wrapper refuses to retry a `local_write`/`remote_write` manifest whose `retry_policy` is `None` (today's default for every registered capability). **Two independent, defense-in-depth enforcement points, both unit-tested** (Wave 5): `supervisor/repair.py::create_repair_task()` refuses to even *propose* a same-capability retry unless `effect_ledger.retry_is_safe(manifest)` is true (`tests/unit/test_repair.py`); `effect_ledger.dispatch_gated_effect()` independently refuses to re-dispatch *any* capability+arguments with an unresolved `pending` record regardless of `retry_policy` (`tests/unit/test_effect_ledger.py::TestDispatchGatedEffectRetryInertness`) — a strictly stronger backstop, since "did the effect land" is unknown there regardless of what the policy says. This is a deterministic code-path property, not contingent on live network/gateway behavior, so unit proof is the appropriate production-like bar here (`GOVERNANCE.md` rule 10's "matched to what it claims"). | Decision 26; `capability-dispatch-production-readiness.md`; Sprint Wave 5 |

### ORC — Task graph, delegation, and replanning

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| ORC-001 | P0 | IMPLEMENTED | The task graph MUST use explicit task states (`DISCOVERED` through `PASSED`/`FAILED`/`BLOCKED`/`STALE`/`SUPERSEDED`) and MUST reject cycles before execution. | Task-graph validation test; cycle-rejection negative test. `supervisor/task.py::TaskGraph` -- exactly this state set, nothing invented beyond `ORC-001`'s own wording; two independent cycle checks (`add_task()`'s per-edge referential-integrity+cycle rejection, `validate_acyclic()`'s whole-graph three-color DFS gate), both unit-tested for direct and transitive cycles (`tests/unit/test_task_graph.py`). | Decision 26; Sprint §9 |
| ORC-002 | P1 | PARTIAL | A validator failure or new observation MUST be able to trigger a scoped replan that creates repair tasks without discarding already-passed, independent work. | Repair-loop test preserving unrelated passed tasks. **Built and unit-proven** (Wave 5): `supervisor/repair.py::create_repair_task()` + `supervisor/loop.py::_dispatch_and_record()`'s single-auto-repair-attempt composition, proven against the real registry/dispatcher with a monkeypatched flaky capability (`tests/unit/test_supervisor_loop.py::TestRepair`) -- the original bootstrap task's `PASSED` result is untouched by the unrelated repair. "Validator failure" specifically (as opposed to a dispatch/execution failure) is not yet reachable -- no registered capability declares `validators` yet. **Live run completed 2026-07-19** (`test_supervisor_live.py`) but the real `pdf/java` pilot never actually failed, so it exercised the observe→plan→execute loop without ever entering the repair path -- the scoped-replan behavior itself remains proven only at unit level (monkeypatched failure), an honest gap rather than a claimed live proof. | Decision 26; Sprint §16.2 |
| ORC-003 | P1 | PARTIAL | Specialist roles (profiling, facts, presentation, metadata, community files, visuals, releases/packages audit, generated-surface audit, verification, repair planning) MUST be invoked automatically from the task graph, never manually selected. | Role-invocation test per specialist. **The invocation mechanism is real, unit-tested, and live-proven** (Wave 5): `supervisor.loop.supervise_repo()`'s planner turn resolves `capability_id` dynamically from `registry.all_tool_schemas()`/`dispatch_tool_call()`, proven dispatching multiple distinct real capabilities via a fixture planner (`test_supervisor_loop.py`) and, live 2026-07-19, via a real gateway planner against `pdf/java` (`test_supervisor_live.py`) -- no per-role hardcoding anywhere in the loop, in either case. Not yet met: no real specialist *roles* exist to invoke (profiling/facts/presentation/etc. are Wave 7's job); today's "roles" are the four read-only Wave 2/3 capabilities. **Dispatch-concurrency note, not a decided constraint** (2026-07-19): recommend sequential, not parallel, specialist dispatch as Wave 7's default, extending decision #27's existing "one capability per planning turn" caution (parallel tool-calling stays `RESEARCH-GATED`, N=1 evidence per model) to the specialist-fan-out level -- Wave 5's own supervisor already follows this (one capability per planning turn, unconditionally). **A real first specialist now exists, but honestly outside this row's literal "from the task graph" wording** (2026-07-19, decision #39): `specialists/registry.py::all_domains()`/`run_domain()` invokes `readme_reconciliation` automatically (never manually selected, registry-driven — Wave 7 adding a specialist is a registration, not a `supervisor/loop.py` edit), but it runs as a deterministic pre-planning step *before* the task graph starts, not as a task-graph node itself — a distinct, complementary mechanism, not yet literal fulfillment of this row. | Decision 26/39; Sprint §9.2 |
| ORC-004 | P2 | BACKLOG | The two independent orchestration entry points (`orchestrator.generate_repo()`/`run` and `supervisor.loop.supervise_repo()`) each maintain their own "is this repo current" state in separate `RunStateV1` slots (the flat `accepted_facts_hash`/`accepted_status`/`upstream_content_fingerprint_at_accept` fields vs. `supervisor_state`), at different granularities, with no shared source of truth between them. | Traced through concretely during decision #38's production-problem pass and found *bounded* (worst case a redundant planning turn or capability call, since gap-detection is always freshly recomputed on the non-`durable_skip` path) rather than actively harmful, so not merged there. No live evidence of a genuinely harmful divergence exists yet. | Decision 38; found outside the task that surfaced it, logged per decision #29 rather than fixed or silently dropped |

### VER — Verification and autonomous repair

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| VER-001 | P0 | PLANNED | An independent verifier, not the capability that authored a proposal, MUST be the sole authority accepting it before it becomes proposal-ready or applied. | Verifier-independence test (verifier and author are distinct capability invocations). Explicitly Wave 8's job, not Wave 5's -- `supervisor/repair.py::create_repair_task()`'s function-boundary shape is deliberately where a real independent verifier plugs in later, without a rewrite, but no independent verification is built now. | Decision 26; Sprint §16.1 |
| VER-002 | P0 | PARTIAL | A failed verification MUST classify the failure, identify the responsible capability, and create a repair task rather than a manual one-off patch to the output. | Repair-loop classification test. **Built and unit-proven** (Wave 5): `supervisor/repair.py::classify_failure()` (`dispatch_rejected`/`execution_error`/`validation_failed`) + `create_repair_task()`, `tests/unit/test_repair.py`. "Verification" here is today's dispatch-level failure (`DispatchResult.outcome`), not a real independent verifier's judgment (`VER-001`, Wave 8) -- the classification mechanism is real, what it's classifying will broaden later. The live run (`test_supervisor_live.py`, 2026-07-19) never produced a failure to classify against the real `pdf/java` pilot, so this row's live coverage remains zero -- unit proof only. | Decision 26; Sprint §16.2 |
| VER-003 | P1 | IMPLEMENTED | Repeated unchanged runs MUST converge to `NO_CHANGE` — no duplicate proposal, asset, handoff, or unnecessary LLM generation on identical independent inputs. | Fingerprint-cache convergence test (second run). **Built, unit-proven, and live-proven** (Wave 5): `supervisor/convergence.py::is_fresh()` + `RunStateV1.supervisor_state.last_observed_upstream_revision`, a cheap pre-planning freshness check (one clone-HEAD comparison) that skips planning entirely on a match -- `tests/unit/test_supervisor_loop.py::TestDurableConvergence` proves a second call makes zero planning calls, using a planner that raises if ever consulted (a structural assertion, not just behavioral). **Live-proven 2026-07-19** (`tests/integration/test_supervisor_live.py::test_live_second_call_converges_durably_with_zero_planning_calls`): a second real `supervise_repo()` call against the real, unchanged `pdf/java` upstream converged to `CONVERGED_NO_CHANGE` with an empty task graph, using a planner that raises `AssertionError` if ever consulted -- zero LLM calls, the exact acceptance text this row states, proven against real infrastructure not just a fake backend. | Decision 26; Sprint §15 (live-proven 2026-07-19) |

### GAP — Unsupported-capability detection and proposal

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| GAP-001 | P0 | IMPLEMENTED | When no capability satisfies a repository's need, the system MUST create a `CapabilityGap` record with evidence and continue independent supported work rather than silently ignoring the repository. | Negative-control fixture: unsupported ecosystem yields a gap record, not silence. Gap record + evidence built and tested (dispatcher creates a `CapabilityGap` with `evidence={"tool_call": ...}` on an unknown `capability_id` — `tests/unit/test_capability_dispatcher.py`). **"Continue independent supported work" now demonstrated** (Wave 5, the multi-step run this needed to continue *in*): `tests/unit/test_supervisor_loop.py::TestCapabilityGap` seeds an unknown-capability request alongside a real, independent `detect_readme_gaps` request in the same run against the real dispatcher -- the gap is recorded, `BLOCKED`, and the independent branch still reaches `PASSED`, final status `PARTIAL_WITH_CAPABILITY_GAP`. | Decision 26/27; Sprint §3.4 |
| GAP-002 | P1 | IMPLEMENTED | A capability-gap result MUST be distinguishable in evidence (`PARTIAL_WITH_CAPABILITY_GAP`) from a fully supported run. | Final-status enum test. `supervisor/convergence.py::final_status()` returns the exact literal `"PARTIAL_WITH_CAPABILITY_GAP"` string this row names, the first real implementation of the status `capabilities/schema.py::CapabilityGap`'s own docstring said belonged to "whoever owns a 'run' (Wave 5's supervisor)" -- proven together with `GAP-001` above in the same test. | Decision 26; Sprint §21 |
| GAP-003 | P2 | PLANNED | A proposed new capability generated in response to a gap MAY be prepared as a reviewed pull request but MUST NOT execute unreviewed in the same production run. | Negative test: no same-run execution of an unreviewed capability. | Decision 26; Sprint §3.4 |

### SCL — Portfolio scale and failure isolation

| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |
|---|---:|---|---|---|---|
| SCL-001 | P1 | PLANNED | A portfolio-wide run MUST isolate per-repository failures so one blocked or erroring repository does not corrupt or falsely complete another repository's result. | Multi-repository run test with one seeded failure. | Decision 26; NFR-010 |
| SCL-002 | P2 | PLANNED | Concurrency across a portfolio run MUST be bounded and MUST respect model/API rate limits without starving individual repository runs indefinitely. | Bounded-concurrency test under simulated rate-limit pressure. | Decision 26; Sprint §20 |
| SCL-003 | P2 | PLANNED | An interrupted portfolio or per-repository run MUST be resumable from durable state without repeating already-passed, independent work. | Interrupt/resume test. | Decision 26; Sprint §9.4/§10.3 |

## 20. Phase traceability summary

This summary does not replace the detailed requirement rows.

| Master-plan phase | Primary requirement groups |
|---|---|
| Phases 0–15 — completed engine | CORE-001–019, LLM-001–004/007–008, VAL-001–004, SAFE-001–009, NFR-001–004/009/012 |
| Phase 16 — local Actions simulation | OPS-001/003, SAFE-004–005, NFR-004 |
| Phase 17 — adversarial review | LLM-006/011, VAL-017, RDM-021 |
| Phase 18 — durability and monitoring | CORE-023/032, LLM-012, OPS-004–008, SAFE-006/018, INT-007, NFR-011 |
| Phase 19 — broader README corpus | CORE-024, RDM-021 |
| Phase 20 — research and requirements controls | GOV-009, RDM-019, OWN-014, MET-001/002/006, DOC-003–007 |
| Phase 21 — product-first README | BIZ-002/006/007, OWN-011, RDM-001–012/014–022, VAL-005–007/014–015 |
| Phase 22 — settings and audit-only surfaces | OWN-003/006/012–015, SURF-001–005/014–015, VAL-008–011, SAFE-010/013/015 |
| Phase 23 — community files | SURF-006–009, VAL-012 |
| Phase 24 — visuals | RDM-017, SURF-010–013, VAL-013, SAFE-016 |
| Phase 25 — product-agent integration and drift | FACT-006/008/010, INT-001–010, SAFE-012, RDM-020 |
| Phase 26 — pilot acceptance and rollout | BIZ-006, PIL-001–010, VAL-016, MET-003–004/007 |
| Sprint Waves 1–9 — autonomous capability-driven runtime | AGT-*, CAP-*, RUN-*, ECO-*, ONB-*, MEM-*, EFF-*, ORC-*, VER-*, GAP-*, SCL-* (see §19) |

## 21. Decision-ledger coverage

| Decision | Covered by requirements |
|---|---|
| 1 | CORE-001, CORE-010 |
| 2 | CORE-002 |
| 3 | GOV-013 |
| 4 | CORE-003–004/032, SAFE-003, OPS-007 |
| 5 | CORE-007 |
| 6 | LLM-004, VAL-002 |
| 7 | CORE-009, RDM-013 |
| 8 | LLM-001–006/009–010, SURF-001 |
| 9 | BIZ-001/003, RDM-001–004/011–014 |
| 10 | CORE-005–006, PIL-001 |
| 11 | CORE-011 |
| 12 | CORE-012, NFR-002 |
| 13 | CORE-001/010 |
| 14 | CORE-013/019, NFR-009 |
| 15 | CORE-014 |
| 16 | CORE-015–017, VAL-001 |
| 17 | BIZ-001/003, RDM-002/010–012, VAL-006 |
| 18 | OWN-009–011, FACT-001–010, BIZ-006–007 |
| 19 | OWN-001–015, SURF-004/008–015, VAL-008–013 |
| 20 | BIZ-004–005, MET-001–008 |
| 21 | INT-001–009, RDM-020, SAFE-012 |
| 22 | FACT-001–010, LLM-005–006, VAL-007/015 |
| 23 | RDM-017, SURF-010–013, VAL-013 |
| 24 | BIZ-006, PIL-001–011, VAL-016 |
| 25 | GOV-001–012, DOC-001–002/009–010 |
| 26 | NFR-013 (doctrine, revised 2026-07-18); generated: LLM-001–006, NFR-001–003/012, VAL-001–004; new capability-driven groups (§19): AGT-*, CAP-*, RUN-*, ECO-*, ONB-*, MEM-*, ORC-*, VER-*, GAP-*, SCL-*; 2026-07-19 doctrine-enforcement review: `NFR-012` reworded to remove the residual anti-usage reading, new `LLM-015` (usage-tracking forcing function), `BACKLOG` rows `LLM-016`/`GOV-016` (later `IMPLEMENTED`, same day); 2026-07-19 capability-dispatch production-readiness assessment: new `EFF-*` group (exactly-once effect application — zero prior requirement covered a `gated_effector` capability's crash-then-retry safety) and a corrected `RESEARCH-GATED`-pending caveat on the `gpt-oss` parallel-tool-calling finding (`plans/investigations/llm-gateway-characterization.md` L7, previously overstated on N=1 evidence) |
| 27 | AGT-002 (PARTIAL, Wave 1 spike evidence); ORC-001 (target state model this decision must map onto, still PLANNED) |
| 28 | No requirement ID directly covers GitHub API client-library choice; traceable to the general minimal-dependency posture demonstrated across CORE-*/OPS-* rather than one specific ID |
| 29 | GOV-014 |
| 30 | GOV-015; ECO-001–003 (IMPLEMENTED, first real application: aspose.org-adapted ecosystem parsers) |
| 31 | GOV-017 |
| 32 | *(gap — see `GOV-019` BACKLOG row)* |
| 33 | GOV-018 |
| 34 | CAP-006 |
| 35 | MEM-004 |

## 22. Open research questions

These are controlled uncertainties, not permission to guess:

1. **Resolved (2026-07-18).** Measurable presentation criteria for different FOSS product types,
   without a common template, are defined in `docs/presentation-standard.md` (ten dimensions,
   three differentiated reference patterns, a ten-point Phase-21 review checklist).
2. **Resolved (2026-07-18).** The complete GitHub surface control matrix — which surfaces are
   API-writeable, settings-only, manually controlled, or generated — is verified per-surface in
   `docs/github-surface-control.md`.
3. Is the ≥10 visitors/week target feasible from the pilot and eventual 25-repository portfolio,
   and over what observation period? Still open — requires aspose.org referral-report and GitHub
   Traffic API access not available in this environment.
4. What is the exact versioned product-facts/change-handoff schema? Still open — a separate
   schema-freeze deliverable (`DOC-006`), not addressed by the presentation-standard or
   surface-control research.
5. Should historical evidence validation become fully offline and independent from the current
   work clone? This remains an explicitly documented design item.

## 23. Changelog

- **2026-07-18 — initial requirements baseline.** Created the first complete normative requirement
  register from the preserved 2026-07-17 implementation plan and the 2026-07-18 product-first,
  ownership, GitHub-control, pilot, drift-protection, and measurement discussion. Added permanent
  IDs, statuses, priorities, acceptance evidence, decision/phase traceability, and bidirectional
  document-control requirements. No completed Phase 0–15 behavior was reclassified as planned.
- **2026-07-18 — registry auto-discovery implemented (Phase 18 slice).** CORE-023 and OPS-005
  moved `PLANNED` → `IMPLEMENTED` and their text corrected to the live GitHub-API scan actually
  built (`data/families.json` + `scripts/update_products_registry.py`), replacing the
  local-aspose.org-checkout approach originally planned; CORE-023's wording bug ("without
  mutating upstream-shaped fields", which contradicts syncing from upstream) fixed to the
  intended meaning (agent-owned fields). Added CORE-032, OPS-007, OPS-008 for the safety
  guarantees this build depends on: new entries always land `disabled`, `families.json` grants no
  allow-list permission, and the workflow only ever proposes a PR.
- **2026-07-18 — agentic–deterministic doctrine.** Added NFR-013 (P0, GOVERNANCE): the system is
  a deliberate blend of deterministic core and narrow agentic edge — deterministic by default,
  LLM only where judgment cannot be a rule, always behind deterministic pre/post gates. Added
  decision-coverage row 26; user directive, recorded as Decision 26 in `master.md`.
- **2026-07-18 — Phase 20 presentation/control research delivered.** DOC-003, DOC-004, DOC-005,
  and RDM-019 moved `RESEARCH-GATED` → `IMPLEMENTED` on delivery of `docs/presentation-standard.md`
  and `docs/github-surface-control.md`, evidenced by a live 25-repository registry survey and a
  six-repository leading-FOSS/dual-license benchmark (n8n, NuGet Aspose.Cells, iText, EPPlus,
  SheetJS, Apache PDFBox). Open research questions 1–2 marked resolved with pointers to the new
  docs. DOC-006/DOC-007/BIZ-004/MET-001/002/006 remain `RESEARCH-GATED`/`PLANNED` — unaddressed by
  this delivery, DOC-007's traffic study specifically blocked on analytics access this environment
  does not have. See `master.md`'s matching Changelog entry and Reference Data subsections.
- **2026-07-18 — Phase 21a–21d built; requirement statuses sharpened to match.** Moved to
  `IMPLEMENTED` with evidence naming the actual module/rule/test: RDM-001 (callout retirement,
  including a new `TestCalloutMigration` orchestrator test proving the migration write survives
  the skip path — the exact scenario a real pre-Phase-21 work clone hits), RDM-002 and VAL-006
  (`product_first_opening`, `commercial_mention_discipline`, both ERROR), RDM-005 and RDM-010
  and RDM-014 (presentation-report/validator mechanisms). Moved to `PARTIAL` (mechanism exists,
  narrower than the full requirement text, or real-pilot confirmation still pending): VAL-005,
  BIZ-002, RDM-006, RDM-007 — each row's acceptance evidence now states exactly what is and isn't
  covered, per the explicit dimension-to-phase boundary in `master.md` (license recognition,
  visual usefulness, and no-fact-lost drift protection are Phases 23/24/25, not 21). OWN-011's
  traceability sharpened to name Phase 21e specifically (deferred, design-only — needs
  `change_boundary`'s contract to evolve first). No row was marked `IMPLEMENTED` without
  objective test evidence (`GOV-007`); rows whose acceptance text names a real-pilot or human
  review step not yet performed were kept at `PARTIAL`, not `IMPLEMENTED`, even where the
  underlying mechanism is fully built and unit-tested. User directive: "design phase 21 and sync
  the plan" — see `master.md`'s matching Changelog entry for the full build record.
- **2026-07-18 — Live pilot re-proof: two real orchestrator bugs found and fixed; RDM-001/007,
  CORE-015–017, BIZ-002 evidence updated to match.** Re-running all three real pilots against
  the Phase 21a–21d code (not synthetic fixtures) surfaced two genuine, pre-existing
  `orchestrator.py` defects — a re-render could silently drop previously-rendered org/com links,
  and a legitimate force-regenerate could spuriously fail its own idempotency check. Both fixed,
  each with a regression test proven to fail pre-fix and pass post-fix. RDM-001 and CORE-015–017
  evidence updated to cite the fix and the live confirmation (`pdf/java`'s real, pre-existing
  legacy callout span was migrated away cleanly). RDM-007 and BIZ-002 evidence updated with the
  live `--check-install` results: all three enabled pilots' Maven coordinates are zero-result,
  correcting the earlier finding that this was unique to `cells-java`. See `master.md`'s matching
  Changelog entry for full detail and evidence run IDs.
- **2026-07-18 — Wave 0 of the autonomous-repository-presenter reset
  (`AUTONOMOUS-REPOSITORY-PRESENTER-RESET-001`).** `NFR-013` rewritten in place to mirror
  `master.md` decision #26's corrected doctrine (autonomous capability-driven control plane, LLM
  plans/coordinates/repairs, deterministic tools own facts/mutations/validation/evidence/rollback)
  — same requirement ID, traceability unchanged (`Decision 26`). Added new §19 "Autonomous runtime
  and capability requirements" with ten new ID groups (`AGT-*`, `CAP-*`, `RUN-*`, `ECO-*`,
  `ONB-*`, `MEM-*`, `ORC-*`, `VER-*`, `GAP-*`, `SCL-*`), 32 rows total, all `PLANNED` per
  `GOV-007` — a lean starter set, sharpened incrementally as each sprint wave actually lands, not
  a complete specification of the target system. Renumbered the trailing structural sections
  (Phase traceability summary → §20, Decision-ledger coverage → §21, Open research questions →
  §22, this Changelog → §23) to make room; no requirement ID was renumbered or reused (`GOV-002`).
  Decision-ledger coverage row 26 updated to list the new groups. See `master.md`'s matching
  Changelog entry for the full Wave-0 scope, what was verified before starting (no existing
  "select a skill" requirement to remove; `llm-gateway-characterization.md` already
  evidence-backs the model-routing claim in decision #26(e)), and what remains explicitly out of
  scope for later waves.
- **2026-07-18 — Wave 1: gateway tool-calling spike, runtime framework decision, one proven loop
  iteration.** `AGT-002` moved `PLANNED` → `PARTIAL` — see its row in §19 for the evidence
  pointer (`plans/investigations/agentic-loop-proof.md`, live 4-round loop against the real
  `pdf/java` pilot). New decision-ledger row added: §21 now lists decision 27 (runtime
  task-graph/dispatcher choice — extend the orchestrator, no new agent framework; native
  tool-calling as the structured-action mechanism), traceable to `AGT-002`, `ORC-001`. No other
  `AGT-*`/`CAP-*`/`RUN-*`/`ECO-*`/`ONB-*`/`MEM-*`/`ORC-*`/`VER-*`/`GAP-*`/`SCL-*` row changed —
  `CAP-004`'s execution-type enum and `ORC-001`'s state-machine requirement remain `PLANNED`,
  unaffected by this wave's spike-only scope. See `master.md`'s matching Changelog entry and the
  three new investigation docs (`llm-gateway-characterization.md` findings L6–L8,
  `runtime-framework-evaluation.md`, `agentic-loop-proof.md`) for full detail.
- **2026-07-18 — Wave 2: capability foundation, first real production capability code.**
  `CAP-003`/`CAP-004` moved `PLANNED` → `IMPLEMENTED`; `CAP-001`/`CAP-002`/`GAP-001` moved
  `PLANNED` → `PARTIAL` (mechanism built and tested, full coverage/supervisor-integration
  clauses genuinely not yet true — see each row's evidence text in §19 for exactly what is and
  isn't met). `GAP-002`/`GAP-003` and the rest of §19 (`RUN-*`/`ECO-*`/`ONB-*`/`MEM-*`/
  `ORC-*`/`VER-*`/`SCL-*`) remain `PLANNED`, unaffected. No new decision-ledger row — Wave 2
  executes what decisions #26/#27 already decided; both rows' traceability in §19 now read
  "Decision 26/27" instead of "Decision 26" alone where Wave 2 work traces to the runtime-choice
  decision as well as the doctrine one. See `master.md`'s matching Changelog entry for the full
  build record: `src/readme_agent/capabilities/` (schema, registry, dispatcher, three read-only
  capabilities), 22 new offline unit tests, one live integration test proving the production
  registry/dispatcher — not a spike script — against the real gateway and pilot repository.
- **2026-07-19 — New requirement `PIL-011`, decision 24 clarified in `master.md` (no
  renumbering).** Research/development tasks MUST cover every `data/products.json` entry with
  equal precedence regardless of `mode`; end-to-end execution stays scoped to the three enabled
  Java pilots (`PIL-001`) solely because they are the only non-`disabled` entries today. §21
  decision-24 coverage row updated to include `PIL-011`. No other row changed.
- **2026-07-19 — Response to an independent review conducted before Wave 3.** No requirement
  status changes — this response strengthened evidence and closed implementation gaps without
  completing or newly satisfying any acceptance criterion. §21 decision-ledger coverage: new row
  for decision 28 (GitHub API library choice — no requirement currently covers this narrowly;
  traceable to the general minimal-dependency posture, not a specific ID). `AGT-002`/`CAP-001`'s
  `PARTIAL` status and evidence text are unchanged in wording but now have additional supporting
  evidence at `plans/investigations/capability-dispatch-robustness.md` (18 further live dispatch
  trials, zero failures) — not cited as new acceptance evidence since neither row's *unmet*
  clauses (full operation coverage, repository-profile filtering, run-continuation-after-gap)
  became true; this is depth of confidence in what was already claimed, not new scope met. See
  `master.md`'s matching Changelog entry for the full response (decision #28, a real rate-limit
  handling gap found and fixed in `scripts/update_products_registry.py`, and the robustness
  campaign itself).
- **2026-07-19 — Backlog discipline (decision 29).** Added `BACKLOG` to the requirement-status
  vocabulary (§2) and new requirement `GOV-014`: an agent that finds a non-blocking issue outside
  its current task MUST log it as an open `BACKLOG` requirement row instead of scope-creeping into
  an unrequested fix or silently dropping it; a blocking issue MUST be fixed before the task is
  done. §21 decision-ledger coverage: new row for decision 29 → `GOV-014`. `AGENTS.md` carries the
  working-rule summary. User directive.
- **2026-07-19 — Wave 3: `ECO-001`/`ECO-002`/`ECO-003` → `IMPLEMENTED`; `ONB-002` → `PARTIAL`;
  new `GOV-015`; new `BACKLOG` row `VAL-018`.** `GOV-015` (decision 30, `GOVERNANCE.md` rule 8):
  prefer a proven source over hand-rolled new logic before writing new parsing/protocol code.
  `ECO-001`–`003` move to `IMPLEMENTED` with real evidence (not design intent): a generalized
  `FileInventory.manifest_paths` and six real `ecosystems/*.py` platform parsers, adapted from
  aspose.org's actual production `package_manifest.py` rather than written from scratch — see
  `master.md`'s matching Changelog entry for the full build record, including two real bugs
  caught and fixed before shipping (`ecosystems/resolver.py`'s stale `"maven"` dispatch key; the
  live-test target originally planned violated decision #4's allow-list and was corrected).
  `ONB-002` moves `PLANNED` → `PARTIAL`: structurally true (every capability is read-only, no
  write capability exists), but not yet proven by a dedicated negative test, and `ONB-001`/
  `ONB-003` remain `PLANNED` untouched. New `BACKLOG` row `VAL-018` (§12): the
  `validation/rules/prominence.py` render-then-rerun bug found during Wave 2's verification pass
  was reported in chat and deferred by direct user instruction, but per decision 29/`GOV-014`
  (already in force) should have been logged as a `BACKLOG` row at the time and wasn't — corrected
  here, not a new finding. §21 decision-ledger coverage: new row for decision 30.
- **2026-07-19 — Reconciled `NFR-012` with the Decision #26 doctrine; new `LLM-015`/`LLM-016`;
  new `BACKLOG` row `GOV-016`.** User-directed root-cause review of why agentic/LLM-driven work
  keeps deferring found that `NFR-012` ("SHOULD minimize LLM calls... wherever possible") was
  never updated when `NFR-013` was rewritten during Wave 0's doctrine correction, leaving a live,
  `PLANNED` requirement that directly contradicted the corrected doctrine (Decision 8's own prose
  already says it's "no longer the ceiling on future LLM jobs," but the requirement row citing it
  was untouched). `NFR-012` reworded in place: scoped to *redundant* calls only (idempotency,
  `NFR-001`), explicit that it MUST NOT be read as minimizing legitimate judgment/planning/
  coordination usage; traceability now cites Decision 8 and 26. New `LLM-015` (P2, `PLANNED`):
  every run's evidence/report MUST record LLM gateway call count and triggering job/capability, so
  usage is auditable rather than silently minimized — the forcing function requested by the
  sponsor (gateway calls are free; usage should be visible in metrics, not avoided). Two `BACKLOG`
  rows logged per `GOV-014` from the same review, not fixed inline (non-blocking to the
  assessment task): `LLM-016` — `env.py:6`'s `DEFAULT_LLM_MODEL="gpt-oss"` default contradicts
  `llm-gateway-characterization.md`'s own finding that `gpt-oss` is unreliable (1/10) for the
  freeform job it's used for; `GOV-016` — `llm/prompts.py`'s prompt is still inline, grandfathered
  against the `prompts/`-only rule. §21 decision-ledger coverage: new row for this review under
  decision 26 (doctrine enforcement, not a new decision). User directive.
- **2026-07-19 — Investigate before overwriting (decision 31).** New requirement `GOV-017`: an
  agent (human or AI) MUST investigate the current content and recent history of a file, Decision
  Ledger entry, requirement row, evidence artifact, or git state before overwriting, replacing,
  deleting, or discarding it, and MUST preserve, migrate, or pause for user input rather than
  silently clobber it when that investigation shows the content matters. Generalizes disciplines
  that already existed narrowly (`GOV-002`/`GOV-003`'s no-silent-deletion for the Decision Ledger
  and requirements, the fixtures immutable-snapshot rule, `GOVERNANCE.md`'s no-orphan-artifacts
  rule) into one rule covering every artifact class. §21 decision-ledger coverage: new row for
  decision 31 → `GOV-017`. `AGENTS.md` carries the working-rule summary. User directive.
- **2026-07-19 — Wave 3 hardening: no status changes, deepened evidence for `ECO-001`–`003`.**
  A full-registry (25 real repos, all modes) survey found and fixed a real crash
  (`ecosystems/python.py`) and a systemic detection gap (`inspection/file_inventory.py` missed
  every non-root-level manifest — affected 100% of the registry's `.NET` entries). Not cited as
  newly satisfying any unmet clause of `ECO-001`–`003` (all three were already `IMPLEMENTED` on
  synthetic-fixture evidence) — this is depth of confidence against real data, the same
  distinction drawn for the pre-Wave-3 robustness campaign. See `master.md`'s matching Changelog
  entry and `plans/investigations/full-registry-ecosystem-detection-survey.md` for the full
  record, including the one honestly-still-open item (large-repo profiling latency, not fixed
  this pass).
- **2026-07-19 — `LLM-015`/`LLM-016`/`GOV-016` → `IMPLEMENTED`.** Closes out the doctrine-
  enforcement review logged earlier the same day. `LLM-016`: `env.py` gained `JOB_MODEL_ROUTING`
  and `llm_model_for_job()` (`LLM_MODEL` env override > per-job table > `DEFAULT_LLM_MODEL`);
  `relationship_explained` now routes to `qwen3-next`, and the bare fallback default changed from
  `gpt-oss` to `qwen3-next` too, since Decision 26(e) prefers it for instruction-critical/
  structured work generally. `orchestrator.py`'s `LiveLLMClient` construction now calls
  `env.llm_model_for_job("relationship_explained")` instead of the flat `env.llm_model()`.
  `GOV-016`: the prompt migrated to `prompts/relationship_explained/{system,user}.txt`
  (`string.Template` substitution, not `.format()`, since the response-shape example contains
  literal JSON braces); `llm/prompts.py::prompt_content_hash()` hashes the loaded assets and a new
  `RepositoryFacts.prompt_content_hash` field joins `facts_hash` (`readme/facts.py::_HASH_FIELDS`)
  so an edited prompt file forces regeneration automatically, per `prompts/README.md` rule 3 --
  the mechanism the migration note promised but the embedded-string version couldn't provide.
  `GENERATION_SCHEMA_VERSION` bumped `3`→`4` (a real `build_prompt()` implementation change, not
  cosmetic) and `tests/fixtures/generation_schema_version_snapshot.json` regenerated after `ruff
  format` settled the final byte content. `LLM-015`: `evidence/writer.py::write_evidence()` gained
  a required `llm_calls: list[str]` parameter, written into `manifest.json` as
  `llm_call_count`/`llm_calls` -- surfaced for free by the existing `readme-agent report <run_id>`
  command, no new report code needed. `GenerateResult` gained `llm_calls` alongside the existing
  `llm_called` bool; `cmd_generate`'s stdout print extended to show it. Per direct user
  confirmation, this stays tracking-only -- no hard minimum-usage gate added to any wave. New
  tests: `tests/unit/test_env.py`, `tests/unit/test_llm_prompts.py`; extended
  `tests/unit/test_readme_facts.py`, `tests/unit/test_prompt_hash_coupling.py`,
  `tests/unit/test_evidence_writer.py`, `tests/unit/test_orchestrator.py`,
  `tests/unit/test_preflight.py` (two assertions flipped from `gpt-oss` to the new
  `qwen3-next` default), `tests/security/test_no_secrets_in_evidence.py` (fixture project root
  now materializes `prompts/relationship_explained/` alongside `config/policies/`, matching the
  existing cwd-relative-config test pattern). Full suite: `ruff check .`, `ruff format --check .`,
  `mypy src` clean (296 tests passed, 7 deselected, up from 286/7 pre-review). User directive.
- **2026-07-19 — Capability-dispatch production-readiness assessment: new `EFF-*` group; corrected
  an overstated finding.** New `plans/investigations/capability-dispatch-production-readiness.md`
  root-causes what would break consistency across reruns in the (not yet wired in) capability
  dispatcher: no retry/idempotency logic exists on the tool-calling path, and no requirement
  covered a `gated_effector` capability's crash-then-retry safety (`MEM-002` covers concurrent
  writers, `VER-003` covers full-run convergence, neither covers a partial effect from a killed
  runner). New `EFF-001`/`002`/`003` (§19), `PLANNED`, grounded in `CapabilityManifest`'s existing
  `idempotency_inputs`/`retry_policy`/`side_effect_class` fields (`schema.py`'s own docstring
  already reserved these for Wave 5). Separately, direct re-inspection of
  `probe_llm_gateway.py:366-399` found the "`gpt-oss` drops one of two parallel tool calls" finding
  (`llm-gateway-characterization.md` L7) rests on a single trial per model, not a repeated-trial
  result — corrected in place to `RESEARCH-GATED` pending an N≥10/≥2-session follow-up; no current
  decision depended on the original wording. No capability at `side_effect_class >= local_write`
  exists yet, so `EFF-*` is accepted ahead of need per decision #30 — implementation should first
  check whether Wave 4's state-backend evaluation (`MEM-003`) provides a reusable idempotency
  primitive. §21 decision-ledger coverage: new entries under decision 26. User directive.
- **2026-07-19 — Wave 4: durable runner state.** `RUN-001`/`MEM-001`/`MEM-002` → `PARTIAL`,
  `MEM-003` → `IMPLEMENTED` (decision #32). Re-checked the `we-are-not-as-piped-naur.md`
  remediation and the just-executed `capability-dispatch-production-readiness.md` plan
  immediately before designing, per this session's own repeated finding that concurrent work
  lands mid-task: confirmed steps 1/2/4/5 of the former are done (`env.py`'s
  `DEFAULT_LLM_MODEL="qwen3-next"`, `prompts/relationship_explained/` migrated, `LLM-015`'s
  `llm_calls` evidence field shipped) and only step 6 remains, logged as new `BACKLOG` row
  `CAP-005` rather than silently dropped; confirmed the new `EFF-001`/`002` group names this
  wave's `MEM-003` evaluation directly and designed `state/schema.py`'s
  `CapabilityOutputCacheEntry.fingerprint` to double as `EFF-001`'s idempotency key for Wave 5 to
  reuse. A first backend draft (one shared git branch holding every repo's state as separate
  files) was reassessed and reversed before implementation: git's non-fast-forward CAS is scoped
  to the whole ref, not a path inside it, so two *unrelated* repos' writes would have falsely
  conflicted — reversed to one dedicated git ref per `org_repo`
  (`refs/readme-agent-state/{org}__{repo}`), matching `MEM-002`'s actual per-repository
  concurrency unit (decision #32). Implemented: `state/schema.py`, `state/backend.py`
  (`StateBackend` Protocol), `state/git_backend.py` (`GitStateBackend` — git plumbing only, no
  per-write working-tree checkout), wired into `orchestrator.generate_repo()` additively
  (`state_backend` param, `None` by default — every existing caller/test unaffected), opt-in via
  new CLI `--durable-state` flag (mirrors `--check-install`'s never-a-default convention);
  `readme-agent-run.yml` gained job-level `contents: write` and passes the flag. New tests:
  `tests/unit/test_state_schema.py`, `tests/unit/test_state_backend.py` (fake backend proves the
  CAS/lock contract, including the cross-repo-no-false-conflict property directly),
  `tests/unit/test_orchestrator.py::TestDurableStateFreshRunner` (two independent runner working
  directories sharing one durable backend — the concrete regression test for `RUN-001`),
  `tests/integration/test_state_git_backend_live.py` (`@pytest.mark.live`, written, not yet run —
  needs explicit confirmation before pushing to this project's own remote, so `RUN-001`/`MEM-001`/
  `MEM-002` stay `PARTIAL` rather than `IMPLEMENTED` until it has). User directive.
- **2026-07-19 — Wave 4 live proof run: real bug found and fixed; `MEM-002` → `IMPLEMENTED`.**
  User confirmed running the live git-backend test against this project's own remote. First run:
  1/4 passed — `save()`/`load()` round-tripped, but every test touching `mktree`
  (`test_two_writers_racing_...`, `test_lock_acquire_release_and_reclaim_...`) failed with `path
  'state.json' does not exist`. Root-caused directly, not guessed: `git ls-tree` on the pushed
  commit showed the stored path as `"state.json\r"` — Python's `subprocess.run(text=True,
  input=...)` applies universal-newlines translation on the *write* side too, silently turning
  every `\n` in `git_backend.py`'s `mktree` input into `os.linesep` (`\r\n` on Windows) before it
  reached git, corrupting the tree entry itself. Fixed in `gitsafety/_git.py::run_git()`: when
  `input_text` is given, stdin is now piped as raw UTF-8 bytes (bypassing `text=True`'s stdin
  encoding entirely), stdout/stderr still decoded as text for every caller — a real Windows-only
  bug no offline/fixture test could have caught, exactly why this project's own convention is to
  actually run the live test rather than trust the unit-tested mock. Second run: 3/4 passed; the
  4th (`test_lock_acquire_release_and_reclaim_after_lease_expiry`) failed for an unrelated reason
  — a 1-second lease patched into the test was shorter than the real network round-trip time of a
  single `acquire_lock()` call (~2-5s observed), so the "held, not expired" assertion raced its
  own second call's fetch/push latency. Not a backend bug — widened the test's patched lease to 8s
  (safely longer than one observed round-trip) and the sleep accordingly; third run: 4/4 passed.
  Full suite reconfirmed clean (`ruff check .`, `ruff format --check .`, `mypy src`, `pytest -q` →
  312 passed unchanged). Local push auth used a temporary, repo-scoped
  `http.https://github.com/.extraheader` built from the already-present `GH_TOKEN` (Git Credential
  Manager's own interactive flow hangs non-interactively) — removed again immediately after,
  confirmed via `git config --local --get` returning nothing. No stray `refs/readme-agent-state/*`
  refs left on `origin` at any point (each test's own `finally` cleanup ran even on failure,
  confirmed via `git ls-remote`). `MEM-002` → `IMPLEMENTED`; `RUN-001`/`MEM-001` stay `PARTIAL` —
  the backend is now live-proven, but no *actual* GitHub Actions runner run has been observed
  (`RUN-003`'s `act` reproduction is the remaining gap, still `PLANNED`). User directive.
- **2026-07-19 — RUN-003 closed via a real `act` reproduction; two real bugs found and fixed;
  `RUN-001` → `IMPLEMENTED`.** User asked to prove Wave 4 both in isolation and in the pipeline,
  then specifically to attempt `RUN-003` (the one remaining `RUN-001` gap). Selected the real
  blank-slate pilot `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` (`--mode dry_run`, never
  pushes). Pipeline-level A/B/C proof first, all via the real CLI and real LLM gateway: (A) clean
  slate + `--durable-state` — 1 real LLM call, establishes accepted durable state; (B) `runs/`
  wiped (byte-for-byte fresh-runner simulation) + `--durable-state` — 0 LLM calls, confirmed the
  local work clone carried zero markers and its last commit was the original upstream commit, not
  either prior generated commit; (C) same wipe, no `--durable-state` (counterfactual) — 1 LLM call
  again, reproducing the exact pre-Wave-4 defect on demand. Real LLM output inspected for quality
  (not just call counts, per user request): all 10 validators passed, no hallucinated claims.
  Then `RUN-003` itself: `act workflow_dispatch -W .github/workflows/readme-agent-run.yml` against
  Docker Desktop. First run failed — `act`'s checkout uses `docker cp` of the actual local working
  tree (confirmed: container `git log` showed local HEAD `4adbaaf`, not stale `origin/main`, which
  is still at the bare initial commit), so the real Wave 4 code executed and correctly recognized
  the pre-existing durable state (fresh work clone, zero LLM calls, confirmed by inspecting the
  still-running container directly) — but the durable-state *write-back* then failed:
  `fatal: could not read Username for 'https://github.com'`. Root-caused by direct inspection of
  the container's git config: `actions/checkout@v4`'s `persist-credentials` did not set
  `http.extraheader` under `act`'s local-copy checkout path (confirmed absent via
  `git config --local --get`). This exposed a real, independent-of-`act` robustness gap: the
  write-back was uncaught, so a credential/network failure on the durable-state push aborted the
  *entire* run and lost the evidence bundle for generation/validation work that had already
  succeeded. Fixed: `orchestrator.py`'s durable-state read and `_record_accepted_state`'s
  write-back are now both best-effort (`try`/`except StateBackendError`, warn to stderr, never
  raise) — mirrors `inspect_repo`'s `check_install` "opt-in enhancement never fails the command"
  convention already established elsewhere in this codebase. New regression test:
  `test_orchestrator.py::TestDurableStateFreshRunner::test_unreachable_state_backend_does_not_abort_the_run`
  (a backend that raises on every call must not stop `generate_repo()` from succeeding and writing
  evidence). Second `act` run (after the fix): the CLI step succeeded with the warning printed as
  designed, but `upload-artifact` then failed with an invalid artifact name — `readme-agent-run.yml`
  used `inputs.repo_key` ("org/repo") directly as the artifact name, which the GitHub Actions API
  rejects (`/` is invalid) — a real, pre-existing bug unrelated to Wave 4, only surfaced because
  this was the first time this workflow had ever actually been run. Fixed with a small shell step
  sanitizing to this project's own `{org}__{repo}` convention. Third `act` run: `Job succeeded`,
  end to end. One purely `act`-specific (not production) gap hit along the way and worked around,
  not coded around: `upload-artifact` needs `ACTIONS_RUNTIME_TOKEN`, which only a genuine
  GitHub-hosted runner provides — `act --artifact-server-path` emulates it locally, now defaulted
  in `.actrc`. `RUN-001`/`RUN-003` → `IMPLEMENTED`. Full suite re-clean: `ruff check .`, `ruff
  format --check .`, `mypy src`, `pytest -q` → 313 passed (up from 312), 11 deselected, unchanged.
  User directive.
- **2026-07-19 — Specialist domain-isolation, root-caused as a production problem ahead of Wave
  6-8.** New `CAP-006`/`MEM-004` (both P0, `PARTIAL` per `GOV-018` — mechanism built and
  unit-tested; real-domain population and a live multi-specialist proof are Wave 6's job).
  `EFF-001` `PLANNED` → `PARTIAL` (registration-time gate implemented; traceability retargeted to
  name Wave 7, not just "Wave 5", as the actual blocking dependency). `AGT-002` evidence text
  extended to state its N=1 evidence covers a single planner only; new `AGT-005` (`BACKLOG`) logs
  the resulting multi-specialist reliability evidence gap. `OWN-011` evidence text extended with
  the multi-specialist surface-collision risk (deliberately not designed — Wave 7's specialist list
  doesn't exist yet). `ORC-003` gets a dispatch-concurrency note (sequential recommended,
  extending decision #27's caution — not decided, no supervisor exists yet). §21 Decision-ledger
  coverage gains rows for decisions 34 (`CAP-006`) and 35 (`MEM-004`). Full reasoning and the
  authorization-library/state-coordination tool evaluations behind the `PARTIAL`-not-hand-waved
  verdicts: `plans/investigations/specialist-domain-isolation-production-readiness.md`. See
  `master.md`'s matching Changelog entry for the code shipped in the same pass. User directive.
- **2026-07-19 — Live-test push-credential hang found and worked around; new `OPS-009` (`BACKLOG`).**
  While live-verifying the above pass, `git push` inside `test_state_git_backend_live.py` hung
  silently for ~35 minutes with zero output before being diagnosed: `GH_TOKEN` being present in the
  environment does not by itself wire git's push authentication, and the hang sits inside git's own
  credential resolution, outside both `run_git()`'s 120s subprocess timeout and pytest's own
  reporting. Root-caused via a bounded, reproducible probe (`git push` under a hard shell timeout,
  silent no-output failure) and fixed for this session with a temporary
  `http.https://github.com/.extraheader` built from `GH_TOKEN`, removed immediately after; all 8
  live tests then passed (4 already had, before the git-backend file; 4 more after the fix). Not a
  CI gap — `actions/checkout` wires the runner token automatically, which is why `RUN-003`'s `act`
  reproduction never hit this. Documented as a prerequisite directly in the test file's own
  docstring; `OPS-009` logs that no scripted/automatic fix exists yet (per Decision 29, found outside
  the task that surfaced it). User directive.
- **2026-07-19 — Wave 5: production supervisor, task graph, effect-safety ledger.** Built
  `src/readme_agent/supervisor/` (`task.py` -- `TaskGraph`, `ORC-001`'s exact state set, two
  independent cycle checks, `SUPERSEDED` dedup; `convergence.py` -- `AGT-004`'s four stop
  conditions, `check_repair_exhausted()`/`final_status()` split after a real bug found live via a
  smoke test, see below; `repair.py` -- `ORC-002`/`VER-002` failure classification and
  auto-repair; `loop.py` -- `supervise_repo()`, promoting Wave 1's spike), `llm/planner_client.py`
  (promotes the spike's `chat_raw()`; cannot reuse `LLMClient`, which hardcodes a
  no-tools/no-tool_choice payload and a strict single-job response schema), and
  `capabilities/effect_ledger.py` (`EFF-002`/`EFF-003`'s two-phase apply / retry-inertness,
  dispatch-tier per decision #26's own "Wave 5's dispatcher-retry-wrapper work" phrasing, not
  supervisor-specific). New CLI `supervise` verb, additive alongside `run`/`run-registry`
  (unchanged), `--durable-state` opt-in matching `run`'s convention; cutting the GitHub Actions
  workflow over to `supervise` is a separate, deliberately deferred decision.

  **A real, dated conflict was found and resolved during planning, not silently picked either
  way**: the user's initial confirmation to register `generate_repo()` as Wave 5's first
  `local_write` capability conflicted with a same-day decision #26 addendum stating "Wave 5's
  supervisor never registers a capability at all; Wave 7 is the actual blocking dependency" for
  `EFF-001`. Brought back to the user rather than silently overridden either direction; resolved
  by separating two questions that had been conflated -- *which wave registers a real mutating
  capability* (Wave 7, unchanged) from *which wave builds and proves the safety mechanism*
  protecting against duplicate effects (now, because it's safety-critical and provable without a
  real capability, via a synthetic effector matching `EFF-002`'s own written acceptance
  criterion). `generate_repo()` also turned out to be a structurally poor `EFF-002` test subject
  independent of the ledger question: its idempotency key (`facts_hash`) isn't a call argument, so
  it can't be computed pre-dispatch.

  A genuine design flaw in the cited prior investigation
  (`capability-dispatch-production-readiness.md`) was found and corrected *before* writing any
  code: its two-phase-apply proposal stored the pending/applied intent record in local
  evidence-dir JSON, exactly the storage Wave 4 built `GitStateBackend` to stop depending on --
  would have lost the record on the precise "runner dies mid-effect" scenario `EFF-002` exists to
  survive. Corrected to the durable git-backed record instead.

  Several real bugs found and fixed during implementation, before or via direct testing (not
  discovered live in production): (1) a premature-convergence bug -- an early `convergence.py`
  design checked graph emptiness at the top of every turn and stopped after the deterministic
  bootstrap alone, *never consulting the planner at all*; found via a manual smoke test, not a
  unit test, before any test suite existed to catch it; fixed by splitting convergence into
  `check_repair_exhausted()` (evaluated every turn) and `final_status()` (only classifies the
  ending state once the planner's own explicit stop signal fires); (2) `TaskGraph.ready_tasks()`
  originally required a dependency to reach `PASSED`, which would permanently strand every repair
  task (whose sole dependency is the `FAILED` task it repairs, which never becomes `PASSED`) --
  fixed to accept any terminal state; (3) `_dispatch_and_record()` returned `None` and callers
  kept referencing the stale pre-dispatch `Task` object (`TaskGraph.mark()` returns a new object,
  consistent with every other pydantic model in this codebase being treated as immutable) --
  fixed to return the resolved task, including the *repair* task's own result when one was
  dispatched, not the original failed task's; (4) the planner's own explicit stop (`tool_call is
  None`) left `outcome` as `None`, which would have crashed the write-back — fixed to compute a
  real `ConvergenceOutcome` on that path too; (5) `acquire_lock()` returning `None` (another
  holder's unexpired lease) was silently proceeding as if the lock were held, directly violating
  `StateBackend.acquire_lock()`'s own documented contract -- fixed to return `BLOCKED
  ("lock_held")` immediately, regression-tested. A dead-code branch (`effect_ledger.py`'s
  `retry_refused` outcome) was found and removed: a failed dispatch always leaves the ledger
  entry `pending`, which unconditionally intercepts before a `retry_policy` check could ever be
  reached -- `EFF-003`'s real enforcement point is one layer up, `repair.py`'s
  `create_repair_task()`, gating whether to even *propose* a retry in the first place.

  `AGT-001`/`AGT-003`/`AGT-004`/`ORC-001`/`GAP-001`/`GAP-002` → `IMPLEMENTED`;
  `EFF-003` → `IMPLEMENTED`; `AGT-002`/`MEM-001`/`EFF-001`/`EFF-002`/`ORC-002`/`ORC-003`/`VER-002`/
  `VER-003` → `PARTIAL` (unit-proven against the real registry/dispatcher, live proof written and
  pending your explicit confirmation, per `GOVERNANCE.md` rule 10). New live tests:
  `tests/integration/test_effect_ledger_live.py`, `tests/integration/test_supervisor_live.py`.
  New unit test files: `test_task_graph.py`, `test_effect_ledger.py`, `test_repair.py`,
  `test_planner_client.py`, `test_convergence.py`, `test_supervisor_loop.py` (52 new tests).
  `orchestrator.py::_require_permitted` renamed to `require_permitted` (public) so
  `supervisor/loop.py` enforces the identical hard allow-list gate (decision #4), not a
  near-duplicate. Full suite: `ruff check .`, `ruff format --check .`, `mypy src` clean;
  `pytest -q` → 396 passed (up from 335), 15 deselected. User directive.
- **2026-07-19 — Wave 5 live proofs run for real.** User confirmed running both live test files
  (what/why/where stated per the same-day `GOVERNANCE.md` rule 10 sharpening: disposable
  `refs/readme-agent-state/...` state on this project's own remote, and a real dry-run
  `supervise_repo()` call plus its accepted durable state against the allow-listed `pdf/java`
  pilot, left behind per Wave 4's precedent — neither touches a target repo's actual remote).
  Both files, 4/4 tests, passed. Hit the already-documented `OPS-009` local push-credential hang
  (`git push` blocks silently and indefinitely without it) on the first attempt — a real cost
  (~66 minutes) of not checking a known prerequisite first; fixed with the documented one-time
  procedure and added the same docstring pointer to `test_supervisor_live.py` that
  `test_state_git_backend_live.py` already had. `AGT-002`, `MEM-001`, `EFF-002`, `VER-003` →
  `IMPLEMENTED` (each row's own literal acceptance text is now live-proven). `EFF-001`,
  `ORC-002`, `ORC-003`, `VER-002` stay `PARTIAL` — the live run against a healthy pilot never
  actually failed, so the repair/replan path itself remains proven only at unit level, and
  `EFF-001`/`ORC-003` remain genuinely blocked on Wave 7 (real mutating capability, real
  specialist roles), not on any live-proof gap. Full suite unaffected: `pytest -q` → 396 passed,
  15 deselected; `ruff check .`, `ruff format --check .`, `mypy src` clean. See `master.md`'s
  matching Changelog entry for full detail. User directive.
- **2026-07-19 — Wave 6 rescoped; durable-skip drift-blindness found and fixed as a standalone
  prerequisite (decisions #37/#38).** "Product agent" confirmed to be an organizational label, not
  a real cooperating system, after direct user pushback — Wave 6's "product-agent integration:
  handoff schema" framing is corrected to "upstream-change watch and reconciliation." Treated as a
  production problem per direct user instruction: found that `generate_repo()`'s durable-state fast
  path skipped validation on `facts_hash` equality alone, and `facts_hash` deliberately excludes
  README content (decision #11) — on the actual production runner topology, this made the system
  permanently blind to real upstream README edits once a repo's facts stabilized, verified directly
  against the existing regression test (which had only ever exercised unchanged content). A second,
  separately live bug found in the same function: `_record_accepted_state()` silently dropped
  `domain_states`/`supervisor_state` on every write — already destructive today, not merely
  forward-looking, since Wave 5's `supervisor_state` is already written. New `RUN-004` (`PARTIAL`)
  for the fix; `MEM-004`'s acceptance text extended for the clobber fix; new `ORC-004` (`BACKLOG`)
  logging the two-entry-point state duality this pass traced through and found bounded, not fixed.
  Sequenced as a standalone change per user directive, verified in isolation before Wave 6's
  remaining feature work (specialist registry, LangGraph, supervisor integration — designed, not
  yet built this pass) is built on top of it. `readme/facts.py::compute_tracked_content_hash()`
  (new, canonical), `inspection/file_inventory.py::FileInventory.community_paths` (new),
  `RunStateV1.upstream_content_fingerprint_at_accept` (new, additive) — 12 new tests, `pytest -q` →
  408 passed (up from 396), 15 deselected unchanged; `ruff check .`, `ruff format --check .`,
  `mypy src` clean. Live re-proof against the real `pdf/java` pilot pending explicit confirmation.
  See `master.md`'s matching Changelog entry for full detail. User directive ("treat this as a
  production problem... reassess the system carefully and identify the underlying causes").
- **2026-07-19 — Wave 6's remaining feature work built (decision #39): first real LangGraph
  specialist, routed through the Wave 5 supervisor.** `langgraph>=1.0` added for real for the first
  time, executing decision #27's Wave 6-8 commitment. New `get_product_facts`/`classify_upstream_
  change` capabilities, `readme/reconciliation.py` classifier, `specialists/readme_reconciliation.py`
  (two-node `classify`->`record` `StateGraph`, state is `DomainStateV1` directly), `specialists/
  registry.py` (mirrors `capabilities/registry.py`'s pattern). `supervisor/loop.py::supervise_repo()`
  gains a registry-driven second convergence tier (`CONVERGED_NO_TRACKED_CHANGE`). New
  `.github/workflows/readme-agent-supervise.yml` (`workflow_dispatch` only). `FACT-001` → `PARTIAL`
  (was still `PLANNED` in the table despite the prior changelog entry claiming otherwise — caught and
  corrected in the same pass as this one, not left inconsistent). `CAP-006`/`MEM-004` extended:
  a real first domain/domain-writer now exists (`readme_reconciliation`), still `PARTIAL` per
  `GOV-018` pending a live, real-gateway proof. `ORC-003` extended with an honest caveat: the new
  specialist runs before the task graph starts, not as a task-graph node — a distinct mechanism, not
  yet literal fulfillment of that row's wording. Two real bugs found and fixed via direct
  test-writing: an `OWNED_SPAN_LOST` misclassification gap (`remove_span()` is a no-op once a span is
  already absent — fixed by adding `DomainStateV1.owned_span_present_at_accept`) and
  `cmd_supervise`'s exit-code mapping not recognizing the new converged status (would have exited `1`
  for a successful run). 29 new tests, `pytest -q` → 437 passed (up from 408), 15 deselected
  unchanged; `ruff check .`, `ruff format --check .`, `mypy src` clean. See `master.md`'s matching
  Changelog entry for full detail. User directive ("execute phase b, make wave 6 execute e2e...
  continue, however do not push to anything to product repos").
- **2026-07-19 — Wave 6 live-proven: `supervise` + its new workflow, real gateway, real remote, no
  push to any product repo.** `readme-agent supervise --repo aspose-cells-foss/Aspose.Cells-FOSS-
  for-Java --durable-state` run for real (hit the already-documented `OPS-009` credential gap again,
  recognized and fixed within minutes this time, not ~66 minutes) — real gateway planner dispatched
  `inspect_repository`/`detect_readme_gaps`/`get_product_facts` and converged correctly; the
  `readme_reconciliation` specialist ran first as designed, recording a real `domain_states` entry
  alongside a real `supervisor_state` write in the same durable record, confirmed by reading it back
  — decision #38's multi-producer fix proven under a genuine second producer. `act workflow_dispatch
  -W .github/workflows/readme-agent-supervise.yml` reproduced the same outcome in a real container --
  `Job succeeded`. `FACT-001`, `CAP-006`, `MEM-004` rows updated with this live evidence (updated in
  place above, not repeated here); all three stay `PARTIAL` — cross-domain denial and genuine
  two-domain collision remain unit-only, pending Wave 7's second domain. Nothing pushed to either
  target repo at any point. See `master.md`'s matching Changelog entry for full detail. User directive.
- **2026-07-20 — Full-registry Wave 6 hardening pass: 25/25 clean, zero bugs, third pilot
  (`3d/java`) live-proven.** `compute_tracked_content_hash()`/`readme.reconciliation.classify()`/
  community-file detection run read-only against all 25 real `data/products.json` entries regardless
  of mode (decision 24/`PIL-011`, mirroring Wave 3's own survey discipline) — no crash, no
  misclassification, ecosystem detection unregressed, no code change needed. `aspose-3d-foss/
  Aspose.3D-FOSS-for-Java` given its first live `supervise --durable-state` run: real gateway
  planner dispatched 5 of 6 registered capabilities in one run and converged; `domain_states`/
  `supervisor_state` both recorded correctly in the same durable record, completing live coverage of
  all 3 enabled pilots (previously only `cells/java` and `pdf/java` had one). Honest limits restated:
  `get_product_facts`'s policy-dependent output still proven for only 3 repos; the classifier's
  non-`FIRST_OBSERVATION` branches remain live-proven for only 1 repo; `CAP-006`/`MEM-004`'s
  domain-denial/multi-domain-collision paths remain unit-only, unchanged by this pass. Full detail:
  `plans/investigations/full-registry-wave6-survey.md`; see `master.md`'s matching entry. User
  directive.
