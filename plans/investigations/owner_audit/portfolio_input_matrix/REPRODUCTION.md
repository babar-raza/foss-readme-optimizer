# Reproduction

## Source pins

- Optimizer GitHub main at audit start: `d71f38b6a050b5282f0ada314f9ee4de35950426`.
- Older local audit checkout: `56a5f09c80f57581d977d77142ed8809ed1ede9d`; `git merge-base d71f38b6 HEAD` equals 56a5f09, so d71 is authoritative.
- Aspose skill bundle: `work/readme-refresh-complete-bundle-20260819-174412/`.

## Read-only checks

```bash
cd /workspace/scratch/22cd18c3f75c/work/github-foss-readme-optimizer
jq 'length' data/products.json
jq -r 'group_by(.ecosystem)[] | [.[0].ecosystem,length] | @tsv' data/products.json
find data/imported/knowledge -mindepth 3 -maxdepth 3 -type d -name merged | wc -l
find data/imported/knowledge -mindepth 4 -maxdepth 4 -type f -name bundle_manifest.json | wc -l
git show d71f38b6:data/imported/knowledge_manifest.json | jq '{schema_version,aggregate_sha256,bundle_count:(.bundles|length)}'
find ../readme-refresh-complete-bundle-20260819-174412/files/reports/repo-presenter-regen-full -mindepth 3 -maxdepth 3 -name readme.md | wc -l
find plans/investigations/evidence/finalized-repository-readmes-v1/repositories -mindepth 2 -maxdepth 2 -type d | wc -l
```

GitHub connector calls were read-only:

- `github_get_repo` for all 33 repository full names (accessibility/default branch).
- `github_search_commits(query="", topn=1)` for each repository (current tip SHA/date).
- `github_fetch(https://api.github.com/repos/{owner}/{repo}/contents/)` for each root (tree shape, README size, root manifests), plus targeted nested manifest directories for 3d/net, email/net, and cells/cpp.

## Deterministic verification

```bash
cd /workspace/scratch/22cd18c3f75c/work/owner_audit/portfolio_input_matrix
python -m json.tool PORTFOLIO_MATRIX.json >/dev/null
sha256sum -c SHA256SUMS
```

`build_evidence.py` was a temporary evidence generator and is not part of the final bundle. The four delivered files are the complete output.
