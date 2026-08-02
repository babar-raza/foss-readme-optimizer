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

RPOC-072 (sprint charter Part B.2 Phase 5 Lane S) makes `plans/status.md`'s PRIMARY table
repository-outcome-based instead of requirement/test/capability-count-based: a per-
`data/products.json`-entry (loaded live via `readme_agent.registry.loader.load_products()`,
never hard-coded) table of org/repo, ecosystem, mode, and current `readme_poc_status`
(RPOC-070 lifecycle vocabulary, `src/readme_agent/state/lifecycle_schema.py::
ReadmePocStatusV1`), joined against the most recent `portfolio-proof-manifest.json` under
`plans/investigations/evidence/` (RPOC-071's `compute_portfolio_summary_aggregates()`
produced that manifest's per-repo `readme_poc_status` field). A repo missing from the
manifest entirely (the 3 Java pilots, proven through their own dedicated evidence path, or
any registry entry newer than the last portfolio run) is reported `not yet run`, never
silently dropped or faked as populated. The pre-existing requirement-status-count table and
Build Checklist summary remain below it as supporting governance detail -- the charter
retires them as the *main* measure, not as content to delete.

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
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # tools -> investigations -> plans -> repo root
REQUIREMENTS_MD = REPO_ROOT / "plans" / "requirements.md"
MASTER_MD = REPO_ROOT / "plans" / "master.md"
STATUS_MD = REPO_ROOT / "plans" / "status.md"
OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "implementation-truth-matrix-2026"
OUT_FILE = OUT_DIR / "matrix.json"
PRODUCTS_JSON = REPO_ROOT / "data" / "products.json"
EVIDENCE_ROOT = REPO_ROOT / "plans" / "investigations" / "evidence"
PORTFOLIO_MANIFEST_GLOB = "*/portfolio-proof-manifest.json"
MISSION_GRAPH_PATH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
REGISTRY_REVISION_PATH = REPO_ROOT / "runs" / "registry-revisions" / "current.json"

sys.path.insert(0, str(REPO_ROOT / "src"))
from readme_agent.registry.loader import load_products  # noqa: E402
from readme_agent.registry.revision import RegistryRevisionV1, products_registry_hash  # noqa: E402
from readme_agent.registry.revision_gate import evaluate_registry_revision  # noqa: E402
from readme_agent.state.git_backend import default_state_backend  # noqa: E402
from readme_agent.supervisor.mission_control import has_graph_drift, mission_state_key  # noqa: E402
from readme_agent.supervisor.mission_goal_guard import derive_lifecycle_scoreboard  # noqa: E402
from readme_agent.supervisor.mission_graph import load_mission_graph  # noqa: E402

_EVIDENCE_DIR_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

WAVE_CHECKLIST_RE = re.compile(r"^- \[(x| )\] (Wave \d+(?:\.\d+)? — [^\n]*)", re.MULTILINE)
DECISION_RE = re.compile(r"^(\d+)\.\s+\*\*", re.MULTILINE)

# Requirement families include the Level-8 consolidation namespace (`L8-001`),
# whose prefix intentionally contains a digit. Keep this aligned with the
# mission-coverage parser so generated status cannot omit an authoritative
# requirement family.
ID_RE = re.compile(r"^[A-Z][A-Z0-9]{1,4}-\d{3}$")
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


def _find_latest_portfolio_manifest(evidence_root: Path | None = None) -> Path | None:
    """Most recent `portfolio-proof-manifest.json` under `plans/investigations/evidence/`
    (RPOC-072). Ranked by the `YYYY-MM-DD` date embedded in its containing evidence
    directory's name (this project's own dated-evidence-dir naming convention, e.g.
    `level8-portfolio-readme-proposals-2026-07-25`); a directory whose name carries no
    date sorts oldest rather than raising, so an unusually-named future manifest is
    still found, just not preferred over a clearly-dated one. Returns None (never
    raises) when no manifest exists yet -- callers report that as `not yet run` for
    every repo, not a crash. `evidence_root` defaults to None (resolved to the module
    -level `EVIDENCE_ROOT` global here, at call time) rather than binding `EVIDENCE_ROOT`
    as a parameter default -- a parameter default is captured once at function-definition
    time, which would silently ignore a test's `monkeypatch.setattr(module, "EVIDENCE_ROOT",
    ...)`."""
    if evidence_root is None:
        evidence_root = EVIDENCE_ROOT
    if not evidence_root.is_dir():
        return None
    candidates = sorted(evidence_root.glob(PORTFOLIO_MANIFEST_GLOB))
    if not candidates:
        return None

    def _sort_key(path: Path) -> tuple[str, float]:
        match = _EVIDENCE_DIR_DATE_RE.search(path.parent.name)
        date_key = match.group(1) if match else ""
        return (date_key, path.stat().st_mtime)

    return max(candidates, key=_sort_key)


def _full_registry_readme_poc_status_rows() -> tuple[list[dict], Path | None, dict | None]:
    """RPOC-072: per-`data/products.json`-entry (live, never hard-coded) README-POC
    lifecycle status, joined against the most recent portfolio-proof-manifest.json.
    This is the sprint charter's PRIMARY status measure (Part B.2 Phase 5 Lane S) --
    not requirement/test/capability counts, plan closure, or three-pilot status.

    A repo absent from the manifest entirely (the 3 Java pilots, proven through their
    own dedicated evidence path -- see `collect_local_readme_proposal_evidence.py` --
    or any registry entry newer than the last portfolio run) is reported `not yet run`.
    A repo present in the manifest whose `readme_poc_status` is `None` (the RPOC-070
    lifecycle field is brand new and not yet driven by a real production run for most
    repos) is reported `not_set`, matching `compute_portfolio_summary_aggregates()`'s
    own `status_distribution["not_set"]` convention -- never faked as populated."""
    manifest_path = _find_latest_portfolio_manifest()
    manifest: dict | None = None
    results_by_org_repo: dict[str, dict] = {}
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for result in manifest.get("results", []):
            org_repo = result.get("org_repo")
            if org_repo:
                results_by_org_repo[org_repo] = result

    rows = []
    for entry in sorted(load_products(PRODUCTS_JSON), key=lambda e: e.org_repo):
        result = results_by_org_repo.get(entry.org_repo)
        if result is None:
            status = "not yet run"
        else:
            status = result.get("readme_poc_status") or "not_set"
        ecosystem = (result or {}).get("ecosystem") or entry.ecosystem or "unknown"
        rows.append(
            {
                "org_repo": entry.org_repo,
                "ecosystem": ecosystem,
                "mode": entry.mode,
                "readme_poc_status": status,
            }
        )
    return rows, manifest_path, manifest


def _render_full_registry_status_table(
    rows: list[dict], manifest_path: Path | None, manifest: dict | None
) -> list[str]:
    lines = [
        "## Full-registry README POC status",
        "",
        "**Primary status measure (sprint charter Part B.2 Phase 5 Lane S).** Every "
        "`data/products.json` entry, counted live at generation time (never hard-coded), with "
        "its current `readme_poc_status` (RPOC-070 lifecycle vocabulary -- "
        "`src/readme_agent/state/lifecycle_schema.py::ReadmePocStatusV1`). Test counts, "
        "capability counts, plan closure, and three-pilot status are NOT the measure here; "
        "the requirement-status and Build Checklist sections below remain as supporting "
        "governance detail, not the headline.",
        "",
    ]
    if manifest_path is not None and manifest is not None:
        lines.append(
            f"Source manifest: `{manifest_path.relative_to(REPO_ROOT).as_posix()}` "
            f"(generated_at: {manifest.get('generated_at', 'unknown')})."
        )
    else:
        lines.append(
            "No `portfolio-proof-manifest.json` found under `plans/investigations/evidence/` -- "
            "every repo below is correctly reported `not yet run`."
        )
    lines += [
        "",
        "`not yet run` = absent from the source manifest entirely (e.g. the 3 Java pilots, "
        "proven through their own dedicated evidence path, or any registry entry newer than the "
        "last portfolio run). `not_set` = present in the manifest but the RPOC-070 lifecycle "
        "field has not been populated by a real run yet -- expected for most repos today, since "
        "that field is brand new.",
        "",
        "| Org/Repo | Ecosystem | Mode | README POC status |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['org_repo']} | {row['ecosystem']} | {row['mode']} | "
            f"{row['readme_poc_status']} |"
        )
    not_yet_run = sum(1 for r in rows if r["readme_poc_status"] == "not yet run")
    not_set = sum(1 for r in rows if r["readme_poc_status"] == "not_set")
    real_status = len(rows) - not_yet_run - not_set
    lines += [
        "",
        f"- {len(rows)} total registry entries (live count from `data/products.json`).",
        f"- {not_yet_run} not yet run (absent from the manifest).",
        f"- {not_set} present in the manifest but lifecycle status not yet set.",
        f"- {real_status} with a real RPOC-070 lifecycle status recorded.",
        "",
    ]
    return lines


def _current_project_status() -> dict:
    """Build the fail-closed current registry, lifecycle, and mission projection."""

    try:
        products_payload = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
        entries = load_products(PRODUCTS_JSON)
        raw_registry_hash = hashlib.sha256(PRODUCTS_JSON.read_bytes()).hexdigest()
        canonical_registry_hash = hashlib.sha256(
            PRODUCTS_JSON.read_text(encoding="utf-8")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .encode("utf-8")
        ).hexdigest()
        canonical_json_hash = products_registry_hash(products_payload)

        revision = RegistryRevisionV1.model_validate_json(
            REGISTRY_REVISION_PATH.read_text(encoding="utf-8")
        )
        revision_gate = evaluate_registry_revision(revision, products_payload)

        graph, loaded_graph_hash = load_mission_graph(MISSION_GRAPH_PATH)
        backend = default_state_backend()
        mission_record = backend.load(mission_state_key(graph.mission_authority.mission_id))
        if mission_record is None or mission_record.mission_execution is None:
            raise RuntimeError("durable mission state is unavailable")
        mission_state = mission_record.mission_execution
        scoreboard = derive_lifecycle_scoreboard(backend)

        lifecycle_records = backend.load_many([entry.org_repo for entry in entries])
        blocked: list[dict[str, str]] = []
        system_failures: list[dict[str, str]] = []
        for entry in entries:
            record = lifecycle_records.get(entry.org_repo)
            lifecycle = record.readme_poc_lifecycle if record is not None else None
            if lifecycle is None:
                continue
            status = lifecycle.status
            reason = lifecycle.history[-1].reason if lifecycle.history else "no transition reason"
            item = {"org_repo": entry.org_repo, "status": status, "reason": reason}
            if status in {"BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"}:
                blocked.append(item)
            if status == "SYSTEM_FAILURE":
                system_failures.append(item)

        return {
            "available": True,
            "denominator": len(entries),
            "registry_hashes": {
                "raw_sha256": raw_registry_hash,
                "canonical_text_sha256": canonical_registry_hash,
                "canonical_json_sha256": canonical_json_hash,
            },
            "registry_revision": revision.model_dump(mode="json"),
            "registry_gate": revision_gate.model_dump(mode="json"),
            "scoreboard": scoreboard.model_dump(mode="json"),
            "blocked": sorted(blocked, key=lambda item: item["org_repo"]),
            "system_failures": sorted(system_failures, key=lambda item: item["org_repo"]),
            "mission": {
                "state_version": mission_record.state_version,
                "active_task_id": mission_state.active_task_id,
                "active_goal_id": mission_state.active_goal_id,
                "claim_id": mission_state.claim_id,
                "claim_expires_at": mission_state.claim_expires_at,
                "durable_graph_sha256": mission_state.graph_sha256,
                "loaded_graph_sha256": loaded_graph_hash,
                "graph_drift": has_graph_drift(mission_state, loaded_graph_hash),
            },
        }
    except Exception as exc:  # fail-closed report; never fall back to historical completion
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _render_current_project_status(status: dict) -> list[str]:
    """Render current truth separately from historical lifecycle labels."""

    lines = ["## Current verified portfolio status", ""]
    if not status["available"]:
        return [
            *lines,
            "**CURRENT_RUNTIME_STATUS_UNAVAILABLE.** Historical manifests are not used "
            "as a fallback.",
            "",
            f"Reason: `{status['error']}`",
            "",
        ]

    scoreboard = status["scoreboard"]
    denominator = status["denominator"]
    lines += [
        "Current completion is derived from the runtime registry, durable repository "
        "lifecycle state, and current fact/acceptance contracts.",
        "",
        "| Boundary | Current contract-valid | Raw lifecycle label (non-closing) |",
        "|---|---:|---:|",
    ]
    for key, label in (
        ("facts_ready", "FACTS_READY"),
        ("candidate_generated", "CANDIDATE_GENERATED"),
        ("deterministic_validated", "DETERMINISTIC_VALIDATED"),
        ("agent_approved", "AGENT_APPROVED"),
        ("no_op_proven", "NO_OP_PROVEN"),
        ("human_accepted", "HUMAN_ACCEPTED"),
    ):
        lines.append(
            f"| {label} | {scoreboard[key]}/{denominator} | "
            f"{scoreboard['raw_' + key]}/{denominator} |"
        )

    hashes = status["registry_hashes"]
    revision = status["registry_revision"]
    gate = status["registry_gate"]
    lines += [
        "",
        "### Registry authority",
        "",
        f"- Denominator: **{denominator}**, loaded from `data/products.json`.",
        f"- Raw SHA-256: `{hashes['raw_sha256']}`.",
        f"- Canonical-text SHA-256: `{hashes['canonical_text_sha256']}`.",
        f"- Canonical-JSON SHA-256: `{hashes['canonical_json_sha256']}`.",
        f"- Registry revision: `{revision['revision_id']}`.",
        f"- Gate-A closure eligible: **{str(gate['eligible']).lower()}**; reasons: "
        + (", ".join(gate["reasons"]) or "none"),
        "",
        "### Excluded discoveries and intake",
        "",
    ]
    exclusions = revision.get("exclusions", [])
    if exclusions:
        for item in exclusions:
            lines.append(f"- `{json.dumps(item, sort_keys=True, ensure_ascii=False)}`")
    else:
        lines.append("- None recorded.")
    for item in revision.get("unexplained_observations", []):
        lines.append(f"- Unexplained observation: `{item}`.")
    for item in revision.get("pending_intake", []):
        lines.append(f"- Pending intake: `{item}`.")

    lines += ["", "### Blocked admitted repositories", ""]
    if status["blocked"]:
        for item in status["blocked"]:
            lines.append(f"- `{item['org_repo']}` — {item['status']}: {item['reason']}")
    else:
        lines.append("- None.")
    if status["system_failures"]:
        for item in status["system_failures"]:
            lines.append(f"- System failure: `{item['org_repo']}` — {item['reason']}")

    mission = status["mission"]
    lines += [
        "",
        "### Live mission",
        "",
        f"- Durable state version: `{mission['state_version']}`.",
        f"- Active task: `{mission['active_task_id'] or '-'}`.",
        f"- Active goal: `{mission['active_goal_id'] or '-'}`.",
        f"- Claim: `{mission['claim_id'] or '-'}`; expires `{mission['claim_expires_at'] or '-'}`.",
        f"- Loaded graph: `{mission['loaded_graph_sha256']}`.",
        f"- Durable graph: `{mission['durable_graph_sha256']}`; drift: "
        f"**{str(mission['graph_drift']).lower()}**.",
        "",
        "Historical portfolio manifests remain inspectable evidence but never supply "
        "headline current status.",
        "",
    ]
    return lines


def build_status_markdown(matrix: dict) -> str:
    status_counts = _requirement_status_counts()
    waves = _wave_checklist_state()
    latest_decision = _latest_decision_number()
    current_status = _current_project_status()

    lines = [
        "# Project status (generated -- do not hand-edit)",
        "",
        "Regenerate with `python plans/investigations/tools/traceability_matrix.py`. This replaces "
        "`plans/master.md`'s old hand-maintained Status section (Wave 9.3, 2026-07-22) -- see "
        "`plans/roadmap.md` for what's next and `logs/` for the dated history.",
        "",
        f"**Latest Decision Ledger entry**: #{latest_decision}" if latest_decision else "",
        "",
    ]
    lines += _render_current_project_status(current_status)
    lines += [
        "## Requirement status counts (supporting detail -- see the Full-registry table above "
        "for the primary measure)",
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
