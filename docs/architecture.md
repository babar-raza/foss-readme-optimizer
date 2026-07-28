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

## Restartable production lifecycle (post-POC target)

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

This lifecycle describes the eventual production design, not the current README POC execution
stage. Per decision #78, broad GitHub App integration is Gate D and remains deferred until the
full-registry local candidates have passed independent agentic review, subsequent human
acceptance, and then the controlled Java PR proof. Gate-A work uses the `local_poc` profile and
read-only access plus push-neutered work clones; it never receives `remote_write`.

At Gate D, analysis will receive a freshly minted, repository-scoped GitHub App token with
contents-read permission, while a later effect job will mint a separate token with separately
reviewed permissions. Production token resolution will ignore ambient `GH_TOKEN`/PAT values. The
control repository's App variables/secrets, installation coverage, health aggregation, and
dead-man monitoring are Gate-D production prerequisites; they are not Gate-A implementation work.

## What the shipped legacy audit capability does

The original deterministic capability audits a GitHub repository's README for four specific,
independently-checkable promotional elements and closes only what's missing:

- `license_mentioned` — does the README state the repo's license?
- `products_org_link` — does it link to the FOSS catalog page (`products.*.org/...`)?
- `products_com_link` — does it link to the commercial edition (`products.*.com/...`)?
- `relationship_explained` — does it explain the FOSS-vs-commercial relationship, with that
  explanation actually co-located with a real commercial/FOSS link (not just prose)?

This was derived empirically: a live audit of 14 real Aspose FOSS READMEs (2026-07-17, see
`tests/fixtures/readmes/real_audit_2026-07-17/`) found repos in three distinct states — fully
compliant (hand-authored), fully blank, and partially compliant — and a binary "has our marker or
not" design can't represent that. See `readme_agent/readme/gap_detector.py`.

## Legacy deterministic capability pipeline

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

## Full-registry README POC pipeline

The canonical `local_poc` path is broader than the legacy capability above and is ordered:

```text
read data/products.json and derive the live denominator
  -> capture each repository's current default-branch README + immutable revision
  -> retain the exact original bytes as evidence
  -> inspect repository/product/platform and reconcile existing/product-agent claims
  -> use LLM judgment to draft verified product understanding and repository-specific presentation
  -> select relevant capabilities/sections/examples/validators automatically
  -> render a local candidate through bounded, hash-checked document operations
  -> retain candidate + exact diff + facts + plan + deterministic validation
  -> independent agentic review (separate judgment role)
  -> bounded repair until accepted or honestly blocked
  -> unchanged rerun/no-op proof
  -> portfolio manifest may declare Gate A only when every live registry entry passes
  -> human review/acceptance (Gate B)
  -> controlled Java PR proof (Gate C)
  -> broad GitHub App integration (Gate D)
```

Dynamic product/platform-aware selection is mandatory in the canonical `local_poc` profile:
`commands_supervision.py` constructs the specialist-selection and repair-planner clients
unconditionally for that profile. `--enable-dynamic-planning` remains an explicit compatibility
opt-in for other profiles; it is not required by the canonical local command (`ORC-009`). A
candidate file's existence is not acceptance: the lifecycle must reach agent approval plus no-op
proof before the artifact can enter the human-review queue (`PIL-015`).

The same supervisor also requires a typed maximum lifecycle stage (`L8-015`). Product-truth
qualification stops at `FACTS_READY`; composition qualification stops after deterministic
candidate validation; review, heterogeneous qualification, and full-registry Gate A advance only
after their dependencies close. Stage ceilings prevent an upstream repair from silently invoking
and invalidating expensive later phases. Gate-A fan-out additionally requires the frozen campaign
identity and single-writer/recovery contracts in `L8-016` and `L8-017`.

Terminal reuse is governed by the current versioned fact-acceptance contract (`L8-018`), not only
by a facts hash: required fields, eligibility, evidence polarity, render eligibility, and conflicts
are re-evaluated before a cached approval remains valid. Repository/dependency code used for
acquisition or examples runs only through the disposable OS-isolated executor required by
`L8-019`; the existing `example_execution.py` boundary remains useful for credential filtering and
timeouts but is explicitly insufficient as acceptance isolation. Composition then applies
`L8-020`: material preserved claims and generated claims share one complete accountability map, so
byte preservation cannot be misread as factual endorsement.

