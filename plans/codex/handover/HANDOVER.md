# Agent Handover

## 1. Live Snapshot

- Repository: `D:/Users/prora/OneDrive/Documents/GitHub/foss-readme-optimizer`
- Branch/HEAD: `main` at `e8f4de70160fb18d61d5ea5ee70802eac0174cc7`
- Mission: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`
- Durable state: version `790`
- Graph SHA-256: `ecc3c4567a448a9796c500a3916e8d6c026d9c18fdce33bc2c35212fbc270df1`
- Stage goal: `GOAL-V0-VERIFIED-PYTHON-POC`
- Active task: `L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES`
- Immediate goal: `DELIVERY-PY-PDF-CURRENT`
- Exact repository scope: `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`
- Goal-interface state: paused. Do not infer execution from a narrative goal or resume without an
  explicit user action/request.
- Working tree: valuable accumulated work; 156 tracked changes and 30 untracked paths at this
  snapshot. Preserve it. Do not reset, restore, clean, stash, or overwrite.

This snapshot is historical after any subsequent state or tree change. Mission `status` and Git
always override it.

## 2. Authority

1. `plans/idea.md` owns the product outcome.
2. `plans/master.md` and `plans/decisions/catalog.jsonl` own architecture and sequence.
3. `plans/requirements/catalog.jsonl` owns normative acceptance.
4. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` is the sole executable
   graph.
5. Durable supervisor state owns live claims, transitions, and runtime status.
6. This handover and other `plans/codex/` files are supporting continuation records only.

## 3. Goal Structure

The umbrella mission never directly authorizes implementation. The controller selects one stage,
one task, and one typed `TaskExecutionFocusV1`.

Current ordered delivery goals:

1. `DELIVERY-PY-PDF-CURRENT` — finish and show PDF Python with independent and no-op proof.
2. `DELIVERY-PY-PAGE-CURRENT` — reconcile and show the cached Page artifact.
3. `DELIVERY-PY-NOTE-CURRENT` — reconcile and show the cached native Note artifact.
4. `DELIVERY-PY-3D-CURRENT` — reconcile and show the cached Aspose.3D artifact.
5. `DELIVERY-PY-REMAINING-COHORT` — finalize and expose each remaining Python README.
6. `DELIVERY-POST-PYTHON-DOTNET-JAVA` — complete .NET first, then Java.

Later portfolio/Gate A/B/C, hosted, presentation-surface, Level-5/6, and background Level-7/8 work
remains in the same active/deferred mission authority. It cannot become current early.

## 4. Anti-Drift Controls Added

- Every active visible task now declares exact immediate outcome, repository scope, allowed change
  classes, next goal, two-attempt limit, 15-minute narrowing limit, and output-before-broad-suite
  policy.
- `mission status` prints the immediate goal, outcome, and repository scope.
- A bounded canary must include `--mission-task-id` and `--mission-observer`.
- `mission_execution_guard.py` rejects graph drift, wrong task/repository/observer, missing or expired
  claims, and an exhausted approach before preflight, clone, or LLM work.
- The approach fingerprint now binds the task execution focus.
- Nonblocking discoveries are deferred; they cannot enlarge the current task.
- PDF, Page, Note, and Aspose.3D are separate durable tasks instead of one combined repair surface.

## 5. True Current State

Live mission projection at reconciliation:

- denominator: 32;
- current facts-ready: 1/32;
- current candidate/validated/agent-approved/no-op: 0/32;
- raw historical: facts 20, candidates 15, deterministic 15, agent-approved 11, no-op 9;
- first failing boundary: `FACTS_READY`;
- 19 repositories are stale under the current fact contract.

Note, Page, and Aspose.3D have useful fresh candidate/no-op artifacts and a prior independent cohort
review, but the durable current scoreboard does not accept them under the latest fact contract.
Treat them as reusable evidence, not current closure.

The anti-drift focused test boundary passed 69 tests. A real bound PDF canary was intentionally
rejected before repository work because the prior claim had expired. The full suite has not been
rerun for this control slice and is not required before the next visible PDF output.

## 6. Exact Resume Action

When the user resumes:

1. Verify Git, processes, goal state, and mission `status`.
2. Run mission `evaluate` only on graph drift.
3. Claim/reclaim the same task through the mission controller; never steal an unexpired claim.
4. Run only:

```powershell
.venv/Scripts/readme-agent supervise `
  --repo aspose-pdf-foss/Aspose-PDF-FOSS-for-Python `
  --execution-profile local_poc `
  --bounded-verified-canary `
  --mission-task-id L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES `
  --mission-observer codex `
  --no-registry-heal
```

5. Resume from PDF's last valid content-addressed boundary.
6. Make only factuality, safety, presentation-acceptance, or repository-runtime fixes that directly
   block PDF.
7. After two equivalent failures or 15 minutes without narrowing, record a first-principles replan
   and change the causal fingerprint before another run.
8. Once PDF is deterministic-approved, independently approved, promoted, and no-op-proven, show its
   exact README immediately. Do not delay it for the broad suite.
9. Transition the same task with evidence, evaluate, then follow the next printed immediate goal.

## 7. Safety and Closure

- No product write, PR, merge, default-branch write, or product effect is authorized.
- Aspose.org is development comparison only and must be unavailable to acceptance/runtime proof.
- The control repository stays on `main`; no control branch.
- Full Python is the platform POC; smaller counts remain partial.
- The mission closes only at independently reproduced full umbrella acceptance. Level-7/8 elapsed
  certification cannot block earlier visible delivery.
