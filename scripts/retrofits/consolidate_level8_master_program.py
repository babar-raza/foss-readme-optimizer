"""Apply the approved Level-8 master-section consolidation without losing candidate history."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER = REPO_ROOT / "plans" / "master.md"
CONTROL = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-master-consolidation-sections.md"
)
EXPECTED_CANDIDATE_SHA256 = "84319379254cc5db1954d78014216f4a0158b5a161fc012713c52e36ba4a2430"

SECTION_BOUNDS = {
    "MISSION": ("## Mission", "## Status"),
    "STATUS": ("## Status", "## Decision Ledger"),
    "ARCHITECTURE": ("## Architecture", "## Registry & Policy Config"),
    "BUILD-CHECKLIST": ("## Build Checklist", "## Verification Checklist"),
    "VERIFICATION-CHECKLIST": ("## Verification Checklist", "## Changelog"),
}

DECISION_BOUNDS = {
    "DECISION-26-AMENDMENT": ("26.", "27."),
    "DECISION-32-AMENDMENT": ("32.", "33."),
    "DECISION-33-AMENDMENT": ("33.", "34."),
    "DECISION-37-AMENDMENT": ("37.", "38."),
}


def _extract(control: str, name: str) -> str:
    start = f"<!-- BEGIN:{name} -->\n"
    end = f"\n<!-- END:{name} -->"
    if control.count(start) != 1 or control.count(end) != 1:
        raise SystemExit(f"control artifact must contain exactly one {name} block")
    return control.split(start, 1)[1].split(end, 1)[0].rstrip() + "\n"


def _replace_section(text: str, start_heading: str, end_heading: str, replacement: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start + len(start_heading))
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def _append_to_decision(text: str, start_id: str, end_id: str, addition: str) -> str:
    start_match = re.search(rf"(?m)^{re.escape(start_id)} ", text)
    end_match = re.search(rf"(?m)^{re.escape(end_id)} ", text)
    if start_match is None or end_match is None or end_match.start() <= start_match.start():
        raise SystemExit(f"cannot find ordered decision bounds {start_id}..{end_id}")
    before = text[: end_match.start()].rstrip()
    return before + "\n\n" + addition.rstrip() + "\n\n" + text[end_match.start() :]


def main() -> int:
    original_bytes = MASTER.read_bytes()
    actual_sha256 = hashlib.sha256(original_bytes).hexdigest()
    if actual_sha256 != EXPECTED_CANDIDATE_SHA256:
        raise SystemExit(
            "master candidate changed since its preservation audit: "
            f"expected {EXPECTED_CANDIDATE_SHA256}, got {actual_sha256}"
        )

    text = original_bytes.decode("utf-8")
    control = CONTROL.read_text(encoding="utf-8")

    for name, (start_heading, end_heading) in SECTION_BOUNDS.items():
        text = _replace_section(text, start_heading, end_heading, _extract(control, name))

    for name, (start_id, end_id) in DECISION_BOUNDS.items():
        text = _append_to_decision(text, start_id, end_id, _extract(control, name))

    architecture_start = text.index("## Architecture")
    new_decisions = _extract(control, "NEW-DECISIONS").rstrip()
    text = (
        text[:architecture_start].rstrip()
        + "\n\n"
        + new_decisions
        + "\n\n"
        + text[architecture_start:]
    )

    MASTER.write_text(text, encoding="utf-8", newline="\n")
    print(f"Consolidated approved Level-8 sections in {MASTER.relative_to(REPO_ROOT)}")
    print("Preserved candidate decisions through #72; added decisions #73-#76")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
