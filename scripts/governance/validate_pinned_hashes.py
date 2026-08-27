"""Pinned-content-hash enforcement (Decision #109, requirement GOV-032, 2026-08-27
production recovery sprint).

A recurring drift class in this repository: some file records a hash or count against
another file's content, and nothing mechanically re-checks that the pin still matches
recomputed truth. The 2026-08-27 production recovery sprint found six live instances of
exactly this pattern, none a behavioral regression -- all a real, verified change whose
recorded pin was never updated in the same commit. Two are already covered by their own
existing dedicated pytest tests (`test_checks_source_hash_matches_recorded_version`,
`test_vendored_check_battery_matches_its_content_addressed_manifest`) and are deliberately
NOT duplicated here. This script covers the remaining, currently entirely unchecked
instances: `plans/requirements.md`'s hand-maintained summary vs. the normative catalog,
and the Level-8 mission graph's three content-addressed pointer blocks vs. their target
files.

Run standalone: `.venv/Scripts/python scripts/governance/validate_pinned_hashes.py`
Exit 0 = every pin matches recomputed truth. Exit 1 = at least one mismatch, with the
exact command to re-pin printed for each.

Intentionally NOT run as part of `run_full_pytest.py` -- a separate, fast, independent CI
job (Decision #109: "separate from the full pytest matrix, so it fails loudly ... instead
of blending into a wall of failures").
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"
REQUIREMENTS_MD_PATH = REPO_ROOT / "plans" / "requirements.md"
GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)


class Mismatch(NamedTuple):
    label: str
    detail: str
    fix_command: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl_records(path: Path) -> list[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _requirements_summary(records: list[dict]) -> tuple[int, dict[str, int], dict[str, int]]:
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for record in records:
        status = record.get("status", "?")
        status_counts[status] = status_counts.get(status, 0) + 1
        match = re.match(r"([A-Z0-9]+)-", record.get("requirement_id", ""))
        if match:
            family = match.group(1)
            family_counts[family] = family_counts.get(family, 0) + 1
    return len(records), status_counts, family_counts


def _check_requirements_md(records: list[dict]) -> list[Mismatch]:
    total, status_counts, family_counts = _requirements_summary(records)
    text = REQUIREMENTS_MD_PATH.read_text(encoding="utf-8")
    mismatches: list[Mismatch] = []

    fix_command = (
        "recompute plans/requirements.md's summary from plans/requirements/catalog.jsonl "
        "(total, per-status counts, per-family counts) and update the three lines by hand -- "
        "no generator script exists yet (that gap is GOV-032's own remaining scope)"
    )

    total_match = re.search(r"catalog contains \*\*(\d+)\*\* requirements", text)
    if total_match is None or int(total_match.group(1)) != total:
        recorded = total_match.group(1) if total_match else "MISSING"
        mismatches.append(
            Mismatch(
                "plans/requirements.md total count",
                f"recorded {recorded}, catalog has {total}",
                fix_command,
            )
        )

    for status, expected_count in sorted(status_counts.items()):
        line_match = re.search(rf"- `{re.escape(status)}`: (\d+)", text)
        if line_match is None or int(line_match.group(1)) != expected_count:
            recorded = line_match.group(1) if line_match else "MISSING"
            mismatches.append(
                Mismatch(
                    f"plans/requirements.md `{status}` count",
                    f"recorded {recorded}, catalog has {expected_count}",
                    fix_command,
                )
            )

    families_line_match = re.search(r"Families: (.+?)\.\s*$", text, re.MULTILINE)
    if families_line_match is None:
        mismatches.append(
            Mismatch("plans/requirements.md Families line", "line not found", fix_command)
        )
    else:
        recorded_families = dict(re.findall(r"`([A-Z0-9]+)`\s+(\d+)", families_line_match.group(1)))
        recorded_families = {k: int(v) for k, v in recorded_families.items()}
        if recorded_families != family_counts:
            mismatches.append(
                Mismatch(
                    "plans/requirements.md Families line",
                    f"recorded {recorded_families} != catalog {family_counts}",
                    fix_command,
                )
            )

    return mismatches


def _check_graph_pointers() -> list[Mismatch]:
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    mismatches: list[Mismatch] = []

    for pointer_key, count_field in (
        ("requirement_catalog", "record_count"),
        ("deferred_task_catalog", "record_count"),
    ):
        pointer = graph.get(pointer_key)
        if not isinstance(pointer, dict):
            continue
        target_path = REPO_ROOT / pointer["path"]
        actual_bytes = target_path.read_bytes()
        actual_sha256 = _sha256_bytes(actual_bytes)
        actual_count = sum(1 for line in actual_bytes.decode("utf-8").splitlines() if line.strip())
        fix_command = (
            f"recompute sha256/{count_field} for {pointer['path']} and update "
            f"level8-autonomous-mission-task-graph.yaml's `{pointer_key}:` block"
        )
        if pointer.get("sha256") != actual_sha256:
            mismatches.append(
                Mismatch(
                    f"graph `{pointer_key}.sha256`",
                    f"recorded {pointer.get('sha256')}, actual {actual_sha256}",
                    fix_command,
                )
            )
        if pointer.get(count_field) != actual_count:
            mismatches.append(
                Mismatch(
                    f"graph `{pointer_key}.{count_field}`",
                    f"recorded {pointer.get(count_field)}, actual {actual_count}",
                    fix_command,
                )
            )

    coverage_pointer = graph.get("requirement_coverage")
    if isinstance(coverage_pointer, dict):
        coverage_path = REPO_ROOT / coverage_pointer["path"]
        coverage_bytes = coverage_path.read_bytes()
        actual_sha256 = _sha256_bytes(coverage_bytes)
        fix_command = (
            "regenerate plans/investigations/evidence/level8-requirement-taskcard-coverage/"
            "requirement-taskcard-coverage.json via "
            "scripts/governance/build_level8_requirement_taskcard_coverage.py, then update the "
            "graph's `requirement_coverage:` pointer block to match"
        )
        if coverage_pointer.get("sha256") != actual_sha256:
            mismatches.append(
                Mismatch(
                    "graph `requirement_coverage.sha256`",
                    f"recorded {coverage_pointer.get('sha256')}, actual {actual_sha256}",
                    fix_command,
                )
            )
        coverage_json = json.loads(coverage_bytes)
        actual_source_sha256 = _sha256_bytes(REQUIREMENTS_CATALOG_PATH.read_bytes())
        if coverage_json.get("source_sha256") != actual_source_sha256:
            mismatches.append(
                Mismatch(
                    "requirement-taskcard-coverage.json `source_sha256` vs. live catalog",
                    f"coverage report was generated against a different catalog revision "
                    f"(recorded {coverage_json.get('source_sha256')}, live catalog is "
                    f"{actual_source_sha256}) -- the coverage report itself is stale, not "
                    f"just its pointer",
                    fix_command,
                )
            )

    return mismatches


def main() -> int:
    records = _jsonl_records(REQUIREMENTS_CATALOG_PATH)
    mismatches = [*_check_requirements_md(records), *_check_graph_pointers()]

    if not mismatches:
        print(f"Pinned hashes clean ({len(records)} requirement records checked).")
        return 0

    for mismatch in mismatches:
        print(f"ERROR: {mismatch.label}: {mismatch.detail}")
        print(f"  fix: {mismatch.fix_command}")
    print(f"\n{len(mismatches)} pinned-hash mismatch(es) found.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
