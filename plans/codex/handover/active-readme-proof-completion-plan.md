# Active README proof completion plan

## Task identity

```text
task: L8-LOCAL-README-PROPOSAL-PROOF
title: Produce three fact-backed repository-specific README proposals
durable status: IN_PROGRESS
dependency: L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS (CLOSED)
next dependency consumer: L8-LOCAL-CENTRAL-AGENT-RESILIENCE
```

Objective: deliver one reviewer-ready, fact-backed, protected, reproducible README proposal for
Cells Java, 3D Java, and PDF Java through the canonical runtime, with a real independent verifier
and identical-rerun no-op proof.

## Required exit conditions

Do not close this task until all of the following are true:

- the document renderer complies with module-responsibility and size governance;
- every candidate reconstructs exactly from immutable source plus typed operations;
- all cited facts are selected, accepted, revision-bound, and conflict-free;
- protected commands, examples, terminology, limitations, and maintainer content are preserved
  unless a cited authoritative correction permits the exact loss;
- Cells contains no false Maven/package-acquisition claim;
- PDF contains no false Maven badge or stale version claim;
- 3D remains product-first without losing the valid commercial/FOSS relationship section;
- all three include a verified acquisition path and exact compiled minimal example;
- cross-pilot review rejects generic cloned prose or structure that obscures product identity;
- a separately implemented verifier accepts all three finished bundles;
- a tampered candidate, fact graph, operation, or checksum is rejected;
- the canonical supervisor produces the expected README proposal outcome for each pilot;
- the identical rerun produces no patch, no duplicate proposal, and no unnecessary LLM call;
- all official checks pass;
- committed evidence has a complete SHA-256 inventory and reproduction instructions; and
- requirements, task state, architecture documentation, and logs match the proven scope.

## Step 1: reconcile the previous child before editing

Run:

```powershell
git status --short
git log -6 --oneline

.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status `
  --mission-observer "<new-agent-name>"
```

Then validate the prior facts bundle without regenerating it:

```powershell
.venv/Scripts/python `
  plans/investigations/tools/verify_local_snapshot_and_product_facts_evidence.py `
  plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24
```

If the verifier's actual CLI differs, inspect `--help` or its parser rather than guessing. The
purpose is read-only reconciliation; do not overwrite the prior bundle.

Confirm:

- active task remains the README proof;
- the prior facts task remains closed;
- all five user-owned paths remain unchanged;
- current evidence checksums pass; and
- no previous claim is duplicated.

Record this predecessor reconciliation in the session log or eventual closeout evidence.

## Step 2: split the renderer before extending it

Investigate `document_renderer.py` and its history first. Preserve public behavior and hashes.

Recommended responsibility split:

1. `readme/document_structure.py`
   - Markdown heading model;
   - heading extraction through `markdown-it-py`;
   - line/byte offset conversion; and
   - GitHub heading-anchor construction.
2. `readme/document_templates.py`
   - template root and declared template inventory;
   - template loading;
   - template hash;
   - fact value formatting; and
   - overview, acquisition, and example fragment rendering.
3. `readme/document_operations.py`
   - SHA-256 helper for source/replacement bytes;
   - typed operation construction;
   - deterministic reverse-order operation application; and
   - stale-span rejection.
4. `readme/document_renderer.py`
   - only document-level orchestration and operation selection.

This is a suggested seam, not permission to move code blindly. Keep dependencies one-way and
public. Do not import `_`-private helpers across modules. If the exact split changes, update the
architecture module map accordingly.

Tests should split with responsibilities:

- structure parsing and byte offsets;
- template hash and deterministic fill;
- operation construction/application and stale source;
- pilot document orchestration.

Acceptance:

- no non-wiring module grows beyond the governance smell threshold;
- candidate bytes and hashes for all three committed pilots remain unchanged;
- existing focused tests remain green; and
- no new repository-specific `if` branch is added outside data/policy-driven rules unless a
  documented standard requires it.

## Step 3: build a genuinely separate verifier

The verifier must consume finished evidence, not call the producer's acceptance function and not
trust `independent-review.json`.

Recommended production seam:

```text
src/readme_agent/verification/readme_document_candidate.py
```

Recommended investigation verifier:

```text
plans/investigations/tools/verify_local_readme_proposal_evidence.py
```

The verifier should:

1. read the source bundle as immutable input;
2. validate `LocalProofManifestV1`, `ProductFactsV2`, `ReadmeDocumentPlanV1`, and
   `RepositoryPresentationPlanV1` schemas;
3. verify the root and per-pilot checksum inventories;
4. verify source revision/facts hash/candidate hash consistency;
5. reapply every operation to `original-readme.md`;
6. compare reconstructed bytes with `candidate-readme.md`;
7. verify `proposal.patch` with native Git apply/check in a disposable local repository;
8. recompute template hash;
9. independently validate fact citations and conflicts;
10. independently fingerprint protected content and authorize only cited corrections;
11. confirm exact verified example and acquisition path;
12. test the false-claim conditions for Cells and PDF;
13. verify the 3D relationship context remains after removing the opening callout;
14. compare all three outputs for suspicious generic/cloned prose while allowing shared safety
    structure;
15. report whether any candidate needs manual prose repair; and
16. emit a machine-readable verdict without modifying the producer bundle.

Write the separate result to a new, self-explanatory evidence directory, for example:

```text
plans/investigations/evidence/
  level8-local-readme-proposals-independent-verification-2026-07-24/
