#!/usr/bin/env python
"""Make the external-fact-block snapshot fixture platform-portable.

`RepositorySnapshotV1` validates `snapshot_root` with `Path(...).is_absolute()`. The
fixture hardcodes "C:/tmp/widget", which is absolute on Windows and NOT absolute under
PurePosixPath -- so on Linux the model raises "snapshot_root must be absolute" and five
tests in this file fail. That has kept CI red on `main` continuously, including at this
sprint's baseline and well before it, while the same suite is green on Windows.

`tests/unit/test_curated_readme_evidence.py:1807` already established the idiom for
exactly this (`"C:/fake" if os.name == "nt" else "/fake"`); this fixture simply never
used it. Reusing the existing pattern rather than inventing a new one.
"""

from __future__ import annotations

import pathlib
import sys

P = pathlib.Path("tests/unit/test_external_fact_block_adapters.py")

OLD = '        snapshot_root="C:/tmp/widget",'
NEW = (
    "        # `RepositorySnapshotV1` requires an absolute `snapshot_root`, and a bare\n"
    '        # "C:/..." is absolute only on Windows -- under PurePosixPath it is not, so\n'
    "        # this fixture failed five tests on the Linux CI runners while passing\n"
    "        # locally. Same idiom as test_curated_readme_evidence.py's own snapshot root.\n"
    '        snapshot_root="C:/tmp/widget" if os.name == "nt" else "/tmp/widget",'
)

OLD_IMPORT = "from __future__ import annotations\n"
NEW_IMPORT = "from __future__ import annotations\n\nimport os\n"


def main() -> int:
    s = P.read_text(encoding="utf-8")
    if OLD not in s:
        print("ANCHOR MISS: snapshot_root line")
        return 1
    s = s.replace(OLD, NEW, 1)
    if "\nimport os\n" not in s:
        s = s.replace(OLD_IMPORT, NEW_IMPORT, 1)
    P.write_text(s, encoding="utf-8")
    print("snapshot fixture made platform-portable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
