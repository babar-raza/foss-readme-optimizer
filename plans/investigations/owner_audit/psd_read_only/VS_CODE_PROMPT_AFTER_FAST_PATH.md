# Strict VS Code prompt — run only after OPT-FAST-PATH-R8-R12 stops

## Where to run

Use the **existing VS Code window that already has the main `foss-readme-optimizer` checkout open**. Do not create a worktree, do not open a second folder, and do not start while `OPT-FAST-PATH-R8-R12` or any other process is writing/testing/committing in this repository.

Start a **new chat tab in that same VS Code window** named exactly:

`OPT-P0-README-ONLY-FOUNDATION`

Paste everything below into that tab.

---

You own one atomic implementation gate: `OPT-P0-README-ONLY-FOUNDATION`.

### 0. Collision and baseline gate — mandatory before any edit

1. Run from the root of the already-open `foss-readme-optimizer` checkout. Print `pwd`, `git status --porcelain=v1`, `git branch --show-current`, `git rev-parse HEAD`, and `git rev-parse origin/main`.
2. Confirm no other agent/process is writing, testing, committing, rebasing, or pushing in this checkout. If uncertain, inspect relevant process/lock/mission state read-only.
3. Require branch `main`, local HEAD equal to `origin/main`, no tracked modifications, and no active writer. Pre-existing untracked directories may remain only if you list them and never touch them.
4. If any requirement fails, STOP. Report exact state. Do not stash, reset, clean, rebase, pull, merge, or edit.
5. Read `AGENTS.md`, `plans/idea.md`, current governing docs, and `plans/investigations/owner_audit/**`, including the PSD addendum. Treat current source/tests as authority when prose is stale.

### 1. Reconcile work that landed while the prior lane ran

Before designing, inspect every commit after `91d9479b1e1fa12a9af41c1692b6f8f421db5f76`. Build a short change table: SHA, files, whether it closes/changes any README-only premise. If the fast-path lane already implemented part of this gate, reuse and test it; do not duplicate it. If it changed the relevant seams materially, adjust the plan and explain before editing.

### 2. Establish exact red fixtures

Use sealed local fixtures representing these exact source states (no network dependency in unit tests):

- `aspose-psd-foss/Aspose.PSD-FOSS-for-Python` at `2f6c746a8a3ebfaf686a7053e34abfad3a2fd8b3`, containing only `README.md` with `# Aspose.PSD-FOSS-for-Python` and `FOSS version of Aspose.PSD for Python`.
- `aspose-psd-foss/Aspose.PSD-FOSS-for-.NET` at `1fe2c6dc8014f26de3b79acbee25b15a8d26e903`, containing only `README.md` with `# Aspose.PSD-FOSS-for-.NET` and `FOSS version of Aspose.PSD for .NET`.

First add focused tests proving the current failure at the real seams:

- universal `README_TRUTH_FIELDS` cannot reach `FACTS_READY` honestly;
- the current universal template requires capability/install/example/license material that the tree does not prove;
- current PSD policy license is an unresolved `TODO(human)` and must never render;
- missing manifest/code cannot be represented as verified zero dependencies;
- disabled registry mode permits read-only analysis but not target mutation.

Run these tests and show they fail for the intended reasons before implementation.

### 3. Implement the smallest shape-aware extension of existing machinery

Do not create a parallel PSD pipeline and do not special-case the family slug in presentation code.

A. Add a typed, content-addressed repository-shape projection at the snapshot/fact boundary. Name it consistently with existing schemas. `README_ONLY_PLACEHOLDER` must require a tracked README and absence of every other tracked implementation/manifest/license/example/docs/build file; record exact qualifying paths, source revision, inventory/tree hash, and reason. Missing only a manifest is insufficient. A new tracked code, manifest, or LICENSE file must change shape and invalidate prior acceptance/cache.

B. Make shape an explicit input to `current_fact_acceptance_contract`/`FactAcceptanceContractV1` and its canonical hash. Add a shape-specific required-field set that accepts only repository-verifiable identity, repository state, and the narrow source-stated relationship. Do not weaken or change the existing code-bearing field set or visitor-render requirements.

C. Emit repository-owned facts for the README-only shape. Keep these separate:

- repository/tree fact: only README is present at the pinned revision;
- source statement fact: repository calls itself the FOSS version of Aspose.PSD for the platform;
- policy/context links: allowed commercial links, clearly nontechnical.

Do not convert `planned_descriptions.json`, `family_descriptions.json`, the products.aspose.org “coming soon” page, commercial APIs, or policy talking points into implementation facts.

D. Extend the existing presentation template/compiler with the smallest shape-aware sparse profile. The README-only candidate must use status/usefulness sections, not force `At a Glance`, `Key Capabilities`, `Installation`, `Quick Start`, API, dependency, example, capability diagram, or License sections. Do not disguise status prose under a capability heading. Keep code-bearing output unchanged.

E. Adapt existing checks/classification so code-dependent checks are explicit `not_applicable`, causally bound to the repository-shape fact and reason. Applicable hard check skip/error remains blocking. Never represent N/A as an empty success.

F. Route the final candidate through the existing claim-map, content-disposition, reconciliation, deterministic checks, evidence writer, cache, and lifecycle machinery. A reconciliation or coverage artifact containing `{error: ...}` must block candidate advancement for this gate.

### 4. Candidate acceptance contract

Both candidates must:

- preserve or causally reframe both original source units;
- state that the inspected repository currently contains only a placeholder README and no implementation/package artifacts;
- explicitly avoid documenting installation, dependencies, API, examples, supported capabilities/formats, and license until repository evidence exists;
- state only the narrow FOSS relationship present in the source README;
- provide useful watch/issues guidance and optionally a clearly labeled separate commercial-product link;
- contain no internal process language.

They must not contain any license name; install/import/package coordinate; dependency-free claim; PSD/PSB/AI feature support; conversion/layer/rendering claim; API symbol; code block; Mermaid diagram; “full-featured”; “Enterprise Edition”; or feature-parity/upgrade-path assertion.

### 5. Mandatory green proofs

Add and pass tests for:

1. exact README-only classification for both fixtures;
2. reclassification/cache invalidation after adding a code file, manifest, or LICENSE;
3. unchanged code-bearing truth and presentation fixtures;
4. exact forbidden sections/vocabulary absent;
5. complete accepted claim map;
6. explicit shape-backed dependency/check N/A and blocking applicable skip/error;
7. two-source-unit preservation and fail-closed reconciliation;
8. byte/hash repeatability across two identical runs;
9. distinct, correct Python/.NET identity without invented technical differences;
10. registry `mode: disabled` remains nonmutating.

Create a committed shape-aware 30-point acceptance rubric and score both real dry-run candidates 30/30. Correct abstention must earn the source-truth points; nonexistent features must never be required or rewarded.

Then run:

- focused new tests;
- all directly affected fact/presentation/check/reconciliation/cache/lifecycle tests;
- the repository's official full pytest command;
- `ruff check .`;
- `ruff format --check .`;
- `mypy src/readme_agent`.

Run two real governed local dry runs, read-only toward target repos, pinned to the exact PSD revisions above. Stop at local candidate generation/deterministic validation. Do not enable the PSD registry rows, write to their clones, commit to them, push, or open PRs.

Seal candidate README, facts/provenance, repository-shape evidence, contract/component hashes, plan, claim map, dispositions, reconciliation, check coverage with actual reasons, and checksums. Verify checksums.

### 6. Commit and stop discipline

Before commit, review the full diff for unrelated/stale-agent changes. If unrelated tracked changes appeared, STOP; do not absorb them.

One atomic commit only, with a message explaining source-shape truth, cache invalidation, sparse presentation, and both PSD proofs. Push only through the repository's already-governed automatic control-repo mechanism; never force-push.

After the commit, STOP and report:

- starting and final HEAD, commit SHA, and whether push succeeded;
- exact changed files and purpose;
- red tests observed before implementation;
- focused/full test counts and lint/type results;
- both candidate paths and SHA-256 hashes;
- both scores with rubric artifact path;
- exact check pass/fail/N/A/error counts and why each N/A is legitimate;
- preservation/reconciliation counts;
- `git status --porcelain=v1`;
- any residual risk or next smallest gate.

Do not claim portfolio readiness, agent approval, publication readiness, or 33/33 completion from this gate.

