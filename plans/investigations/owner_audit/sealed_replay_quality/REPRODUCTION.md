# Reproduction

Run these commands from `/workspace/scratch/22cd18c3f75c` unless a command explicitly changes
directory. They are read-only except for creation of disposable directories under `/tmp`.

## 1. Validate this audit bundle

```bash
jq empty work/owner_audit/sealed_replay_quality/MATRIX.json
jq empty work/owner_audit/sealed_replay_quality/REPLAY_FIXTURES.json
cd work/owner_audit/sealed_replay_quality
sha256sum -c SHA256SUMS
```

## 2. Confirm the sealed predecessor README bytes

The full-registry survey files are exact Git blobs for the three pre-refresh SHAs:

```bash
git hash-object work/github-foss-readme-optimizer/plans/investigations/evidence/full-registry-github-survey/aspose-3d-foss__Aspose.3D-FOSS-for-Python--README.md
git hash-object work/github-foss-readme-optimizer/plans/investigations/evidence/full-registry-github-survey/aspose-note-foss__Aspose.Note-FOSS-for-Python--README.md
git hash-object work/github-foss-readme-optimizer/plans/investigations/evidence/full-registry-github-survey/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python--README.md
```

Expected, in order:

```text
c952868888c0bd91688ad4fa2ddad8ddf8a04563
629a9706aabf7f20919abebda16b4a975e687490
069205725fdbd5b0fa8ae45087cb44d2908381d8
```

In a local clone of each target repository, independently confirm:

```bash
git show ab1a2267a0ba6302311d0c7c4ad01494974c7d76:README.md | git hash-object --stdin
git show 6d97a522a9ed24708687911f1aabb76e2dea2da7:README.md | git hash-object --stdin
git show 53f2c3350b8171f2c8275e7b1a178f218695ac45:README.md | git hash-object --stdin
```

## 3. Confirm exact published snapshots where present

```bash
git hash-object work/readme-refresh-complete-bundle-20260819-174412/files/reports/repo-presenter/_scratch/mt040_3d_python/live_readme.md
git hash-object work/readme-refresh-complete-bundle-20260819-174412/files/reports/repo-presenter/note/python/readme.md
```

Expected:

```text
4e4a264298dcf5099919d314834672653d1fed4f
ad1e4a5fb65f0394aa78ad9c703a346e032822fb
```

The exact published Barcode README blob is
`03445fbc7b846b51c500a4a5e3d956c14a57b149`, verified through GitHub at
`06eca5c01e13ed6d59a640f1cf330c1c5a57d151`. The supplied bundle contains earlier/later
Barcode candidate variants, not that exact blob; fetch it from GitHub or run the following in a
local target clone before byte-level comparison:

```bash
git show 06eca5c01e13ed6d59a640f1cf330c1c5a57d151:README.md | git hash-object --stdin
```

## 4. Reproduce the historical optimizer delta

These diffs demonstrate that the 2026-07-25 candidates mostly wrap the old README:

```bash
diff -u \
  work/github-foss-readme-optimizer/plans/investigations/evidence/full-registry-github-survey/aspose-3d-foss__Aspose.3D-FOSS-for-Python--README.md \
  work/github-foss-readme-optimizer/plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-3d-foss-for-python/candidate-readme.md

diff -u \
  work/github-foss-readme-optimizer/plans/investigations/evidence/full-registry-github-survey/aspose-note-foss__Aspose.Note-FOSS-for-Python--README.md \
  work/github-foss-readme-optimizer/plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-note-foss-for-python/candidate-readme.md

diff -u \
  work/github-foss-readme-optimizer/plans/investigations/evidence/full-registry-github-survey/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python--README.md \
  work/github-foss-readme-optimizer/plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-barcode-foss-for-python/candidate-readme.md
```

Confirm all three failed independent review:

