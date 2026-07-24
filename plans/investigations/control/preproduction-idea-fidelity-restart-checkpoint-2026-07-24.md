# Pre-production idea-fidelity restart checkpoint

Checkpoint time: 2026-07-24, after the first three live-local Gate A runs.

## Resumable mission state

- Mission: `LEVEL8-CENTRAL-REPOSITORY-PRESENTATION`
- Durable state version: `68`
- Active task: `L8-PREPRODUCTION-IDEA-FIDELITY-GATE`
- Task status: `IN_PROGRESS`
- Graph SHA-256 recorded in durable state:
  `2c742430de805b5f029f260b0b48c00c95f0dfa8e32c29c56469408fa69379b8`
- Source branch: `main`
- Source HEAD and `origin/main` at task start:
  `f8b83a41506fb22a6884f494f1b16ffb8213076e`
- No control-repository feature branch was created.
- No product repository was pushed or otherwise written remotely.

Resume status command:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status
```

Do not claim a second task. The pre-production fidelity task is already active.

## Completed before the checkpoint

1. Confirmed commits `f8b83a4` and `a7ac331` are on `origin/main`.
2. Audited the existing Wave-2 proof:
   - `act` executed only the production workflow's matrix-planning job;
   - the hosted workflow stopped before `supervise`;
   - neither proves the complete `plans/idea.md` operating model.
3. Added the local → complete-current-workflow `act` → isolated-staging gate:
   - investigation report:
     `plans/investigations/preproduction-idea-fidelity-gate-2026-07-24.md`;
   - normative requirement: `L8-014`;
   - bounded mission task:
     `L8-PREPRODUCTION-IDEA-FIDELITY-GATE`;
   - production Wave 2 now depends on the pre-production gate.
4. Updated requirement-task coverage to 391 rows and 18 mission taskcards.
5. Fixed read-only mission status evaluation so a newly added graph task does not crash before
   durable reconciliation. Focused mission tests passed: 15/15.
6. Ran the canonical live-local supervisor against all three Java pilot archetypes with
   `local_dry_run` and dynamic planning.
7. Found and fixed a real false-convergence defect:
   `FIRST_OBSERVATION` specialist state had been treated as acceptable even when details contained
   `STALE_NONCOMPLIANT`, blocked facts, and failed presentation dimensions.
8. Added deterministic specialist terminal classification:
   - `PARTIAL_WITH_FINDINGS` is nonzero and names unresolved findings;
   - `CONVERGED_PROPOSAL_READY` distinguishes completed proposals from no change.
9. Re-ran 3D/Java live and proved the false-success correction:
   it changed from exit-0 `CONVERGED_NO_CHANGE` to exit-1
   `PARTIAL_WITH_FINDINGS`.

## Live-local evidence still under `runs/`

These are disposable runtime bundles and have not yet been copied into a committed evidence
directory:

| Repository / purpose | Evidence directory | Observed terminal result |
|---|---|---|
| 3D/Java before terminal fix | `runs/evidence/20260723-230757-082f/` | `CONVERGED_NO_CHANGE` despite explicit missing facts and stale presentation |
| 3D/Java after terminal fix | `runs/evidence/20260723-231310-624b/` | `PARTIAL_WITH_FINDINGS`: two metadata blocks, stale README, three failed dimensions |
| Cells/Java after terminal fix | `runs/evidence/20260723-231434-0dba/` | `PARTIAL_WITH_FINDINGS`: two metadata blocks and stale README |
| PDF/Java after terminal fix | `runs/evidence/20260723-231612-3132/` | `PARTIAL_WITH_FINDINGS`: two metadata blocks, stale README, two failed dimensions |

The next session must preserve these bundles long enough to collect checksum-addressed Gate A
evidence.

## Open blocking defects discovered

1. **Planner implicit-stop defect.** In the 3D and Cells live runs, the planner returned no tool
   call while its prose explicitly said the next useful/logical step was another capability.
   `planner_loop.py` currently treats every no-tool response as a valid stop.
2. **Premature explicit stop.** PDF called the `stop` capability while its reason still described
   an unresolved `products_org_link` gap.
3. **Gate A remains incomplete.** No pilot yet produced an idea-complete README proposal; all
   three correctly remain partial.
4. **Full supervisor-loop regression run is incomplete.** It was intentionally interrupted for
   this machine-restart checkpoint, not failed:
   `.venv/Scripts/python -m pytest -q tests/unit/test_supervisor_loop.py`.
5. **Production work remains deferred.** No GitHub App, production secret, production pilot,
   hosted recovery proof, or dead-man setup should start before local, `act`, and staging gates
   close.

## Exact resume sequence

1. Read this checkpoint and
   `plans/investigations/preproduction-idea-fidelity-gate-2026-07-24.md`.
2. Confirm no unexpected worktree change occurred during restart.
3. Run:

   ```powershell
   .venv/Scripts/python -m pytest -q tests/unit/test_supervisor_loop.py
   ```

4. Reconcile any failures caused by the new specialist terminal classifier. Do not mechanically
   change expectations: inspect whether each fixture actually contains unresolved findings or a
   completed proposal.
5. Harden planner termination behind the execution profile:
   production-like local/`act`/staging profiles must require an explicit, validated `stop`
   capability or retry an invalid implicit stop and then fail closed.
6. Re-run all three live-local pilots and collect their bundles into a checksum-addressed
   pre-production Gate A evidence directory.
7. Continue with full current-workflow `act` only after Gate A is honest and reproducible.

## Worktree ownership

Pre-existing user-owned changes that must not be overwritten or staged accidentally:

- `AGENTS.md`
- `plans/idea.md`
- `plans/changelog.md`
- `plans/roadmap.md`
- `plans/status.md`

The remaining modified/untracked paths are the in-progress Codex pre-production gate and
false-convergence repair. No commit was created because the supervisor-loop regression suite had
not completed at checkpoint time. When a later commit is ready, commit only reviewed task paths on
`main` and include:

```text
Co-Authored-By: Codex <noreply@openai.com>
```

## Process state

The interrupted `pytest tests/unit/test_supervisor_loop.py` process tree was explicitly
terminated. At checkpoint time, no process whose command line referenced this repository remained
running.