## Trust and reconciliation doctrine

Two principles govern every fact and claim this system handles, learned the hard way
2026-07-24 (`plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/`):
the resolver's Maven check queried the deprecated `search.maven.org` Solr index, which does
not index the `org.aspose` group at all, so it reported every published Aspose Java package
as `NOT_PUBLISHED` — and the README pipeline stripped a correct install and substituted
source-build, degrading a good README on a false premise. The fix required more than a
one-line endpoint change; it required these two principles becoming structural, not
case-by-case:

1. **Verify against authoritative ground truth; never trust a capability's output, a stored
   fact, an evidence bundle, a subagent report, or a manifest's self-declared name as if it
   were reality.** A resolver, a facts record, a prior evidence bundle, or a package
   manifest's declared name can all be stale or simply wrong (`ecosystems/resolver.py`'s
   Solr-vs-`repo1.maven.org` bug; a manifest's unpublished placeholder name). The independent
   verifier (`verification/readme_proposal_bundle.py::_verify_acquisition_ground_truth`)
   re-resolves the canonical coordinate LIVE at verification time rather than trusting what
   the candidate's stored facts claim — it is the concrete enforcement of this principle for
   package acquisition, and the same discipline applies to every other claim class.
2. **README content is untrusted *input to investigate*, and a reusable fact source once
   autonomously verified — never blindly trusted, and never discarded as noise just because
   it is unverified.** A repository's own README carries real candidate facts (install
   coordinates, examples, capabilities). The system must corroborate each against
   authoritative repository/registry evidence rather than reflexively rejecting or
   overwriting it. The cells-java Maven `<dependency>` block was the exact failure mode this
   principle exists to prevent: a true, corroborable README claim was discarded as noise
   instead of being verified and kept. Today, corroboration happens by construction rather
   than by promotion: a `readme_claim`-sourced fact can only ever be
   `unverified`/`conflicting`/`blocked` (`facts/schema_v2.py`'s own guard — "README prose is
   untrusted data and cannot be verified by itself") and never wins fact resolution on its
   own; what actually keeps a true claim is an independently-sourced, authoritatively-derived
   fact (e.g. `facts/acquisition.py`'s receipt-backed `external_registry` record) that happens to agree
   with it, so the resolved value matches the README precisely when the README was right.
   Directly promoting a corroborated `readme_claim` fact itself to `verified` is not yet
   built — an honest, open gap (`RDM-025`), not silently claimed as done.

The "aspose {family} foss" coordinate rule (`ecosystems/foss_coordinate.py`) is principle 1
applied to package acquisition specifically: derive the canonical FOSS coordinate per
ecosystem and check it against that ecosystem's authoritative registry (Maven →
`repo1.maven.org`, not the Solr search index; C++ → NuGet, where the Aspose C++ FOSS packages
actually ship, not Conan/vcpkg), never the manifest's self-declared name and never a
similarly-named commercial package.

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
| `registry/` | `data/products.json` + `config/policies/*.yml` loading, the allow-list gate; `priority.py` validates `data/platform_priorities.json` and gives canonical portfolio runs Python -> .NET -> Java -> C++ -> TypeScript -> Rust -> Go order while retaining stable within-ecosystem registry order; `surface_ownership.py` materializes the five control classes and their allowed operations, permissions, and rollback; `discovery.py` (GitHub org scan/classify/merge core, shared with `scripts/data-refresh/update_products_registry.py`) and `self_heal.py` (supervise-time registry drift self-heal, `CORE-034`) |
| `preflight/` | GitHub + LLM connectivity checks, fail-closed |
| `gitsafety/` | Clone, push-neuter, pre-push hook, independent verification; `process.py` owns bounded subprocess-tree cancellation so a timed-out git operation cannot leave credential/git descendants holding pipes |
| `inspection/`, `ecosystems/` | Git metadata; generic multi-manifest file inventory (`FileInventory.manifest_paths`, data-driven from `ecosystems.registry.known_manifest_globs()`); seven real per-platform manifest parsers (`java.py` -- pom.xml or build.gradle, `python.py`, `dotnet.py`, `typescript.py`, `go.py`, `cpp.py`, `rust.py` -- Cargo.toml via stdlib `tomllib`). Python package/public-consumer truth is split across typed contracts (`python_api_schema.py`), manifest/source-root discovery (`python_package_layout.py`), module/re-export inspection (`python_public_api.py`), and class-member extraction (`python_symbol_members.py`); .NET public-example normalization and proof share the conservative source-derived type/namespace index in `dotnet_public_types.py`, so the stored candidate, compiler input, and recorded fully qualified symbols remain identical; TypeScript package/public-consumer truth uses typed contracts (`typescript_api_schema.py`) and package/export/declaration projection (`typescript_package_layout.py`) before the pinned compiler proves the built consumer surface. Rust truth adapts the pinned aspose.org regression contract through responsibility-sized `rust_*` modules: package/lib identity, tree-sitter module and `#[path]` resolution, unrestricted-public visibility, re-exports, types, fields, variants, traits, implementations, rustdoc, and directionally explicit format evidence. Opt-in live install-path resolution (`resolver.py`) checks the authoritative registry per ecosystem -- Maven Central, PyPI, npm, NuGet, the Go module proxy, crates.io, plus Conan Center/vcpkg for C++ (`foss_coordinate.py`'s "aspose {family} foss" rule resolves C++ through NuGet instead, where the real Aspose C++ FOSS packages ship). |
| `profile/` | `RepositoryProfile`/`DetectedEcosystem` (`schema.py`), `build_profile()` (`detector.py`) -- multi-ecosystem detection built on `inspection/`+`ecosystems/`, one scan, one source of truth, not a second parallel scanner. Cached/API/clone profiling carries the observed source revision into downstream fact provenance. |
| `repository_snapshot.py` | `RepositorySnapshotV1` captures one immutable revision, absolute clone root, README and Git-tree inventory checksums, package roots, capture time, and provenance. The supervisor binds it through a context-local scope across every specialist and planner capability; nested clone/profile calls reuse that view without another remote probe, and stage boundaries fail closed on drift. |
| `facts/` | `schema.py` retains the narrow V1 compatibility contract. `schema_v2.py` defines the provenance-complete required-field inventory; `acceptance_contract.py` versions required-field membership, eligibility, evidence-polarity, root-role selection, conflict, classification, and visitor-render semantics so stale cached truth cannot inherit a terminal label; `migration.py` explicitly converts V1 without inventing missing values; `provider.py` reconciles policy and repository facts for both the facts and metadata capabilities, while `context.py` binds the exact run-scoped graph so downstream stages cannot silently recollect a different view. `root_role_schema.py`, `root_role_evidence.py`, and `root_roles.py` preserve every detected package root as typed evidence and deterministically bind visitor facts to the sole distributed-product root; ambiguous roots remain `unknown`. `manifest_facts.py` derives identity, coordinate, compatibility, and release facts only from that binding; `repository_ingestion.py` combines those facts with mechanically verified policy assertions and license evidence. `policy_evidence.py` validates policy-selected technical assertions against exact snapshot paths and anchors, and `evidence_polarity.py` binds each anchor to a fact ID, immutable revision, exact excerpt, and bounded context before distinguishing positive implementation proof from explicit, subject-bound constraint proof. Curated README content therefore remains high-value input but cannot become accepted product truth merely because its wording or API name occurs in the repository. `drafting_context.py` supplies bounded evidence context with repository-owned example sources ahead of broad implementation files, while `agentic_drafting.py` remains responsible for the structured proposal itself. `code_normalization.py` converts model-authored typographic quote delimiters to parser-safe ASCII before the exact normalized source is compiled; `python_example_normalization.py`, `typescript_example_normalization.py`, and `rust_example_normalization.py` reduce generated import inventories, stale package imports, or malformed consumers to one source-derived, constructible public consumer; `example_quality.py` rejects unsuitable generated examples; `repository_examples.py` extracts bounded repository-authored README examples as untrusted compiler candidates; `problem_grounding.py` deterministically reuses exact verified capability text when an interpretive problem draft is ungrounded, avoiding unsupported paraphrases and redundant model repair calls; `interpretive_resolution.py` retains already-proved technical facts across bounded repair attempts and re-runs interpretive grounding against the exact final selections; and `render_views.py` converts selected structured facts to typed visitor-facing phrases without leaking internal keys or policy codes. Interpretive facts retain their selected grounding fact IDs, while structured/internal-token text has no prose-eligible view. `example_execution.py` remains a bounded, secret-filtered host diagnostic whose typed result is permanently truth-ineligible. `isolated_execution_schema.py`, `isolated_execution_inputs.py`, and `isolated_execution.py` define and enforce immutable-image, named-volume, non-root, no-network, read-only-root, cgroup-bounded Docker execution; `isolated_docker_control.py` requires immutable image identity plus converged wait/terminal-state evidence, and `isolated_cleanup.py` retries idempotent removal and accepts only explicit Docker not-found plus empty-listing responses as complete cleanup provenance. `compiled_consumer_schema.py` and `compiled_consumer.py` bind exact example bytes, selected public bindings, source paths, and source checksums to one isolated compiler result; `java_example_verifier.py`, `dotnet_example_verifier.py`, `cpp_example_verifier.py`, and `go_example_verifier.py` apply that contract with digest-pinned official toolchains and network-disabled builds. `python_consumer.py`/`python_example_verifier.py` install the pinned Python source and require exact public imports; `typescript_toolchain.py` hash-locks inert compiler archives, while `typescript_consumer.py`, `typescript_consumer_driver.js`, and `typescript_example_verifier.py` build a deterministic package artifact, resolve exports/declarations through TypeScript itself, exclude private/protected/hash members, and compile the exact consumer in immutable network-denied Node. Rust separates networked metadata/vendor acquisition (`rust_dependency_acquisition.py`, no repository-code execution, no credentials, immutable image, exact Cargo lock and checksums) from the truth-eligible `rust_consumer.py`/`rust_example_verifier.py` boundary, which compiles a separate external consumer with `cargo check --locked --offline` under the network-denied executor. `local_verification.py` fails closed unless an ecosystem supplies such a truth-eligible adapter, while its old host toolchain paths remain diagnostic only. `resolution.py` applies source precedence and records conflicts; `gating.py` maps facts to dependent surfaces, rejects non-selected citations, and validates technical claims; `protected_content.py` fingerprints commands, examples, terminology, limitations, and maintainer regions through `markdown-it-py`. |
| `ecosystems/registry_request.py`; `facts/acquisition*.py` | `registry_request.py` is the single coordinate-to-authoritative-request-URL seam used by both live resolvers and persisted-receipt validation. `acquisition_schema.py` defines checksum-complete authoritative-registry and isolated-source receipts and rejects a response URL that does not exactly match its coordinate. `acquisition_pins.py` projects Python package source, TypeScript compiler/archive/built-artifact, and Rust lock/vendor/config checksums into one workload-pin contract. `acquisition.py` gives a published registry coordinate precedence and permits source acquisition only after receipt-backed registry absence plus a successful pinned, network-denied isolated build; registry uncertainty, incomplete dependency inventories, and host-only builds remain blocked. The acceptance-contract hash includes this boundary so stale cached installation truth is recollected. |
| `presentation/` | `schema.py` defines `RepositoryPresentationPlanV1`; `markdown_structure.py`, `claim_validation.py`, `git_patch.py`, and `planner.py` provide deterministic structure, factuality, and native-Git patch proof; `document_planner.py` bridges fine-grained README operations into the repository surface plan. |
| `readme/` | Legacy gap/render compatibility remains in `gap_detector.py`, `renderer.py`, and `candidate_pipeline.py`. The complete-document pipeline is split by responsibility (no monoliths): `assessment.py` and `assessment_claims.py` inventory source-bound sections and material claims while treating prompt-like repository text as untrusted data; `claim_accountability_models.py` owns the typed accountability contracts, `claim_accountability.py` inventories every inherited/generated content unit as fact-bound, owner-required, uncertain, correction-required, unjustifiably lost, or unbound without treating preservation as approval, and `claim_accountability_validation.py` rechecks exact spans, complete inventories, correction operations, and approval blockers; `agentic_composition.py` orchestrates authoring and repair behind its unchanged public seam, `agentic_composition_models.py` owns typed contracts, `agentic_composition_grounding.py` materializes accepted visitor facts, and `agentic_composition_validation.py` enforces source/fact/assessment/prompt/schema bindings; `agentic_operation_coverage.py` fails closed when an actionable decision has no bounded edit; `acquisition_contracts.py` identifies contradicted package claims and exact stale coordinate-version spans; `document_plan.py` defines the typed byte-span plan and carries the complete claim-accountability map; `fact_grounding.py` locates literal selected-fact phrases and `claim_map.py` binds those phrases to exact candidate/source bytes; `document_structure.py` parses Markdown headings, sections, fenced-code source spans, and GitHub anchors; `document_templates.py` owns template loading/hashing and ecosystem-specific fact-to-section prose; `document_operations.py` applies hash-checked operations in reverse order; `document_hashing.py` owns shared SHA-256 helpers; `header_visual_models.py` defines the factual title, badge, and Mermaid contracts, `header_badges.py` selects only registry-verified package/version and verified-license badges, `header_visual.py` renders sanitized repository-specific diagrams, `header_visual_validation.py` validates their grammar and provenance, and `document_header_visual.py` compiles them into bounded title/header/diagram operations while removing visitor-visible comments; `document_reconciliation.py` turns unresolved section assessments into exclusive, bounded withholding operations while retaining their exact source evidence; `document_link_hygiene.py` removes unbound Aspose targets without altering protected code, `document_links.py` materializes verified contextual bindings beside the exact accepted example, and `document_terminology.py` plans bounded Enterprise Edition corrections; `document_renderer.py` orchestrates candidate construction over the immutable `document_render_context.py`, while `document_opening.py`, `document_acquisition.py`, `document_examples.py`, `document_limitations.py`, and `document_release.py` independently select bounded operations for their respective sections; and `document_validation.py` independently reconstructs the marker-free candidate, validates protected content, and rejects an absent, stale, or incomplete accountability map. Legacy complete-document markers remain readable only for migration; production provenance lives in the durable document plan and evidence. The pre-extraction contracts, before/after map, and frozen hashes are recorded in `docs/readme-composition-seams.md`. |
| `llm/` | Strict-schema client (live + fixture), `prompts.py` (facts+policy only). Wave 5 (decision #36): `planner_client.py` (`PlannerTurn`, `PlannerClient` Protocol, `LivePlannerClient`/`FixturePlannerClient`) -- a separate thin family, not a reuse of `LLMClient`, since a tool-call planning turn has no `content` to validate against the strict-schema client's `LLMBlockResponse`; promotes Wave 1's spike `chat_raw()` logic into tested production code. `verifier_client.py` supplies the live-proven forced-tool transport and `reviewer_client.py` binds the independent README verdict schema to it, preventing freeform-JSON corruption while retaining the analysis result seam. Wave 8.5 (`GOV-024`/`AGT-008`): `prompt_schema.py`/`prompt_registry.py` -- a categorical, schema-validated prompt store (mirrors `capabilities/registry.py`'s eager-registration pattern), replacing flat `.txt` files. `planning_prompts.py` is the only assembly seam for supervisor, specialist-selection, and repair-planning messages; `prompt_source_audit.py` finds executable prompt references and prohibited inline literals; `prompt_hygiene.py` reconciles that source inventory with every prompt file, route, owner, consumer, output contract, documentation row, and dependency-scoped invalidation hash before paid fan-out. `call_schema.py`, `call_transport.py`, `call_ledger.py`, and `bundle_accounting.py` account every physical provider attempt, fixture use, and cache reuse without retaining prompt/response content; unique IDs and per-job totals reconcile into run, revision-bundle, and portfolio manifests, while pre-ledger bundles remain `UNKNOWN_LEGACY`. |
| `validation/` | 10-rule deterministic registry |
| `golden_set/` | Non-mutating model-route qualification. `scenarios.py`/`harness.py` score the real supervisor prompt without dispatch; `review_fixtures.py`, `review_scenarios.py`, `review_corpus.py`, and `review_harness.py` provide ProductFactsV2-grounded seven-ecosystem reviewer controls and run the real independent-review prompt; `qualification.py` aggregates distinct planner/reviewer sessions against the 100-evaluation, three-session, 95% gate; `auto_disable.py` disables a route below the governed floor; `aggregation.py` reads durable production metrics. |
| `license/`, `links/` | License classification plus the contextual-linking boundary. `links/catalog_models.py` and `catalog.py` define and load checksum-valid, parent-domain-pure `.com`/`.org` targets through one typed seam; `allocation.py` uses `markdown-it-py` to measure pre-link visible prose and verified code blocks before resolving automatic or configured ceilings; `occurrences.py` counts Markdown, image, autolink, HTML, raw, subdomain, and repeated Aspose URL occurrences consistently; `contextual_models.py`, `contextual_matching.py`, `contextual_selection.py`, and `contextual_validation.py` bind accepted public API examples to strongly matched verified articles and fail closed on catalog, placement, occurrence, or budget drift; `runtime_context.py` loads the registered policy and catalogs for the supervised document seam; and `terminology.py` scopes deterministic `Enterprise Edition` correction and validation to visitor-facing Aspose product language without rewriting protected code or non-Aspose fixtures. `validator.py` retains the generic HTTPS/live reachability check. |
| `evidence/` | Redaction and atomic writes; `manifest_v3.py` binds trigger/checkpoints/facts/plan/authorization/verifier/effects/requirements, and `writer.py` maintains its checksum inventory. |
| `commands.py`, `commands_*.py` | Stable CLI façade plus responsibility-sized compatibility, supervision, governance, and lifecycle handlers. `commands_lifecycle.py` owns the authoritative matrix, recovery sweep, and health report commands. Legacy verbs stay read-only. |
| `orchestrator.py` | Compatibility inspection/reporting and candidate-evidence wiring. Its legacy `run_repo()` never commits; production mutation is not dispatched here. |
| `effects/` | Small effect primitives reachable only through registered capabilities; `local_readme_commit.py` owns the local verified-README commit primitive. |
| `github_api/` | Wave 7b (decision #41): `client.py` -- shared, read-only GitHub REST API client (GET-only), extending `scripts/update_products_registry.py`'s live-proven pagination/rate-limit pattern rather than a fourth/fifth independent reimplementation. `repo_summary`/`list_contributors`/`list_languages` (7b), `list_releases` (7c), `get_community_profile` (7e -- live-verified its `files` object reports recognition for exactly `readme`/`license`/`code_of_conduct`/`contributing`/`issue_template`/`pull_request_template`, never `security`/`support`) |
| `capabilities/` | Wave 2 onward: typed registry/dispatcher plus one module per capability. `contracts.py` materializes strict Pydantic input and output models from every registered manifest; dispatch rejects malformed arguments, undeclared wiring arguments, missing permissions, and executor output that violates its contract. `compatibility.py` owns the ecosystem-to-build/package/registry vocabulary, validates manifest declarations at registry construction, and supports repository-profile filtering. Registry construction also rejects incomplete permission declarations, unknown validators, invalid evidence fields, and mutating capabilities without evidence/idempotency/retry contracts. Read-only capabilities inspect/profile/audit/propose; `plan_readme_composition.py` is the domain-scoped agentic authoring proposal over one immutable snapshot and verified fact graph, while `build_presentation_plan.py` independently re-derives facts, bounded document operations, claim spans, and ownership before verification. `commit_readme_write.py` is the `readme_presentation` domain's `local_write` effector and `open_presentation_pr.py` (decision #51) is its first `remote_write` effector. Both declare idempotency/reconciliation/evidence contracts, require `mode: full`, and run through `effect_ledger.dispatch_gated_effect()`. The PR effector uses `github_api/write_client.py` and a dedicated never-neutered PR clone, has one real Cells/Java proof, and is deliberately not yet wired into a specialist or the normal supervisor path. `prepare_visual_asset.py` remains manual-delivery preparation only. `domains.py` and `registry.all_tool_schemas(caller_domain=)` enforce specialist-domain isolation independently of orchestration-framework tool scoping. |
| `state/` | Durable Git-ref CAS state and leases. `schema.py` keeps V1 as an explicit migration source and makes `RunStateV2` current; `migrations.py` fails closed on unknown versions. `git_backend.py` bulk-loads exact remote ref names into numeric isolated refs so case-distinct historical names cannot collapse on Windows. `lifecycle_schema.py` defines trigger/checkpoint/health contracts; `mission_goal_schema.py` defines governed goal, contribution, portfolio-scoreboard, exact-next-task, and closeout-evidence records; `lifecycle.py` coordinates acceptance, transitions, resume, and active context; `cas.py`, `checkpoints.py`, and `recovery.py` own their named persistence responsibilities; `trigger_v2.py` normalizes provider identity; `health.py` aggregates portfolio health. Existing domain, freshness, effect, and model-route records remain additive within the same per-repository state. |
| `retry.py` | Six typed, bounded external-operation policies. Tenacity supplies exponential jitter; HTTP adapters classify retryable transport/status failures and honor GitHub rate-limit headers. |
| `specialists/` | `registry.py` owns registry-driven domain ordering, dependency checks, and complete domain registration. `readme_reconciliation.py`, `github_generated_surface_audit.py`, `package_release_audit.py`, `metadata_presentation.py`, `community_files_presentation.py`, `cross_surface_validation.py`, `readme_presentation.py`, `visual_preparation.py`, `presentation_benchmarking.py`, and `independent_verification.py` run through typed capability dispatch. `metadata_presentation.py` dispatches only `propose_metadata_changes(org_repo)`; that capability independently derives facts through `facts/provider.py`. `readme_presentation.py` alone reaches the local README effect, only after its candidate has a structured, executable presentation plan and passes factuality and independent-verification gates. `readme_presentation_review.py` owns the separate gate node, `readme_review_validation.py` owns deterministic candidate/bundle dispatch and reconstruction, and `readme_review_repair.py` owns reviewer-instructed regeneration plus full revalidation; together they propagate only the final accepted candidate. |
| `specialists/readme_factuality.py` | Pre-effect factuality boundary for README candidates. It obtains facts and acquisition evidence through separate registered capabilities, rejects positively false package claims and protected-content loss, and supplies a fact hash to `readme_presentation.py` before its independent verifier and effect ledger are reachable. |
| `specialists/metadata_presentation.py` | Dispatches only the metadata proposal capability. That registered boundary accepts `org_repo` alone and independently re-derives ProductFactsV2 through `facts/provider.py`; caller-supplied eligibility, citations, URLs, and product fields are rejected by the capability input contract. |
| `supervisor/` | The canonical production runtime. `loop.py` owns repository lifecycle/locks; `stage_limit.py` defines typed local proof ceilings so an active facts task cannot invoke composition or review; `product_truth.py` prepares, caches, persists, and invalidates one revision- and prompt-bound ProductFactsV2 graph before planning or specialist execution; `portfolio_stage_cache.py` validates revision-addressed, checksum-complete bounded-stage bundles under current fact contracts so sequential portfolio slices advance without repeating accepted work; `execution_context.py` carries run-scoped proposal-only and fact-graph boundaries without adding a second controller; `specialist_tier.py` owns isolated domain execution and retry; `planner_loop.py` owns bounded capability selection; `action_dispatch.py` owns permission/effect/repair dispatch; `finding_status.py` classifies specialist findings/proposals and `work_ledger.py` deterministically prevents them from collapsing into false no-change or premature planner stop results; `local_poc_evidence.py` materializes snapshot/fact/candidate boundaries and `local_poc_review_evidence.py` writes deterministic review, independent verdict, repair history, final verdict, and unchanged-rerun proof into that same revision-addressed bundle. `state_tracking.py`, `evidence.py`, `models.py`, and `status.py` own their named contracts. `task.py` owns repository tasks; `mission_schema.py`, `mission_graph.py`, `mission_control.py`, and `mission_command.py` own the central mission task graph, while `mission_goal_guard.py` derives the dynamic durable lifecycle scoreboard and rejects contribution-free closure. `readme-agent supervise` accepts exactly one target: `--repo`, `--registry`, or `--mission-task-graph`; all remain one supervisor authority. |
