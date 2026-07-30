# Qualified Cohort ACT Inputs

These inputs preserve the exact three `TRUSTED_NO_OP_PROVEN` runtime bundles and their durable
Git-ref states for `TRP-04P-ACT-WORKFLOW-PARITY`.

The tar contains only the three revision-addressed `runs/readme-poc/` roots named by the frozen
cohort. The Git bundle contains only their three `refs/readme-agent-state/*` histories. The actual
workflow restores both into disposable local paths and validates the cohort contracts and checksum
inventory before invoking `readme-agent supervise --execution-profile act_poc`.

Reproduction is performed by the task's ACT harness after the workflow and restore command land.
The hosted profile remains GitHub-App-only; these inputs authorize no product or control remote
write.
