# Reference and evidence index

## Primary authority

| Purpose | Path |
|---|---|
| User product vision | `plans/idea.md` |
| Current architecture/decisions/waves | `plans/master.md` |
| Normative obligations | `plans/requirements.md` |
| Plan governance | `plans/GOVERNANCE.md` |
| Agent repository instructions | `AGENTS.md` |
| Executable mission taskcards | `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` |
| Requirement-task coverage | `plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json` |
| History | `logs/README.md` and `logs/2026-07-24.md` |

## Current implementation documentation

| Subject | Path |
|---|---|
| Pipeline and module map | `docs/architecture.md` |
| Safety properties | `docs/safety-model.md` |
| Policy authoring | `docs/policy-authoring.md` |
| Presentation standard | `docs/presentation-standard.md` |
| GitHub surface ownership/control | `docs/github-surface-control.md` |

## Pre-production sequencing reports

| Subject | Path |
|---|---|
| Local -> act -> staging decision and clause matrix | `plans/investigations/preproduction-idea-fidelity-gate-2026-07-24.md` |
| Earlier machine-resume checkpoint | `plans/investigations/preproduction-idea-fidelity-resume-checkpoint-2026-07-24.md` |
| Detailed restart checkpoint | `plans/investigations/control/preproduction-idea-fidelity-restart-checkpoint-2026-07-24.md` |

## Evidence roots relevant to the current sprint

| Proven scope | Evidence root | Truth status |
|---|---|---|
| Wave-0 semantic closure | `plans/investigations/evidence/level8-semantic-closure-verification.json` | Closed bounded gate |
| Fresh-clone baseline | `plans/investigations/evidence/level8-wave0-fresh-clone-head-reproduction/` | Closed bounded gate |
| Canonical safety/false-success cases | `plans/investigations/evidence/level8-wave1-heterogeneous-fail-closed-2026-07-23/` | Closed Wave 1 |
| Restartable runtime local foundation | `plans/investigations/evidence/level8-wave2-restartable-actions-2026-07-23/` | Partial; hosted/production gates open |
| ProductFactsV2 local foundation | `plans/investigations/evidence/level8-wave3-local-product-truth-foundation-2026-07-23/` | Closed bounded local child |
| Presentation-plan local foundation | `plans/investigations/evidence/level8-wave4-local-presentation-plan-foundation-2026-07-23/` | Closed bounded local child |
| Truthful pre-production baseline | `plans/investigations/evidence/level8-preproduction-truthful-baseline-2026-07-24/` | Closed bounded child |
| Immutable pilot snapshots/facts | `plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-2026-07-24/` | Closed bounded child |
| Latest three README proposals | `plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/` | Producer-accepted checkpoint; active task not closed |

## Latest README proposal artifacts

### Cells Java

```text
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/cells-java/
```

Important artifacts:

- `original-readme.md`;
- `candidate-readme.md`;
- `proposal.patch`;
- `product-facts-v2.json`;
- `readme-document-plan-v1.json`;
- `repository-presentation-plan-v1.json`;
- `document-validation.json`;
- `independent-review.json`; and
- `artifact-sha256.json`.

### 3D Java

```text
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/three-dimensional-java/
```

Same artifact set.

### PDF Java

```text
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/pdf-java/
```

Same artifact set.

### Root manifest

```text
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/local-proof-manifest-v1.json
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/sha256sums.txt
plans/investigations/evidence/level8-local-readme-proposals-2026-07-24/reproduction-command.txt
```

## Evidence producer and verifier tools

| Function | Path |
|---|---|
| Truthful-baseline producer | `plans/investigations/tools/collect_preproduction_truthful_baseline_evidence.py` |
| Immutable facts producer | `plans/investigations/tools/collect_local_immutable_snapshot_and_product_facts_evidence.py` |
| Immutable facts verifier | `plans/investigations/tools/verify_local_snapshot_and_product_facts_evidence.py` |
| README proposal producer | `plans/investigations/tools/collect_local_readme_proposal_evidence.py` |
| README proposal independent verifier | Not yet implemented; this is an active-task blocker |

