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
from readme_agent.evidence.manifest_v3 import RunManifestV3
from readme_agent.evidence.redaction import redact
from readme_agent.readme.document_hashing import sha256_hex


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


def write_redacted_json(path: Path, data: Any) -> None:
    """Atomically persist a redacted runtime evidence document.

    Portfolio aggregation is evidence too.  It therefore uses this public
    seam instead of inventing a second JSON writer that could expose an
    upstream token or an LLM response in a summary file.
    """
    _atomic_write_json(path, data)


def write_redacted_text(path: Path, text: str) -> None:
    """Atomically persist text evidence through the shared secret redactor."""
    _atomic_write_text(path, _redacted(text))


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


def write_run_manifest_v3(evidence_dir: Path, manifest: RunManifestV3) -> None:
    _atomic_write_json(evidence_dir / "manifest.json", manifest)


def refresh_sha256sums(evidence_dir: Path) -> None:
    _write_sha256sums(evidence_dir)


def write_readme_proposal_bundle(
    bundle_dir: Path,
    *,
    original_readme: str,
    candidate_readme: str,
    patch_text: str,
    product_facts_v2: dict,
    readme_assessment_v1: dict,
    readme_document_plan_v1: dict,
    claim_map_v1: dict,
    repository_presentation_plan_v1: dict,
    document_validation: dict,
) -> None:
    """RPOC-050/051: materialize the 8-file independent-verifier evidence
    bundle (`verification/readme_proposal_bundle.py::_REQUIRED_ARTIFACTS`)
    `specialists/readme_presentation.py`'s new `_review_node` needs, reusing
    this module's own atomic-write/redaction discipline (`_atomic_write_
    text`/`_atomic_write_json`) rather than a fourth hand-rolled file-writing
    convention -- `plans/investigations/tools/collect_local_readme_proposal_
    evidence.py`/`collect_portfolio_readme_proposal_evidence.py` are the
    standalone-tool writers this production call site replaces the need for.

    `artifact-sha256.json` is computed from the raw bytes actually written to
    disk, via `readme.document_hashing.sha256_hex` -- deliberately NOT this
    module's own CRLF-normalizing `sha256_file()` above, which would produce
    checksums `verify_readme_proposal_bundle()` (itself built on the same
    plain, unnormalized `sha256_hex`) could never match."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(bundle_dir / "original-readme.md", original_readme)
    _atomic_write_text(bundle_dir / "candidate-readme.md", candidate_readme)
    _atomic_write_text(bundle_dir / "proposal.patch", patch_text)
    _atomic_write_json(bundle_dir / "product-facts-v2.json", product_facts_v2)
    _atomic_write_json(bundle_dir / "readme-assessment-v1.json", readme_assessment_v1)
    _atomic_write_json(bundle_dir / "readme-document-plan-v1.json", readme_document_plan_v1)
    _atomic_write_json(bundle_dir / "claim-map-v1.json", claim_map_v1)
    _atomic_write_json(
        bundle_dir / "repository-presentation-plan-v1.json", repository_presentation_plan_v1
    )
    _atomic_write_json(bundle_dir / "document-validation.json", document_validation)
    artifacts = {
        path.name: sha256_hex(path.read_bytes())
        for path in sorted(bundle_dir.iterdir())
        if path.is_file() and path.name != "artifact-sha256.json"
    }
    _atomic_write_json(bundle_dir / "artifact-sha256.json", artifacts)


def _write_sha256sums(evidence_dir: Path) -> None:
    lines = []
    for path in sorted(evidence_dir.rglob("*")):
        if path.is_file() and path.name != "sha256sums.txt":
            digest, _size = sha256_file(path)
            relative = path.relative_to(evidence_dir).as_posix()
            lines.append(f"{digest}  {relative}")
    _atomic_write_text(evidence_dir / "sha256sums.txt", "\n".join(lines) + "\n")
