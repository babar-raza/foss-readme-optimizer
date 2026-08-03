"""Build bounded reusable indexes for exact public-API claim matching."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ApiCoordinateIndexV1:
    classes_by_name: dict[str, dict]
    all_member_names: frozenset[str]
    modules_by_export: dict[str, tuple[dict, ...]]


_CACHE_MAX_SIZE = 8
_CACHE: OrderedDict[int, tuple[object, ApiCoordinateIndexV1]] = OrderedDict()
_CACHE_LOCK = Lock()


def _build(value: dict) -> ApiCoordinateIndexV1:
    raw_classes = value.get("classes")
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
    raw_modules = value.get("modules")
    modules = raw_modules if isinstance(raw_modules, list) else []
    by_export: dict[str, list[dict]] = {}
    for module in modules:
        if not isinstance(module, dict) or not isinstance(module.get("exports"), list):
            continue
        for export in module["exports"]:
            if isinstance(export, str):
                by_export.setdefault(export, []).append(module)
    return ApiCoordinateIndexV1(
        classes_by_name=classes_by_name,
        all_member_names=all_member_names,
        modules_by_export={name: tuple(items) for name, items in by_export.items()},
    )


def api_coordinate_index(value: dict) -> ApiCoordinateIndexV1:
    """Return a bounded identity-checked index without hashing a large fact per claim."""

    key = id(value)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None and cached[0] is value:
            _CACHE.move_to_end(key)
            return cached[1]
    compiled = _build(value)
    with _CACHE_LOCK:
        _CACHE[key] = (value, compiled)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_SIZE:
            _CACHE.popitem(last=False)
    return compiled