## Current implementation seams

### Mission and truthful terminal behavior

```text
src/readme_agent/supervisor/mission_control.py
src/readme_agent/supervisor/mission_command.py
src/readme_agent/supervisor/finding_status.py
src/readme_agent/supervisor/work_ledger.py
src/readme_agent/supervisor/convergence.py
src/readme_agent/supervisor/planner_loop.py
src/readme_agent/supervisor/status.py
```

### Immutable snapshot and facts

```text
src/readme_agent/repository_snapshot.py
src/readme_agent/facts/repository_ingestion.py
src/readme_agent/facts/policy_evidence.py
src/readme_agent/facts/local_verification.py
src/readme_agent/facts/provider.py
src/readme_agent/facts/schema_v2.py
```

### README planning/rendering/validation

```text
src/readme_agent/readme/document_plan.py
src/readme_agent/readme/document_renderer.py
src/readme_agent/readme/document_validation.py
src/readme_agent/readme/idea_candidate.py
src/readme_agent/presentation/document_planner.py
src/readme_agent/verification/checks.py
src/readme_agent/capabilities/render_readme_candidate.py
src/readme_agent/capabilities/build_presentation_plan.py
src/readme_agent/specialists/readme_factuality.py
src/readme_agent/specialists/readme_presentation.py
```

### Templates

```text
templates/readme/product-overview-and-navigation.md
templates/readme/verified-minimal-example.md
templates/readme/verified-source-acquisition.md
```

## Focused tests

```text
tests/unit/test_work_ledger.py
tests/unit/test_convergence.py
tests/unit/test_supervisor_loop.py
tests/unit/test_prompt_registry.py
tests/unit/test_repository_snapshot.py
tests/unit/test_product_truth_ingestion.py
tests/unit/test_readme_document_plan.py
tests/unit/test_capabilities.py
tests/unit/test_specialists.py
```

## Key requirements for the current and next gates

```text
L8-002  sole production runtime
L8-003  lifecycle/checkpoint schemas
L8-004  recovery/health/dead-man
L8-005  terminal manifest completeness
L8-006  ProductFactsV2
L8-007  presentation plan/protected content
L8-008  verified/open proposal lifecycle
L8-009  prohibited effects/token separation
L8-010  Level 5/6/7 acceptance
L8-011  Level 8 elapsed proof
L8-012  deterministic/agentic thresholds
L8-013  analysis/effect job separation
L8-014  local -> act -> staging before production

RDM-003 no generic full-document replacement
RDM-004 surgical fact-backed changes
RDM-007 verified acquisition
RDM-008 verified minimal example
RDM-018 protected technical content
RDM-025 conflicts must correct rendered text

FACT-001 provenance before presentation
RUN-009 lifecycle checkpoints
OPS-010 credential/process isolation
VER-001 independent verification
VER-009 specialist errors cannot converge
```

Read the full row in `plans/requirements.md`; this index is not a substitute for its complete
acceptance language.

## Commit chain

```text
f8b83a41506fb22a6884f494f1b16ffb8213076e  origin/main at handover inspection
946081e81c670d84d49604b1fefb712226eb886c  truthful runtime and child task sequence
05589be23d37a398231975c9d72abc893980a2c2  truthful-baseline evidence
5e31f9c11e7a54d9acc8638b23e1f85fc799ed9a  immutable snapshots and pilot facts
5d2256b559890353d1a1b3e380cb848f2c831b15  README document planning foundation
ab8a54d9e68eefe25a030498e217a9a62c64c302  README proposal evidence checkpoint
```

The handover commit created after this file must be appended by the next agent when verifying
HEAD.

## External references already adopted into the plan

The project plan cites official GitHub documentation for:

- GitHub App authentication in Actions;
- Actions concurrency behavior; and
- scheduled-run limitations.

Use the citations in the approved Level-8 plan/master history. For new technical work, use
primary/official sources and record the version/date. Do not build production authentication from
memory or model-name folklore.
