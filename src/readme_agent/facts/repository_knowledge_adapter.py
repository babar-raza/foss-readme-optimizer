"""Adapt deterministic scout output to the local imported-knowledge contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ADAPTER_SCHEMA_VERSION = "repository-knowledge-v2"
_REQUIRED_SCOUT_ARTIFACTS = frozenset(
    {
        "absent_evidence.json",
        "api_surface.json",
        "claims.json",
        "class_graph.json",
        "coverage_matrix.json",
        "formats.json",
        "install.md",
        "limitations.md",
        "model.yaml",
        "scout_report.json",
        "snippets/snippets_index.json",
        "scout-validation.json",
    }
)


def _claim_provenance(claim: dict) -> str:
    evidence = claim.get("evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            path = item.get("file")
            line = item.get("line")
            if isinstance(path, str) and path:
                return f"repository-scout:{path}" + (f":{line}" if line is not None else "")
    return "repository-scout"


def _content_addressed_claim_id(claim: dict) -> str:
    """Replace the upstream 24-bit suffix with a stable semantic content address."""

    upstream_id = str(claim["claim_id"])
    prefix, separator, _suffix = upstream_id.rpartition("-")
    if not separator or not prefix.startswith("CLM-"):
        prefix = "CLM-local"
    semantic = {
        key: value
        for key, value in claim.items()
        if key not in {"claim_id", "evidence", "provenance"}
    }
    encoded = json.dumps(
        semantic,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:16]}"


def _merge_duplicate_claims(claims: list[dict]) -> list[dict]:
    """Collapse semantic duplicates while retaining every distinct source citation."""

    merged: dict[str, dict] = {}
    order: list[str] = []
    for claim in claims:
        claim_id = str(claim["claim_id"])
        existing = merged.get(claim_id)
        if existing is None:
            merged[claim_id] = claim
            order.append(claim_id)
            continue

        comparable_existing = {
            key: value for key, value in existing.items() if key not in {"evidence", "provenance"}
        }
        comparable_claim = {
            key: value for key, value in claim.items() if key not in {"evidence", "provenance"}
        }
        if comparable_existing != comparable_claim:
            raise ValueError(f"scout claim id collision has conflicting semantics: {claim_id}")

        evidence_by_bytes: dict[str, dict] = {}
        for item in [*(existing.get("evidence") or []), *(claim.get("evidence") or [])]:
            if not isinstance(item, dict):
                raise ValueError(f"scout claim {claim_id} contains malformed evidence")
            key = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            evidence_by_bytes[key] = item
        existing["evidence"] = [evidence_by_bytes[key] for key in sorted(evidence_by_bytes)]
    return [merged[claim_id] for claim_id in order]


def adapt_scout_output(output: Path, *, extracted_at: str, generator_sha256: str) -> None:
    """Normalize one raw scout directory without granting its claims factual authority."""

    present = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    missing = sorted(_REQUIRED_SCOUT_ARTIFACTS - present)
    if missing:
        raise ValueError(f"scout output is missing required artifacts: {missing}")

    model_path = output / "model.yaml"
    model = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    if not isinstance(model, dict):
        raise ValueError("scout model.yaml must contain an object")
    model.update(
        {
            "extracted_at": extracted_at,
            "schema_version": 2,
            "generator_semver": ADAPTER_SCHEMA_VERSION,
            "generator_fingerprint": generator_sha256,
            "source": "repository_scout",
        }
    )
    model_path.write_text(
        yaml.safe_dump(model, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    claims_path = output / "claims.json"
    envelope = json.loads(claims_path.read_text(encoding="utf-8"))
    if not isinstance(envelope, dict) or not isinstance(envelope.get("claims"), list):
        raise ValueError("raw scout claims.json must contain an object with a claims list")
    declared_count = envelope.get("claim_count")
    if declared_count != len(envelope["claims"]):
        raise ValueError("raw scout claim_count does not match the number of emitted claim records")
    if not envelope["claims"]:
        raise ValueError("scout emitted zero source-derived claims")
    claims: list[dict] = []
    for raw_claim in envelope["claims"]:
        if not isinstance(raw_claim, dict):
            raise ValueError("raw scout claims.json contains a non-object claim")
        if not raw_claim.get("claim_id") or not raw_claim.get("kind") or not raw_claim.get("text"):
            raise ValueError("raw scout emitted a claim without id, kind, or text")
        claim = dict(raw_claim)
        claim["claim_source"] = str(claim.get("claim_source") or "repository_scout")
        claim["provenance"] = str(claim.get("provenance") or _claim_provenance(claim))
        claim["claim_id"] = _content_addressed_claim_id(claim)
        claims.append(claim)
    claims = _merge_duplicate_claims(claims)
    claims_path.write_text(
        json.dumps(claims, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
