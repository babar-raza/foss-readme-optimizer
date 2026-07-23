# Full-Surface Current State — All Five Control Classes

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> taskcards: (§A), (§B–C), (§D–E), (§F–H)
> Evidence: code at HEAD `4adbaaf`; real run artifacts `runs/` (2026-07-17); GET-only GitHub fixtures
> `evidence/github-fixtures/` (2026-07-18, transcript proves zero mutation); Maven Central queries.

## A. Repository-file managed — current state

### A1. README (deep reconstruction — verified against HEAD `4adbaaf`)

The shipped engine's README handling is fully reconstructed in the authoritative plan the current-state reconstruction
(pipeline, dead code, quirks). Citations re-verified this session:
- work-clone reuse without upstream sync: [orchestrator.py:85-88](../../src/readme_agent/orchestrator.py#L85-L88) ✔
- `commit_sha=None` hardcoded (git_metadata dead): [orchestrator.py:147](../../src/readme_agent/orchestrator.py#L147) ✔
- skip decision: [orchestrator.py:175-177](../../src/readme_agent/orchestrator.py#L175-L177) ✔
- `--check-links` ignored: [orchestrator.py:258-264](../../src/readme_agent/orchestrator.py#L258-L264) ✔
- evidence `mode` hardcoded `"dry_run"`: [orchestrator.py:231](../../src/readme_agent/orchestrator.py#L231) ✔

Current pilot READMEs (baseline clones, 2026-07-17): 3d 86 lines (bot-authored, all 4 promo
elements present, no images); cells 250 lines (substantial technical content, install section,
**no** products.org/.com links — the "blank-slate" is promo-element-blank, not content-blank);
pdf 193 lines (4 badges, honest "not yet on Central" install section, missing only the .org link).
**No product illustration in any pilot** (pdf: badges only). README-embedded-asset machinery:
none exists in the engine (no image handling anywhere).

**Capability summary:** the engine can detect 4 promo elements anywhere in the README and
additively render owned marker spans. It cannot: parse structure (no AST), reconcile a
product-agent overwrite (change_boundary blocks + stale work clone), track upstream revision,
distinguish legitimate updates from regressions, or handle any file other than README.

### A2. Community files (GET fixtures, 2026-07-18)

| File | cells | 3d | pdf |
|---|---|---|---|
| README recognized | YES | YES | YES |
| LICENSE recognized by GitHub | **no** ⚠ | YES | YES |
| CONTRIBUTING | no | no | no |
| CODE_OF_CONDUCT | no | no | no |
| issue templates | no | no | no |
| PR template | no | no | no |
| community health % | **37** | 50 | 50 |

⚠ **Finding A2-1:** cells keeps its license at `License/LICENSE.txt` (nested, non-standard) —
`file_inventory.py` finds it (case-insensitive nested scan) but **GitHub does not recognize it**
(community profile `license: null`, health 37%). Real, actionable class-A gap: move/copy to a
recognized location. No org-level default community files were detected for any pilot org
(profiles show nothing inherited). No SECURITY.md/SUPPORT.md anywhere.
**Engine support today: none** — no community-file detector, renderer, or validator exists
(Phase 23 unbuilt, as planned).

### A3. README illustrations / repository assets

None exist in any pilot; engine has zero asset machinery (no generation, hashing, naming,
alt-text validation). Everything in the plan's A3 notes is greenfield.

## B. API/settings managed — current state (GET fixtures)

| Field | cells | 3d | pdf |
|---|---|---|---|
| description | product-specific, good ✔ | `"Aspose.3D FOSS for Java"` — name-only, weak ⚠ | **null** ⚠ |
| homepage | `https://products.aspose.org/cells/` ✔ | **null** ⚠ | **null** ⚠ |
| topics | **[] empty** ⚠ | **[] empty** ⚠ | **[] empty** ⚠ |
| Issues/Wiki/Projects/Discussions | on/on/on/off | on/on/on/off | on/on/on/off |
| default branch | **master** ⚠ (others: main) | main | main |

**Findings B-1..B-4:** every pilot has empty topics; pdf has neither description nor homepage;
3d's description is a name, not an explanation; cells is the only well-configured pilot (and its
description quality shows what "good" looks like — likely product-agent-authored). Feature
settings look default; **no evidence any were deliberately chosen** → B4 rule (change only with
business justification) has no current baseline to preserve.
**Engine support today: none** — no settings reader/proposer exists (Phase 22 unbuilt).

## C. Manual UI managed — current state

Social preview: **no read API exists** (documented GitHub limitation; upload is Settings-UI-only).
Current state of each pilot's social preview: **UNKNOWN — honest `MISSING_STATE`**; determining it
requires a human viewing Settings or rendering a share card. Engine support: none (Phase 24
unbuilt). This is the class where "never claim applied without operator evidence" (SAFE-011)
starts from zero.

## D. Product-agent owned — current state (GET fixtures + Maven Central + poms)

Releases: cells `V26.5.0`, `V26.4.0`; 3d `v26.5.0`; pdf `v26.6.0` — all with **0 assets**.
Pom versions match latest tags (26.5.0 / 26.5.0 / 26.6.0) ✔.

**Finding D-1 (real, user-facing):** release tag prefix is inconsistent across the family
(`V` vs `v`) — a naming-consistency audit item for the owning product agents.
**Finding D-2 (real, high-value):** `org.aspose:aspose-{3d,cells,pdf}-foss` — **zero results on
Maven Central** (search.maven.org queried 2026-07-18), yet:
- **cells README instructs adding the Maven Central `<dependency>`** → a *broken install path*
 presented as working (violates the intent of RDM-007/FACT-008; owned by the product agent →
 exactly a `HandoffFindingV1` case, not a central-agent fix);
- **pdf README's Maven-Central badge points at `org.aspose/aspose-pdf`** — a *different*
 artifactId than its pom (`aspose-pdf-foss`) — misleading badge, though its prose honestly says
 "not yet available on Central";
- 3d README says build-from-source only ✔ consistent.
**Finding D-3:** GitHub Packages could not be checked — token lacks `read:packages`
(`BLOCKED_EXTERNAL`; evidence: 403 transcript). Poms declare no `distributionManagement` →
no alternative publish target declared anywhere.
**Engine support today: none** (audit/handoff unbuilt — Phase 22/25), and per CORE-022 there must
never be a write handler here.

## E. GitHub generated — current state (GET fixtures)

Languages: 100% Java in all three (clean — no Linguist anomaly). Contributors: cells
`babar-raza(11), laurence-chen(4)`; 3d `babar-raza(3)`; pdf `andreynekrasov0911(12),
prorata-net(1)` — small human sets, no bot noise, no anomaly. Stars/forks: 1–2 (observation
only; **must never become validators**). Activity: pilots were pushed 2026-06-18 (cells),
2026-07-17 (3d), 2026-07-16 (pdf) → **product agents are actively pushing**; the post-publish
reconciliation problem is live, not hypothetical.
**Engine support today: none**, and none is ever allowed to write (OWN-003/005).

## First-failing-boundary per surface

| Surface | First boundary where today's system loses consistency |
|---|---|
| README | **Input acquisition**: stale work clone + upstream-blind fingerprint (plan the current-state reconstruction) — before any reconciliation could even start |
| Community files | **Detection**: no detector exists; drift invisible (e.g. A2-1 unrecognized LICENSE went unnoticed) |
| Description/homepage/topics | **Detection**: no reader exists; B-1..B-4 gaps invisible to the system |
| Social preview | **Observability**: no read API — state unknowable without operator input; needs explicit MISSING_STATE handling |
| Releases/packages | **Detection + routing**: no audit exists; D-1/D-2 live defects flow to users (broken install) with no handoff path |
| GitHub-generated | **None applicable** (audit-only): risk is inverse — accidentally *adding* control; must stay write-path-free |

## F. Reuse matrix () — evidence-based, per component

| Component | Current proof | Decision | Reason |
|---|---|---|---|
| allow-list (`registry/loader.py`) | tests + live block proof (BLOCKED_NOT_ALLOWLISTED) | **reuse as-is** | Hard gate independent of surface; extend registry fields only |
| preflight (`preflight/*`) | live the settings proof026-07-17 (3 repos HTTP 200, model check) | **extend** | Add model-routing checks (L2/L3) + wire into `run` (CON-004) |
| git safety (neuter/hook/verify) | real-push-block test; verified live clones | **reuse as-is** | Class-A apply channel unchanged (never-push) |
| clone handling (`gitsafety/clone.py`) | deterministic-flags tests | **extend** | Add work-clone re-sync from upstream (the the current-state boundary fix); keep determinism flags |
| inspection (`file_inventory`) | tests incl. nested-LICENSE case | **reuse as-is** | Found A2-1 (nested LICENSE) — proves value |
| ecosystem parsers (`ecosystems/*`) | maven tests; generic dispatch | **extend** | 1 of 6 platforms implemented; add per-ecosystem parsers via existing dispatch (no new call sites) |
| facts model (`readme/facts.py`) | hash tests; evidence | **redesign→extend** | Becomes `ProductFactsV1` consumer; add `commit_sha` (currently None) + provenance fields |
| hashing (`sha256_text`, canonical JSON) | hash tests; CRLF-normalized | **reuse as-is** | Foundation for all new fingerprints |
| gap detection (`gap_detector.py`) | 14-README ground-truth table | **reuse as compatibility check** | Keeps 4-element check; must NOT be the quality definition (RDM-014) |
| markers (`readme/markers.py`) | round-trip tests | **reuse, demoted** | Useful for owned spans; no longer the reconciliation mechanism |
| renderer (`readme/renderer.py`) | tests; deterministic URLs | **extend** | Deterministic URL/UTM rendering stays; callout retirement (RDM-001) pending |
| validators (8 rules + registry) | tests + STALE_NONCOMPLIANT proof | **extend** | Registry pattern generalizes; `change_boundary` **redesign** → ownership-aware boundary |
| LLM client (fixture/live, strict schema) | tests + live call proof | **extend** | Add per-job model routing (L2) + generation cache; keep schema-fail-closed |
| evidence writer + redaction | atomic writes, 2-layer secret scan | **extend** | Becomes `RunManifestV1` writer; redaction reused verbatim (this probe used it) |
| CLI (`cli.py`/`commands.py`) | CLI tests, exit codes | **extend** | New verbs per surface; exit-code contract kept |
| orchestrator | e2e proofs ×3 pilots | **redesign** | Single-surface linear flow → per-surface state-machine walk; stages reused as workers |
| workflows (ci/readme-agent-run) | CI green; dry-run dispatch | **extend** | Add state-aware run; keep read-only permissions |
| stable work clone | idempotency proof (local only) | **demote to cache** | CON-002; durable state → `.state/` StateStore |
| run history (`history/` empty) | none | **build new** | Nothing exists to reuse |
| `links/validator.py` (unwired) | unit tests exist | **wire or drop** | CON-006 route |

## G. Coordination-behavior requirements record (— precedes framework choice)

Required, from the proofs' actual shape: **states** = the run state machine (plan the cross-cutting architecture) per
(repo, surface) with `MISSING_STATE` + `BLOCKED_EXTERNAL` observed in practice (C-class, D-3);
**interrupts** = human apply gate (class A patches, class C operator apply) + checkpoint stops;
**persistence** = `.state/` JSON per repo, atomic, schema-validated, surviving process restart
(proofs re-read it across runs); **concurrency** = per-repo lease + remote-HEAD capture/re-check
(single-writer per repo is sufficient at pilot scale — 3 repos, serial registry loop today);
**retry** = bounded per external call (existing LLM client pattern), never on schema failure;
**failure isolation** = per-repo AND per-surface (one surface failing must not falsely complete
the run — RunManifestV1 rule); **observable events** = state transitions logged to evidence.
Assessment against options (full scoring in the framework selection): pilot needs are met by
**existing-orchestrator-as-workers + explicit state machine + Pydantic state models** — no
framework dependency is *required* at this scale; LangGraph/Pydantic-AI/Agents-SDK add value only
if T4 finds resumability/interrupt ergonomics worth the dependency. Framework decision stays in
the framework selection with this record as input.

## H. LLM gateway characterization (— summary; full report `llm-gateway-characterization.md`)

L1 context NOT small (originally reported ~96k on qwen3-next/VL, **corrected 2026-07-21/22, `LLM-019`:
the probe script had a filler-scaling bug; the real, live-proven ceiling is ~71,069 tokens**) — prior
assumption disconfirmed; L2 **`gpt-oss` (current default) is the unreliable model** (needle 0/6 sizes,
JSON validity poor and inconsistent across reruns — originally reported "1/10," **corrected 2026-07-22,
`LLM-018`: a 0.4-0.8 swing across two single-session N=10 reruns, not a stable rate**) → per-job model
routing required; L3 `qwen3-next` 5/5 structured, ~2s; L4 `qwen3-embedding-8b` separates same-template
(0.79) from unrelated (0.45–0.55) → embedding-based template/drift detection viable; L5 gateway
also hosts vision (VL) + image-gen (SD-3.5) → Phase-24 visuals can stay on-gateway.
