"""Prove the atomic writer survives a >MAX_PATH destination on Windows.

Bounded review writes `<repo>/<40-char revision>/review/bounded-packet-cache/
<64-hex>.json`, which crosses 260 characters for longer repository names and
failed with `FileNotFoundError` from `os.replace`. Kept per the no-throwaway-
scripts rule so the reproduction stays runnable.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from readme_agent.evidence.writer import _win_long_path, write_redacted_json

ROOT = Path("runs/readme-poc/_longpath_probe")


def main() -> int:
    deep = ROOT / "aspose-note-foss__Aspose.Note-FOSS-for-Python" / ("4" * 40)
    target = deep / "review" / "bounded-packet-cache" / (("a" * 64) + ".json")
    absolute = os.path.abspath(target)
    print(f"destination length: {len(absolute)}")
    write_redacted_json(target, {"ok": True})
    probe = _win_long_path(absolute) if os.name == "nt" else absolute
    print(f"written: {os.path.isfile(probe)}")
    shutil.rmtree(_win_long_path(ROOT) if os.name == "nt" else str(ROOT), ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