```

Do not edit the existing bundle in place merely to make its checks pass.

Required negative controls:

- one candidate byte changed;
- one cited fact changed or removed;
- one operation source hash changed;
- one checksum entry changed;
- one protected command/example removed without authoritative correction;
- one candidate copied from another pilot with only the product name replaced; and
- one fake `independent-review.json` that says accepted despite corrupted artifacts.

Every negative control must be rejected by the separate verifier.

## Step 4: strengthen cross-pilot and prose-quality review

The current producer's `product_specific_identity` boolean is not enough.

Add deterministic checks for:

- exact product identity and repository coordinates;
- product-specific audience/problem/capabilities/formats;
- correct example symbols and imports;
- correct repository URL and source revision;
- no coordinates or class names from another pilot;
- normalized paragraph similarity across pilot-specific prose;
- preserved repository-specific existing sections; and
- absence of placeholders, generic claims, and unsupported superlatives.

Use the existing agentic prose-quality capability only for editorial judgment that deterministic
checks cannot express. Its result remains advisory until deterministic factuality and boundary
checks pass. Record model route, prompt/template hashes, inputs, and verdict. A model cannot
authorize its own candidate.

The acceptance statement must distinguish:

- “deterministically valid”;
- “independently reconstructed”;
- “editorially accepted without manual prose repair”; and
- “not yet production proven.”

## Step 5: prove the path through the canonical supervisor

The current evidence tool calls contracts directly. Exercise the same path through
`readme-agent supervise`.

Start with the focused README domain so unrelated metadata/manual-UI findings do not obscure this
child's result:

```powershell
.venv/Scripts/readme-agent supervise `
  --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java `
  --domain readme_presentation `
  --execution-profile local_dry_run `
  --enable-dynamic-planning

.venv/Scripts/readme-agent supervise `
  --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java `
  --domain readme_presentation `
  --execution-profile local_dry_run `
  --enable-dynamic-planning

.venv/Scripts/readme-agent supervise `
  --repo aspose-pdf-foss/Aspose.PDF-FOSS-for-Java `
  --domain readme_presentation `
  --execution-profile local_dry_run `
  --enable-dynamic-planning
