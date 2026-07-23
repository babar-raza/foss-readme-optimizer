# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Semantic implementation-truth matrix for requirement closure claims.

For every `plans/requirements.md` row currently marked `IMPLEMENTED`, checks that cited paths exist,
cited pytest node IDs resolve to real functions/methods, cited JSON evidence parses, evidence files
are checksum-addressed in the generated matrix, and the row's own acceptance prose does not
explicitly contradict its `IMPLEMENTED` status. P0/P1 closure also requires a concrete test node or
a committed evidence artifact; a path-only citation is no longer accepted as semantic proof.

This remains downgrade-only: it never promotes a row or infers that a passing test proves more than
the row cites. It establishes the machine-checkable semantic floor required before deeper human or
independent-agent review.

Uses an escape-aware table-row splitter (matching `scripts/governance/validate_plan_structure.py`'s
own `_split_table_row()`, duplicated here rather than imported so this investigations tool stays
standalone -- never imported by `src/`, per this project's existing tool-placement convention.

Also generates `plans/status.md` (Wave 9.3): a short, mechanically-computed current-status summary
-- requirement counts by status, Build Checklist wave state, latest decision number -- replacing
`plans/master.md`'s old hand-maintained Status section, which routinely drifted (this project's own
`validate_plan_structure.py::check_master_status_mentions_latest_decision` warning exists precisely
because that section kept falling behind). `plans/status.md` is generated, never hand-edited; rerun
this tool to refresh it.

Output: plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json, plans/status.md
Usage:
  python plans/investigations/tools/traceability_matrix.py
  python plans/investigations/tools/traceability_matrix.py --check
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # tools -> investigations -> plans -> repo root
REQUIREMENTS_MD = REPO_ROOT / "plans" / "requirements.md"
MASTER_MD = REPO_ROOT / "plans" / "master.md"
STATUS_MD = REPO_ROOT / "plans" / "status.md"
OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "implementation-truth-matrix-2026"
OUT_FILE = OUT_DIR / "matrix.json"

WAVE_CHECKLIST_RE = re.compile(r"^- \[(x| )\] (Wave \d+(?:\.\d+)? — [^\n]*)", re.MULTILINE)
DECISION_RE = re.compile(r"^(\d+)\.\s+\*\*", re.MULTILINE)

ID_RE = re.compile(r"^[A-Z]{2,5}-\d{3}$")
_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")

# Backtick-quoted paths that look like real repo-relative references. Keep an optional pytest
# `::Class::test_method` suffix so closure claims resolve the exact cited symbol, not just its file.
CITED_REFERENCE_RE = re.compile(
    r"`((?:src/readme_agent|tests|scripts|\.github/workflows|docs|plans|config|data)/[^`\s()]+)"
)
LIVE_EVIDENCE_RE = re.compile(
    r"live[- ]proven|confirmed live|real gateway|real pilot|live,? 2026-|real PR|live proof",
    re.IGNORECASE,
)
CONTRADICTED_IMPLEMENTATION_RE = re.compile(
    r"\bstill honestly unmet\b"
    r"|\b(?:this|the) (?:requirement|guarantee|acceptance|row) (?:is|remains) "
    r"(?:unmet|partial|incomplete|not implemented)\b"
    r"|\bcannot be considered implemented\b"
    r"|\bstatus (?:must|should) (?:remain|be) [`*]*(?:PARTIAL|BACKLOG|PLANNED)[`*]*",
    re.IGNORECASE,
)
EVIDENCE_PREFIXES = ("plans/investigations/evidence/",)


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in _UNESCAPED_PIPE_RE.split(stripped)]


def _extract_citations(evidence_text: str) -> list[dict[str, str | None]]:
    citations: list[dict[str, str | None]] = []
    for match in CITED_REFERENCE_RE.finditer(evidence_text):
        candidate = match.group(1).rstrip(".,:;")
        file_part, separator, symbol = candidate.partition("::")
        citations.append(
            {
                "raw": candidate,
                "path": file_part,
                "symbol": symbol if separator else None,
            }
        )
    return citations


def _top_level_symbols(tree: ast.Module) -> dict[str, ast.AST]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _class_contains_tests(node: ast.ClassDef) -> bool:
    return any(
        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and member.name.startswith("test_")
        for member in node.body
    )


