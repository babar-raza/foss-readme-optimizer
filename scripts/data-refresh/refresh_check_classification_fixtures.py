#!/usr/bin/env python3
"""Deliberately refresh the committed check-classification fixtures
(`data/check_classification_fixtures/<repo_dir_name>/`) from a repository's
current local `runs/readme-poc/` candidate.

`classify_aspose_checks.py`'s empirical false-positive pass must be
reproducible from a clean checkout (Gate R4 of the 2026-08-19 knowledge-
pipeline course-correction review): it reads these committed fixtures, never
`runs/` directly. When one of the three validation repositories
(3D/barcode/cells-Python) produces a new accepted candidate worth validating
against, run this script for that repository to update its fixture, then
rerun `classify_aspose_checks.py` to regenerate
`data/aspose_check_classification.json` against the refreshed fixture.

Usage:

    .venv/Scripts/python scripts/data-refresh/refresh_check_classification_fixtures.py \\
        aspose-3d-foss__Aspose.3D-FOSS-for-Python ee05c1ba9153ef5916b7a108406c794f2e464d01
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / "runs" / "readme-poc"
FIXTURES_ROOT = REPO_ROOT / "data" / "check_classification_fixtures"


def refresh(repo_dir_name: str, revision: str) -> None:
    source = RUNS_ROOT / repo_dir_name / revision
    candidate_readme = source / "candidate" / "README.md"
    facts_path = source / "facts" / "product-facts.json"
    if not candidate_readme.is_file():
        raise FileNotFoundError(f"no candidate README at {candidate_readme}")

    dest = FIXTURES_ROOT / repo_dir_name
    (dest / "candidate").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate_readme, dest / "candidate" / "README.md")

    if facts_path.is_file():
        (dest / "facts").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(facts_path, dest / "facts" / "product-facts.json")

    print(f"refreshed {dest.relative_to(REPO_ROOT).as_posix()} from {repo_dir_name}/{revision}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_dir_name", help="e.g. aspose-3d-foss__Aspose.3D-FOSS-for-Python")
    parser.add_argument("revision", help="the runs/readme-poc/<repo_dir_name>/<revision> to copy")
    args = parser.parse_args()
    refresh(args.repo_dir_name, args.revision)


if __name__ == "__main__":
    main()
