# Reproduction notes

These notes reproduce the audit without modifying any repository. Network-derived states are pinned by commit SHA. Use a disposable directory for clones and do not substitute current READMEs for historical originals.

## Inputs and pins

- Optimizer audited state: `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`.
- Optimizer later observed state: `d71f38b6`. Commit `eaf5eef6` fixed five baseline failures (reported result: 4,207 passed, one skipped, one xfailed, zero failed) by excluding `template_sha256` from semantic plan hashes after output-equivalence verification and skipping a mutable Note artifact on hash mismatch. Subsequent changes were auto-push governance and do not touch the audited product-knowledge quality path.
- 3D/Python: current `ee05c1ba9153ef5916b7a108406c794f2e464d01`; sealed pre-refresh `ab1a2267a0ba6302311d0c7c4ad01494974c7d76`; first refresh content `9fad4565`; refresh merge `62fb89f3ca76dc0afa9b2dfb983b9a1fa3f74fba`.
- Note/Python: current `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676`; pre-refresh/knowledge `6d97a522a9ed24708687911f1aabb76e2dea2da7`.
- Barcode/Python: current `06eca5c01e13ed6d59a640f1cf330c1c5a57d151`; pre-refresh/knowledge `53f2c3350b8171f2c8275e7b1a178f218695ac45`.
- Complete Aspose bundle archive: `upload/readme-refresh-complete-bundle-20260819-174412.zip`, SHA-256 `2d8eb6ae810d920b98136f3fa587b46d36b2e0c6b5250df109fa98c73e470465`.

The 3D pre-refresh bytes are not present in optimizer's finalized `ORIGINAL-README.md`; that file represents the post-refresh merge state at `62fb89f3…`. Fetch `README.md` from `ab1a2267…` when a true before/after replay is required.

## Clone the pinned sources

```bash
AUDIT_TMP=$(mktemp -d)
git clone --filter=blob:none https://github.com/babar-raza/foss-readme-optimizer.git "$AUDIT_TMP/optimizer"
git -C "$AUDIT_TMP/optimizer" checkout 6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51

git clone --filter=blob:none https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git "$AUDIT_TMP/3d"
git -C "$AUDIT_TMP/3d" checkout ee05c1ba9153ef5916b7a108406c794f2e464d01
git -C "$AUDIT_TMP/3d" fetch origin ab1a2267a0ba6302311d0c7c4ad01494974c7d76

git clone --filter=blob:none https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python.git "$AUDIT_TMP/note"
git -C "$AUDIT_TMP/note" checkout 41de2e8ab478b5aeff3663f7f7cbf83b19fdf676

git clone --filter=blob:none https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python.git "$AUDIT_TMP/barcode"
git -C "$AUDIT_TMP/barcode" checkout 06eca5c01e13ed6d59a640f1cf330c1c5a57d151
```

Confirm default branches and pins:

```bash
git -C "$AUDIT_TMP/optimizer" rev-parse HEAD
git -C "$AUDIT_TMP/3d" rev-parse HEAD
git -C "$AUDIT_TMP/note" rev-parse HEAD
git -C "$AUDIT_TMP/barcode" rev-parse HEAD
git -C "$AUDIT_TMP/3d" show ab1a2267a0ba6302311d0c7c4ad01494974c7d76:README.md | sha256sum
```

## Revision and README lineage

For each merged directory, compare `model.yaml`, `index.json`, `knowledge_state.json`, and `upstream_baselines.json` with the checked-out source SHA. Relevant paths begin at:

```text
data/imported/knowledge/3d/python/merged/
data/imported/knowledge/note/python/merged/
data/imported/knowledge/barcode/python/merged/
```

Inspect source history without assuming the first parent is the pre-refresh input:

```bash
git -C "$AUDIT_TMP/3d" log --all --oneline -- README.md
git -C "$AUDIT_TMP/3d" diff --stat ab1a2267a0ba6302311d0c7c4ad01494974c7d76..ee05c1ba9153ef5916b7a108406c794f2e464d01
git -C "$AUDIT_TMP/note" diff --stat 6d97a522a9ed24708687911f1aabb76e2dea2da7..41de2e8ab478b5aeff3663f7f7cbf83b19fdf676
git -C "$AUDIT_TMP/barcode" diff --stat 53f2c3350b8171f2c8275e7b1a178f218695ac45..06eca5c01e13ed6d59a640f1cf330c1c5a57d151
```

Normalize CRLF to LF before comparing bundle/optimizer README and snippet bytes. Do not normalize content beyond line endings and the optimizer's explicit snippet authorization header.

## Selector defect

Inspect the causal functions and their test:

```bash
rg -n 'def (_file_evidence_corroboration|_claim_eligibility|select_knowledge_claims)' \
  "$AUDIT_TMP/optimizer/src/readme_agent/facts/aspose_knowledge_selection.py"
rg -n 'file_evidence_corroborates_non_license_claims' \
  "$AUDIT_TMP/optimizer/tests/unit/test_aspose_knowledge_selection.py"
```

