"""Validate product-truth proposal and prompt provenance."""

from __future__ import annotations

import json
from pathlib import Path


def load_product_truth_json_object(path: Path, label: str) -> dict:
    """Load one required JSON object from the product-truth evidence set."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid product-truth {label}: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"product-truth {label} must be an object: {path}")
    return value


def load_coherent_product_truth_proposal(bundle_dir: Path, manifest: dict) -> dict | None:
    """Validate the closed resolution/prompt/proposal provenance contract."""

    resolution_source = manifest.get("resolution_source")
    prompt_hash = manifest.get("prompt_hash")
    proposal_path = bundle_dir / "facts" / "proposed-product-truth.json"
    if resolution_source == "repository_and_policy":
        if proposal_path.exists() or prompt_hash is not None:
            raise RuntimeError(
                "repository-derived product truth cannot retain agent proposal provenance"
            )
        return None
    if resolution_source == "agent_draft":
        if not proposal_path.is_file():
            raise RuntimeError("agent-drafted product truth requires a proposal artifact")
        if not isinstance(prompt_hash, str) or not prompt_hash:
            raise RuntimeError("agent-drafted product truth requires drafting prompt provenance")
        return load_product_truth_json_object(proposal_path, "proposed product truth")
    raise RuntimeError(f"unknown product-truth resolution source {resolution_source!r}")
