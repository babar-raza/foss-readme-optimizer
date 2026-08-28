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
# Completion is judged by the "complete=N/33" counter reaching the full
# denominator, or by that counter plateauing across two consecutive
# iterations (no further progress possible without more engineering, e.g.
# structurally BLOCKED repos) -- NOT by `slice_complete=True`/
# `processed=33`, which only means the whole registry was *looked at* in
# one time slice, not that every repository actually reached a terminal
# complete state. A prior revision of this script conflated the two
# (2026-08-18 incident log): it reported "DONE" after iterating all 33
# members once, each failing near-instantly on an unrelated hygiene bug,
# with real progress unchanged at 1/33.
#
# --portfolio-time-budget-seconds defaults to 1200s (override via
# $PORTFOLIO_TIME_BUDGET_SECONDS), well above the CLI's own 300s default:
# confirmed live (2026-08-18) that a BLOCKED repository is NOT cached
# between passes (only NO_OP_PROVEN/AGENT_APPROVED short-circuit with zero
# calls) -- every already-known-BLOCKED repository is retried in full on
# every single invocation. With the 300s default this reliably consumed
# the whole slice on the same ~4 already-known-blocked repositories before
# ever reaching an unprocessed one; a real portfolio-wide throughput gap
# (repeatedly re-litigating known failures instead of making forward
# progress), not something this script alone can fix -- widening the
# budget is a workaround, not a substitute for adding real backoff/skip
# caching for repeatedly-BLOCKED repositories in the supervisor itself.
#
# Kept after use as the executable record/reusable driver for local Gate A
# execution -- see plans/GOVERNANCE.md, "Repository layout", placement
# rule 5 (mirrors the precedent of run_full_registry_supervise_pass.sh).
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

MAX_ITERATIONS="${1:-40}"
MISSION_TASK_ID="L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY"
# One unique directory per driver invocation (2026-08-18 incident: a resumed
# driver reused the date-fixed directory and restarted its iteration counter
# at 001, overwriting the first run's per-iteration logs -- that evidence is
# gone). Override via $GATE_A_RUN_ID only to deliberately group related runs.
RUN_ID="${GATE_A_RUN_ID:-$(date +%Y%m%d-%H%M%S)-$$}"
LOG_DIR="runs/gate-a-local-poc-portfolio/${RUN_ID}"
mkdir -p "$LOG_DIR"

# Opt-in: force live re-execution of members whose last outcome was BLOCKED
# even though no bound dependency fingerprint changed (see --retry-blocked's
# own --help text). Off by default -- a normal resume pass should never pay
# for known-BLOCKED repos it has no new reason to re-litigate.
RETRY_BLOCKED_FLAG=()
if [ "${RETRY_BLOCKED:-0}" = "1" ]; then
  RETRY_BLOCKED_FLAG=(--retry-blocked)
fi

previous_complete=""
plateau_count=0

for ((i = 1; i <= MAX_ITERATIONS; i++)); do
  log_file="$LOG_DIR/iteration-$(printf '%03d' "$i").log"
  echo "=== iteration $i/$MAX_ITERATIONS -> $log_file ==="
  ./.venv/Scripts/python -m readme_agent.cli supervise \
    --registry data/products.json \
    --execution-profile local_poc \
    --mission-task-id "$MISSION_TASK_ID" \
    --mission-observer readme-agent-supervisor \
    --portfolio-time-budget-seconds "${PORTFOLIO_TIME_BUDGET_SECONDS:-1200}" \
    "${RETRY_BLOCKED_FLAG[@]}" \
    2>&1 | tee "$log_file"
  exit_code="${PIPESTATUS[0]}"

  # 2026-08-28 incident: this used to grep the whole log for a literal per-repo
  # "SYSTEM_FAILURE" line (the 2026-08-19 output format). That line no longer
  # appears in current output -- only the summary's lowercase `system_failed=N`
  # field does -- so this check silently never fired while a live pass hit 26/28
  # SYSTEM_FAILURE outcomes and the loop proceeded straight into iteration 2.
  # Check the structurally-guaranteed summary field first; keep the literal-line
  # grep too, in case a future per-repo detail line reappears without a summary.
  summary_line="$(grep -E "^local_poc portfolio: target=" "$log_file" | tail -n1)"
  echo "$summary_line"
  system_failed_count="$(echo "$summary_line" | grep -oE 'system_failed=[0-9]+' | head -n1)"
  system_failed_count="${system_failed_count#system_failed=}"
  if [ -n "$system_failed_count" ] && [ "$system_failed_count" != "0" ]; then
    echo "STOPPED: system_failed=$system_failed_count in $log_file -- investigate before continuing."
    exit 1
  fi
  if grep -q "SYSTEM_FAILURE" "$log_file"; then
    echo "STOPPED: SYSTEM_FAILURE detected in $log_file -- investigate before continuing."
    exit 1
  fi

  complete_fraction="$(echo "$summary_line" | grep -oE 'complete=[0-9]+/[0-9]+' | head -n1)"
  complete_count="${complete_fraction%%/*}"
  complete_count="${complete_count#complete=}"
  denominator="${complete_fraction##*/}"

  if [ -n "$complete_count" ] && [ -n "$denominator" ] && [ "$complete_count" = "$denominator" ]; then
    echo "DONE: complete=$complete_fraction after $i iteration(s) -- Gate A denominator reached."
    exit 0
  fi

  if [ "$complete_count" = "$previous_complete" ]; then
    plateau_count=$((plateau_count + 1))
  else
    plateau_count=0
  fi
  previous_complete="$complete_count"

  if [ "$plateau_count" -ge 2 ]; then
    echo "STOPPED: complete=$complete_fraction unchanged for 2 consecutive iterations -- no" \
      "further progress possible without more engineering (check BLOCKED reasons in" \
      "$LOG_DIR before resuming)."
    exit 1
  fi

  if [ "$exit_code" != "0" ] && [ "$exit_code" != "1" ]; then
    echo "STOPPED: unexpected exit code $exit_code in $log_file -- investigate before continuing."
    exit 1
  fi
done

echo "STOPPED: reached MAX_ITERATIONS=$MAX_ITERATIONS without reaching the full denominator."
exit 1
