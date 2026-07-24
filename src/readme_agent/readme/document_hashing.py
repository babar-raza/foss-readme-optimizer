"""SHA-256 helper shared across the README document pipeline modules.

Extracted verbatim from the former single-file ``document_renderer`` so the
structure, template, operation, and orchestration modules can share one hash
implementation instead of re-declaring it (`GOVERNANCE.md` "no monoliths").
"""

from __future__ import annotations

import hashlib


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
