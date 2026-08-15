# Upstream issues — Aspose.3D FOSS for Python

Verified: 2026-08-02 against https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python

## Broken shadow-imports break LoadOptions/SaveOptions for OBJ/STL/glTF/Collada
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `aspose/threed/formats/__init__.py` imports the correct, properly-subclassed `Obj/Stl/Gltf/Collada` `*LoadOptions`/`*SaveOptions` from their real submodules, then re-imports and shadows them with broken top-level stub classes with no base class. `isinstance(options, LoadOptions/SaveOptions)` is `False` for all four as a result — `Scene.open()` silently discards user-supplied options, and `Scene.save()` crashes with `AttributeError`, when using the top-level-imported classes.
- **Impact**: anyone following the documented top-level import path (`from aspose.threed.formats import GltfSaveOptions`, etc.) hits silent no-ops or crashes.
- **Not fixable here because**: the shadowing lives in the installed package's own `__init__.py`. (The README works around it with submodule-qualified imports, which is a legitimate real fix for README purposes, but the underlying package defect remains.)

## GltfFormat.create_save_options() omits file_format needed for stream-based save
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: unlike `StlFormat`'s equivalent, `GltfFormat.create_save_options()` doesn't populate `options.file_format`, so `Scene.save(stream, options)` (no filename) fails unless `file_format` is set explicitly.
- **Impact**: stream-based glTF export fails using the otherwise-documented pattern.
- **Not fixable here because**: it's in the installed package's format-options factory.

## aspose/threed/formats/collada/ has no __init__.py
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `from aspose.threed.formats.collada import ColladaLoadOptions` imports a module object, not the class, because the package directory has no `__init__.py`.
- **Impact**: the natural import path for Collada options doesn't work as expected.
- **Not fixable here because**: it's a missing file in the installed package.

## Collada export unreachable via the public Scene.save() API
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `FbxExporter` never overrides `Exporter.supports_format()` and is registered before `ColladaPlugin` in the internal dispatcher, so `IOService.create_exporter()` raises `NotImplementedError` before ever reaching the real Collada exporter — even though a working Collada exporter implementation exists in the source tree.
- **Impact**: Collada export is unusable through the documented public API in this version.
- **Not fixable here because**: it's in the installed package's exporter-registration order/dispatch logic.