```

Before running, inspect the current CLI and execution-profile contracts. Do not paste credentials
into command lines or evidence. `local_dry_run` must not write a product remote.

For each pilot, collect:

- exact control commit;
- immutable target revision;
- normalized trigger/run identity;
- selected capability sequence;
- specialist result;
- work ledger;
- facts and plan hashes;
- validator/verifier outcome;
- terminal status and process exit code;
- evidence directory; and
- proof that product-remote writes remained zero.

Expected successful README result is `CONVERGED_PROPOSAL_READY`, not
`CONVERGED_NO_CHANGE`, on the first changed run. A full all-surface run may remain partial because
metadata or manual-UI work belongs to the next child; do not hide that distinction.

If dynamic planning cannot make the required path reliable, diagnose it. Do not replace the
canonical runtime with a fixture-only proof and call the gate passed.

## Step 6: prove identical rerun and failure controls

Run the accepted candidate again through an isolated, reproducible local state harness.

Prove:

- identical input produces zero document operations;
- candidate hash is unchanged;
- no duplicate proposal/effect record appears;
- deterministic work ledger is empty;
- no unnecessary LLM call occurs; and
- terminal status is an honest no-change form.

Also prove:

- stale source revision blocks;
- changed source span blocks;
- prompt-injected repository text cannot add operations/capabilities;
- missing selected fact blocks only the dependent operation;
- conflicting fact blocks the affected operation;
- verifier rejection cannot become proposal-ready; and
- evidence corruption prevents closure.

Use an isolated local Git remote/state backend where durable behavior is part of the assertion.
Do not write the control repository's production state ref for disposable scenario data.

## Step 7: produce final task evidence

Create a new evidence root rather than overwriting the checkpoint:

```text
plans/investigations/evidence/
  level8-local-readme-proposal-proof-accepted-2026-07-24/
```

It should cite the original producer bundle and contain:

- renderer-refactor compatibility report;
- focused and official test logs;
- three canonical supervisor run bundles;
- no-op rerun bundles;
- separate independent-verifier result;
- cross-pilot editorial/similarity report;
- negative-control results;
- exact reproduction commands;
- control and target revisions;
- tool/runtime versions;
- redaction statement;
- product-remote write count; and
- root SHA-256 inventory.

The final acceptance report must name any remaining scope explicitly:

- complete local multi-surface resilience remains the next child;
- `act`, staging, production App, and product effects remain later gates.

## Step 8: reconcile requirements and documentation

After evidence passes:

1. inspect every affected row rather than changing status mechanically;
2. update only the proven local-pilot scope in:
   - `RDM-003`;
   - `RDM-004`;
   - `RDM-007`;
   - `RDM-008`;
   - `RDM-018`;
   - `RDM-025`;
   - `L8-007`; and
   - `L8-014`;
3. keep portfolio, cross-surface, `act`, staging, and production clauses open;
4. regenerate normalized requirement inventory/coverage using the existing producer;
5. update `docs/architecture.md` for the renderer split and verifier seam;
6. append a dated log entry using `scripts/governance/append_log_entry.py`;
7. do not edit `plans/master.md` without fresh section-specific approval; and
8. run plan validation and semantic traceability.

Do not mark a requirement `IMPLEMENTED` merely because the three pilot candidates pass if the row
also requires portfolio or production evidence.

## Step 9: run the official gate

From repository root:

```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/governance/validate_plan_structure.py
actionlint
```

Use the repository's actual actionlint invocation if it is wrapped or installed elsewhere.
Capture stdout, stderr, exit code, exact commit, and checksums in evidence.

Inspect for repository-scoped helper processes after cancellation or completion. Never expose
environment variable values in diagnostic output.

## Step 10: commit and transition the durable task

Commit coherent code/evidence changes directly to `main` with:

```text
Co-Authored-By: <agent name and address required by repository policy>
```

Then transition one state at a time, only when the named evidence exists:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action transition `
  --mission-task-id L8-LOCAL-README-PROPOSAL-PROOF `
  --mission-to-status IMPLEMENTED `
  --mission-observer "<implementing-agent>" `
  --mission-reason "<exact committed implementation and scope>" `
  --mission-evidence "commit:<full-sha>" `
  --mission-evidence "plans/investigations/evidence/level8-local-readme-proposal-proof-accepted-2026-07-24/"
```

Repeat for:

```text
IMPLEMENTED -> VERIFIED
VERIFIED -> SCORED
SCORED -> CLOSED
```

Use a verifier identity distinct from the implementation producer for `VERIFIED`. Each transition
requires a real reason and exact evidence reference.

Finally claim the next task through the same supervisor:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action claim `
  --mission-observer "<next-agent-name>"
```

The expected next task is `L8-LOCAL-CENTRAL-AGENT-RESILIENCE`. If another task becomes eligible,
stop and inspect the graph/dependencies rather than overriding the controller manually.
