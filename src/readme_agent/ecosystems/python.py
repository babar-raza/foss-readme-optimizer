"""Python manifest metadata parser for pyproject, setup.cfg, and setup.py.

Adapted from aspose.org's extraction/package_manifest.py
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

import ast
import re
import tomllib
from configparser import ConfigParser
from pathlib import Path


def _literal_assignment(path: Path, name: str) -> str | None:
    """Read one module-level string assignment without importing repository code."""

    try:
        tree = ast.parse(
            path.read_text(encoding="utf-8-sig", errors="replace"),
            filename=str(path),
        )
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is None:
            continue
        try:
            literal = ast.literal_eval(value)
        except (TypeError, ValueError):
            return None
        return literal if isinstance(literal, str) and literal.strip() else None
    return None


def _dynamic_setuptools_version(pyproject_path: Path, data: dict) -> str | None:
    """Resolve a PEP 621 setuptools ``version.attr`` from static source only."""

    project = data.get("project", {})
    if "version" not in project.get("dynamic", []):
        return None
    setuptools_cfg = data.get("tool", {}).get("setuptools", {})
    version_cfg = setuptools_cfg.get("dynamic", {}).get("version", {})
    attr = version_cfg.get("attr") if isinstance(version_cfg, dict) else None
    if not isinstance(attr, str) or "." not in attr:
        return None
    module_name, attribute_name = attr.rsplit(".", 1)
    if not module_name or not attribute_name.isidentifier():
        return None

    package_dirs = setuptools_cfg.get("package-dir", {})
    source_root = ""
    if isinstance(package_dirs, dict):
        configured = package_dirs.get("")
        if isinstance(configured, str):
            source_root = configured
    module_root = pyproject_path.parent / source_root
    module_path = module_root.joinpath(*module_name.split("."))
    candidates = [module_path.with_suffix(".py"), module_path / "__init__.py"]
    return next(
        (
            version
            for candidate in candidates
            if (version := _literal_assignment(candidate, attribute_name)) is not None
        ),
        None,
    )


def parse_pyproject(pyproject_path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8", errors="replace"))
    project = data.get("project", {})
    if project.get("name"):
        info["name"] = project["name"]
    if project.get("version"):
        info["version"] = project["version"]
    elif dynamic_version := _dynamic_setuptools_version(pyproject_path, data):
        info["version"] = dynamic_version

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


def parse_setup_cfg(setup_cfg_path: Path) -> dict[str, str]:
    parser = ConfigParser()
    parser.read(setup_cfg_path, encoding="utf-8")
    info: dict[str, str] = {}
    if parser.has_section("metadata"):
        for source, target in (("name", "name"), ("version", "version"), ("license", "license")):
            value = parser.get("metadata", source, fallback="").strip()
            if value:
                info[target] = value
    if parser.has_section("options"):
        requires_python = parser.get("options", "python_requires", fallback="").strip()
        if requires_python:
            info["requires_python"] = requires_python
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
        setup_cfg_path = repo_root / "setup.cfg"
        if setup_cfg_path.exists():
            info.update(parse_setup_cfg(setup_cfg_path))

    if not info.get("name"):
        setup_py_path = repo_root / "setup.py"
        if setup_py_path.exists():
            info.update(parse_setup_py(setup_py_path))

    return info
