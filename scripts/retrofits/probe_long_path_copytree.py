"""Prove `_copy_evidence_directory` survives a >MAX_PATH destination on Windows.

`shutil.copytree` opens every entry through the raw Win32 API with no
long-path handling of its own, unlike `os.replace` (see
`evidence/writer.py::win_long_path`). Kept per the no-throwaway-scripts rule
so the reproduction stays runnable.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from readme_agent.evidence.writer import win_long_path
from readme_agent.supervisor.local_poc_superseded import _copy_evidence_directory

ROOT = Path("runs/readme-poc/_longpath_copytree_probe")


def main() -> int:
    source = ROOT / "source"
    (source / "assessment").mkdir(parents=True, exist_ok=True)
    (source / "assessment" / "current-readme-assessment.json").write_text("{}", encoding="utf-8")

    # Long enough on its own that any repo/revision prefix pushes the real
    # `superseded/<16-hex>/...` destination past 260 characters, matching the
    # shape that broke for real: `aspose-note-foss__Aspose.Note-FOSS-for-Python/
    # <40-char revision>/superseded/<16-hex>/assessment/current-readme-assessment.json`.
    destination = ROOT / ("x" * 60) / ("y" * 60) / ("z" * 60) / "superseded" / ("a" * 16)
    print(f"destination length: {len(os.path.abspath(destination))}")
    _copy_evidence_directory(source, destination, name="assessment")
    copied = destination / "assessment" / "current-readme-assessment.json"
    # `Path.is_file()` itself has no long-path handling on Windows, so checking
    # existence needs the same prefix the copy itself needed.
    probe = win_long_path(copied) if os.name == "nt" else str(copied)
    print(f"copied: {os.path.isfile(probe)}")
    shutil.rmtree(win_long_path(ROOT) if os.name == "nt" else str(ROOT), ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
