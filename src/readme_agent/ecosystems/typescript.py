"""JavaScript/TypeScript platform manifest parser: package.json. Adapted from
aspose.org's extraction/package_manifest.py (_parse_js_manifest), GOVERNANCE.md
rule 8.
"""

import json
from pathlib import Path


def parse_package_json(package_json_path: Path) -> dict[str, str]:
    data = json.loads(package_json_path.read_text(encoding="utf-8", errors="replace"))
    info: dict[str, str] = {}
    if data.get("name"):
        info["name"] = data["name"]
    if data.get("version"):
        info["version"] = data["version"]
    if data.get("license"):
        info["license"] = data["license"]
    engines_node = (data.get("engines") or {}).get("node")
    if engines_node:
        info["engines_node"] = engines_node
    return info


def parse(repo_root: Path) -> dict[str, str]:
    package_json_path = repo_root / "package.json"
    if not package_json_path.exists():
        return {}
    try:
        return parse_package_json(package_json_path)
    except (json.JSONDecodeError, OSError):
        return {}
