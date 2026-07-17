"""License facts from GitHub's API classification + LICENSE file content.
Must not crash on null -- confirmed real case: aspose-cells-foss's GitHub
license classifier reports null (non-standard License/LICENSE.txt path), but
the file itself states MIT. Both facts are real and complementary, not a
contradiction; the file-content fallback exists specifically for this case.
"""

import re
from dataclasses import dataclass
from pathlib import Path

_CLASSIFIERS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bmit license\b", re.IGNORECASE), "MIT"),
    (re.compile(r"\bapache license\b.*\bversion 2\.0\b", re.IGNORECASE | re.DOTALL), "Apache-2.0"),
    (
        re.compile(r"\bgnu general public license\b.*\bversion 3\b", re.IGNORECASE | re.DOTALL),
        "GPL-3.0",
    ),
    (re.compile(r"\bbsd 3-clause\b", re.IGNORECASE), "BSD-3-Clause"),
    (re.compile(r"\bbsd 2-clause\b", re.IGNORECASE), "BSD-2-Clause"),
    (re.compile(r"\bisc license\b", re.IGNORECASE), "ISC"),
    (re.compile(r"\bmozilla public license\b", re.IGNORECASE), "MPL-2.0"),
)


@dataclass
class LicenseState:
    detected: str | None
    source: str  # "github_api" | "file_content" | "undetected"


def classify_license_text(text: str) -> str | None:
    for pattern, spdx_id in _CLASSIFIERS:
        if pattern.search(text):
            return spdx_id
    return None


def detect_license(github_spdx_id: str | None, license_file_path: Path | None) -> LicenseState:
    if github_spdx_id and github_spdx_id.lower() != "noassertion":
        return LicenseState(detected=github_spdx_id, source="github_api")

    if license_file_path is not None and license_file_path.exists():
        text = license_file_path.read_text(encoding="utf-8", errors="replace")
        classified = classify_license_text(text)
        if classified:
            return LicenseState(detected=classified, source="file_content")

    return LicenseState(detected=None, source="undetected")
