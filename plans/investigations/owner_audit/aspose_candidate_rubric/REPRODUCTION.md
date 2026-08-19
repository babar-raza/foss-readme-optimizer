# Reproduction Notes

Run from `/workspace/scratch/22cd18c3f75c`. These commands read the extracted bundle and write
only `work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json`.

## Pins

```bash
sha256sum upload/readme-refresh-complete-bundle-20260819-174412.zip
git -C work/github-foss-readme-optimizer rev-parse HEAD
```

Expected archive SHA-256:
`2d8eb6ae810d920b98136f3fa587b46d36b2e0c6b5250df109fa98c73e470465`.
The optimizer SHA is context only and may advance after this audit.

## Rebuild metrics

```bash
python work/owner_audit/aspose_candidate_rubric/collect_metrics.py
python -m json.tool \
  work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json >/dev/null
```

`collect_metrics.py` uses only the Python standard library. Its Markdown counts are structural
lexical measurements, not a browser-rendering engine: table counts use separator rows; badge
images are pre-H2 image links minus `banner-readme`; word counts use a documented regex; fenced
blocks classify Mermaid separately. None of these measurements is a quality score.

## Reconcile 31 canonical vs 30 eligible

```bash
find work/readme-refresh-complete-bundle-20260819-174412/files/reports/repo-presenter-regen-full \
  -mindepth 3 -maxdepth 3 -name readme.md | wc -l
jq '[.[] | select(.active == true)] | length' \
  work/readme-refresh-complete-bundle-20260819-174412/files/data/products.json
jq '.' \
  work/readme-refresh-complete-bundle-20260819-174412/files/data/registry_exclusions.json
```

Expected: 31 canonical files, 31 raw active rows, and an exclusion for `cells/typescript`, hence
30 eligible products. The unrelated excluded PDF Go MCP repository is not a canonical candidate.

## Verify 8 clean / 22 dirty

```bash
jq '{candidate_tree, clean_count, dirty_count, total, skipped}' \
  work/readme-refresh-complete-bundle-20260819-174412/files/reports/_scratch/mt056_audit_portfolio_FINAL.json
jq -r '.products[] | select(.clean) | (.family + "/" + .platform)' \
  work/readme-refresh-complete-bundle-20260819-174412/files/reports/_scratch/mt056_audit_portfolio_FINAL.json
```

Expected: `repo-presenter-regen-full`, 8 clean, 22 dirty, 30 total, no skipped products.

## Inspect aggregate metrics and ledgers

```bash
jq '.scope, .eligible_portfolio_summary.metric_distributions,
    .eligible_portfolio_summary.section_frequency_out_of_30,
    .eligible_portfolio_summary.ledger_aggregate' \
  work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json
jq '.by_platform, .by_family' \
  work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json
```

Each of the 31 candidate records contains product identity, eligible/excluded state, Markdown
metrics, all four ledger summaries, `last-verified.json` data where present, pinned clone-cache
README comparison, and the bundled audit's findings.

## Verify candidate-bound freshness

```bash
jq '{markers:.eligible_portfolio_summary.last_verified_marker_present,
     matching:.eligible_portfolio_summary.last_verified_marker_matches_candidate,
     mismatches:.eligible_portfolio_summary.marker_mismatch_products}' \
  work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json
```

Expected: 30 markers, 18 matching candidate bytes, 12 mismatches. A timestamp alone is not used
as evidence.

## Verify published-snapshot comparison

```bash
jq '{audit_published:([.candidates[] | select(.eligible_active and .portfolio_audit.published)] | length),
     raw_byte_equal:.eligible_portfolio_summary.candidate_byte_matches_pinned_published_snapshot,
     strip_equal:.eligible_portfolio_summary.candidate_pipeline_strip_matches_pinned_published_snapshot}' \
  work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json
jq -r '.candidates[] |
  select(.eligible_active and .published_snapshot.pipeline_strip_equal_to_candidate) |
  (.family + "/" + .platform)' \
  work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json
```

Expected against this bundle: 13 dated audit flags, 4 raw-byte matches, 12 matches under the
pipeline's `.strip()` comparison. The mismatch is reported rather than reconciled away because
the bundle is not an atomic live-GitHub snapshot.

## Verify deliverable checksums

```bash
cd work/owner_audit/aspose_candidate_rubric
sha256sum -c SHA256SUMS
```

Expected: every listed file reports `OK`.
