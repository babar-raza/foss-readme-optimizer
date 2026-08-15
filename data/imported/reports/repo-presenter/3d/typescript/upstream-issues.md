# Upstream issues — Aspose.3D FOSS for TypeScript

Verified: 2026-08-02 against https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript

## Binary glTF (GLB) export crashes with RangeError
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `GltfExporter._writeGlb()` (`src/aspose/threed/formats/gltf/GltfExporter.ts:396-419`) sizes the output buffer using the binary payload's element count instead of byte length (4 bytes/float), so `Buffer.alloc()` is undersized once real geometry is written, throwing `RangeError: offset out of range`. Reproduced independently and via the repo's own test suite (`testSimpleTriangleBinary` in `tests/test_gltf_exporter.test.ts` fails identically).
- **Impact**: any real binary GLB export crashes.
- **Not fixable here because**: it's in the library's own exporter source. (The README now demonstrates non-binary glTF export instead, which works correctly.)

## glTF export does not round-trip node hierarchy correctly
- **Severity**: FUNCTIONAL-DEFECT
- **Evidence**: `GltfExporter.export()` (lines 106-112) pushes every node into the exported file's `scenes[0].nodes`, not just true roots. Re-importing a self-exported glTF duplicates non-root nodes as extra top-level children, shifting `childNodes` indices (confirmed: a material-bearing node ends up at `childNodes[1]` instead of `[0]` in a self-exported round trip). Import logic is correct against well-formed (non-self-exported) input — the defect is exporter-only.
- **Impact**: self-export-then-reimport workflows silently get the wrong node structure.
- **Not fixable here because**: it's in the library's exporter source, not the README.

## npm run lint fails unconditionally
- **Severity**: INFORMATIONAL
- **Evidence**: no `.eslintrc.*`/`eslint.config.js` is committed anywhere in the repo, so ESLint exits with "couldn't find a configuration file" regardless of platform.
- **Impact**: contributors following the documented lint command get an immediate failure unrelated to their code.
- **Not fixable here because**: the missing config file is the upstream repo's own.

## adm-zip required at runtime but declared only as a devDependency
- **Severity**: INFORMATIONAL
- **Evidence**: the 3MF importer/exporter requires `adm-zip` at runtime, but `package.json` lists it only under `devDependencies`.
- **Impact**: an external consumer installing the published package (once published) would be missing this dependency unless coincidentally already present.
- **Not fixable here because**: it's the upstream repo's own `package.json` dependency classification. No documented README example currently exercises the 3MF path, so this doesn't block anything shown in the README today.
