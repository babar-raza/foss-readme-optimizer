"""Run-id generation, atomic writes, sha256 (CRLF-normalized) -- all adopted
verbatim from aspose.org's session_ledger.py / cleanroom_manifest.py patterns.

Every string is redacted before it touches disk (evidence/redaction.py).
"""

import difflib
import hashlib
import json
import os
import secrets
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent import env
from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.evidence.redaction import redact


def generate_run_id() -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    rand = secrets.token_hex(2)
    return f"{ts}-{rand}"


def sha256_file(path: Path) -> tuple[str, int]:
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    digest = hashlib.sha256(normalized).hexdigest()
    return digest, len(raw)


def _redacted(value: Any) -> Any:
    secrets_live = env.secret_values()
    if isinstance(value, str):
        return redact(value, secrets_live)
    if isinstance(value, dict):
        return {k: _redacted(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redacted(v) for v in value]
    return value


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _atomic_write_json(path: Path, data: Any) -> None:
    redacted = _redacted(_to_jsonable(data))
    _atomic_write_text(path, json.dumps(redacted, indent=2, ensure_ascii=False) + "\n")


def unified_diff(baseline_text: str, work_text: str, filename: str = "README.md") -> str:
    """difflib-based, deliberately not `git diff`: no git internals, blob
    SHAs, or local core.autocrlf baked into evidence; needs only two in-memory
    strings, no worktree state."""
    diff_lines = difflib.unified_diff(
        baseline_text.splitlines(keepends=True),
        work_text.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff_lines)


def write_evidence(
    evidence_dir: Path,
    *,
    run_id: str,
    org_repo: str,
    mode: str,
    status: str,
    facts: Any,
    facts_hash: str,
    llm_mode: str | None,
    llm_calls: list[str],
    llm_request: list[dict[str, str]] | None,
    llm_response: Any | None,
    baseline_readme: str,
    work_readme: str,
    rendered_spans: dict[str, str],
    validation_results: list[Any],
    push_block_detail: str | None,
) -> None:
    _atomic_write_json(evidence_dir / "facts.json", {"facts": facts, "facts_hash": facts_hash})

    if llm_request is not None:
        _atomic_write_json(evidence_dir / "llm_request.json", llm_request)
    if llm_response is not None:
        _atomic_write_json(evidence_dir / "llm_response.json", llm_response)

    if rendered_spans:
        block_text = "\n\n".join(rendered_spans.values())
        _atomic_write_text(evidence_dir / "block.md", _redacted(block_text))

    diff_text = unified_diff(baseline_readme, work_readme)
    _atomic_write_text(evidence_dir / "diff.patch", _redacted(diff_text))

    _atomic_write_json(
        evidence_dir / "validation_report.json",
        [_to_jsonable(r) for r in validation_results],
    )

    manifest = {
        "run_id": run_id,
        "org_repo": org_repo,
        "mode": mode,
        "llm_mode": llm_mode,
        # `LLM-015`: usage MUST be visible in evidence/report, not just minimized
        # (`NFR-012`) -- this is the tracked-usage forcing function.
        "llm_call_count": len(llm_calls),
        "llm_calls": llm_calls,
        "status": status,
        "facts_hash": facts_hash,
        "push_block_detail": push_block_detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _atomic_write_json(evidence_dir / "manifest.json", manifest)

    _write_sha256sums(evidence_dir)


def write_run_manifest_v2(evidence_dir: Path, manifest: RunManifestV2) -> None:
    """Wave 13.1 (`EVID-001`): the single, canonical `manifest.json` writer
    for `supervisor/loop.py::supervise_repo()`'s evidence bundle -- reuses
    this module's own redaction/atomic-write helpers, same as `write_
    evidence()` above does for `orchestrator.generate_repo()`'s bundle.
    Never a parallel writer: `_write_supervise_evidence()` calls this
    instead of constructing its own ad hoc dict."""
    _atomic_write_json(evidence_dir / "manifest.json", manifest)


def _write_sha256sums(evidence_dir: Path) -> None:
    lines = []
    for path in sorted(evidence_dir.iterdir()):
        if path.is_file() and path.name != "sha256sums.txt":
            digest, _size = sha256_file(path)
            lines.append(f"{digest}  {path.name}")
    _atomic_write_text(evidence_dir / "sha256sums.txt", "\n".join(lines) + "\n")
