#!/usr/bin/env python3
"""One-shot: log 5 commits landed by a separate concurrent agent (Codex, OpenAI --
`Co-Authored-By: Codex <noreply@openai.com>` on all 5) into this project's own governance
trail. The user's instruction was explicit and read-only in scope: "another agent moved
forward with the execution of main goal. Check everything and report the current status" ->
report only, no fixing -- followed by "log it" after this session's own report noted the
commits touch no logs/, plans/master.md, or requirements catalog. This script performs only
that logging: two requirement rows (VER-015, CORE-043) with evidence read directly from each
commit's full diff, no code changes.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/log_codex_bounded_review_and_narration_fixes.py`
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
        "requirement_id": "VER-015",
        "section": "19. Autonomous runtime and capability requirements",
        "status": "IMPLEMENTED",
        "priority": "P2",
        "requirement": (
            "The bounded independent review packetization/caching machinery MUST split an "
            "oversized Markdown table atomic unit into row-bounded fragments (targeting a "
            "provider-latency-bounded chunk size, not just the raw packet budget) instead of "
            "routing it into the unpacketizable/oversized bucket, and coverage acceptance "
            "MUST require a unit's cited packets to fully, byte-for-byte cover it before "
            "counting it as covered. Separately, bundle resealing after an interrupted review "
            "MUST be able to recover: a `sha256sums.txt` inventory that predates now-present, "
            "individually valid `review/bounded-packet-cache/*.json` entries written by the "
            "interrupted attempt MUST be resealable without promoting any unvalidated content "
            "or accepting a review verdict, and recovery MUST ignore nested/independently "
            "sealed inventories (e.g. under `superseded/`) rather than misreading them as loose "
            "extra files."
        ),
        "acceptance_evidence": (
            "VER015-CODEX-BOUNDED-REVIEW-ROBUSTNESS-001 (2026-08-28): landed by a separate "
            "agent (Codex, OpenAI) working this same mission concurrently on this machine -- "
            "every commit below carries `Co-Authored-By: Codex <noreply@openai.com>`. Found "
            "read-only while investigating repo state per the user's explicit instruction "
            "('another agent moved forward with the execution of main goal. Check everything "
            "and report the current status'); this session did not write any of the code "
            "described here, and logged it only after the user's follow-up 'log it'. Four "
            "commits, read in full diff before writing this row: "
            "(1) `1b44c54570a89ac4d6026285dab9b3435dc28da1` 'fix(review): split oversized "
            "factual tables' (2026-08-28T14:51:11+05:00) -- adds "
            "`_split_oversized_table_unit()` to `bounded_review_packers.py`, splitting an "
            "oversized Markdown table `_MutableUnit` at row boundaries into multiple parts via "
            "`dataclasses.replace` (preserving `claim_ids`/`provenance_ids` on every part; "
            "fails closed, returning `()`, if even a single row alone still exceeds budget); "
            "`_build_factual_packets()` tries this before falling back to the "
            "oversized/unpacketizable bucket. `bounded_review_coverage.py` gains "
            "`retain_only_complete_coverage()`, zeroing a unit's `factual_covering`/"
            "`visitor_covering` unless its cited packets' spans fully cover it -- closing a "
            "partial-coverage-counted-as-covered gap for split units. New test in "
            "`test_bounded_review_packets.py`, `test_oversized_factual_table_is_split_"
            "exhaustively_at_row_boundaries` (2,400-row synthetic table), asserts exhaustive "
            "byte coverage and contiguous packet boundaries. "
            "(2) `b9dacca2e292a97084541d7bb41b388650ea5109` 'fix(review): bound oversized "
            "table fragments' (2026-08-28T15:15:16+05:00) -- adds "
            "`_OVERSIZED_TABLE_PACKET_TARGET_CHARS = 40_000`; `_split_oversized_table_unit()` "
            "now targets `min(budget_chars, 40_000)` instead of the full "
            "`DEFAULT_BOUNDED_PACKET_BUDGET_CHARS` (120,000), 'so provider latency remains "
            "bounded' per the commit's own table-fragment sizing; also adds a de-duplication "
            "guard in `_greedy_group_units()` preventing a repeated `unit_id` (a split table's "
            "multiple parts share one logical unit id) from being merged twice into the same "
            "packet group. Test threshold updated from the full budget to 40,000. "
            "(3) `1ada61acb63bdce2cc5c687d5d0b5fc020580f5d` 'fix(evidence): recover "
            "interrupted review caches' (2026-08-28T15:24:23+05:00) -- new file "
            "`local_poc_bounded_review_recovery.py` "
            "(`recover_interrupted_bounded_review_cache_write(bundle_dir, *, org_repo, "
            "source_revision) -> bool`): validates every artifact the existing "
            "`sha256sums.txt` inventory already covers still matches exactly (refusing "
            "recovery on any mismatch), then requires every extra on-disk file to match "
            "`review/bounded-packet-cache/<64-hex>.json` and structurally validate as a "
            "`BoundedReviewPacketCacheV1` whose `cache_key`/`org_repo`/`source_revision` all "
            "agree with its filename and the caller's expected identity, before calling "
            "`refresh_sha256sums()` + `verify_sha256sums()`; returns `False` (no reseal) on "
            "any `OSError`/`UnicodeError`/`ValidationError`/`ValueError`, or if there are zero "
            "extra files at all. Wired into `local_poc_snapshot_evidence.py`'s "
            "`_validate_sealed_snapshot()` as a third recovery attempt alongside the existing "
            "section-authoring and candidate-supersession recovery paths, all gated behind "
            "`verify_sha256sums(bundle_dir)` already failing. This is the direction-opposite "
            "counterpart of this session's own still-open VER-014 finding (VER-014: files "
            "recorded in the inventory but missing from disk block acceptance; this commit: "
            "files present on disk but missing from the inventory, from an interrupted write, "
            "are now safely reseal-able) -- not confirmed whether the two share a root cause; "
            "not fixed further here, logging only. New test in `test_bounded_review_cache.py`, "
            "`test_interrupted_packet_cache_writes_are_validated_and_resealed`. "
            "(4) `0e1aba5fd7df02487f8b344a5970d36bc52aaff3` 'fix(evidence): ignore nested "
            "checksum manifests' (2026-08-28T15:28:13+05:00) -- one-line follow-up to (3): the "
            "'actual on-disk files' enumeration excluded `sha256sums.txt` by relative-path "
            "equality (`relative.as_posix() != 'sha256sums.txt'`), which missed a nested, "
            "independently-sealed inventory (e.g. `superseded/prior/sha256sums.txt`), "
            "misreading it as a loose extra cache file and failing structural validation "
            "against it; changed to filename equality (`physical.name != 'sha256sums.txt'`), "
            "excluding every such nested inventory regardless of path depth. New test setup in "
            "`test_bounded_review_cache.py` seeds exactly this nested-inventory case. All four "
            "commits' own new/changed tests pass as part of the full-suite baseline captured "
            "under CORE-043 below (run "
            "`bh649w3vt`, `dirty_tree: true` from this session's own uncommitted capsule "
            "regeneration only, `tree_changed_during_run: false`, HEAD "
            "`d8795bbdbe6d51778956c1daf8cddf1642c8b00f`): **5 failed, 5463 passed, 1 "
            "skipped** -- the 4 pre-existing VER-014/RDM-034 failures plus exactly one new "
            "failure, `test_vendored_check_battery_matches_its_content_addressed_manifest` "
            "(see CORE-043's own evidence for that one; unrelated to this row's 4 commits). "
            "Not independently re-verified by this session beyond reading the full diffs and "
            "confirming the trustworthy full-suite counts above -- this session did not author "
            "or modify this code."
        ),
        "traceability": (
            "landed 2026-08-28 by a separate concurrent agent (Codex); logged into this "
            "project's governance trail by this session per explicit user instruction "
            "('log it') after this session's own read-only status report flagged the gap"
        ),
    },
    {
        "requirement_id": "CORE-043",
        "section": "9. Core engine and registry requirements",
        "status": "IMPLEMENTED",
        "priority": "P2",
        "requirement": (
            "The vendored Aspose.org process-narration/internal-reference leak checks "
            "(`readme_refresh_checks.py::check_process_narration_smells()` and "
            "`check_no_internal_details_leaked_into_issue_draft()`) MUST scan large generated "
            "READMEs (e.g. a several-thousand-row API-reference table) in bounded time, "
            "without relying on a single large alternation regex's repeated backtracking "
            "across the whole document, and MUST preserve the exact same match set, document "
            "order, and 40-character context window as the prior single-regex implementation."
        ),
        "acceptance_evidence": (
            "CORE043-CODEX-NARRATION-SCAN-BOUND-001 (2026-08-28): landed by the same separate "
            "concurrent agent (Codex, OpenAI) as VER-015 above -- see that row for the shared "
            "process/attribution context; read in full diff before writing this row, this "
            "session did not author or modify this code. "
            "`d8795bbdbe6d51778956c1daf8cddf1642c8b00f` 'perf(validation): bound narration "
            "scans' (2026-08-28T15:41:21+05:00): replaces the single combined-alternation "
            "`_PROCESS_NARRATION_RE.finditer()` scan with `_find_process_narration_matches()`, "
            "which runs each of the ~20 individual narration patterns as its own compiled "
            "regex (`_PROCESS_NARRATION_RES`), collects all candidate matches "
            "`(start, pattern_index, end, phrase)` across every pattern, sorts by start "
            "position, and greedily keeps the first non-overlapping match per position "
            "(`consumed_until` cursor) -- reproducing the same leftmost-longest-alternation "
            "semantics as the single combined regex, in the same document order, without one "
            "large alternation's own backtracking cost scaling with the number of "
            "alternatives per scan position. Both call sites "
            "(`check_process_narration_smells()` and "
            "`check_no_internal_details_leaked_into_issue_draft()`) switched to the shared "
            "helper; the issue-draft check keeps its separate `_ISSUE_DRAFT_ADDITIONAL_LEAK_RE` "
            "pass unchanged (only the narration half was bounded). New test file "
            "`test_process_narration_checks.py`: one correctness test asserting exact phrase "
            "order/content is unchanged on a small fixture, one perf-bound test asserting a "
            "4,000-row synthetic API table scans with zero findings in under 5 seconds. "
            "KNOWN, NOT-YET-FIXED CONSEQUENCE (found by this session while investigating, "
            "flagged per this project's 'root-caused, not rushed' convention, explicitly out "
            "of scope for this logging-only pass -- the user asked only to log Codex's work, "
            "not to fix it): this commit edited "
            "`src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/"
            "readme_refresh_checks.py` in place without re-pinning its recorded hash in "
            "`data/imported/aspose_org_check_battery_manifest.json` (recorded "
            "`ef3fafc842606643f084af7ae590a7edbbb72540d091719eedce258ecfac2321`, actual "
            "`21fbcd4a2f1b051468c42fd1bfbcf85e92e058329645cb8da3052e5f9f293ead`, confirmed by "
            "direct SHA-256 computation; sibling file `api_table_dupes.py` still matches at "
            "`a6fc0e17b26eb8009e35765f44e5ac229e42777b36a97354d6e7b57aa369a8c2`) -- an exact "
            "recurrence of the GOV-032/Decision #109 pinned-content-hash drift pattern, this "
            "session's own earlier commit `515369d1a` having fixed the identical drift class "
            "for the same file once already this session. This is not a governance-registry "
            "gap: GOV-032's own `validate_pinned_hashes.py` deliberately does NOT cover this "
            "file (its module docstring says so explicitly), because it is already covered by "
            "its own dedicated pytest test, "
            "`test_aspose_org_check_battery_source.py::"
            "test_vendored_check_battery_matches_its_content_addressed_manifest` -- and that "
            "test caught this drift exactly as designed, which is why it is the one new "
            "failure in the full-suite run cited under VER-015 above (5 failed, 5463 passed, "
            "1 skipped, vs. 4 failed pre-existing). Re-pinning the manifest hash is a small, "
            "low-risk, mechanical fix (identical in shape to `515369d1a`) but is intentionally "
            "left undone here, pending explicit authorization."
        ),
        "traceability": (
            "landed 2026-08-28 by a separate concurrent agent (Codex); logged into this "
            "project's governance trail by this session per explicit user instruction "
            "('log it') after this session's own read-only status report flagged the gap"
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
    new_total_prefix = f"The catalog contains **{total}** requirements (2026-08-28 -- "
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
