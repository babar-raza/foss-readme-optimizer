"""Process-narration checks remain correct and bounded on large generated READMEs."""

from __future__ import annotations

import sys
from time import perf_counter

sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline")
sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/lib")
sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss")
import readme_refresh_checks  # noqa: E402


def test_process_narration_findings_keep_document_order_and_context() -> None:
    readme = (
        "# Product\n\nThe package was verified against a local checkout.\n\n"
        "The table below mirrors the reference structure.\n"
    )

    findings = readme_refresh_checks.check_process_narration_smells(readme)

    assert [finding["phrase"] for finding in findings] == [
        "was verified",
        "table below mirrors",
    ]
    assert all("context" in finding for finding in findings)


def test_process_narration_scan_is_bounded_for_large_api_table() -> None:
    table = "| Type | Description |\n| --- | --- |\n" + "".join(
        f"| ApiType{index} | Public member number {index}. |\n" for index in range(4_000)
    )

    started = perf_counter()
    findings = readme_refresh_checks.check_process_narration_smells(table)
    elapsed = perf_counter() - started

    assert findings == []
    assert elapsed < 5.0
