"""Regression tests for bounded subprocess-tree cleanup."""

import os
import subprocess
import sys
import time
from pathlib import Path

from readme_agent.gitsafety.process import run_bounded


def _process_exists(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_timeout_kills_python_descendant_tree(tmp_path: Path):
    pid_path = tmp_path / "descendant.pid"
    child_code = "import time; time.sleep(60)"
    parent_code = (
        "import pathlib,subprocess,sys,time;"
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
        f"pathlib.Path({str(pid_path)!r}).write_text(str(p.pid));"
        "time.sleep(60)"
    )

    result = run_bounded([sys.executable, "-c", parent_code], timeout=1)

    assert result.returncode == 124
    assert pid_path.exists()
    descendant_pid = int(pid_path.read_text(encoding="utf-8"))
    for _ in range(20):
        if not _process_exists(descendant_pid):
            break
        time.sleep(0.1)
    assert not _process_exists(descendant_pid)
