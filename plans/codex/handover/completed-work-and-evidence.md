# Completed work and evidence

This document distinguishes code that exists, evidence that was independently reproduced, and
evidence that is currently only asserted by the same producer that created the artifact.

## Starting point and resequencing

The user clarified that GitHub App provisioning belongs after the system is proven locally,
under `act`, and in staging. The prior Wave-2-first production sequence had produced substantial
infrastructure but no convincing idea-complete local product result.

The implemented response was:

- preserve the existing runtime, registry, safety, facts, specialists, lifecycle, and evidence
  foundations;
- keep `supervise` as the one runtime;
- split the active pre-production parent into ordered child tasks under the same mission state;
- repair false convergence before extending presentation behavior;
- prove immutable facts before generating complete README proposals;
- defer production credentials and target effects.

The governing investigation is:

```text
plans/investigations/preproduction-idea-fidelity-gate-2026-07-24.md
```

## Truthful baseline restoration

### Implementation commit

```text
946081e81c670d84d49604b1fefb712226eb886c
fix(supervisor): make remaining work authoritative
```

### Defects found

Three live local Java pilot runs showed that the runtime could report
`CONVERGED_NO_CHANGE` even when its own specialist output contained:

- `STALE_NONCOMPLIANT`;
- missing or blocked facts;
- failed presentation dimensions;
- unattempted useful capabilities; or
- a planner prose response that explicitly named more work but returned no tool call.

PDF Java also called the explicit `stop` capability while still naming an unresolved
`products_org_link` gap.

### Changes delivered

- Added `supervisor/finding_status.py` to deterministically classify specialist details.
- Added `WorkLedgerV1` in `supervisor/work_ledger.py` as the remaining-work and stop authority.
- Added `PARTIAL_WITH_FINDINGS` for unresolved findings.
- Added `CONVERGED_PROPOSAL_READY` so a completed proposal is not mislabeled no-change.
- Made planner implicit no-tool stopping invalid while mapped work remains.
- Rejected explicit `stop` calls while the work ledger remains non-empty.
- Made prompt registry loading independent of import order and current working directory.
- Reconciled supervisor tests based on the fixture's actual findings rather than mechanically
  changing expectations.
- Split the pre-production gate into six durable child tasks in the existing graph.

### Evidence commit

```text
05589be23d37a398231975c9d72abc893980a2c2
test(preproduction): preserve truthful baseline proof
```

Evidence root:

```text
plans/investigations/evidence/level8-preproduction-truthful-baseline-2026-07-24/
```

It contains:

- before-repair false-success evidence;
- after-repair evidence for 3D, Cells, and PDF Java;
- focused runtime-test output;
- complete official-check output;
- nested and root SHA-256 inventories;
- reproduction instructions; and
- `truthful-baseline-acceptance.json`.

The durable task `L8-PREPRODUCTION-TRUTHFUL-BASELINE` is `CLOSED`.

## Immutable repository view and product truth

### Implementation/evidence commit

```text
5e31f9c11e7a54d9acc8638b23e1f85fc799ed9a
feat(facts): bind pilot truth to immutable snapshots
```

### Changes delivered

#### `RepositorySnapshotV1`

`src/readme_agent/repository_snapshot.py` captures:

- repository identity;
- immutable source revision;
- local snapshot root;
- README path and SHA-256;
- tracked inventory SHA-256;
- package roots;
- capture time; and
- provenance.

The supervisor binds a single snapshot for nested facts, profile, specialist, renderer, and
verifier work. Snapshot reuse fails closed if:

- the README checksum changes;
- the inventory checksum changes;
- the repository identity changes; or
- a nested capability attempts to observe another repository.

#### Complete pilot `ProductFactsV2`

The three policy profiles gained explicit product-truth evidence sufficient for their pilot
READMEs. New ingestion and verification modules include:

