"""Canonical hashing and JSON projection helpers for replay attestation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from readme_agent.evidence.writer import sha256_file
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    ALLOWED_DIFFERENCE_KEYS,
    HashModeV1,
)

_SCALAR_TYPES = (str, int, float, bool, type(None))
_MISSING = object()


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_contract_digest(contract: ReplayAttestationContractV1) -> str:
    # sort_keys=True canonicalizes JSON OBJECT key order but never touches ARRAY element order --
    # artifacts/identity_bindings/product_effects are declarations, not sequences, so their
    # declared order must not affect the digest (requirement 8, "stable output ordering/hash").
    payload = contract.model_dump(mode="json")
    payload["artifacts"] = sorted(payload["artifacts"], key=lambda item: item["artifact_id"])
    payload["identity_bindings"] = sorted(
        payload["identity_bindings"], key=lambda item: item["component"]
    )
    payload["product_effects"] = sorted(payload["product_effects"], key=lambda item: item["effect"])
    return canonical_json_sha256(payload)


def _mode_digest(path: Path, data: bytes, mode: HashModeV1, parsed: Any) -> str:
    if mode == "raw_sha256":
        return sha256_hex(data)
    if mode == "crlf_normalized_sha256":
        return sha256_file(path)[0]
    return canonical_json_sha256(parsed)


def _pointer_escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _resolve_pointer(document: Any, pointer: str) -> tuple[bool, Any]:
    if pointer == "":
        return True, document
    if not pointer.startswith("/"):
        return False, None
    node = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False, None
            node = node[token]
        elif isinstance(node, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                return False, None
            index = int(token)
            if index >= len(node):
                return False, None
            node = node[index]
        else:
            return False, None
    return True, node


def _project_semantic(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _project_semantic(sub)
            for key, sub in sorted(value.items())
            if not (key in ALLOWED_DIFFERENCE_KEYS and isinstance(sub, _SCALAR_TYPES))
        }
    if isinstance(value, list):
        return [_project_semantic(item) for item in value]
    return value


def _diff_allowed_pointers(first: Any, replay: Any, *, path: str = "") -> list[str]:
    observed: list[str] = []
    if isinstance(first, dict) and isinstance(replay, dict):
        for key in sorted(set(first) | set(replay)):
            child = f"{path}/{_pointer_escape(key)}"
            f_val = first.get(key, _MISSING)
            r_val = replay.get(key, _MISSING)
            if f_val == r_val:
                continue
            if (
                key in ALLOWED_DIFFERENCE_KEYS
                and (f_val is _MISSING or isinstance(f_val, _SCALAR_TYPES))
                and (r_val is _MISSING or isinstance(r_val, _SCALAR_TYPES))
            ):
                observed.append(child)
            elif f_val is not _MISSING and r_val is not _MISSING:
                observed.extend(_diff_allowed_pointers(f_val, r_val, path=child))
    elif isinstance(first, list) and isinstance(replay, list) and len(first) == len(replay):
        for index, (f_item, r_item) in enumerate(zip(first, replay, strict=True)):
            observed.extend(_diff_allowed_pointers(f_item, r_item, path=f"{path}/{index}"))
    return observed
