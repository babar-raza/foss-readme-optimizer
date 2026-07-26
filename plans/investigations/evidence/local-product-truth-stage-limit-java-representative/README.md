# Local Product-Truth Stage-Limit Proof

Task: `L8-TRUTH-01-STAGE-LIMIT`

Requirement: `L8-015`

Implementation commit: `97e02a9f97f344804513fa768a74228b100414cc`

## Purpose

Prove that the canonical `local_poc` portfolio command can stop honestly at
`FACTS_READY` without invoking composition, specialist review, repair, no-op acceptance, or a
remote write.

## Command

```powershell
.venv/Scripts/readme-agent supervise `
  --registry runs/level8-truth-stage-limit-verification/java-representative-registry.json `
  --execution-profile local_poc `
  --max-readme-poc-stage FACTS_READY
```

The one-entry runtime registry is an unchanged copy of the canonical allow-list record for
`aspose-3d-foss/Aspose.3D-FOSS-for-Java`. It narrows this representative proof; it is not a
full-registry or Gate-A claim.

## Verified Result

The closure run started and ended on clean committed `main` at
`cd752bbbf9643468434d51fbcd29c8652c3a4f29`. The wrapper verified zero tracked or untracked
changes before and after the command. It returned exit code 0:

```text
aspose-3d-foss/Aspose.3D-FOSS-for-Java: STAGE_COMPLETE
  [0] readme_poc_stage_complete: requested FACTS_READY; observed FACTS_READY; no later capability executed
local_poc portfolio: target=FACTS_READY complete=1/1 agent_approved=0/1 system_failed=0 processed=1 slice_complete=True
```

The terminal manifest reports `STAGE_COMPLETE`, `llm_call_count: 0`, no effects, and an empty
specialist-result object. The portfolio summary reports exactly one `FACTS_READY` result and
explicitly reports zero agent-approved results. The source revision is
`8de5f467e93138b3605acdc46ca40e93f0364ee8`.

The run ID is `20260726-094650-a657`. Its manifest contains four checkpoints for this invocation,
including `snapshot_captured` and `final_acceptance`; no specialist task, verifier, or effect
checkpoint exists. This is evidence only for the `FACTS_READY` ceiling. It is not evidence that
the fact graph satisfies the still-open complete acceptance contract in
`L8-TRUTH-01A-FACT-CONTRACT`.

## Focused Verification Already Passed

- 10 stage-limit, CLI/profile, heterogeneous-registry, portfolio-summary, and public-supervisor
  tests.
- 130 lifecycle, execution-profile, allow-list, push-blocking, evidence-redaction, and execution
  boundary tests.
- Ruff check and format check for all affected source/tests.
- Mypy for `src/`.
- `git diff --check`.

The wider filtered supervisor lane had 30 passes and one known failure in
`test_local_poc_repairs_revalidates_and_rereviews_before_accepting`: two repair attempts produced
the same candidate hash. That defect predates and is not reached by the facts-only ceiling; it
remains owned by `L8-REVIEW-03-EFFECTIVE-REPAIR`.

## Artifact Map

- `java-representative-registry.json`: exact representative input.
- `repository-revision.json`: immutable snapshot identity.
- `product-facts.json` and `product-fact-provenance.json`: classified fact graph.
- `portfolio-summary.json`: bounded portfolio outcome.
- `supervisor-decisions.json`: explicit stage-boundary decision.
- `supervisor-specialist-results.json`: empty later-stage call inventory.
- `supervisor-run-manifest-v3.json`: terminal trigger/checkpoint/LLM/effect evidence.
- `supervisor-runtime-sha256sums.txt`: runtime evidence inventory.
- `sha256sums.txt`: inventory for this promoted evidence directory.
