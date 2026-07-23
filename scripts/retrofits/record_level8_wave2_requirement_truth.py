"""Replace Wave-2 requirement rows with the current, evidence-bounded truth."""

# ruff: noqa: E501

from __future__ import annotations

import re
from pathlib import Path

REQUIREMENTS_PATH = Path("plans/requirements.md")

REPLACEMENTS = {
    "RUN-002": "| RUN-002 | P1 | PARTIAL | One official runner entry point MUST accept `workflow_call`, `repository_dispatch`, `workflow_dispatch`, and scheduled triggers, all entering the same governed runtime. | `.github/workflows/readme-agent-production.yml` wires all four triggers to `supervise --execution-profile github_observe`; `repository_dispatch` requires a stable delivery ID. The old portfolio schedule is retired to manual diagnostic use. Actionlint/static contracts pass and the workflow-dispatch recovery/plan path succeeds under `act`; remote Actions proofs for all four triggers remain open. | Decision 26; Wave 2 |",
    "RUN-005": "| RUN-005 | P0 | PARTIAL | A run that requires durable state for idempotency, locking, recovery, or effect reconciliation MUST fail closed when that state cannot be read or committed; it MUST NOT report successful autonomous completion after silently degrading to ephemeral state. | GitHub profiles require the durable backend before preflight, strict state reads/writes propagate, and domain/specialist markers fail closed. A unit test proves intake uncertainty prevents the preflight/LLM boundary. Production-like outage injection remains open. | Decisions 26, 32, 74; Wave 2 |",
    "RUN-006": "| RUN-006 | P0 | PARTIAL | Trigger intake MUST persist a stable event identity, deduplicate equivalent schedule/event/operator deliveries, and recover accepted-but-unfinished work after runner loss. | `TriggerEnvelopeV2`, seven-state `TriggerLifecycleV2`, `accept_trigger()`, and `recovery_sweep()` are wired into the canonical command and workflow. The sweep emits a per-repository recovery matrix, and `--resume-trigger-key` loads the original envelope rather than inventing a new logical trigger. Terminal duplicates suppress; unfinished duplicates resume. Unit fault injection covers every checkpoint; hosted-runner loss proof remains open. | Decisions 26, 74; Wave 2 |",
    "RUN-007": "| RUN-007 | P1 | PARTIAL | The normal portfolio runtime MUST expose health and backlog state sufficient to detect missed schedules, stuck leases, repeated repository failures, rate-limit backoff, evidence-write failure, open proposals, and last success without reading raw runner logs. | `HealthReportV1` and `readme-agent health-report` expose durable portfolio state; the workflow uploads it, creates/updates an issue, fails its Actions check, and supports an external dead-man heartbeat. Rate-limit/evidence-failure population and live alert proof remain open. | Decisions 26, 74; Wave 2 |",
    "RUN-009": "| RUN-009 | P2 | PARTIAL | Durable state MUST persist progress after 11 checkpoints: trigger accepted, run started, snapshot captured, profile completed, task started, task completed, verifier result, repair plan, effect pending, effect applied, and final acceptance, so a new runner can resume or reconcile unfinished work. | `CheckpointV1` and `LifecycleRecorder` are wired at every named producer. A parameterized kill-after-persist test recovers and completes the same logical trigger at all 11 boundaries. Real process-kill/runner reproduction remains open. | Decision 74; Wave 2 |",
    "EVID-004": "| EVID-004 | P2 | PARTIAL | The production run manifest MUST record the authorization and trigger identity that governed or initiated the run. | `RunManifestV3` binds the complete `TriggerEnvelopeV2`, terminal trigger status, checkpoints, and an honest authorization status/record field. Real authorized-effect proof remains Wave 5 work. | `EVID-001`; `AUTH-001`-`006`; `RUN-006`; Wave 2 |",
    "L8-001": "| L8-001 | P0 | PARTIAL | Every production target-access job MUST authenticate with a freshly minted, short-lived GitHub App installation token. A production profile MUST NOT accept PAT or ambient `GH_TOKEN` fallback. | The production workflow mints a repository-scoped App token with contents-read permission for analysis. `env.gh_token()` uses only `README_AGENT_GITHUB_APP_TOKEN` under the production-auth marker; negative tests prove ambient token/PAT rejection. Live App installation proof remains open. | Decisions 33, 73; Waves 2 and 5 |",
    "L8-003": "| L8-003 | P0 | PARTIAL | Production lifecycle state MUST implement `TriggerEnvelopeV2`, `CheckpointV1`, seven trigger states, all named lifecycle checkpoints, and explicit migrations from supported earlier schemas; unknown/newer schemas MUST fail closed. | V1-to-V2 and unknown-version tests pass; all 11 checkpoint fault injections resume one logical trigger; intake state outage blocks preflight/LLM. Real runner-kill and state-outage proofs remain open. | Decisions 32, 74; Wave 2; RUN-006/009 |",
    "L8-004": "| L8-004 | P0 | PARTIAL | Every scheduled run MUST recover accepted/processing/retryable work with expired leases, and `HealthReportV1` plus an external dead-man monitor MUST expose missed windows, backlog, stale leases, repeated failures, rate limits, evidence failures, open proposals, and last success. | Recovery/health CLI commands and the scheduled workflow are built with a durable-trigger recovery matrix, original-envelope resume, issue/check alerting, and heartbeat support. External monitor configuration and production-like missed-schedule/rate-limit/evidence-failure proofs remain open. | Decision 74; Wave 2 |",
    "L8-005": "| L8-005 | P0 | PARTIAL | Every terminal run MUST produce a retention-governed, checksum-complete `RunManifestV3` binding trigger, checkpoints, facts, presentation plan, authorization, verifier, effects, and requirement-level results. Terminal classification MUST fail closed if required evidence is absent or invalid. | `RunManifestV3`, atomic writer, checksum inventory, corruption gate, and GitHub-profile evidence requirement are built. Retention policy and production-like 100%-terminal-manifest proof remain open. | Decision 74; Waves 2 and 8; EVID-*; SAFE-008/009 |",
    "L8-013": "| L8-013 | P0 | PARTIAL | The production workflow MUST separate analysis and effect jobs so repository content, package/example execution, LLM planning, and validation run without a target-write token; only the final authorized effect job may mint and receive one. | Wave 2's production analysis job receives only a repository-scoped contents-read App token; central state writes use the control repository token. No target effect job exists before the verified-proposal lifecycle in Wave 5. Static permission tests pass; live compromise-boundary proof remains open. | Decisions 73, 75; Waves 1, 2, and 5 |",
}

