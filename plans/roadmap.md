# Roadmap — remaining atomic work, reordered to the full-registry POC charter

> **SUPERSEDED as execution authority (2026-07-24).** The 2026-07-23 Level-8 consolidation
> (`master.md` Build Checklist **Waves 0–8** + the durable execution overlay
> `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`) is the single current
> plan; `master.md` records that the untracked `roadmap.md`/`status.md`/`changelog.md` "are not
> authority." For "what's next," read `master.md`'s Build Checklist and the L8 task graph; for
> current status, read the generated `plans/status.md`; for dated history, read `logs/`.

Governed by [`plans/master.md`](master.md) (Decision Ledger, Build Checklist) and
[`plans/requirements.md`](requirements.md) (normative requirements). This document tracks
**future** work; `plans/status.md` tracks current generated status; `logs/` tracks dated history.
Update this file as each item closes — it is hand-maintained (unlike `plans/status.md`), so keep
entries terse and move completed items to a one-line "closed" note rather than deleting them
(`GOV-003`).

**Reordered 2026-07-25** (`RPOC-013`, full-registry README POC charter): this file's content is
now grouped under the charter's 12-item delivery order instead of the old Wave 9–15 numbering. No
information from the prior Wave 9–15 grouping was deleted — every item below still names its
originating wave/sub-item for cross-reference. The prior Wave 9–15 numbering never mapped 1:1 onto
`master.md`'s current Waves 0–8 either (see the SUPERSEDED banner above); this reorder does not
change that — it is a relabeling of this already-non-authoritative file's own internal structure.

## 1. Authority correction

Already in force — the SUPERSEDED banner at the top of this file, standing since 2026-07-24 and
reaffirmed by decision #78 (`master.md`, 2026-07-25): `plans/idea.md`, `master.md`,
`plans/requirements.md`, and `plans/GOVERNANCE.md` are authoritative in their respective roles.
This file, `plans/status.md`, and `plans/changelog.md` are reference/history, never authority — see
`plans/GOVERNANCE.md`'s rule on authority precedence (`RPOC-016`).

## 2. Stack / build-vs-adopt audit — done

Completed: [`plans/investigations/full-registry-readme-poc-build-vs-adopt-audit.md`](investigations/full-registry-readme-poc-build-vs-adopt-audit.md)
(taskcard `RPOC-002`). Covers agent orchestration/task graph, Markdown parsing, GitHub API access,
retry/HTTP, structured LLM output, state/checkpointing, and observability, each with a
`KEEP_CURRENT`/`WRAP_WITH_PROVEN_LIBRARY`/`MIGRATE_INCREMENTALLY`/`REPLACE_BEFORE_POC`/
`DEFER_REPLACEMENT` recommendation and a one-paragraph justification. This is the precedent
`plans/GOVERNANCE.md`'s new build-vs-adopt rule (`RPOC-016`) points at for any future new custom
infrastructure.

## 3. Canonical local README runtime

Runtime-correctness foundation the rest of the sequence depends on — originally Wave 9
("Foundation, Truth Closure & Autonomous-Runtime Correctness") plus the infra-shaped parts of the
old Wave 13.

- [x] 9.1 — Verification baseline, lockfile, `run_official_checks.py`, malformed-row fix, `GOV-024`
      reclassified. Closed 2026-07-22.
- [x] 9.2 — Implementation-truth matrix tool built and run (114 `IMPLEMENTED` rows checked, 0
      high-confidence overclaims). Closed 2026-07-22. Deeper semantic sweep across the ~170
      `PLANNED`/`BACKLOG`/`PARTIAL` rows stays open, ongoing across future sessions.
- [x] 9.3 — Doc repair (`AGENTS.md`, `docs/safety-model.md`, `docs/repository-presentation-surface-
      model.md`), `OWN-004` scope correction, `LLM-018`/`LLM-019` citation fixes, decision #37
      amended in place, `plans/status.md`/`plans/roadmap.md`/`plans/changelog.md` created, `master.md`
      Status section trimmed. Closed 2026-07-22.
- [ ] 9.4 — Execution profiles (`local_inspect`/`local_dry_run`/`github_observe`/`github_proposal`/
      `github_apply`), `--execution-profile` CLI flag, close the `supervise --domain` bypass.
- [ ] 9.5 — Fail-closed durable state, 11-checkpoint incremental persistence, trigger identity/dedup
      (`TriggerRecordV1`).
- [ ] 9.6 — Correct effect identity: `EffectIdentityV1` (candidate-byte-aware idempotency key),
      fixing the confirmed live bug (`fresh_fingerprint` hashes the pre-render baseline, never the
      rendered candidate).
- [ ] 9.7 — Per-surface freshness contracts (`SurfaceFreshnessContractV1`), corrected 7-condition
      `NO_CHANGE` gate, `GOV-024`'s narrower remaining piece (confirm fingerprint hash-coupling).
- [ ] 13.1 — Evidence unification (`RunManifestV2`) — the runtime's own evidence contract.
- [ ] 13.4 — Model-routing governance wiring — which model executes which job, a runtime concern
      independent of any one agentic task (see also item 5 below, which covers the agentic jobs
      themselves).
- [ ] 13.6 — Dependency & runner reproducibility (SBOM, Python matrix, `act` proof).

*Reserved, not yet triggered* — Wave 10 (specialist process-independence and MCP-hosted
deployment, decision #41). Trigger condition: item 7/8's controlled-rollout cost data (repointed
from old Wave 9 during Wave 9.3). Does not map onto any single charter item below; kept here as
the closest fit (a runtime-topology question) until its trigger condition fires.

## 4. Complete fact acquisition

Originally Wave 11 ("Repository Intelligence, Product Facts & Capability Typing"). Feeds `FACT-017`
(`plans/requirements.md`) — the agentic drafting + mechanical-verification loop that replaces the
old "manually author `product_truth` for 28 repos" framing.

