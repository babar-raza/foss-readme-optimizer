"""Canonical hashing helpers for bounded README review packets."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def canonical_json(value: BaseModel) -> str:
    """Deterministic sorted-key JSON serialization shared by every model in this module."""

    return json.dumps(
        value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _packet_sha256(
    substantive_payload: Mapping[str, Any], *, algorithm_contract_version: str
) -> str:
    versioned = {
        **substantive_payload,
        "_algorithm_contract_version": algorithm_contract_version,
    }
    return _canonical_hash(versioned)


def _packet_id_slug(section_path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", section_path.casefold()).strip("-")
    return slug or "section"
