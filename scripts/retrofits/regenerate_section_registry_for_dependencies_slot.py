"""Regenerate templates/readme/section-registry-v2.json from the live contract.

Run once after adding the "dependencies" TemplateSlot
(repository-presentation-v1.json template_version 1.19.0 -> 1.20.0) so the
committed T14 section registry stops hand-drifting from the live contract,
mirroring the same regeneration T5-R1 did for "api_method_index"
(commit 669a227a5).
"""

from __future__ import annotations

import json

from readme_agent.presentation.sections import (
    SECTION_REGISTRY_PATH,
    derive_section_registry_from_live_contract,
)


def main() -> None:
    registry = derive_section_registry_from_live_contract()
    payload = registry.model_dump(mode="json")
    SECTION_REGISTRY_PATH.write_text(
        json.dumps(payload, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(registry.entries)} entries to {SECTION_REGISTRY_PATH}")
    print(f"unmapped_section_checks: {list(registry.unmapped_section_checks)}")


if __name__ == "__main__":
    main()
