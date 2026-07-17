"""File inventory scan: README / LICENSE / manifest presence, no LLM.

Case-insensitive matching is deliberate, not incidental: the real registry
repos disagree on casing (LICENSE in 3D/PDF, License in Cells) and NTFS's
case-insensitive filesystem would silently mask a bug here that surfaces the
moment this runs on a Linux CI runner.
"""

from dataclasses import dataclass
from pathlib import Path

_README_NAMES = {"readme.md", "readme", "readme.rst", "readme.txt"}
_LICENSE_NAMES = {"license", "license.txt", "license.md", "copying", "license.rst"}


@dataclass
class FileInventory:
    readme_path: Path | None
    license_path: Path | None
    pom_path: Path | None


def _find_case_insensitive(directory: Path, candidate_names: set[str]) -> Path | None:
    if not directory.is_dir():
        return None
    for entry in directory.iterdir():
        if entry.is_file() and entry.name.lower() in candidate_names:
            return entry
    return None


def scan(repo_path: Path) -> FileInventory:
    readme_path = _find_case_insensitive(repo_path, _README_NAMES)

    license_path = _find_case_insensitive(repo_path, _LICENSE_NAMES)
    if license_path is None:
        # e.g. aspose-cells-foss's real repos: License/LICENSE.txt
        for entry in repo_path.iterdir() if repo_path.is_dir() else []:
            if entry.is_dir() and entry.name.lower() == "license":
                license_path = _find_case_insensitive(entry, _LICENSE_NAMES)
                if license_path:
                    break

    candidate_pom = repo_path / "pom.xml"
    pom_path = candidate_pom if candidate_pom.exists() else None

    return FileInventory(readme_path=readme_path, license_path=license_path, pom_path=pom_path)
