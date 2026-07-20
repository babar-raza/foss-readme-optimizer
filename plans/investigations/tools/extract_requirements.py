# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Extract every requirement row from plans/requirements.md into a normalized
machine-readable inventory (YAML), asserting ID uniqueness (GOV-001/002).

Read-only with respect to the governed documents. Output:
  plans/investigations/control/normalized-requirements-inventory.yaml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]  # tools -> investigations -> plans -> repo root
REQUIREMENTS_MD = REPO_ROOT / "plans" / "requirements.md"
OUT_DIR = REPO_ROOT / "plans" / "investigations" / "control"
OUT_FILE = OUT_DIR / "normalized-requirements-inventory.yaml"

# A requirement row: | GOV-001 | P0 | GOVERNANCE | text | evidence | traceability |
ROW_RE = re.compile(
    r"^\|\s*(?P<id>[A-Z]+-\d{3})\s*"
    r"\|\s*(?P<priority>P\d)\s*"
    r"\|\s*(?P<status>[A-Z-]+)\s*"
    r"\|\s*(?P<requirement>.*?)\s*"
    r"\|\s*(?P<evidence>.*?)\s*"
    r"\|\s*(?P<traceability>.*?)\s*\|\s*$"
)
SECTION_RE = re.compile(r"^##\s+(?P<num>\d+)\.\s+(?P<title>.+?)\s*$")
DECISION_RE = re.compile(r"Decisions?\s+([\d–\-, /]+)")
PHASE_RE = re.compile(r"Phases?\s+([\d–\-, /]+)")

VALID_STATUSES = {
    "IMPLEMENTED",
    "PARTIAL",
    "PLANNED",
    "RESEARCH-GATED",
    "GOVERNANCE",
    "DEPRECATED",
}


def _expand_ref_list(raw: str) -> list[str]:
    """'18-24' -> ['18','19',...]; '16, 25' -> ['16','25']; keeps order, dedupes."""
    out: list[str] = []
    for chunk in re.split(r"[,/]", raw):
        chunk = chunk.strip().rstrip(".")
        if not chunk:
            continue
        m = re.match(r"^(\d+)\s*[–\-]\s*(\d+)$", chunk)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            out.extend(str(i) for i in range(lo, hi + 1))
        elif chunk.isdigit():
            out.append(chunk)
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def main() -> int:
    text = REQUIREMENTS_MD.read_text(encoding="utf-8")
    rows: list[dict] = []
    section = ""
    problems: list[str] = []

    for line in text.splitlines():
        sec = SECTION_RE.match(line)
        if sec:
            section = f"{sec.group('num')}. {sec.group('title')}"
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        d = m.groupdict()
        trace = d["traceability"]
        rows.append(
            {
                "id": d["id"],
                "group": d["id"].split("-")[0],
                "priority": d["priority"],
                "status": d["status"],
                "section": section,
                "requirement": d["requirement"],
                "acceptance_evidence": d["evidence"],
                "traceability_raw": trace,
                "decision_refs": _expand_ref_list(" ".join(DECISION_RE.findall(trace))),
                "phase_refs": _expand_ref_list(" ".join(PHASE_RE.findall(trace))),
            }
        )
        if d["status"] not in VALID_STATUSES:
            problems.append(f"{d['id']}: unknown status {d['status']!r}")

    ids = [r["id"] for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        problems.append(f"duplicate IDs (GOV-001/002 violation): {dupes}")

    by_group: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for r in rows:
        by_group[r["group"]] = by_group.get(r["group"], 0) + 1
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        by_priority[r["priority"]] = by_priority.get(r["priority"], 0) + 1

    inventory = {
        "governed_by": ["plans/master.md", "plans/requirements.md", "plans/GOVERNANCE.md"],
        "artifact_role": "analysis_or_evidence_only",
        "source_document": "plans/requirements.md",
        "source_head_commit": "4adbaaf33d3c733afc8f9c9a14761f10e5b10d7c",
        "totals": {
            "requirements": len(rows),
            "unique_ids": len(set(ids)),
            "by_group": dict(sorted(by_group.items())),
            "by_status": dict(sorted(by_status.items())),
            "by_priority": dict(sorted(by_priority.items())),
        },
        "integrity_problems": problems,
        "requirements": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        yaml.safe_dump(inventory, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )

    print(f"requirements: {len(rows)}  unique: {len(set(ids))}  dupes: {dupes or 'none'}")
    print(f"by_group: {dict(sorted(by_group.items()))}")
    print(f"by_status: {dict(sorted(by_status.items()))}")
    print(f"by_priority: {dict(sorted(by_priority.items()))}")
    print(f"problems: {problems or 'none'}")
    print(f"wrote: {OUT_FILE.relative_to(REPO_ROOT)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