- [ ] 11.1 — Repository profile graph (`PackageRoot`, `SharedSurface`, `UnresolvedFinding`).
- [ ] 11.2 — Multi-registry acquisition verification (PyPI/npm/NuGet/Go-proxy/Conan/vcpkg resolvers).
- [ ] 11.3 — `ProductFactsV1`/`ProductChangeSetV1`, 3 ingestion modes, corrective (not just blocking)
      conflict-mode — the concrete execution of previously-deferred `DOC-006`.
- [ ] 11.4 — Capability contract typing (`input_model`/`output_model`) & dispatcher hardening.

## 5. Agentic planning and generation

Originally Wave 12.1/12.2 plus the agentic-routing parts of Wave 13.

- [ ] 12.1 — Semantic README reconciliation structural model + claim-verification/correction pass —
      the direct fix for the real `cells/java` PR problem (a known-false Maven coordinate shipped
      untouched). 8 golden-set proof scenarios including that exact regression fixture.
- [ ] 12.2 — Real task-graph planning & dynamic specialist selection; wires already-existing
      `specialist_selection_client`/`repair_planner_client` params through `commands.py`; closes
      `AGT-008`'s dossier/token-budget prerequisite. Mandatory (not optional) dynamic capability
      selection for the canonical local path is now a normative requirement (`ORC-009`,
      `plans/requirements.md`) — this item is that requirement's build-out; today's
      `--enable-dynamic-planning` CLI flag stays opt-in until it lands.
- [ ] 13.5 — Live golden-set-from-Actions + auto-disable closure (depends on 13.4) — keeps the
      agentic routes this item builds honest over time.

## 6. Independent review and repair

Originally Wave 12.3. Feeds the new independent agentic README reviewer requirement (`VER-011`,
`plans/requirements.md`) — a separate LLM judgment role from whatever produced the candidate, using
the `ACCEPT`/`REJECT_REPAIRABLE`/`BLOCKED_FACT_CONFLICT`/`BLOCKED_MISSING_EVIDENCE`/
`SYSTEM_FAILURE` taxonomy.

- [ ] 12.3 — Verification reordering & final-acceptance gate (independent verifier runs strictly
      after all tasks+repairs).

## 7. All-products local execution

Originally Wave 14.1/14.2 ("Heterogeneous Proof Portfolio"), now read against every entry in the
runtime-loaded registry rather than the original 7-target scope.

- [ ] 14.1 — Prep & registry expansion (originally scoped to 7 real targets: 6 in the `cells`
      family + `pdf/go`; the charter's Gate A widens this to every registry entry).
- [ ] 14.2 — Live execution & convergence proof (seed→reject→repair→propose→converge), run across
      the full registry rather than the original 7-target set.

## 8. Full-registry closure

Originally Wave 14's "Program Closure" line. This is Gate A's own closure milestone — every
registry repository at a terminal local-proof status, not a partial-registry result presented as
if it were the whole POC (`plans/GOVERNANCE.md`'s new anti-partial-POC rule, `RPOC-016`).

- [ ] Regenerate `plans/status.md`/`plans/roadmap.md`, confirm all external completion gates,
      zip the evidence tree, print its absolute path — scoped to the full registry, not a sample.

## 9. Human review

Human review follows full-registry independent agentic approval and no-op proof, never precedes it
— see `plans/idea.md`'s "README POC Readiness and Ordered Delivery Gates" section and decision #78
(`master.md`). Every current registry candidate must be human-accepted before Gate C.

- [ ] 15.5 — Structured pilot review report (standing artifact, not an operational gate; `PIL-008`
      stays a human-only fact code cannot self-certify). Originally Wave 15.5.
- Sponsor/human acceptance (`PIL-008`) is a separate, honestly labeled fact the system cannot
  self-certify, but it is a Gate-B prerequisite for Java PR proof.

## 10. Java PR proof (Gate C)

Attempted only after items 1–9 are accepted for the full registry (decision #78, `master.md`).
Wave 6's own three-Java-repository technical content (`master.md` Build Checklist) is unchanged;
this item is about *when* it starts, not what it proves.

- [ ] 13.2 — Effect-class taxonomy & authorization-record schema (`AuthorizationRecordV1`) — the
      mechanism a real PR-opening effect must satisfy.
- [ ] 13.3 — Authorization enforcement cutover (depends on 9.6).

## 11. GitHub App integration (Gate D)

Sequenced after Gate C, never before or alongside it (decision #78, `master.md`; `AUTH-008`,
`plans/requirements.md`).

- [ ] 13.7 — Decision Ledger amendment: `GOV-018`/`GOV-023` evolve to authorization-scoped autonomy
      (depends on 13.2/13.3 being proven first).

## 12. Wider repository-presentation surfaces

Originally Wave 15 ("Presentation Completeness & Full Surface Coverage", `idea.md`-driven), beyond
the README itself — pursued after the README-focused gates above, per `plans/idea.md`'s standing
"README health is the foundational goal ... must not be displaced by broader presentation
features" principle.

- [ ] 15.1 — Repository settings proposal capability (description/homepage/topics).
- [ ] 15.2 — Visual & social-preview delivery completion.
- [ ] 15.3 — Maintenance signal diagnostic (audit-only, closes `BIZ-002` correctly).
- [ ] 15.4 — Remaining README content-quality validators (full ten-dimension checklist).

## Full closure

Items 1–12 above closed and reconciled (`GOV-022`) = the system operates fully autonomously across
the whole registry, through Gate D. `PIL-008` (sponsor/human acceptance, item 9) remains a
separately recorded external fact the system cannot self-certify, but it is required at Gate B
before Gate C can begin.
