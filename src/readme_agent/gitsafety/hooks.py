"""Pre-push hook installer -- the second of two independent push-blocking controls.

Belt-and-suspenders alongside neuter.py: even if the neutered remote URL were
ever restored by mistake, this hook still hard-blocks any push attempt.
"""

import os
import stat
from pathlib import Path

BLOCK_MARKER = "READMEAGENT_PUSH_BLOCKED"

HOOK_SCRIPT = f"""#!/bin/sh
echo "readme-agent: push blocked by design ({BLOCK_MARKER})" >&2
echo "this is a disposable local clone -- pushes are never permitted" >&2
exit 1
"""


def install_pre_push_hook(repo_path: Path) -> Path:
    hook_path = repo_path / ".git" / "hooks" / "pre-push"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8", newline="\n")
    try:
        current = os.stat(hook_path).st_mode
        os.chmod(hook_path, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        # NTFS has no meaningful executable bit; Git for Windows invokes hooks
        # via its bundled shell based on the shebang regardless. Recorded, not
        # treated as fatal -- see verify.py's explicit note on this.
        pass
    return hook_path
