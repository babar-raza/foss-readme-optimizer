"""Fail official checks when the active prompt inventory does not reconcile."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from readme_agent.llm.prompt_hygiene import audit_prompt_hygiene  # noqa: E402


def main() -> int:
    report = audit_prompt_hygiene(repo_root=REPO_ROOT)
    if "--json" in sys.argv:
        print(json.dumps(report.model_dump(mode="json"), indent=2))
    if report.clean:
        print(f"Prompt hygiene clean: {len(report.entries)} active prompt(s)")
        return 0
    for error in report.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
