"""PF04 recovery inventories must remain portable and tamper-evident."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from readme_agent.supervisor.proven_transaction_runner import pf04_recovery_proof


def test_recovery_inventory_accepts_windows_bom_and_rejects_tampering(tmp_path: Path):
    evidence = tmp_path / "receipt.json"
    evidence.write_text('{"status":"current"}\n', encoding="utf-8")
    inventory = [
        {
            "path": str(evidence.resolve()),
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        }
    ]
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8-sig")

    assert (
        pf04_recovery_proof._verify_inventory(tmp_path)
        == hashlib.sha256(inventory_path.read_bytes()).hexdigest()
    )
    evidence.write_text('{"status":"changed"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="inventory mismatch"):
        pf04_recovery_proof._verify_inventory(tmp_path)