- `facts/repository_ingestion.py`;
- `facts/policy_evidence.py`;
- `facts/local_verification.py`; and
- the existing `facts/provider.py` integration.

The accepted pilot facts cover:

- identity;
- audience and problems solved;
- capabilities and formats;
- platforms and compatibility;
- installation coordinates and verified acquisition;
- minimal example;
- documentation and support;
- release/maintenance state;
- limitations and license; and
- commercial/FOSS relationship.

Mechanically checkable facts are bound to repository paths, symbols, manifests, revision, or a
timed external lookup. Policy-approved intent remains distinguishable from mechanical evidence.

#### Acquisition and example verification

For all three Java pilots:

- Maven registry checks reported the configured artifacts were not published;
- a disposable source build was used instead of inventing a package install;
- a policy-selected minimal Java example compiled against that build;
- no write credential was passed to build/example execution; and
- the snapshot content remained unchanged.

The known false Cells Maven claim was therefore rejected rather than propagated.

### Evidence

Evidence root:

```text
plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24/
```

Important files:

- `immutable-snapshot-and-product-facts-proof.json`;
- `independent-factuality-review.json`;
- `official-checks-attempt-4.log`;
- `sha256sums.txt`; and
- `reproduction-command.txt`.

The separate verifier is:

```text
plans/investigations/tools/verify_local_snapshot_and_product_facts_evidence.py
```

Its committed verdict is accepted for all three current pilots and three historical scenarios.
The final recorded official gate reported:

- Ruff passed;
- formatting passed;
- mypy passed;
- plan validation passed with warnings only;
- actionlint passed; and
- 1,338 non-live tests passed, 18 excluded.

The durable task `L8-LOCAL-IMMUTABLE-SNAPSHOT-AND-FACTS` is `CLOSED`.

## Complete-document README proposal foundation

### Implementation commit

```text
5d2256b559890353d1a1b3e380cb848f2c831b15
feat(readme): add complete document proposal planning
```

### Contracts and modules delivered

#### `ReadmeDocumentPlanV1`

`src/readme_agent/readme/document_plan.py` defines:

- immutable base revision;
- facts hash;
- template hash;
- source-document hash;
- presentation-span adoption metadata;
- typed operations;
- source byte spans and expected hashes;
- replacement hashes;
- fact citations;
- protected-content treatment;
- rationale;
- validators;
- rollback; and
- stop conditions.

Supported operation vocabulary is:

- `preserve`;
- `insert_before`;
- `insert_after`;
- `replace`;
- `move_exact`; and
- evidence-backed `remove`.

#### Complete document rendering

`src/readme_agent/readme/document_renderer.py`:

- parses Markdown headings with `markdown-it-py`;
- adopts the complete existing README byte-for-byte into one presentation span;
- produces source-span operations against the immutable inner bytes;
- adds a verified product overview and navigation;
- adds or corrects source-build acquisition;
- adds a verified minimal example;
- removes specific unsupported registry/promotion claims;
- corrects a manifest-backed release version;
- renders only from selected accepted facts and templates; and
- produces a deterministic candidate and plan.

#### Independent re-derivation seam

`src/readme_agent/readme/document_validation.py` and
`src/readme_agent/verification/checks.py` can:

- verify source, facts, template, and candidate hashes;
- reconstruct the candidate from the plan;
- validate every fact citation;
- reject stale or conflicting facts;
- validate protected-content losses;
- check the selected minimal example and overview are present; and
- compare a candidate with a fresh independent render.

This is integrated into `render_readme_candidate`, `build_presentation_plan`, the factuality
specialist, and the existing independent verifier seam.

#### Templates

Fact-filled templates were added under `templates/readme/`:

- `product-overview-and-navigation.md`;
- `verified-minimal-example.md`; and
- `verified-source-acquisition.md`.

Their bytes join the document template hash, so template changes invalidate stale plans.

### Pilot-specific deterministic outcomes

