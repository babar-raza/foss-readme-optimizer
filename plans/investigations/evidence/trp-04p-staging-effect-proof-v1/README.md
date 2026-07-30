# TRP-04P Disposable Staging Effect Proof

This evidence closes `TRP-04P-STAGING-EFFECT-PROOF` for the immutable trusted cohort
`1773cf81721531515766e5a61dc1a2e1ca467e1d6cc8350920f04dbb15095331`.

The canonical production workflow was exercised under `act_staging_effect`. It consumed the
already-qualified trusted candidates, skipped analysis and LLM work, and allowed the dedicated
staging effect job to use the isolated write credential. Live scenarios covered first creation,
unchanged reuse, in-place candidate update, proposal-branch drift, duplicate delivery,
lost-response reconciliation, expired authorization, and crash-boundary recovery.

The three cohort targets now each have exactly one open draft PR on
`readme-agent/presentation-update`. A fourth private disposable target exists only to prove first
creation inside the canonical workflow; it is not a new cohort member. Independent GitHub reads
confirmed that all four default branches retain their initial commit and README bytes, while all
four proposal branches contain the exact qualified candidate bytes.

This is trusted-content transport proof, not factual verification. Existing README claims remain
`trusted_inherited`, `factual_truth_verified` remains false, and none of this evidence can satisfy
repository-verified Gate A/B/C or a maturity level.

## Reproduction

1. Validate the frozen cohort manifest and its SHA-256 inventory.
2. Validate the staging target manifest and expiring authorization records under `runs/staging/`.
3. Run `.github/workflows/readme-agent-production.yml` with `proof_mode=act_staging_effect`, the
   cohort manifest, a staging target manifest, `--bind`, and the dedicated staging write secret.
4. Compare each target's `main` revision and README SHA-256 with `verification.json`.
5. Compare the stable proposal branch README SHA-256 with the cohort candidate SHA-256.
6. Query open pull requests and require exactly one draft PR from the stable proposal branch.
7. Scan runtime logs for the staging token and require zero matches.
8. Recompute this directory's `sha256sums.txt`.

Raw runtime logs, isolated state, authorization fixtures, target manifests, and workflow result
records remain under `runs/staging/`. They are intentionally not committed because `runs/` is
disposable runtime state.

## Cleanup

Retain the four private disposable staging repositories and their open draft PRs through GitHub App
hosted qualification. Never merge them. Cleanup requires retained evidence and explicit
authorization.
