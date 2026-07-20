"""Python platform manifest parser: pyproject.toml primary, setup.py regex
fallback. Adapted from aspose.org's extraction/package_manifest.py
(_parse_python_manifest), GOVERNANCE.md rule 8 -- a real, in-production
reference tuned against the same Aspose FOSS corpus this project targets, not
written from scratch. This project targets Python 3.11+ only, so aspose.org's
own tomllib/tomli dual-path (for pre-3.11 Python) is dropped -- stdlib
tomllib unconditionally, matching pyproject.toml's own requires-python floor.

Known caveat, carried forward: `canonical_package` uses a namespace-package
heuristic (first dotted, non-wildcard entry naming the package) tuned for
Aspose's own `aspose.<family>_foss`-style package layout -- kept as-is,
intentionally Aspose-specific, not generalized to other namespace-package
conventions.

Hardened against a real crash found by the full-registry survey (Wave 3
follow-up, 2026-07-19): the ported logic assumed
`[tool.setuptools.packages.find].include = [...]` unconditionally, but a real
registry repo (`aspose-cells-foss/Aspose.Cells-FOSS-for-Python`) uses the
flatter `[tool.setuptools] packages = [...]` shape instead -- `packages` is a
list there, not a dict, and `.get("find", {})` on a list raised
`AttributeError`. Both real shapes are now checked.
"""

import re
import tomllib
from pathlib import Path


def parse_pyproject(pyproject_path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8", errors="replace"))
    project = data.get("project", {})
    if project.get("name"):
        info["name"] = project["name"]
    if project.get("version"):
        info["version"] = project["version"]

    license_value = project.get("license", "")
    if isinstance(license_value, dict):
        license_value = license_value.get("text", license_value.get("file", ""))
    if license_value:
        info["license"] = license_value

    if project.get("requires-python"):
        info["requires_python"] = project["requires-python"]

    # Namespace-package canonical import path. Two real setuptools config
    # shapes exist in this project's own registry (found via the full-
    # registry survey, not assumed): the nested
    # [tool.setuptools.packages.find].include = ["aspose.email_foss", ...]
    # aspose.org's original code assumed, and the flatter [tool.setuptools]
    # packages = ["aspose", "aspose.cells_foss", ...] a real repo actually
    # uses. Both checked; first dotted, non-wildcard entry wins. Aspose-
    # specific convenience, not a general namespace-package resolver.
    setuptools_cfg = data.get("tool", {}).get("setuptools", {})
    packages_cfg = setuptools_cfg.get("packages", [])
    if isinstance(packages_cfg, dict):
        candidates = packages_cfg.get("find", {}).get("include", [])
    elif isinstance(packages_cfg, list):
        candidates = packages_cfg
    else:
        candidates = []
    for candidate in candidates:
        if candidate and "." in candidate and not candidate.endswith(("*", ".*")):
            info["canonical_package"] = candidate
            break

    return info


def parse_setup_py(setup_py_path: Path) -> dict[str, str]:
    text = setup_py_path.read_text(encoding="utf-8", errors="replace")
    info: dict[str, str] = {}
    match = re.search(r'name\s*=\s*["\']([^"\']+)', text)
    if match:
        info["name"] = match.group(1)
    match = re.search(r'version\s*=\s*["\']([^"\']+)', text)
    if match:
        info["version"] = match.group(1)
    return info


def parse(repo_root: Path) -> dict[str, str]:
    """pyproject.toml is authoritative when present and yields a name;
    setup.py is only consulted when pyproject.toml is absent or incomplete
    (matches aspose.org's own `if not info.get("name")` fallback order)."""
    info: dict[str, str] = {}
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        info.update(parse_pyproject(pyproject_path))

    if not info.get("name"):
        setup_py_path = repo_root / "setup.py"
        if setup_py_path.exists():
            info.update(parse_setup_py(setup_py_path))

    return info
