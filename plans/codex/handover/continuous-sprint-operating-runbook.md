# Continuous autonomous sprint operating runbook

## Startup protocol

1. Work from:

   ```text
   D:\Users\prora\OneDrive\Documents\GitHub\foss-readme-optimizer
   ```

2. Read, in full:

   - `AGENTS.md`;
   - `plans/GOVERNANCE.md`;
   - `plans/idea.md`;
   - this handover directory;
   - the active taskcard in the mission graph;
   - the evidence for the immediately preceding task; and
   - relevant current architecture/safety documentation.

3. Confirm interpreter and branch:

   ```powershell
   git branch --show-current
   .venv/Scripts/python --version
   .venv/Scripts/readme-agent --version
   ```

4. Confirm the worktree boundary:

   ```powershell
   git status --short
   git log -8 --oneline
   git rev-list --left-right --count origin/main...main
   ```

5. Read durable state:

   ```powershell
   .venv/Scripts/readme-agent supervise `
     --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
     --mission-action status `
     --mission-observer "<agent-name>"
   ```

6. Resume the active task. Do not call `claim` while an active task exists.

## Per-task autonomous loop

For each task:

1. reconcile the predecessor against code, tests, evidence, master Status/Checklist, and affected
   requirements;
2. inspect the current implementation and Git history before replacing anything;
3. identify battle-tested libraries/reference implementations before custom code;
4. implement only inside the taskcard's allowed scope;
5. keep deterministic authority over safety, facts, boundaries, and acceptance;
6. run focused tests after each coherent change;
7. run real/prod-like proof matched to the claim;
8. generate committed evidence with an identifiable producer;
9. run a verifier that did not author or trust the producer's acceptance result;
10. repair failures rather than weakening acceptance;
11. reconcile requirements and documentation;
12. run complete official checks;
13. commit coherent changes on `main`;
14. transition `IMPLEMENTED -> VERIFIED -> SCORED -> CLOSED` with exact evidence; and
15. claim the next dependency-ready task and continue.

Do not stop merely because:

- a commit was made;
- tests passed;
- one evidence bundle exists;
- context was compacted;
- one lane failed;
- a machine checkpoint occurred; or
- the task would benefit from routine human review.

## Focused-to-full verification discipline

Use the repository-root virtualenv for every Python command.

Typical focused cycle:

```powershell
.venv/Scripts/python -m pytest tests/unit/test_readme_document_plan.py -q
.venv/Scripts/python -m pytest tests/unit/test_product_truth_ingestion.py -q
.venv/Scripts/python -m pytest tests/unit/test_repository_snapshot.py -q
.venv/Scripts/python -m pytest tests/unit/test_supervisor_loop.py -q
```

Official gate:

```powershell
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m mypy src
.venv/Scripts/python -m pytest -q
.venv/Scripts/python scripts/governance/validate_plan_structure.py
actionlint
```

Before accepting a check:

- capture exact commit SHA;
- record command, exit code, stdout/stderr, tool versions, and test count;
- ensure live tests are explicitly marked and intentionally invoked;
- ensure non-live tests do not inherit credentials or network;
- inspect whether cancelled processes left descendants; and
- checksum committed evidence.

Never print environment-variable values while diagnosing credentials. Check only presence, source,
or redacted metadata.

## Evidence rules

Runtime output belongs under `runs/` and is disposable. Committed audit evidence belongs under:

```text
plans/investigations/evidence/<self-explanatory-investigation-name>/
```

Every committed evidence directory must:

- identify its producer tool;
- be cited by a report or requirement;
- record immutable control/target revisions;
- contain raw results, not only a summary;
- contain a SHA-256 inventory;
- include reproduction instructions;
- be redacted;
- distinguish simulated, local-live, `act`, staging, and production evidence; and
- state what remains unproven.

Do not overwrite prior evidence to make a later check pass. Produce a new bounded evidence root
that cites the prior input.

## Requirement and plan reconciliation

### Requirements

For each affected requirement:

1. read the entire row;
2. compare every clause with evidence;
3. change status only to the weakest status consistent with all clauses;
4. cite exact evidence paths and scope;
5. keep portfolio/production clauses open when only pilots/local work passed;
6. regenerate canonical requirement inventory and taskcard coverage; and
7. run plan validation.