INSERT_AFTER = "RUN-009"
NEW_ROW = "| RUN-010 | P1 | PARTIAL | GitHub reads, LLM calls, state CAS, clone operations, package registries, and GitHub writes MUST use distinct bounded retry policies with exponential jitter; GitHub `Retry-After`/rate-limit reset MUST be honored. Permanent failures MUST not be replayed. | `retry.py::RetryPolicyV1`, `run_with_retry()`, and `run_http_with_retry()` drive all six operation classes, including every state-CAS retry loop and transient clone retry. Tests prove attempt bounds, jitter/backoff routing, rate-limit headers, and that an unmarked permanent GitHub 403 is not replayed. Production-like rate-limit proof remains open. | Decision 74; Wave 2 |"


def main() -> None:
    text = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    for requirement_id, replacement in REPLACEMENTS.items():
        pattern = rf"^\| {re.escape(requirement_id)} \|.*$"
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
        if count != 1:
            raise RuntimeError(f"expected exactly one row for {requirement_id}, found {count}")
    if re.search(r"^\| RUN-010 \|", text, flags=re.MULTILINE):
        raise RuntimeError("RUN-010 already exists")
    anchor = REPLACEMENTS[INSERT_AFTER]
    text = text.replace(anchor, f"{anchor}\n{NEW_ROW}", 1)
    REQUIREMENTS_PATH.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
