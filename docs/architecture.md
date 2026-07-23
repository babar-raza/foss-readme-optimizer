# Architecture

## Target architecture

The architecture implements the core product idea described in
[`plans/idea.md`](../plans/idea.md): a central repository-presentation agent that autonomously
monitors the registered repositories, runs on schedules or triggers, maintains durable operational
state, and relies on humans primarily for passive oversight. The idea document communicates the
product vision; `plans/master.md` is the authoritative executable specification.

The governing doctrine (`plans/master.md` decision #26) is an autonomous, capability-driven
control plane running primarily from GitHub Actions: the runtime discovers a repository's
structure, automatically selects from a registered set of capabilities, and lets the LLM plan,
interpret, coordinate, and repair — while every fact, mutation, validation, evidence record, and
rollback stays deterministic and gated. No human selects a prompt, skill, command, or next action
during a normal run.

Everything below this section describes **the current, proven engine** — the Phase 0–21
deterministic README/presentation pipeline, real and load-bearing today. It is the first
capability surface the target runtime will wrap as later waves land a capability registry,
supervisor, and durable cross-runner state (see the 2026-07-18 sprint reset entry in
`logs/2026-07-18.md`); it is not being discarded, and nothing below is aspirational.

**Wave 1 update (2026-07-18, decision #27):** the runtime's task-graph/dispatcher will extend
this orchestrator directly, built on `pydantic` (already a dependency) — not a third-party agent
framework. A live probe of `llm.professionalize.com` found native tool-calling reliable for both
routed chat models, so the sprint's structured-action dispatch protocol is implemented as a
native tool call rather than freeform-JSON prompting. See
`plans/investigations/llm-gateway-characterization.md` (findings L6–L8),
`plans/investigations/runtime-framework-evaluation.md` (the framework comparison), and
`plans/investigations/agentic-loop-proof.md` (one live observe→plan→execute→observe→replan
iteration proven against a real pilot repository) for the full evidence.

**Wave 2 update (2026-07-18):** the capability registry and permission-aware dispatcher are now
real, tested production code — `src/readme_agent/capabilities/` (see Module map below), not
investigation spikes. Three read-only capabilities are registered so far, wrapping already-proven
`orchestrator`/`readme`/`ecosystems` functions; no mutating capability exists yet. A live
integration test (`tests/integration/test_capabilities_live.py`) proves the real registry and
dispatcher work end to end against the real gateway and a real pilot repository — the
production-code equivalent of Wave 1's spike script.

**Wave 3 update (2026-07-19):** repository profiling is no longer single-ecosystem. The prior
`inspection/file_inventory.py` hardcoded one manifest field (`pom_path`) and
`ecosystems/registry.py` had exactly one registered parser (`"maven"`) — a real structural gap
`ECO-002` could never actually prove. Both are now generalized: `FileInventory.manifest_paths`
is a `dict[str, Path]` populated data-driven from `ecosystems.registry.known_manifest_globs()`,
and six real platform parsers are registered (Java — pom.xml *or* build.gradle, Python, .NET,
TypeScript, Go, C++), adapted from aspose.org's real, in-production
`scripts/pipeline/extraction/package_manifest.py` (GOVERNANCE.md rule 8, Decision #30) rather
than written from scratch. `profile/` builds a `RepositoryProfile` (multiple detected ecosystems,
not one string — `ECO-001`) on top of this same generalized detection, not a second scanner.
The shipped pipeline's `ecosystem`/`policy_profile` fields are unchanged in *purpose* (deliberate
policy selection, decision #1) — only the dispatch key for the existing Java pilots was renamed
`"maven"` → `"java"` (migrated in `data/products.json` in the same change) to match the new
platform-keyed vocabulary. See `plans/investigations/` — no dedicated Wave 3 investigation doc
was needed; the aspose.org source was read directly and adapted, not spiked first, per decision
#30's own reasoning (a proven reference beats a from-scratch design *and* a from-scratch spike).

**Wave 4 update (2026-07-19, decision #32):** idempotency ("run twice, second run makes zero LLM
calls") no longer depends only on `paths.work_dir()`'s persistent local clone, which a GitHub
Actions runner wipes after every job (`RUN-001`). `src/readme_agent/state/` adds a durable,
backend-independent record (`MEM-*`) that `orchestrator.generate_repo()` consults additively,
alongside the existing local-clone check, not instead of it. The real backend
(`state/git_backend.py`) is one dedicated git ref per `org_repo` on this project's own
remote -- a first draft (one shared branch holding every repo's state as separate files) was
reassessed and reversed before implementation: a shared branch's non-fast-forward CAS check is
scoped to the whole ref, so two *unrelated* repos' concurrent writes would have falsely
conflicted, a false positive on exactly the safety signal `MEM-002` exists to produce. A
per-`org_repo` ref makes that impossible by construction. Opt-in via CLI `--durable-state`
(mirrors `--check-install`'s never-a-default convention, since it's a real network write);
`readme-agent-run.yml` passes it by default. The live git-push proof
(`tests/integration/test_state_git_backend_live.py`) ran with explicit confirmation and passed
4/4, catching a real bug along the way: `subprocess.run(text=True, input=...)` silently
translates `\n` to `\r\n` on Windows even on the *write* side, which was corrupting
`git_backend.py`'s `mktree` input before it reached git -- fixed in
`gitsafety/_git.py::run_git()` by piping `input_text` as raw UTF-8 bytes instead. `MEM-002` is
now `IMPLEMENTED`. `RUN-003` closed the same day: a real `act workflow_dispatch` reproduction of
`readme-agent-run.yml` (confirmed to run the actual local code via `act`'s `docker cp`-based
checkout, not a stale `origin/main`) found two more real bugs on its first two attempts -- a
durable-state write-back failure (missing push credentials under `act`'s local-checkout mode) was
uncaught and aborted the whole run, so `orchestrator.py`'s durable-state read/write-back are now
both best-effort (mirrors `inspect_repo`'s `check_install` convention, never able to fail the run
by itself); and `readme-agent-run.yml`'s `upload-artifact` step used `inputs.repo_key`
("org/repo") directly as an artifact name, which the GitHub Actions API rejects (`/` is invalid),
fixed with a shell step sanitizing to the `{org}__{repo}` convention. Third attempt: `Job
succeeded`. `RUN-001`/`RUN-003` are now `IMPLEMENTED`.

**Wave 7+ resolution (2026-07-19, decisions #34/#35):** the "subgraph/specialist-role composition"
question decision #27 left open is settled ahead of Wave 7 actually landing, as two separate
sub-decisions rather than one framework choice. LangGraph is adopted for Wave 6-8 specialist
composition (decision #27's addendum) -- but its per-node tool binding is a request-time
reliability/UX layer, not the enforcement boundary. The actual boundary is dispatch-side:
`capabilities/schema.py::CapabilityManifest.allowed_domains` plus `dispatcher.py`'s `caller_domain`
check (decision #34, `CAP-006`), evaluated against real proven authorization libraries (Oso, Casbin,
Cedar, OPA) and found to still favor this hand-rolled, additive extension. Separately,
`state/schema.py::RunStateV1` gained `domain_states` (decision #35, `MEM-004`) so multiple
specialists writing independent accepted results into one repo's state record in the same run don't
false-positive collide or silently clobber each other -- the same CAS-granularity bug decision #32
fixed once already, one layer down; evaluated against GitHub-native and external (S3/DynamoDB)
alternatives and found to still favor extending the existing git-ref backend. Both shipped as code
this pass (additive, all existing tests green); real domain population and a live multi-specialist
proof remain Wave 6's job. See `plans/master.md` decisions #34/#35 and
`plans/investigations/specialist-domain-isolation-production-readiness.md` for full reasoning.

**Wave 5 update (2026-07-19, decision #36):** `src/readme_agent/supervisor/` is the production
supervisor `capabilities/schema.py::CapabilityGap`'s own docstring called "the first wave with a
'run'" -- a real task graph (`ORC-001`'s exact states, two independent cycle checks, a
`SUPERSEDED` dedup rule that makes convergence decidable), `AGT-004`'s four stop conditions,
`ORC-002`/`VER-002` failure classification and one bounded auto-repair attempt per failure, and
`supervise_repo()` promoting Wave 1's spike into tested production code. Wave 1 of the Level-8
consolidation made it the sole production runtime: `run`/`run-registry`/`generate` remain
compatibility spellings but route to read-only supervision and cannot cross an effect boundary.
`llm/planner_client.py` is a
Live/Fixture client pair (`LLMClient` can't carry a tool-calling response). `capabilities/
effect_ledger.py` implements `EFF-002`/`EFF-003` (two-phase pending/applied apply, retry
structurally inert unless declared safe) at the dispatch tier, not supervisor-specific, proven
against a synthetic test effector since no real mutating capability is registered yet (decision
#26: that stays Wave 7's job, a same-day conflict with an initial user confirmation that was
surfaced and resolved rather than silently picked). See `plans/master.md` decision #36 for the
corrected effect-ledger storage design and the bugs found via direct testing before/instead of in
production. **Live-proven 2026-07-19**: both `tests/integration/test_effect_ledger_live.py` and
`test_supervisor_live.py` have now run for real (real `GitStateBackend` push/fetch, real LLM
gateway, real `pdf/java` pilot) and pass 4/4 -- crash-mid-effect survival, real multi-round
convergence, and a real durable zero-planning-call second call, closing `AGT-002`/`MEM-001`/
`EFF-002`/`VER-003` to `IMPLEMENTED`. `EFF-001`/`ORC-002`/`ORC-003`/`VER-002` stay `PARTIAL`: the
healthy pilot never actually failed, so the repair/replan path itself remains proven only at unit
level, and a real mutating capability/specialist role still doesn't exist until Wave 7.

## Restartable production lifecycle

`.github/workflows/readme-agent-production.yml` is the sole scheduled and reusable production
entry point. Schedule, manual, reusable-workflow, and repository-dispatch events normalize to
`TriggerEnvelopeV2`, persist before preflight or LLM access, and pass through seven lifecycle
states plus eleven durable checkpoints. A per-repository Actions queue and Git-ref CAS lease
compose rather than substitute for each other. Every scheduled pass runs a recovery sweep before
building its authoritative matrix from all active registry entries.

Recovery restarts canonical supervision for the original trigger and relies on checkpoint/effect
idempotency and reconciliation; checkpoints are not a stage-skipping instruction pointer.
Terminal classification is evidence-first: final acceptance is checkpointed, Manifest V3 is
finalized and checksum-validated, and only then may durable lifecycle state become `completed` or
`blocked`. An evidence failure leaves the trigger `retryable`, never falsely successful.

Analysis receives a freshly minted, repository-scoped GitHub App token with contents-read
permission. The control repository's `GITHUB_TOKEN` writes only durable state refs. Production
token resolution ignores ambient `GH_TOKEN`/PAT values. Health aggregation runs even when one
matrix member fails, uploads `HealthReportV1`, alerts through an issue and failed Actions check,
and optionally pings an external dead-man monitor. Backlog is age/status classified: retryable or
SLA-aged work is actionable and makes the report unhealthy, while recent bounded in-flight work
remains visible without creating a false incident.

The control repository must configure the Actions variable `GH_APP_ID` and secrets
`GH_APP_PRIVATE_KEY`, `LLM_BASE_URL`, and `LLM_API_KEY`. `DEAD_MAN_HEARTBEAT_URL` is optional for
local reproduction but required before Wave 2 can be production-proven, because an in-platform
workflow cannot detect that its own scheduler never started. The GitHub App installation must
cover every observed target repository and grant target contents-read only; a later effect job
will mint a separate token with separately reviewed permissions.

## What this tool does

`readme-agent` audits a GitHub repository's README for four specific, independently-checkable
promotional elements and closes only what's missing:

- `license_mentioned` — does the README state the repo's license?
- `products_org_link` — does it link to the FOSS catalog page (`products.*.org/...`)?
- `products_com_link` — does it link to the commercial edition (`products.*.com/...`)?
- `relationship_explained` — does it explain the FOSS-vs-commercial relationship, with that
  explanation actually co-located with a real commercial/FOSS link (not just prose)?

This was derived empirically: a live audit of 14 real Aspose FOSS READMEs (2026-07-17, see
`tests/fixtures/readmes/real_audit_2026-07-17/`) found repos in three distinct states — fully
compliant (hand-authored), fully blank, and partially compliant — and a binary "has our marker or
not" design can't represent that. See `readme_agent/readme/gap_detector.py`.

## Pipeline order

```
allow-list check (data/products.json)
  -> preflight (GitHub read + LLM /models, both fail-closed)
  -> git safety (clone baseline, clone/reuse work, neuter push, install pre-push hook, verify)
  -> inspect (git metadata, file inventory, ecosystem manifest parse)
  -> gap-detect (scan the *whole* README, not just our own marker span)
  -> facts + facts_hash (repo metadata + policy content hash + prompt content hash --
     NOT gap_report, see below)
  -> decide: skip (compliant or hash-matches-and-still-valid) vs regenerate
  -> LLM call *only* if relationship_explained is a gap (every other element is
     deterministically rendered from policy config -- no LLM needed to know a URL
     that's already in config/policies/*.yml)
  -> render missing elements into one owned span (resources)
  -> validate (10 deterministic rules, always run, even on the skip path)
  -> evidence (redacted, atomic writes)
  -> independent verification
  -> registered effect dispatch (authorization/effect ledger)
  -> optional local commit or draft-PR effect (never a default-branch write)
```

## One owned span, not two

Through Phase 20 the renderer used two owned spans: `callout` (immediately after the H1, addressing
*prominence*) and `resources` (appended at the end of the file, mirroring the one real repo that
already had this fully hand-authored — `aspose-3d-foss/Aspose.3D-FOSS-for-Java`). Phase 21 retired
`callout`: the reference-repository benchmark showed that what leading FOSS projects actually share
about commercial mentions isn't a fixed position, it's tone, density, and singularity (decision #9,
corrected) — and singularity is incompatible with maintaining two separate spans that could each
carry a commercial link. `resources` (appended at the end of the file) is now the *only* owned span.
`markers.py`'s `remove_span` still recognizes the legacy `"callout"` name so the orchestrator can
strip any already-materialized callout span from a work clone on its next run
(`GENERATION_SCHEMA_VERSION` bumped to `"3"` to force that migration), but `upsert_span` no longer
accepts it — `callout` cannot be created again.

The single `resources` span renders **only** the specific elements missing for that repo. A repo
missing only the org link (the real `pdf/java` case) gets a one-line resources addition and nothing
else — no LLM call, no redundant restatement of content that's already there.

Two new ERROR-severity validator rules (`product_first_opening`, `commercial_mention_discipline`)
now also gate the *entire* README text on every run, not just newly-rendered content — so a
repo that never needed regeneration can still fail validation if its existing commercial mentions
violate the corrected decision #9 (e.g. `3d/java`'s pre-existing bot-authored resources section).

## Why facts_hash excludes gap_report

`gap_report` is *derived from* README content this tool itself rewrites. Including it in the hash
used to decide "should I regenerate" is circular: rendering closes gaps, which changes gap_report,
which would make the hash unable to ever match itself again. `facts_hash` covers only genuinely
independent inputs (repo metadata, detected license, policy content, prompt content, generation
schema version). Prompt content hashing (`llm/prompts.py::prompt_content_hash()`) means an edited
`prompts/generation/relationship_explained.yaml` file forces regeneration on its own, without
needing a `GENERATION_SCHEMA_VERSION` bump (`prompts/README.md` rule 3).
See `readme_agent/readme/facts.py` and the orchestrator test that caught this
(`tests/unit/test_orchestrator.py::TestBlankSlateRepo::test_second_run_is_idempotent_zero_llm_calls`).

## Idempotency requires a persistent work clone

This tool never pushes. That means the *only* place "run twice, second run makes zero LLM calls"
can be real is a local work clone that persists across separate CLI invocations
(`paths.work_dir`, keyed by `org/repo`, not by run-id). A fresh work clone every run would make
idempotency fictional, since the real upstream repo never receives our changes to remember them.
Evidence (`paths.evidence_dir`) is the opposite: always run-id-scoped, since it's meant to
accumulate as a historical audit trail.

## Module map

| Module | Responsibility |
|---|---|
| `registry/` | `data/products.json` + `config/policies/*.yml` loading, the allow-list gate; `discovery.py` (GitHub org scan/classify/merge core, shared with `scripts/data-refresh/update_products_registry.py`) and `self_heal.py` (supervise-time registry drift self-heal, `CORE-034`) |
| `preflight/` | GitHub + LLM connectivity checks, fail-closed |
| `gitsafety/` | Clone, push-neuter, pre-push hook, independent verification; `process.py` owns bounded subprocess-tree cancellation so a timed-out git operation cannot leave credential/git descendants holding pipes |
| `inspection/`, `ecosystems/` | Git metadata; generic multi-manifest file inventory (`FileInventory.manifest_paths`, data-driven from `ecosystems.registry.known_manifest_globs()`); six real per-platform manifest parsers (`java.py` -- pom.xml or build.gradle, `python.py`, `dotnet.py`, `typescript.py`, `go.py`, `cpp.py`), all adapted from aspose.org's proven `package_manifest.py` (GOVERNANCE.md rule 8, Wave 3); opt-in live install-path resolution (`resolver.py`, Maven Central only) |
| `profile/` | Wave 3: `RepositoryProfile`/`DetectedEcosystem` (`schema.py`), `build_profile()` (`detector.py`) -- multi-ecosystem detection built on `inspection/`+`ecosystems/`, one scan, one source of truth, not a second parallel scanner |
| `readme/` | `gap_detector.py`, `markers.py` (one span), `facts.py`, `renderer.py`, `presentation_report.py`; candidate construction is split into `candidate_pipeline.py` (render/validate wiring), `candidate_models.py` (immutable contract), and `candidate_workspace.py` (safe work-clone reuse) |
| `llm/` | Strict-schema client (live + fixture), `prompts.py` (facts+policy only). Wave 5 (decision #36): `planner_client.py` (`PlannerTurn`, `PlannerClient` Protocol, `LivePlannerClient`/`FixturePlannerClient`) -- a separate thin family, not a reuse of `LLMClient`, since a tool-call planning turn has no `content` to validate against the strict-schema client's `LLMBlockResponse`; promotes Wave 1's spike `chat_raw()` logic into tested production code. Wave 8.5 (`GOV-024`/`AGT-008`): `prompt_schema.py`/`prompt_registry.py` -- a categorical, schema-validated prompt store (mirrors `capabilities/registry.py`'s eager-registration pattern), replacing flat `.txt` files; `schema.py::Usage`/`LLMResponseMeta.usage` -- the gateway's own reported token accounting, when present |
| `validation/` | 10-rule deterministic registry |
| `license/`, `links/` | License classification, link checks |
| `evidence/` | Redaction and atomic writes; `manifest_v3.py` binds trigger/checkpoints/facts/plan/authorization/verifier/effects/requirements, and `writer.py` maintains its checksum inventory. |
| `commands.py`, `commands_*.py` | Stable CLI façade plus responsibility-sized compatibility, supervision, governance, and lifecycle handlers. `commands_lifecycle.py` owns the authoritative matrix, recovery sweep, and health report commands. Legacy verbs stay read-only. |
| `orchestrator.py` | Compatibility inspection/reporting and candidate-evidence wiring. Its legacy `run_repo()` never commits; production mutation is not dispatched here. |
| `effects/` | Small effect primitives reachable only through registered capabilities; `local_readme_commit.py` owns the local verified-README commit primitive. |
| `github_api/` | Wave 7b (decision #41): `client.py` -- shared, read-only GitHub REST API client (GET-only), extending `scripts/update_products_registry.py`'s live-proven pagination/rate-limit pattern rather than a fourth/fifth independent reimplementation. `repo_summary`/`list_contributors`/`list_languages` (7b), `list_releases` (7c), `get_community_profile` (7e -- live-verified its `files` object reports recognition for exactly `readme`/`license`/`code_of_conduct`/`contributing`/`issue_template`/`pull_request_template`, never `security`/`support`) |
| `capabilities/` | Wave 2 onward: typed registry/dispatcher plus one module per capability. `contracts.py` materializes strict Pydantic input and output models from every registered manifest; dispatch rejects malformed arguments, undeclared wiring arguments, missing permissions, and executor output that violates its contract. `compatibility.py` owns the ecosystem-to-build/package/registry vocabulary, validates manifest declarations at registry construction, and supports repository-profile filtering. Registry construction also rejects incomplete permission declarations, unknown validators, invalid evidence fields, and mutating capabilities without evidence/idempotency/retry contracts. Read-only capabilities inspect/profile/audit/propose; `commit_readme_write.py` is the `readme_presentation` domain's `local_write` effector and `open_presentation_pr.py` (decision #51) is its first `remote_write` effector. Both declare idempotency/reconciliation/evidence contracts, require `mode: full`, and run through `effect_ledger.dispatch_gated_effect()`. The PR effector uses `github_api/write_client.py` and a dedicated never-neutered PR clone, has one real Cells/Java proof, and is deliberately not yet wired into a specialist or the normal supervisor path. `prepare_visual_asset.py` remains manual-delivery preparation only. `domains.py` and `registry.all_tool_schemas(caller_domain=)` enforce specialist-domain isolation independently of orchestration-framework tool scoping. |
| `state/` | Durable Git-ref CAS state and leases. `schema.py` keeps V1 as an explicit migration source and makes `RunStateV2` current; `migrations.py` fails closed on unknown versions. `lifecycle_schema.py` defines trigger/checkpoint/health contracts; `lifecycle.py` coordinates acceptance, transitions, resume, and active context; `cas.py`, `checkpoints.py`, and `recovery.py` own their named persistence responsibilities; `trigger_v2.py` normalizes provider identity; `health.py` aggregates portfolio health. Existing domain, freshness, effect, and model-route records remain additive within the same per-repository state. |
| `retry.py` | Six typed, bounded external-operation policies. Tenacity supplies exponential jitter; HTTP adapters classify retryable transport/status failures and honor GitHub rate-limit headers. |
| `specialists/` | Wave 6 (decision #39): `registry.py` (`SpecialistManifest{domain, name, purpose, run}`, `all_domains()`/`run_domain()`, mirrors `capabilities/registry.py`'s dispatch-table pattern -- adding a specialist is a new registration here, never a new call site in `supervisor/loop.py`; Wave 7a adds a completeness gate asserting `domains.KNOWN_DOMAINS == set(_BY_DOMAIN)`, so a half-registered domain fails at import time). All eight Wave 7 specialists now shipped, each a two-node LangGraph (`classify` -> `record`) over `DomainStateV1` directly, except `cross_surface_validation.py` (no capability of its own) and `readme_presentation.py` (three nodes): `readme_reconciliation.py` (read-only; Wave 7f adds `details["license_claim"]`, the README text's own regex-classified license mention), `github_generated_surface_audit.py` (Wave 7b, read-only, class E, no write path ever), `package_release_audit.py` (Wave 7c, read-only, class D, dispatches both its own `audit_package_release_surfaces` and the existing unscoped `check_install_path`; records `HandoffFindingV1` entries into its own `DomainStateV1.details` when a real package-resolution anomaly is found), `metadata_presentation.py` (Wave 7d, read-only, class B, dispatches the existing unscoped `get_product_facts` plus its own `propose_metadata_changes`; `accepted_status` deliberately stays the plain change/no-change verdict even when a real proposal is unaddressed, so a persistent gap never blocks the convergence shortcut), `community_files_presentation.py` (Wave 7e, read-only, class 1, dispatches its own `audit_community_files` -- correlates local LICENSE/CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/SUPPORT presence against Community Profile API recognition, and prepares real Contributor-Covenant-v2.1 candidate content for a missing `CODE_OF_CONDUCT.md` only, deliberately not fabricating a template for the other three files; no write into any work clone this wave, since 7g owns this project's first real `local_write` capability; Wave 7f adds `details["detected_license"]`, reusing `license.auditor.detect_license()`), `cross_surface_validation.py` (Wave 7f, read-only, domain 6 -- reads `readme_reconciliation`'s and `community_files_presentation`'s already-recorded `DomainStateV1` entries directly via `backend.load()`, no capability dispatch of its own; flags a real README-license-claim-vs-LICENSE-file-classification mismatch into `details["inconsistencies"]`; only meaningful with a real `--durable-state` backend, degrades honestly otherwise), `readme_presentation.py` (Wave 7g, domain 7 -- the one real mutating specialist: `render` dispatches the existing `render_readme_candidate`; `commit` dispatches the new `commit_readme_write` via `dispatch_gated_effect()` only when a write is actually needed and only with a real durable backend, refusing to mutate otherwise; `accepted_status` stays the generic change/no-change verdict via `facts_hash` directly, never the orchestrator's own GENERATED/COMPLIANT_NO_CHANGE vocabulary, which lives in `details["render_status"]` instead; unifies `ORC-004`'s two accepted-state ledgers by calling `record_accepted_readme_state()` from its own `commit` node -- live-proven with a real local git commit, real steady-state convergence, and real crash-recovery reconciliation against `aspose-cells-foss/Aspose.Cells-FOSS-for-Java`), `visual_preparation.py` (Wave 7h, domain 8 -- the final Wave 7 specialist, dispatches the existing unscoped `get_product_facts` plus its own `prepare_visual_asset`; prepare-only, no write path exists this wave). `independent_verification.py` (Wave 8b/8c, domain 9 -- the independent verifier: `verify_readme_candidate` gates `readme_presentation`'s `commit` node via a required `verification_verdict` argument (the literal reading of `VER-001` for this project's one real write); 8c extends it with evidence completeness across every other domain, requirement-ID mapping, and adversarial cross-domain checks; honestly post-hoc/non-blocking for every domain except the one it gates). `presentation_benchmarking.py` (domain 10 -- an LLM-based structured comparison of the current presentation against `docs/presentation-standard.md`; evidence-only, no write path; registered and tested but, as of this pass, not yet documented anywhere in `plans/master.md`'s Decision Ledger/Build Checklist or `plans/requirements.md` -- a real gap this pass's own validator (`scripts/governance/validate_plan_structure.py`) now catches mechanically for any future specialist added without a matching module-map row). `SpecialistManifest.depends_on` (Wave 7f): declares and build-time-checks (`_build()`) that a specialist's dependencies are registered earlier in `_SPECIALISTS`, since dispatch order is registration order and nothing else enforces it |
| `supervisor/` | The canonical production runtime. `loop.py` owns repository lifecycle/locks; `specialist_tier.py` owns isolated domain execution and retry; `planner_loop.py` owns bounded capability selection; `action_dispatch.py` owns permission/effect/repair dispatch; `state_tracking.py`, `evidence.py`, `models.py`, and `status.py` own their named contracts. `task.py` owns repository tasks; `mission_schema.py`, `mission_graph.py`, `mission_control.py`, and `mission_command.py` own the central mission task graph. `readme-agent supervise` accepts exactly one target: `--repo` or `--mission-task-graph`; both remain one supervisor authority. |
