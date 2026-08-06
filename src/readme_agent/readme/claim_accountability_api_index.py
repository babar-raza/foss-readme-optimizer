"""Build bounded reusable indexes for exact public-API claim matching."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ApiCoordinateIndexV1:
    classes_by_name: dict[str, dict]
    all_member_names: frozenset[str]
    modules_by_export: dict[str, tuple[dict, ...]]
    modules_by_name: dict[str, dict]
    package_export_names: frozenset[str]
    coordinate_prefix: str


_CACHE_MAX_SIZE = 8
_CACHE: OrderedDict[int, tuple[object, tuple[object, object], ApiCoordinateIndexV1]] = OrderedDict()
_CACHE_LOCK = Lock()


def _empty(*, coordinate_prefix: str = "") -> ApiCoordinateIndexV1:
    return ApiCoordinateIndexV1({}, frozenset(), {}, {}, frozenset(), coordinate_prefix)


def _catalog_value(value: dict) -> tuple[dict, str] | None:
    envelope = value.get("coordinate_catalog")
    if envelope is None:
        return value, ""
    if (
        not isinstance(envelope, dict)
        or envelope.get("schema_version") != 1
        or envelope.get("public_api_source_sha256") != value.get("public_api_source_sha256")
        or not isinstance(envelope.get("content_sha256"), str)
    ):
        return None
    catalog = {key: item for key, item in envelope.items() if key != "content_sha256"}
    payload = json.dumps(
        catalog,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if hashlib.sha256(payload).hexdigest() != envelope["content_sha256"]:
        return None
    return catalog, "/coordinate_catalog"


def _build(value: dict) -> ApiCoordinateIndexV1:
    selected = _catalog_value(value)
    if selected is None:
        return _empty(coordinate_prefix="/coordinate_catalog")
    catalog, coordinate_prefix = selected
    raw_classes = catalog.get("classes")
    classes = raw_classes if isinstance(raw_classes, list) else []
    classes_by_name = {
        item["name"]: item
        for item in classes
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    all_member_names = frozenset(
        member["name"]
        for item in classes_by_name.values()
        if isinstance(item.get("members"), list)
        for member in item["members"]
        if isinstance(member, dict) and isinstance(member.get("name"), str)
    )
    raw_modules = catalog.get("modules")
    modules = raw_modules if isinstance(raw_modules, list) else []
    by_export: dict[str, list[dict]] = {}
    for module in modules:
        if not isinstance(module, dict) or not isinstance(module.get("exports"), list):
            continue
        for export in module["exports"]:
            if isinstance(export, str):
                by_export.setdefault(export, []).append(module)
    modules_by_name = {
        module["module"]: module
        for module in modules
        if isinstance(module, dict) and isinstance(module.get("module"), str)
    }
    package_export_names = frozenset(
        export
        for module in modules
        if isinstance(module, dict)
        and str(module.get("source_path") or "").replace("\\", "/").endswith("/__init__.py")
        and isinstance(module.get("exports"), list)
        for export in module["exports"]
        if isinstance(export, str)
    )
    return ApiCoordinateIndexV1(
        classes_by_name=classes_by_name,
        all_member_names=all_member_names,
        modules_by_export={name: tuple(items) for name, items in by_export.items()},
        modules_by_name=modules_by_name,
        package_export_names=package_export_names,
        coordinate_prefix=coordinate_prefix,
    )


def api_coordinate_index(value: dict) -> ApiCoordinateIndexV1:
    """Return a bounded identity-checked index without hashing a large fact per claim."""

    key = id(value)
    catalog = value.get("coordinate_catalog")
    fingerprint = (
        catalog.get("content_sha256") if isinstance(catalog, dict) else None,
        value.get("public_api_source_sha256"),
    )
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None and cached[0] is value and cached[1] == fingerprint:
            _CACHE.move_to_end(key)
            return cached[2]
    compiled = _build(value)
    with _CACHE_LOCK:
        _CACHE[key] = (value, fingerprint, compiled)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_SIZE:
            _CACHE.popitem(last=False)
    return compiled
