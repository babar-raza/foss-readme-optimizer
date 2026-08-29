#!/usr/bin/env python3
"""One-shot: log GOV-033 (Tier 0: targeted pinned-hash dedicated-test gate + advisory
governance-write CAS lock) and GOV-034 (Tier 1: document_template_hash flip-rate
instrumentation) -- the leaner, goal-sequenced fix for the Claude/Codex uncoordinated
shared-governance-write collision, built after a deeper pass rejected front-loading
Decisions #111/#112 as too slow and too risky to be the fast path to either "faster
portfolio delivery" or "quickly preventing recurrence."

Run once from the repo root:
`.venv/Scripts/python
scripts/retrofits/append_gov033_034_concurrent_agent_consistency_tier0_tier1.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
REQUIREMENTS_MD_PATH = REPO_ROOT / "plans" / "requirements.md"

NEW_ROWS = [
    {
        "requirement_id": "GOV-033",
        "section": "3. Requirements governance",
        "status": "IMPLEMENTED",
        "priority": "P2",
        "requirement": (
            "A commit touching a file with its own dedicated pinned-hash pytest test "
            "(deliberately excluded from GOV-032's declarative registry because it already "
            "has one -- e.g. the vendored check-battery manifest) MUST run that specific "
            "test locally before the commit is allowed, not rely on CI alone, which is "
            "advisory (the post-commit hook pushes to origin unconditionally regardless of "
            "CI outcome). Separately, a commit touching a shared governance path "
            "(plans/, logs/, AGENTS.md, the Level-8 mission graph) MUST leave a short-lived, "
            "self-expiring advisory trace on the same CAS backend mission_control.py's "
            "taskcard claims already use, so a concurrent agent's own commit-time check can "
            "observe recent governance-write activity -- Phase 1 only: informational, never "
            "blocking, since adoption of the underlying claim/lease mechanism was confirmed "
            "at zero for both agents this entire session."
        ),
        "acceptance_evidence": (
            "GOV033-CONCURRENT-AGENT-COLLISION-TIER0-001 (2026-08-29): found via a deeper "
            "reassessment after this session made 24 commits directly to shared governance "
            "files with no coordination, and a separate agent (Codex) landed 5 more hours "
            "later, one of which (`d8795bbdb`) reintroduced a known pinned-hash drift (the "
            "check-battery manifest) that reached `main` and sat there undetected until an "
            "unrelated full-suite run caught it -- proving CI-as-advisory-not-gating is a "
            "real hole, not a theoretical one. An earlier draft of this fix proposed a "
            "standalone 'session presence marker,' correctly rejected as a fourth ad hoc "
            "coordination mechanism; this version instead extends the already-proven CAS "
            "lock primitive. `git_backend.py::_acquire_lock_generic`/`_release_lock_generic`/"
            "`_renew_lock_generic`/`_lock_still_held_generic` read in full: a real, "
            "already-production-used, non-blocking optimistic-CAS distributed lock "
            "(holder_id, lease expiry, `--force-with-lease` compare-and-swap release), "
            "already generalized over an arbitrary key, already backing two independent "
            "families (`LOCK_REF_PREFIX` per-write, `RUN_LOCK_REF_PREFIX` per-repository "
            "run). Added a third thin wrapper, `GOVERNANCE_LOCK_REF_PREFIX = "
            "'refs/readme-agent-state/governance-locks'`, `GOVERNANCE_LOCK_LEASE_SECONDS = "
            "900`, and `acquire_governance_lock()`/`release_governance_lock()`/"
            "`peek_governance_lock()` (the last a new read-only peek, needed because a "
            "failed acquire returns bare `None` with no holder detail -- added specifically "
            "to compose a human-readable advisory message, never used as a CAS decision "
            "input). New `tests/unit/test_governance_write_lock.py` (7 tests) exercises the "
            "real `GitStateBackend` against a local bare-repo remote: acquire-when-free, "
            "collision-while-unexpired, peek-without-mutating, peek-absent, "
            "reclaim-after-lease-expiry (via `monkeypatch.setattr(git_backend, "
            "'GOVERNANCE_LOCK_LEASE_SECONDS', 0)`), release-then-peek-shows-absent, and "
            "confirmed the three lock families are genuinely independent (same key "
            "acquirable in all three simultaneously). New "
            "`scripts/governance/validate_pinned_hash_dedicated_tests.py`: a declarative "
            "`DedicatedTestTrigger` table (one entry today, the check-battery manifest, "
            "whose trigger paths are derived live from the manifest's own `files` list, not "
            "hardcoded, so the trigger list can't independently drift from what the manifest "
            "actually pins) that runs only the specific pytest node id(s) relevant to files "
            "staged in *this* commit -- closing the exact hole `d8795bbdb` fell through "
            "without moving the full suite into pre-commit, which this project's own hook "
            "design note already rejects as an invitation to `--no-verify` fatigue. 7 tests "
            "in `tests/unit/test_validate_pinned_hash_dedicated_tests.py` cover path "
            "matching only (pytest itself is not re-tested). New "
            "`scripts/governance/validate_governance_write_lock.py`: no-op (zero network "
            "calls, confirmed via a test that raises if `GitStateBackend` is constructed) "
            "when no staged file touches a protected path; otherwise acquires the lock and "
            "leaves it to expire naturally (deliberately NOT released immediately -- an "
            "earlier draft's plan to release-at-end-of-hook was corrected during "
            "implementation once it became clear an immediate release would erase the very "
            "trace a concurrent session is meant to observe), or peeks and prints an "
            "informational note if already held; any backend/network error is caught and "
            "degrades to a soft skip, never blocking an ordinary commit. Deliberately does "
            "NOT yet distinguish this session's own prior lock from a genuine peer's -- "
            "Phase 1 does not need to, since it never blocks either way; Phase 2 (real "
            "enforcement) is explicitly deferred pending a stable per-session identity "
            "mechanism, not built here. 12 tests in "
            "`tests/unit/test_validate_governance_write_lock.py` (path matching, acquire, "
            "peer-warning, backend-unavailable degradation). Both wired into "
            "`install_hooks.py`'s `PRE_COMMIT_HOOK_SCRIPT` template (dedicated-test gate "
            "blocking via `|| exit 1`; governance lock deliberately not) after the existing "
            "`mypy src` step; 3 new tests in `tests/unit/test_install_hooks.py` assert step "
            "order and that only the dedicated-test gate is blocking. Hook reinstalled "
            "locally via `install_hooks.py` (shared across all worktrees) and proven live: "
            "a real commit touching `plans/`/`logs/` correctly triggered the governance-lock "
            "advisory step. `ruff check`/`ruff format --check`/`mypy src` clean on every "
            "touched file; all 35 new tests pass."
        ),
        "traceability": (
            "Tier 0 of the leaner, goal-sequenced plan superseding the earlier "
            "session-presence-marker draft; found and built 2026-08-29 in direct response to "
            "the Claude/Codex uncoordinated governance-write collision"
        ),
    },
    {
        "requirement_id": "GOV-034",
        "section": "3. Requirements governance",
        "status": "IMPLEMENTED",
        "priority": "P3",
        "requirement": (
            "Before committing multi-day engineering to Decision #111/CORE-039 (per-repository "
            "composition-plan invalidation scoping), the claim that `document_template_hash()`'s "
            "global invalidation is the dominant cost driver -- inherited from the 2026-08-27 "
            "diagnosis, not freshly measured -- MUST be checked against real, additive-only "
            "instrumentation: the hash's value logged alongside real work, with every flip "
            "attributed to the specific contributing files that actually changed."
        ),
        "acceptance_evidence": (
            "GOV034-DOCUMENT-TEMPLATE-HASH-INSTRUMENTATION-001 (2026-08-29): Tier 1 of the "
            "same plan as GOV-033. New "
            "`scripts/governance/log_document_template_hash_observation.py`: purely "
            "observational, never imported by any production code path. "
            "`_contributing_files()` reproduces `document_template_hash()`'s own file "
            "resolution (template names, implementation paths, catalog paths, and the four "
            "glob patterns) by importing its public constants directly rather than "
            "duplicating literals, so the attribution logic cannot independently drift from "
            "what the real function hashes. `observe()` appends one JSON line per invocation "
            "to `runs/observability/document-template-hash-history.jsonl` (gitignored, same "
            "disposable tier as every other `runs/` artifact -- no new storage tier, per the "
            "plan's own constraint); each entry records `observed_at`, `template_hash`, "
            "`git_head`, whether it flipped since the last observation, and, on a flip, the "
            "intersection of `git diff --name-only <previous_head> <current_head>` (or "
            "`git diff --name-only HEAD` when the flip came from uncommitted working-tree "
            "changes rather than a new commit) against the contributing-file set. `report()` "
            "prints observation count, distinct hash count, flip count, and each flip's "
            "attributed files. 6 tests in "
            "`tests/unit/test_log_document_template_hash_observation.py`: contributing-file "
            "resolution is non-empty and includes a known file; a first observation is never "
            "a flip; an identical hash across two observations is not a flip; a changed hash "
            "is a flip and correctly attributes the (monkeypatched) changed files; the report "
            "correctly counts a 3-entry synthetic history with 2 distinct hashes and 1 flip; "
            "an absent history file reports cleanly instead of crashing. Wired into "
            "`scripts/retrofits/run_gate_a_local_poc_portfolio_loop.sh`: one observation per "
            "wrapper invocation (not per iteration, since the hash cannot change mid-pass), "
            "`|| true` so it can never affect the wrapper's own pass/fail. Took one real "
            "baseline observation by hand at HEAD "
            "(`.venv/Scripts/python "
            "scripts/governance/log_document_template_hash_observation.py`), "
            "confirmed `--report` reads it back correctly (1 observation, 1 distinct hash, 0 "
            "flips) and that the local history file lands under gitignored `runs/` as "
            "intended (no unexpected tracked-file diff). This is a measurement tool, not a "
            "conclusion: no flip-rate data exists yet beyond this single baseline point -- "
            "CORE-039's actual cost impact remains unmeasured until the instrumentation "
            "accumulates real history across future portfolio passes."
        ),
        "traceability": (
            "Tier 1 of the same 2026-08-29 leaner, goal-sequenced plan as GOV-033; a "
            "same-day, near-zero-risk prerequisite to deciding whether Decision #111/CORE-039 "
            "is worth its multi-day cost, not a substitute for that decision"
        ),
    },
]


def _append_catalog_rows() -> int:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing_ids = {json.loads(line)["requirement_id"] for line in lines if line.strip()}
    appended = 0
    for row in NEW_ROWS:
        if row["requirement_id"] in existing_ids:
            continue
        record = {
            **row,
            "schema_version": 1,
            "legacy_line": len(lines) + 1,
            "legacy_row_sha256": hashlib.sha256(
                f"native-authored:{row['requirement_id']}".encode()
            ).hexdigest(),
        }
        lines.append(json.dumps(record, ensure_ascii=False))
        appended += 1
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return appended


def _refresh_requirements_md_summary() -> None:
    data = REQUIREMENTS_MD_PATH.read_bytes()
    original_text = data.decode("utf-8")
    if "\r\n" not in original_text:
        raise SystemExit("expected requirements.md to be CRLF-encoded; got no CRLF at all")
    text = original_text.replace("\r\n", "\n")

    catalog_text = CATALOG_PATH.read_text(encoding="utf-8")
    lines = [json.loads(line) for line in catalog_text.splitlines() if line.strip()]
    total = len(lines)
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for record in lines:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
        family_match = re.match(r"^([A-Z0-9]+)-", record["requirement_id"])
        if family_match:
            family = family_match.group(1)
            family_counts[family] = family_counts.get(family, 0) + 1

    total_anchor = text.index("The catalog contains")
    total_pattern = re.compile(r"The catalog contains \*\*\d+\*\* requirements \([0-9-]+ -- ")
    new_total_prefix = f"The catalog contains **{total}** requirements (2026-08-29 -- "
    match = total_pattern.match(text, total_anchor)
    if match is None:
        raise SystemExit("failed to locate the catalog-count summary line")
    text = text[: match.start()] + new_total_prefix + text[match.end() :]
    after_total = match.start() + len(new_total_prefix)

    bullet_start = text.index("- `", after_total)
    families_anchor = text.index("Families: ", bullet_start)
    bullet_end = text.rindex("\n\n", bullet_start, families_anchor) + 1
    status_lines = "".join(
        f"- `{status}`: {count}\n" for status, count in sorted(status_counts.items())
    )
    text = text[:bullet_start] + status_lines + text[bullet_end:]

    families_line_pattern = re.compile(r"Families: .*?\.\n")
    families_text = ", ".join(
        f"`{family}` {count}" for family, count in sorted(family_counts.items())
    )
    text, count = families_line_pattern.subn(f"Families: {families_text}.\n", text, count=1)
    if count != 1:
        raise SystemExit("failed to locate the Families summary line")

    REQUIREMENTS_MD_PATH.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))


def main() -> None:
    appended = _append_catalog_rows()
    _refresh_requirements_md_summary()
    print(f"appended {appended} new row(s), refreshed requirements.md")


if __name__ == "__main__":
    main()
