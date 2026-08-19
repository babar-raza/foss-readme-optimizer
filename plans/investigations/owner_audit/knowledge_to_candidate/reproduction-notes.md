# Reproduction notes

## Scope and safety

This audit was read-only. It did not invoke the production supervisor against a real repository, call the Qwen endpoint, mutate a clone, write GitHub state, or alter the optimizer checkout. The only writes are the five files in this audit directory.

The repository’s `AGENTS.md` prohibits proving real-repository behavior by calling production internals directly. The numeric selector calculations reported here were pure, read-only forensic calculations over already imported JSON and immutable local clones; they are not represented as production-run proof. Existing committed runtime/evidence artifacts remain the source of truth for historical runs.

## Pins and roots

- Optimizer checkout inspected: `/tmp/knowledge-audit-current`
- Audit pin: `6d112bbf88bc54f7ef3367b16ef8e9b769bdfb51`
- Latest main later observed by owner: `d71f38b6`
- Material post-pin change: `eaf5eef6` repaired five baseline-test failures by excluding `template_sha256` from semantic plan hashes after field-diff and skipping a mutable Note runtime artifact after hash mismatch. Reported current suite result: 4,207 passed, one skipped, one xfailed, zero failed. Later `5e9…`/`d71…` changes are auto-push/auth robustness. None touches the audited knowledge-to-candidate path.
- 3D clone: `/tmp/source-knowledge-truth.CkQFZ2/3d-python` at `ee05c1ba9153ef5916b7a108406c794f2e464d01`
- Note clone: `/tmp/source-knowledge-truth.CkQFZ2/note-python` at `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676`
- Barcode clone: `/tmp/source-knowledge-truth.CkQFZ2/barcode-python` at `06eca5c01e13ed6d59a640f1cf330c1c5a57d151`
- Aspose bundle: `/workspace/scratch/22cd18c3f75c/work/readme-refresh-complete-bundle-20260819-174412`
- Repository-pin note: `/workspace/scratch/22cd18c3f75c/work/owner_audit/repository_pins.md`

The current target tips already include refreshed READMEs. Do not use current README text as proof that the optimizer or imported corpus caused those bytes.

## Primary evidence paths

Optimizer code:

- `src/readme_agent/facts/provider.py`
- `src/readme_agent/facts/aspose_knowledge_claims.py`
- `src/readme_agent/facts/aspose_knowledge_selection.py`
- `src/readme_agent/facts/aspose_detectors.py`
- `src/readme_agent/facts/aspose_seo_keyword_facts.py`
- `src/readme_agent/facts/acceptance_contract.py`
- `src/readme_agent/facts/render_views.py`
- `src/readme_agent/facts/knowledge_application_evidence.py`
- `src/readme_agent/readme/agentic_composition.py`
- `src/readme_agent/readme/agentic_composition_inputs.py`
- `src/readme_agent/readme/claim_map.py`
- `src/readme_agent/presentation/verified_template_capabilities.py`
- `src/readme_agent/specialists/factual_review_packet.py`
- `src/readme_agent/validation/aspose_checks_bridge.py`
- `src/readme_agent/readme/document_validation.py`
- `src/readme_agent/supervisor/product_truth.py`
- `src/readme_agent/supervisor/local_poc_cache.py`

Imported data:

- `data/imported/knowledge_manifest.json`
- `data/imported/data/products.json`
- `data/imported/knowledge/{3d,note,barcode}/python/merged/`

Historical optimizer evidence:

- `plans/investigations/evidence/finalized-repository-readmes-v1/cohort-manifest.json`
- `plans/investigations/evidence/finalized-repository-readmes-v1/repositories/python/{3d,note,barcode}--*/`

Aspose bundle evidence:

- `verification/results.txt`
- `verification/pytest-readme-refresh-summary.txt`
- `files/reports/repo-presenter-regen-full/*/*/readme.md`
- `files/reports/_scratch/mt056_audit_portfolio_FINAL.json`
- `files/reports/_scratch/mt049_portfolio_sweep_results.json`
- `files/reports/_scratch/mt050_install_quickstart_leak_sweep_results.json`
- `files/reports/_scratch/mt051_image_disposition_sweep_results.json`

## Read-only inventory commands

Run from `/tmp/knowledge-audit-current` unless noted:

