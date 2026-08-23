# Known limitations

1. **The five real PF-01 receipts are not qualified against this module.** See
   `CURRENT_FIVE_BLOCKS_MATRIX.md`. This is the single largest gap between this handoff
   and a fully "done" resolution of PF-01's `infra_external` count.

2. **`_DIAGNOSTIC_CODE_TO_BLOCK_CLASS` is this module's own vocabulary, not any real
   upstream tool's actual diagnostic codes.** The 12 codes (`GIT_CLONE_FAILED`,
   `TOOLCHAIN_UNAVAILABLE`, etc.) are illustrative placeholders chosen to be
   self-explanatory. Whoever integrates this module must either map real diagnostic
   signals from `deterministic_truth_salvage.py`, `local_verification.py`,
   `acquisition.py`, etc. onto this vocabulary, or extend the table with the real codes
   those modules actually produce.

3. **Only 5 of 13 `ExternalFactBlockClassV1` values have a dedicated causal-relevance
   row that was hand-checked against a real-world scenario during design** (the ones
   discussed at length in the task brief: `toolchain_unavailable`, `corrupt_local_cache`
   vs. `network_rate_limited`, `unsupported_platform_verifier`,
   `source_package_mismatch`, `repository_clone_failure`). The remaining 8 rows in
   `_CAUSALLY_RELEVANT_FIELDS_BY_BLOCK_CLASS` follow the same reasoning pattern but were
   not individually scenario-tested beyond the classification-mapping test
   (`test_every_documented_diagnostic_code_is_recognized_from_structured_input`). They
   are reasonable first-pass field selections, not battle-tested against real failures.

4. **The `omission_basis` conflict-resolution rule for tier 6 is simplistic.** If a
   catalog somehow contains multiple `non_applicability_evidence` items for the same
   claim kind with *different* `omission_basis` values (`"not_applicable"` for one,
   `"omit"` for another), the resolver deterministically picks the alphabetically-first
   `evidence_id`'s basis rather than treating the disagreement as its own kind of
   conflict. No test exercises this specific edge case; it was judged out of scope for
   a first pass and not called out in the original task brief.

5. **No fixture files were created**, per the design recommendation in
   `AUTHORIZED_WORDING_MATRIX.md`'s sibling planning work -- all 52 test scenarios are
   inline Python literals via small local helper functions (`_block`, `_evidence`,
   `_catalog`, `_fingerprint`), matching `tests/unit/test_readme_facts_readiness.py`'s
   established style. If a future integration needs sanitized real-world fixtures (once
   the five real receipts become available), they would need to be added fresh.

6. **`module_handoffs/` is a new top-level directory** (did not previously exist in this
   repository). It was created only because the task brief named it as the required
   handoff destination; it is not registered anywhere in `docs/architecture.md`'s
   directory map, since `docs/**` is a prohibited path for this lane. Whoever integrates
   this module should decide whether `module_handoffs/` becomes a standing convention
   (and gets documented) or whether this handoff should be relocated/removed once its
   contents are absorbed.
