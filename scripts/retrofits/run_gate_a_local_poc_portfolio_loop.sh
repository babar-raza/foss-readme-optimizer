#!/usr/bin/env bash
# 2026-08-18: local driver for the Gate A local_poc portfolio.
#
# `readme-agent supervise --registry data/products.json --execution-profile
# local_poc` deliberately processes one bounded time slice per invocation
# (commands_supervision.py's `_LOCAL_POC_EXECUTION_SLICE_SECONDS`) and exits
# so an external caller re-triggers it -- in production that caller is a
# scheduled GitHub Actions workflow (.github/workflows/readme-agent-
# production.yml); locally, it's this script. Each invocation resumes from
# durable state exactly where the last one left off (no re-work, no
# skipped repositories).
#
# Stops immediately (does not loop past it) on the first SYSTEM_FAILURE
# line in any single invocation's output -- per the standing "harden
# before moving forward" discipline: a crash is a real defect to root-
# cause and fix, never something to run past and repeat across the rest
# of the registry. BLOCKED entries (claim-accountability holdouts,
# missing-evidence, etc.) are expected, already-triaged terminal states
# for this pass and do not stop the loop.
#
# Kept after use as the executable record/reusable driver for local Gate A
# execution -- see plans/GOVERNANCE.md, "Repository layout", placement
# rule 5 (mirrors the precedent of run_full_registry_supervise_pass.sh).
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

MAX_ITERATIONS="${1:-40}"
MISSION_TASK_ID="L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY"
LOG_DIR="runs/gate-a-local-poc-portfolio-2026-08-18"
mkdir -p "$LOG_DIR"

for ((i = 1; i <= MAX_ITERATIONS; i++)); do
  log_file="$LOG_DIR/iteration-$(printf '%03d' "$i").log"
  echo "=== iteration $i/$MAX_ITERATIONS -> $log_file ==="
  ./.venv/Scripts/python -m readme_agent.cli supervise \
    --registry data/products.json \
    --execution-profile local_poc \
    --mission-task-id "$MISSION_TASK_ID" \
    --mission-observer readme-agent-supervisor \
    2>&1 | tee "$log_file"
  exit_code="${PIPESTATUS[0]}"

  if grep -q "SYSTEM_FAILURE" "$log_file"; then
    echo "STOPPED: SYSTEM_FAILURE detected in $log_file -- investigate before continuing."
    exit 1
  fi

  summary_line="$(grep -E "^local_poc portfolio: target=" "$log_file" | tail -n1)"
  echo "$summary_line"
  if echo "$summary_line" | grep -q "slice_complete=True"; then
    echo "DONE: portfolio slice reported complete after $i iteration(s)."
    exit 0
  fi
  if [ "$exit_code" != "0" ] && [ "$exit_code" != "1" ]; then
    echo "STOPPED: unexpected exit code $exit_code in $log_file -- investigate before continuing."
    exit 1
  fi
done

echo "STOPPED: reached MAX_ITERATIONS=$MAX_ITERATIONS without slice_complete=True."
exit 1