Non-blocking issues found outside task scope become a `BACKLOG` row in the matching section. A
correctness/safety blocker is fixed before closing the task.

### Master plan

Before any `plans/master.md` edit:

1. name the exact sections;
2. state why each must change;
3. obtain fresh explicit approval in that turn; and
4. edit only those sections.

Earlier approval is not reusable. Logs and requirements do not share this master edit gate.

### Logs

Append through:

```powershell
.venv/Scripts/python scripts/governance/append_log_entry.py --help
```

Use the script rather than hand-editing the shard and index independently.

## Commit protocol

Work on `main` only. Stage explicit paths:

```powershell
git add -- <exact-task-paths>
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

Verify that these user-owned paths are absent:

```text
AGENTS.md
plans/idea.md
plans/changelog.md
plans/roadmap.md
plans/status.md
```

Every AI-authored commit requires the correct trailer. For Codex:

```text
Co-Authored-By: Codex <noreply@openai.com>
```

After commit:

```powershell
git log -1 --format=fuller
git log -1 --format=%B | git interpret-trailers --parse
git status --short
```

Do not use `reset --hard`, `clean`, broad checkout/restore, or force push.

## Durable task transitions

Valid success progression:

```text
IN_PROGRESS -> IMPLEMENTED -> VERIFIED -> SCORED -> CLOSED
```

Each transition is a separate durable compare-and-swap update. Use exact evidence references.

Example:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action transition `
  --mission-task-id "<task-id>" `
  --mission-to-status "<next-status>" `
  --mission-observer "<observer>" `
  --mission-reason "<specific evidence-backed reason>" `
  --mission-evidence "commit:<full-sha>" `
  --mission-evidence "<evidence-path>"
```

Never jump directly from `IN_PROGRESS` to `CLOSED`. The author of a proposal must not be the sole
verification observer.

After closure:

```powershell
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action claim `
  --mission-observer "<agent-name>"
```

Inspect the selected task before executing it.

## Failure and blocker handling

### Local engineering failure

Keep the task active. Capture the first failing producer/consumer, repair it, rerun focused tests,
then full regression. Do not call it external.

### Unrelated lane failure

Persist it as blocked/retryable and continue independent eligible work.

### Missing fact

Emit an exact scoped handoff and block only dependent surfaces. Continue unrelated audit/proposal
work.

### Unsupported ecosystem/pattern

Emit a `CapabilityGap` with evidence. Do not silently skip and do not invent a result.

### External authority/access blocker

Exhaust local and isolated alternatives first. Then record:

- exact unavailable authority/credential;
- why it cannot be self-provisioned;
- exact minimal human action;
- affected and unaffected tasks;
- evidence proving the blocker; and
- deterministic resume condition.

Only then may a task become `BLOCKED_EXTERNAL`.

### Machine restart

Before stopping:

- commit all agent-owned work;
- leave the active task and state version recorded;
- validate evidence checksums;
- ensure no repository-scoped helper remains;
- record uncommitted user-owned paths;
- do not transition an incomplete task; and
- provide the exact resume command.

## Human-only boundaries

The human is required only for:

1. fresh section-specific approval before `plans/master.md` edits;
2. disposable staging target/access approval when Gate C is reached;
3. GitHub App registration/installation and production secrets after pre-production passes;
4. fresh what/why/where confirmation before each product-repository push;
5. genuinely manual GitHub UI actions with no supported API;
6. analytics/dead-man authority; and
7. independent elapsed-window acceptance authority.

The human is not expected to run tests, choose capabilities, generate proposals, operate
workflows, create evidence, or repeatedly tell the agent to continue.

## Moving to another workspace

The current work is ahead of `origin/main`. If the new agent uses this same workspace, it can
continue immediately.

If the new agent uses a separate clone:

1. make all local control-repository commits available on `main`;
2. separately preserve/transfer the five user-owned uncommitted files if they are needed;
3. ensure the durable mission-state ref remains reachable from the configured `origin`;
4. recreate `.venv` from the committed lock;
5. verify the exact HEAD and state version; and
6. only then resume.

Do not put uncommitted user files into an ad hoc branch or commit merely to move them without the
user's explicit disposition.