```bash
git rev-parse HEAD
find data/imported -type f | wc -l
du -sb data/imported
find data/imported/knowledge -mindepth 3 -maxdepth 3 -type d -name merged | sort
find plans/investigations/evidence/finalized-repository-readmes-v1/repositories \
  -mindepth 2 -maxdepth 2 -type d | sort
```

Portfolio/bundle reconciliation:

```bash
find "$ASPOSE_BUNDLE/files/reports/repo-presenter-regen-full" \
  -iname readme.md -not -path '*/_scratch/*' -printf '%P\n' | sort
python -m json.tool \
  "$ASPOSE_BUNDLE/files/reports/_scratch/mt056_audit_portfolio_FINAL.json"
python -m json.tool \
  plans/investigations/evidence/finalized-repository-readmes-v1/cohort-manifest.json
```

Static consumer discovery:

```bash
rg -n "data/imported|knowledge_manifest|knowledge_claim_fact_records|build_aspose_detection_bundle" \
  src/readme_agent --glob '*.py' --glob '!**/vendored_asposeorg/**'
rg -n "run_aspose_checks|blocking_aspose_check_findings" \
  src/readme_agent --glob '*.py' --glob '!**/vendored_asposeorg/**'
rg -n "build_knowledge_application_report|write_local_poc_knowledge_application" \
  src/readme_agent --glob '*.py'
```

Bundle row counts were obtained by parsing JSON/YAML and taking list lengths for the six named files. Aggregate claim-kind counts were obtained by parsing every `merged/claims.json` and counting `kind`. Evidence-shape counts were obtained by enumerating each claim’s `evidence` objects and classifying `file` versus `source_file` keys.

## Selector calculation protocol

For each trio member, use:

- family/platform from registry;
- `data_root=<optimizer>/data/imported`;
- `clone_cache=<pinned current clone>`;
- `source_revision=<current clone HEAD>`.

Record every disposition and group by:

- accepted/rejected;
- `kind`;
- `verification_state`;
- `corroboration`;
- `rejection_reason`;
- `resulting_fact_field`.

Then determine author eligibility from the same accepted-state rule used by `accepted_composition_fact_ids`: selected fact state is `verified` or `policy_approved` and has no unresolved conflict. Count both field records and item members; never compare one to the other as if they shared a unit.

The `source_file` experiment was a forensic in-memory key-normalization calculation, not a code edit. It treated `evidence[].source_file` as a candidate file reference under the same repository-relative existence rule as `file`, then reran the eligibility aggregation. It demonstrated a real mixed 3D install field and the downstream `verified_any` authorization defect.

## Visible-influence test

The historical candidate exact-match check normalized selected claim text and candidate text, then tested complete claim-string containment. Result: zero matches for 3D, Note, and Barcode.

This test has only one safe interpretation: it found no exact-copy evidence. It cannot disprove paraphrase. The decisive absence is instead that:

1. historical candidates predate the new knowledge layer;
2. they have no `knowledge-application.json`;
3. the current production writer is pre-render only;
4. no current post-feature trio candidate bundle was available.

Therefore visible imported-claim influence is “not proven,” not “proved absent from every possible run.”

## Candidate hashes and counts

Candidate SHA-256 values were computed over exact file bytes; word counts used whitespace tokenization only as a descriptive size measure. They are not quality metrics.

Historical candidate identities are encoded in their directory names. Current published README identities came from the pinned target clones. Aspose candidate identities came from `repo-presenter-regen-full` in the supplied bundle.

## Known limits

- No Qwen request was made, so the report can prove what is offered to the model but not what a new model call would choose.
- No current post-feature end-to-end optimizer run exists in the inspected evidence for the trio.
- The Aspose bundle has no PSD candidate; its PSD behavior cannot be verified here.
- The bundle’s final portfolio audit is an internal snapshot and may predate later unbundled repairs. Within the supplied evidence, however, it is the strongest portfolio-wide acceptance artifact and does not show 30/30 clean.
- Exact text matching is not semantic influence detection; only byte/provenance binding is accepted as positive proof.
- Current GitHub main moved after the audit pin. The owner reviewed the intervening commits and identified no change to the audited knowledge path; if later commits touch any causal module listed above, rerun the audit.

## Validation of these deliverables

```bash
python -m json.tool lineage-matrix.json >/dev/null
sha256sum report.md lineage-matrix.json repair-backlog.md reproduction-notes.md > SHA256SUMS
sha256sum -c SHA256SUMS
```