At the audited pin, `_file_evidence_corroboration` checks whether a normalized evidence path resolves to an existing repository file. It does not read the cited line/excerpt or compare the proposition with method behavior. The unit test creates a real file containing only a placeholder comment and expects the unrelated format claim to become verified.

Run `select_knowledge_claims` with each merged `claims.json`, checked-out repository root, current SHA, and the matching model SHA. Record considered/selected/rejected counts and selected texts. Expected counts are:

```text
3D:      3452 considered, 35 selected, 3417 rejected, 5 fact fields
Note:     333 considered,  6 selected,  327 rejected, 1 fact field
Barcode:  375 considered, 13 selected,  362 rejected, 3 fact fields
```

The minimum semantic assertions are:

- reject a positive `NurbsSurface.to_mesh` claim because `aspose/threed/entities/NurbsSurface.py` raises `NotImplementedError`;
- keep “COLLADA not exportable through public `Scene.save`” while separately recording that the internal `ColladaExporter.export` has an implementation;
- never simultaneously select Barcode PDF export and `PdfRenderer.render`/`Barcode.to_pdf` not-implemented limitations.

## 3D COLLADA public-path trace

Static path:

```text
Scene.save
  -> FileFormat.get_format_by_extension('.dae') -> ColladaFormat
  -> IOService.create_exporter
  -> registered exporters in OBJ, STL, glTF, 3MF, FBX, COLLADA order
  -> FbxExporter inherits Exporter.supports_format -> NotImplementedError
  -> ColladaExporter is not reached
```

There is a second public-options mismatch: `aspose.threed.formats.__init__` exports the legacy `formats/ColladaSaveOptions.py`, which is not derived from `SaveOptions`; the implemented plugin uses `formats/collada/ColladaSaveOptions.py`.

Reproduce with a bounded in-memory/temporary-file probe from the 3D checkout:

```bash
python - <<'PY'
import io, os, sys, tempfile
sys.path.insert(0, '.')
from aspose.threed import Scene
from aspose.threed.formats import ColladaSaveOptions

scene = Scene()
try:
    scene.save(io.BytesIO(), ColladaSaveOptions())
except Exception as exc:
    print('public options path:', type(exc).__name__, str(exc))

fd, path = tempfile.mkstemp(suffix='.dae')
os.close(fd)
try:
    scene.save(path)
except Exception as exc:
    print('public extension path:', type(exc).__name__, str(exc))
finally:
    os.unlink(path)
PY
```

Expected at `ee05c1b…`: options path `AttributeError`; extension path `NotImplementedError`. The direct internal exporter tests are independently runnable:

```bash
python -m unittest tests.test_collada_exporter
```

The audit run passed all five of those tests. They prove internal implementation, not public reachability.

## Deterministic source comparisons

For API entries, parse current Python source AST and compare `(name, relative file, line, kind)`. Separately count top-level definitions and nested/local definitions; tuple resolution alone does not establish public visibility.

For limitations, count concrete method bodies containing `raise NotImplementedError`, excluding abstract-interface declarations when reporting usable limitations. Compare with `limitations.md` table rows.

For evidence closure:

1. resolve each evidence `file` under the repository root;
2. reject traversal/absent files;
3. check line and excerpt against the pinned file;
4. bind README excerpts to the exact README revision/content hash;
5. compare claim polarity with the cited implementation.

For snippets, use `compile(snippet, '<snippet>', 'exec')` only as a syntax check. Then verify the indexed source function exists. Treat unresolved `self`, fixtures, imports, and surrounding setup as non-standalone until adapted and executed.

## Drift blind spot

```bash
rg -n 'def _compare_bundle|bundle_manifest' \
  "$AUDIT_TMP/optimizer/scripts/data-refresh/detect_aspose_upstream_drift.py"
find "$AUDIT_TMP/optimizer/data/imported/knowledge" -path '*/merged/model.yaml' -print | sort
find "$AUDIT_TMP/optimizer/data/imported/knowledge" -path '*/merged/bundle_manifest.json' -print | sort
```

The detector enumerates only `bundle_manifest.json`. Note/Python and Barcode/Python have `model.yaml` but no bundle manifest, so they are absent from its comparison set. The script compares imported bytes to the Aspose corpus; it does not compare target repository default-branch SHAs.

## Classification rules

- `exact`: exact current repository projection in the audited scope.
- `supported`: true but not exact/complete.
- `contradicted`: current repository evidence disproves the statement or disposition.
- `external-only`: governed by an external catalog/registry, not repository bytes.
- `stale`: tied to a non-current revision or superseded README.
- `partial`: mixed correct and materially incomplete scope.
- `missing`: required artifact/field absent.
- `unprovable`: available evidence cannot decide.

External package publication and URL availability were not re-queried. Preserve the imported registry observation date (`2026-08-01`) and classify present-day status as external-only unless separately verified.