```bash
for product in aspose-3d-foss-for-python aspose-note-foss-for-python aspose-barcode-foss-for-python; do
  jq '{org_repo, verified, failures}' \
    "work/github-foss-readme-optimizer/plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/$product/independent-review.json"
done
```

Confirm the identical missing-field pattern:

```bash
for product in aspose-3d-foss-for-python aspose-note-foss-for-python aspose-barcode-foss-for-python; do
  jq '[.facts[] | select(.verification_state == "missing") | .field]' \
    "work/github-foss-readme-optimizer/plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/$product/product-facts-v2.json"
done
```

## 5. Reproduce Aspose content-accountability counts

```bash
for product in 3d note barcode; do
  file="work/readme-refresh-complete-bundle-20260819-174412/files/reports/repo-presenter-regen-full/$product/python/content-dispositions.json"
  printf '%s\n' "$product"
  jq '{
    units: length,
    dispositions: (group_by(.disposition) | map({disposition: .[0].disposition, count: length})),
    verification: (group_by(.verification.status) | map({status: .[0].verification.status, count: length}))
  }' "$file"
done
```

Expected totals: 3D 71 units (11 merged/reframed, 60 excluded); Note 148 (120 merged/reframed,
28 excluded); Barcode 51 (40 merged verbatim, 11 excluded).

## 6. Reproduce imported-knowledge contamination findings

Confirm declared SHAs:

```bash
for product in 3d note barcode; do
  printf '%s ' "$product"
  sed -n 's/^repo_sha: //p' "work/github-foss-readme-optimizer/data/imported/knowledge/$product/python/merged/model.yaml"
done
```

Count claims whose evidence points at a README:

```bash
for product in 3d note barcode; do
  file="work/github-foss-readme-optimizer/data/imported/knowledge/$product/python/merged/claims.json"
  printf '%s ' "$product"
  jq '[.[] | select((.evidence // []) | any(((.file // .source_file // "") | ascii_downcase | contains("readme"))))] | length' "$file"
done
```

Expected: 3D `70`, Note `0`, Barcode `10`.

Inspect the decisive 3D contradiction and unsupported inferences:

```bash
jq '[.[] | select(
  (.claim_id // .id) == "ERC-3d-python-338c230c" or
  (.claim_id // .id) == "ERC-3d-python-8e9815fe" or
  (.claim_id // .id) == "CLM-3d-f966ea" or
  (.claim_id // .id) == "CLM-3d-31f56e" or
  (.claim_id // .id) == "ERC-3d-python-cb601cba" or
  (.claim_id // .id) == "ERC-3d-python-f14fb8f0"
) | {id: (.claim_id // .id), kind, text, evidence, provenance}]' \
  work/github-foss-readme-optimizer/data/imported/knowledge/3d/python/merged/claims.json
```

## 7. Clean replay protocol

For each product, create a disposable clone and checkout the sealed SHA. Do not copy any Aspose
candidate into it or into the model/retrieval context.

```bash
fixture_root=$(mktemp -d)
git clone --no-checkout https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git "$fixture_root/3d-python"
git -C "$fixture_root/3d-python" checkout --detach ab1a2267a0ba6302311d0c7c4ad01494974c7d76

git clone --no-checkout https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python.git "$fixture_root/note-python"
git -C "$fixture_root/note-python" checkout --detach 6d97a522a9ed24708687911f1aabb76e2dea2da7

git clone --no-checkout https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python.git "$fixture_root/barcode-python"
git -C "$fixture_root/barcode-python" checkout --detach 53f2c3350b8171f2c8275e7b1a178f218695ac45
```

Before running the optimizer, require an input manifest containing the target tree SHA, README
blob/SHA-256, knowledge hashes, configuration hash, model identifier, and an assertion that no
post-refresh reference was mounted. Seal the optimizer candidate and its evidence ledger first.
Only then mount the Aspose reference for blind comparison. A second run over the first candidate
tests idempotence; it is not a substitute for the first generation run.
