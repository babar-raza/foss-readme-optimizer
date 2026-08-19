# Read-only reproduction

All commands below are read-only. Run from:

```bash
cd /workspace/scratch/22cd18c3f75c/work/github-foss-readme-optimizer
```

The local worktree was divergent during the audit, so runtime source was always read with `git show <pin>:<path>`, never from unchecked working-tree files.

## 1. Pin optimizer `main`

```bash
git ls-remote https://github.com/babar-raza/foss-readme-optimizer.git refs/heads/main
```

Initial result used by this audit:

```text
d71f38b6a050b5282f0ada314f9ee4de35950426 refs/heads/main
```

Latest result observed before sealing:

```text
91d9479b1e1fa12a9af41c1692b6f8f421db5f76 refs/heads/main
```

Relevant intervening runtime fix:

```text
05ef1e532ae34bea07fefe951543a43f41ca55c4 fix(presentation): make SEO knowledge shape capability titles safely
```

## 2. Derive 103 versus 89 check inventory by AST

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss/readme_refresh_checks.py > /tmp/optimizer-readme-refresh-checks.py

python - <<'PY'
import ast
from pathlib import Path

canonical = Path('/workspace/scratch/22cd18c3f75c/work/readme-refresh-complete-bundle-20260819-174412/files/scripts/pipeline/commands/foss/readme_refresh_checks.py')
optimizer = Path('/tmp/optimizer-readme-refresh-checks.py')

def names(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('check_')}

c = names(canonical)
o = names(optimizer)
print('canonical', len(c))
print('optimizer', len(o))
print('missing', len(c - o))
print('\n'.join(sorted(c - o)))
print('optimizer_only', sorted(o - c))
PY
```

Expected counts: canonical 103, optimizer 89, missing 14, optimizer-only empty. The exact 14 names are in D12 of `DEFECT_GATE_MATRIX.json`.

## 3. Derive classification counts; do not trust prose

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:data/aspose_check_classification.json > /tmp/aspose-check-classification.json

python - <<'PY'
import collections, json
rows = json.load(open('/tmp/aspose-check-classification.json', encoding='utf-8'))
if isinstance(rows, dict):
    rows = rows.get('checks', rows.get('entries', []))
print('rows', len(rows))
print('classification', dict(sorted(collections.Counter(r['classification'] for r in rows).items())))
print('blocking', dict(sorted(collections.Counter(bool(r.get('blocking')) for r in rows).items())))
PY
```

Expected: 89 rows; 11 blocking; classifications 11 `applicable_reusable`, 61 `applicable_after_adaptation`, 17 `diagnostic_heuristic`.

## 4. Prove blocking skip/error fails open

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/validation/aspose_checks_bridge.py | nl -ba | sed -n '130,185p'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/readme/document_validation.py | nl -ba | sed -n '550,585p'
```

Observe:

- missing parameters append only to `checks_skipped`;
- exceptions and non-list results append only to `checks_errored`;
- `valid` is based only on critical normalized findings;
- document errors receive only `blocking_aspose_check_findings(result)`, not blocking skip/error obligations.

## 5. Prove existence-only knowledge corroboration and aggregate promotion

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/facts/aspose_knowledge_selection.py | nl -ba | sed -n '220,285p'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/facts/aspose_knowledge_selection.py | nl -ba | sed -n '535,585p'
```

Observe `_file_evidence_corroboration()` checks only `(clone_cache / file_ref).is_file()`. It does not read line, symbol, implementation, route or polarity. Observe `verified_any` and that each aggregate item value stores claim ID, kind, text and confidence but no individual verification/corroboration state.

API kinds are bypassed rather than semantically reconciled:

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/facts/aspose_knowledge_selection.py | nl -ba | sed -n '95,112p'
```

## 6. Reproduce historical false 3D approval/no-op evidence

```bash
base='plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/3d--62fb89f3ca76--5735c3f66e57'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:"$base/README.md" | rg -n -C 2 'NurbsSurface|to_mesh|converting content to mesh'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:"$base/final-verdict.json" | rg -n 'AGENT_APPROVED|verdict|status'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:"$base/no-op-proof.json" | rg -n 'NO_OP_PROVEN|status|candidate_sha256'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:"$base/independent-agent-review.json" | rg -n 'finding|fact|identity|installation'
```

Then inspect the authorization source:

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:"$base/product-facts.json" | rg -n -C 3 'api.public_surface:python-exports|NurbsSurface|to_mesh'
```