def _test_symbol_resolves(path: str, symbol: str) -> tuple[bool, str | None]:
    """Resolve a cited pytest test or suite against the AST without importing test code."""
    try:
        tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"), filename=path)
    except (OSError, SyntaxError) as exc:
        return False, f"cannot parse cited test file `{path}`: {exc}"

    segments = [segment.split("[", 1)[0] for segment in symbol.split("::") if segment]
    if not segments:
        return False, f"cites `{path}::` without a test symbol"

    symbols = _top_level_symbols(tree)
    current = symbols.get(segments[0])
    # Historical requirement prose sometimes cites a class method as `file.py::test_method`
    # rather than its canonical pytest node `file.py::Class::test_method`. Accept it only when
    # exactly one method with that name exists, avoiding an ambiguous best guess.
    if current is None and len(segments) == 1:
        nested_matches = [
            member
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            for member in node.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name == segments[0]
        ]
        if len(nested_matches) == 1 and segments[0].startswith("test_"):
            return True, None
    if current is None:
        return False, f"cited test symbol `{path}::{symbol}` does not exist"
    for segment in segments[1:]:
        if not isinstance(current, ast.ClassDef):
            return False, f"cited test symbol `{path}::{symbol}` does not exist"
        members = {
            node.name: node
            for node in current.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        current = members.get(segment)
        if current is None:
            return False, f"cited test symbol `{path}::{symbol}` does not exist"
    if isinstance(current, ast.ClassDef):
        if _class_contains_tests(current):
            return True, None
        return False, f"cited pytest suite `{path}::{symbol}` contains no tests"
    if not segments[-1].startswith("test_"):
        return False, f"cited pytest symbol `{path}::{symbol}` is not a test or suite"
    return True, None


def _evidence_metadata(path: str) -> tuple[dict | None, str | None]:
    if not path.startswith(EVIDENCE_PREFIXES):
        return None, None
    artifact = REPO_ROOT / path
    if not artifact.is_file():
        return None, f"cited evidence artifact `{path}` is not a file"
    payload = artifact.read_bytes()
    metadata: dict[str, object] = {
        "path": path,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if artifact.suffix.lower() == ".json":
        try:
            json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return metadata, f"cited JSON evidence `{path}` does not parse: {exc}"
        metadata["json_valid"] = True
    return metadata, None


def build_matrix() -> dict:
    text = REQUIREMENTS_MD.read_text(encoding="utf-8")
    rows = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("| "):
            continue
        cells = _split_table_row(line)
        if len(cells) != 6:
            continue
        req_id = cells[0].strip("`")
        if not ID_RE.match(req_id):
            continue
        priority, status, requirement, evidence, traceability = cells[1:6]
        if status != "IMPLEMENTED":
            continue

        citations = _extract_citations(evidence)
        cited_paths = list(dict.fromkeys(str(citation["path"]) for citation in citations))
        existing = [p for p in cited_paths if (REPO_ROOT / p).exists()]
        missing = [p for p in cited_paths if not (REPO_ROOT / p).exists()]
        test_paths = [p for p in cited_paths if p.startswith("tests/")]
        concrete_test_nodes = []
        invalid_test_nodes = []
        for citation in citations:
            path = str(citation["path"])
            symbol = citation["symbol"]
            if not path.startswith("tests/") or symbol is None or not (REPO_ROOT / path).exists():
                continue
            resolved, finding = _test_symbol_resolves(path, symbol)
            if resolved:
                concrete_test_nodes.append(str(citation["raw"]))
            elif finding:
                invalid_test_nodes.append(finding)

        evidence_artifacts = []
        evidence_artifact_findings = []
        for path in cited_paths:
            metadata, finding = _evidence_metadata(path)
            if metadata:
                evidence_artifacts.append(metadata)
            if finding:
                evidence_artifact_findings.append(finding)
        has_live_evidence = bool(LIVE_EVIDENCE_RE.search(evidence))
        contradicts_status = bool(CONTRADICTED_IMPLEMENTATION_RE.search(evidence))

        high_confidence_findings = []
        informational_findings = []
        if missing:
            high_confidence_findings.append(
                f"cites {len(missing)} path(s) that do not exist: {missing}"
            )
        high_confidence_findings.extend(invalid_test_nodes)
        high_confidence_findings.extend(evidence_artifact_findings)
        if contradicts_status:
            high_confidence_findings.append(
                "acceptance evidence explicitly contradicts the row's IMPLEMENTED status"
            )
        if priority in {"P0", "P1"} and not concrete_test_nodes and not evidence_artifacts:
            high_confidence_findings.append(
                f"{priority} closure cites neither a concrete pytest node nor a committed "
                "evidence artifact"
            )
        elif not test_paths:
            informational_findings.append(
                "cites zero tests/ paths as evidence (may predate "
                "this project's later per-row citation convention -- not necessarily a real gap)"
            )
        if not has_live_evidence and not test_paths and not cited_paths:
            informational_findings.append(
                "no backtick-quoted path and no live-proof language found at all"
            )

        rows.append(
            {
                "id": req_id,
                "line": lineno,
                "priority": priority,
                "cited_paths": cited_paths,
                "cited_paths_existing": existing,
                "cited_paths_missing": missing,
                "cited_test_paths": test_paths,
                "concrete_test_nodes": concrete_test_nodes,
                "invalid_test_nodes": invalid_test_nodes,
                "evidence_artifacts": evidence_artifacts,
                "has_live_evidence_language": has_live_evidence,
                "acceptance_evidence_contradicts_status": contradicts_status,
                "high_confidence_findings": high_confidence_findings,
                "informational_findings": informational_findings,
            }
        )
    return {
        "generated_by": "plans/investigations/tools/traceability_matrix.py",
        "requirements_source": "plans/requirements.md",
        "total_implemented_rows_checked": len(rows),
        "rows_with_high_confidence_findings": [r for r in rows if r["high_confidence_findings"]],
        "rows_with_informational_findings_only": [
            r for r in rows if r["informational_findings"] and not r["high_confidence_findings"]
        ],
        "rows_clean": [
            r["id"]
            for r in rows
            if not r["high_confidence_findings"] and not r["informational_findings"]
        ],
        "all_rows": rows,
    }


def _requirement_status_counts() -> Counter:
    text = REQUIREMENTS_MD.read_text(encoding="utf-8")
    counts: Counter = Counter()
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = _split_table_row(line)
        if len(cells) != 6:
            continue
        req_id = cells[0].strip("`")
        if not ID_RE.match(req_id):
            continue
        counts[cells[2]] += 1
    return counts


def _wave_checklist_state() -> list[tuple[bool, str]]:
    if not MASTER_MD.exists():
        return []
    text = MASTER_MD.read_text(encoding="utf-8")
    return [(m.group(1) == "x", m.group(2)) for m in WAVE_CHECKLIST_RE.finditer(text)]


def _latest_decision_number() -> int | None:
    if not MASTER_MD.exists():
        return None
    text = MASTER_MD.read_text(encoding="utf-8")
    numbers = [int(n) for n in DECISION_RE.findall(text)]
    return max(numbers) if numbers else None


def build_status_markdown(matrix: dict) -> str:
    status_counts = _requirement_status_counts()
    waves = _wave_checklist_state()
    latest_decision = _latest_decision_number()

    lines = [
        "# Project status (generated -- do not hand-edit)",
        "",
        "Regenerate with `python plans/investigations/tools/traceability_matrix.py`. This replaces "
        "`plans/master.md`'s old hand-maintained Status section (Wave 9.3, 2026-07-22) -- see "
        "`plans/roadmap.md` for what's next and `logs/` for the dated history.",
        "",
        f"**Latest Decision Ledger entry**: #{latest_decision}" if latest_decision else "",
        "",
        "## Requirement status counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in sorted(status_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {status} | {count} |")
    lines += [
        "",
        "## Build Checklist wave state",
        "",
    ]
    for checked, label in waves:
        box = "x" if checked else " "
        lines.append(f"- [{box}] {label}")
    lines += [
        "",
        "## Implementation-truth matrix summary (Wave 9.2)",
        "",
        f"- {matrix['total_implemented_rows_checked']} `IMPLEMENTED` rows checked.",
        f"- {len(matrix['rows_with_high_confidence_findings'])} with a semantic closure finding.",
        f"- {len(matrix['rows_with_informational_findings_only'])} with informational-only "
        "findings (no test path cited -- often pre-dates this project's later per-row citation "
        "convention, not necessarily a real gap).",
        f"- {len(matrix['rows_clean'])} fully clean.",
        "- Full detail: "
        "`plans/investigations/evidence/implementation-truth-matrix-2026/matrix.json`.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="validate without rewriting generated artifacts; exit non-zero on closure findings",
    )
    mode.add_argument(
        "--matrix-only",
        action="store_true",
        help="refresh matrix.json without overwriting the separately gated status candidate",
    )
    args = parser.parse_args(argv)
    matrix = build_matrix()
    if not args.check:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(json.dumps(matrix, indent=2, sort_keys=False), encoding="utf-8")
        if not args.matrix_only:
            STATUS_MD.write_text(build_status_markdown(matrix), encoding="utf-8")

    total = matrix["total_implemented_rows_checked"]
    high = matrix["rows_with_high_confidence_findings"]
    info_only = matrix["rows_with_informational_findings_only"]
    clean = matrix["rows_clean"]
    print(f"Checked {total} IMPLEMENTED rows.")
    print(f"  {len(high)} row(s) with a semantic closure finding.")
    print(f"  {len(info_only)} row(s) with informational-only findings (no test path cited).")
    print(f"  {len(clean)} row(s) fully clean.")
    if not args.check:
        print(f"Written: {OUT_FILE.relative_to(REPO_ROOT)}")
        if not args.matrix_only:
            print(f"Written: {STATUS_MD.relative_to(REPO_ROOT)}")
    if high:
        print("\nHigh-confidence findings (real, actionable):")
        for row in high:
            print(
                f"  {row['id']} (line {row['line']}): {'; '.join(row['high_confidence_findings'])}"
            )
    return 1 if args.check and high else 0


if __name__ == "__main__":
    raise SystemExit(main())