| Pilot | Immutable revision | Operations proven in the candidate bundle |
|---|---|---|
| Cells Java | `2be25d979d1f3bf2875a1798aed62a16efab6619` | Add overview/navigation, replace false Maven installation with verified source build, add verified minimal example |
| 3D Java | `605f67d1192fee1881078dfd53d37b8cb29623ba` | Add overview/navigation/source acquisition, add verified minimal example, remove opening promotional callout while preserving relationship context |
| PDF Java | `1ed0a411171e49758b462321ed24bff568bb4444` | Add overview/navigation/source acquisition and example, remove unsupported Maven Central badge, correct declared version to manifest-backed `26.6.0` |

Candidate SHA-256 values:

```text
Cells Java: 43fae20ac1561fbe3ba094310be514b1d3d5bf21ea474a1f9d88ea35af5d7fba
3D Java:    9ed32c5eeabfb70f6e0fc98c607b337dbb1944b1fb2eb5dc0d7cdef971ccee8b
PDF Java:   1dc2ffd5ffb692f5239fd910f755de1704400f64a931656e37bc982c0bdb4030
```

### Test result

At implementation commit `5d2256b`, the canonical offline gate passed:

- Ruff check;
- Ruff format check;
- mypy;
- plan validation;
- actionlint; and
- 1,344 tests passed, 18 deselected.

The focused unit coverage includes:

- exact byte preservation during span adoption;
- Cells false-install correction;
- PDF badge/version correction;
- 3D promotional-callout correction;
- unchanged candidate no-op; and
- rejection of a tampered candidate.

### Evidence checkpoint

Evidence commit:

```text
ab8a54d9e68eefe25a030498e217a9a62c64c302
chore(evidence): checkpoint local README proposals
```

Evidence root:

```text
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/
```

Each pilot bundle contains:

- `original-readme.md`;
- `candidate-readme.md`;
- `proposal.patch`;
- `product-facts-v2.json`;
- `readme-document-plan-v1.json`;
- `repository-presentation-plan-v1.json`;
- `document-validation.json`;
- `independent-review.json`; and
- `artifact-sha256.json`.

The root contains:

- `local-proof-manifest-v1.json`;
- `reproduction-command.txt`; and
- `sha256sums.txt` with 29 validated entries.

The producer reported:

- all three first runs executable;
- all three review verdicts accepted;
- all three identical reruns no-op;
- no unnecessary LLM call for the deterministic rerun; and
- zero product-remote writes.

## Why the active task is not closed

The latest evidence is useful but does not yet satisfy the task's full independent-proof claim.

### Producer and reviewer are the same executable

`collect_local_readme_proposal_evidence.py` creates the candidate, calls validation, computes the
review checks, writes `independent-review.json`, and then accepts its own manifest. The
`reviewer` string names an independent reviewer, but there is no separately implemented verifier
process that reads the finished bundle without trusting the producer.

Treat these files as producer self-checks until a separate verifier reproduces them.

### Renderer violates the repository's size/concern rule

`src/readme_agent/readme/document_renderer.py` is 474 lines. It contains Markdown structure
parsing, template loading, value formatting, operation construction/application, and
repository-specific document orchestration. This violates the binding split-before-extension
guidance around 300 lines.

### Canonical supervisor proof is missing

The evidence producer calls deterministic contracts directly. The new path is wired into
capabilities and specialists, but the three complete candidates have not yet been reproduced
through a canonical `readme-agent supervise` end-to-end run after `5d2256b`.

### Cross-pilot and editorial acceptance is too weak

The producer checks that product identity appears, but it does not perform a serious
cross-pilot template-clone comparison or an independently reproduced “no manual prose repair”
assessment. The active task requires both.

### Normative state intentionally remains open

- Durable task: `L8-LOCAL-README-PROPOSAL-PROOF = IN_PROGRESS`.
- Several requirement rows still describe README proposal integration as open.
- No `plans/master.md` closure was claimed.

This is the correct checkpoint state.