## 7. Reproduce FBX, COLLADA, Barcode and import-root source truth

The supplied audit bundle and its extracted truth audit give exact claim IDs and source paths:

```bash
rg -n 'NurbsSurface|FBX|COLLADA|PdfRenderer|Barcode.to_pdf|aspose_3d_foss|aspose_note|aspose.threed|aspose.note' \
  /workspace/scratch/22cd18c3f75c/work/owner_audit/source_knowledge_truth/report.md \
  /workspace/scratch/22cd18c3f75c/work/owner_audit/source_knowledge_truth/truth_matrix.json \
  /workspace/scratch/22cd18c3f75c/work/readme-refresh-complete-bundle-20260819-174412
```

Verify the optimizer's stronger COLLADA route detector:

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/facts/curated_constraint_evidence.py | nl -ba | sed -n '129,240p'
```

This detector requires the Scene, service, base exporter, FBX exporter/plugin, COLLADA exporter/plugin and registration order; it is qualitatively stronger than generic file-existence corroboration.

## 8. Reproduce July Note Maven/JDK artifact

```bash
rg -n -C 3 'mvn clean install|JDK unknown|Maven' \
  plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-note-foss-for-python/candidate-readme.md \
  plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-note-foss-for-python/independent-review.json
```

This is a historical proposal whose own review is unverified, not an `AGENT_APPROVED` artifact.

## 9. Prove reconciliation is strict internally and best-effort at persistence

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/readme/readme_reconciliation.py | nl -ba | sed -n '115,215p'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/supervisor/local_poc_evidence.py | nl -ba | sed -n '327,355p'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:tests/unit/test_readme_reconciliation.py | nl -ba | sed -n '205,235p'
```

Observe overlap raises, relocation by substring containment, omission by any covering operation, caller exception-to-error-JSON conversion, and the real `pytest.xfail`.

## 10. Prove merged-review truncation has no top-level fallback

```bash
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/llm/reviewer_client.py | nl -ba | sed -n '15,25p;100,130p'
git show d71f38b6a050b5282f0ada314f9ee4de35950426:src/readme_agent/specialists/merged_readme_review.py | nl -ba | sed -n '50,130p'
```

Observe the 4000-token merged budget, one transport/response attempt, `client.analyze(messages)` before the fallback `try`, and fallback limited to a later blind-role grounding failure.

## 11. Reconcile the SEO fix that landed during the audit

```bash
git diff d71f38b6a050b5282f0ada314f9ee4de35950426..05ef1e532ae34bea07fefe951543a43f41ca55c4 -- \
  src/readme_agent/presentation/verified_template_capabilities.py \
  src/readme_agent/presentation/verified_template_capability_seo.py \
  tests/unit/test_verified_template_capabilities_seo_keyword_lineage.py
```

The diff proves the safety fix: changed title bytes, vocabulary grounding, no authoritative SEO fact ID, one keyword use. It also shows the residual: `keyword_used_here` is not part of the returned row tuple, so no persisted output-span attribution exists.

## 12. Reproduce later `setup.py` silent-empty evidence

```bash
git show 91d9479b1e1fa12a9af41c1692b6f8f421db5f76:plans/investigations/readme-knowledge-lineage-audit.md | nl -ba | sed -n '50,105p'
git show 91d9479b1e1fa12a9af41c1692b6f8f421db5f76:src/readme_agent/facts/python_dependency_acquisition.py | nl -ba | sed -n '35,80p'
git show 91d9479b1e1fa12a9af41c1692b6f8f421db5f76:src/readme_agent/facts/dependency_snapshot.py | rg -n -C 3 'no pyproject.toml|applicable'
```

## 13. Verify this audit package

```bash
cd /workspace/scratch/22cd18c3f75c/work/owner_audit/defect_gate_map
python -m json.tool DEFECT_GATE_MATRIX.json >/dev/null
sha256sum -c SHA256SUMS
```
