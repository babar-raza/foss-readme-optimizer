# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: production-like workflow reproduction
"""Run the production workflow under act after one asserted parser-only compatibility edit."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "readme-agent-production.yml"
QUEUE_LINE = "      queue: max\n"
EXPECTED_QUEUE_OCCURRENCES = 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument(
        "--repository",
        default="aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    )
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    original = WORKFLOW_PATH.read_text(encoding="utf-8")
    queue_occurrences = original.count(QUEUE_LINE)
    if queue_occurrences != EXPECTED_QUEUE_OCCURRENCES:
        raise RuntimeError(
            f"expected {EXPECTED_QUEUE_OCCURRENCES} production concurrency queue lines, "
            f"found {queue_occurrences}"
        )
    compatible = original.replace(QUEUE_LINE, "")

    with tempfile.TemporaryDirectory(prefix="readme-agent-act-wave2-") as scratch:
        scratch_path = Path(scratch)
        workflow_copy = scratch_path / "readme-agent-production-act-compatible.yml"
        event_path = scratch_path / "workflow-dispatch-event.json"
        workflow_copy.write_text(compatible, encoding="utf-8", newline="\n")
        event_path.write_text(
            json.dumps({"inputs": {"repository": args.repository}}),
            encoding="utf-8",
        )
        command = [
            "act",
            "workflow_dispatch",
            "-W",
            str(workflow_copy),
            "-e",
            str(event_path),
            "-j",
            "plan",
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    (evidence_dir / "act-plan-job-output.log").write_text(
        completed.stdout,
        encoding="utf-8",
        newline="\n",
    )
    transform = {
        "source_workflow": str(WORKFLOW_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "act_compatible_sha256": hashlib.sha256(compatible.encode("utf-8")).hexdigest(),
        "only_removed_line": QUEUE_LINE.strip(),
        "removed_occurrences": queue_occurrences,
        "reason": (
            "GitHub supports concurrency.queue=max; local act 0.2.89 rejects that newer "
            "schema key before job execution."
        ),
        "repository_scope": args.repository,
        "command": command,
        "return_code": completed.returncode,
    }
    (evidence_dir / "act-queue-compatibility-transform.json").write_text(
        json.dumps(transform, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(completed.stdout)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
