# Amended File Inventory

Snapshot base: `main` at `59b94b9ecc089c3dca96856077559a4efca35566`.

## Owning plans and governance

- `AGENTS.md` - repository operating contract, active verified lane, campaign and review rules.
- `plans/GOVERNANCE.md` - subject-specific authority and trusted-history restrictions.
- `plans/idea.md` - immutable outcome and ordered verified delivery gates.
- `plans/master.md` - architecture, current status, decisions #81-#88, build and verification gates.
- `plans/requirements.md` - normative acceptance, deprecated trusted-only rows, and `L8-044`.
- `plans/roadmap.md` - derived six-campaign view only.
- `plans/status.md` - current generated denominator and lifecycle truth.
- `plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md` - supporting execution guide.
- `logs/2026-08-02.md` and `logs/README.md` - append-only reconciliation record and index.

## Executable graph and durable-control contracts

- `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` - P0 task, verified
  ordering, trusted-history exclusion, typed six-campaign catalog, and exact task membership.
- `src/readme_agent/state/mission_goal_schema.py` - P0 goal and campaign identifiers.
- `src/readme_agent/supervisor/mission_schema.py` - typed campaign graph contract.
- `src/readme_agent/supervisor/mission_graph.py` - campaign and historical-goal validation.
- `src/readme_agent/supervisor/mission_control.py` - campaign-aware selection and concurrency.
- `src/readme_agent/supervisor/mission_command.py` - campaign status output.
- `src/readme_agent/supervisor/mission_goal_guard.py` - campaign-bound closeout evidence.
- `scripts/governance/build_level8_requirement_taskcard_coverage.py` - canonical goal/campaign and
  requirement mappings.

## Generated truth and verification seams

- `plans/investigations/tools/traceability_matrix.py` - current sources instead of historical
  manifest fallback.
- `plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json` - regenerated
  semantic traceability.
- `plans/investigations/evidence/level8-requirement-taskcard-coverage/requirement-taskcard-coverage.json`
  - regenerated 464-row coverage.
- `tests/unit/test_mission_control.py` - campaign, trusted exclusion, ordering, and contribution
  evidence controls.
- `tests/unit/test_traceability_matrix.py` - current 31-entry status generation controls.

## Explicitly excluded dirty work

README composition, fact extraction, prompts, templates, ecosystem adapters, product tests, and
other candidate implementation already present in the working tree were preserved but not treated
as part of this plan-reconciliation implementation. `CampaignFreezeV1` content-addresses the
applicable contract bytes without claiming those unrelated changes are committed or verified.

## Freeze and external-review package

- `campaign-freeze-v1.json` - control commit plus eleven dependency-group and seven critical-file
  hashes, with dirty-contract and incomplete-registry disclosure.
- `freeze-validation.json` and `freeze-validation-history.md` - rejected ambiguous membership
  attempt followed by independent 11/11 and 7/7 acceptance.
- `INDEPENDENT-REVIEW-START.md` and `review-zip-files.txt` - canonical external-review entrypoint
  and exact archive membership.
